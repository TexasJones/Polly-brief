"""
Mocked-network tests for polly_brief/news_snapshot.py (no real HTTP).
Headlines are real ones from the outlets' feeds on 2026-09-23..25; stale,
off-topic, opinion, undated and broken-feed cases are mixed in on purpose.
Run from the repo root:  python3 test_news_snapshot.py
"""
import datetime as dt
import sys
from email.utils import format_datetime
from unittest.mock import MagicMock, patch

sys.path.insert(0, "polly_brief")
import news_snapshot as ns  # noqa: E402
import requests  # noqa: E402

NOW = dt.datetime(2026, 9, 25, 10, 0, tzinfo=dt.timezone.utc)  # 6 a.m. Eastern
TODAY = dt.date(2026, 9, 25)


def hours_ago(h):
    return NOW - dt.timedelta(hours=h)


def rss(items):
    """items: (title, link, published_datetime_or_None, description)."""
    out = ['<?xml version="1.0"?><rss version="2.0"><channel><title>t</title>']
    for title, link, published, desc in items:
        pub = f'<pubDate>{format_datetime(published)}</pubDate>' if published else ''
        out.append(f'<item><title><![CDATA[{title}]]></title><link>{link}</link>{pub}'
                   f'<description><![CDATA[{desc}]]></description></item>')
    out.append('</channel></rss>')
    return ''.join(out).encode()


def fake_requests(feeds, google=None, redirects=None, fail=()):
    """feeds: {url: [items]}; google: {section_query_word: [items]} matched by
    substring of the search URL; redirects: {google_link: publisher_url};
    fail: feed URLs that time out."""
    google, redirects = google or {}, redirects or {}

    def get(url, headers=None, timeout=None, allow_redirects=None, stream=None):
        if url in fail:
            raise requests.exceptions.Timeout("simulated timeout")
        resp = MagicMock()
        resp.status_code = 200
        resp.raise_for_status.return_value = None
        if stream:  # _resolve_final_url
            resp.url = redirects.get(url, url)
            return resp
        if url.startswith(ns.GOOGLE_NEWS_BASE):
            items = next((v for k, v in google.items() if k in url), [])
            resp.content = rss(items)
            return resp
        resp.content = rss(feeds.get(url, []))
        return resp
    return get


def run(feeds, google=None, redirects=None, fail=(), history=None):
    state = {"sections": history or {}}
    with patch.object(ns.requests, "get", side_effect=fake_requests(feeds, google, redirects, fail)), \
         patch.object(ns, "_load_recent_stories", lambda *a, **k: state["sections"]), \
         patch.object(ns, "_save_recent_stories", lambda s, *a, **k: state.update(sections=s)):
        stories = ns.get_top_stories(today=TODAY, now=NOW)
    return {s.section: s.item for s in stories}, state["sections"]


H = ns._HILL
F = {name: [url for _, url, _b in ns.SECTION_FEEDS[name]] for name in ns.SECTION_FEEDS}


