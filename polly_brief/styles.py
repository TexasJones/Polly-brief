from __future__ import annotations

# Core Color Palette
INK = '#161616'
MUTED = '#767676'
ACCENT = '#2B5A4D'
ACCENT_LIGHT = '#E4EDE9'
HAIRLINE = '#E7E5E0'
BG = '#F4F3EF'
CARD = '#FFFFFF'
WHITE = '#FFFFFF'

# Typography
HEADLINE_FONT = "Georgia, 'Times New Roman', serif"
BODY_FONT = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"

# Topic Colors — Each section gets its own visual identity
TOPIC_COLORS = {
    'Campaigns': '#3357A8',
    'Media': '#8E44AD',
    'AI+Policy': '#0E8C96',
    'Energy': '#C77B12',
    'Finance': '#2B5A4D',
    'Legislative': '#A8324A',
}


# ============================================================================
# STYLE BUILDERS — Composable, DRY style generation
# ============================================================================

def divider_style() -> str:
    """Subtle horizontal divider with refined opacity."""
    return f'border-top: 2px solid {HAIRLINE}; margin: 28px 0;'


def section_heading_style(color: str = INK, size: str = '15px') -> str:
    """Reusable section heading styling."""
    return (f'font-size: {size}; font-weight: 700; color: {color}; '
            f'font-family: {BODY_FONT}; letter-spacing: 0.4px;')


def section_subtitle_style() -> str:
    """Small muted subtitle next to a section heading."""
    return f'font-size: 12px; color: {MUTED}; font-family: {BODY_FONT};'


def badge_style(bg_color: str, text_color: str = WHITE) -> str:
    """Solid-color pill badge — used for topic tags so a section's color
    shows up as an actual color block instead of just tinted text."""
    return (f'display: inline-block; background-color: {bg_color}; color: {text_color}; '
            f'padding: 4px 12px; border-radius: 20px; font-size: 11px; font-weight: 700; '
            f'text-transform: uppercase; letter-spacing: 0.5px; font-family: {BODY_FONT};')


def top_story_tag_style() -> str:
    """Translucent white pill for the '★ TODAY'S TOP STORY ★' tag, meant
    to sit on top of a solid dark background."""
    return (f'display: inline-block; background-color: rgba(255,255,255,0.18); color: {WHITE}; '
            f'padding: 5px 14px; border-radius: 20px; font-size: 11px; font-weight: 700; '
            f'text-transform: uppercase; letter-spacing: 1px; font-family: {BODY_FONT};')


def card_style(background: str = CARD, radius: str = '10px', padding: str = '14px 18px',
               border_left: str = None) -> str:
    """Reusable card/box styling with optional accent border."""
    style = f'background-color: {background}; border-radius: {radius}; padding: {padding};'
    if border_left:
        style += f' border-left: 4px solid {border_left};'
    return style


def bordered_card_style(radius: str = '14px') -> str:
    """Plain white card with a thin hairline border — used for the Hiring
    Pulse panel and the newsroom grid cards."""
    return f'background-color: {CARD}; border: 1px solid {HAIRLINE}; border-radius: {radius};'


def stat_number_style(color: str = ACCENT, size: str = '32px') -> str:
    """Large, impactful stat number styling."""
    return f'font-size: {size}; font-weight: 900; color: {color}; letter-spacing: -1px; font-family: {HEADLINE_FONT};'


def stat_label_style(color: str = MUTED, size: str = '11px') -> str:
    """Small, uppercase stat label."""
    return f'font-size: {size}; color: {color}; text-transform: uppercase; letter-spacing: 0.8px; margin-top: 2px;'


def headline_style(color: str = INK, size: str = '18px', font: str = HEADLINE_FONT) -> str:
    """Story/article headline styling."""
    return f'font-size: {size}; font-weight: 700; color: {color}; line-height: 1.35; font-family: {font};'


def link_style(color: str, weight: str = '700', underline: bool = False) -> str:
    """Consistent link styling."""
    decoration = 'underline' if underline else 'none'
    return f'color: {color}; text-decoration: {decoration}; font-weight: {weight};'


def solid_button_style(bg_color: str, text_color: str = WHITE, padding: str = '12px 22px') -> str:
    """Solid call-to-action button styling."""
    return (f'background-color: {bg_color}; color: {text_color}; padding: {padding}; '
            f'border-radius: 6px; font-weight: 700; font-size: 13px; text-decoration: none; '
            f'display: inline-block; font-family: {BODY_FONT};')


def outline_button_style(border_color: str, text_color: str = None, padding: str = '10px 20px') -> str:
    """Outlined (transparent-fill) button — used for secondary CTAs like
    'View Job' or 'Explore all jobs on ThePolly.co'."""
    text_color = text_color or border_color
    return (f'background-color: transparent; color: {text_color}; padding: {padding}; '
            f'border: 1.5px solid {border_color}; border-radius: 6px; font-weight: 700; '
            f'font-size: 13px; text-decoration: none; display: inline-block; font-family: {BODY_FONT};')


def highlight_block_style(bg_color: str) -> str:
    """Solid-color hero block for the top story."""
    return f'background-color: {bg_color}; border-radius: 14px; padding: 28px 28px 24px 28px;'


def newsroom_card_style() -> str:
    """Card style for each story tile in the 3-column newsroom grid."""
    return (f'background-color: {CARD}; border: 1px solid {HAIRLINE}; border-radius: 10px; '
            f'padding: 16px;')


def icon_circle_style(bg_color: str, size: str = '40px') -> str:
    """Circular icon badge (e.g. the calendar icon on the countdown block)."""
    return (f'display: inline-block; width: {size}; height: {size}; line-height: {size}; '
            f'background-color: {bg_color}; border-radius: 50%; text-align: center; font-size: 18px;')


def logo_box_style(size: str = '44px') -> str:
    """Small square frame for a company logo on a job card."""
    return (f'width: {size}; height: {size}; border: 1px solid {HAIRLINE}; border-radius: 8px; '
            f'background-color: {WHITE};')


def list_row_style(text_color: str = INK, size: str = '14px', 
                   padding: str = '6px 0') -> str:
    """Styling for list items."""
    return f'padding: {padding}; font-size: {size}; color: {text_color}; line-height: 1.5;'


def featured_job_card_style() -> str:
    """Job row card — light neutral background, no color-coded border
    (color now lives on the logo/badge instead) to match the flatter,
    grid-style job list look."""
    return f'background-color: {BG}; border-radius: 8px; padding: 14px 16px;'


def muted_text_style(size: str = '13px') -> str:
    """Secondary/muted text styling."""
    return f'font-size: {size}; color: {MUTED}; line-height: 1.6;'


def summary_text_style() -> str:
    """Story summary/excerpt text styling."""
    return f'font-size: 14px; color: {MUTED}; line-height: 1.6; margin: 8px 0 12px 0;'
