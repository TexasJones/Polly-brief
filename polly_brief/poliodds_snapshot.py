"""
PoliOdds Watch -- live prediction-market odds and polling averages for
The Polly Brief.

Two sources, both chosen because they're public, key-free, and explicitly
meant to be consumed this way (no scraping, no terms-of-service gray area):

  * Kalshi (CFTC-regulated prediction market) -- public market-data API,
    no account or API key needed for reads. Supplies:
      - House control after the 2026 midterms   (event CONTROLH-2026)
      - Senate control after the 2026 midterms  (event CONTROLS-2026)
      - Every 2026 Senate race by state          (events SENATE{ST}-26)
    Each Kalshi market also reports its price from 24 hours earlier
    (previous_price_dollars), so the day-over-day change arrows come
    straight from Kalshi -- no history file of our own needed.

  * VoteHub -- free public polling API, licensed CC BY 4.0 (attribution
    required, which template.py renders in the section footer). Supplies
    the generic congressional ballot and presidential approval. VoteHub
    returns individual polls, not averages, so this module averages the
    most recent poll per pollster over the last POLL_WINDOW_DAYS (7) days.

No old data: Kalshi prices are only used if the market traded in the last
24 hours (else the live bid/ask quote, else skipped -- see _prices()), and
polls older than a week are ignored. Nothing is cached between runs; every
brief pulls fresh numbers the morning it sends.

Deliberately NOT used:
  * RealClearPolling -- no official API; the only way in is scraping, and
    its terms didn't confirm that's allowed.
  * Polymarket -- public API, but its current docs don't document the
    price fields, so parsing them would be guesswork. Easy phase-2 add
    once that's confirmed against a live response.

Everything here is fail-safe: any network error, schema surprise, or
outage returns None (or drops just the affected line), and template.py
drops the whole section when there's nothing to show. A Kalshi hiccup can
never block the brief from sending.

Run directly for a smoke test:  python3 polly_brief/poliodds_snapshot.py
"""
from __future__ import annotations

import datetime as dt
import time
from dataclasses import dataclass, field
from typing import Optional

import requests

# --- Endpoints -------------------------------------------------------------
# Host per Kalshi's current "Quick Start: Market Data" docs.
KALSHI_BASE = "https://external-api.kalshi.com/trade-api/v2"
KALSHI_WEB = "https://kalshi.com/markets"
KALSHI_MIDTERMS_URL = "https://kalshi.com/category/elections/midterms"
VOTEHUB_BASE = "https://api.votehub.com"
VOTEHUB_WEB = "https://votehub.com/polls/"

HEADERS = {
    "Accept": "application/json",
    "User-Agent": "PollyBrief/1.0 (+https://thepolly.co)",
}
TIMEOUT_SECONDS = 8
REQUEST_SPACING_SECONDS = 0.05  # polite pacing across ~36 Kalshi calls

# --- What we watch ---------------------------------------------------------
HOUSE_CONTROL_EVENT = "CONTROLH-2026"
SENATE_CONTROL_EVENT = "CONTROLS-2026"
# Both use Kalshi's full "controls/{chamber}-winner/{ticker}" path rather
# than a shorter guessed slug -- this exact path was directly confirmed
# live for both chambers (not just inferred from the ticker naming
# pattern), so it's the one link we know resolves correctly instead of
# one confirmed path plus one unverified shortcut.
HOUSE_CONTROL_URL = f"{KALSHI_WEB}/controls/house-winner/controlh-2026"
SENATE_CONTROL_URL = f"{KALSHI_WEB}/controls/senate-winner/controls-2026"

