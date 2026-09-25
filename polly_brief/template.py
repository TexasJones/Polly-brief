from __future__ import annotations
import datetime as dt
import html
import inspect
from typing import Optional
from jobs_snapshot import HiringPulse, JobPosting
from news_snapshot import TopStory
from poliodds_snapshot import PoliOdds, OddsLine, VOTEHUB_WEB
import styles as s

ELECTION_DAY = dt.date(2026, 11, 3)

# Party colors for PoliOdds Watch -- intentionally NOT drawn from
# TOPIC_COLORS (those brand news sections; DEM/REP need to read as
# "blue team / red team" at a glance, independent of whatever color a
# news topic happens to already own).
PARTY_COLORS = {"DEM": "#1D4ED8", "REP": "#B91C1C", "IND": "#6D28D9"}
DEFAULT_PARTY_COLOR = "#475569"

# Hosted, transparent PNG of the Polly bird mark (exact artwork, not inline SVG —
# Outlook desktop and Brevo campaigns don't reliably render inline/embedded SVG).
BIRD_LOGO_URL = "https://raw.githubusercontent.com/TexasJones/Polly-brief/main/polly_brief/polly-bird-header.png"
BIRD_LOGO_RATIO = 596 / 315  # width/height of the source artwork, keep any resized img proportional

# Order the Remote/Hybrid/Onsite bar renders in, left to right. Colors are
# looked up from styles.py via _c('LOCATION_COLORS', ...) with this as the
# fallback, so a palette tweak in styles.py doesn't require touching this
# file — same pattern as TOPIC_COLORS below.
LOCATION_MIX_ORDER = ("Remote", "Hybrid", "Onsite")
DEFAULT_LOCATION_COLORS = {"Remote": "#1E3A8A", "Hybrid": "#D97706", "Onsite": "#CBD5E1"}


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


def _mobile_style_block() -> str:
    """Media query that reflows the fixed-width 600px layout for narrow
    (phone) browser viewports. Email clients that ignore <style>/@media
    (older Outlook desktop chief among them) simply keep the existing
    fixed-width table -- this only changes rendering in modern mail apps
    (Gmail, Apple Mail, most mobile clients) and in the GitHub Pages
    "View in browser" copy, both of which do support @media queries.

    The !important flags are necessary because every element in this
    template is styled with inline styles (the standard email-safe
    pattern), which otherwise always win over stylesheet rules.
    """
    return (
        '<style>'
        '@media only screen and (max-width: 620px) {'
        '  .polly-card { width: 100% !important; }'
        '  .polly-pad { padding-left: 20px !important; padding-right: 20px !important; }'
        '  .polly-col { display: block !important; width: 100% !important; '
        'padding-right: 0 !important; padding-left: 0 !important; padding-bottom: 12px !important; }'
        '}'
        '</style>'
    )


def _divider() -> str:
    """Render a horizontal divider row."""
    hairline = _c('HAIRLINE', '#E2E8F0')
    divider_css = _style('divider_style', fallback=f"border-bottom: 1px solid {hairline}; margin: 24px 0;")
    return (f'<tr><td class="polly-pad" style="padding:0 40px;">'
            f'<div style="{divider_css}"></div>'
            f'</td></tr>')


def _section_heading(emoji: str, title: str, color: str = None, gap: int = 14) -> str:
    """Render a section heading.

    The bottom margin is set here explicitly rather than left to the
    style: styles.section_heading_style() carries no margin (only this
    function's fallback did, and the fallback is never used when styles.py
    is present), so every heading sat flush against the cards/badges below
    it."""
    ink = _c('INK', '#0F172A')
    color = color or ink
    heading_css = _style('section_heading_style', color, fallback=f"font-size: 18px; font-weight: 800; color: {color};")
    return (f'<div style="{heading_css} margin: 0 0 {gap}px 0;">'
            f'{emoji} {_esc(title)}</div>')


def _subheading_label(text: str) -> str:
    """Small uppercase label used above a mini-section within Hiring Pulse
    (e.g. 'Top Hiring Categories', 'Remote / Hybrid / Onsite'). Pulled out
    as its own helper since it was previously written inline twice with
    identical styling — this keeps the two Hiring Pulse column labels and
    the new location-mix label from drifting out of sync."""
    muted = _c('MUTED', '#64748B')
    return (f'<div style="font-size: 11px; font-weight: 800; color: {muted}; '
            f'text-transform: uppercase; letter-spacing: 0.6px; margin-bottom: 8px">'
            f'{_esc(text)}</div>')


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


def _pair_cell_padding(first: bool) -> str:
    """Split the gap between two side-by-side cards evenly (6px each side)
    so the pair is centered in the column. Previously both cards padded
    only on the right, which left the right-hand card ~12px short of the
    column edge."""
    return 'padding-right: 6px;' if first else 'padding-left: 6px;'


