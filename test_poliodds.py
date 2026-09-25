"""
Mocked-network tests for poliodds_snapshot.py. No real HTTP calls -- this
sandbox's egress policy blocks Kalshi/VoteHub outright (confirmed via the
proxy log), so every scenario here fakes requests.Session.get() with
response shapes taken from Kalshi's and VoteHub's own published docs.
The real, unmocked first run happens in the GitHub Action, which has
normal internet access like every other script in this repo.
"""
import sys
import datetime as dt
from unittest.mock import patch, MagicMock

sys.path.insert(0, "polly_brief")
import poliodds_snapshot as po


def _market(sub_title, last_price=None, prev_price=None, yes_bid=None, yes_ask=None,
           prev_bid=None, prev_ask=None, volume=0, status="active", volume_24h=1_000):
    # volume_24h defaults to "traded today" so older tests model a normally
    # active market; the freshness tests below set it to 0 explicitly.
    m = {"yes_sub_title": sub_title, "status": status, "volume_fp": volume,
         "volume_24h_fp": volume_24h}
    if last_price is not None:
        m["last_price_dollars"] = last_price
    if prev_price is not None:
        m["previous_price_dollars"] = prev_price
    if yes_bid is not None:
        m["yes_bid_dollars"] = yes_bid
    if yes_ask is not None:
        m["yes_ask_dollars"] = yes_ask
    if prev_bid is not None:
        m["previous_yes_bid_dollars"] = prev_bid
    if prev_ask is not None:
        m["previous_yes_ask_dollars"] = prev_ask
    return m


def fake_get_factory(event_responses: dict, poll_responses: dict = None, fail_hosts: tuple = ()):
    """event_responses: {event_ticker: (status_code, markets_list_or_None)}
    poll_responses: {poll_type: json_body}
    fail_hosts: substrings that should raise a connection error."""
    poll_responses = poll_responses or {}

    def fake_get(url, params=None, headers=None, timeout=None):
        for host in fail_hosts:
            if host in url:
                raise po.requests.exceptions.ConnectionError(f"simulated outage: {host}")
        resp = MagicMock()
        if "/events/" in url:
            ticker = url.rsplit("/", 1)[-1]
            code, markets = event_responses.get(ticker, (404, None))
            resp.status_code = code
            if code == 404:
                return resp
            # Documented shape for with_nested_markets=true: markets nested
            # inside "event" (top-level "markets" is deprecated).
            resp.json.return_value = {"event": {"event_ticker": ticker, "markets": markets}}
            resp.raise_for_status.return_value = None
            return resp
        if "/polls" in url:
            resp.status_code = 200
            resp.json.return_value = poll_responses.get(params.get("poll_type"), [])
            resp.raise_for_status.return_value = None
            return resp
        resp.status_code = 404
        return resp
    return fake_get


def test_normal_house_and_senate_with_change():
    events = {
        "CONTROLH-2026": (200, [
            _market("Democratic Party", last_price=0.90, prev_price=0.88, volume=1_000_000),
            _market("Republican Party", last_price=0.10, prev_price=0.12, volume=1_000_000),
        ]),
        "CONTROLS-2026": (200, [
            _market("Democratic Party", last_price=0.64, prev_price=0.60, volume=500_000),
            _market("Republican Party", last_price=0.36, prev_price=0.40, volume=500_000),
        ]),
    }
    with patch.object(po.requests.Session, "get", side_effect=fake_get_factory(events, fail_hosts=("votehub",))):
        client = po._KalshiClient(po.requests.Session())
        odds = po._fetch_odds(client)
    assert odds.house.leader == "DEM" and odds.house.leader_pct == 90
    assert odds.house.change_pts == 2
    assert odds.senate.leader == "DEM" and odds.senate.leader_pct == 64
    assert odds.senate.change_pts == 4
    print("PASS: normal house/senate with 24h change")


