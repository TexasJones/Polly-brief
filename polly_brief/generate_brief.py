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
        TopStory("Congress", "🏛", NewsItem("Politico", "Sample Congress headline",
