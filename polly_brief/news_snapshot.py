"""
News for The Polly Brief: one fresh, on-topic story per section, plus the
PR & Comms Industry item.

HOW STORIES ARE CHOSEN (rebuilt 2026-09-25 -- "no old news")
------------------------------------------------------------
The previous version ran one Google News *search* per section. Google
ranks search results by relevance, not recency, so the freshest on-topic
story often wasn't in the results at all, and the code then fell back to
anything up to 14, then 30 days old, then undated items. Readers got 4-,
10-, 11- and 21-day-old stories, plus off-topic matches (a Supreme Court
story under AI+Policy).

Now:
  1. SOURCES: each section reads several outlets' own RSS feeds
     (SECTION_FEEDS) -- only feeds confirmed to work; unconfirmed
     candidates are health-checked in the log (PENDING_FEEDS) but unused. Outlet feeds are in time order and carry real
     timestamps, and their links go straight to the publisher.
  2. FRESHNESS: stories from the last FRESH_HOURS (24) always come first;
     nothing older than MAX_AGE_HOURS (48) is ever used, and anything
     without a verifiable timestamp is dropped. If a section has nothing
     that fresh, it's left out of the brief -- never padded with old news.
  3. RELEVANCE: a headline must match its section's topic words
     (SECTION_TOPIC_PATTERNS), even from a section-specific feed -- outlet
     section feeds wander (The Hill's energy feed also carries mortgage-
     rate stories).
  4. IMPORTANCE: among fresh candidates, the story that other outlets are
     also covering wins ("coverage", counted across every feed fetched this
     run), so a section leads with the day's real story rather than
     whatever minor item was posted last. Ties go to the newest.
  5. BACKUP: only if a section's feeds yield nothing fresh and relevant is
     a Google News search tried -- under the same 48-hour rule.

Every feed prints a one-line diagnostic (entries, how many are within
24h/48h, newest age) so the workflow log shows exactly where each pick
came from.
"""
from __future__ import annotations

import datetime as dt
import json
import re
import time
from dataclasses import dataclass
from html import unescape
from pathlib import Path
from typing import Optional
from urllib.parse import quote_plus, urlparse
from zoneinfo import ZoneInfo

import feedparser
import requests
from bs4 import BeautifulSoup

HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; PollyBriefBot/1.0; +https://www.thepolly.co)'}
GOOGLE_NEWS_BASE = 'https://news.google.com/rss/search'
EASTERN = ZoneInfo('America/New_York')
FEED_TIMEOUT_SECONDS = 10
RETRY_PAUSE_SECONDS = 2

# ─────────────────────────────────────────────
# Freshness
# ─────────────────────────────────────────────
FRESH_HOURS = 24      # always preferred
MAX_AGE_HOURS = 48    # hard limit -- nothing older is ever shown

# ─────────────────────────────────────────────
# Sections and their sources
# ─────────────────────────────────────────────
# Display order of the six news sections (template.py renders them in this
# order, minus whichever story is promoted to the hero slot).
SECTIONS = [
    ('Campaigns', chr(0x1F5F3)),
    ('Media', chr(0x1F4FA)),
    ('AI+Policy', chr(0x1F916)),
    ('Energy', chr(0x26A1)),
    ('Economy', chr(0x1F4C8)),
    ('Legislative', chr(0x1F3DB)),
]

