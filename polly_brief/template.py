from __future__ import annotations
import datetime as dt
import html
from typing import Optional
from jobs_snapshot import HiringPulse, JobPosting
from news_snapshot import TopStory
import styles as s

ELECTION_DAY = dt.date(2026, 11, 3)


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
    return (f'<div style="{s.section_heading_style(color)}">'
            f'{emoji} {_esc(title)}</div>')


def _list_row(text: str) -> str:
    """Render a single list item row."""
    return (f'<tr><td style="{s.list_row_style()}">'
            f'{_esc(text)}</td></tr>')


def _stat_block(number: str, label: str, url: str = None) -> str:
    """Render an enhanced stat block (Active Jobs, New Today, etc.)."""
    open_tag = f'<a href="{url}" target="_blank" rel="noopener noreferrer" style="text-decoration:none;">' if url else '<div>'
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
    color = _topic_color(story.section)
    heading = _section_heading(story.emoji, story.section, color=color)
    
    if not story.item:
        return (f'<tr><td style="padding-bottom: 12px;">{heading}'
                f'<div style="{s.muted_text_style()}; font-style: italic;">'
                f'No story matched this section today.</div></td></tr>')
    
    item = story.item
    summary_html = ''
    if item.summary:
        summary_html = f'<div style="{s.summary_text_style()}">{_esc(item.summary)}</div>'
    
    return (f'<tr><td style="padding-bottom: 12px;">{heading}'
            f'<div style="{s.headline_style()}">{_esc(item.title)}</div>'
            f'{summary_html}'
            f'<a href="{_esc(item.url)}" target="_blank" rel="noopener noreferrer" '
            f'style="{s.link_style(color)}; font-size: 13px;">'
            f'Read More &rarr;</a></td></tr>')


def _featured_job_block(job: JobPosting) -> str:
    """Render an enhanced featured job card with colored left border."""
    location = _esc(job.location) if job.location else ''
    company = _esc(job.company)
    
    # Create colored border based on job posting date or default to accent
    job_color = s.ACCENT
    
    meta_parts = [p for p in [company, location] if p]
    meta = ' &middot; '.join(meta_parts)
    
    return (f'<tr><td style="padding-bottom: 14px;">'
            f'<div style="{s.featured_job_card_style(job_color)}">'
            f'<a href="{_esc(job.url)}" target="_blank" rel="noopener noreferrer" '
            f'style="{s.link_style(job_color)}; font-size: 15px;">'
            f'{_esc(job.title)}</a>'
            f'<div style="{s.muted_text_style(size="13px")}; margin-top: 6px;">{meta}</div>'
            f'</div></td></tr>')


def _pick_top_highlight(top_stories: list[TopStory]) -> Optional[TopStory]:
    """Find the first story with content to feature at the top."""
    for story in top_stories:
        if story.item:
            return story
    return None


def _top_highlight_block(top_stories: list[TopStory]) -> str:
    """Render a prominent featured story box."""
    story = _pick_top_highlight(top_stories)
    if not story:
        return ''
    
    color = _topic_color(story.section)
    item = story.item
    
    return (f'<tr><td style="padding: 0 40px 32px 40px;">'
            f'<div style="{s.highlight_block_style(color, color)}">'
            f'<div style="{s.section_heading_style(color, size="12px")}; '
            f'text-transform: uppercase; margin-bottom: 10px;">'
            f"Today's Top Story &middot; {story.emoji} {_esc(story.section)}</div>"
            f'<div style="{s.headline_style(size="19px")}">{_esc(item.title)}</div>'
            f'<a href="{_esc(item.url)}" target="_blank" rel="noopener noreferrer" '
            f'style="{s.link_style(color)}; font-size: 13px; margin-top: 12px; display: inline-block;">'
            f'Read More &rarr;</a>'
            f'</div></td></tr>')