def test_thin_race_excluded_from_mover_and_tightest():
    events = {
        "CONTROLH-2026": (404, None),
        "CONTROLS-2026": (404, None),
    }
    for code in po.SENATE_RACE_CODES:
        ticker = po.SENATE_RACE_EVENT.format(code=code)
        if code == "NC":  # real race, decent volume, small move
            events[ticker] = (200, [
                _market("Democratic Party", last_price=0.52, prev_price=0.51, volume=800_000),
                _market("Republican Party", last_price=0.48, prev_price=0.49, volume=800_000),
            ])
        elif code == "WY":  # thin market, huge apparent swing -- must be excluded
            events[ticker] = (200, [
                _market("Republican Party", last_price=0.95, prev_price=0.60, volume=200),
                _market("Democratic Party", last_price=0.05, prev_price=0.40, volume=200),
            ])
        else:
            events[ticker] = (404, None)

    with patch.object(po.requests.Session, "get", side_effect=fake_get_factory(events, fail_hosts=("votehub",))):
        client = po._KalshiClient(po.requests.Session())
        odds = po._fetch_odds(client)

    all_labels = [odds.spotlight.label if odds.spotlight else None] + [r.label for r in odds.tight_races]
    assert "WY Senate" not in all_labels, "thin market should be filtered by MIN_RACE_VOLUME_CONTRACTS"
    assert "NC Senate" in all_labels
    print("PASS: thin/low-liquidity race excluded from spotlight & tight-races")


def test_retired_race_code_404_is_skipped_not_fatal():
    events = {"CONTROLH-2026": (404, None), "CONTROLS-2026": (404, None)}
    # every SENATE_RACE_CODES ticker 404s (simulates a code that no longer
    # has an active market, e.g. after a cycle rolls over)
    with patch.object(po.requests.Session, "get", side_effect=fake_get_factory(events, fail_hosts=("votehub",))):
        client = po._KalshiClient(po.requests.Session())
        odds = po._fetch_odds(client)
    assert odds.house is None and odds.senate is None
    assert odds.tight_races == [] and odds.spotlight is None
    assert not odds.has_odds
    print("PASS: universal 404s degrade to empty odds, no exception")


def test_total_kalshi_outage_returns_none_not_exception():
    with patch.object(po.requests.Session, "get",
                      side_effect=fake_get_factory({}, fail_hosts=("kalshi", "votehub"))):
        result = po.get_poliodds(today=dt.date(2026, 9, 25))
    assert result is None, "a total outage must degrade to None so the section is dropped, not crash the brief"
    print("PASS: total outage -> None (section silently dropped), no exception raised")


def test_generic_ballot_and_approval_averaging():
    polls = {
        "generic-ballot": [
            {"pollster": "Marist", "end_date": "2026-09-20",
             "answers": [{"choice": "Democrat", "pct": 47}, {"choice": "Republican", "pct": 43}]},
            {"pollster": "Quinnipiac", "end_date": "2026-09-18",
             "answers": [{"choice": "Democrat", "pct": 46}, {"choice": "Republican", "pct": 44}]},
            {"pollster": "Marist", "end_date": "2026-09-10",  # older Marist poll -- should be superseded
             "answers": [{"choice": "Democrat", "pct": 40}, {"choice": "Republican", "pct": 50}]},
            {"pollster": "CampaignInc", "end_date": "2026-09-21", "internal": True,  # excluded
             "answers": [{"choice": "Democrat", "pct": 60}, {"choice": "Republican", "pct": 30}]},
            {"pollster": "YouGov", "end_date": "2026-09-19",
             "answers": [{"choice": "Democrat", "pct": 45}, {"choice": "Republican", "pct": 45}]},
        ],
        "approval": [
            {"pollster": "Marist", "end_date": "2026-09-20", "subject": "Donald Trump",
             "answers": [{"choice": "Approve", "pct": 43}, {"choice": "Disapprove", "pct": 54}]},
            {"pollster": "Quinnipiac", "end_date": "2026-09-18", "subject": "Donald Trump",
             "answers": [{"choice": "Approve", "pct": 41}, {"choice": "Disapprove", "pct": 56}]},
            {"pollster": "YouGov", "end_date": "2026-09-19", "subject": "Donald Trump",
             "answers": [{"choice": "Approve", "pct": 44}, {"choice": "Disapprove", "pct": 53}]},
        ],
    }
    with patch.object(po.requests.Session, "get", side_effect=fake_get_factory({}, polls, fail_hosts=("kalshi",))):
        with po.requests.Session() as session:
            ballot = po._generic_ballot(session, dt.date(2026, 9, 1))
            approval = po._approval(session, dt.date(2026, 9, 1))
    # 3 distinct pollsters after de-dup+exclude (Marist's newer poll wins, internal dropped)
    assert "3 polls" in ballot.detail, ballot.detail
    assert ballot.value.startswith("D +"), ballot.value  # (47-43)+(46-44)+(45-45) avg = D +1.7
    assert approval.value == "43%", approval.value  # (43+41+44)/3 = 42.67 -> 43%
    print("PASS: generic ballot & approval average correctly, de-dup by pollster, internal excluded")