# (outlet display name, feed URL, beat). "beat" = the feed IS this
# section's beat (The Hill's campaign feed for Campaigns, Utility Dive for
# Energy): its items may pass the topic check on their summary as well as
# the headline, and win ties against general feeds. General feeds (NPR
# Politics, NBC Politics, Semafor, ...) must match on the headline itself.
#
# ACTIVE feeds only: every one was checked on 2026-09-25 to exist and post
# fresh items daily. Politico (politics, congress, energy, technology),
# CNBC, The Verge and Mediaite were confirmed by the first GitHub run's
# pending check the same day and promoted here. Politico's economy feed was dropped: that run found
# only 3 items, none within 48 hours.
_HILL = 'https://thehill.com'
_NPR_POLITICS = 'https://feeds.npr.org/1014/rss.xml'
_NBC_POLITICS = 'https://feeds.nbcnews.com/nbcnews/public/politics'
_CBS_POLITICS = 'https://www.cbsnews.com/latest/rss/politics'
_ABC_POLITICS = 'https://abcnews.com/abcnews/politicsheadlines'
_ROLL_CALL = 'https://rollcall.com/feed/'
_SEMAFOR = 'https://www.semafor.com/rss.xml'
SECTION_FEEDS = {
    'Campaigns': [
        ('The Hill', f'{_HILL}/homenews/campaign/feed/', True),
        ('Ballotpedia', 'https://news.ballotpedia.org/feed/', True),
        ('NBC News', _NBC_POLITICS, False),
        ('CBS News', _CBS_POLITICS, False),
        ('ABC News', _ABC_POLITICS, False),
        ('NPR', _NPR_POLITICS, False),
        ('Roll Call', _ROLL_CALL, False),
        ('Politico', 'https://rss.politico.com/politics-news.xml', False),
    ],
    'Media': [
        ('The Hill', f'{_HILL}/homenews/media/feed/', True),
        ('Poynter', 'https://www.poynter.org/feed/', True),
        ('Nieman Lab', 'https://www.niemanlab.org/feed/', True),
        ('Semafor', _SEMAFOR, False),
        ('Press Gazette', 'https://www.pressgazette.co.uk/feed/', False),
        # General, not beat: Mediaite mixes political commentary with media
        # news, so its headlines must name a media topic, and the beat feeds
        # above win ties. Very fresh (18 items within 24h on 2026-09-25).
        ('Mediaite', 'https://www.mediaite.com/feed/', False),
    ],
    'AI+Policy': [
        ('The Hill', f'{_HILL}/policy/technology/feed/', True),
        ('Politico', 'https://rss.politico.com/technology.xml', True),
        ('The Verge', 'https://www.theverge.com/rss/policy/index.xml', True),
        ('FedScoop', 'https://fedscoop.com/feed/', False),
        ('Nextgov', 'https://www.nextgov.com/rss/all/', False),
        ('NPR', 'https://feeds.npr.org/1019/rss.xml', False),
        ('NBC News', _NBC_POLITICS, False),
        ('Semafor', _SEMAFOR, False),
    ],
    'Energy': [
        ('The Hill', f'{_HILL}/policy/energy-environment/feed/', True),
        ('Utility Dive', 'https://www.utilitydive.com/feeds/news/', True),
        ('Politico', 'https://rss.politico.com/energy.xml', True),
        ('Canary Media', 'https://www.canarymedia.com/rss.rss', True),
        ('Inside Climate News', 'https://insideclimatenews.org/feed/', True),
        ('Grist', 'https://grist.org/feed/', False),
    ],
    'Economy': [
        ('The Hill', f'{_HILL}/business/feed/', True),
        ('NPR', 'https://feeds.npr.org/1017/rss.xml', True),
        ('CBS News', 'https://www.cbsnews.com/latest/rss/moneywatch', True),
        ('NBC News', 'https://feeds.nbcnews.com/nbcnews/public/business', True),
        ('CNBC', 'https://www.cnbc.com/id/20910258/device/rss/rss.html', True),
        ('Fortune', 'https://fortune.com/feed/fortune-feeds/?id=3230629', False),
        ('Semafor', _SEMAFOR, False),
    ],
    'Legislative': [
        ('Roll Call', _ROLL_CALL, True),
        ('The Hill', f'{_HILL}/homenews/house/feed/', True),
        ('The Hill', f'{_HILL}/homenews/senate/feed/', True),
        ('Politico', 'https://rss.politico.com/congress.xml', True),
        ('NPR', _NPR_POLITICS, False),
        ('NBC News', _NBC_POLITICS, False),
        ('CBS News', _CBS_POLITICS, False),
        ('ABC News', _ABC_POLITICS, False),
    ],
}

# Candidate feeds NOT yet confirmed (they block the sandbox's checking
# tool). Every run fetches them and logs a "[pending check]" line -- OK
# with item counts, or FAILED -- but their stories are never used. Once a
# log shows one is OK, move it into SECTION_FEEDS above (section, beat).
PENDING_FEEDS = [
    # Empty: every candidate so far has been confirmed or rejected. Add a
    # new feed here first, as ('Outlet', 'url'), to test it for a run.
]

