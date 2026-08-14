from __future__ import annotations
import datetime as dt
import html
import inspect
from typing import Optional
from jobs_snapshot import HiringPulse, JobPosting
from news_snapshot import TopStory
import styles as s

ELECTION_DAY = dt.date(2026, 11, 3)

# Base64-encoded parrot silhouette favicon (64x64), used as the small
# header mark next to "The Polly Brief" wordmark. If you ever want to
# swap the logo, base64-encode the new PNG (e.g. `base64 -w 0 logo.png`)
# and replace the string below.
LOGO_BASE64 = "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"


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
    """Render a plain (non-badge) section heading with emoji."""
    color = color or s.INK
    heading_style = s.section_heading_style(color)
    return (f'<div style="{heading_style}">'
            f'{emoji} {_esc(title)}</div>')


def _topic_badge(emoji: str, title: str, color: str) -> str:
    """Render a solid-color pill badge for a topic label."""
    return f'<span style="{s.badge_style(color)}">{emoji} {_esc(title)}</span>'


def _list_row(text: str) -> str:
    """Render a single list item row."""
    return (f'<tr><td style="{s.list_row_style()}">'
            f'{_esc(text)}</td></tr>')


def _stat_block(number: str, label: str, color: str, url: str = None) -> str:
    """Render a bold, solid-color stat block (Active Jobs, New Today, etc.)."""
    open_tag = (f'<a href="{url}" target="_blank" rel="noopener noreferrer" '
                f'style="text-decoration:none;">') if url else '<div>'
    close_tag = '</a>' if url else '</div>'

    return (f'<td style="padding-right: 16px;">'
            f'{open_tag}'
            f'<div style="{s.stat_block_style(color)}">'
            f'<div style="{s.stat_number_style()}">{_esc(number)}</div>'
            f'<div style="{s.stat_label_style()}">{_esc(label)}</div>'
            f'</div>'
            f'{close_tag}</td>')


def _story_block(story: TopStory) -> str:
    """Render a news story block with a topic-colored badge."""
    color = _topic_color(story.section)
    badge_row = f'<div style="margin-bottom: 10px">{_topic_badge(story.emoji, story.section, color)}</div>'

    if not story.item:
        return (f'<tr><td style="padding-bottom: 12px;">{badge_row}'
                f'<div style="{s.muted_text_style()}; font-style: italic;">'
                f'No story matched this section today.</div></td></tr>')

    item = story.item
    summary_html = ''
    if item.summary:
        summary_html = f'<div style="{s.summary_text_style()}">{_esc(item.summary)}</div>'

    headline_style = s.headline_style()

    return (f'<tr><td style="padding-bottom: 12px;">{badge_row}'
            f'<div style="{headline_style}">{_esc(item.title)}</div>'
            f'{summary_html}'
            f'<a href="{_esc(item.url)}" target="_blank" rel="noopener noreferrer" '
            f'style="{s.link_style(color)}; font-size: 13px;">'
            f'Read More &rarr;</a></td></tr>')


def _call_style_fn(func, *args, **kwargs):
    """Safely call a style function whether or not it expects parameters."""
    sig = inspect.signature(func)
    params = sig.parameters
    if not params:
        return func()
    
    # Pass positional args if defined
    bound_args = []
    for i, p in enumerate(params.values()):
        if p.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD):
            if i < len(args):
                bound_args.append(args[i])
            elif p.name in kwargs:
                bound_args.append(kwargs[p.name])
            elif p.default is not inspect.Parameter.empty:
                bound_args.append(p.default)

    return func(*bound_args)


def _featured_job_block(job: JobPosting) -> str:
    """Render a featured job card."""
    location = _esc(job.location) if job.location else ''
    company = _esc(job.company)

    job_color = s.TOPIC_COLORS.get(job.category, s.ACCENT) if job.category else s.ACCENT

    meta_parts = [p for p in [company, location] if p]
    meta = ' &middot; '.join(meta_parts)

    # Safely call style functions to prevent argument mismatch issues
    card_style = _call_style_fn(s.featured_job_card_style, job_color)
    muted_style = _call_style_fn(s.muted_text_style, size="13px")

    return (f'<tr><td style="padding-bottom: 14px;">'
            f'<div style="{card_style}">'
            f'<a href="{_esc(job.url)}" target="_blank" rel="noopener noreferrer" '
            f'style="{s.link_style(job_color)}; font-size: 15px">'
            f'{_esc(job.title)}</a>'
            f'<div style="{muted_style}; margin-top: 6px">{meta}</div>'
            f'</div></td></tr>')


def _pick_top_highlight(top_stories: list[TopStory]) -> Optional[TopStory]:
    """Find the first story with content to feature at the top."""
    for story in top_stories:
        if story.item:
            return story
    return None