def _stat_block(number: str, label: str, bg_color: str = "#1E3A8A", url: str = None,
                first: bool = True) -> str:
    """Render a high-contrast stat card with solid white text."""
    open_tag = (f'<a href="{url}" target="_blank" rel="noopener noreferrer" '
                f'style="text-decoration:none; display:block;">') if url else '<div style="display:block;">'
    close_tag = '</a>' if url else '</div>'

    return (f'<td width="50%" class="polly-col" style="{_pair_cell_padding(first)} vertical-align: top;">'
            f'{open_tag}'
            f'<div style="background-color: {bg_color}; border-radius: 10px; padding: 18px 16px; text-align: center; color: #FFFFFF;">'
            f'<div style="font-size: 32px; font-weight: 900; line-height: 1; color: #FFFFFF; font-family: Helvetica, Arial, sans-serif;">{_esc(number)}</div>'
            f'<div style="font-size: 11px; font-weight: 800; text-transform: uppercase; margin-top: 8px; letter-spacing: 0.8px; color: #FFFFFF; opacity: 0.95;">{_esc(label)}</div>'
            f'</div>'
            f'{close_tag}</td>')


def _location_mix_bar(mix: dict[str, int]) -> str:
    """Render the Remote/Hybrid/Onsite split as a single-row stacked bar.

    Built as a plain HTML table with percentage-width cells and solid
    background colors -- the same table-based technique this template
    already uses everywhere else (e.g. _stat_block's width:50% cells).
    Deliberately NOT a generated chart image: that would mean hosting and
    refreshing a PNG on every run (an extra moving part, and one more
    thing that can go stale or get blocked by an email client's
    image-loading default), whereas an inline table renders immediately
    and consistently across Outlook, Gmail, and Apple Mail with zero
    external requests.

    `mix` is expected to have all three LOCATION_MIX_ORDER keys present
    (HiringPulse.location_mix is zero-filled by jobs_snapshot.py), but
    .get(..., 0) below is kept defensive in case this is ever called with
    a partial dict from elsewhere.
    """
    muted = _c('MUTED', '#64748B')
    total = sum(mix.get(label, 0) for label in LOCATION_MIX_ORDER)

    if total == 0:
        return f'<div style="font-size: 13px; color: {muted};">No location data available today.</div>'

    colors = _c('LOCATION_COLORS', DEFAULT_LOCATION_COLORS)
    if not isinstance(colors, dict):
        colors = DEFAULT_LOCATION_COLORS

    segment_cells = []
    legend_items = []
    for label in LOCATION_MIX_ORDER:
        count = mix.get(label, 0)
        if count == 0:
            continue  # skip empty segments rather than render a 0%-wide <td>

        pct = round(count / total * 100)
        color = colors.get(label, '#94A3B8')
        text_color = '#FFFFFF' if label != 'Onsite' else '#334155'
        # Only print the percentage inside the segment itself if there's
        # room for it to be legible -- a 4%-wide sliver showing "4%" just
        # overflows illegibly in most email clients. The exact number is
        # always still available in the legend below regardless.
        cell_label = f'{pct}%' if pct >= 10 else ''

        segment_cells.append(
            f'<td width="{pct}%" style="background-color: {color}; height: 22px; '
            f'font-size: 10px; font-weight: 800; color: {text_color}; text-align: center; '
            f'line-height: 22px; font-family: Helvetica, Arial, sans-serif;">{cell_label}</td>'
        )
        legend_items.append(
            f'<span style="display:inline-block; margin-right:16px; font-size:12px; color:{muted}; margin-top:6px;">'
            f'<span style="display:inline-block; width:9px; height:9px; border-radius:2px; '
            f'background-color:{color}; margin-right:5px; vertical-align:middle;"></span>'
            f'<span style="vertical-align:middle;">{_esc(label)} &middot; {count}</span></span>'
        )

    bar = (
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        'style="border-radius: 6px; overflow: hidden;"><tr>'
        f'{"".join(segment_cells)}'
        '</tr></table>'
    )
    return bar + f'<div>{"".join(legend_items)}</div>'


def _party_color(key: str) -> str:
    return PARTY_COLORS.get(key, DEFAULT_PARTY_COLOR)


PARTY_ABBR = {"DEM": "D", "REP": "R", "IND": "Ind"}


def _party_abbr(key: str) -> str:
    """"D" / "R" / "Ind", or a candidate surname (title-cased) for an
    outcome Kalshi didn't label with a party."""
    return PARTY_ABBR.get(key, (key or '').title())


def _odds_change_label(change_pts: Optional[int]) -> str:
    """'▲ 2pts vs yesterday' / '▼ 3pts vs yesterday' / '' when
    unknown or flat -- Kalshi's own previous_price_dollars fields are what
    make this possible without a history file of our own (see
    poliodds_snapshot.py)."""
    if not change_pts:
        return ''
    arrow = '▲' if change_pts > 0 else '▼'
    plural = '' if abs(change_pts) == 1 else 's'
    return f'{arrow} {abs(change_pts)}pt{plural} vs yesterday'


