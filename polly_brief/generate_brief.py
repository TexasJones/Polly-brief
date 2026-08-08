#!/usr/bin/env python3

import argparse
import json
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET


# ------------------------------------------------------------
# CONFIG
# ------------------------------------------------------------

NEWS_FEEDS = {
    "Politico": "https://rss.politico.com/politics-news.xml",
    "The Hill": "https://thehill.com/feed/",
    "Axios": "https://www.axios.com/feeds/feed.rss",
    "Roll Call": "https://rollcall.com/feed/",
}


# ------------------------------------------------------------
# NEWS
# ------------------------------------------------------------

def fetch_feed(name, url, limit=3):
    """Fetch a simple RSS/Atom feed."""

    try:
        request = Request(
            url,
            headers={"User-Agent": "PollyBrief/1.0"}
        )

        with urlopen(request, timeout=15) as response:
            data = response.read()

        root = ET.fromstring(data)
        stories = []

        # RSS
        for item in root.findall(".//item")[:limit]:
            title = item.findtext("title", "")
            link = item.findtext("link", "")
            pub_date = item.findtext("pubDate", "")

            if title and link:
                stories.append({
                    "source": name,
                    "title": title.strip(),
                    "url": link.strip(),
                    "date": pub_date.strip(),
                })

        # Atom
        if not stories:
            ns = {"atom": "http://www.w3.org/2005/Atom"}

            for entry in root.findall(".//atom:entry", ns)[:limit]:
                title = entry.findtext("atom:title", "", ns)
                link = ""

                link_element = entry.find("atom:link", ns)
                if link_element is not None:
                    link = link_element.attrib.get("href", "")

                if title and link:
                    stories.append({
                        "source": name,
                        "title": title.strip(),
                        "url": link.strip(),
                        "date": "",
                    })

        return stories

    except Exception as e:
        print(f"WARNING: Could not load {name}: {e}")
        return []


def get_news():
    stories = []

    for name, url in NEWS_FEEDS.items():
        stories.extend(fetch_feed(name, url, limit=3))

    return stories[:12]


# ------------------------------------------------------------
# JOB DATA
# ------------------------------------------------------------

def load_job_data():
    """
    Look for a jobs.json file created by the existing Polly
    job pipeline. If it is not available, the brief still
    generates with default values.
    """

    possible_files = [
        Path("jobs.json"),
        Path("polly_brief/jobs.json"),
        Path("output/jobs.json"),
    ]

    for path in possible_files:
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                print(f"Loaded job data from {path}")
                return data

            except Exception as e:
                print(f"WARNING: Could not read {path}: {e}")

    print("No jobs.json found. Using zero/default job counts.")

    return {
        "active_jobs": 0,
        "new_today": 0,
        "campaign_jobs": 0,
        "public_affairs": 0,
        "communications": 0,
        "remote": 0,
        "top_employers": [],
        "featured_jobs": [],
    }


# ------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------

def number(value):
    try:
        return f"{int(value):,}"
    except Exception:
        return "0"


