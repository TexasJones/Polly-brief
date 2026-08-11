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
        # keep total subject length reasonable for inbox display
        max_headline_len = 70
        if len(top_headline) > max_headline_len:
            top_headline = top_headline[:max_headline_len].rsplit(' ', 1)[0] + '...'
        return f'The Polly Brief: {top_headline}'
    return f'The Polly Brief -- {date_str}'

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--sample', action='store_true')
    parser.add_argument('--out', default='polly_brief.html')
    parser.add_argument('--subject-out', default='polly_brief_subject.txt')
    parser.add_argument('--headlines-per-outlet', type=int, default=10)
    parser.add_argument('--quote', default=None)
    parser.add_argument('--quote-source', default=None)
    args = parser.parse_args()

    today = dt.date.today()

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
        stories = get_top_stories(per_outlet=args.headlines_per_outlet)
        for s in stories:
            status = s.item.title if s.item else '(none found)'
            print(' -', s.section, ':', status)
        quote, quote_source = args.quote, args.quote_source

    html_out = render_brief(pulse, stories, jobs, quote_text=quote, quote_source=quote_source, today=today)
    with open(args.out, 'w', encoding='utf-8') as f:
        f.write(html_out)
    print('Wrote', args.out)

    subject = _build_subject(pulse, stories, today)
    with open(args.subject_out, 'w', encoding='utf-8') as f:
        f.write(subject)
    print('Subject:', subject)
    print('Wrote', args.subject_out)

    return 0

if __name__ == '__main__':
    sys.exit(main())
