from __future__ import annotations
import datetime as dt
import html
import inspect
from typing import Optional
from jobs_snapshot import HiringPulse, JobPosting
from news_snapshot import TopStory
import styles as s

ELECTION_DAY = dt.date(2026, 11, 3)


def _esc(text: str) -> str:
    """HTML-escape text for safe rendering."""
    return html.escape(text or '')


def _c(name: str, default: str) -> str:
    """Safely fetch a constant from styles module without raising AttributeError."""
    return getattr(s, name, default)


def _topic_color(section: str) -> str:
    """Get the accent color for a topic section."""
    topic_colors = _c('TOPIC_COLORS', {})
    accent = _c('ACCENT', '#1E3A8A')
    if isinstance(topic_colors, dict):
        return topic_colors.get(section, accent)
    return accent


def _days_until_election(today: dt.date = None) -> int:
    """Calculate days remaining until election day."""
    today = today or dt.date.today()
    return max((ELECTION_DAY - today).days, 0)


def _style(name: str, *args, fallback: str = "", **kwargs) -> str:
    """Safely fetch and execute a style function from styles.py."""
    func = getattr(s, name, None)
    if func is None or not callable(func):
        return fallback

    try:
        sig = inspect.signature(func)
        params = sig.parameters
        if not params:
            return str(func())

        bound_args = []
        for i, p in enumerate(params.values()):
            if p.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD):
                if i < len(args):
                    bound_args.append(args[i])
                elif p.name in kwargs:
                    bound_args.append(kwargs[p.name])
                elif p.default is not inspect.Parameter.empty:
                    bound_args.append(p.default)

        return str(func(*bound_args))
    except Exception:
        try:
            return str(func(*args, **kwargs))
        except Exception:
            return fallback


def _divider() -> str:
    """Render a horizontal divider row."""
    hairline = _c('HAIRLINE', '#E2E8F0')
    divider_css = _style('divider_style', fallback=f"border-bottom: 1px solid {hairline}; margin: 24px 0;")
    return (f'<tr><td style="padding:0 40px;">'
            f'<div style="{divider_css}"></div>'
            f'</td></tr>')


def _section_heading(emoji: str, title: str, color: str = None) -> str:
    """Render a section heading."""
    ink = _c('INK', '#0F172A')
    color = color or ink
    heading_css = _style('section_heading_style', color, fallback=f"font-size: 18px; font-weight: 800; color: {color}; margin-bottom: 16px;")
    return (f'<div style="{heading_css}">'
            f'{emoji} {_esc(title)}</div>')


def _topic_badge(emoji: str, title: str, color: str) -> str:
    """Render a solid-color pill badge for a topic label."""
    badge_css = _style('badge_style', color, fallback=f"background-color: {color}; color: #ffffff; padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: 700; text-transform: uppercase; display: inline-block;")
    return f'<span style="{badge_css}">{emoji} {_esc(title)}</span>'


def _list_row(text: str) -> str:
    """Render a single list item row."""
    ink = _c('INK', '#1E293B')
    row_css = _style('list_row_style', fallback=f"padding: 5px 0; font-size: 14px; color: {ink}; font-weight: 500;")
    return (f'<tr><td style="{row_css}">'
            f'{_esc(text)}</td></tr>')


def _stat_block(number: str, label: str, bg_color: str = "#1E3A8A", url: str = None) -> str:
    """Render a high-contrast stat card with solid white text."""
    open_tag = (f'<a href="{url}" target="_blank" rel="noopener noreferrer" '
                f'style="text-decoration:none; display:block;">') if url else '<div style="display:block;">'
    close_tag = '</a>' if url else '</div>'

    return (f'<td width="50%" style="padding-right: 12px; vertical-align: top;">'
            f'{open_tag}'
            f'<div style="background-color: {bg_color}; border-radius: 10px; padding: 18px 16px; text-align: center; color: #FFFFFF;">'
            f'<div style="font-size: 32px; font-weight: 900; line-height: 1; color: #FFFFFF; font-family: Helvetica, Arial, sans-serif;">{_esc(number)}</div>'
            f'<div style="font-size: 11px; font-weight: 800; text-transform: uppercase; margin-top: 8px; letter-spacing: 0.8px; color: #FFFFFF; opacity: 0.95;">{_esc(label)}</div>'
            f'</div>'
            f'{close_tag}</td>')


