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
        if i > 0:
            job_rows += _divider()
        job_rows += _job_block(j)
    if not job_rows:
        job_rows = '<tr><td style="font-size:13px; color:' + MUTED + ';">No featured jobs today.</td></tr>'

    days_left = _days_until_election(today)

    quote_section = ''
    if quote_text:
        attribution = ''
        if quote_source:
            attribution = '<div style="font-size:13px; color:' + MUTED + '; margin-top:8px;">&mdash; ' + _esc(quote_source) + '</div>'
        quote_section = _divider() + '<tr><td style="padding:0 40px;">' + _section_heading('\U0001F4AC', 'Quote of the Day') + '<div style="font-size:16px; color:' + INK + '; font-style:italic; line-height:1.5;">&ldquo;' + _esc(quote_text) + '&rdquo;</div>' + attribution + '</td></tr>'

    html_out = '<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>The Polly Brief</title></head>'
    html_out += '<body style="margin:0; padding:0; background-color:' + BG + '; font-family:-apple-system,BlinkMacSystemFont,\'Segoe UI\',Helvetica,Arial,sans-serif;">'
    html_out += '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:' + BG + '; padding:32px 0;"><tr><td align="center">'
    html_out += '<table role="presentation" width="600" cellpadding="0" cellspacing="0" style="background-color:' + CARD + '; border-radius:12px;">'
    html_out += '<tr><td style="padding:40px 40px 24px 40px;"><div style="font-size:20px; font-weight:700; color:' + INK + '; letter-spacing:-0.3px;">The Polly Brief</div><div style="font-size:13px; color:' + MUTED + '; margin-top:4px;">' + _esc(date_label) + '</div></td></tr>'
    html_out += _divider()
    html_out += '<tr><td style="padding:0 40px;">' + _section_heading('\U0001F4CA', 'Polly Hiring Pulse')
    html_out += '<table role="presentation" cellpadding="0" cellspacing="0" style="margin-bottom:20px;"><tr>' + _stat_block(f'{pulse.total_active:,}', 'Active Jobs') + _stat_block(str(pulse.new_today), 'New Today') + '</tr></table>'
    html_out += '<table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>'
    html_out += '<td width="50%" valign="top" style="padding-right:16px;"><div style="font-size:11px; font-weight:700; color:' + MUTED + '; text-transform:uppercase; letter-spacing:0.6px; margin-bottom:8px;">Top Hiring Categories</div><table role="presentation" cellpadding="0" cellspacing="0">' + category_rows + '</table></td>'
    html_out += '<td width="50%" valign="top"><div style="font-size:11px; font-weight:700; color:' + MUTED + '; text-transform:uppercase; letter-spacing:0.6px; margin-bottom:8px;">Top Hiring Organizations</div><table role="presentation" cellpadding="0" cellspacing="0">' + employer_rows + '</table></td>'
    html_out += '</tr></table></td></tr>'
    html_out += _divider()
    html_out += '<tr><td style="padding:0 40px;"><div style="font-size:15px; font-weight:700; color:' + INK + '; margin-bottom:20px;">\U0001F4F0 Top Stories</div><table role="presentation" width="100%" cellpadding="0" cellspacing="0">' + story_rows + '</table></td></tr>'
    html_out += _divider()
    html_out += '<tr><td style="padding:0 40px;">' + _section_heading('\U0001F525', 'Jobs Worth Looking At') + '<table role="presentation" width="100%" cellpadding="0" cellspacing="0">' + job_rows + '</table></td></tr>'
    html_out += _divider()
    html_out += '<tr><td style="padding:0 40px;">' + _section_heading('\U0001F4C5', 'Election Countdown') + '<div style="font-size:15px; color:' + INK + ';">' + str(days_left) + ' Days Until Election Day</div></td></tr>'
    html_out += quote_section
    html_out += '<tr><td style="padding:36px 40px 40px 40px;"><div style="border-top:1px solid ' + HAIRLINE + '; padding-top:20px; text-align:center;"><div style="font-size:13px; font-weight:600; color:' + INK + ';">Powered by &ldquo;Pollyai&rdquo;</div><div style="font-size:12px; color:' + MUTED + '; margin-top:2px;">The Talent Marketplace for Politics &amp; Public Affairs</div></div></td></tr>'
    html_out += '</table></td></tr></table></body></html>'
    return html_out