# Headline topic check, per section. A candidate's headline must match its
# section's pattern (case-insensitive, whole words; "\w*" marks a stem).
# "White House" is masked before matching (see _topic_text) so it never
# counts as "House" for Legislative.
SECTION_TOPIC_PATTERNS = {
    'Campaigns': (
        r"campaign\w*|election\w*|primar(?:y|ies)|midterms?|ballots?|voters?|voting|"
        r"polls?|polling|pollsters?|candidates?|endorse\w*|super pac|"
        r"fundrais\w*|donors?|debates?|turnout|rnc|dnc|running mate|ticket|swing states?|"
        r"battleground\w*|governor'?s race|senate race|house race|race for|reelection|"
        r"re-election|redistricting|gerrymander\w*|attack ads?|campaign ads?|presidential|"
        r"hopefuls?|2028|races?|incumbents?|challengers?|seats?|governor"
    ),
    'Media': (
        r"media|journalis\w*|newsrooms?|reporters?|press|broadcast\w*|television|tv|cable|"
        r"networks?|anchors?|editors?|publishers?|newspapers?|podcast\w*|streaming|streamers?|"
        r"hollywood|studios?|films?|movies?|box office|late-night|talk show|ratings|viewers?|"
        r"viewership|fcc|first amendment|free speech|censor\w*|misinformation|disinformation|"
        r"social media|paywall|subscribers?|cnn|msnbc|ms now|fox news|abc|cbs|nbc|npr|pbs|"
        r"new york times|washington post|wall street journal|press corps|press pool|kimmel|"
        r"colbert|paramount|warner bros\w*|disney|netflix|comcast|tiktok|youtube|financial times|"
        r"bbc|the guardian|reuters|associated press|axios|politico|substack"
    ),
    'AI+Policy': (
        r"ai|a\.i\.|artificial intelligence|chatbots?|openai|anthropic|chatgpt|deepfakes?|"
        r"machine learning|large language models?|llms?|generative|data centers?|nvidia|"
        r"semiconductors?|chips?|algorithm\w*|automation|robot\w*|big tech|tech giants?|"
        r"superintelligence|agi|genai"
    ),
    'Energy': (
        r"energy|epa|climate|power plants?|power grid|grids?|electric\w*|utilit(?:y|ies)|solar|"
        r"wind|renewabl\w*|emissions?|fossil fuels?|oil|natural gas|gas prices|gasoline|diesel|"
        r"lng|drilling|pipelines?|nuclear|coal|batter(?:y|ies)|lithium|carbon|greenhouse|"
        r"wildfires?|drought|heat waves?|ferc|transmission|permitting|department of energy|doe|"
        r"crude|opec|refiner\w*|evs?|clean energy|offshore|hydropower|geothermal|power generat\w*|power sector"
    ),
    'Economy': (
        r"econom\w*|inflation|jobs report|jobless|unemployment|employment|payrolls?|hiring|"
        r"layoffs?|wages?|fed|federal reserve|interest rates?|rate cuts?|rate hikes?|"
        r"mortgages?|gdp|recession|tariffs?|trade war|trade deal|trade deficit|stocks?|"
        r"markets?|wall street|dow|s&p|nasdaq|treasur(?:y|ies)|bonds?|yields?|prices|"
        r"consumers?|spending|deficit|debt|budget|tax(?:es)?|bessent|powell|housing|rents?|"
        r"affordab\w*|dividends?|banks?|banking|crypto\w*|bitcoin|earnings|retail\w*|"
        r"manufactur\w*|farmers?|supply chains?|imports?|exports?|social security|retirement|medicare costs?"
    ),
    'Legislative': (
        r"congress\w*|senate|senators?|house|lawmakers?|legislat\w*|bills?|votes?|voted|"
        r"committee|subcommittee|appropriat\w*|spending bill|funding|shutdown|filibuster|"
        r"speaker|caucus|markup|hearings?|confirmation|confirmed|resolution|amendment|"
        r"capitol hill|thune|schumer|jeffries|mike johnson|cloture|stopgap|continuing resolution"
    ),
}
_TOPIC_RE = {name: re.compile(rf"\b(?:{pat})\b", re.IGNORECASE)
             for name, pat in SECTION_TOPIC_PATTERNS.items()}


def _topic_text(headline: str) -> str:
    """Headline prepared for topic matching: 'White House' masked so it
    can't count as the chamber."""
    return re.sub(r"white house", "whitehouse", headline, flags=re.IGNORECASE)


def _is_on_topic(headline: str, section: str, summary: str = '') -> bool:
    """Headline matches the section's topic words -- or, when a summary is
    passed (beat feeds only), the summary does."""
    pattern = _TOPIC_RE.get(section)
    if pattern is None:
        return True
    return bool(pattern.search(_topic_text(headline)) or
                (summary and pattern.search(_topic_text(summary))))


