# The Polly Brief — generator + sender

Generates the daily Brief (Hiring Pulse, Top Stories, Featured Jobs,
Election Countdown) and emails it via Brevo — fully automated on a daily
GitHub Actions schedule.

## How it works
1. `jobs_snapshot.py` reads feed.xml from the political-jobs-feed repo
2. `news_snapshot.py` pulls headlines from 11 RSS sources + Axios (scraped),
   classifies into 6 topics: Campaigns, Media, AI+Policy, Energy, Finance,