def _story_block(story: TopStory) -> str:
    """Render a news story block with a topic-colored badge."""
    color = _topic_color(story.section)
    badge_row = f'<div style="margin-bottom: 10px">{_topic_badge(story.emoji, story.section, color)}</div>'

    muted = _c('MUTED', '#64748B')
    muted_css = _style('muted_text_style', fallback=f"font-size: 14px; color: {muted};")
    if not story.item:
        return (f'<tr><td style="padding-bottom: 12px;">{badge_row}'
                f'<div style="{muted_css}; font-style: italic;">'
                f'No story matched this section today.</div></td></tr>')

    item = story.item
    summary_html = ''
    if item.summary:
        summary_css = _style('summary_text_style', fallback=f"font-size: 14px; color: {muted}; margin: 6px 0 10px 0; line-height: 1.4;")
        summary_html = f'<div style="{summary_css}">{_esc(item.summary)}</div>'

    ink = _c('INK', '#0F172A')
    headline_css = _style('headline_style', fallback=f"font-size: 16px; font-weight: 700; color: {ink}; line-height: 1.3;")
    link_css = _style('link_style', color, fallback=f"color: {color}; text-decoration: none; font-weight: 700;")

    return (f'<tr><td style="padding-bottom: 16px;">{badge_row}'
            f'<div style="{headline_css}">{_esc(item.title)}</div>'
            f'{summary_html}'
            f'<a href="{_esc(item.url)}" target="_blank" rel="noopener noreferrer" '
            f'style="{link_css}; font-size: 13px;">'
            f'Read More &rarr;</a></td></tr>')


def _featured_job_block(job: JobPosting) -> str:
    """Render a featured job card."""
    location = _esc(job.location) if job.location else ''
    company = _esc(job.company)

    accent = _c('ACCENT', '#1E3A8A')
    topic_colors = _c('TOPIC_COLORS', {})
    job_color = topic_colors.get(job.category, accent) if (isinstance(topic_colors, dict) and job.category) else accent

    meta_parts = [p for p in [company, location] if p]
    meta = ' &middot; '.join(meta_parts)

    muted = _c('MUTED', '#64748B')

    return (f'<tr><td style="padding-bottom: 12px;">'
            f'<div style="border-left: 4px solid {job_color}; padding: 14px 18px; background-color: #F8FAFC; border-radius: 0 8px 8px 0;">'
            f'<a href="{_esc(job.url)}" target="_blank" rel="noopener noreferrer" '
            f'style="color: #0F172A; text-decoration: none; font-size: 15px; font-weight: 700;">'
            f'{_esc(job.title)}</a>'
            f'<div style="font-size: 13px; color: {muted}; margin-top: 4px; font-weight: 500;">{meta}</div>'
            f'</div></td></tr>')


def _pick_top_highlight(top_stories: list[TopStory]) -> Optional[TopStory]:
    """Find the first story with content to feature at the top."""
    for story in top_stories:
        if story.item:
            return story
    return None


def _top_highlight_block(top_stories: list[TopStory]) -> str:
    """Render a clean, high-contrast top story box."""
    story = _pick_top_highlight(top_stories)
    if not story:
        return ''

    color = _topic_color(story.section)
    item = story.item

    ink = _c('INK', '#0F172A')
    muted = _c('MUTED', '#64748B')

    return (
        f'<tr><td style="padding: 0 40px 24px 40px;">'
        f'<div style="border: 1px solid #E2E8F0; border-top: 4px solid {color}; padding: 20px; border-radius: 12px; background-color: #F8FAFC;">'
        f'<div style="margin-bottom: 12px">'
        f'{_topic_badge(story.emoji, story.section, color)} '
        f'<span style="font-size: 11px; font-weight: 700; color: {muted}; '
        f'text-transform: uppercase; letter-spacing: 0.6px; margin-left: 6px;">&middot; Today&rsquo;s Top Story</span>'
        f'</div>'
        f'<div style="font-size: 18px; font-weight: 800; color: {ink}; line-height: 1.35;">{_esc(item.title)}</div>'
        f'<a href="{_esc(item.url)}" target="_blank" rel="noopener noreferrer" '
        f'style="color: {color}; text-decoration: none; font-weight: 700; font-size: 13px; margin-top: 14px; display: inline-block">'
        f'Read More &rarr;</a>'
        f'</div></td></tr>'
    )