def test_too_few_polls_returns_none_not_a_fake_average():
    polls = {"generic-ballot": [
        {"pollster": "Marist", "end_date": "2026-09-20",
         "answers": [{"choice": "Democrat", "pct": 47}, {"choice": "Republican", "pct": 43}]},
    ]}
    with patch.object(po.requests.Session, "get", side_effect=fake_get_factory({}, polls, fail_hosts=("kalshi",))):
        with po.requests.Session() as session:
            ballot = po._generic_ballot(session, dt.date(2026, 9, 1))
    assert ballot is None, "one poll must never be presented as an 'average'"
    print("PASS: below MIN_POLLS_FOR_AVERAGE correctly returns None instead of a misleading average")


def test_lone_minority_outcome_is_not_shown_as_leader():
    lone_low = [_market("Democratic Party", last_price=0.20, prev_price=0.22, volume=50_000)]
    lone_high = [_market("Republican Party", last_price=0.80, prev_price=0.78, volume=50_000)]
    assert po._line_from_markets("XX Senate", lone_low, "u") is None, \
        "a single 20% outcome must never be labeled the leader"
    line = po._line_from_markets("XX Senate", lone_high, "u")
    assert line.leader == "REP" and line.leader_pct == 80 and line.change_pts == 2
    print("PASS: lone sub-50% outcome skipped, lone majority outcome kept")


def test_approval_ignores_other_subjects_and_stale_polls():
    polls = {"approval": [
        {"pollster": "Marist", "end_date": "2026-09-20", "subject": "Donald Trump",
         "answers": [{"choice": "Approve", "pct": 43}, {"choice": "Disapprove", "pct": 54}]},
        {"pollster": "Quinnipiac", "end_date": "2026-09-18", "subject": "Donald Trump",
         "answers": [{"choice": "Approve", "pct": 41}, {"choice": "Disapprove", "pct": 56}]},
        {"pollster": "YouGov", "end_date": "2026-09-19", "subject": "Donald Trump",
         "answers": [{"choice": "Approve", "pct": 44}, {"choice": "Disapprove", "pct": 53}]},
        # Must be excluded: wrong subject, and a stale poll the server "forgot" to filter
        {"pollster": "Gallup", "end_date": "2026-09-20", "subject": "Congress",
         "answers": [{"choice": "Approve", "pct": 15}, {"choice": "Disapprove", "pct": 80}]},
        {"pollster": "Emerson", "end_date": "2026-03-01", "subject": "Donald Trump",
         "answers": [{"choice": "Approve", "pct": 20}, {"choice": "Disapprove", "pct": 75}]},
    ]}
    with patch.object(po.requests.Session, "get", side_effect=fake_get_factory({}, polls, fail_hosts=("kalshi",))):
        with po.requests.Session() as session:
            approval = po._approval(session, dt.date(2026, 9, 11))
    assert approval.value == "43%" and "3 polls" in approval.detail, (approval.value, approval.detail)
    assert approval.label == "Trump approval"
    print("PASS: approval excludes Congress-approval and stale polls")


