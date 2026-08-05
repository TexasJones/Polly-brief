from __future__ import annotations
import datetime as dt
import html
from typing import Optional
from jobs_snapshot import HiringPulse, JobPosting
from news_snapshot import TopStory

INK = '#161616'
MUTED = '#767676'
ACCENT = '#2B5A4D'
HAIRLINE = '#E7E5E0'
BG = '#F4F3EF'
CARD = '#FFFFFF'
ELECTION_DAY = dt.date(2026, 11, 3)

def _esc(s):
    return html.escape(s or '')

def _days_until_election(today=None):
    today = today or dt.date.today()
    return max((ELECTION_DAY - today).days, 0)

def _divider():
    return '<tr><td style="padding:0 40px;"><div style="border-top:1px solid ' + HAIRLINE + '; margin:28px 0;"></div></td></tr>'

def _section_heading(emoji, title):
    return '<div style="font-size:15px; font-weight:700; color:' + INK + '; margin-bottom:16px;">' + emoji + ' ' + _esc(title) + '</div>'

def _list_row(text):
    return '<tr><td style="padding:3px 0; font-size:14px; color:' + INK + ';">' + _esc(text) + '</td></tr>'

def _stat_block(number, label):
    return '<td style="padding-right:32px;"><div style="font-size:30px; font-weight:700; color:' + INK + '; letter-spacing:-0.5px;">' + number + '</div><div style="font-size:11px; color:' + MUTED + '; text-transform:uppercase; letter-spacing:0.6px; margin-top:2px;">' + _esc(label) + '</div></td>'

def _story_block(story):
    if not story.item:
        return '<tr><td style="padding-bottom:6px;">' + _section_heading(story.emoji, story.section) + '<div style="font-size:13px; color:' + MUTED + '; font-style:italic;">No story matched this section today.</div></td></tr>'
    item = story.item
    summary_html = ''
    if item.summary:
        summary_html = '<div style="font-size:14px; color:' + MUTED + '; line-height:1.5; margin:6px 0 10px 0;">' + _esc(item.summary) + '</div>'
    return '<tr><td style="padding-bottom:6px;">' + _section_heading(story.emoji, story.section) + '<div style="font-size:15px; font-weight:600; color:' + INK + '; line-height:1.4;">' + _esc(item.title) + '</div>' + summary_html + '<a href="' + _esc(item.url) + '" style="font-size:13px; font-weight:600; color:' + ACCENT + '; text-decoration:none;">Read More &rarr;</a></td></tr>'

def _job_block(job):
    location = _esc(job.location) if job.location else ''
    company = _esc(job.company)
    parts = [p for p in [company, location] if p]
    meta = ' &middot; '.join(parts)
    return '<tr><td style="padding-bottom:6px;"><a href="' + _esc(job.url) + '" style="font-size:15px; font-weight:600; color:' + INK + '; text-decoration:none;">' + _esc(job.title) + '</a><div style="font-size:13px; color:' + MUTED + '; margin-top:2px;">' + meta + '</div></td></tr>'

def render_brief(pulse, top_stories, featured_jobs, quote_text=None, quote_source=None, today=None):
    today = today or dt.date.today()
    date_label = today.strftime('%A, %B %-d, %Y')

    category_rows = ''.join(_list_row(name) for name, _c in pulse.top_categories)
    if not category_rows:
        category_rows = '<tr><td style="font-size:13px; color:' + MUTED + ';">No category data available.</td></tr>'

    employer_rows = ''.join(_list_row(name) for name, _c in pulse.top_employers)
    if not employer_rows:
        employer_rows = '<tr><td style="font-size:13px; color:' + MUTED + ';">No employer data available.</td></tr>'

    story_rows = ''
    for i, s in enumerate(top_stories):
        if i > 0:
            story_rows += _divider()
        story_rows += _story_block(s)

    job_rows = ''
    for i, j in enumerate(featured_jobs):
        if i > 0:
            job_rows += _divider()
        job_rows += _job_block(j)
    if not job_rows:
        job_rows = '<tr><td style="font-size:13px; color:' + MUTED + ';">No featured jobs today.</td></tr>'

    days_left = _days_until_election(today)

    quote_section = ''
    if quote_text:
        attribution = ''
        if quote_source:
            attribution = '<div style="font-size:13px; color:' + MUTED + '; margin-top:8px;">&mdash; ' + _esc(quote_source) + '</div>'
        quote_section = _divider() + '<tr><td style="padding:0 40px;">' + _section_heading('\U0001F4AC', 'Quote of the Day') + '<div style="font-size:16px; color:' + INK + '; font-style:italic; line-height:1.5;">&ldquo;' + _esc(quote_text) + '&rdquo;</div>' + attribution + '</td></tr>'

    html_out = '<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>The Polly