def realistic_feeds():
    return {
        f"{H}/homenews/campaign/feed/": [
            ("Democrats hold 11-point lead over GOP on congressional ballot: Poll", f"{H}/c/1", hours_ago(24), "Democrats hold a comfortable lead."),
            ("Fed's Barr says future interest rate hikes 'likely' needed to tame inflation", f"{H}/c/2", hours_ago(11), ""),
            ("Governor's race tightens in three battlegrounds", f"{H}/c/old", hours_ago(24 * 5), ""),
        ],
        "https://rss.politico.com/politics-news.xml": [
            ("'We are hemorrhaging': Cracks emerge in GOP's Florida firewall", "https://www.politico.com/p/1", hours_ago(2), "Republicans worry."),
        ],
        "https://feeds.npr.org/1014/rss.xml": [
            ("In one of their last votes before November, Senate GOP blocks effort to end Iran war", "https://www.npr.org/n/1", hours_ago(14), ""),
        ],
        "https://rollcall.com/feed/": [
            ("Senate plots its final week before elections with potential data center electricity vote", "https://rollcall.com/r/1", hours_ago(4), ""),
            ("Who would this independent caucus with? 'Everybody'", "https://rollcall.com/r/2", hours_ago(14), ""),
        ],
        f"{H}/homenews/media/feed/": [
            ("Journalists for CNN, MS NOW, Politico allowed back in White House following Trump ban", f"{H}/m/1", hours_ago(17), ""),
            ("Jennings on $5K dividend: 'I don't know that that is the right idea'", f"{H}/m/2", hours_ago(12), ""),
        ],
        "https://www.poynter.org/feed/": [
            ("Want your next investigation to make an impact?", "https://www.poynter.org/p/promo", hours_ago(18), ""),
            ("Judge rules against Trump's White House media ban", "https://www.poynter.org/p/1", hours_ago(22), ""),
        ],
        f"{H}/policy/technology/feed/": [
            ("UN panel calls for guardrails on AI as current safeguards are 'unraveling'", f"{H}/t/old", hours_ago(82), ""),
            ("Crypto super PAC to spend $30M opposing Sherrod Brown in Ohio", f"{H}/t/2", hours_ago(20), ""),
        ],
        "https://feeds.npr.org/1019/rss.xml": [
            ("OpenAI's breach of Australian health department website prompts rebuke", "https://www.npr.org/t/1", hours_ago(5), ""),
            ("eBay bans airbag sales as concerns about faulty or counterfeit parts rise", "https://www.npr.org/t/2", hours_ago(1), ""),
        ],
        "https://www.semafor.com/rss.xml": [
            ("Nvidia CEO Jensen Huang dismisses AI fears as 'distraction'", "https://www.semafor.com/s/1", hours_ago(11), ""),
            ("UBS considers an exit from Switzerland", "https://www.semafor.com/s/2", hours_ago(11), ""),
        ],
        f"{H}/policy/energy-environment/feed/": [
            ("White House seeks to pressure Democrats to move faster on permitting reform deal", f"{H}/e/1", hours_ago(15), ""),
            ("Benchmark mortgage rate tops 7 percent, highest in 2 years", f"{H}/e/2", hours_ago(17), ""),
            ("Phone weather forecast often wrong? Here's why", f"{H}/e/3", hours_ago(16), ""),
            ("Op-ed: Congress should rein in EPA", f"{H}/opinion/energy/1", hours_ago(1), ""),
        ],
        "https://www.utilitydive.com/feeds/news/": [
            ("Advanced transmission projects get $1.9B in DOE funding", "https://www.utilitydive.com/u/1", hours_ago(19), ""),
        ],
        f"{H}/business/feed/": [
            ("Economic frustrations chip away at Trump's rural support: Survey", f"{H}/b/1", hours_ago(38), ""),
        ],
        "https://feeds.npr.org/1017/rss.xml": [
            ("American farmers are hurting -- and worried about their futures", "https://www.npr.org/e/1", hours_ago(1), ""),
            ("Why this Pokémon set is dropping in value", "https://www.npr.org/e/2", hours_ago(-1), ""),
            ("Undated economy story", "https://www.npr.org/e/3", None, ""),
        ],
        f"{H}/homenews/house/feed/": [
            ("Bipartisan lawmakers announce 20-30 percent US film incentive package", f"{H}/h/1", hours_ago(15), ""),
        ],
        f"{H}/homenews/senate/feed/": [
            ("GOP senators dismayed by Trump embrace of Xi after China helped Iran target US troops", f"{H}/s/1", hours_ago(0), ""),
        ],
    }


def test_realistic_day_all_fresh_and_on_topic():
    fail = ("https://rss.politico.com/energy.xml", "https://www.cnbc.com/id/20910258/device/rss/rss.html")
    picks, history = run(realistic_feeds(), fail=fail)
    for section, item in picks.items():
        assert item is not None, f"{section} should have a fresh story"
        assert item.published_date in (TODAY, TODAY - dt.timedelta(days=1)), (section, item.published_date)
        assert ns._is_on_topic(item.title, section), (section, item.title)
    assert picks["Energy"].title != "Benchmark mortgage rate tops 7 percent, highest in 2 years"
    assert "opinion" not in picks["Energy"].url
    assert "Crypto" not in picks["AI+Policy"].title and "UN panel" not in picks["AI+Policy"].title
    assert "eBay" not in picks["AI+Policy"].title
    assert picks["Media"].url != "https://www.poynter.org/p/promo"
    # The Hill's campaign beat feed wins over general feeds; the Fed story
    # and the 5-day-old story in that same feed are rejected.
    assert picks["Campaigns"].url == f"{H}/c/1", picks["Campaigns"].url
    assert picks["Economy"].url == "https://www.npr.org/e/1"          # undated + Pokémon rejected
    # Links go straight to publishers, not news.google.com redirects.
    assert all("news.google.com" not in i.url for i in picks.values())
    # Every pick is recorded for tomorrow's cross-day check.
    assert all(picks[s].url in history[s] for s in picks)
    print("PASS: realistic day -> every section fresh (<=48h), on-topic, direct links; broken feeds ignored")


def test_24h_story_beats_better_covered_older_story():
    feeds = {F["Energy"][0]: [
        ("EPA finalizes power plant rule", f"{H}/e/old", hours_ago(30), ""),
        ("Grid operator warns of winter shortfall", f"{H}/e/new", hours_ago(5), ""),
    ], F["Energy"][2]: [
        ("EPA finalizes power plant rule, utilities react", "https://www.utilitydive.com/x", hours_ago(29), ""),
    ], F["Economy"][2]: [
        ("What the EPA power plant rule means for bills", "https://www.npr.org/x", hours_ago(28), ""),
    ]}
    picks, _ = run(feeds)
    assert picks["Energy"].url == f"{H}/e/new", picks["Energy"].url
    print("PASS: anything within 24h outranks an older (24-48h) story, even a widely covered one")