# Every 2026 Senate seat: the Class 2 seats plus the Ohio and Florida
# special elections (Kalshi marks specials with a trailing "S": SENATEOHS,
# SENATEFLS). Any code Kalshi doesn't have a market for simply 404s and is
# skipped, so a wrong or retired code costs one wasted request, not a
# broken section. After Nov 3 these resolve and fall away on their own;
# swap this list (and the two control events above) for the next cycle.
#
# Every code below was checked against Kalshi's live API on 2026-09-25:
# each event's own title names the expected state ("Iowa Senate winner?",
# etc.). The one exception is Kentucky -- Kalshi files it under
# "SENATELA-26" (its title really is "Kentucky Senate winner?", and
# "SENATEKY-26" returns 404), so Kentucky is mapped explicitly in
# SENATE_EVENT_OVERRIDES. Louisiana is left out: its race uses a different
# scheme ("KXSENATELA-26NOV") that hasn't been checked, and templating
# "SENATELA-26" for it would fetch KENTUCKY's odds and label them "LA".
SENATE_RACE_CODES = (
    "AK", "AL", "AR", "CO", "DE", "FLS", "GA", "IA", "ID", "IL", "KS", "KY",
    "MA", "ME", "MI", "MN", "MS", "MT", "NC", "NE", "NH", "NJ", "NM",
    "OHS", "OK", "OR", "RI", "SC", "SD", "TN", "TX", "VA", "WV", "WY",
)
SENATE_RACE_EVENT = "SENATE{code}-26"
SENATE_EVENT_OVERRIDES = {"KY": "SENATELA-26"}

# --- Selection tuning ------------------------------------------------------
# Thin markets can swing 10+ points on a few hundred dollars, which would
# make "Biggest mover" pure noise. Races below this many contracts traded
# are ignored for mover/tightest picks (control markets are always shown).
MIN_RACE_VOLUME_CONTRACTS = 5_000
# A race has to move at least this much in 24h to be called a "mover";
# otherwise the spotlight card goes to the tightest race instead.
MOVER_MIN_POINTS = 2
# Set to 0 (the leaner layout Chris picked over the full version with
# extra split-bar rows): control cards + one spotlight race only. The
# selection logic below is unchanged either way -- it still computes the
# full sorted list, this just slices it down to nothing -- so bumping
# this back up later to bring the extra rows back is a one-line change,
# not a re-implementation.
TIGHT_RACES_SHOWN = 0
# Stop hammering Kalshi if it's clearly down, rather than timing out 36x.
MAX_CONSECUTIVE_FAILURES = 5
# No stale prices: see _prices(). A market with no trades in the last 24h
# falls back to its live bid/ask midpoint, but only if the spread is at
# most this wide (10 cents = 10 points); otherwise it isn't shown at all.
MAX_QUOTE_SPREAD = 0.10

# No stale polls: only polls that finished fieldwork in the last week
# count. If fewer than MIN_POLLS_FOR_AVERAGE pollsters released one in that
# window, that poll line is left out for the day rather than padded with
# older polls. (Was 14; tightened to 7 at Chris's request -- no old data.)
POLL_WINDOW_DAYS = 7
MIN_POLLS_FOR_AVERAGE = 3  # never present one or two polls as an "average"
# VoteHub's documented subject values for approval polls are "Congress",
# "Donald Trump" and "Supreme Court" (from its /subjects docs) -- so the
# server-side filter has to use the full name. The client-side filter in
# _approval() matches on APPROVAL_MATCH as a second line of defence, so
# Congress or Supreme Court approval can never be averaged in by mistake.
APPROVAL_SUBJECT = "Donald Trump"
APPROVAL_MATCH = "trump"
APPROVAL_LABEL = "Trump approval"


@dataclass
class OddsLine:
    """One market, reduced to what the brief shows."""
    label: str                 # "House", "Senate", "NC Senate"
    leader: str                # "DEM", "REP", "IND", or a short name
    leader_pct: int            # leader's chance, 0-100
    change_pts: Optional[int]  # leader's 24h change in points; None if unknown
    dem_pct: Optional[int]
    rep_pct: Optional[int]
    volume: float              # contracts traded (liquidity signal)
    url: str
    # Second-place outcome. Not always the other major party: in Nebraska
    # it's independent Dan Osborn (~30%) while the Democrat is under 1%, so
    # the brief shows leader vs runner-up rather than a fixed "D vs R".
    runner_up: Optional[str] = None
    runner_up_pct: Optional[int] = None

    @property
    def closeness(self) -> int:
        """Distance from a coin flip -- smaller is tighter."""
        return abs(self.leader_pct - 50)


@dataclass
class PollAverage:
    label: str      # "Generic ballot", "Trump approval"
    value: str      # "D +2.4", "43% approve"
    detail: str     # "avg of 5 polls, last 7 days"


