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
"""

from __future__ import annotations

import datetime as dt
from collections import Counter
from dataclasses import dataclass, field
from typing import Optional
from xml.etree import ElementTree as ET

import requests

# Raw feed straight from the scraper's repo (TexasJones/political-jobs-feed,
# main branch). Swap this for a different URL if the feed ever moves (e.g.
# to a CDN or the site's own domain).
FEED_URL = "https://raw.githubusercontent.com/TexasJones/political-jobs-feed/main/feed.xml"


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
        url = _text(job_el, "canonical_url") or _text(job_el, "apply_url") or ""

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


def build_hiring_pulse(jobs: list[JobPosting], num_featured: int = 4, num_employers: int = 5,
                        num_categories: int = 5, today: Optional[dt.date] = None) -> HiringPulse:
    today = today or dt.date.today()
    total_active = len(jobs)
    new_today = sum(1 for j in jobs if j.date_posted == today)
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