def test_widely_covered_story_beats_newer_minor_one_within_24h():
    feeds = {F["Legislative"][0]: [
        ("House passes stopgap funding bill to avert shutdown", "https://rollcall.com/big", hours_ago(10), ""),
        ("Senate committee advances Klomp nomination", "https://rollcall.com/minor", hours_ago(1), ""),
    ], F["Legislative"][3]: [
        ("Stopgap funding bill clears House, shutdown averted for now", "https://www.politico.com/big", hours_ago(9), ""),
    ], F["Campaigns"][2]: [
        ("House stopgap funding bill heads to Senate ahead of shutdown deadline", "https://www.npr.org/big", hours_ago(8), ""),
    ]}
    picks, _ = run(feeds)
    assert picks["Legislative"].url in ("https://rollcall.com/big", "https://www.politico.com/big"), picks["Legislative"].url
    assert picks["Legislative"].coverage >= 2, picks["Legislative"].coverage
    print("PASS: within 24h, the story other outlets are covering wins over a newer minor item")


def test_section_left_out_when_nothing_fresh():
    feeds = {F["AI+Policy"][0]: [("AI safety bill stalls in committee", f"{H}/t/old", hours_ago(60), "")]}
    google = {quote("artificial intelligence policy"): [
        ("Old AI story - Axios", "https://news.google.com/rss/articles/old", hours_ago(100), ""),
    ]}
    picks, _ = run(feeds, google=google)
    assert picks["AI+Policy"] is None, "no story older than 48h may be used"
    print("PASS: nothing within 48h (feeds or backup) -> section left out, never an old story")


def quote(s):
    from urllib.parse import quote_plus
    return quote_plus(s)


def test_backup_search_used_only_when_feeds_empty():
    google = {quote("Congress Senate House vote bill"): [
        ("Senate confirms new trade representative - Punchbowl News", "https://news.google.com/rss/articles/abc", hours_ago(6), ""),
        ("Opinion: Congress is broken - The Hill", "https://news.google.com/rss/articles/op", hours_ago(2), ""),
    ]}
    redirects = {"https://news.google.com/rss/articles/op": f"{H}/opinion/congress-blog/1",
                 "https://news.google.com/rss/articles/abc": "https://punchbowl.news/article/x"}
    picks, _ = run({}, google=google, redirects=redirects)
    item = picks["Legislative"]
    assert item is not None and item.outlet == "Punchbowl News", item
    assert item.title == "Senate confirms new trade representative"
    print("PASS: backup Google search fills an empty section (48h rule, opinion pieces skipped)")


def test_yesterdays_pick_is_not_repeated():
    feeds = {F["Media"][1]: [
        ("Judge rules against Trump's White House media ban", "https://www.poynter.org/p/1", hours_ago(20), ""),
        ("Newsrooms brace for election night staffing crunch", "https://www.poynter.org/p/2", hours_ago(30), ""),
    ]}
    history = {"Media": {"https://www.poynter.org/p/1": (TODAY - dt.timedelta(days=1)).isoformat()}}
    picks, _ = run(feeds, history=history)
    assert picks["Media"].url == "https://www.poynter.org/p/2"
    print("PASS: yesterday's pick is skipped; next freshest (still <=48h) is used")


def test_same_story_never_in_two_sections():
    npr = "https://feeds.npr.org/1014/rss.xml"
    feeds = {npr: [("Senate GOP blocks effort to end Iran war in election-year vote", "https://www.npr.org/n/1", hours_ago(3), "")]}
    picks, _ = run(feeds)
    shown = [s for s, i in picks.items() if i and i.url == "https://www.npr.org/n/1"]
    assert len(shown) == 1, shown
    print("PASS: one story can't appear in two sections on the same day")


def test_topic_rules():
    assert not ns._is_on_topic("White House hosts state dinner for Xi", "Legislative")
    assert ns._is_on_topic("House passes stopgap funding bill", "Legislative")
    assert not ns._is_on_topic("Jackson warns Supreme Court's emergency rulings imposing 'institutional costs'", "AI+Policy")
    assert not ns._is_on_topic("Iran's president tells Fox anchor the war was 'imposed on us'", "Campaigns")
    assert not ns._is_on_topic("Senate committee advances Klomp nomination", "Campaigns")
    assert ns._is_on_topic("Nvidia CEO Jensen Huang dismisses AI fears as 'distraction'", "AI+Policy")
    assert not ns._is_on_topic("Said the senator", "AI+Policy")  # 'ai' inside 'said' must not match
    print("PASS: topic rules reject the real off-topic picks seen in production")