@dataclass
class PoliOdds:
    house: Optional[OddsLine] = None
    senate: Optional[OddsLine] = None
    spotlight: Optional[OddsLine] = None
    spotlight_kind: str = ""                  # "Biggest mover" / "Tightest race"
    tight_races: list[OddsLine] = field(default_factory=list)
    polls: list[PollAverage] = field(default_factory=list)

    @property
    def has_odds(self) -> bool:
        return bool(self.house or self.senate or self.spotlight or self.tight_races)

    @property
    def has_content(self) -> bool:
        return self.has_odds or bool(self.polls)


# --- Kalshi ----------------------------------------------------------------

def _to_float(value) -> Optional[float]:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _dollars(market: dict, base: str) -> Optional[float]:
    """Read a price as a 0-1 probability. Prefers Kalshi's current
    `<base>_dollars` string fields; falls back to the older integer-cents
    fields in case an older response shape ever comes back."""
    value = _to_float(market.get(f"{base}_dollars"))
    if value is not None:
        return value
    cents = _to_float(market.get(base))
    return cents / 100.0 if cents is not None else None


def _volume_24h(market: dict) -> Optional[float]:
    """Contracts traded in the last 24 hours (Kalshi's `volume_24h_fp`),
    or None if the field isn't there."""
    for key in ("volume_24h_fp", "volume_24h"):
        value = _to_float(market.get(key))
        if value is not None:
            return value
    return None


def _midpoint(market: dict, prefix: str = "") -> Optional[float]:
    """Midpoint of the standing yes bid/ask. Current quotes are live by
    definition, but a wide spread (say 5c bid / 95c ask) says nothing about
    the real odds, so anything wider than MAX_QUOTE_SPREAD is refused."""
    bid = _dollars(market, f"{prefix}yes_bid")
    ask = _dollars(market, f"{prefix}yes_ask")
    if bid is None or ask is None or not (0 < bid <= ask) or ask - bid > MAX_QUOTE_SPREAD:
        return None
    return (bid + ask) / 2


def _prices(market: dict) -> tuple[Optional[float], Optional[float]]:
    """(current, 24-hours-ago) implied probability -- or (None, None) when
    there's no CURRENT number we trust, so the market is skipped.

    Freshness rule: a market's "last price" is simply its most recent trade,
    whenever that was -- in a quiet race that can be days or weeks old and
    still look current. So the last trade is only used when Kalshi confirms
    the market actually traded in the last 24 hours. Otherwise the live
    bid/ask midpoint is used, and if the spread is too wide to mean
    anything, the market is dropped rather than shown with a stale number.
    The 24h-ago value always comes from the same kind of price as the
    current one, so the change arrow is like-for-like."""
    if (_volume_24h(market) or 0) > 0:
        last = _dollars(market, "last_price")
        if last is not None and last > 0:
            prev = _dollars(market, "previous_price")
            return last, (prev if prev is not None and prev > 0 else None)
    mid = _midpoint(market)
    if mid is not None:
        return mid, _midpoint(market, "previous_")
    return None, None


def _volume(market: dict) -> float:
    for key in ("volume_fp", "volume"):
        value = _to_float(market.get(key))
        if value is not None:
            return value
    return 0.0


def _outcome_key(market: dict) -> Optional[str]:
    """Party of one outcome market: "DEM", "REP", "IND", or (last resort)
    a short candidate name.

    Checked against Kalshi's live 2026 Senate data (2026-09-25): most race
    markets label the outcome by CANDIDATE in yes_sub_title ("Ashley
    Hinson", "Jon Ossoff"), and only a few by party ("Democratic party"),
    so yes_sub_title alone can't be trusted for party. Party comes from:
      1. the ticker's final segment when it's exactly D or R
         ("SENATEIA-26-R"). Exact match only: independents get their own
         suffixes -- "-IND" (Montana), but also "-DOSB" (Dan Osborn,
         Nebraska) and "-TACH" (Todd Achilles, Idaho) -- so a "starts with
         D" test would call Osborn a Democrat.
      2. otherwise the words in `subtitle` / `yes_sub_title`, which carry
         the party for every live market seen ("Republican party:: ...",
         "Dan Osborn:: Independent", "Democratic (DFL) party").
    """
    suffix = str(market.get("ticker") or "").rsplit("-", 1)[-1].upper()
    if suffix == "D":
        return "DEM"
    if suffix == "R":
        return "REP"
    text = " ".join(str(market.get(k) or "") for k in ("subtitle", "yes_sub_title")).lower()
    if "democrat" in text:
        return "DEM"
    if "republican" in text:
        return "REP"
    if "independent" in text:
        return "IND"
    name = str(market.get("yes_sub_title") or market.get("title") or "").strip()
    # Unlabeled outcome -- keep it under a short name so a leader is never
    # silently dropped.
    return name.split()[-1].upper()[:12] if name else None