# Backup Google News queries (used only when a section's feeds yield
# nothing fresh and on-topic). Restricted to trusted outlets.
SECTION_BACKUP_QUERIES = {
    'Campaigns': 'campaign election midterm candidates',
    'Media': 'news media journalists networks press',
    'AI+Policy': 'artificial intelligence policy regulation',
    'Energy': 'energy policy EPA power grid',
    'Economy': 'economy inflation jobs Federal Reserve markets',
    'Legislative': 'Congress Senate House vote bill',
}
_FREE_SOURCES_INNER = (
    'site:axios.com OR site:politico.com OR site:punchbowl.news '
    'OR site:semafor.com OR site:apnews.com OR site:thehill.com '
    'OR site:npr.org OR site:notus.org OR site:nbcnews.com OR site:cnn.com '
    'OR site:pbs.org OR site:bbc.com OR site:csmonitor.com '
    'OR site:govexec.com OR site:stateline.org OR site:rollcall.com'
)
_MEDIA_TRADE_INNER = (
    'site:variety.com OR site:hollywoodreporter.com OR site:deadline.com '
    'OR site:adweek.com OR site:niemanlab.org OR site:cjr.org OR site:thewrap.com '
    'OR site:poynter.org'
)
BACKUP_SOURCES = f'({_FREE_SOURCES_INNER})'
BACKUP_SOURCE_OVERRIDES = {'Media': f'({_FREE_SOURCES_INNER} OR {_MEDIA_TRADE_INNER})'}

# Google sometimes labels a source by its bare domain; map those to names.
SOURCE_NAME_MAP = {
    'axios.com': 'Axios', 'politico.com': 'Politico', 'punchbowl.news': 'Punchbowl News',
    'semafor.com': 'Semafor', 'apnews.com': 'AP', 'thehill.com': 'The Hill', 'npr.org': 'NPR',
    'rollcall.com': 'Roll Call', 'notus.org': 'NOTUS', 'nbcnews.com': 'NBC News', 'cnn.com': 'CNN',
    'pbs.org': 'PBS', 'bbc.com': 'BBC', 'csmonitor.com': 'The Christian Science Monitor',
    'govexec.com': 'Government Executive', 'stateline.org': 'Stateline', 'variety.com': 'Variety',
    'hollywoodreporter.com': 'The Hollywood Reporter', 'deadline.com': 'Deadline',
    'adweek.com': 'Adweek', 'niemanlab.org': 'Nieman Lab', 'cjr.org': 'Columbia Journalism Review',
    'thewrap.com': 'TheWrap', 'poynter.org': 'Poynter',
}


def _normalize_source_name(source: str) -> str:
    key = source.strip().lower()
    if key.startswith('www.'):
        key = key[4:]
    return SOURCE_NAME_MAP.get(key, source)


# ─────────────────────────────────────────────
# PR & Comms industry section
# ─────────────────────────────────────────────
# Read from two PR trade publications' own feeds. Kept out of
# get_top_stories() on purpose: template.py only picks the hero story from
# that list, so the PR item can never become the day's lead. Same 48-hour
# freshness rule as every other section.
PR_TRADE_PRESS_SECTION_NAME = 'PR & Comms Industry'
PR_TRADE_PRESS_EMOJI = chr(0x1F4E2)  # 📢
PR_TRADE_PRESS_SOURCES = [
    # (display name, feed URL, requires keyword filter)
    ('PRovoke Media', 'https://www.provokemedia.com/newsfeed/provoke-media-latest', False),
    ('PRWeek', 'http://feeds.feedburner.com/PrweekUsNews', True),
]
PR_TRADE_PRESS_KEYWORDS = [
    'hires', 'hire', 'hired', 'names', 'appoints', 'appointed', 'promotes',
    'promoted', 'joins', 'taps', 'names ceo', 'names cco', 'names chief',
    'steps down', 'to leave', 'to exit', 'leaves', 'departs', 'exits',
    'account win', 'wins account', 'acquires', 'acquisition', 'merger',
    'merges', 'launches agency', 'agency of record', ' aor ',
]

# ─────────────────────────────────────────────
# Cross-day memory (don't repeat a story a section already ran)
# ─────────────────────────────────────────────
# Per section, url -> date last shown; committed by the workflow. With the
# 48-hour window this simply means "yesterday's pick can't run again today"
# -- the next freshest story is used instead, never an older one.
RECENT_STORIES_PATH = Path(__file__).resolve().parent / ".state" / "recent_stories.json"
RECENT_STORIES_RETENTION_DAYS = 21


def _safe_parse_date(date_str: str) -> Optional[dt.date]:
    try:
        return dt.date.fromisoformat(date_str)
    except (ValueError, TypeError):
        return None


def _load_recent_stories(path: Path = RECENT_STORIES_PATH) -> dict:
    """section -> {url: date shown}. Missing/corrupt file = nothing on
    record (worst case a story repeats once; never crash the brief)."""
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text()).get("sections", {})
    except (json.JSONDecodeError, OSError):
        return {}