def test_ticker_list_and_urls_regressions():
    assert "LA" not in po.SENATE_RACE_CODES, "SENATELA-26 is Kentucky, not Louisiana"
    assert po.SENATE_EVENT_OVERRIDES.get("KY") == "SENATELA-26"
    assert po.HOUSE_CONTROL_URL.endswith("/controls/house-winner/controlh-2026")
    assert len(set(po.SENATE_RACE_CODES)) == len(po.SENATE_RACE_CODES), "duplicate race code"
    print("PASS: KY maps to SENATELA-26, no LA code, House URL is the verified path, no duplicate codes")


def test_attribution_only_credits_sources_shown():
    sys.path.insert(0, "polly_brief")
    import template
    polls_only = po.PoliOdds(polls=[po.PollAverage("Generic ballot", "D +1.7", "avg of 6 polls")])
    html = template._poliodds_section(polls_only)
    assert "Kalshi" not in html and "VoteHub" in html
    odds_only = po.PoliOdds(house=po.OddsLine("House", "DEM", 90, 2, 90, 8, 1e6, po.HOUSE_CONTROL_URL))
    html = template._poliodds_section(odds_only)
    assert "Kalshi" in html and "VoteHub" not in html
    print("PASS: footer credits only the sources actually shown")


def test_stale_last_price_is_never_shown():
    # Last trade was at 60%, but nothing has traded in 24h and the live
    # quotes now sit at 70/72 -- the brief must show 71, not the stale 60.
    stale_but_quoted = [
        _market("Republican Party", last_price=0.60, prev_price=0.60, yes_bid=0.70, yes_ask=0.72,
                prev_bid=0.66, prev_ask=0.68, volume=50_000, volume_24h=0),
        _market("Democratic Party", last_price=0.40, prev_price=0.40, yes_bid=0.28, yes_ask=0.30,
                prev_bid=0.32, prev_ask=0.34, volume=50_000, volume_24h=0),
    ]
    line = po._line_from_markets("XX Senate", stale_but_quoted, "u")
    assert line.leader == "REP" and line.leader_pct == 71, (line.leader, line.leader_pct)
    assert line.change_pts == 4, line.change_pts  # 71 now vs 67 midpoint yesterday, like-for-like

    # Stale last trade AND a meaningless 5c/95c quote -> no trustworthy
    # current number at all, so the race is dropped, not shown stale.
    stale_wide = [
        _market("Republican Party", last_price=0.60, yes_bid=0.05, yes_ask=0.95, volume=50_000, volume_24h=0),
        _market("Democratic Party", last_price=0.40, yes_bid=0.05, yes_ask=0.95, volume=50_000, volume_24h=0),
    ]
    assert po._line_from_markets("XX Senate", stale_wide, "u") is None
    print("PASS: stale last trade replaced by live quote; unquotable stale market dropped")