def _brand_header() -> str:
    """Render the header using a single hosted image asset."""
    # Point this to your single image containing the icon + the word "Polly"
    logo_url = "https://thepolly.co/assets/polly-header.png"

    return (
        f'<a href="https://thepolly.co" target="_blank" style="text-decoration: none; display: block;">'
        f'<img src="{logo_url}" alt="Polly" height="36" '
        f'style="display: block; border: 0; outline: none; height: 36px; width: auto;" />'
        f'</a>'
    )


def render_brief(pulse: HiringPulse, top_stories: list[TopStory], featured_jobs: list[JobPosting],
                 quote_text: str = None, quote_source: str = None, today: dt.date = None) -> str:
    """Generate the complete HTML email for The Polly Brief."""
    today = today or dt.date.today()
    try:
        date_label = today.strftime('%A, %B %-d, %Y')
    except ValueError:
        date_label = today.strftime('%A, %B %d, %Y').replace(' 0', ' ')

    muted = _c('MUTED', '#64748B')
    ink = _c('INK', '#0F172A')
    bg = _c('BG', '#F1F5F9')
    card = _c('CARD', '#FFFFFF')
    accent = _c('ACCENT', '#1E3A8A')
    white = _c('WHITE', '#FFFFFF')
    hairline = _c('HAIRLINE', '#E2E8F0')
    headline_font = _c('HEADLINE_FONT', 'Georgia, serif')
    body_font = _c('BODY_FONT', '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif')

    muted_default_css = f"font-size: 14px; color: {muted};"

    category_rows = ''.join(_list_row(name) for name, _c_val in pulse.top_categories)
    if not category_rows:
        category_rows = f'<tr><td style="{muted_default_css}">No category data available.</td></tr>'

    employer_rows = ''.join(_list_row(name) for name, _c_val in pulse.top_employers)
    if not employer_rows:
        employer_rows = f'<tr><td style="{muted_default_css}">No employer data available.</td></tr>'

    story_rows = ''
    for i, st in enumerate(top_stories):
        if i > 0:
            story_rows += _divider()
        story_rows += _story_block(st)

    job_rows = ''
    for job in featured_jobs:
        job_rows += _featured_job_block(job)
    if not job_rows:
        job_rows = f'<tr><td style="{muted_default_css}">No featured jobs today.</td></tr>'

    quote_section = ''
    if quote_text:
        attribution = ''
        if quote_source:
            attribution = f'<div style="{muted_default_css}; margin-top: 10px">&mdash; {_esc(quote_source)}</div>'
        quote_section = (
            _divider() +
            f'<tr><td style="padding: 0 40px">'
            f'{_section_heading("💬", "Quote of the Day")}'
            f'<div style="font-size: 16px; font-weight: 600; color: {ink}; font-style: italic; line-height: 1.4">'
            f'&ldquo;{_esc(quote_text)}&rdquo;</div>{attribution}</td></tr>'
        )

    days_left = _days_until_election(today)

    topic_colors = _c('TOPIC_COLORS', {})
    if not isinstance(topic_colors, dict):
        topic_colors = {}

    top_bar_gradient = (
        f"{topic_colors.get('Campaigns', '#2563EB')}, "
        f"{topic_colors.get('Media', '#059669')}, "
        f"{topic_colors.get('AI+Policy', '#7C3AED')}, "
        f"{topic_colors.get('Energy', '#D97706')}, "
        f"{topic_colors.get('Finance', '#DC2626')}, "
        f"{topic_colors.get('Legislative', '#4F46E5')}"
    )

    parts = [
        '<!DOCTYPE html><html><head>',
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">',
        '<title>The Polly Brief</title></head>',
        f'<body style="margin: 0; padding: 0; background-color: {bg}; font-family: {body_font};">',
        '<div style="display: none; max-height: 0; overflow: hidden; mso-hide: all">',
    ]

    top_story = _pick_top_highlight(top_stories)
    preheader = (top_story.item.title if top_story else
                 f'{pulse.total_active} active jobs in politics & public affairs')
    parts.append(_esc(preheader))
    parts.append('&nbsp;' * 40)
    parts.append('</div>')

    parts.extend([
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color: {bg}; padding: 32px 0">',
        '<tr><td align="center">',
        f'<table role="presentation" width="600" cellpadding="0" cellspacing="0" style="background-color: {card}; border-radius: 14px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.06)">',
        f'<tr><td style="background-color: {accent}; background: linear-gradient(90deg, {top_bar_gradient}); height: 6px; line-height: 6px; font-size: 0">&nbsp;</td></tr>',
        '<tr><td style="padding: 32px 40px 20px 40px">',
        _brand_header(),
        f'<div style="font-size: 12px; color: {muted}; margin-top: 10px; letter-spacing: 0.3px; font-weight: 600;">{_esc(date_label)}</div>',
        '</td></tr>',
        _top_highlight_block(top_stories),
        _divider(),
        '<tr><td style="padding: 0 40px">',
        f'{_section_heading("📊", "Polly Hiring Pulse")}',
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin-bottom: 20px;"><tr>',
        _stat_block(f'{pulse.total_active:,}', 'Active Jobs', bg_color="#1E3A8A", url='https://jobs.thepolly.co/jobs'),
        _stat_block(str(pulse.new_today), 'New Today', bg_color="#2563EB"),
        '</tr></table>',
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>',
        '<td width="50%" valign="top" style="padding-right: 20px">',
        f'<div style="font-size: 11px; font-weight: 800; color: {muted}; text-transform: uppercase; letter-spacing: 0.6px; margin-bottom: 8px">Top Hiring Categories</div>',
        f'<table role="presentation" cellpadding="0" cellspacing="0">{category_rows}</table></td>',
        '<td width="50%" valign="top">',
        f'<div style="font-size: 11px; font-weight: 800; color: {muted}; text-transform: uppercase; letter-spacing: 0.6px; margin-bottom: 8px">Top Hiring Organizations</div>',
        f'<table role="presentation" cellpadding="0" cellspacing="0">{employer_rows}</table></td>',
        '</tr></table></td></tr>',
        _divider(),
        '<tr><td style="padding: 0 40px">',
        f'{_section_heading("📰", "Top Stories")}',
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0">{story_rows}</table>',
        '</td></tr>',
        _divider(),
        '<tr><td style="padding: 0 40px">',
        f'{_section_heading("🔥", "Jobs Worth Looking At")}',
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0">{job_rows}</table>',
        '</td></tr>',
        _divider(),
        '<tr><td style="padding: 0 40px">',
        f'<div style="background-color: #0F172A; border-radius: 12px; padding: 24px; text-align: center">',
        f'{_section_heading("📅", "Election Countdown", color=white)}',
        f'<div style="font-size: 44px; font-weight: 900; color: {white}; font-family: {headline_font}; letter-spacing: -1px; line-height: 1;">{days_left}</div>',
        f'<div style="font-size: 11px; color: #94A3B8; text-transform: uppercase; letter-spacing: 0.8px; margin-top: 8px; font-weight: 700;">Days Until Election Day</div>',
        '</div></td></tr>',
        quote_section,
        '<tr><td style="padding: 24px 40px 16px 40px; text-align: center">',
        f'<a href="https://thepolly.co" target="_blank" rel="noopener noreferrer" style="color: {muted}; text-decoration: none; font-size: 12px; font-weight: 600;">Know someone job hunting in politics? Invite them to Polly →</a>',
        '</td></tr>',
        '<tr><td style="padding: 16px 40px 36px 40px">',
        f'<div style="border-top: 1px solid {hairline}; padding-top: 18px; text-align: center">',
        f'<div style="font-size: 12px; font-weight: 700; color: {ink};">Powered by Pollyai</div>',
        f'<div style="font-size: 11px; color: {muted}; margin-top: 2px">The Talent Marketplace for Politics &amp; Public Affairs</div>',
        '</div></td></tr>',
        '</table></td></tr></table></body></html>',
    ])

    return ''.join(parts)