def render_brief(pulse: HiringPulse, top_stories: list[TopStory], featured_jobs: list[JobPosting],
                 quote_text: str = None, quote_source: str = None, today: dt.date = None) -> str:
    """Generate the complete HTML email for The Polly Brief."""
    today = today or dt.date.today()
    date_label = today.strftime('%A, %B %-d, %Y')
    
    # Build category/employer rows
    category_rows = ''.join(_list_row(name) for name, _c in pulse.top_categories)
    if not category_rows:
        category_rows = f'<tr><td style="{s.muted_text_style()};">No category data available.</td></tr>'
    
    employer_rows = ''.join(_list_row(name) for name, _c in pulse.top_employers)
    if not employer_rows:
        employer_rows = f'<tr><td style="{s.muted_text_style()};">No employer data available.</td></tr>'
    
    # Build story rows
    story_rows = ''
    for i, st in enumerate(top_stories):
        if i > 0:
            story_rows += _divider()
        story_rows += _story_block(st)
    
    # Build job rows
    job_rows = ''
    for job in featured_jobs:
        job_rows += _featured_job_block(job)
    if not job_rows:
        job_rows = f'<tr><td style="{s.muted_text_style()};">No featured jobs today.</td></tr>'
    
    # Build quote section (if provided)
    quote_section = ''
    if quote_text:
        attribution = ''
        if quote_source:
            attribution = f'<div style="{s.muted_text_style()}; margin-top: 10px;">&mdash; {_esc(quote_source)}</div>'
        quote_section = (
            _divider() +
            f'<tr><td style="padding: 0 40px;">'
            f'{_section_heading("💬", "Quote of the Day")}'
            f'<div style="{s.headline_style(size="16px")}; font-style: italic;">'
            f'&ldquo;{_esc(quote_text)}&rdquo;</div>{attribution}</td></tr>'
        )
    
    # Base64 logo (unchanged from original)
    logo_b64 = "iVBORw0KGgoAAAANSUhEUgAAAK0AAABaCAYAAADKONbiAAAbXklEQVR4nO19eVgUV7r375yqgoZmkc0dFFRkMSriAm6tIsRokkFCozG4TJKR+cbcGTRek1wz6SbJTBLR5PqMmuv1i0acJ04aNXEc830zGoVkoolj1IlLNEZRFFFQxw1Uurv"
    
    days_left = _days_until_election(today)
    
    # Assemble complete HTML
    parts = [
        '<!DOCTYPE html><html><head>',
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">',
        '<title>The Polly Brief</title></head>',
        f'<body style="margin: 0; padding: 0; background-color: {s.BG}; font-family: {s.BODY_FONT};">',
        
        # Preheader text
        '<div style="display: none; max-height: 0; overflow: hidden; mso-hide: all;">',
    ]
    
    top_story = _pick_top_highlight(top_stories)
    preheader = (top_story.item.title if top_story else 
                f'{pulse.total_active} active jobs in politics & public affairs')
    parts.append(_esc(preheader))
    parts.append('&nbsp;' * 40)
    parts.append('</div>')
    
    # Main container
    parts.extend([
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color: {s.BG}; padding: 32px 0;">',
        '<tr><td align="center">',
        f'<table role="presentation" width="600" cellpadding="0" cellspacing="0" style="background-color: {s.CARD}; border-radius: 14px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.08);">',
        
        # Top accent bar
        f'<tr><td style="background: linear-gradient(90deg, {s.ACCENT}, {_topic_color("Campaigns")}); height: 5px; line-height: 5px; font-size: 0;">&nbsp;</td></tr>',
        
        # Header with logo
        '<tr><td style="padding: 36px 40px 24px 40px;">',
        '<table role="presentation" cellpadding="0" cellspacing="0"><tr>',
        f'<td style="padding-right: 12px; vertical-align: middle;"><img src="data:image/png;base64,{logo_b64}" width="58" height="30" alt="Polly" style="display: block;"></td>',
        f'<td style="vertical-align: middle;"><div style="font-size: 24px; font-weight: 900; color: {s.INK}; letter-spacing: -0.5px; font-family: {s.HEADLINE_FONT};">The Polly Brief</div></td>',
        '</tr></table>',
        f'<div style="font-size: 12px; color: {s.MUTED}; margin-top: 8px; letter-spacing: 0.3px;">{_esc(date_label)}</div>',
        '</td></tr>',
        
        # Top story highlight
        _top_highlight_block(top_stories),
        _divider(),
        
        # Hiring Pulse section
        '<tr><td style="padding: 0 40px;">',
        f'{_section_heading("📊", "Polly Hiring Pulse")}',
        '<table role="presentation" cellpadding="0" cellspacing="0" style="margin-bottom: 24px;"><tr>',
        _stat_block(f'{pulse.total_active:,}', 'Active Jobs', url='https://jobs.thepolly.co/jobs'),
        _stat_block(str(pulse.new_today), 'New Today'),
        '</tr></table>',
        
        # Top categories & employers
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>',
        '<td width="50%" valign="top" style="padding-right: 20px;">',
        f'<div style="font-size: 11px; font-weight: 700; color: {s.MUTED}; text-transform: uppercase; letter-spacing: 0.6px; margin-bottom: 12px;">Top Hiring Categories</div>',
        f'<table role="presentation" cellpadding="0" cellspacing="0">{category_rows}</table></td>',
        '<td width="50%" valign="top">',
        f'<div style="font-size: 11px; font-weight: 700; color: {s.MUTED}; text-transform: uppercase; letter-spacing: 0.6px; margin-bottom: 12px;">Top Hiring Organizations</div>',
        f'<table role="presentation" cellpadding="0" cellspacing="0">{employer_rows}</table></td>',
        '</tr></table></td></tr>',
        
        _divider(),
        
        # Top Stories section
        '<tr><td style="padding: 0 40px;">',
        f'<div style="{s.section_heading_style()}">📰 Top Stories</div>',
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0">{story_rows}</table>',
        '</td></tr>',
        
        _divider(),
        
        # Featured Jobs section
        '<tr><td style="padding: 0 40px;">',
        f'{_section_heading("🔥", "Jobs Worth Looking At")}',
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0">{job_rows}</table>',
        '</td></tr>',
        
        _divider(),
        
        # Election Countdown
        '<tr><td style="padding: 0 40px;">',
        f'<div style="background: linear-gradient(135deg, {s.INK}, #2a2a2a); border-radius: 12px; padding: 28px; text-align: center;">',
        f'{_section_heading("📅", "Election Countdown", color=s.WHITE)}',
        f'<div style="font-size: 48px; font-weight: 900; color: {s.WHITE}; font-family: {s.HEADLINE_FONT}; letter-spacing: -1px;">{days_left}</div>',
        f'<div style="font-size: 12px; color: #BBBBBB; text-transform: uppercase; letter-spacing: 0.8px; margin-top: 8px;">Days Until Election Day</div>',
        '</div></td></tr>',
        
        # Quote section (if present)
        quote_section,
        
        # Footer
        '<tr><td style="padding: 28px 40px 16px 40px; text-align: center;">',
        f'<a href="https://thepolly.co" target="_blank" rel="noopener noreferrer" style="{s.link_style(s.MUTED)}; font-size: 12px;">Know someone job hunting in politics? Invite them to Polly →</a>',
        '</td></tr>',
        
        '<tr><td style="padding: 16px 40px 40px 40px;">',
        f'<div style="border-top: 1px solid {s.HAIRLINE}; padding-top: 20px; text-align: center;">',
        f'<div style="font-size: 12px; font-weight: 600; color: {s.INK};">Powered by Pollyai</div>',
        f'<div style="font-size: 11px; color: {s.MUTED}; margin-top: 4px;">The Talent Marketplace for Politics &amp; Public Affairs</div>',
        '</div></td></tr>',
        
        '</table></td></tr></table></body></html>',
    ]
    
    return ''.join(parts)