def test_polls_older_than_a_week_are_ignored():
    today = dt.date(2026, 9, 25)
    since = today - dt.timedelta(days=po.POLL_WINDOW_DAYS)
    assert po.POLL_WINDOW_DAYS == 7
    polls = {"generic-ballot": [
        {"pollster": "Marist", "end_date": "2026-09-23",
         "answers": [{"choice": "Democrat", "pct": 47}, {"choice": "Republican", "pct": 43}]},
        {"pollster": "YouGov", "end_date": "2026-09-21",
         "answers": [{"choice": "Democrat", "pct": 45}, {"choice": "Republican", "pct": 45}]},
        {"pollster": "Quinnipiac", "end_date": "2026-09-18",  # exactly 7 days -- still in
         "answers": [{"choice": "Democrat", "pct": 46}, {"choice": "Republican", "pct": 44}]},
        {"pollster": "Emerson", "end_date": "2026-09-12",  # 13 days old -- out
         "answers": [{"choice": "Democrat", "pct": 30}, {"choice": "Republican", "pct": 60}]},
    ]}
    with patch.object(po.requests.Session, "get", side_effect=fake_get_factory({}, polls, fail_hosts=("kalshi",))):
        with po.requests.Session() as session:
            ballot = po._generic_ballot(session, since)
    assert ballot.detail == "avg of 3 polls, last 7 days", ballot.detail
    assert ballot.value == "D +2.0", ballot.value
    print("PASS: polls older than 7 days excluded; detail says 'last 7 days'")


def test_against_real_kalshi_snapshot():
    """Replays Kalshi's real API responses from 2026-09-25 (saved in
    kalshi_snapshot_2026-09-25.json) through the real code path."""
    import json, os
    here = os.path.dirname(os.path.abspath(__file__))
    events = json.load(open(os.path.join(here, "kalshi_snapshot_2026-09-25.json")))["events"]
    responses = {t: (200, m) for t, m in events.items()}
    with patch.object(po.requests.Session, "get", side_effect=fake_get_factory(responses, fail_hosts=("votehub",))):
        odds = po._fetch_odds(po._KalshiClient(po.requests.Session()))
    assert (odds.house.leader, odds.house.leader_pct, odds.house.change_pts) == ("DEM", 91, -1)
    assert (odds.senate.leader, odds.senate.leader_pct, odds.senate.change_pts) == ("DEM", 61, -3)
    assert odds.spotlight.label == "ME Senate" and odds.spotlight_kind == "Biggest mover"
    assert (odds.spotlight.leader, odds.spotlight.leader_pct, odds.spotlight.change_pts) == ("DEM", 58, 8)
    assert (odds.spotlight.runner_up, odds.spotlight.runner_up_pct) == ("REP", 42)

    # Every race must resolve to a party, never a bare candidate surname --
    # most real markets are labeled by candidate ("Ashley Hinson").
    lines = {t: po._line_from_markets(t, m, "u") for t, m in events.items()}
    for t, line in lines.items():
        assert line.leader in ("DEM", "REP", "IND"), (t, line.leader)
    # Independents: "-DOSB" must not be read as a Democrat, and the real
    # runner-up (Osborn) must be shown, not the ~0% Democrat.
    ne = lines["SENATENE-26"]
    assert (ne.leader, ne.leader_pct, ne.runner_up, ne.runner_up_pct) == ("REP", 73, "IND", 30)
    assert lines["SENATEIA-26"].leader == "REP" and lines["SENATEIA-26"].dem_pct == 44
    # Kentucky really lives at SENATELA-26; KY must resolve there.
    assert po.SENATE_EVENT_OVERRIDES["KY"] == "SENATELA-26" and "LA" not in po.SENATE_RACE_CODES
    print("PASS: real Kalshi snapshot -> DEM 91 House, DEM 61 Senate, ME biggest mover; all races party-labeled")


if __name__ == "__main__":
    test_normal_house_and_senate_with_change()
    test_thin_race_excluded_from_mover_and_tightest()
    test_retired_race_code_404_is_skipped_not_fatal()
    test_total_kalshi_outage_returns_none_not_exception()
    test_generic_ballot_and_approval_averaging()
    test_too_few_polls_returns_none_not_a_fake_average()
    test_lone_minority_outcome_is_not_shown_as_leader()
    test_approval_ignores_other_subjects_and_stale_polls()
    test_ticker_list_and_urls_regressions()
    test_attribution_only_credits_sources_shown()
    test_stale_last_price_is_never_shown()
    test_polls_older_than_a_week_are_ignored()
    test_against_real_kalshi_snapshot()
    print("\nAll tests passed.")