def _is_live(market: dict) -> bool:
    return market.get("status") in (None, "", "active", "open")


class _KalshiClient:
    def __init__(self, session: requests.Session):
        self.session = session
        self.consecutive_failures = 0

    @property
    def gave_up(self) -> bool:
        return self.consecutive_failures >= MAX_CONSECUTIVE_FAILURES

    def event_markets(self, event_ticker: str) -> Optional[list[dict]]:
        if self.gave_up:
            return None
        time.sleep(REQUEST_SPACING_SECONDS)
        try:
            resp = self.session.get(
                f"{KALSHI_BASE}/events/{event_ticker}",
                params={"with_nested_markets": "true"},
                headers=HEADERS, timeout=TIMEOUT_SECONDS,
            )
            if resp.status_code == 404:
                # Reachable, just no such event -- not a failure.
                self.consecutive_failures = 0
                return None
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:  # network, HTTP, or JSON error
            self.consecutive_failures += 1
            print(f"    [poliodds] Kalshi {event_ticker} failed: {exc}")
            return None
        self.consecutive_failures = 0
        # Markets come back top-level or nested under "event" depending on
        # with_nested_markets support -- accept either.
        return data.get("markets") or (data.get("event") or {}).get("markets") or []


def _line_from_markets(label: str, markets: list[dict], url: str) -> Optional[OddsLine]:
    outcomes: dict[str, tuple[float, Optional[float], float]] = {}
    for market in markets:
        if not _is_live(market):
            continue
        key = _outcome_key(market)
        now, prev = _prices(market)
        if key is None or now is None or key in outcomes:
            continue
        outcomes[key] = (now, prev, _volume(market))
    if not outcomes:
        return None

    leader_key, (leader_now, leader_prev, _) = max(outcomes.items(), key=lambda kv: kv[1][0])
    # If only ONE outcome came back (a single yes/no market, or the other
    # side's market paused), "highest of one" isn't a leader: a lone
    # "Democratic party" market at 20% would otherwise be shown as
    # "DEM 20%" leading. The other side can't be safely inferred either --
    # it might be an independent (e.g. Nebraska), not the other party --
    # so a lone sub-50% outcome is skipped rather than mislabeled.
    if len(outcomes) == 1 and leader_now < 0.5:
        return None
    leader_pct = round(leader_now * 100)
    # `is not None`, not truthiness: _prices() happens never to return 0.0
    # today, but this shouldn't silently depend on that.
    change = (leader_pct - round(leader_prev * 100)) if leader_prev is not None else None

    def pct(key: str) -> Optional[int]:
        return round(outcomes[key][0] * 100) if key in outcomes else None

    others = sorted(((k, v[0]) for k, v in outcomes.items() if k != leader_key),
                    key=lambda kv: kv[1], reverse=True)
    runner_up, runner_up_pct = (others[0][0], round(others[0][1] * 100)) if others else (None, None)

    return OddsLine(
        label=label, leader=leader_key, leader_pct=leader_pct, change_pts=change,
        dem_pct=pct("DEM"), rep_pct=pct("REP"),
        volume=sum(v for _, _, v in outcomes.values()), url=url,
        runner_up=runner_up, runner_up_pct=runner_up_pct,
    )


