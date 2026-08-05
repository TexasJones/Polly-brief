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

def _story_
