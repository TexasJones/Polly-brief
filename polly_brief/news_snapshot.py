from __future__ import annotations
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
SECTION_QUERIES = [
    ('Campaigns', chr(0x1F5F3), 'political campaign primary election'),
    ('Media', chr(0x1F4FA), 'media industry journalism press freedom'),
    ('AI+Policy', chr(0x1F916), 'artificial intelligence policy regulation Congress'),
    ('Energy', chr(0x26A1), 'energy policy EPA regulation'),
    ('Finance', chr(0x1F4B0), 'campaign finance Federal Reserve policy'),
    ('Legislative', chr(0x1F3DB), 'Congress legislation bill'),
]

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

def _fetch_topic_story(query, limit=5):
    url = f'{GOOGLE_NEWS_BASE}?q={query.replace(" ", "+")}&hl=en-US&gl=US&ceid=US:en'
    parsed = feedparser.parse(url, request_headers=HEADERS)
    for entry in parsed.entries[:limit]:
        raw_title = getattr(entry, 'title', '').strip()
        link = getattr(entry, 'link', '').strip()
        if not raw_title or not link:
            continue
        headline, source = _split_title_source(raw_title)
        # Google News RSS descriptions turned out to just repeat the
        # title/source as boilerplate, not a real snippet -- so we skip
        # trying to extract a summary at all rather than show duplicate text.
        return NewsItem(outlet=source, title=headline, url=link, summary='')
    return None

def get_top_stories(per_outlet=5):
    # per_outlet kept as a parameter for compatibility with generate_brief.py's
    # existing --headlines-per-outlet flag; here it controls how many results
    # deep we look per topic before giving up on that section.
    stories = []
    for name, emoji, query in SECTION_QUERIES:
        try:
            item = _fetch_topic_story(query, limit=per_outlet)
        except Exception:
            item = None
        stories.append(TopStory(section=name, emoji=emoji, item=item))
    return stories
