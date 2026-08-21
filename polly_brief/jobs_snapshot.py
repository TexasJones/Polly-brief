"""
jobs_snapshot.py
-----------------
Builds the "Hiring Pulse" and "Featured Jobs" sections of The Polly Brief
directly from the political-jobs-feed scraper's own output (feed.xml),
rather than scraping the live Job Boardly HTML pages.

This is the same feed.xml that gets imported into thepolly.co's job board,
fetched straight from GitHub — so it's the actual source of truth for
what's on Polly, not a guess at fragile page markup.

If the feed's field names or hosting location ever change, only
FEED_URL and `_parse_feed_xml()` need updating.

"New Today" logic
------------------
`date_posted` comes from the original ATS (Greenhouse, Lever, etc.) and
reflects when the EMPLOYER posted the job — not when it showed up on Polly.
Comparing that to "today" only works if the brief happens to run the same
calendar day the job was originally posted, which is rare, and the scraper
only refreshes feed.xml weekly anyway, so most days nothing would match.

Instead, "new" is now a delta: a job counts as new if its URL wasn't in the
snapshot from the last time the brief ran. That snapshot is a small JSON
file committed back to the repo after each run (see SNAPSHOT_PATH below).
The GitHub Actions workflow needs a step to commit this file after
generate_brief.py runs — see the note at the bottom of this file.

Freshness logic
----------------
Earlier versions of this script treated "the job is still in feed.xml" as
equivalent to "the job is still active," which isn't true — a company can
leave a Greenhouse/Lever posting reachable for weeks after the role has
effectively closed. Every job is now classified by age into fresh / active
/ aging / stale / unknown (see `classify_freshness`), and:

  - "Active" counts (total_active, top employers/categories, location_mix)
    include fresh + active + unknown jobs. Unknown-date jobs are kept
    rather than silently dropped — a growing unknown count usually means
    the upstream feed's date_posted parsing is breaking on some source
    site, and that's worth being able to see, not something to hide by
    excluding them.
  - "Featured" jobs (the ones shown first in the newsletter) are fresh only.
  - Nothing is deleted from the feed itself — fetch_all_jobs() still returns
    every job, so the full history/archive is preserved. Only what counts
    as "active" and what's eligible for "featured" changes.

FRESH_DAYS / ACTIVE_DAYS / AGING_DAYS are starting points, not gospel —
tune them once we see real distribution data. FRESHNESS_OVERRIDES_DAYS
exists because some categories (gov appointments, fellowships) genuinely
stay open far longer than a typical entry-level or comms role.

Location mix
------------
`location_mix` counts live jobs by Remote / Hybrid / Onsite for the
"Hiring Pulse" stacked bar in the newsletter. This reads the feed's
`location` field directly — the scraper (political-jobs-feed) already
writes a clean categorical label there ("Remote" / "Hybrid" / "Onsite"),
separate from the messy free-text office address, which lives in
`office_location` instead. See political_jobs_feed.py's add_job(): the
`location` tag is a compatibility alias carrying LOCATION_TYPE_LABELS,
specifically so downstream consumers like this one don't have to
re-parse free text to figure out work arrangement. That means no new
scraping or state is needed here — just a count of a value already being
read into JobPosting.location today.
"""

from __future__ import annotations

import datetime as dt
import json
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from xml.etree import ElementTree as ET

import requests

# Raw feed straight from the scraper's repo (TexasJones/political-jobs-feed,
# main branch). Swap this for a different URL if the feed ever moves (e.g.
# to a CDN or the site's own domain).
FEED_URL = "https://raw.githubusercontent.com/TexasJones/political-jobs-feed/main/feed.xml"

# Where the "jobs seen last run" snapshot lives. Anchored to this file's own
# location (not the current working directory) so it resolves correctly
# regardless of whether the workflow runs this from the repo root or from
# inside polly_brief/ — cwd-relative paths silently break depending on how
# `generate_brief.py` gets invoked, so this avoids that class of bug.
SNAPSHOT_PATH = Path(__file__).resolve().parent / ".state" / "seen_jobs.json"

# Freshness buckets, in days since date_posted. Defaults — some categories
# (fellowships, gov appointments, senior/exec searches) genuinely stay open
# far longer than a typical entry-level or comms role, so treat these as a
# starting point to tune once we see real data, not gospel.
FRESH_DAYS = 14
ACTIVE_DAYS = 30
AGING_DAYS = 45

# Per-category overrides for how long a job can go before hitting "stale."
# Add to this as we learn which categories legitimately run long.
FRESHNESS_OVERRIDES_DAYS: dict[str, int] = {
    "Government & Policy": 60,
    "Fellowship": 90,
}

