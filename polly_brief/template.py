from __future__ import annotations
import datetime as dt
import html
from typing import Optional
from jobs_snapshot import HiringPulse, JobPosting
from news_snapshot import TopStory
import styles as s

ELECTION_DAY = dt.date(2026, 11, 3)

# If you have a real logo, base64-encode the PNG (e.g. `base64 -i logo.png`)
# and paste the resulting string here. Until then this stays empty and the
# header falls back to text-only -- which is intentional, since rendering
# an <img> with an empty/invalid data URI just shows a broken-image icon
# in every subscriber's inbox.
LOGO_BASE64 = ""


def _esc(text):
    """HTML-escape text for safe rendering."""
    return html.escape(text or '')


def _topic_color(section: str) -> str:
    """Get the accent color for a topic section."""
    return s.TOPIC_COLORS.get(section, s.ACCENT)


def _days_until_election(today=None) -> int:
    """Calculate days remaining until election day."""
    today = today or dt.date.today()
    return max((ELECTION_DAY - today).days, 0)


def _divider() -> str:
    """Render a horizontal divider row."""
    return (f'<tr><td style="padding:0 40px;">'
            f'<div style="{s.divider_style()}"></div>'
            f'</td></tr>')


def _section_heading(emoji: str, title: str, color: str = None) -> str:
    """Render a section heading with emoji."""
    color = color or s.INK
    heading_style = s.section_heading_style(color)
    return (f'<div style="{heading_style}">'
            f'{emoji} {_esc(title)}</div>')


def _list_row(text: str) -> str:
    """Render a single list item row."""
    return (f'<tr><td style="{s.list_row_style()}">'
            f'{_esc(text)}</td></tr>')


def _stat_block(number: str, label: str, url: str = None) -> str:
    """Render an enhanced stat block (Active Jobs, New Today, etc.)."""
    open_tag = (f'<a href="{url}" target="_blank" rel="noopener noreferrer" '
                f'style="text-decoration:none;">') if url else '<div>'
    close_tag = '</a>' if url else '</div>'

    return (f'<td style="padding-right: 16px;">'
            f'{open_tag}'
            f'<div style="{s.stat_block_style(s.ACCENT_LIGHT)}">'
            f'<div style="{s.stat_number_style()}">{_esc(number)}</div>'
            f'<div style="{s.stat_label_style()}">{_esc(label)}</div>'
            f'</div>'
            f'{close_tag}</td>')


def _story_block(story: TopStory) -> str:
    """Render a news story block with topic color."""
    color =
