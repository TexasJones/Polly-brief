from __future__ import annotations
import datetime as dt
import html
from typing import Optional
from jobs_snapshot import HiringPulse, JobPosting
from news_snapshot import TopStory

INK = '#161616'
MUTED = '#767676'
ACCENT = '#2B5A4D'
ACCENT_LIGHT = '#E4EDE9'
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

def _stat_block(number, label, url=None):
    a = '<td style="padding-right:12px;">'
    open_tag = '<a href="' + url + '" target="_blank" rel="noopener noreferrer" style="text-decoration:none;">' if url else '<div>'
    close_tag = '</a>' if url else '</div>'
    b = open_tag + '<div style="background-color:' + ACCENT_LIGHT + '; border-radius:10px; padding:16px 20px;">'
    c = '<div style="font-size:30px; font-weight:800; color:' + ACCENT + '; letter-spacing:-0.5px;">'
    d = number + '</div>'
    e = '<div style="font-size:11px; color:' + MUTED + '; text-transform:uppercase; letter-spacing:0.6px; margin-top:2px;">'
    f = _esc(label) + '</div></div>' + close_tag + '</td>'
    return a + b + c + d + e + f

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
    d = '<a href="' + _esc(item.url) + '" target="_blank" rel="noopener noreferrer" style="font-size:13px; font-weight:700; color:' + ACCENT + '; text-decoration:none;">'
    e = 'Read More &rarr;</a></td></tr>'
    return a + b + c + d + e

def _job_block(job):
    location = _esc(job.location) if job.location else ''
    company = _esc(job.company)
    parts = [p for p in [company, location] if p]
    meta = ' &middot; '.join(parts)
    a = '<tr><td style="padding-bottom:10px;">'
    b = '<div style="background-color:' + BG + '; border-radius:10px; padding:14px 18px;">'
    c = '<a href="' + _esc(job.url) + '" target="_blank" rel="noopener noreferrer" style="font-size:15px; font-weight:700; color:' + ACCENT + '; text-decoration:none;">'
    d = _esc(job.title) + '</a>'
    e = '<div style="font-size:13px; color:' + MUTED + '; margin-top:4px;">' + meta + '</div></div></td></tr>'
    return a + b + c + d + e

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
        job_rows += _job_block(j)
    if not job_rows:
        job_rows = '<tr><td style="font-size:13px; color:' + MUTED + ';">No featured jobs today.</td></tr>'

    days_left = _days_until_election(today)

    quote_section = ''
    if quote_text:
        attribution = ''
        if quote_source:
            a1 = '<div style="font-size:13px; color:' + MUTED + '; margin-top:8px;">'
            attribution = a1 + '&mdash; ' + _esc(quote_source) + '</div>'
        qh = _section_heading('\U0001F4AC', 'Quote of the Day')
        q1 = _divider() + '<tr><td style="padding:0 40px;">' + qh
        q2 = '<div style="font-size:16px; color:' + INK + '; font-style:italic; line-height:1.5;">'
        q3 = '&ldquo;' + _esc(quote_text) + '&rdquo;</div>' + attribution + '</td></tr>'
        quote_section = q1 + q2 + q3

    parts = []
    parts.append('<!DOCTYPE html><html><head>')
    parts.append('<meta charset="utf-8">')
    parts.append('<meta name="viewport" content="width=device-width, initial-scale=1.0">')
    parts.append('<title>The Polly Brief</title></head>')
    parts.append('<body style="margin:0; padding:0; background-color:' + BG + '; font-family:sans-serif;">')
    parts.append('<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:' + BG + '; padding:32px 0;">')
    parts.append('<tr><td align="center">')
    parts.append('<table role="presentation" width="600" cellpadding="0" cellspacing="0" style="background-color:' + CARD + '; border-radius:12px; overflow:hidden;">')
    parts.append('<tr><td style="background-color:' + ACCENT + '; height:6px; line-height:6px; font-size:0;">&nbsp;</td></tr>')
    parts.append('<tr><td style="padding:36px 40px 24px 40px;">')
    parts.append('<div style="font-size:20px; font-weight:700; color:' + INK + '; letter-spacing:-0.3px;">The Polly Brief</div>')
    parts.append('<div style="font-size:13px; color:' + MUTED + '; margin-top:4px;">' + _esc(date_label) + '</div>')
    parts.append('</td></tr>')
    parts.append(_divider())
    parts.append('<tr><td style="padding:0 40px;">')
    parts.append(_section_heading('\U0001F4CA', 'Polly Hiring Pulse'))
    parts.append('<table role="presentation" cellpadding="0" cellspacing="0" style="margin-bottom:20px;"><tr>')
    parts.append(_stat_block(f'{pulse.total_active:,}', 'Active Jobs', url='https://jobs.thepolly.co/jobs'))
    parts.append(_stat_block(str(pulse.new_today), 'New Today'))
    parts.append('</tr></table>')
    parts.append('<table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>')
    parts.append('<td width="50%" valign="top" style="padding-right:16px;">')
    parts.append('<div style="font-size:11px; font-weight:700; color:' + MUTED + '; text-transform:uppercase;">Top Hiring Categories</div>')
    parts.append('<table role="presentation" cellpadding="0" cellspacing="0">' + category_rows + '</table></td>')
    parts.append('<td width="50%" valign="top">')
    parts.append('<div style="font-size:11px; font-weight:700; color:' + MUTED + '; text-transform:uppercase;">Top Hiring Organizations</div>')
    parts.append('<table role="presentation" cellpadding="0" cellspacing="0">' + employer_rows + '</table></td>')
    parts.append('</tr></table></td></tr>')
    parts.append(_divider())
    parts.append('<tr><td style="padding:0 40px;">')
    parts.append('<div style="font-size:15px; font-weight:700; color:' + INK + '; margin-bottom:20px;">\U0001F4F0 Top Stories</div>')
    parts.append('<table role="presentation" width="100%" cellpadding="0" cellspacing="0">' + story_rows + '</table>')
    parts.append('</td></tr>')
    parts.append(_divider())
    parts.append('<tr><td style="padding:0 40px;">')
    parts.append(_section_heading('\U0001F525', 'Jobs Worth Looking At'))
    parts.append('<table role="presentation" width="100%" cellpadding="0" cellspacing="0">' + job_rows + '</table>')
    parts.append('</td></tr>')
    parts.append(_divider())
    parts.append('<tr><td style="padding:0 40px;">')
    parts.append('<div style="background-color:' + INK + '; border-radius:10px; padding:24px; text-align:center;">')
    parts.append(_section_heading('\U0001F4C5', 'Election Countdown').replace(INK, '#FFFFFF').replace(MUTED, '#CCCCCC'))
    parts.append('<div style="font-size:32px; font-weight:800; color:#FFFFFF;">' + str(days_left) + '</div>')
    parts.append('<div style="font-size:12px; color:#CCCCCC; text-transform:uppercase; letter-spacing:0.6px;">Days Until Election Day</div>')
    parts.append('</div></td></tr>')
    parts.append(quote_section)
    parts.append('<tr><td style="padding:36px 40px 40px 40px;">')
    parts.append('<div style="border-top:1px solid ' + HAIRLINE + '; padding-top:20px; text-align:center;">')
    parts.append('<div style="font-size:13px; font-weight:600; color:' + INK + ';">Powered by Pollyai</div>')
    parts.append('<div style="font-size:12px; color:' + MUTED + '; margin-top:2px;">The Talent Marketplace for Politics &amp; Public Affairs</div>')
    parts.append('</div></td></tr>')
    parts.append('</table></td></tr></table></body></html>')
    return ''.join(parts)
