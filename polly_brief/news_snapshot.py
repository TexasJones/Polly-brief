from __future__ import annotations
import datetime as dt
import re
from dataclasses import dataclass
from html import unescape
from typing import Optional
import feedparser
from bs4 import BeautifulSoup
HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; PollyBriefBot/1.0; +https://www.thepolly.co)'}
GOOGLE_NEWS_BASE = 'https://news.google.com/rss/search'
# One targeted search query per topic instead of maintaining individual
# outlet RSS feeds. This sidesteps broken/guessed outlet URLs entirely and
# guarantees on-topic results, since we're searching for the topic directly
# rather than filtering a general political-news pool after the fact.
#
# Finance vs Economy: these used to be blended into one "Finance" query
# (campaign finance + Federal Reserve policy), which meant only one of the
# two ever won the single daily slot. Split into two distinct, non-
# overlapping queries so both get real coverage: Finance is money IN
# politics (fundraising, PACs, dark money); Economy is the macro picture
# (jobs, markets, inflation, the Fed) that affects the political landscape
# but isn't itself campaign finance.
SECTION_QUERIES = [
    ('Campaigns', chr(0x1F5F3), 'political campaign primary election'),
    ('Media', chr(0x1F4FA), 'media industry journalism press freedom'),
    ('AI+Policy', chr(0x1F916), 'artificial intelligence policy regulation Congress'),
    ('Energy', chr(0x26A1), 'energy policy EPA regulation'),
    ('Finance', chr(0x1F4B0), 'campaign finance PAC fundraising dark money'),
    ('Economy', chr(0x1F4C8), 'jobs report unemployment stock market inflation economy'),
    ('Legislative', chr(0x1F3DB), 'Congress legislation bill'),
]

# Freshness ceiling for a "top story." Search windows below widen up to
# this same number and then stop -- previously the last resort was an
# unrestricted search (no `when:` operator at all), which let Google's
# plain relevance ranking hand back a months-old piece on any topic having
# a quiet news day. Every entry's own published date is now also checked
# against this same cutoff (see _entry_published_date), independent of
# which search window it came from -- Google's `when:` operator biases the
# search, but it isn't a hard guarantee, so a stale entry can still slip
# into an otherwise-recent window and needs to be caught here too.
MAX_STORY_AGE_DAYS = 14

# Widens in stages so a quiet-news-day topic still gets *something* recent
# rather than immediately falling back to a looser match, but never
# reaches further than MAX_STORY_AGE_DAYS.
SEARCH_WINDOWS = ('when:1d', 'when:3d', 'when:7d', 'when:14d')


@dataclass
class NewsItem:
    outlet: str
    title: str
    url: str
    summary: str
@dataclass
class TopStory:
    section: str
    emoji: str
    item: Optional[NewsItem]
def _clean_html(raw_html):
    if not raw_html:
        return ''
    text = BeautifulSoup(unescape(raw_html), 'html.parser').get_text(separator=' ').strip()
    return re.sub(r'\s+', ' ', text)
def _split_title_source(raw_title):
    # Google News formats titles as "Headline - Source Name". Split on the
    # LAST " - " so headlines that themselves contain a hyphen don't get
    # cut in the wrong place.
    if ' - ' in raw_title:
        headline, source = raw_title.rsplit(' - ', 1)
        return headline.strip(), source.strip()
    return raw_title.strip(), 'Google News'
def _summary_from_description(raw_html, max_sentences=2):
    text = _clean_html(raw_html)
    if not text:
        return ''
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return ' '.join(sentences[:max_sentences]).strip()


def _entry_published_date(entry) -> Optional[dt.date]:
    """Pull the entry's own publish date out of feedparser's parsed struct,
    independent of whatever `when:` window the search itself used. Checks
    `published_parsed` first, falling back to `updated_parsed` since not
    every feed populates both. Returns None if neither is present or
    parseable -- that's treated as "can't verify this is fresh" by the
    caller, not as "assume it's fine," since the whole point here is not
    trusting an unverified date."""
    struct = getattr(entry, 'published_parsed', None) or getattr(entry, 'updated_parsed', None)
    if not struct:
        return None
    try:
        return dt.date(struct.tm_year, struct.tm_mon, struct.tm_mday)
    except (TypeError, ValueError):
        return None


def _fetch_topic_story(query, limit=5, today: Optional[dt.date] = None):
    # Plain relevance search with no freshness filter can surface a
    # month-old "roundup" piece over anything from today, since Google
    # ranks by topical match, not recency. The `when:` search operator
    # restricts results to a rolling window; try the tightest window
    # first and only widen if that comes up empty, so sections don't
    # start going blank on quieter news days just to stay fresh.
    #
    # Widening now stops at SEARCH_WINDOWS' last entry (14 days) rather
    # than ever dropping the `when:` operator entirely -- see
    # MAX_STORY_AGE_DAYS above for why an unbounded fallback was the
    # actual source of multi-week-old stories getting through.
    today = today or dt.date.today()

    for window in SEARCH_WINDOWS:
        windowed_query = f'{query} {window}'
        url = f'{GOOGLE_NEWS_BASE}?q={windowed_query.replace(" ", "+")}&hl=en-US&gl=US&ceid=US:en'
        parsed = feedparser.parse(url, request_headers=HEADERS)
        for entry in parsed.entries[:limit]:
            raw_title = getattr(entry, 'title', '').strip()
            link = getattr(entry, 'link', '').strip()
            if not raw_title or not link:
                continue

            # Verify the entry's own date rather than trusting the `when:`
            # window alone -- Google's search-time freshness filter isn't
            # a hard guarantee, so a stale entry can still show up inside
            # a nominally "recent" window. An entry with no parseable date
            # at all is skipped too, same reasoning: we can't call
            # something "today's news" if we can't confirm when it ran.
            pub_date = _entry_published_date(entry)
            if pub_date is None or (today - pub_date).days > MAX_STORY_AGE_DAYS:
                continue

            headline, source = _split_title_source(raw_title)
            # Google News RSS descriptions turned out to just repeat the
            # title/source as boilerplate, not a real snippet -- so we skip
            # trying to extract a summary at all rather than show duplicate text.
            return NewsItem(outlet=source, title=headline, url=link, summary='')
    return None
def get_top_stories(per_outlet=5, today: Optional[dt.date] = None):
    # per_outlet kept as a parameter for compatibility with generate_brief.py's
    # existing --headlines-per-outlet flag; here it controls how many results
    # deep we look per topic before giving up on that section.
    today = today or dt.date.today()
    stories = []
    for name, emoji, query in SECTION_QUERIES:
        try:
            item = _fetch_topic_story(query, limit=per_outlet, today=today)
        except Exception:
            item = None
        stories.append(TopStory(section=name, emoji=emoji, item=item))
    return stories
