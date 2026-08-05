from __future__ import annotations
import argparse
import datetime as dt
import sys
from jobs_snapshot import HiringPulse, JobPosting, get_hiring_pulse
from news_snapshot import NewsItem, TopStory, get_top_stories
from template import render_brief

def _sample_data():
    pulse = HiringPulse(total_active=1247, new_today=58,
        top_categories=[('Campaigns', 0), ('Communications', 0), ('Public Affairs', 0), ('Government Relations', 0), ('Digital', 0)],
        top_employers=[('Morning Consult', 0), ('FP1 Strategies', 0), ('Public Affairs Council', 0), ('Senate Offices', 0), ('Movement Labs', 0)])
    stories = [
        TopStory('Congress', chr(0x1F3DB), NewsItem('Politico', 'Sample Congress headline', 'https://example.com', 'Two sentence summary would appear here.')),
        TopStory('Campaigns', chr(0x1F5F3), NewsItem('Axios', 'Sample campaign headline', 'https://example.com', 'Two sentence summary would appear here.')),
    ]
    jobs = [
        JobPosting('Communications Director', 'Morning Consult', 'Washington, DC', 'https://www.thepolly.co/jobs/sample-1', dt.date.today()),
        JobPosting('Deputy Political Director', 'Campaign', 'Arizona', 'https://www.thepolly.co/jobs/sample-2', dt.date.today()),
    ]
    return pulse, stories, jobs

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--sample', action='store_true')
    parser.add_argument('--out', default='polly_brief.html')
    parser.add_argument('--headlines-per-outlet', type=int, default=10)
    parser.add_argument('--quote', default=None)
    parser.add_argument('--quote-source', default=None)
    args = parser.parse_args()

    if args.sample:
        pulse, stories, jobs = _sample_data()
        quote = args.quote or 'Sample quote'
        quote_source = args.quote_source or 'Sample Attribution'
    else:
        pulse = get_hiring_pulse()
        jobs = pulse.featured
        stories = get_top_stories(per_outlet=args.headlines_per_outlet)
        quote,
