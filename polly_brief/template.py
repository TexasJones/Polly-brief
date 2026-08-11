from __future__ import annotations
import datetime as dt
import html
from typing import Optional
from jobs_snapshot import HiringPulse, JobPosting
from news_snapshot import TopStory

INK = '#161616'
MUTED = '#767676'
ACCENT = '#2B5A4D'
ACCENT_LIGHT = '#E4EDE9'
HAIRLINE = '#E7E5E0'
BG = '#F4F3EF'
CARD = '#FFFFFF'
ELECTION_DAY = dt.date(2026, 11, 3)

def _esc(s):
    return html.escape(s or '')

def _days_until_election(today=None):
    today = today or dt.date.today()
    return max((ELECTION_DAY - today).days, 0)

def _divider():
    a = '<tr><td style="padding:0 40px;">'
    b = '<div style="border-top:1px solid ' + HAIRLINE + '; margin:28px 0;"></div>'
    c = '</td></tr>'
    return a + b + c

def _section_heading(emoji, title):
    a = '<div style="font-size:15px; font-weight:700; color:' + INK + '; margin-bottom:16px;">'
    return a + emoji + ' ' + _esc(title) + '</div>'

def _list_row(text):
    a = '<tr><td style="padding:3px 0; font-size:14px; color:' + INK + ';">'
    return a + _esc(text) + '</td></tr>'

def _stat_block(number, label, url=None):
    a = '<td style="padding-right:12px;">'
    open_tag = '<a href="' + url + '" target="_blank" rel="noopener noreferrer" style="text-decoration:none;">' if url else '<div>'
    close_tag = '</a>' if url else '</div>'
    b = open_tag + '<div style="background-color:' + ACCENT_LIGHT + '; border-radius:10px; padding:16px 20px;">'
    c = '<div style="font-size:30px; font-weight:800; color:' + ACCENT + '; letter-spacing:-0.5px;">'
    d = number + '</div>'
    e = '<div style="font-size:11px; color:' + MUTED + '; text-transform:uppercase; letter-spacing:0.6px; margin-top:2px;">'
    f = _esc(label) + '</div></div>' + close_tag + '</td>'
    return a + b + c + d + e + f

def _story_block(story):
    heading = _section_heading(story.emoji, story.section)
    if not story.item:
        a = '<tr><td style="padding-bottom:6px;">' + heading
        b = '<div style="font-size:13px; color:' + MUTED + '; font-style:italic;">'
        c = 'No story matched this section today.</div></td></tr>'
        return a + b + c
    item = story.item
    summary_html = ''
    if item.summary:
        s1 = '<div style="font-size:14px; color:' + MUTED + '; line-height:1.5; margin:6px 0 10px 0;">'
        summary_html = s1 + _esc(item.summary) + '</div>'
    a = '<tr><td style="padding-bottom:6px;">' + heading
    b = '<div style="font-size:15px; font-weight:600; color:' + INK + '; line-height:1.4;">'
    c = _esc(item.title) + '</div>' + summary_html
    d = '<a href="' + _esc(item.url) + '" target="_blank" rel="noopener noreferrer" style="font-size:13px; font-weight:700; color:' + ACCENT + '; text-decoration:none;">'
    e = 'Read More &rarr;</a></td></tr>'
    return a + b + c + d + e

def _job_block(job):
    location = _esc(job.location) if job.location else ''
    company = _esc(job.company)
    parts = [p for p in [company, location] if p]
    meta = ' &middot; '.join(parts)
    a = '<tr><td style="padding-bottom:10px;">'
    b = '<div style="background-color:' + BG + '; border-radius:10px; padding:14px 18px;">'
    c = '<a href="' + _esc(job.url) + '" target="_blank" rel="noopener noreferrer" style="font-size:15px; font-weight:700; color:' + ACCENT + '; text-decoration:none;">'
    d = _esc(job.title) + '</a>'
    e = '<div style="font-size:13px; color:' + MUTED + '; margin-top:4px;">' + meta + '</div></div></td></tr>'
    return a + b + c + d + e