def _top_highlight_block(top_stories: list[TopStory]) -> str:
    """Render a prominent featured story box with a colored topic badge."""
    story = _pick_top_highlight(top_stories)
    if not story:
        return ''

    color = _topic_color(story.section)
    item = story.item

    headline_style = s.headline_style(size='19px')
    highlight_style = s.highlight_block_style(color, color)
    link_style = s.link_style(color)

    return (
        f'<tr><td style="padding: 0 40px 32px 40px;">'
        f'<div style="{highlight_style}">'
        f'<div style="margin-bottom: 12px">'
        f'{_topic_badge(story.emoji, story.section, color)} '
        f'<span style="font-size: 11px; font-weight: 700; color: {s.MUTED}; '
        f'text-transform: uppercase; letter-spacing: 0.6px;">&middot; Today&rsquo;s Top Story</span>'
        f'</div>'
        f'<div style="{headline_style}">{_esc(item.title)}</div>'
        f'<a href="{_esc(item.url)}" target="_blank" rel="noopener noreferrer" '
        f'style="{link_style}; font-size: 13px; margin-top: 12px; display: inline-block">'
        f'Read More &rarr;</a>'
        f'</div></td></tr>'
    )


def _brand_header() -> str:
    """Render the header logo + wordmark row."""
    if LOGO_BASE64:
        logo_cell = (
            f'<td style="padding-right: 12px; vertical-align: middle">'
            f'<div style="background-color: {s.ACCENT_LIGHT}; border-radius: 10px; '
            f'padding: 6px; display: inline-block; line-height: 0;">'
            f'<img src="data:image/png;base64,{LOGO_BASE64}" width="28" height="28" '
            f'alt="Polly" style="display: block"></div></td>'
        )
    else:
        logo_cell = ''

    return (
        '<table role="presentation" cellpadding="0" cellspacing="0"><tr>'
        f'{logo_cell}'
        f'<td style="vertical-align: middle"><div style="font-size: 24px; font-weight: 900; '
        f'color: {s.INK}; letter-spacing: -0.5px; font-family: {s.HEADLINE_FONT};">'
        f'The Polly Brief</div></td>'
        '</tr></table>'
    )


