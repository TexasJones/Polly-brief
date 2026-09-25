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
           prev_bid=None, prev_ask=None, volume=0, status="active"):
    m = {"yes_sub_title": sub_title, "status": status, "volume_fp": volume}
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
            resp.json.return_value = {"markets": markets}
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
            {"pollster": "Marist", "end_date": "2026-09-20", "subject": "Trump",
             "answers": [{"choice": "Approve", "pct": 43}, {"choice": "Disapprove", "pct": 54}]},
            {"pollster": "Quinnipiac", "end_date": "2026-09-18", "subject": "Trump",
             "answers": [{"choice": "Approve", "pct": 41}, {"choice": "Disapprove", "pct": 56}]},
            {"pollster": "YouGov", "end_date": "2026-09-19", "subject": "Trump",
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


if __name__ == "__main__":
    test_normal_house_and_senate_with_change()
    test_thin_race_excluded_from_mover_and_tightest()
    test_retired_race_code_404_is_skipped_not_fatal()
    test_total_kalshi_outage_returns_none_not_exception()
    test_generic_ballot_and_approval_averaging()
    test_too_few_polls_returns_none_not_a_fake_average()
    print("\nAll tests passed.")