def _excluded_urls_for_section(sections: dict, section: str, today: dt.date) -> set:
    cutoff = today - dt.timedelta(days=RECENT_STORIES_RETENTION_DAYS)
    return {url for url, d in sections.get(section, {}).items()
            if (parsed := _safe_parse_date(d)) is not None and parsed >= cutoff}


def _save_recent_stories(sections: dict, today: dt.date, path: Path = RECENT_STORIES_PATH) -> None:
    cutoff = today - dt.timedelta(days=RECENT_STORIES_RETENTION_DAYS)
    pruned = {}
    for section, url_to_date in sections.items():
        kept = {u: d for u, d in url_to_date.items()
                if (parsed := _safe_parse_date(d)) is not None and parsed >= cutoff}
        if kept:
            pruned[section] = kept
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"sections": pruned}, indent=2))


# ─────────────────────────────────────────────
# Filters: placeholder titles, opinion pieces
# ─────────────────────────────────────────────
GENERIC_TITLE_BLOCKLIST = {
    'headlines', 'headline', 'news', 'latest', 'latest news', 'top stories',
    'home', 'homepage', 'morning edition', 'all things considered',
    'weekend edition', 'weekend edition saturday', 'weekend edition sunday',
    'here and now', 'the daily', 'up first', '1a', 'marketplace', 'fresh air',
    'on point', 'the takeaway',
}
GENERIC_TITLE_SUBSTRING_BLOCKLIST = ('breaking news', 'latest news today', 'news: breaking news')


def _is_generic_title(title: str) -> bool:
    normalized = title.strip().lower()
    return normalized in GENERIC_TITLE_BLOCKLIST or any(
        phrase in normalized for phrase in GENERIC_TITLE_SUBSTRING_BLOCKLIST)


# Opinion/column pieces are excluded by URL path: the brief reports news,
# and an op-ed presented as "today's news" reads as taking a side.
OPINION_URL_MARKERS = (
    '/opinion/', '/opinions/', '/oped/', '/op-ed/', '/editorial/',
    '/editorials/', '/commentary/', '/blogs/congress-blog/',
)
MAX_BACKUP_OPINION_CHECKS = 4  # redirect lookups per section, backup search only


def _is_opinion_url(url: str) -> bool:
    path = urlparse(url).path.lower()
    return any(marker in path for marker in OPINION_URL_MARKERS)


def _resolve_final_url(link: str, timeout: float = 6.0) -> Optional[str]:
    """Follow a Google News redirect to the publisher URL (backup search
    only -- direct feed links are already publisher URLs). None on failure,
    which the caller treats as "couldn't verify", not "is opinion"."""
    try:
        resp = requests.get(link, headers=HEADERS, timeout=timeout, allow_redirects=True, stream=True)
        resp.close()
        return resp.url
    except Exception:
        return None


# ─────────────────────────────────────────────
# Data types
# ─────────────────────────────────────────────
@dataclass
class NewsItem:
    outlet: str
    title: str
    url: str
    summary: str
    # Publish date in Eastern time (drives "Today"/"Yesterday" in the brief).
    published_date: Optional[dt.date] = None
    # How many OTHER outlets ran the same story in this run's feeds -- the
    # "importance" signal. template.py uses it to pick the hero story.
    coverage: int = 0


@dataclass
class TopStory:
    section: str
    emoji: str
    item: Optional[NewsItem]


@dataclass
class _Entry:
    outlet: str
    title: str
    url: str
    summary: str
    published: dt.datetime  # timezone-aware, UTC
    feed_url: str = ''


# ─────────────────────────────────────────────
# Text helpers
# ─────────────────────────────────────────────
def _clean_html(raw_html):
    if not raw_html:
        return ''
    text = BeautifulSoup(unescape(raw_html), 'html.parser').get_text(separator=' ').strip()
    return re.sub(r'\s+', ' ', text)


def _split_title_source(raw_title):
    """Google News titles are "Headline - Source"; split on the LAST " - "."""
    if ' - ' in raw_title:
        headline, source = raw_title.rsplit(' - ', 1)
        return headline.strip(), _normalize_source_name(source.strip())
    return raw_title.strip(), 'Google News'


SUMMARY_MAX_CHARS = 220


