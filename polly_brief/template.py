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
    parts.append('<table role="presentation" cellpadding="0" cellspacing="0"><tr>')
    parts.append('<td style="padding-right:10px; vertical-align:middle;"><img src="data:image/png;base64,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" width="28" height="28" alt="Polly" style="display:block;"></td>')
    parts.append('<td style="vertical-align:middle;"><div style="font-size:20px; font-weight:700; color:' + INK + '; letter-spacing:-0.3px;">The Polly Brief</div></td>')
    parts.append('</tr></table>')
    parts.append('<div style="font-size:13px; color:' + MUTED + '; margin-top:6px;">' + _esc(date_label) + '</div>')
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