def _control_card(line: OddsLine, first: bool = True) -> str:
    """Big colored stat card for House/Senate control -- same visual
    weight as Hiring Pulse's Active Jobs / New Today cards (_stat_block),
    plus a 24h-change line underneath since 'who's ahead' matters less
    here than 'did that just move'."""
    bg = _party_color(line.leader)
    change = _odds_change_label(line.change_pts)
    change_html = (f'<div style="font-size: 11px; font-weight: 700; '
                   f'color: rgba(255,255,255,0.85); margin-top: 6px;">{_esc(change)}</div>') if change else ''

    return (f'<td width="50%" class="polly-col" style="{_pair_cell_padding(first)} vertical-align: top;">'
            f'<a href="{_esc(line.url)}" target="_blank" rel="noopener noreferrer" '
            f'style="text-decoration:none; display:block;">'
            f'<div style="background-color: {bg}; border-radius: 10px; padding: 18px 16px; '
            f'text-align: center; color: #FFFFFF;">'
            f'<div style="font-size: 28px; font-weight: 900; line-height: 1; color: #FFFFFF; '
            f'font-family: Helvetica, Arial, sans-serif;">{_esc(line.leader)} {line.leader_pct}%</div>'
            f'<div style="font-size: 11px; font-weight: 800; text-transform: uppercase; margin-top: 8px; '
            f'letter-spacing: 0.8px; color: #FFFFFF; opacity: 0.95;">{_esc(line.label)} Control</div>'
            f'{change_html}'
            f'</div></a></td>')


def _spotlight_card(line: OddsLine, kind: str) -> str:
    """The single featured race -- either the day's biggest mover or, on
    a quiet day with no real movement, the tightest race on the board
    (see poliodds_snapshot.MOVER_MIN_POINTS). Wider than the two control
    cards since it carries a full race name plus both parties' numbers."""
    bg = _party_color(line.leader)
    ink = _c('INK', '#161616')
    muted = _c('MUTED', '#767676')
    # Leader vs runner-up, not a fixed "D vs R": in a race like Nebraska the
    # real contest is Republican vs independent, and a D/R line would show
    # "D 0% · R 73%" and hide the actual challenger.
    head = f'{_esc(_party_abbr(line.leader))} {line.leader_pct}%'
    runner = (f'{_esc(_party_abbr(line.runner_up))} {line.runner_up_pct}%'
              if line.runner_up and line.runner_up_pct is not None else '')
    both = ' &middot; '.join(p for p in (head, runner) if p)
    change = _odds_change_label(line.change_pts)

    # The whole card is one link (not just the race name) -- same reasoning
    # as _control_card: a small text-only tap target is easy to miss,
    # especially on mobile, when the visual "button" (the colored % box)
    # sits right next to it looking clickable but wasn't.
    return (
        f'<a href="{_esc(line.url)}" target="_blank" rel="noopener noreferrer" '
        f'style="text-decoration: none; display: block; color: inherit;">'
        f'<div style="border: 1px solid {_c("HAIRLINE", "#E7E5E0")}; border-radius: 10px; '
        f'padding: 14px 16px; margin-bottom: 12px;">'
        f'<div style="font-size: 11px; font-weight: 800; text-transform: uppercase; '
        f'letter-spacing: 0.6px; color: {muted}; margin-bottom: 6px;">{_esc(kind)}</div>'
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>'
        f'<td valign="middle">'
        f'<div style="color: {ink}; font-size: 16px; font-weight: 700;">{_esc(line.label)}</div>'
        # `both` is joined with a raw &middot; entity, so it's inserted
        # as-is -- _esc() on the whole string would double-escape the
        # entity into literal "&amp;middot;" text. Each piece that could
        # come from Kalshi (the party/name labels) was already _esc()'d
        # individually above, before the join.
        f'<div style="font-size: 13px; color: {muted}; margin-top: 2px;">{both}'
        f'{" &middot; " + _esc(change) if change else ""}</div>'
        f'</td>'
        f'<td width="70" align="center" valign="middle">'
        f'<div style="background-color: {bg}; border-radius: 8px; padding: 8px 4px; color: #FFFFFF; '
        f'font-size: 18px; font-weight: 900;">{line.leader_pct}%</div>'
        f'</td></tr></table></div></a>'
    )


def _tight_race_row(line: OddsLine) -> str:
    """One compact row per remaining tight race: name + leader on top,
    a two-color split bar below. dem_pct/rep_pct are rendered at their
    own widths (not renormalized to sum to 100) so any gap -- undecided,
    a third-party candidate -- shows honestly as blank track rather than
    being silently absorbed into one party's share."""
    ink = _c('INK', '#161616')
    muted = _c('MUTED', '#767676')
    dem, rep = line.dem_pct or 0, line.rep_pct or 0
    leftover = max(0, 100 - dem - rep)

    segments = ''
    if dem:
        segments += f'<td width="{dem}%" style="background-color:{PARTY_COLORS["DEM"]}; height:12px;"></td>'
    if rep:
        segments += f'<td width="{rep}%" style="background-color:{PARTY_COLORS["REP"]}; height:12px;"></td>'
    if leftover:
        segments += f'<td width="{leftover}%" style="background-color:#E2E8F0; height:12px;"></td>'
    bar = (f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
           f'style="border-radius: 4px; overflow: hidden;"><tr>{segments}</tr></table>')

    # Whole row (label + bar) is one link, same reasoning as the spotlight
    # card above -- the bar itself looks like a control, so it should
    # behave like one rather than only the text next to it being tappable.
    return (
        f'<tr><td style="padding: 6px 0 10px 0;">'
        f'<a href="{_esc(line.url)}" target="_blank" rel="noopener noreferrer" '
        f'style="text-decoration: none; display: block; color: inherit;">'
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>'
        f'<td style="font-size: 13px; font-weight: 700; color: {ink};">{_esc(line.label)}</td>'
        f'<td align="right" style="font-size: 12px; color: {muted}; font-weight: 700;">'
        f'{_esc(line.leader)} {line.leader_pct}%</td>'
        f'</tr></table>{bar}</a></td></tr>'
    )