STATE_NAMES = {
    "AK": "Alaska", "AL": "Alabama", "AR": "Arkansas", "CO": "Colorado", "DE": "Delaware",
    "FL": "Florida", "GA": "Georgia", "IA": "Iowa", "ID": "Idaho", "IL": "Illinois",
    "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana", "MA": "Massachusetts", "ME": "Maine",
    "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi", "MT": "Montana",
    "NC": "North Carolina", "NE": "Nebraska", "NH": "New Hampshire", "NJ": "New Jersey",
    "NM": "New Mexico", "OH": "Ohio", "OK": "Oklahoma", "OR": "Oregon", "RI": "Rhode Island",
    "SC": "South Carolina", "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas",
    "VA": "Virginia", "WV": "West Virginia", "WY": "Wyoming",
}


def _race_label(code: str) -> str:
    """"Maine Senate", "Ohio Senate (special)" -- full state names read
    better in the brief than postal codes ("ME Senate")."""
    state = STATE_NAMES.get(code[:2], code[:2])
    return f"{state} Senate" + (" (special)" if len(code) == 3 else "")


def _fetch_odds(client: _KalshiClient) -> PoliOdds:
    odds = PoliOdds()

    markets = client.event_markets(HOUSE_CONTROL_EVENT)
    if markets:
        odds.house = _line_from_markets("House", markets, HOUSE_CONTROL_URL)
    markets = client.event_markets(SENATE_CONTROL_EVENT)
    if markets:
        odds.senate = _line_from_markets("Senate", markets, SENATE_CONTROL_URL)

    races: list[OddsLine] = []
    for code in SENATE_RACE_CODES:
        if client.gave_up:
            print("    [poliodds] Kalshi unreachable -- skipping remaining races")
            break
        event = SENATE_EVENT_OVERRIDES.get(code) or SENATE_RACE_EVENT.format(code=code)
        markets = client.event_markets(event)
        if not markets:
            continue
        series = event.rsplit("-", 1)[0].lower()
        line = _line_from_markets(_race_label(code), markets, f"{KALSHI_WEB}/{series}/{event.lower()}")
        if line and line.volume >= MIN_RACE_VOLUME_CONTRACTS:
            races.append(line)

    if not races:
        return odds

    movers = [r for r in races if r.change_pts is not None and abs(r.change_pts) >= MOVER_MIN_POINTS]
    if movers:
        odds.spotlight = max(movers, key=lambda r: (abs(r.change_pts), -r.closeness))
        odds.spotlight_kind = "Biggest mover"
    else:
        odds.spotlight = min(races, key=lambda r: (r.closeness, -r.volume))
        odds.spotlight_kind = "Tightest race"

    remaining = [r for r in races if r is not odds.spotlight]
    odds.tight_races = sorted(remaining, key=lambda r: (r.closeness, -r.volume))[:TIGHT_RACES_SHOWN]
    return odds


# --- VoteHub ---------------------------------------------------------------

def _fetch_polls(session: requests.Session, poll_type: str, since: dt.date,
                 subject: Optional[str] = None) -> list[dict]:
    params = {"poll_type": poll_type, "from_date": since.isoformat()}
    if subject:
        params["subject"] = subject
    try:
        resp = session.get(f"{VOTEHUB_BASE}/polls", params=params,
                           headers=HEADERS, timeout=TIMEOUT_SECONDS)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        print(f"    [poliodds] VoteHub {poll_type} failed: {exc}")
        return []
    if isinstance(data, dict):
        data = data.get("polls") or data.get("data") or []
    if not isinstance(data, list):
        return []
    # from_date is documented as filtering server-side, but re-check here
    # anyway: if it were ever ignored, a pollster whose last poll was months
    # ago would otherwise be averaged in as if it were current. ISO dates
    # (with or without a time part) compare correctly as strings. Undated
    # polls are dropped -- their freshness can't be confirmed.
    cutoff = since.isoformat()
    return [p for p in data
            if isinstance(p, dict) and str(p.get("end_date") or "")[:10] >= cutoff]


def _latest_per_pollster(polls: list[dict]) -> list[dict]:
    """One poll per pollster (their most recent), so a pollster that
    publishes daily can't dominate the average. Internal campaign polls
    are excluded."""
    latest: dict[str, dict] = {}
    for poll in polls:
        if poll.get("internal"):
            continue
        name = (poll.get("pollster") or "").strip().lower() or f"id:{poll.get('id')}"
        end = str(poll.get("end_date") or "")
        if name not in latest or end > str(latest[name].get("end_date") or ""):
            latest[name] = poll
    return list(latest.values())