def election_countdown():
    election_day = datetime(2026, 11, 3, tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    days = (election_day.date() - now.date()).days
    return max(days, 0)


# ------------------------------------------------------------
# HTML COMPONENTS
# ------------------------------------------------------------

def news_card(story):
    source = escape(story.get("source", "News"))
    title = escape(story.get("title", "Political news"))
    url = escape(story.get("url", "#"), quote=True)

    return f"""
    <div class="story">
        <div class="story-source">{source}</div>
        <a href="{url}" target="_blank" class="story-title">{title}</a>
        <a href="{url}" target="_blank" class="read-more">Read story →</a>
    </div>
    """


def job_card(job):
    title = escape(job.get("title", "Political Opportunity"))
    company = escape(job.get("company", "Political Organization"))
    location = escape(job.get("location", "United States"))
    url = escape(job.get("url", "#"), quote=True)

    return f"""
    <div class="job">
        <div class="job-title">{title}</div>
        <div class="job-company">{company}</div>
        <div class="job-location">{location}</div>
        <a href="{url}" target="_blank" class="job-button">View Job →</a>
    </div>
    """


# ------------------------------------------------------------
# GENERATE NEWSLETTER
# ------------------------------------------------------------

def generate_html(jobs, news):

    today = datetime.now().strftime("%A, %B %-d, %Y")

    active_jobs = number(jobs.get("active_jobs", 0))
    new_today = number(jobs.get("new_today", 0))
    campaign_jobs = number(jobs.get("campaign_jobs", 0))
    public_affairs = number(jobs.get("public_affairs", 0))
    communications = number(jobs.get("communications", 0))
    remote = number(jobs.get("remote", 0))

    employers = jobs.get("top_employers", [])
    featured_jobs = jobs.get("featured_jobs", [])

    employer_html = ""

    for employer in employers[:5]:
        if isinstance(employer, dict):
            employer_name = employer.get("name", "Political Organization")
        else:
            employer_name = str(employer)

        employer_html += f"""
        <div class="employer">{escape(employer_name)}</div>
        """

    if not employer_html:
        employer_html = """
        <div class="empty">
            New hiring data coming soon.
        </div>
        """

    news_html = "".join(news_card(story) for story in news[:8])

    if not news_html:
        news_html = """
        <div class="empty">
            No news feeds were available this morning.
        </div>
        """

    jobs_html = "".join(job_card(job) for job in featured_jobs[:5])

    if not jobs_html:
        jobs_html = """
        <div class="empty">
            Featured jobs will appear here as Polly's job data is connected.
        </div>
        """

    days = election_countdown()

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>The Polly Brief</title>

<style>
body {{
    margin: 0;
    padding: 0;
    background: #f8f1e7;
    font-family: Arial, Helvetica, sans-serif;
    color: #111111;
}}

.container {{
    max-width: 680px;
    margin: 0 auto;
    padding: 30px 20px;
}}

.header {{
    background: #050505;
    color: white;
    padding: 26px;
    border-radius: 12px 12px 0 0;
}}

.logo {{
    font-size: 30px;
    font-weight: 800;
    letter-spacing: -1px;
}}

.tagline {{
    margin-top: 5px;
    color: #dddddd;
    font-size: 13px;
}}

.date {{
    margin-top: 20px;
    font-size: 13px;
    color: #bbbbbb;
}}

.intro {{
    background: white;
    padding: 25px;
    border-bottom: 1px solid #eeeeee;
}}

.intro h1 {{
    margin: 0 0 8px 0;
    font-size: 28px;
}}

.intro p {{
    margin: 0;
    color: #555555;
    line-height: 1.5;
}}

.section {{
    background: white;
    margin-top: 14px;
    padding: 25px;
}}

.section-title {{
    font-size: 20px;
    font-weight: 800;
    margin-bottom: 18px;
}}

.stats {{
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 10px;
}}

.stat {{
    background: #f5f5f5;
    padding: 17px;
    border-radius: 8px;
}}

.stat-number {{
    font-size: 27px;
    font-weight: 800;
}}

.stat-label {{
    font-size: 12px;
    color: #666666;
    margin-top: 4px;
}}

.story {{
    padding: 16px 0;
    border-top: 1px solid #eeeeee;
}}

.story-source {{
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    color: #777777;
    margin-bottom: 6px;
}}

.story-title {{
    color: #111111;
    font-size: 17px;
    line-height: 1.35;
    font-weight: 700;
    text-decoration: none;
}}

.read-more {{
    display: block;
    margin-top: 8px;
    font-size: 12px;
    font-weight: 700;
    color: #111111;
    text-decoration: none;
}}

.employer {{
    display: inline-block;
    background: #f1f1f1;
    padding: 9px 12px;
    border-radius: 20px;
    margin: 0 5px 7px 0;
    font-size: 12px;
    font-weight: 600;
}}

.job {{
    border: 1px solid #eeeeee;
    border-radius: 9px;
    padding: 17px;
    margin-bottom: 10px;
}}

.job-title {{
    font-weight: 800;
    font-size: 16px;
}}

.job-company {{
    margin-top: 5px;
    font-size: 13px;
    color: #555555;
}}

.job-location {{
    margin-top: 3px;
    font-size: 12px;
    color: #777777;
}}

.job-button {{
    display: inline-block;
    margin-top: 12px;
    background: #111111;
    color: white;
    padding: 8px 12px;
    border-radius: 5px;
    text-decoration: none;
    font-size: 12px;
    font-weight: 700;
}}

.countdown {{
    text-align: center;
    background: #111111;
    color: white;
    border-radius: 10px;
    padding: 25px;
}}

.countdown-number {{
    font-size: 42px;
    font-weight: 800;
}}

.countdown-label {{
    margin-top: 3px;
    font-size: 12px;
    color: #cccccc;
    text-transform: uppercase;
}}

.footer {{
    text-align: center;
    padding: 30px 10px;
    color: #777777;
    font-size: 11px;
}}

.empty {{
    color: #777777;
    font-size: 13px;
    padding: 10px 0;
}}

@media(max-width: 500px) {{
    .container {{
        padding: 10px;
    }}

    .stats {{
        grid-template-columns: 1fr 1fr;
    }}
}}
</style>
</head>

<body>
<div class="container">

    <div class="header">
        <div class="logo">Polly</div>
        <div class="tagline">
            The Talent Marketplace for Politics &amp; Public Affairs
        </div>
        <div class="date">{escape(today)}</div>
    </div>

    <div class="intro">
        <h1>The Polly Brief</h1>
        <p>
            What's happening in political hiring and campaign politics,
            in about 60 seconds.
        </p>
    </div>

    <div class="section">
        <div class="section-title">📊 Hiring Pulse</div>

        <div class="stats">
            <div class="stat">
                <div class="stat-number">{active_jobs}</div>
                <div class="stat-label">Active Jobs</div>
            </div>

            <div class="stat">
                <div class="stat-number">{new_today}</div>
                <div class="stat-label">New Today</div>
            </div>

            <div class="stat">
                <div class="stat-number">{campaign_jobs}</div>
                <div class="stat-label">Campaign Jobs</div>
            </div>

            <div class="stat">
                <div class="stat-number">{public_affairs}</div>
                <div class="stat-label">Public Affairs</div>
            </div>

            <div class="stat">
                <div class="stat-number">{communications}</div>
                <div class="stat-label">Communications</div>
            </div>

            <div class="stat">
                <div class="stat-number">{remote}</div>
                <div class="stat-label">Remote</div>
            </div>
        </div>
    </div>

    <div class="section">
        <div class="section-title">📰 Political News</div>
        {news_html}
    </div>

    <div class="section">
        <div class="section-title">🔥 Hiring Now</div>
        {employer_html}
    </div>

    <div class="section">
        <div class="section-title">👀 Jobs Worth Looking At</div>
        {jobs_html}
    </div>

    <div class="section">
        <div class="countdown">
            <div class="countdown-number">{days}</div>
            <div class="countdown-label">Days Until Election Day</div>
        </div>
    </div>

    <div class="footer">
        <strong>The Polly Brief</strong>
        <br><br>
        The daily briefing for politics,
        public affairs and campaign professionals.
        <br><br>
        Powered by Polly
    </div>

</div>
</body>
</html>
"""


# ------------------------------------------------------------
# MAIN
# ------------------------------------------------------------

def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="polly_brief.html")
    args = parser.parse_args()

    print("Starting Polly Brief...")

    jobs = load_job_data()
    news = get_news()

    print(f"Loaded {len(news)} news stories.")

    html = generate_html(jobs, news)

    output = Path(args.out).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    with open(output, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Polly Brief created: {output}")
    print(f"File size: {output.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