def _summary_from_description(raw_html, max_sentences=2, title: str = ''):
    """First sentence or two of a feed item's description, without
    WordPress boilerplate, capped at SUMMARY_MAX_CHARS. Empty if it would
    just repeat the headline."""
    text = _clean_html(raw_html)
    text = re.sub(r'\s*The post .*? appeared first on .*$', '', text)
    text = re.sub(r'\s*(Continue reading|Read more)\s*(\.\.\.|…|»)?\s*$', '', text, flags=re.IGNORECASE)
    if not text:
        return ''
    sentences = re.split(r'(?<=[.!?])\s+', text)
    summary = ' '.join(sentences[:max_sentences]).strip()
    if len(summary) > SUMMARY_MAX_CHARS:
        summary = summary[:SUMMARY_MAX_CHARS].rsplit(' ', 1)[0].rstrip(',;:') + '…'
    if title and summary.lower().rstrip('.…') == title.lower().rstrip('.…'):
        return ''
    return summary


_TOKEN_STOPWORDS = {
    'trump', 'trumps', 'biden', 'whitehouse', 'white', 'house', 'senate', 'congress',
    'president', 'says', 'said', 'over', 'after', 'amid', 'could', 'would', 'will',
    'with', 'from', 'that', 'this', 'they', 'their', 'them', 'about', 'into', 'more',
    'than', 'what', 'when', 'where', 'which', 'while', 'against', 'ahead', 'before',
    'first', 'last', 'year', 'years', 'week', 'weeks', 'report', 'reports', 'news',
    'live', 'update', 'updates', 'here', 'there', 'just', 'only', 'still', 'also',
    'back', 'down', 'make', 'makes', 'made', 'take', 'takes', 'calls', 'call', 'gets',
    'plan', 'plans', 'push', 'pushes', 'talks', 'deal', 'americans', 'american',
    'state', 'states', 'federal', 'government', 'officials', 'official', 'people',
    'says', 'new', 'how', 'why', 'who', 'amid', 'being', 'been', 'have', 'has', 'were',
    'your', 'some', 'most', 'many', 'much', 'very', 'like', 'next', 'time', 'days',
    'republicans', 'democrats', 'republican', 'democratic', 'gop',
}


def _tokens(headline: str) -> set:
    words = re.findall(r"[a-z][a-z'\-]{3,}", _topic_text(headline).lower())
    return {w.removesuffix("'s").strip("'-") for w in words} - _TOKEN_STOPWORDS


def _same_story(a: set, b: set) -> bool:
    """Two headlines' significant-word sets describe the same story."""
    overlap = len(a & b)
    return overlap >= 3 or (overlap >= 2 and overlap >= 0.6 * min(len(a), len(b)))


def _entry_datetime(entry) -> Optional[dt.datetime]:
    """Publish time as an aware UTC datetime (feedparser normalizes feed
    timestamps to UTC). None if the item carries no usable timestamp --
    such items are dropped, since their freshness can't be verified."""
    struct = getattr(entry, 'published_parsed', None) or getattr(entry, 'updated_parsed', None)
    if not struct:
        return None
    try:
        return dt.datetime(*struct[:6], tzinfo=dt.timezone.utc)
    except (TypeError, ValueError):
        return None


def _age_hours(published: dt.datetime, now: dt.datetime) -> float:
    return (now - published).total_seconds() / 3600


def _eastern_date(published: dt.datetime) -> dt.date:
    return published.astimezone(EASTERN).date()


# ─────────────────────────────────────────────
# Fetching
# ─────────────────────────────────────────────
def _get_with_retry(url: str):
    """GET with one retry after a short pause on a connection error or
    timeout -- the first live run lost NPR's technology feed to a one-off
    "connection reset by peer" while NPR's other feeds loaded fine. HTTP
    errors (404, 403) aren't retried; they won't fix themselves in a second."""
    try:
        return requests.get(url, headers=HEADERS, timeout=FEED_TIMEOUT_SECONDS)
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        time.sleep(RETRY_PAUSE_SECONDS)
        return requests.get(url, headers=HEADERS, timeout=FEED_TIMEOUT_SECONDS)


def _fetch_feed(outlet: str, url: str, now: dt.datetime, cache: dict, label: str = '') -> list:
    """All timestamped, non-placeholder, non-opinion items from one feed that
    are within MAX_AGE_HOURS. Cached per URL for the run (several sections
    share feeds). Any failure returns [] -- one bad feed never breaks the
    brief."""
    if url in cache:
        return cache[url]
    entries, status, raw_count = [], None, 0
    try:
        resp = _get_with_retry(url)
        status = resp.status_code
        resp.raise_for_status()
        parsed = feedparser.parse(resp.content)
        raw_count = len(parsed.entries)
        for e in parsed.entries:
            title = _clean_html(getattr(e, 'title', ''))
            link = getattr(e, 'link', '').strip()
            published = _entry_datetime(e)
            if not title or not link or published is None:
                continue
            if _is_generic_title(title) or _is_opinion_url(link):
                continue
            if _age_hours(published, now) > MAX_AGE_HOURS or _age_hours(published, now) < -2:
                continue  # too old, or a bogus future timestamp
            summary = _summary_from_description(
                getattr(e, 'summary', '') or getattr(e, 'description', ''), title=title)
            entries.append(_Entry(outlet, title, link, summary, published, url))
    except Exception as exc:
        print(f'    [news] {outlet} {label}: FAILED ({type(exc).__name__}: {exc}) status={status}')
        cache[url] = []
        return []
    fresh = sum(1 for e in entries if _age_hours(e.published, now) <= FRESH_HOURS)
    newest = min((_age_hours(e.published, now) for e in entries), default=None)
    newest_txt = f'{newest:.0f}h' if newest is not None else '-'
    print(f'    [news] {outlet} {label}: {raw_count} items, {fresh} within {FRESH_HOURS}h, '
          f'{len(entries)} within {MAX_AGE_HOURS}h, newest {newest_txt} old')
    cache[url] = entries
    return entries


