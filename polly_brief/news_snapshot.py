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

# Preferred freshness window for a "top story." This is a PREFERENCE, not
# a hard reject -- see the tiered fallback in _fetch_topic_story below.
# We used to also lean on Google's `when:` search-time operator
# (when:1d/3d/7d/14d, widening in stages) to bias results toward recent
# articles before any per-entry date check even ran. That turned out to
# be the actual bug: `when:` is undocumented at the RSS level and behaves
# unreliably -- windowed queries were silently returning zero results far
# more often than expected. With no unrestricted fallback left after the
# last window, every section went blank at once -- a fetch failure, not
# seven simultaneous quiet news days.
#
# Fix, in two parts:
#   1. Stop depending on `when:` entirely -- one plain, unrestricted
#      search per topic, which is what was reliably working the whole
#      time under the old code's fallback.
#   2. Prefer articles within this many days, but never let "nothing
#      fresh enough" collapse into "show nothing" -- an older article,
#      or even an unverified-date one, is still more useful to a reader
#      than a blank section. A section only comes back empty if Google
#      genuinely returned zero usable entries for that query.
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
    trusting an unverified date. Used by _fetch_topic_story to rank
    candidates by actual freshness rather than search-result order; an
    entry with no parseable date can still be used as a last-resort
    fallback there, but only after every dated entry has been tried."""
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

    # NOTE on selection strategy: we used to return the FIRST entry (in
    # Google's relevance-ranked order) that passed the freshness check.
    # But relevance ranking has no concept of recency -- Google can easily
    # rank a 12-day-old deep-dive above a 2-day-old news item for the same
    # query. Taking "first in list order" meant we could pick a stale
    # story over a fresher one sitting a few slots lower, even though both
    # were within the 14-day window. So instead we collect every entry we
    # can extract a date from and pick by date, not by search-result order.
    url = f'{GOOGLE_NEWS_BASE}?q={query.replace(" ", "+")}&hl=en-US&gl=US&ceid=US:en'
    parsed = feedparser.parse(url, request_headers=HEADERS)

    # dated: (pub_date, raw_title, link) for every entry with a parseable
    # date, regardless of how old. undated: (raw_title, link) for entries
    # we couldn't get a date from at all, kept only as a last-resort
    # fallback -- see below.
    dated = []
    undated = []
    for entry in parsed.entries[:limit]:
        raw_title = getattr(entry, 'title', '').strip()
        link = getattr(entry, 'link', '').strip()
        if not raw_title or not link:
            continue

        pub_date = _entry_published_date(entry)
        if pub_date is None:
            undated.append((raw_title, link))
        else:
            dated.append((pub_date, raw_title, link))

    # Tier 1: newest entry within MAX_STORY_AGE_DAYS. This is the normal,
    # expected case -- fresh news exists and we picked the freshest of it.
    fresh = [c for c in dated if (today - c[0]).days <= MAX_STORY_AGE_DAYS]
    if fresh:
        pub_date, raw_title, link = max(fresh, key=lambda c: c[0])
    # Tier 2: nothing within 14 days, but Google did return dated articles
    # on this topic -- take the single newest one anyway rather than
    # showing nothing. An older-than-ideal story is still more useful to
    # a reader than a blank section, and a genuinely quiet-news-day topic
    # (rather than a broken fetch) is exactly the case this is for.
    elif dated:
        pub_date, raw_title, link = max(dated, key=lambda c: c[0])
    # Tier 3: nothing had a parseable date at all -- fall back to
    # whatever Google ranked first by relevance. We can't verify how old
    # it is, but returning it is still better than an empty section when
    # the feed clearly returned real results.
    elif undated:
        raw_title, link = undated[0]
    # Tier 4: the feed itself returned nothing usable for this query --
    # this is the only case that should still produce an empty section.
    else:
        return None

    headline, source = _split_title_source(raw_title)
    # Google News RSS descriptions turned out to just repeat the
    # title/source as boilerplate, not a real snippet -- so we skip
    # trying to extract a summary at all rather than show duplicate text.
    return NewsItem(outlet=source, title=headline, url=link, summary='')
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
