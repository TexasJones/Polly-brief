"""
news_snapshot.py
-----------------
Builds the "Top Stories" section: one story per topic (Congress, Campaigns,
Politics & Money, Public Affairs), each with a short summary pulled from
the outlet's own RSS description — not freshly written, since that risks
misquoting or misstating what the article actually says.

Approach:
  1. Pull a pool of recent items from each outlet's RSS feed (Axios has no
     RSS, so it's scraped directly).
  2. Classify each item into one of the four topic sections by keyword
     match against its title.
  3. For each section, take the most recent matching item and clean its
     RSS summary down to ~2 sentences.

If a section has no matching story on a given day, it's flagged as empty
so the template can skip it cleanly instead of showing a stale/wrong item.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from html import unescape
from typing import Optional

import feedparser
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent":