def _fetch_backup(section: str, now: dt.datetime) -> list:
    """Google News backup search for one section, same 48-hour rule. Links
    are Google redirects, so the opinion check resolves the real URL for
    the few candidates actually considered."""
    sources = BACKUP_SOURCE_OVERRIDES.get(section, BACKUP_SOURCES)
    query = f'{SECTION_BACKUP_QUERIES[section]} {sources}'
    url = f'{GOOGLE_NEWS_BASE}?q={quote_plus(query)}&hl=en-US&gl=US&ceid=US:en'
    try:
        resp = requests.get(url, headers=HEADERS, timeout=FEED_TIMEOUT_SECONDS)
        resp.raise_for_status()
        parsed = feedparser.parse(resp.content)
    except Exception as exc:
        print(f'    [news] {section} backup search FAILED ({type(exc).__name__}: {exc})')
        return []
    entries = []
    for e in parsed.entries:
        raw_title = getattr(e, 'title', '').strip()
        link = getattr(e, 'link', '').strip()
        published = _entry_datetime(e)
        if not raw_title or not link or published is None:
            continue
        if not (-2 <= _age_hours(published, now) <= MAX_AGE_HOURS):
            continue
        headline, outlet = _split_title_source(raw_title)
        if _is_generic_title(headline):
            continue
        entries.append(_Entry(outlet, headline, link, '', published))
    print(f'    [news] {section} backup search: {len(parsed.entries)} items, {len(entries)} within {MAX_AGE_HOURS}h')
    return entries


# ─────────────────────────────────────────────
# Selection
# ─────────────────────────────────────────────
def _coverage(entry: _Entry, pool: list) -> int:
    """Number of OTHER outlets in this run's feeds carrying the same story."""
    mine = _tokens(entry.title)
    if len(mine) < 2:
        return 0
    outlets = {other.outlet for other in pool
               if other.outlet != entry.outlet and _same_story(mine, _tokens(other.title))}
    return len(outlets)


def _pick(candidates: list, pool: list, now: dt.datetime, beat_urls: set = frozenset()) -> Optional[tuple]:
    """Best candidate, ranked by: within 24h first; then most-covered
    (capped, so a huge story doesn't need endless coverage to win); then
    from one of the section's own beat feeds; then newest.
    Returns (entry, coverage) or None."""
    if not candidates:
        return None
    scored = [(c, _coverage(c, pool)) for c in candidates]
    scored.sort(key=lambda s: (_age_hours(s[0].published, now) <= FRESH_HOURS,
                               min(s[1], 3), s[0].feed_url in beat_urls, s[0].published),
                reverse=True)
    return scored[0]


def _eligible(entries: list, section: str, excluded: set, picked_titles: list,
              beat_urls: set = frozenset()) -> list:
    """On-topic, not shown by this section recently, not already used
    (same URL or same story) by another section today. De-duplicated by
    URL (feeds overlap)."""
    seen, out = set(), []
    for e in entries:
        if e.url in seen or e.url in excluded:
            continue
        seen.add(e.url)
        if not _is_on_topic(e.title, section, e.summary if e.feed_url in beat_urls else ''):
            continue
        toks = _tokens(e.title)
        if any(_same_story(toks, t) for t in picked_titles):
            continue
        out.append(e)
    return out


