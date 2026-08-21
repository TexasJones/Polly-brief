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

# Freshness ceiling for a "top story." This is now the ONLY freshness
# mechanism -- see _fetch_topic_story below. We used to also lean on
# Google's `when:` search-time operator (when:1d/3d/7d/14d, widening in
# stages) to bias results toward recent articles before this per-entry
# check even ran. That turned out to be the actual bug: `when:` is
# undocumented at the RSS level and behaves unreliably -- windowed queries
# were silently returning zero results far more often than expected. In
# the old code (before `when:` existed) there was a single unrestricted
# search with no freshness filter at all, which is why stale roundup
# articles could win on quiet days. In the newer code, ALL FOUR windowed
# searches could come up empty, and with no unrestricted fallback left,
# every section went blank -- a total seven-section blackout, which is a
# fetch failure, not seven simultaneous quiet news days.
#
# Fix: stop depending on `when:` entirely. Go back to one plain,
# unrestricted search (the thing that was reliably working the whole
# time), and keep freshness enforcement entirely in _entry_published_date
# below, which checks each candidate's own real publish date against this
# cutoff. That's a mechanism we've actually verified works, instead of
# one we now have evidence is unreliable.
MAX_STORY_AGE_DAYS = 14


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
    """Pull the entry's own publish date out of feedparser's parsed struct.
    Checks `published_parsed` first, falling back to `updated_parsed` since
    not every feed populates both. Returns None if neither is present or
    parseable -- that's treated as "can't verify this is fresh" by the
    caller, not as "assume it's fine," since the whole point here is not
    trusting an unverified date. This is now the sole freshness gate (see
    MAX_STORY_AGE_DAYS above) -- the search itself is unrestricted, so
    every candidate has to clear this check on its own merits."""
    struct = getattr(entry, 'published_parsed', None) or getattr(entry, 'updated_parsed', None)
    if not struct:
        return None
    try:
        return dt.date(struct.tm_year, struct.tm_mon, struct.tm_mday)
    except (TypeError, ValueError):
        return None


def _fetch_topic_story(query, limit=5, today: Optional[dt.date] = None):
    # Plain, unrestricted relevance search -- no `when:` operator. We
    # previously tried to bias this toward recent results by layering
    # `when:1d/3d/7d/14d` windowed searches on top, widening until one
    # returned something. In practice those windowed queries were
    # unreliable at the RSS level and would frequently return nothing at
    # all, and with no fallback left after the last window, topics went
    # silently empty. The plain search is the one query we know actually
    # returns results consistently; freshness is enforced afterward by
    # checking each entry's own published date (see _entry_published_date
    # and MAX_STORY_AGE_DAYS), not by trying to filter at search time.
    today = today or dt.date.today()

    url = f'{GOOGLE_NEWS_BASE}?q={query.replace(" ", "+")}&hl=en-US&gl=US&ceid=US:en'
    parsed = feedparser.parse(url, request_headers=HEADERS)
    for entry in parsed.entries[:limit]:
        raw_title = getattr(entry, 'title', '').strip()
        link = getattr(entry, 'link', '').strip()
        if not raw_title or not link:
            continue

        # Reject anything we can't confirm is recent. An entry with no
        # parseable date at all is skipped too, same reasoning: we can't
        # call something "today's news" if we can't confirm when it ran.
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