def render_brief(pulse, top_stories, featured_jobs, quote_text=None, quote_source=None, today=None):
    today = today or dt.date.today()
    date_label = today.strftime('%A, %B %-d, %Y')

    category_rows = ''.join(_list_row(name) for name, _c in pulse.top_categories)
    if not category_rows:
        category_rows = '<tr><td style="font-size:13px; color:' + MUTED + ';">No category data available.</td></tr>'

    employer_rows = ''.join(_list_row(name) for name, _c in pulse.top_employers)
    if not employer_rows:
        employer_rows = '<tr><td style="font-size:13px; color:' + MUTED + ';">No employer data available.</td></tr>'

    story_rows = ''
    for i, s in enumerate(top_stories):
        if i > 0:
            story_rows += _divider()
        story_rows += _story_block(s)

    job_rows = ''
    for i, j in enumerate(featured_jobs):
        job_rows += _job_block(j)
    if not job_rows:
        job_rows = '<tr><td style="font-size:13px; color:' + MUTED + ';">No featured jobs today.</td></tr>'

    days_left = _days_until_election(today)

    quote_section = ''
    if quote_text:
        attribution = ''
        if quote_source:
            a1 = '<div style="font-size:13px; color:' + MUTED + '; margin-top:8px;">'
            attribution = a1 + '&mdash; ' + _esc(quote_source) + '</div>'
        qh = _section_heading('\U0001F4AC', 'Quote of the Day')
        q1 = _divider() + '<tr><td style="padding:0 40px;">' + qh
        q2 = '<div style="font-size:16px; color:' + INK + '; font-style:italic; line-height:1.5;">'
        q3 = '&ldquo;' + _esc(quote_text) + '&rdquo;</div>' + attribution + '</td></tr>'
        quote_section = q1 + q2 + q3

    parts = []
    parts.append('<!DOCTYPE html><html><head>')
    parts.append('<meta charset="utf-8">')
    parts.append('<meta name="viewport" content="width=device-width, initial-scale=1.0">')
    parts.append('<title>The Polly Brief</title></head>')
    parts.append('<body style="margin:0; padding:0; background-color:' + BG + '; font-family:sans-serif;">')
    parts.append('<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:' + BG + '; padding:32px 0;">')
    parts.append('<tr><td align="center">')
    parts.append('<table role="presentation" width="600" cellpadding="0" cellspacing="0" style="background-color:' + CARD + '; border-radius:12px; overflow:hidden;">')
    parts.append('<tr><td style="background-color:' + ACCENT + '; height:6px; line-height:6px; font-size:0;">&nbsp;</td></tr>')
    parts.append('<tr><td style="padding:36px 40px 24px 40px;">')
    parts.append('<table role="presentation" cellpadding="0" cellspacing="0"><tr>')
    parts.append('<td style="padding-right:10px; vertical-align:middle;"><img src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAK0AAABaCAYAAADKONbiAAAbXklEQVR4nO19eVgUV7r375yqgoZmkc0dFFRkMSriAm6tIsRokkFCozG4TJKR+cbcGTRek1wz6SbJTBLR5PqMmuv1i0acJ04aNXEc830zGoVkoolj1IlLNEZRFFFQxw1Uurve+0efwkLRq4lAY+r3PO8jS9HWOfU7b73n3Q6DAQM/EkTE7Ha7VFBQ4BLfB+/cuTPd4XDE1dXVjVIUhfn5+UFRFLjdblZbW0tms7l7VVXVyv79+1f/7Gc/2xkVFfVFTU0NAMBqtUrFxcXuFh2UgQcXRMR0X/ts2LDh6cmTJx/s1asXBQUFkSzLJEkSybJcL5IkEQAKCAigqKgoSklJUZ977rn/v379+hwi6io+juk/24CB+wKHwyEBABG1Wbt27c9nzJhxODY2lgAQADcAl/j3FmGMqeL3LgDEGKNu3bpRTk7O5eLi4qdNJhNgENfA/YTVatUI22727Nl7evToUU9WzrmbMaZ9f0dhjBHnnBhj9QROSEigRYsWLTebzbDZbLJBXAM/GtOnT1cAYPfu3Var1XpWENTJOXdzzu+KrI0J55wkSVIBXO/RowctX778bQBITk5WmneEBh4oWCwWGQBWrVr1K4vF4oZHW961Zr0bEcSt69Gjh/qnP/1pCnDDFDFg4K4hXtEy5xwffPBBdrdu3dwAVEmS7ith0ZC47iFDhtDmzZsfAQziGrgHCMJKnHO89dZbC5KTkzXbVcV9JqsmjDGSJMkFQE1JSTlx4cKFEADcZrPx5hq3gdYLBkBSFAVPP/30O6GhoYQbu/8mISwaktdpMplozpw57zLG6s0TAwYaBRGx5ORkRZZlzJo16+327dsTgLqm1LA3C+fcDcA9bty440QUDM8iMmCgcWhazWaz/b5Dhw4EoK4p7Nc7ifBGuBISEuirr756qhmGbaC1wmKxyIwxrFix4rWoqCgC4BSbo2YlrRBncHCw+sYbbxQ2w9ANtEZou/TNmzdn9uvXj9DEm667EGebNm2osLDQ3sRDN9AaoQvNRj366KMXALiEXdkihBXmgTspKYmOHDkytImHb6C1QRCWXb16tfuTTz5ZKUkStSRhAY/rC4ArLi6OtmzZMhXGRsyABs0XS0QsLy/vUy00ixYkrCaMMRfnnPLz8zcqihHRNYB6wnKTyYR58+ZtbN++fT1R4AWk1ezplJSUCuH2MvBThqZhZVnG3LlzF4aEhBAAZ3O7tu4k4l7cXbt2paKiosymnA8DXg4REuVmsxlvvfXW/42MjCR4srVanKiNiMtkMqn5+flLmnBKDHgziIiLf+UXX3zxs7CwMIInPNvS5LyduAHQww8/XNJEU2LAm2Gz2WQAIKJ2zz///P8LCgryZg2rmQgqAOrfv/+3TTUvBrwQRMS00CwRdcrPz98bGBhI8DIbtjHRFtTo0aNrm2h6DHgb9Lmo69evtw4bNqxSUZRWQVjozIOkpKTP7/vkGPAuaO4s8TVftmzZnL59+2pEcLUSwhIAlyzLNG3atD82wTQZ8BZoCdOSJGH79u0j8vLySrt27UoA3JIktWik615Ec3lFRUXRihUrJjfFXBnwAuhyCExLlixZnpKSUp/m500bLlGhoIpghlsrs9Ffo93vyJEj/0VEHZtqzgy0ELRggfg6Ki8vb4tI3nZBmAOaoIXJKjwCt2SPKYrS4P4YYy5JktQZM2Z8JEkSjNKFBwg2m40zxlTOuXvLli2PP/HEE8s2bNjQ1ul0ujjnsqqqIKKWvk1wzqGqqguA3KVLFwwePLg6JCTkn6qqdrhw4UKXgICAr1euXGlxOp3EOWeqqlJ0dDTLyspavXjx4pa+fQP3A8J21bRrpzlz5ixKTEys38C0tFbVi2aihIaGUlZW1only5c/TEQhiqKAiDgRRWRmZq6XJEnLf3ACIKvV+lcikrQmIQZaKWw2G9ceoqIoWL9+fU5ubu654OBgAqA2V/Hh3YpYPGqnTp3ohRde+MNN9ikjIvnNN998o0OHDsQ5d3HOXQDIYrHUVlZWdtXGfH9n0UCzQGyy6h8eESW8+OKLn0RHR2sE8Trfq+YBiImJofnz5/9Wu3ebzeZDROybb77pn5eXd9bPz4/gSYl0AqARI0ZcLy0tzdCN20Brgj6ixTkHEXV77733Vo8YMeKKeNgq51z1NsICqO+UOH78eCKiKADS1q1bZSJiRMROnjwZOXPmzE/Gjh1L8fHx1Lt3b5o6deqBr7/+Og0wCNsqoX9ohw4dynrllVf+nJqaelGkEhKEK8sbCQvccFulpaUREfUCoE/aYQBgMplARL23b98+bd++fU8SUeDNYzfQSqDLF/D//e9//58DBgwgk8mkJ6vqDW6sO4lG2lGjRqlEFCfGozdxGBoppTFs2FYGrWYLAMrLyx+eOHHi5+3atSOI3q/eago0Jpp58Nhjj92iafUgIm6z2WSjxWcrg952DQgIwMqVK/PT09M1Ter0ZjPgdqKVzKSnp58iohBtnPd98gw0P7RcVwCorq4e8Otf//qvMTExBI+/1eXtZsDthDHmBkBZWVk7/Pz87u+kGWh+2Gw2LjQrAwAiCissLPzdqFGj3CJ90KvyBX6guHx8fGjWrFkriYgZQYJWCCJiN++KiUiaP3/+tIyMjO/btm1L8AQIvCqi9UNE613Qrl0713vvvfckYHgEWhX0CS0AYDabQUQ9iouLf5uVlfWZ6JtFaKW2a2Oi2bMDBgw4R0QBunkw4M3QKl+174kowuFwTHnhhRf+mZKScr1jx471r9H73Q6+pYUx5lQURZ06deoq4TEwtKw3Q2+/iShWh6KiovcnTpx4Tmyw6jXrg0ZW4IZp0K1bN1q7du0ooOFm04CXQf9wiCh6/vz5/5WRkXFBH8VijLlbk7/1XkXrBTZhwoSTRGSGZ7NpmAbeBn1QgIgC3n333XfS09NrAgIC6snKOVcfAI/A3YjT19dXff311/8buHH+mAEvARExTbv6+flh/fr1/5aZmXlUeAIIos/rg6pVbxbNNIiPj6dPP/10MgBs3brVMA28BWKDwQDgypUrGfn5+SW6Uwxdog6qxYnUnKLVe6Wnp18jou6AkUvgNdB1bJGWLFnyHyNHjqzTegrcy5GbD6A4fXx8KC0t7S0Axsk03gB9jsDZs2cH5ubm/lUkYqvwsjKX5hYt6TsyMtJVVFTUBzDs2RaF3nYFgE8++WT6I4884pZlWdOuXlXm0hKi5RqMHTt2PxEp0PmoDTQjGgkQ+BUWFj7fq1cvgke7el2ZSwuKq02bNmS3218CDNOg2aEPvUqSBCKKWLFihXXChAm7RNjVZWjXG6K58vr163eViDrr5tBAU0HULXGHwyFpGoIxBiJKKCwsLMzNzT0r2gtphG1xoniTiNJvNTc3t9TX1xcwTIP7C5vNxoXI8GjTWzQCEZnnzZs3OyMjwyVaYxIewByB+yGabzYqKorWrFkzGTAyun4smM1m47oS7FsI6u/vDyJqc+bMmT4rV658dMGCBa/m5eV9rwsQtKoyl+YWrYVRenr6XxRFaRKPwU/FOGZWq5UXFxe7CwoKCPDYpiaTCVeuXInetGmTfP78+VHnz59/ZO/eveHZ2dmJR44cCb58+TKrrq7GpUuXAE+nQUlVVUlV1ZYdjZdCtDtC9+7d2UsvvVS4adMmJCQkGLbsXYI5HA5JhAzrV3pgYCCIKGbVqlXZ8+fP/6vVat2dlpZWFxsbS506dSJdbkC9VoUu+6q1lro0lzDGXIqi0KxZsz4jIsmIfv0v0DZPjb2OiEhZs2bNnJkzZ+5KSUmpiYqKIhGxupmgLm0TwRgzTIB7ENHv1v3II4+cI6IOQNOFbB8Y80BHMBARKy8vH33w4MGkHTt2JGZkZAz49ttv40+ePKld7hZ/wxhjTHdaITQxcPfgnJPb7VZ79Ogh5+TkTGGMVTocDiknJ8fd0vfmtRDJ1YGVlZUDFy5cuHTMmDEH+/fvTz169CDRLoggDiaWJEn9KSavNLG4wsLCaM6cOW8yxowk7ztBMwVsNttYi8VyOjEx8XqbNm20iawDcB0erVqHG03NtPNe3Tf9zImfeL7AvYqw8d0AaPLkyTuJSII4X/euHuAPRKteEVVVVQwAjh8/biorK2t34sQJKIqC4OBgBAQEKLIsQ1VVp6+vr3L9+nXU1tZClmWEh4e7r169Kp06dYq73W5wziHLMlwuF65fv97Sw2o14JzD7XargwcP5q+88sq/M8bcDodDEgu/ydCqSVtaWuqy2Wz89ddfX/fHP/7x+dOnT6dWV1e7Y2JieERExG4i+rKysrKse/fufa5evdpNluXBFy5cONqxY8dlFRUV6f/4xz8GlZeXU2hoKA8ODibOOV+zZk12WVmZSUTAWnqIXgtB2LrQ0FCfCRMmvB4bG7vVZrPJOTk5rpa+twcWRCQRUSci6ij+jTly5MjT06dP3y88C63m9JfmFhG2rvP396f8/PwyIgoCwJsrv6BVa1o9rFarVFVVxUpLS2GxWDBixAgAQElJCUpLS10AQERhGzduzPjiiy+m5ebmJpnN5giXy4WzZ8/i+PHjuHz5MqqqquB0OgEjXt4otPMSAgIClKysrE/eeeed5xhjl8R5D8ar6cdAH+8movAFCxZMeuaZZ47HxcU15qMliNRCNHLaiiENNKyzTZs2NHPmzK1E5Cfm11jgPxaaU5uI/IqKit7PzMys1jfDgMgfkCSJJEkizjlp3VwM70HjIlp11oWFhdHs2bM/0mriDMLeB2iE3bNnzxM5OTnfhoeH15PViHLdu4jDRpzw9OKiOXPmfCxcW9wI0/5IEBHbunWr1ow3asqUKXXwTLzTyMr6wYR1AyCz2UwjRoyg2bNn24hIhsiWu/enZAAOh0MS0ZcGE3jw4MHMnj17EoA6cR5VixOgFYoKgHr16uV87rnnlpw4cWIUYx7ngFGFcA/QSHpzvZEogQnZu3fvkFWrVi3MyMg4JMuy29vO0WotIloZudLS0so///zzx/RTbRD2DtCytrZu3aqRtIE29ff3R3V19ciPPvrotzNnzvzbmDFjyvr06UNhYWH1k9/cGra1b+Q45yRJkguAMykpiUpKSoYBgNVq9TGqD24DraqgsYQLX19fOJ3OkX/5y1+mz5o1690xY8bs6devnxoZGaknilYR677fBGKMaX1WXRDtjYS4xc9adQ6DsF/rAFDfvn1p+fLleeKZPDC+/PsCrRu2xWK55ZUvNG2vkpKS6a+++uqizMzMzRkZGdS1a1fy9/fXT7hGErfebfVjSSPcYBop6/232iktaPjAyWw2U/v27alt27Yk+h94vWhzJBYk9e3bl7Kyso6vWbPmGcB7m2s0q32inRVlt9t5QUGBdmy6/vcdDh06FL927drhp0+fHldeXt7/+++/x7Fjx1BTUwNxvQoAjDGtxovdLkdA2zgwxrRqWlVcy262zbRrAKiqqmofKAGeE2bCwsLQuXPn88OHDz9w6tQp/4qKikSTyQQAJ+Li4k537tz5qJ+f30EAqKioGPb+++9nnDhxgot8Xa/NYxBuQEycOPGozWZbGhsbu4QxVgvP2H96+bCiE4tWSNhg1YpTpzscOXJk9OLFi381ZcqUovT09JP9+vWj0NDQmzWpU1QU3KJBdZpVO2LThYav69tpUlX7G3F9fa6BoijUtWtXGjBgQM1TTz313aJFi1Zv2rRpEhGFKYqiFT92EuIryw3foLIsw2q1zhURpGvwUrebuD93t27dqKSkJFXcvtcf4nHf7RUiYsXFxXzx4sVMEMij2hiDqqpKTU1NwurVqxO///77jLy8POuuXbv8T5w4gfPnz2sxfxWeAzI455yrqqo1d4P2OR7lRSQ0J4OorBXXSIqiwGw2azVhCA0NRadOneByuco7d+58Ydu2bTGHDh3Sev9DURQpJCQEnTp1QkxMzHcPPfTQ4cTExOLs7OztAMoYY07dELnT6VQZYxX6n8Hju2RBQUHK888/f/2pp546VFtbiy+//NLXZDKhoqICuLHItN61t31L3CsYY+Cck6qqd/2ZRKQC4H369NlrsVi+Xrp0qTJ9+nSXsG+9Fj/aPNBIWlxcjOLiYoLulU9EJgAd/vznP/fct2+f9bvvvhtWVlbW4+jRozhz5kwDkgIA51yCIB8R1b+yGWPkdru1iazvTWA2mxEREQF/f38EBgZeio2NZT4+Pgfatm17pmPHjmfDwsL21dbWlgwYMKC2d+/eDMAps9l8qaCg4NV169a9fPHixauJiYmXk5KS9nTp0uVvycnJn/Ts2fOILMvOG/+dp6XPjBkzyGq1atqyPvJmt9s17V8/H8IUCaqsrOy0bdu2mdeuXTu5efPmX5SWlnYqKyvTT59bjLtBhtS9EFmbH9VTIiwBcIs1Id3pc8Q9urp27SrPnz8/Pzs7e6HNZpMLCgq8PrXwh5CW2Ww2BuAWu9THxwfXr19vt23btr4bNmzoefXq1d/s27evY3l5uamiogK1tbWAR/OqACBJEte0jZ6kALSHQBAk9fX1RWhoKCIjIxEWFnY6KSnpktls/pu/v/+nFoulKikp6SAAHhAQcLa2tvZOD54TEa5cudKrpqbmSrt27c5JknTxprJwLUSp3kzKHwoiCly7du30HTt2/J+ysjKf6urqkOPHjwccO3ZMu9f6RSnMIO110qjmFCVGqtCWcnR0NBITE107duyQq6qq6q+5Xbm7ZuMnJiby5cuXDx40aND21lLXdVfmgc1m44mJiSwnJwcAtN4BqiCpadeuXb02btyYcOnSpWfGjBnz0MmTJ0NOnTqFf/3rX9pHaBqFSZLEiKhes+i0hP4BSZxzSSNp9+7dq/39/T8cOnTooeHDh++IjY09BODSbcjEAHCr1arV3KsAYLfbAc/rWRUL4xvd30jiehIkVcWCREFBwd3Ppg5ExOx2Oztw4ABLSEhgjLHLABYQ0TsA/AGEFRUVDf/73/+eef78+RF79uwJVRQFiqJg7969DJ4FyyA0J2NM0ha2qqpuVVUZAB4dHc0HDhx4auzYsf8xZcqUL99+++38kydP9vn0009TvvnmG1Wbj9vcpnrmzBm+c+fOEQC279+/v/UGDvSuqJt/FxQUBCLquXHjxtfmzp27MTs7+0Tfvn0pPDxcv0lyQzQUlmVZlSTJLezb26b+BQQEUHh4OA0cOJDS0tKqpk+f/rfCwsJflZWVjSSisMbu02KxyDabTXY4HJIg/F1POnkODm62xGVtU3rzz7WGdkVFRU99/PHH2fv37x/92GOPuYcPH05paWmXOnfurM2RlrhCJpOJBg4cSL/85S//6XA48omovf4z/f39sXz58tmpqan1vRxuswl0BgYG0pw5c+YBra+zYX2yCW7a5YudcvePP/54/IIFC9Y+8cQTu/v373+9S5cuep+lCk+6n0uWZTfnXCOotpMnABQREUGpqamUlZVFY8eOpUmTJtGMGTNcmZmZH/3mN795+w9/+MO/7d+/fzQRdRCNy/SQ9ARFKz0hRVtct/OqAEBVVVW/ixcvphJR52XLlj07bdq00vHjx1NkZCQNGzaMZsyYseTw4cMjydP3FYAnCEBE2nGlnIjknTt3jnr88ce/EOZGY5UYTh8fH5o0adIbwL2RVvccWgQNVr9Y+f67d+/++dKlS9+dNm3aP1NTUy/HxMToy7EJQB1j7Do8Fa910JETAPn7+1O7du0oNTWVBg0adHjGjBmfL1y48KVz586lElGiTnr4+Pg0el8Wi0Vu6clpDggSyyIa2Ohx8kTUf9myZb8+efJkX85vXHKHI+ZlAPjggw8e79Kly+06kzsVRaFHH330dwCkqVOnmoTy0rwxTK8gqJFmKC3iHhMGvVRWVjZp6dKlrz377LMfDR06tCIuLo505dgEDzGv4UZZNgEgPz8/6ty5MyUkJNCQIUMoNzf38sSJEzfNnTt3xdKlS589evTo40Tk97+cPM1vftU39bi9GSTajGpkbuQSqbF5EiZPg+6PRORrsVguADeO+9SJU5Zlmjp16ttaIOYOqL8P8fa1EFFH7Wfas/sBw71nsHnz5u1xOByyoiiJhw8fxoULF+ByuQAPSVUAvhAT4O/vj/DwcERGRkKSpLL4+PizPj4+fx8yZMjluLi4I3369PkGwDk/P78T165du+X/slgsknAdNdhAiWwsA7eBPpJot9vVxuZLuNo8u1hJgsvlkq5cuRIXEBDgb7VaF6xZs2YYY0zVVxoIDwINHjy4ZsCAAX/q0qVL+ZAhQyg+Pn5dYGDgQQAmeMhawxhzE1HykiVLfr5+/foUVVWTJUmqHjp06KKXX375dzrfrraJbDKwl19+uWjdunWTDxw40OAXgYGBCA8PhyRJ7ujo6AuhoaH7+/TpU9WrV6+S1NTUg+Hh4dv8/PyuNkJOwKM5+YgRI2C32wmeYIF3xjEfAGiEJaKeRUVFuZ999lns6dOnk6uqqroCkKqqqmrKy8vN4tr6v9Plx0JRFISEhKBt27ZwuVx1sixXREREKIGBgXJgYGAN5/yzqqqq8bt27WpTXV0NCO9G+/btMXr06F0PP/zw2kGDBu1NSEjYIJRek4FxznHgwIEhH3744dRTp04NdrlcUlBQUI2iKNtGjRp1LTw8fFVycvJxs9l8SfhZG/w9PBskAIDdblftdjs0d5GBpofORAiaOnXqrk2bNsVUVlbechlu+IGZJEnc7XZrQRAtkqb3z95ikvj4+KCurg4AnJIkcc65RESqy+VyA1CCg4MRHx+PjIyM6a+99tqy7Oxsqbi4uMl8vvWvi4CAAAQGBsJsNjd2HbNarTfv4A20MLSN0OrVq9MiIiIIAMXHx1NOTs6VcePG1Xbv3t0dExNDHTt2pPDw8Jt7m6n6fA59HofImtM8QVqLKb09XL+vMZvN1KFDBwoODqbZs2d/QbozKpoCMgDVZrPxkpISrvUHgLA/Re+A+qhQU64cAz8MWmuodevW9fbx8cEvfvGLA3l5ebOSk5P3AsCWLVtCiGic2+3uXV1dTRUVFYEbN24c9/XXX8sicw7wBDAYY4yLAAYDwES2Gw8LC5OioqLg4+NTV1NTczYoKKijr68vv3jxojs6Orpy2LBhO+Li4o5duXKlXWBg4IeMMXI4HBDBKAMGGsJqtUqMMRQUFHz06quvvk9EgXe6nnOOa9euxdrt9sLx48eXx8TEkO5U9AYSGRlJzzzzzMFly5a9smfPnqFE1J2IfInoISIaQkQ9iahRf2VTwnjFPyC4evVqTHBw8NG6ujo4HA7JarWqdrtde74cqO+2QxChYVVVQ0pLS1O++uqrjGPHjo28ePFin2+//ZYURaG0tLSagQMHvpmZmblA+OPvBEnkoyAxMZGaOn/hfwA/Oe6UiLaGwQAAAABJRU5ErkJggg==" width="58" height="30" alt="Polly" style="display:block;"></td>')
    parts.append('<td style="vertical-align:middle;"><div style="font-size:20px; font-weight:700; color:' + INK + '; letter-spacing:-0.3px;">The Polly Brief</div></td>')
    parts.append('</tr></table>')
    parts.append('<div style="font-size:13px; color:' + MUTED + '; margin-top:6px;">' + _esc(date_label) + '</div>')
    parts.append('</td></tr>')
    parts.append(_divider())
    parts.append('<tr><td style="padding:0 40px;">')
    parts.append(_section_heading('\U0001F4CA', 'Polly Hiring Pulse'))
    parts.append('<table role="presentation" cellpadding="0" cellspacing="0" style="margin-bottom:20px;"><tr>')
    parts.append(_stat_block(f'{pulse.total_active:,}', 'Active Jobs', url='https://jobs.thepolly.co/jobs'))
    parts.append(_stat_block(str(pulse.new_today), 'New Today'))
    parts.append('</tr></table>')
    parts.append('<table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>')
    parts.append('<td width="50%" valign="top" style="padding-right:16px;">')
    parts.append('<div style="font-size:11px; font-weight:700; color:' + MUTED + '; text-transform:uppercase;">Top Hiring Categories</div>')
    parts.append('<table role="presentation" cellpadding="0" cellspacing="0">' + category_rows + '</table></td>')
    parts.append('<td width="50%" valign="top">')
    parts.append('<div style="font-size:11px; font-weight:700; color:' + MUTED + '; text-transform:uppercase;">Top Hiring Organizations</div>')
    parts.append('<table role="presentation" cellpadding="0" cellspacing="0">' + employer_rows + '</table></td>')
    parts.append('</tr></table></td></tr>')
    parts.append(_divider())
    parts.append('<tr><td style="padding:0 40px;">')
    parts.append('<div style="font-size:15px; font-weight:700; color:' + INK + '; margin-bottom:20px;">\U0001F4F0 Top Stories</div>')
    parts.append('<table role="presentation" width="100%" cellpadding="0" cellspacing="0">' + story_rows + '</table>')
    parts.append('</td></tr>')
    parts.append(_divider())
    parts.append('<tr><td style="padding:0 40px;">')
    parts.append(_section_heading('\U0001F525', 'Jobs Worth Looking At'))
    parts.append('<table role="presentation" width="100%" cellpadding="0" cellspacing="0">' + job_rows + '</table>')
    parts.append('</td></tr>')
    parts.append(_divider())
    parts.append('<tr><td style="padding:0 40px;">')
    parts.append('<div style="background-color:' + INK + '; border-radius:10px; padding:24px; text-align:center;">')
    parts.append(_section_heading('\U0001F4C5', 'Election Countdown').replace(INK, '#FFFFFF').replace(MUTED, '#CCCCCC'))
    parts.append('<div style="font-size:32px; font-weight:800; color:#FFFFFF;">' + str(days_left) + '</div>')
    parts.append('<div style="font-size:12px; color:#CCCCCC; text-transform:uppercase; letter-spacing:0.6px;">Days Until Election Day</div>')
    parts.append('</div></td></tr>')
    parts.append(quote_section)
    parts.append('<tr><td style="padding:36px 40px 40px 40px;">')
    parts.append('<div style="border-top:1px solid ' + HAIRLINE + '; padding-top:20px; text-align:center;">')
    parts.append('<div style="font-size:13px; font-weight:600; color:' + INK + ';">Powered by Pollyai</div>')
    parts.append('<div style="font-size:12px; color:' + MUTED + '; margin-top:2px;">The Talent Marketplace for Politics &amp; Public Affairs</div>')
    parts.append('</div></td></tr>')
    parts.append('</table></td></tr></table></body></html>')
    return ''.join(parts)
