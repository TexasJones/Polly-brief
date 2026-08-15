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


@dataclass
class JobPosting:
    title: str
    company: str
    location: Optional[str]
    url: str
    date_posted: Optional[dt.date]
    category: Optional[str] = None
    logo_url: Optional[str] = None


@dataclass
class HiringPulse:
    total_active: int
    new_today: int
    top_employers: list[tuple[str, int]] = field(default_factory=list)
    top_categories: list[tuple[str, int]] = field(default_factory=list)
    featured: list[JobPosting] = field(default_factory=list)


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


def build_hiring_pulse(jobs: list[JobPosting], num_featured: int = 4, num_employers: int = 5,
                        num_categories: int = 5, today: Optional[dt.date] = None,
                        snapshot_path: Path = SNAPSHOT_PATH) -> HiringPulse:
    today = today or dt.date.today()
    total_active = len(jobs)

    current_urls = {_job_key(j) for j in jobs}
    previously_seen = _load_seen_urls(snapshot_path)

    # First run ever (no snapshot file yet): don't claim every job is "new,"
    # that's noise, not signal. Treat it as a baseline instead.
    if previously_seen:
        new_today = sum(1 for j in jobs if _job_key(j) not in previously_seen)
    else:
        new_today = 0

    _save_seen_urls(current_urls, snapshot_path)

    top_employers = Counter(j.company for j in jobs).most_common(num_employers)
    top_categories = Counter(j.category for j in jobs if j.category).most_common(num_categories)

    # Featured = most recently posted, deduped by company so one employer
    # doesn't hog the whole "Featured Jobs" block
    sorted_jobs = sorted(
        jobs,
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
    )


def get_hiring_pulse(feed_url: str = FEED_URL) -> HiringPulse:
    jobs = fetch_all_jobs(feed_url=feed_url)
    return build_hiring_pulse(jobs)


if __name__ == "__main__":
    pulse = get_hiring_pulse()
    print(f"Active jobs: {pulse.total_active}")
    print(f"New today:   {pulse.new_today}")
    print("Top employers:", pulse.top_employers)
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