def test_pr_story_48h_cap():
    feeds = {"https://www.provokemedia.com/newsfeed/provoke-media-latest": [
        ("Burson names new global CEO", "https://www.provokemedia.com/1", hours_ago(60), "")]}
    state = {}
    with patch.object(ns.requests, "get", side_effect=fake_requests(feeds)), \
         patch.object(ns, "_load_recent_stories", lambda *a, **k: state), \
         patch.object(ns, "_save_recent_stories", lambda *a, **k: None):
        story = ns.get_pr_industry_story(today=TODAY, now=NOW)
    assert story.item is None
    print("PASS: PR & Comms item older than 48h is not used")


def test_hero_is_most_covered_story():
    sys.path.insert(0, "polly_brief")
    import template
    a = ns.TopStory("Campaigns", "x", ns.NewsItem("A", "a", "u1", "", TODAY, coverage=0))
    b = ns.TopStory("Legislative", "y", ns.NewsItem("B", "b", "u2", "", TODAY, coverage=3))
    assert template._pick_top_highlight([a, b]) is b
    assert template._pick_top_highlight([a, ns.TopStory("Energy", "z", None)]) is a
    print("PASS: hero slot goes to the most widely covered story")


def test_summary_cleanup():
    s = ns._summary_from_description("<p>Lawmakers passed the bill. It now heads to the Senate. More text.</p>"
                                     "The post X appeared first on Roll Call.", title="t")
    assert s == "Lawmakers passed the bill. It now heads to the Senate.", s
    assert ns._summary_from_description("Same as title", title="Same as title") == ""
    assert ns._summary_from_description("x " * 200).endswith("…")
    print("PASS: summaries trimmed, boilerplate removed")


def test_pending_feeds_checked_but_never_used():
    mediaite = "https://www.mediaite.com/feed/"
    feeds = {mediaite: [("CNN anchor exits network after 20 years", "https://www.mediaite.com/pend", hours_ago(1), "")],
             ns.SECTION_FEEDS["Media"][0][1]: [("Newsrooms brace for election-night staffing crunch", f"{H}/m/ok", hours_ago(20), "")]}
    picks, _ = run(feeds)
    assert all(i is None or "mediaite.com" not in i.url for i in picks.values())
    assert picks["Media"].url == f"{H}/m/ok"
    print("PASS: pending (unconfirmed) feeds are health-checked only, never used for picks")


def test_one_retry_on_connection_error():
    calls = {"n": 0}
    url = ns.SECTION_FEEDS["Energy"][1][1]
    good = fake_requests({url: [("Grid operator warns of winter shortfall", "https://www.utilitydive.com/ok", hours_ago(3), "")]})

    def flaky(u, **kw):
        if u == url and calls["n"] == 0:
            calls["n"] += 1
            raise requests.exceptions.ConnectionError("Connection reset by peer")
        return good(u, **kw)
    state = {"sections": {}}
    with patch.object(ns.requests, "get", side_effect=flaky), patch.object(ns.time, "sleep", lambda s: None), \
         patch.object(ns, "_load_recent_stories", lambda *a, **k: {}), \
         patch.object(ns, "_save_recent_stories", lambda s, *a, **k: state.update(sections=s)):
        stories = {st.section: st.item for st in ns.get_top_stories(today=TODAY, now=NOW)}
    assert stories["Energy"] and stories["Energy"].url == "https://www.utilitydive.com/ok"
    print("PASS: a one-off connection reset is retried once instead of losing the feed")


def test_source_list_rules():
    active = [url for feeds in ns.SECTION_FEEDS.values() for _o, url, _b in feeds]
    pending = [url for _o, url in ns.PENDING_FEEDS]
    assert not any("fox" in u for u in active + pending), "no Fox News feeds"
    assert not set(active) & set(pending)
    assert all(len(feeds) >= 5 for feeds in ns.SECTION_FEEDS.values()), \
        {k: len(v) for k, v in ns.SECTION_FEEDS.items()}
    print("PASS: no Fox News; every section has at least 5 confirmed feeds")


if __name__ == "__main__":
    test_realistic_day_all_fresh_and_on_topic()
    test_24h_story_beats_better_covered_older_story()
    test_widely_covered_story_beats_newer_minor_one_within_24h()
    test_section_left_out_when_nothing_fresh()
    test_backup_search_used_only_when_feeds_empty()
    test_yesterdays_pick_is_not_repeated()
    test_same_story_never_in_two_sections()
    test_topic_rules()
    test_pr_story_48h_cap()
    test_hero_is_most_covered_story()
    test_summary_cleanup()
    test_pending_feeds_checked_but_never_used()
    test_one_retry_on_connection_error()
    test_source_list_rules()
    print("\nAll news tests passed.")
