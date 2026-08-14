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
            f'margin-bottom: 16px; font-family: {BODY_FONT}; letter-spacing: 0.4px;')


def card_style(background: str = CARD, radius: str = '10px', padding: str = '14px 18px',
               border_left: str = None) -> str:
    """Reusable card/box styling with optional accent border."""
    style = f'background-color: {background}; border-radius: {radius}; padding: {padding};'
    if border_left:
        style += f' border-left: 4px solid {border_left};'
    return style


def stat_block_style(background: str, number_color: str = ACCENT, 
                     font_size: str = '36px', label_size: str = '11px') -> str:
    """Enhanced stat block with larger numbers and better contrast."""
    return (f'background: linear-gradient(135deg, {background}, rgba(255,255,255,0.5)); '
            f'border-radius: 12px; padding: 20px 24px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);')


def stat_number_style(color: str = ACCENT, size: str = '40px') -> str:
    """Large, impactful stat number styling."""
    return f'font-size: {size}; font-weight: 900; color: {color}; letter-spacing: -1px; font-family: {HEADLINE_FONT};'


def stat_label_style(color: str = MUTED, size: str = '11px') -> str:
    """Small, uppercase stat label."""
    return f'font-size: {size}; color: {color}; text-transform: uppercase; letter-spacing: 0.8px; margin-top: 4px;'


def headline_style(color: str = INK, size: str = '18px', font: str = HEADLINE_FONT) -> str:
    """Story/article headline styling."""
    return f'font-size: {size}; font-weight: 700; color: {color}; line-height: 1.35; font-family: {font};'


def link_style(color: str, weight: str = '700', underline: bool = False) -> str:
    """Consistent link styling."""
    decoration = 'underline' if underline else 'none'
    return f'color: {color}; text-decoration: {decoration}; font-weight: {weight};'


def highlight_block_style(bg_color: str, border_color: str) -> str:
    """Featured/highlight box styling (top story, featured job, etc.)"""
    return (f'background-color: {bg_color}15; border-left: 5px solid {border_color}; '
            f'border-radius: 8px; padding: 20px 22px; box-shadow: 0 1px 3px rgba(0,0,0,0.08);')


def button_style(bg_color: str, text_color: str = WHITE, padding: str = '12px 16px') -> str:
    """Call-to-action button styling."""
    return (f'background-color: {bg_color}; color: {text_color}; padding: {padding}; '
            f'border-radius: 6px; font-weight: 600; text-decoration: none; '
            f'display: inline-block; transition: opacity 0.2s;')


def list_row_style(text_color: str = INK, size: str = '14px', 
                   padding: str = '6px 0') -> str:
    """Styling for list items."""
    return f'padding: {padding}; font-size: {size}; color: {text_color}; line-height: 1.5;'


def featured_job_card_style(color: str) -> str:
    """Enhanced job card with topic-colored left border."""
    return (f'background-color: {CARD}; border-left: 5px solid {color}; '
            f'border-radius: 8px; padding: 16px 18px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);')


def muted_text_style(size: str = '13px') -> str:
    """Secondary/muted text styling."""
    return f'font-size: {size}; color: {MUTED}; line-height: 1.6;'


def summary_text_style() -> str:
    """Story summary/excerpt text styling."""
    return f'font-size: 14px; color: {MUTED}; line-height: 1.6; margin: 8px 0 12px 0;'