def _answer_pct(poll: dict, *needles: str, exclude: tuple[str, ...] = ()) -> Optional[float]:
    for answer in poll.get("answers") or []:
        choice = str(answer.get("choice") or "").lower()
        if any(n in choice for n in needles) and not any(x in choice for x in exclude):
            return _to_float(answer.get("pct"))
    return None


def _generic_ballot(session: requests.Session, since: dt.date) -> Optional[PollAverage]:
    margins = []
    for poll in _latest_per_pollster(_fetch_polls(session, "generic-ballot", since)):
        dem = _answer_pct(poll, "dem")
        rep = _answer_pct(poll, "rep")
        if dem is not None and rep is not None:
            margins.append(dem - rep)
    if len(margins) < MIN_POLLS_FOR_AVERAGE:
        return None
    avg = sum(margins) / len(margins)
    value = "Tied" if abs(avg) < 0.05 else f"{'D' if avg > 0 else 'R'} +{abs(avg):.1f}"
    return PollAverage("Generic ballot", value, f"avg of {len(margins)} polls, last {POLL_WINDOW_DAYS} days")


def _approval(session: requests.Session, since: dt.date) -> Optional[PollAverage]:
    def is_subject(poll: dict) -> bool:
        return APPROVAL_MATCH in str(poll.get("subject") or "").lower()

    # Always filter client-side, even when the server-side subject filter
    # was used -- never average Congress/Supreme Court approval in.
    polls = [p for p in _fetch_polls(session, "approval", since, subject=APPROVAL_SUBJECT) if is_subject(p)]
    if not polls:  # subject naming may differ -- fetch unfiltered, filter here
        polls = [p for p in _fetch_polls(session, "approval", since) if is_subject(p)]
    approves, nets = [], []
    for poll in _latest_per_pollster(polls):
        approve = _answer_pct(poll, "approve", exclude=("disapprove",))
        disapprove = _answer_pct(poll, "disapprove")
        if approve is not None and disapprove is not None:
            approves.append(approve)
            nets.append(approve - disapprove)
    if len(approves) < MIN_POLLS_FOR_AVERAGE:
        return None
    approve_avg = sum(approves) / len(approves)
    net_avg = sum(nets) / len(nets)
    sign = "+" if net_avg >= 0 else "−"
    return PollAverage(APPROVAL_LABEL, f"{approve_avg:.0f}%",
                       f"net {sign}{abs(net_avg):.0f} · avg of {len(approves)} polls, last {POLL_WINDOW_DAYS} days")


# --- Entry point -----------------------------------------------------------

def get_poliodds(today: Optional[dt.date] = None) -> Optional[PoliOdds]:
    """Everything PoliOdds Watch needs, or None if there's nothing usable
    (in which case template.py leaves the section out entirely)."""
    today = today or dt.date.today()
    try:
        with requests.Session() as session:
            odds = _fetch_odds(_KalshiClient(session))
            since = today - dt.timedelta(days=POLL_WINDOW_DAYS)
            odds.polls = [p for p in (_generic_ballot(session, since), _approval(session, since)) if p]
    except Exception as exc:  # belt and braces -- never break the brief
        print(f"    [poliodds] unexpected error, section skipped: {exc}")
        return None
    return odds if odds.has_content else None


def _describe(line: Optional[OddsLine]) -> str:
    if not line:
        return "(none)"
    change = "n/a" if line.change_pts is None else f"{line.change_pts:+d}"
    return f"{line.label}: {line.leader} {line.leader_pct}% (24h {change}, vol {line.volume:,.0f})"


if __name__ == "__main__":
    result = get_poliodds()
    if not result:
        print("No PoliOdds data available.")
    else:
        print("House:    ", _describe(result.house))
        print("Senate:   ", _describe(result.senate))
        print(f"Spotlight ({result.spotlight_kind or '-'}):", _describe(result.spotlight))
        for race in result.tight_races:
            print("Tight:    ", _describe(race))
        for poll in result.polls:
            print(f"Poll:      {poll.label}: {poll.value} ({poll.detail})")
