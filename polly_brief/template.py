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
    a = '<tr><td style="padding:0 40px;">'
    b = '<div style="border-top:1px solid ' + HAIRLINE + '; margin:28px 0;"></div>'
    c = '</td></tr>'
    return a + b + c

def _section_heading(emoji, title):
    a = '<div style="font-size:15px; font-weight:700; color:' + INK + '; margin-bottom:16px;">'
    return a + emoji + ' ' + _esc(title) + '</div>'

def _list_row(text):
    a = '<tr><td style="padding:3px 0; font-size:14px; color:' + INK + ';">'
    return a + _esc(text) + '</td></tr>'

def _stat_block(number, label):
    a = '<td style="padding-right:32px;">'
    b = '<div style="font-size:30px; font-weight:700; color:' + INK + '; letter-spacing:-0.5px;">'
    c = number + '</div>'
    d = '<div style="font-size:11px; color:' + MUTED + '; text-transform:uppercase; letter-spacing:0.6px; margin-top:2px;">'
    e = _esc(label) + '</div></td>'
    return a + b + c + d + e

def _story_block(story):
    heading = _section_heading(story.emoji, story.section)
    if not story.item:
        a = '<tr><td style="padding-bottom:6px;">' + heading
        b = '<div style="font-size:13px; color:' + MUTED + '; font-style:italic;">'
        c = 'No story matched this section today.</div></td></tr>'
        return a + b + c
    item = story.item
    summary_html = ''
    if item.summary:
        s1 = '<div style="font-size:14px; color:' + MUTED + '; line-height:1.5; margin:6px 0 10px 0;">'
        summary_html = s1 + _esc(item.summary) + '</div>'
    a = '<tr><td style="padding-bottom:6px;">' + heading
    b = '<div style="font-size:15px; font-weight:600; color:' + INK + '; line-height:1.4;">'
    c = _esc(item.title) + '</div>' + summary_html
    d = '<a href="' + _esc(item.url) + '" style="font-size:13px; font-weight:600; color:' + ACCENT + '; text-decoration:none;">'
    e = 'Read More &rarr;</a></td></tr>'
    return a + b + c + d + e

def _job_block(job):
    location = _esc(job.location) if job.location else ''
    company = _esc(job.company)
    parts = [p for p in [company, location] if p]
    meta = ' &middot; '.join(parts)
    a = '<tr><td style="padding-bottom:6px;">'
    b = '<a href="' + _esc(job.url) + '" style="font-size:15px; font-weight:600; color:' + INK + '; text-decoration:none;">'
    c = _esc(job.title) + '</a>'
    d = '<div style="font-size:13px; color:' + MUTED