def get_top_stories(per_outlet=100, today: Optional[dt.date] = None,
                    now: Optional[dt.datetime] = None):
    """One TopStory per section in SECTIONS order; item is None when the
    section has nothing fresh (within MAX_AGE_HOURS) and on-topic -- the
    template then leaves that section out. per_outlet is accepted for
    compatibility with generate_brief.py and no longer used."""
    now = now or dt.datetime.now(dt.timezone.utc)
    today = today or now.astimezone(EASTERN).date()
    sections_data = _load_recent_stories()
    cache: dict = {}

    # Fetch everything first: the coverage count compares each candidate
    # against every outlet's headlines, not just its own section's.
    by_section = {name: [e for outlet, url, _beat in SECTION_FEEDS[name]
                         for e in _fetch_feed(outlet, url, now, cache, label=f'[{name}]')]
                  for name, _ in SECTIONS}
    beat_urls = {name: {url for _o, url, beat in SECTION_FEEDS[name] if beat}
                 for name, _ in SECTIONS}
    pool = [e for entries in cache.values() for e in entries]

    # Log-only health check of not-yet-confirmed feeds (never used for picks,
    # and kept out of `pool` so they can't affect coverage either).
    pending_cache: dict = {}
    for outlet, url in PENDING_FEEDS:
        _fetch_feed(outlet, url, now, pending_cache,
                    label=f'[pending check {urlparse(url).netloc}{urlparse(url).path}]')

    stories, same_day_urls, picked_titles = [], set(), []
    for name, emoji in SECTIONS:
        excluded = _excluded_urls_for_section(sections_data, name, today) | same_day_urls
        choice = _pick(_eligible(by_section[name], name, excluded, picked_titles, beat_urls[name]),
                       pool, now, beat_urls[name])
        source = 'feeds'
        if choice is None:
            backup = _eligible(_fetch_backup(name, now), name, excluded, picked_titles)
            backup.sort(key=lambda e: e.published, reverse=True)
            checks = 0
            for e in backup:
                if checks >= MAX_BACKUP_OPINION_CHECKS:
                    break
                checks += 1
                final = _resolve_final_url(e.url)
                if final is None or not _is_opinion_url(final):
                    choice, source = (e, _coverage(e, pool)), 'backup search'
                    break
        item = None
        if choice:
            entry, cov = choice
            item = NewsItem(outlet=entry.outlet, title=entry.title, url=entry.url,
                            summary=entry.summary, published_date=_eastern_date(entry.published),
                            coverage=cov)
            same_day_urls.add(entry.url)
            picked_titles.append(_tokens(entry.title))
            sections_data.setdefault(name, {})[entry.url] = today.isoformat()
            print(f'    [news] {name}: picked ({source}) {entry.outlet}, '
                  f'{_age_hours(entry.published, now):.0f}h old, covered by {cov} other outlet(s)')
        else:
            print(f'    [news] {name}: nothing fresh and on-topic -- section left out today')
        stories.append(TopStory(section=name, emoji=emoji, item=item))

    _save_recent_stories(sections_data, today)
    return stories


def get_pr_industry_story(today: Optional[dt.date] = None,
                          now: Optional[dt.datetime] = None) -> TopStory:
    """Newest PR/comms-industry trade-press item within MAX_AGE_HOURS
    (agency hires, promotions, account wins, mergers). item is None if
    neither feed has anything that fresh."""
    now = now or dt.datetime.now(dt.timezone.utc)
    today = today or now.astimezone(EASTERN).date()
    sections_data = _load_recent_stories()
    excluded = _excluded_urls_for_section(sections_data, PR_TRADE_PRESS_SECTION_NAME, today)

    cache: dict = {}
    candidates = []
    for outlet, feed_url, require_keyword in PR_TRADE_PRESS_SOURCES:
        for e in _fetch_feed(outlet, feed_url, now, cache, label='[PR]'):
            if require_keyword and not any(kw in f' {e.title.lower()} ' for kw in PR_TRADE_PRESS_KEYWORDS):
                continue
            if e.url not in excluded:
                candidates.append(e)
    candidates.sort(key=lambda e: e.published, reverse=True)

    item = None
    if candidates:
        e = candidates[0]
        item = NewsItem(outlet=e.outlet, title=e.title, url=e.url, summary=e.summary,
                        published_date=_eastern_date(e.published))
        sections_data.setdefault(PR_TRADE_PRESS_SECTION_NAME, {})[item.url] = today.isoformat()
        _save_recent_stories(sections_data, today)
    return TopStory(section=PR_TRADE_PRESS_SECTION_NAME, emoji=PR_TRADE_PRESS_EMOJI, item=item)


if __name__ == '__main__':
    # Dry run: prints every feed's freshness line and each section's pick.
    # Note: records the picks in .state/recent_stories.json like a real run.
    for story in get_top_stories() + [get_pr_industry_story()]:
        it = story.item
        print(f'{story.section:22} {("(none)" if not it else f"{it.outlet}: {it.title}")}')
