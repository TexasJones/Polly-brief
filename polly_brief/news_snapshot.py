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
# Finance and Economy were originally split into two separate categories,
# then both removed entirely (neither mapped to a job category Polly
# actually tracks). Economy came back as a single category afterward,
# deliberately scoped to broader business/economic news (markets, jobs
# reports, macro trends) rather than the narrower "money in politics"
# angle Finance used to cover -- readers wanted general business context
# for a political-professional audience, not a second campaign-finance
# section.
SECTION_QUERIES = [
    ('Campaigns', chr(0x1F5F3), 'political campaign primary election'),
    ('Media', chr(0x1F4FA), 'U.S. media television cable news Hollywood press freedom -"journalists association"'),
    ('AI+Policy', chr(0x1F916), 'artificial intelligence policy regulation Congress'),
    ('Energy', chr(0x26A1), 'energy policy EPA regulation'),
    ('Economy', chr(0x1F4C8), 'U.S. economy jobs report inflation stock market Federal Reserve'),
    ('Legislative', chr(0x1F3DB), 'Congress committee vote markup bill passed signed law'),
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

# Outer cap on how old a story can be even in the "graceful fallback"
# tier below -- added after a 139-day-old story slipped through under
# the previous uncapped version. An old story still beats a blank
# section up to a point, but 139 days is well past that point; beyond
# this cap, an empty section is the more honest outcome.
MAX_FALLBACK_AGE_DAYS = 30

# Titles that indicate Google matched a section/category INDEX page
# (e.g. a publisher's generic "Headlines" landing page) rather than an
# actual individual news article -- these can occasionally get indexed
# and outrank real articles for a broad query. Checked as an exact match
# against the full trimmed headline, not a substring, so a real headline
# that happens to CONTAIN one of these words (e.g. "Latest jobs report
# shows...") isn't wrongly excluded.
GENERIC_TITLE_BLOCKLIST = {
    'headlines', 'headline', 'news', 'latest', 'latest news',
    'top stories', 'home', 'homepage',
}


def _is_generic_title(title: str) -> bool:
    return title.strip().lower() in GENERIC_TITLE_BLOCKLIST

# Applied to every SECTION_QUERIES search below. Rather than trying to
# detect opinion "tone" in headline text (unreliable -- an op-ed title
# doesn't have to say "opinion" anywhere, e.g. "Congress Should Rein in
# EPA Overreach"), this excludes by URL PATH instead: nearly every major
# outlet organizes opinion/editorial content under a predictable URL
# segment (nytimes.com/opinion/..., washingtonpost.com/opinions/...,
# etc.), and Google's `-inurl:` operator can filter on that structurally.
# Matters here specifically because Polly's audience spans both parties --
# a directionally-framed op-ed showing up as "today's news" reads as the
# brief taking a side, which straight reporting doesn't.
OPINION_EXCLUSION = '-inurl:opinion -inurl:oped -inurl:op-ed -inurl:editorial -inurl:commentary'

# The "core 15" trusted political news sources -- outlets that publish on
# DC politics/policy multiple times a day, which is what actually fixes
# staleness: a tightened topic query narrows WHAT matches, but doesn't by
# itself guarantee the matches are recent. Restricting to outlets that
# cover this beat constantly means there's almost always something fresh
# to find, and it also raises source credibility across the board --
# Polly's own audience already reads these outlets, so citing them is a
# trust signal, not just a freshness fix.
FREE_SOURCES = (
    '(site:axios.com OR site:politico.com OR site:punchbowl.news '
    'OR site:semafor.com OR site:apnews.com OR site:thehill.com '
    'OR site:npr.org OR site:notus.org OR site:nbcnews.com OR site:cnn.com '
    'OR site:pbs.org OR site:bbc.com OR site:csmonitor.com '
    'OR site:govexec.com OR site:stateline.org)'
)

# Genuinely useful, authoritative sources -- but each has a real paywall
# (Reuters is metered, the rest are hard paywalls or subscription-gated).
# Kept as a SECOND-CHOICE tier rather than removed outright: still better
# to occasionally show a paywalled story than nothing at all on a
# genuinely quiet-news topic, but a reader shouldn't hit "Read More" and
# get blocked more often than not. See _fetch_topic_story's 3-stage
# cascade -- this tier is only tried if FREE_SOURCES comes up completely
# empty for that topic.
PAYWALLED_SOURCES = (
    '(site:reuters.com OR site:washingtonpost.com OR site:bloomberg.com '
    'OR site:nationaljournal.com OR site:rollcall.com)'
)

# Google News sometimes labels a story's source by its proper name
# ("Reuters") and sometimes by its bare domain ("reuters.com"), depending
# on how the individual publisher's own RSS feed happens to be formatted
# upstream -- not something under our control. This maps the domain-style
# form back to a proper display name, for the same 15 trusted outlets
# listed in TRUSTED_SOURCES above (kept in sync with that same list).
# Anything outside these 15 (e.g. a Stage 2 widened-search result) is left
# exactly as Google reports it, since there's no way to enumerate every
# possible outlet's preferred display name.
SOURCE_NAME_MAP = {
    'axios.com': 'Axios',
    'politico.com': 'Politico',
    'punchbowl.news': 'Punchbowl News',
    'semafor.com': 'Semafor',
    'reuters.com': 'Reuters',
    'apnews.com': 'AP',
    'washingtonpost.com': 'The Washington Post',
    'thehill.com': 'The Hill',
    'npr.org': 'NPR',
    'rollcall.com': 'Roll Call',
    'notus.org': 'NOTUS',
    'bloomberg.com': 'Bloomberg',
    'nbcnews.com': 'NBC News',
    'nationaljournal.com': 'National Journal',
    'cnn.com': 'CNN',
}


def _normalize_source_name(source: str) -> str:
    """Map a bare-domain source name (e.g. 'reuters.com') back to its
    proper display name (e.g. 'Reuters') for the 15 trusted outlets --
    see SOURCE_NAME_MAP above. A source already in proper-name form, or
    from outside the trusted 15, passes through unchanged."""
    key = source.strip().lower()
    if key.startswith('www.'):
        key = key[4:]
    return SOURCE_NAME_MAP.get(key, source)


@dataclass
class NewsItem:
    outlet: str
    title: str
    url: str
    summary: str
    # The story's own verified publish date, as determined during
    # selection in _fetch_topic_story (see _entry_published_date). None
    # specifically means "Google gave us no parseable date for this one"
    # (the Tier 3 undated fallback) -- kept as None rather than guessing
    # a date, since template.py uses this to decide whether to show a
    # "time ago" label at all: an unverified date shouldn't display a
    # fabricated-looking one.
    published_date: Optional[dt.date] = None
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
        return headline.strip(), _normalize_source_name(source.strip())
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


def _fetch_candidates(query, limit):
    """Fetch and parse one Google News search into (dated, undated) candidate
    lists. Pulled out as its own function so the two-stage search in
    _fetch_topic_story (trusted-15 first, then a widened fallback) can
    run identical parsing logic on both stages rather than duplicating it."""
    url = f'{GOOGLE_NEWS_BASE}?q={query.replace(" ", "+")}&hl=en-US&gl=US&ceid=US:en'
    parsed = feedparser.parse(url, request_headers=HEADERS)

    # dated: (pub_date, raw_title, link) for every entry with a parseable
    # date, regardless of how old. undated: (raw_title, link) for entries
    # we couldn't get a date from at all, kept only as a last-resort
    # fallback -- see the tier selection in _fetch_topic_story.
    dated = []
    undated = []
    for entry in parsed.entries[:limit]:
        raw_title = getattr(entry, 'title', '').strip()
        link = getattr(entry, 'link', '').strip()
        if not raw_title or not link:
            continue

        # Check the actual headline portion (before " - Source") against
        # the generic-title blocklist -- checking the full raw_title
        # would let a real headline from a source whose own NAME happens
        # to match (unlikely, but the split keeps this precise either way).
        headline_only = raw_title.rsplit(' - ', 1)[0].strip() if ' - ' in raw_title else raw_title
        if _is_generic_title(headline_only):
            continue

        pub_date = _entry_published_date(entry)
        if pub_date is None:
            undated.append((raw_title, link))
        else:
            dated.append((pub_date, raw_title, link))

    return dated, undated


def _fetch_topic_story(query, limit=15, today: Optional[dt.date] = None, used_urls: Optional[set] = None):
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
    used_urls = used_urls or set()

    def _exclude_used(dated_list, undated_list):
        # Drop any candidate whose URL was already picked for an earlier
        # section in this same day's brief -- without this, two topic
        # queries that both genuinely match the same real story (e.g. an
        # AI-regulation story hitting both "AI+Policy" and "Legislative")
        # would show the identical headline twice in one email.
        d = [c for c in dated_list if c[2] not in used_urls]
        u = [c for c in undated_list if c[1] not in used_urls]
        return d, u

    # Stage 1: free/lightly-gated sources. Tried first because these
    # outlets both publish on DC politics constantly (fixing staleness)
    # and are sources Polly's own audience already trusts (fixing
    # sourcing quality) -- see FREE_SOURCES above. A reader who clicks
    # "Read More" here should almost always be able to actually read
    # the story, not hit a paywall.
    free_query = f'{query} {FREE_SOURCES} {OPINION_EXCLUSION}'
    dated, undated = _fetch_candidates(free_query, limit)
    dated, undated = _exclude_used(dated, undated)

    # Stage 2: only if Stage 1 came back with literally nothing usable
    # at all, try the paywalled-but-authoritative tier (Reuters, WaPo,
    # Bloomberg, etc.) before giving up on quality sourcing entirely.
    # These are genuinely good sources -- the issue isn't that they're
    # bad, it's that they shouldn't be a story's ONLY chance to be
    # featured when a free alternative exists. Only reached when the
    # free tier genuinely has nothing for this topic today.
    if not dated and not undated:
        paywalled_query = f'{query} {PAYWALLED_SOURCES} {OPINION_EXCLUSION}'
        dated, undated = _fetch_candidates(paywalled_query, limit)
        dated, undated = _exclude_used(dated, undated)

    # Stage 3: only if BOTH trusted tiers came back with literally
    # nothing usable at all -- not "nothing fresh enough" (Tier 1/2 below
    # already handle that gracefully), but zero results, full stop -- do
    # we widen to the unrestricted web. This preserves the Stage 1/2
    # quality/freshness win for the normal case, while still honoring
    # the "never show a blank section over a stale one" policy for
    # whatever topic neither trusted tier covered that day.
    if not dated and not undated:
        unrestricted_query = f'{query} {OPINION_EXCLUSION}'
        dated, undated = _fetch_candidates(unrestricted_query, limit)
        dated, undated = _exclude_used(dated, undated)

    # NOTE on selection strategy: we used to return the FIRST entry (in
    # Google's relevance-ranked order) that passed the freshness check.
    # But relevance ranking has no concept of recency -- Google can easily
    # rank a 12-day-old deep-dive above a 2-day-old news item for the same
    # query. Taking "first in list order" meant we could pick a stale
    # story over a fresher one sitting a few slots lower, even though both
    # were within the 14-day window. So instead we collect every entry we
    # can extract a date from and pick by date, not by search-result order.

    # Tier 1: newest entry within MAX_STORY_AGE_DAYS. This is the normal,
    # expected case -- fresh news exists and we picked the freshest of it.
    fresh = [c for c in dated if (today - c[0]).days <= MAX_STORY_AGE_DAYS]
    if fresh:
        pub_date, raw_title, link = max(fresh, key=lambda c: c[0])
        headline, source = _split_title_source(raw_title)
        return NewsItem(outlet=source, title=headline, url=link, summary='', published_date=pub_date)

    # Tier 2: nothing within MAX_STORY_AGE_DAYS, but Google did return
    # dated articles on this topic -- take the single newest one anyway,
    # UNLESS it's older than MAX_FALLBACK_AGE_DAYS too. An older-than-
    # ideal story is still more useful to a reader than a blank section,
    # but only up to a real outer limit -- this cap exists specifically
    # because a 139-day-old story once made it through here uncapped.
    if dated:
        newest_date, newest_title, newest_link = max(dated, key=lambda c: c[0])
        if (today - newest_date).days <= MAX_FALLBACK_AGE_DAYS:
            headline, source = _split_title_source(newest_title)
            return NewsItem(outlet=source, title=headline, url=newest_link, summary='', published_date=newest_date)

    # Tier 3: nothing had a parseable date at all (or the only dated
    # candidate exceeded MAX_FALLBACK_AGE_DAYS) -- fall back to whatever
    # Google ranked first by relevance among the undated entries. We
    # can't verify how old it is, but returning it is still better than
    # an empty section when the feed clearly returned real results.
    if undated:
        raw_title, link = undated[0]
        headline, source = _split_title_source(raw_title)
        return NewsItem(outlet=source, title=headline, url=link, summary='', published_date=None)

    # Tier 4: nothing usable at all, from any source tier -- this is the
    # only case that should still produce an empty section.
    return None


def get_top_stories(per_outlet=15, today: Optional[dt.date] = None):
    # per_outlet kept as a parameter for compatibility with generate_brief.py's
    # existing --headlines-per-outlet flag; here it controls how many results
    # deep we look per topic before giving up on that section.
    today = today or dt.date.today()
    stories = []
    # Tracks every story URL already picked for an earlier section this
    # run, so a later section can't pick the same story again -- see the
    # _exclude_used check inside _fetch_topic_story.
    used_urls = set()
    for name, emoji, query in SECTION_QUERIES:
        try:
            item = _fetch_topic_story(query, limit=per_outlet, today=today, used_urls=used_urls)
        except Exception:
            item = None
        if item:
            used_urls.add(item.url)
        stories.append(TopStory(section=name, emoji=emoji, item=item))
    return stories