def _poliodds_section(odds: PoliOdds) -> str:
    """Full PoliOdds Watch body (heading rendered by the caller, same
    pattern as PR & Comms Industry): control cards, one spotlight race,
    up to three more tight races, a polling strip, then attribution.
    Every piece is independently optional -- odds.has_content already
    gated whether this function gets called at all (see render_brief),
    but each sub-piece here also checks its own data so a partial feed
    (say, Kalshi up but VoteHub down) renders whatever came through
    instead of an all-or-nothing block."""
    parts = []

    if odds.house or odds.senate:
        cards = ((_control_card(odds.house, first=True) if odds.house else '') +
                 (_control_card(odds.senate, first=not odds.house) if odds.senate else ''))
        parts.append(
            '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
            f'style="margin-bottom: 16px;"><tr>{cards}</tr></table>'
        )

    if odds.spotlight:
        parts.append(_spotlight_card(odds.spotlight, odds.spotlight_kind or 'Featured Race'))

    if odds.tight_races:
        rows = ''.join(_tight_race_row(r) for r in odds.tight_races)
        parts.append(f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0">{rows}</table>')

    if odds.polls:
        ink = _c('INK', '#161616')
        muted = _c('MUTED', '#767676')
        # One poll per line: run together on a single line, the two items
        # wrapped mid-phrase ("avg of 5 / polls") at normal email widths.
        poll_items = ''.join(
            f'<div style="padding: 2px 0;"><strong style="color:{ink};">{_esc(p.label)}:</strong> '
            f'{_esc(p.value)} <span style="color:{muted};">({_esc(p.detail)})</span></div>'
            for p in odds.polls
        )
        parts.append(f'<div style="font-size: 12px; margin: 4px 0 14px 0;">{poll_items}</div>')

    # Credit only the sources actually shown today: on a day Kalshi is down
    # but VoteHub isn't, the footer must not say "Odds via Kalshi" over a
    # section that has no odds in it.
    muted = _c('MUTED', '#767676')
    credits = []
    if odds.has_odds:
        credits.append(f'Odds via <a href="https://kalshi.com" target="_blank" rel="noopener noreferrer" '
                       f'style="color:{muted};">Kalshi</a>')
    if odds.polls:
        credits.append(f'Polling via <a href="{VOTEHUB_WEB}" target="_blank" rel="noopener noreferrer" '
                       f'style="color:{muted};">VoteHub</a> (CC BY 4.0)')
    credits.append('updated daily')
    parts.append(f'<div style="font-size: 11px; color: {muted};">{" &middot; ".join(credits)}</div>')

    return ''.join(parts)


def _bold_lead_in(text: str, num_words: int = 8) -> str:
    """Bold the first few words of a sentence -- Axios's 'smart brevity'
    trick, so a skimmer catches the gist of each item without reading the
    full summary. Splits on the RAW text first, then escapes each half
    separately, so escaping never gets applied mid-split (which could
    otherwise break an HTML entity like &amp; in two)."""
    words = (text or '').split()
    if not words:
        return ''
    lead = ' '.join(words[:num_words])
    rest = ' '.join(words[num_words:])
    lead_html = f'<strong>{_esc(lead)}</strong>'
    return f'{lead_html} {_esc(rest)}' if rest else lead_html


def _estimate_read_time(top_stories: list[TopStory], quote_text: str = None, wpm: int = 225) -> tuple[int, int]:
    """Rough word count + read-time estimate, Axios-newsletter style
    ('711 words, a 2½-min. read'). Counts only the editorial content a
    reader actually reads top to bottom -- story headlines, summaries, and
    the quote of the day -- not job listings or nav/footer chrome, since
    those are scanned/skimmed rather than read line by line.
    Minutes are rounded to the nearest whole minute, floored at 1 so a
    short brief never claims a '0-min. read'."""
    chunks = []
    for st in top_stories:
        if st.item:
            chunks.append(st.item.title or '')
            if st.item.summary:
                chunks.append(st.item.summary)
    if quote_text:
        chunks.append(quote_text)

    word_count = sum(len(chunk.split()) for chunk in chunks)
    minutes = max(1, round(word_count / wpm))
    return word_count, minutes


def _time_ago_label(published_date, today: dt.date) -> str:
    """Human-readable relative freshness label ('Today', 'Yesterday',
    '3 days ago') for a story's own verified publish date. Returns '' if
    published_date is None (the Tier 3 undated fallback in
    news_snapshot.py) -- an unverified date shouldn't display a
    fabricated-looking label, so the caller simply omits this line rather
    than show something misleading. Day-level only on purpose: the brief is
    built early in the morning but read all day, so "3 hours ago" would be
    wrong by the time most readers see it. (news_snapshot.py never picks a
    story older than 48 hours, so this is always Today or Yesterday.)"""
    if published_date is None:
        return ''
    days = (today - published_date).days
    if days <= 0:
        return 'Today'
    if days == 1:
        return 'Yesterday'
    return f'{days} days ago'


def _story_block(story: TopStory, today: dt.date, show_badge: bool = True) -> str:
    """Render a news story block with a topic-colored badge. show_badge=False
    for a story that already sits under its own section heading (PR & Comms
    Industry), where a badge repeating the heading's words is redundant."""
    color = _topic_color(story.section)
    badge_row = (f'<div style="margin-bottom: 10px">{_topic_badge(story.emoji, story.section, color)}</div>'
                 if show_badge else '')

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
        summary_html = f'<div style="{summary_css}">{_bold_lead_in(item.summary)}</div>'

    time_ago = _time_ago_label(item.published_date, today)
    time_ago_html = ''
    if time_ago:
        time_ago_html = (f'<div style="font-size: 12px; color: {muted}; font-weight: 600; '
                          f'text-transform: uppercase; letter-spacing: 0.4px; margin: 4px 0 8px;">'
                          f'{_esc(time_ago)}</div>')

    ink = _c('INK', '#0F172A')
    headline_css = _style('headline_style', fallback=f"font-size: 16px; font-weight: 700; color: {ink}; line-height: 1.3;")
    link_css = _style('link_style', color, fallback=f"color: {color}; text-decoration: none; font-weight: 700;")

    return (f'<tr><td style="padding-bottom: 16px;">{badge_row}'
            f'<div style="{headline_css}">{_esc(item.title)}</div>'
            f'{summary_html}'
            f'{time_ago_html}'
            f'<a href="{_esc(item.url)}" target="_blank" rel="noopener noreferrer" '
            f'style="{link_css}; font-size: 13px;">'
            f'Read More ({_esc(item.outlet)}) &rarr;</a></td></tr>')


def _featured_job_block(job: JobPosting) -> str:
    """Render a featured job card: a logo square (the company's real logo
    when the feed supplied one via job.logo_url -- populated in
    jobs_snapshot.py but never actually used in this file before -- or
    else a colored initial in the job's topic color) plus title/company/
    location. Replaces the earlier plain-text, left-border-only card: the
    logo square gives each row a visual anchor to scan by. Uses
    logo_box_style() and featured_job_card_style() from styles.py."""
    location = _esc(job.location) if job.location else ''
    company = _esc(job.company)

    accent = _c('ACCENT', '#1E3A8A')
    topic_colors = _c('TOPIC_COLORS', {})
    job_color = topic_colors.get(job.category, accent) if (isinstance(topic_colors, dict) and job.category) else accent

    meta_parts = [p for p in [company, location] if p]
    meta = ' &middot; '.join(meta_parts)

    muted = _c('MUTED', '#64748B')
    ink = _c('INK', '#0F172A')
    headline_font = _c('HEADLINE_FONT', 'Georgia, serif')

    box_css = _style('logo_box_style', fallback=(
        'width: 44px; height: 44px; border: 1px solid #E2E8F0; '
        'border-radius: 8px; background-color: #FFFFFF;'
    ))
    if job.logo_url:
        logo_html = (f'<img src="{_esc(job.logo_url)}" width="44" height="44" alt="" '
                     f'style="display:block; width:44px; height:44px; border-radius:8px; '
                     f'object-fit:contain;">')
    else:
        initial = (job.company[:1] if job.company else '?').upper()
        logo_html = (f'<div style="width:44px; height:44px; line-height:44px; '
                     f'text-align:center; font-family:{headline_font}; font-weight:800; '
                     f'font-size:17px; color:{job_color};">{_esc(initial)}</div>')

    card_css = _style('featured_job_card_style', fallback=(
        'background-color: #F8FAFC; border-radius: 8px; padding: 14px 16px;'
    ))

    return (
        f'<tr><td style="padding-bottom: 10px;">'
        f'<div style="{card_css}">'
        f'<table role="presentation" cellpadding="0" cellspacing="0" width="100%"><tr>'
        f'<td width="44" style="{box_css}" valign="middle" align="center">{logo_html}</td>'
        f'<td style="padding-left: 14px;" valign="middle">'
        f'<a href="{_esc(job.url)}" target="_blank" rel="noopener noreferrer" '
        f'style="color: {ink}; text-decoration: none; font-size: 15px; font-weight: 700;">'
        f'{_esc(job.title)}</a>'
        f'<div style="font-size: 13px; color: {muted}; margin-top: 2px; font-weight: 500;">{meta}</div>'
        f'</td></tr></table>'
        f'</div></td></tr>'
    )


def _pick_top_highlight(top_stories: list[TopStory]) -> Optional[TopStory]:
    """The day's lead story: the one the most other outlets are also
    covering (NewsItem.coverage, counted by news_snapshot.py). Ties -- and
    a day where nothing is widely covered -- go to the earliest section, so
    Campaigns still leads when nothing stands out."""
    with_items = [s for s in top_stories if s.item]
    if not with_items:
        return None
    return max(with_items, key=lambda s: getattr(s.item, 'coverage', 0) or 0)


def _top_highlight_block(top_stories: list[TopStory], today: dt.date) -> str:
    """Render the top story as a solid-color hero block in that story's own
    topic color, with a translucent tag naming the section -- using
    highlight_block_style() and top_story_tag_style() from styles.py
    (previously defined there but never wired up). Replaces the earlier
    light, bordered box, which read as just another card rather than the
    day's lead item; the solid color also means the hero itself changes
    color day to day depending on which section led (blue for a Campaigns
    day, purple for Media, etc.), the same information the badge used to
    carry, just more visible at a glance."""
    story = _pick_top_highlight(top_stories)
    if not story:
        return ''

    color = _topic_color(story.section)
    item = story.item

    white = _c('WHITE', '#FFFFFF')
    headline_font = _c('HEADLINE_FONT', 'Georgia, serif')

    time_ago = _time_ago_label(item.published_date, today)
    time_ago_html = ''
    if time_ago:
        time_ago_html = (f'<div style="font-size: 12px; color: rgba(255,255,255,0.75); '
                          f'font-weight: 600; text-transform: uppercase; letter-spacing: 0.4px; '
                          f'margin: 10px 0 0;">{_esc(time_ago)}</div>')

    hero_css = _style('highlight_block_style', color, fallback=(
        f'background-color: {color}; border-radius: 14px; padding: 28px 28px 24px 28px;'
    ))
    tag_css = _style('top_story_tag_style', fallback=(
        'display: inline-block; background-color: rgba(255,255,255,0.18); color: #FFFFFF; '
        'padding: 5px 14px; border-radius: 20px; font-size: 11px; font-weight: 700; '
        'text-transform: uppercase; letter-spacing: 1px;'
    ))
    cta_css = _style('outline_button_style', white, fallback=(
        f'background-color: transparent; color: {white}; padding: 10px 20px; '
        f'border: 1.5px solid {white}; border-radius: 6px; font-weight: 700; '
        f'font-size: 13px; text-decoration: none; display: inline-block;'
    ))

    return (
        f'<tr><td class="polly-pad" style="padding: 0 40px 4px 40px;">'
        f'<div style="{hero_css}">'
        f'<div style="{tag_css}">{story.emoji} {_esc(story.section)} &middot; Today&rsquo;s Top Story</div>'
        f'<div style="font-size: 20px; font-weight: 800; color: {white}; line-height: 1.35; '
        f'font-family: {headline_font}; margin-top: 14px;">{_esc(item.title)}</div>'
        f'{time_ago_html}'
        f'<a href="{_esc(item.url)}" target="_blank" rel="noopener noreferrer" '
        f'style="{cta_css}; margin-top: 16px;">Read More ({_esc(item.outlet)}) &rarr;</a>'
        f'</div></td></tr>'
    )


def _bird_img(width: int, alt: str = "Polly") -> str:
    """Render the Polly bird mark as an email-safe <img>, sized proportionally from BIRD_LOGO_RATIO."""
    height = round(width / BIRD_LOGO_RATIO)
    return (f'<img src="{BIRD_LOGO_URL}" width="{width}" height="{height}" alt="{_esc(alt)}" '
            f'style="display:inline-block; vertical-align:middle; border:0; outline:none; max-width:{width}px;">')


def _brand_header() -> str:
    """Render the Polly wordmark with the bird mark as a hosted <img> (email-safe: no inline SVG)."""
    ink = _c('INK', '#0F172A')
    headline_font = _c('HEADLINE_FONT', 'Georgia, serif')

    return (
        '<table role="presentation" cellpadding="0" cellspacing="0" border="0"><tr>'
        '<td style="padding-right: 10px; vertical-align: middle;">'
        f'{_bird_img(46, alt="Polly")}'
        '</td>'
        '<td style="vertical-align: middle;">'
        f'<div style="font-size: 26px; font-weight: 900; color: {ink}; letter-spacing: -0.5px; font-family: {headline_font}; line-height: 1;">'
        'The Polly Brief</div>'
        '</td>'
        '</tr></table>'
    )


def _view_in_browser_link(view_url: str) -> str:
    """Render the 'View in browser' link shown at the top of the email, next
    to the date. Only rendered when a view_url is supplied (see
    generate_brief.py, which builds this from the day's published GitHub
    Pages copy of the brief) — omitted entirely, not shown broken, if no
    URL is available for a given run (e.g. --sample runs)."""
    muted = _c('MUTED', '#64748B')
    return (
        f'<div style="margin-top: 6px;">'
        f'<a href="{_esc(view_url)}" target="_blank" rel="noopener noreferrer" '
        f'style="font-size: 12px; color: {muted}; text-decoration: underline; font-weight: 600;">'
        f'View in browser</a></div>'
    )


def render_brief(pulse: HiringPulse, top_stories: list[TopStory], featured_jobs: list[JobPosting],
                 pr_story: Optional[TopStory] = None,
                 quote_text: str = None, quote_source: str = None, today: dt.date = None,
                 view_url: str = None, poliodds: Optional[PoliOdds] = None) -> str:
    """Generate the complete HTML email for The Polly Brief.

    pr_story: the PR & Comms Industry trade-press item from
    news_snapshot.get_pr_industry_story(), fetched and passed in SEPARATELY
    from top_stories. This is deliberate, not an oversight -- top_stories is
    the only list _pick_top_highlight() below scans for the day's hero/lead
    story, so keeping pr_story out of it structurally guarantees this
    section can never become the highlighted story, regardless of what the
    six news sections do or don't find that day. It renders as
    its own fixed block below Top Stories instead (or not at all, same
    silently-dropped-if-empty treatment as the other sections -- see
    remaining_stories below).

    view_url: absolute URL of this day's brief as published to GitHub
    Pages (docs/briefs/{date}.html). When provided, a 'View in browser'
    link is shown under the date in the header. When omitted (e.g. sample
    runs, or before Pages publishing is wired up), the link is simply not
    rendered rather than pointing somewhere that 404s.
    """
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
    # Exclude whichever story is already shown in the "Today's Top Story"
    # callout above (_top_highlight_block) -- without this, that same
    # story was also being repeated as the first entry in the Top Stories
    # list right below it, wasting space on a duplicate rather than
    # showing a sixth distinct story.
    #
    # Also exclude any section with no matching story at all (st.item is
    # None). These used to still get a row -- a topic badge followed by
    # "No story matched this section today." in italics -- which reads as
    # an unpolished, semi-technical message to land in a subscriber's
    # inbox. Dropping the row entirely means a slow news day for one
    # section (e.g. Media) just means four story cards instead of five,
    # not an apology. _story_block() keeps its own "no item" branch as a
    # defensive fallback, but this filter means that branch should no
    # longer be reachable from here.
    highlighted_story = _pick_top_highlight(top_stories)
    remaining_stories = [st for st in top_stories if st is not highlighted_story and st.item]

    if remaining_stories:
        for i, st in enumerate(remaining_stories):
            if i > 0:
                story_rows += _divider()
            story_rows += _story_block(st, today)
    else:
        story_rows = f'<tr><td style="{muted_default_css}">No other stories today.</td></tr>'

    # PR & Comms Industry -- rendered as its own fixed block, entirely
    # separate from top_stories/highlighted_story/remaining_stories above.
    # Never considered by _pick_top_highlight (it isn't in top_stories at
    # all), and dropped with no divider/heading at all on the rare day it
    # has no item -- same "no blank sections" treatment the other six
    # sections got, not the old italic "No story matched" placeholder.
    pr_story_section = ''
    if pr_story and pr_story.item:
        pr_story_section = (
            _divider() +
            '<tr><td class="polly-pad" style="padding: 0 40px">' +
            _section_heading("📢", "PR & Comms Industry") +
            '<table role="presentation" width="100%" cellpadding="0" cellspacing="0">' +
            _story_block(pr_story, today, show_badge=False) +
            '</table></td></tr>'
        )

    job_rows = ''
    for job in featured_jobs:
        job_rows += _featured_job_block(job)
    if not job_rows:
        job_rows = f'<tr><td style="{muted_default_css}">No featured jobs today.</td></tr>'

    jobs_cta = ''
    if featured_jobs:
        accent = _c('ACCENT', '#1E3A8A')
        cta_css = _style('outline_button_style', accent, fallback=(
            f'background-color: transparent; color: {accent}; padding: 10px 20px; '
            f'border: 1.5px solid {accent}; border-radius: 6px; font-weight: 700; '
            f'font-size: 13px; text-decoration: none; display: inline-block;'
        ))
        jobs_cta = (
            '<tr><td style="padding-top: 6px; text-align: center;">'
            f'<a href="https://jobs.thepolly.co/jobs" target="_blank" rel="noopener noreferrer" '
            f'style="{cta_css}">Explore all jobs on ThePolly.co &rarr;</a>'
            '</td></tr>'
        )

    quote_section = ''
    if quote_text:
        attribution = ''
        if quote_source:
            attribution = f'<div style="{muted_default_css}; margin-top: 10px">&mdash; {_esc(quote_source)}</div>'
        quote_section = (
            _divider() +
            f'<tr><td class="polly-pad" style="padding: 0 40px">'
            f'{_section_heading("💬", "Quote of the Day")}'
            f'<div style="font-size: 16px; font-weight: 600; color: {ink}; font-style: italic; line-height: 1.4">'
            f'&ldquo;{_esc(quote_text)}&rdquo;</div>{attribution}</td></tr>'
        )

    # Include pr_story in the word count / read-time estimate -- it's real
    # editorial content a reader reads top to bottom, same as the six
    # top_stories -- while still keeping it out of top_stories itself so it
    # stays ineligible for _pick_top_highlight() above.
    read_time_stories = list(top_stories) + ([pr_story] if pr_story else [])
    word_count, read_minutes = _estimate_read_time(read_time_stories, quote_text)
    read_time_label = f"{word_count:,} words, a {read_minutes}-min. read"

    days_left = _days_until_election(today)

    topic_colors = _c('TOPIC_COLORS', {})
    if not isinstance(topic_colors, dict):
        topic_colors = {}

    top_bar_gradient = (
        f"{topic_colors.get('Campaigns', '#2563EB')}, "
        f"{topic_colors.get('Media', '#059669')}, "
        f"{topic_colors.get('AI+Policy', '#7C3AED')}, "
        f"{topic_colors.get('Energy', '#D97706')}, "
        f"{topic_colors.get('Economy', '#15803D')}, "
        f"{topic_colors.get('Legislative', '#4F46E5')}"
    )

    parts = [
        '<!DOCTYPE html><html><head>',
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">',
        '<title>The Polly Brief</title>',
        _mobile_style_block(),
        '</head>',
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
        f'<table role="presentation" width="600" class="polly-card" cellpadding="0" cellspacing="0" style="background-color: {card}; border-radius: 14px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.06)">',
        f'<tr><td style="background-color: {accent}; background: linear-gradient(90deg, {top_bar_gradient}); height: 6px; line-height: 6px; font-size: 0">&nbsp;</td></tr>',
        '<tr><td class="polly-pad" style="padding: 32px 40px 20px 40px">',
        _brand_header(),
        f'<div style="font-size: 12px; color: {muted}; margin-top: 10px; letter-spacing: 0.3px; font-weight: 600;">{_esc(date_label)}</div>',
        f'<div style="font-size: 12px; color: {muted}; margin-top: 4px;">{_esc(read_time_label)}</div>',
        (_view_in_browser_link(view_url) if view_url else ''),
        '</td></tr>',
        _top_highlight_block(top_stories, today),
        _divider(),
        '<tr><td class="polly-pad" style="padding: 0 40px">',
        f'{_section_heading("📊", "Polly Hiring Pulse")}',
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin-bottom: 20px;"><tr>',
        _stat_block(f'{pulse.total_active:,}', 'Active Jobs', bg_color="#1E3A8A", url='https://jobs.thepolly.co/jobs'),
        _stat_block(str(pulse.new_today), 'New Today', bg_color="#2563EB", first=False),
        '</tr></table>',
        # Remote / Hybrid / Onsite stacked bar. Sits between the stat cards
        # and the category/employer columns -- it's a Hiring Pulse metric
        # like the others, not a separate section, so it shares the same
        # heading and doesn't get its own emoji/divider.
        f'<div style="margin-bottom: 20px;">{_subheading_label("Remote / Hybrid / Onsite")}{_location_mix_bar(pulse.location_mix)}</div>',
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>',
        '<td width="50%" valign="top" class="polly-col" style="padding-right: 20px">',
        _subheading_label("Top Hiring Categories"),
        f'<table role="presentation" cellpadding="0" cellspacing="0">{category_rows}</table></td>',
        '<td width="50%" valign="top" class="polly-col">',
        _subheading_label("Top Hiring Organizations"),
        f'<table role="presentation" cellpadding="0" cellspacing="0">{employer_rows}</table></td>',
        '</tr></table></td></tr>',
        # PoliOdds Watch -- dropped entirely (no heading, no divider) when
        # there's nothing usable, same "no blank sections" treatment as
        # PR & Comms Industry and the six news sections. odds.has_content
        # is already what poliodds_snapshot.get_poliodds() gates on before
        # returning non-None, but checked again here so this still
        # degrades safely if render_brief is ever called directly with a
        # PoliOdds that happens to be empty.
        (_divider() +
         '<tr><td class="polly-pad" style="padding: 0 40px">' +
         _section_heading("🎲", "PoliOdds Watch") +
         _poliodds_section(poliodds) +
         '</td></tr>') if (poliodds and poliodds.has_content) else '',
        _divider(),
        '<tr><td class="polly-pad" style="padding: 0 40px">',
        f'{_section_heading("📰", "Top Stories")}',
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0">{story_rows}</table>',
        '</td></tr>',
        pr_story_section,
        _divider(),
        '<tr><td class="polly-pad" style="padding: 0 40px">',
        f'{_section_heading("🔥", "Jobs Worth Looking At")}',
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0">{job_rows}{jobs_cta}</table>',
        '</td></tr>',
        _divider(),
        '<tr><td class="polly-pad" style="padding: 0 40px">',
        f'<div style="background-color: #0F172A; border-radius: 12px; padding: 24px; text-align: center">',
        f'{_section_heading("📅", "Election Countdown", color=white, gap=8)}',
        f'<div style="font-size: 44px; font-weight: 900; color: {white}; font-family: {headline_font}; letter-spacing: -1px; line-height: 1;">{days_left}</div>',
        f'<div style="font-size: 11px; color: #94A3B8; text-transform: uppercase; letter-spacing: 0.8px; margin-top: 8px; font-weight: 700;">Days Until Election Day</div>',
        '</div></td></tr>',
        quote_section,
        '<tr><td class="polly-pad" style="padding: 24px 40px 16px 40px; text-align: center">',
        f'<a href="https://thepolly.co" target="_blank" rel="noopener noreferrer" style="color: {muted}; text-decoration: none; font-size: 12px; font-weight: 600;">Know someone job hunting in politics? Invite them to Polly →</a>',
        '</td></tr>',
        '<tr><td class="polly-pad" style="padding: 16px 40px 36px 40px">',
        f'<div style="border-top: 1px solid {hairline}; padding-top: 18px; text-align: center">',
        f'<div style="font-size: 12px; font-weight: 700; color: {ink};">'
        f'{_bird_img(18, alt="")} '
        f'<span style="vertical-align:middle;">Powered by Pollyai</span>'
        f'</div>',
        f'<div style="font-size: 11px; color: {muted}; margin-top: 2px">The Talent Marketplace for Politics &amp; Public Affairs</div>',
        f'<div style="font-size: 11px; color: {muted}; margin-top: 10px">All rights reserved.</div>',
        '</div></td></tr>',
        '</table></td></tr></table></body></html>',
    ])

    return ''.join(parts)
