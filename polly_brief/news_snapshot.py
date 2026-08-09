from __future__ import annotations
import re
from dataclasses import dataclass
from html import unescape
from typing import Optional
import feedparser
import requests
from bs4 import BeautifulSoup

HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; PollyBriefBot/1.0; +https://www.thepolly.co)'}

RSS_FEEDS = {
    'Politico': 'https://rss.politico.com/politics-news.xml',
    'Roll Call': 'https://www.rollcall.com/rss/all_news.xml',
    'The Hill': 'https://thehill.com/news/feed/',
    'Semafor': 'https://www.semafor.com/rss.xml',
    'NPR': 'https://feeds.npr.org/1014/rss.xml',
    'Washington Examiner': 'https://www.washingtonexaminer.com/section/news/feed',
    'Government Executive': 'https://www.govexec.com/rss/all/',
    'Route Fifty': 'https://www.route-fifty.com/rss/all/',
    'CNN': 'https://rss.cnn.com/rss/cnn_allpolitics.rss',
    'NYT': 'https://rss.nytimes.com/services/xml/rss/nyt/Politics.xml',
    'Washington Post': 'https://feeds.washingtonpost.com/rss/politics',
    'NBC News': 'https://feeds.nbcnews.com/feeds/nbcpolitics',
}
AXIOS_URL = 'https://www.axios.com/politics-policy'

SECTIONS = [
    ('Campaigns', chr(0x1F5F3), ['campaign', 'candidate', 'primary', 'midterm', 'election day', 'ballot', 'poll', 'voters', 'runs for', 'reelection', "governor's race", 'senate race']),
    ('Media', chr(0x1F4FA), ['press secretary', 'press briefing', 'journalist', 'newsroom', 'broadcast', 'press corps', 'leaked', 'scoop', 'media coverage', 'editor-in-chief', 'newsroom layoffs', 'subscription model', 'cable news', 'network news', 'tv ratings', 'streaming service', 'media merger', 'press freedom', 'fcc', 'disinformation', 'misinformation']),
    ('AI+Policy', chr(0x1F916), ['artificial intelligence', 'ai regulation', 'ai policy', 'chatgpt', 'openai', 'algorithm', 'tech policy', 'data privacy', 'section 230', 'ai safety', 'machine learning', 'big tech']),
    ('Energy', chr(0x26A1), ['energy policy', 'oil', 'pipeline', 'renewable', 'solar', 'wind power', 'epa', 'emissions', 'climate rule', 'power grid', 'grid reliability', 'utility rates', 'utility regulator', 'drilling', 'lng', 'natural gas', 'coal plant', 'nuclear power', 'offshore wind', 'carbon capture']),
    ('Finance', chr(0x1F4B0), ['banking', 'sec', 'federal reserve', 'fed chair', 'rate cut', 'rate hike', 'fintech', 'wall street', 'stock market', 'financial regulation', 'interest rate', 'inflation data', 'economic growth', 'recession', 'tariff', 'treasury', 'irs', 'tax bill', 'donor', 'super pac', 'campaign finance']),
    ('Legislative', chr(0x1F3DB), ['congress', 'senate', 'house republicans', 'house democrats', 'capitol hill', 'speaker', 'majority leader', 'filibuster', 'committee', 'lawmakers', 'appropriations', 'confirmation hearing', 'state legislature', 'statehouse', 'governor signs', 'bill passes']),
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

def _clean_summary(raw_html, max_sentences=2):
    if not raw_html:
        return ''
    text = BeautifulSoup(unescape(raw_html), 'html.parser').get_text(separator=' ').strip()
    text = re.sub(r'\s+', ' ', text)
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return ' '.join(sentences[:max_sentences]).strip()

def _fetch_rss_pool(outlet, feed_url, limit):
    parsed = feedparser.parse(feed_url, request_headers=HEADERS)
    items = []
    for entry in parsed.entries[:limit]:
        title = getattr(entry, 'title', '').strip()
        link = getattr(entry, 'link', '').strip()
        raw_summary = getattr(entry, 'summary', '') or getattr(entry, 'description', '')
        if title and link:
            items.append(NewsItem(outlet=outlet, title=title, url=link, summary=_clean_summary(raw_summary)))
    return items

def _fetch_axios_pool(limit, session=None):
    sess = session or requests.Session()
    try:
        resp = sess.get(AXIOS_URL, headers=HEADERS, timeout=20)
        resp.raise_for_status()
    except requests.RequestException:
        return []
    soup = BeautifulSoup(resp.text, 'html.parser')
    items, seen = [], set()
    for a in soup.find_all('a', href=True):
        href = a['href']
        text = a.get_text(strip=True)
        if not text or len(text) < 20:
            continue
        if not any(seg.isdigit() and len(seg) == 4 for seg in href.split('/')[:2]):
            continue
        full_url = href if href.startswith('http') else f'https://www.axios.com{href}'
        if full_url in seen:
            continue
        seen.add(full_url)
        items.append(NewsItem(outlet='Axios', title=text, url=full_url, summary=''))
        if len(items) >= limit:
            break
    return items

def _fetch_pool(per_outlet=20):
    pool = []
    for outlet, feed_url in RSS_FEEDS.items():
        try:
            pool.extend(_fetch_rss_pool(outlet, feed_url, per_outlet))
        except Exception:
            pass
    pool.extend(_fetch_axios_pool(per_outlet))
    return pool

def _classify(item):
    # Match against title + summary combined, not just the headline --
    # a lot of relevant context only shows up in the article summary.
    t = (item.title + ' ' + item.summary).lower()
    for name, _emoji, keywords in SECTIONS:
        for kw in keywords:
            pattern = r'\b' + re.escape(kw.strip()) + r'\b'
            if re.search(pattern, t):
                return name
    return None

def get_top_stories(per_outlet=20):
    pool = _fetch_pool(per_outlet=per_outlet)
    by_section = {}
    for item in pool:
        section = _classify(item)
        if section and section not in by_section:
            by_section[section] = item
    return [TopStory(section=name, emoji=emoji, item=by_section.get(name)) for name, emoji, _keywords in SECTIONS]