# Canonical order for the location-mix stacked bar. Anything in the feed
# that isn't one of these three labels (shouldn't happen, given the
# scraper's LOCATION_TYPE_LABELS, but feeds drift) is simply not counted
# rather than crashing the run — see build_hiring_pulse().
LOCATION_TYPES = ("Remote", "Hybrid", "Onsite")


@dataclass
class JobPosting:
    title: str
    company: str
    location: Optional[str]
    url: str
    date_posted: Optional[dt.date]
    category: Optional[str] = None
    logo_url: Optional[str] = None
    age_days: Optional[int] = None   # filled in at build time (needs "today"), not fetch time
    status: str = "unknown"          # "fresh" / "active" / "aging" / "stale" / "unknown"


@dataclass
class HiringPulse:
    total_active: int
    new_today: int
    top_employers: list[tuple[str, int]] = field(default_factory=list)
    top_categories: list[tuple[str, int]] = field(default_factory=list)
    featured: list[JobPosting] = field(default_factory=list)
    # Counts of live jobs by work arrangement, e.g. {"Remote": 55, "Hybrid": 39, "Onsite": 37}.
    # Always has all three LOCATION_TYPES keys present (zero-filled), so
    # template.py can render a stacked bar without checking for missing keys.
    location_mix: dict[str, int] = field(default_factory=dict)


def _text(job_el, tag: str) -> Optional[str]:
    child = job_el.find(tag)
    if child is None or child.text is None:
        return None
    return child.text.strip()


def _parse_date(s: Optional[str]) -> Optional[dt.date]:
    if not s:
        return None
    try:
        return dt.date.fromisoformat(s[:10])
    except ValueError:
        return None


def _parse_feed_xml(xml_bytes: bytes) -> list[JobPosting]:
    root = ET.fromstring(xml_bytes)
    jobs = []
    for job_el in root.findall("job"):
        title = _text(job_el, "title")
        company = _text(job_el, "company")
        if not title or not company:
            continue  # skip malformed entries rather than crash the whole run

        location = _text(job_el, "location") or _text(job_el, "office_location")
        # apply_url comes straight from the original source (Greenhouse, Lever,
        # etc.) and is always correct. canonical_url is the scraper's *guess*
        # at what URL Job Boardly will assign the job on import, and that
        # guess doesn't always match reality — which is what was causing
        # 404s in the newsletter. Preferring apply_url means links always
        # work, at the cost of sending readers off Polly's own site to apply.
        url = _text(job_el, "apply_url") or _text(job_el, "canonical_url") or ""

        jobs.append(JobPosting(
            title=title,
            company=company,
            location=location,
            url=url,
            date_posted=_parse_date(_text(job_el, "date_posted")),
            category=_text(job_el, "category"),
            logo_url=_text(job_el, "logo") or _text(job_el, "company_logo"),
        ))
    return jobs


def fetch_all_jobs(feed_url: str = FEED_URL, session: Optional[requests.Session] = None) -> list[JobPosting]:
    sess = session or requests.Session()
    resp = sess.get(feed_url, timeout=20)
    resp.raise_for_status()
    return _parse_feed_xml(resp.content)


def _job_key(job: JobPosting) -> str:
    """Stable identifier for a job across runs. URL is unique per posting
    and doesn't change if title/category get re-classified later."""
    return job.url or f"{job.company}::{job.title}"


def _load_seen_urls(path: Path = SNAPSHOT_PATH) -> set[str]:
    if not path.exists():
        return set()
    try:
        data = json.loads(path.read_text())
        return set(data.get("seen_urls", []))
    except (json.JSONDecodeError, OSError):
        # Corrupt or unreadable snapshot shouldn't crash the whole run —
        # worst case everything looks "new" once, which is recoverable.
        return set()


def _save_seen_urls(urls: set[str], path: Path = SNAPSHOT_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "seen_urls": sorted(urls),
        "updated_at": dt.date.today().isoformat(),
    }, indent=2))


def compute_age_days(date_posted: Optional[dt.date], today: dt.date) -> Optional[int]:
    if date_posted is None:
        return None
    return (today - date_posted).days


def classify_freshness(age_days: Optional[int], category: Optional[str] = None) -> str:
    """Bucket a job by age. `age_days is None` means the feed didn't give us
    a parseable date_posted — that's reported as 'unknown' rather than
    silently defaulting to fresh OR silently getting dropped, so it stays
    visible in the data instead of being hidden by a default assumption."""
    if age_days is None:
        return "unknown"

    stale_cutoff = FRESHNESS_OVERRIDES_DAYS.get(category, AGING_DAYS)

    if age_days <= FRESH_DAYS:
        return "fresh"
    if age_days <= ACTIVE_DAYS:
        return "active"
    if age_days <= stale_cutoff:
        return "aging"
    return "stale"


