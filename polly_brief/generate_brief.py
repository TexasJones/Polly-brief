"""
generate_brief.py
------------------
Entry point. Generates The Polly Brief as an HTML file.

Usage:
    python3 generate_brief.py                 # live: feed.xml + news RSS
    python3 generate_brief.py --sample         # offline: sample data for preview
    python3 generate_brief.py --out brief.html
    python3 generate_brief.py --quote "Text of quote" --quote-source "Name, Title"

The Quote of the Day is intentionally NOT auto-generated or auto-scraped —
misattributing a quote to a real person is the kind of mistake that's very
visible and very avoidable. Pass one in manually with --quote/--quote-source,
or leave it out and that section is skipped.
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys

from jobs_snapshot import HiringPulse, JobPosting, get_hiring_pulse
from news_snapshot import NewsItem, TopStory, get_top_stories
from template import render_brief


def _sample_data():
    pulse = HiringPulse(
        total_active=1247,
        new_today=58,
        top_categories=[("Campaigns", 0), ("Communications", 0), ("Public Affairs", 0),
                         ("Government Relations", 0), ("Digital", 0)],
        top_employers=[("Morning Consult", 0), ("FP1 Strategies", 0), ("Public Affairs Council", 0),
                        ("Senate Offices", 0), ("Movement Labs", 0)],
    )
    stories = [
        TopStory("Congress", "🏛", NewsItem("Politico", "Sample Congress headline", "https://example.com", "Two-sentence summary would appear here.")),
        TopStory("Campaigns", "🗳", NewsItem("Axios", "Sample campaign headline", "https://example.com", "Two-sentence summary would appear here.")),
        TopStory("Politics & Money", "💰", NewsItem("The Hill", "Sample fundraising headline", "https://example.com", "Two-sentence summary would appear here.")),
        TopStory("Public Affairs", "🌎", NewsItem("Roll Call", "Sample lobbying headline", "https://example.com", "Two-sentence summary would appear here.")),
    ]
    jobs = [
        JobPosting("Communications Director", "Morning Consult", "Washington, DC", "https://www.thepolly.co/jobs/sample-1", dt.date.today()),
        JobPosting("Deputy Political Director", "Campaign", "Arizona", "https://www.thepolly.co/jobs/sample-2", dt.date.today()),
        JobPosting("Digital Fundraising Manager", None, "Remote", "https://www.thepolly.co/jobs/sample-3", dt.date.today()),
        JobPosting("Government Relations Manager", None, "Austin", "https://www.thepolly.co/jobs/sample-4", dt.date.today()),
    ]
    return pulse, stories, jobs


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate The Polly Brief")
    parser.add_argument("--sample", action="store_true", help="Use sample data instead of live scraping")
    parser.add_argument("--out", default="polly_brief.html", help="Output HTML file path")
    parser.add_argument("--headlines-per-outlet", type=int, default=10)
    parser.add_argument("--quote", default=None, help="Quote of the Day