def render_brief(pulse: HiringPulse, top_stories: list[TopStory], featured_jobs: list[JobPosting],
                 quote_text: str = None, quote_source: str = None, today: dt.date = None) -> str:
    """Generate the complete HTML email for The Polly Brief."""
    today = today or dt.date.today()
    try:
        date_label = today.strftime('%A, %B %-d, %Y')
    except ValueError:
        date_label = today.strftime('%A, %B %d, %Y').replace(' 0', ' ')

    category_rows = ''.join(_list_row(name) for name, _c in pulse.top_categories)
    if not category_rows:
        category_rows = f'<tr><td style="{s.muted_text_style()};">No category data available.</td></tr>'

    employer_rows = ''.join(_list_row(name) for name, _c in pulse.top_employers)
    if not employer_rows:
        employer_rows = f'<tr><td style="{s.muted_text_style()};">No employer data available.</td></tr>'

    story_rows = ''
    for i, st in enumerate(top_stories):
        if i > 0:
            story_rows += _divider()
        story_rows += _story_block(st)

    job_rows = ''
    for job in featured_jobs:
        job_rows += _featured_job_block(job)
    if not job_rows:
        job_rows = f'<tr><td style="{s.muted_text_style()};">No featured jobs today.</td></tr>'

    quote_section = ''
    if quote_text:
        attribution = ''
        if quote_source:
            attribution = f'<div style="{s.muted_text_style()}; margin-top: 10px">&mdash; {_esc(quote_source)}</div>'
        headline_16 = s.headline_style(size='16px')
        quote_section = (
            _divider() +
            f'<tr><td style="padding: 0 40px">'
            f'{_section_heading("💬", "Quote of the Day")}'
            f'<div style="{headline_16}; font-style: italic">'
            f'&ldquo;{_esc(quote_text)}&rdquo;</div>{attribution}</td></tr>'
        )

    days_left = _days_until_election(today)

    top_bar_gradient = (
        f'{s.TOPIC_COLORS["Campaigns"]}, {s.TOPIC_COLORS["Media"]}, {s.TOPIC_COLORS["AI+Policy"]}, '
        f'{s.TOPIC_COLORS["Energy"]}, {s.TOPIC_COLORS["Finance"]}, {s.TOPIC_COLORS["Legislative"]}'
    )

    parts = [
        '<!DOCTYPE html><html><head>',
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">',
        '<title>The Polly Brief</title></head>',
        f'<body style="margin: 0; padding: 0; background-color: {s.BG}; font-family: {s.BODY_FONT};">',
        '<div style="display: none; max-height: 0; overflow: hidden; mso-hide: all">',
    ]

    top_story = _pick_top_highlight(top_stories)
    preheader = (top_story.item.title if top_story else
                 f'{pulse.total_active} active jobs in politics & public affairs')
    parts.append(_esc(preheader))
    parts.append('&nbsp;' * 40)
    parts.append('</div>')

    parts.extend([
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color: {s.BG}; padding: 32px 0">',
        '<tr><td align="center">',
        f'<table role="presentation" width="600" cellpadding="0" cellspacing="0" style="background-color: {s.CARD}; border-radius: 14px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.08)">',
        f'<tr><td style="background-color: {s.TOPIC_COLORS["Campaigns"]}; background: linear-gradient(90deg, {top_bar_gradient}); height: 7px; line-height: 7px; font-size: 0">&nbsp;</td></tr>',
        '<tr><td style="padding: 36px 40px 24px 40px">',
        _brand_header(),
        f'<div style="font-size: 12px; color: {s.MUTED}; margin-top: 8px; letter-spacing: 0.3px">{_esc(date_label)}</div>',
        '</td></tr>',
        _top_highlight_block(top_stories),
        _divider(),
        '<tr><td style="padding: 0 40px">',
        f'{_section_heading("📊", "Polly Hiring Pulse")}',
        '<table role="presentation" cellpadding="0" cellspacing="0" style="margin-bottom: 24px"><tr>',
        _stat_block(f'{pulse.total_active:,}', 'Active Jobs', color=s.ACCENT, url='https://jobs.thepolly.co/jobs'),
        _stat_block(str(pulse.new_today), 'New Today', color=s.TOPIC_COLORS['Campaigns']),
        '</tr></table>',
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>',
        '<td width="50%" valign="top" style="padding-right: 20px">',
        f'<div style="font-size: 11px; font-weight: 700; color: {s.MUTED}; text-transform: uppercase; letter-spacing: 0.6px; margin-bottom: 12px">Top Hiring Categories</div>',
        f'<table role="presentation" cellpadding="0" cellspacing="0">{category_rows}</table></td>',
        '<td width="50%" valign="top">',
        f'<div style="font-size: 11px; font-weight: 700; color: {s.MUTED}; text-transform: uppercase; letter-spacing: 0.6px; margin-bottom: 12px">Top Hiring Organizations</div>',
        f'<table role="presentation" cellpadding="0" cellspacing="0">{employer_rows}</table></td>',
        '</tr></table></td></tr>',
        _divider(),
        '<tr><td style="padding: 0 40px">',
        f'<div style="{s.section_heading_style()}">📰 Top Stories</div>',
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0">{story_rows}</table>',
        '</td></tr>',
        _divider(),
        '<tr><td style="padding: 0 40px">',
        f'{_section_heading("🔥", "Jobs Worth Looking At")}',
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0">{job_rows}</table>',
        '</td></tr>',
        _divider(),
        '<tr><td style="padding: 0 40px">',
        f'<div style="background-color: {s.INK}; background: linear-gradient(135deg, {s.INK}, #2a2a2a); border-radius: 12px; padding: 28px; text-align: center">',
        f'{_section_heading("📅", "Election Countdown", color=s.WHITE)}',
        f'<div style="font-size: 48px; font-weight: 900; color: {s.WHITE}; font-family: {s.HEADLINE_FONT}; letter-spacing: -1px">{days_left}</div>',
        f'<div style="font-size: 12px; color: #BBBBBB; text-transform: uppercase; letter-spacing: 0.8px; margin-top: 8px">Days Until Election Day</div>',
        '</div></td></tr>',
        quote_section,
        '<tr><td style="padding: 28px 40px 16px 40px; text-align: center">',
        f'<a href="https://thepolly.co" target="_blank" rel="noopener noreferrer" style="{s.link_style(s.MUTED)}; font-size: 12px">Know someone job hunting in politics? Invite them to Polly →</a>',
        '</td></tr>',
        '<tr><td style="padding: 16px 40px 40px 40px">',
        f'<div style="border-top: 1px solid {s.HAIRLINE}; padding-top: 20px; text-align: center">',
        f'<div style="font-size: 12px; font-weight: 600; color: {s.INK};">Powered by Pollyai</div>',
        f'<div style="font-size: 11px; color: {s.MUTED}; margin-top: 4px">The Talent Marketplace for Politics &amp; Public Affairs</div>',
        '</div></td></tr>',
        '</table></td></tr></table></body></html>',
    ])

    return ''.join(parts)