def _compute_location_mix(live_jobs: list[JobPosting]) -> dict[str, int]:
    """Count live jobs by work arrangement. Zero-fills all three
    LOCATION_TYPES keys (even if a category had no postings today) so
    template.py never needs a `.get(label, 0)` fallback dance — it can just
    index straight into the dict. Anything outside the three known labels
    (an empty string, or a feed drifting from LOCATION_TYPE_LABELS) is
    silently excluded from the mix rather than raising, same philosophy as
    the rest of this file: a malformed field shouldn't crash a whole run."""
    counts = Counter(j.location for j in live_jobs if j.location in LOCATION_TYPES)
    return {label: counts.get(label, 0) for label in LOCATION_TYPES}


def build_hiring_pulse(jobs: list[JobPosting], num_featured: int = 4, num_employers: int = 5,
                        num_categories: int = 5, today: Optional[dt.date] = None,
                        snapshot_path: Path = SNAPSHOT_PATH) -> HiringPulse:
    today = today or dt.date.today()

    # Classify every job before doing anything else with the list.
    for j in jobs:
        j.age_days = compute_age_days(j.date_posted, today)
        j.status = classify_freshness(j.age_days, j.category)

    # "Active" for the Brief/board = fresh + active + unknown. Aging/stale
    # jobs are excluded from counts and stats, but NOT deleted from `jobs`
    # itself — fetch_all_jobs() still returns the full feed, so the archive
    # is preserved even though live_jobs is the filtered view used here.
    live_jobs = [j for j in jobs if j.status in ("fresh", "active", "unknown")]
    total_active = len(live_jobs)

    # Snapshot tracking is based on the FULL feed (not live_jobs), so a job
    # that goes stale and later reappears (e.g. re-scraped, re-posted)
    # doesn't get treated as brand new just because it dropped off the
    # "seen" list while it was excluded from live_jobs.
    current_urls = {_job_key(j) for j in jobs}
    previously_seen = _load_seen_urls(snapshot_path)

    # First run ever (no snapshot file yet): don't claim every job is "new,"
    # that's noise, not signal. Treat it as a baseline instead.
    if previously_seen:
        new_today = sum(1 for j in live_jobs if _job_key(j) not in previously_seen)
    else:
        new_today = 0

    _save_seen_urls(current_urls, snapshot_path)

    top_employers = Counter(j.company for j in live_jobs).most_common(num_employers)
    top_categories = Counter(j.category for j in live_jobs if j.category).most_common(num_categories)
    location_mix = _compute_location_mix(live_jobs)

    # Featured = fresh only, deduped by company so one employer doesn't hog
    # the whole "Featured Jobs" block. No point leading the newsletter with
    # a 3-week-old posting just because it happened to sort first.
    sorted_jobs = sorted(
        (j for j in live_jobs if j.status == "fresh"),
        key=lambda j: j.date_posted or dt.date.min,
        reverse=True,
    )
    featured, used_companies = [], set()
    for j in sorted_jobs:
        if j.company in used_companies:
            continue
        featured.append(j)
        used_companies.add(j.company)
        if len(featured) >= num_featured:
            break

    return HiringPulse(
        total_active=total_active,
        new_today=new_today,
        top_employers=top_employers,
        top_categories=top_categories,
        featured=featured,
        location_mix=location_mix,
    )


def get_hiring_pulse(feed_url: str = FEED_URL) -> HiringPulse:
    jobs = fetch_all_jobs(feed_url=feed_url)
    return build_hiring_pulse(jobs)


if __name__ == "__main__":
    pulse = get_hiring_pulse()
    print(f"Active jobs: {pulse.total_active}")
    print(f"New today:   {pulse.new_today}")
    print("Top employers:", pulse.top_employers)
    print("Location mix:", pulse.location_mix)
    print("Featured:")
    for j in pulse.featured:
        print(f"  - {j.title} @ {j.company} ({j.location}) -> {j.url}")

# ---------------------------------------------------------------------------
# GitHub Actions workflow note:
#
# This script writes polly_brief/.state/seen_jobs.json on every run, but that
# write only persists locally to the runner — it needs to be committed back
# to the repo or the next run will start from an empty snapshot again (which
# just re-triggers the "first run, treat as baseline" case above forever).
#
# Add a step AFTER "Generate the Brief" in the workflow, e.g.:
#
#   - name: Commit updated job snapshot
#     run: |
#       git config user.name "actions-user"
#       git config user.email "actions@github.com"
#       git add polly_brief/.state/seen_jobs.json
#       git diff --quiet --cached || git commit -m "Update seen jobs snapshot"
#       git push
#
# The `git diff --quiet --cached ||` guards against an empty commit on days
# the job list didn't change at all.
# ---------------------------------------------------------------------------
