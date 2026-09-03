from __future__ import annotations
import argparse
import datetime as dt
import sys
from pathlib import Path
from zoneinfo import ZoneInfo
from jobs_snapshot import HiringPulse, JobPosting, get_hiring_pulse
from news_snapshot import NewsItem, TopStory, get_top_stories
from template import render_brief

# GitHub Pages base for this repo (Settings -> Pages: main branch, /docs
# folder). Dated copies of the brief get published to
# docs/briefs/{YYYY-MM-DD}.html, which resolves under this base -- see
# _publish_to_pages() below. If the repo, org, or Pages folder ever change,
# only this constant needs updating.
PAGES_BASE_URL = "https://texasjones.github.io/Polly-brief"


def _sample_data():
    pulse = HiringPulse(total_active=1247, new_today=58,
        top_categories=[('Campaigns', 0), ('Communications', 0), ('Public Affairs', 0), ('Government Relations', 0), ('Digital', 0)],
        top_employers=[('Morning Consult', 0), ('FP1 Strategies', 0), ('Public Affairs Council', 0), ('Senate Offices', 0), ('Movement Labs', 0)])
    stories = [
        TopStory('Congress', chr(0x1F3DB), NewsItem('Politico', 'Sample Congress headline', 'https://example.com', '')),
        TopStory('Campaigns', chr(0x1F5F3), NewsItem('Axios', 'Sample campaign headline', 'https://example.com', '')),
    ]
    jobs = [
        JobPosting('Communications Director', 'Morning Consult', 'Washington, DC', 'https://www.thepolly.co/jobs/sample-1', dt.date.today()),
        JobPosting('Deputy Political Director', 'Campaign', 'Arizona', 'https://www.thepolly.co/jobs/sample-2', dt.date.today()),
    ]
    return pulse, stories, jobs


def _build_subject(pulse, stories, today):
    date_str = today.strftime('%B %-d')
    top_headline = None
    for s in stories:
        if s.item:
            top_headline = s.item.title
            break
    if top_headline:
        # Keep total subject length under ~60 chars -- most inbox lists
        # (Gmail especially) truncate well before 70-90 chars, which was
        # cutting headlines off mid-word.
        prefix = 'The Polly Brief: '
        max_headline_len = 60 - len(prefix)
        if len(top_headline) > max_headline_len:
            top_headline = top_headline[:max_headline_len].rsplit(' ', 1)[0] + '...'
        return prefix + top_headline
    return f'The Polly Brief -- {date_str}'


def _publish_to_pages(html_out: str, today: dt.date) -> str:
    """
    Writes a dated copy of the rendered brief into docs/briefs/, the folder
    GitHub Pages is configured to serve (Settings -> Pages: main / /docs).
    Returns the public URL for that copy, for use as the "View in browser"
    link in the email header.

    Path is resolved from this file's own location, not the current working
    directory -- the same reasoning jobs_snapshot.py uses for
    SNAPSHOT_PATH: cwd-relative paths silently break depending on whether
    the workflow invokes this script from the repo root or from inside
    polly_brief/, and this avoids that class of bug. This script lives at
    polly_brief/generate_brief.py, so docs/ (a sibling of polly_brief/) is
    one level up from this file's parent.
    """
    docs_dir = Path(__file__).resolve().parent.parent / "docs" / "briefs"
    docs_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{today.isoformat()}.html"
    (docs_dir / filename).write_text(html_out, encoding="utf-8")

    return f"{PAGES_BASE_URL}/briefs/{filename}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--sample', action='store_true')
    parser.add_argument('--out', default='polly_brief.html')
    parser.add_argument('--subject-out', default='polly_brief_subject.txt')
    parser.add_argument('--headlines-per-outlet', type=int, default=10)
    parser.add_argument('--quote', default=None)
    parser.add_argument('--quote-source', default=None)
    args = parser.parse_args()
    
    # Get today's date in America/New_York timezone, not UTC
    tz_eastern = ZoneInfo('America/New_York')
    today = dt.datetime.now(tz_eastern).date()
    
    if args.sample:
        pulse, stories, jobs = _sample_data()
        quote = args.quote or 'Sample quote'
        quote_source = args.quote_source or 'Sample Attribution'
    else:
        print('Reading live job feed...')
        pulse = get_hiring_pulse()
        print('Active jobs:', pulse.total_active, 'New today:', pulse.new_today)
        jobs = pulse.featured
        print('Fetching news...')
        stories = get_top_stories(per_outlet=args.headlines_per_outlet, today=today)
        for s in stories:
            status = s.item.title if s.item else '(none found)'
            print(' -', s.section, ':', status)
        quote, quote_source = args.quote, args.quote_source

    # The "View in browser" link needs the day's published URL before the
    # HTML itself is rendered (the URL is embedded in the header), but the
    # URL only depends on today's date -- not on the brief's content -- so
    # it can be built up front. Skipped for --sample runs so local test
    # output doesn't overwrite a real day's published copy and doesn't
    # link to a URL that was never actually published.
    view_url = None
    if not args.sample:
        filename = f"{today.isoformat()}.html"
        view_url = f"{PAGES_BASE_URL}/briefs/{filename}"

    html_out = render_brief(pulse, stories, jobs, quote_text=quote, quote_source=quote_source,
                             today=today, view_url=view_url)

    with open(args.out, 'w', encoding='utf-8') as f:
        f.write(html_out)
    print('Wrote', args.out)

    if not args.sample:
        published_url = _publish_to_pages(html_out, today)
        print('Published to', published_url)

    subject = _build_subject(pulse, stories, today)
    with open(args.subject_out, 'w', encoding='utf-8') as f:
        f.write(subject)
    print('Subject:', subject)
    print('Wrote', args.subject_out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
