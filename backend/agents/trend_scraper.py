import time

STATE_TO_GEO = {
    'California': 'US-CA', 'Texas': 'US-TX', 'New York': 'US-NY',
    'Florida': 'US-FL', 'Illinois': 'US-IL', 'Pennsylvania': 'US-PA',
    'Ohio': 'US-OH', 'Georgia': 'US-GA', 'North Carolina': 'US-NC',
    'Michigan': 'US-MI', 'New Jersey': 'US-NJ', 'Virginia': 'US-VA',
    'Washington': 'US-WA', 'Arizona': 'US-AZ', 'Massachusetts': 'US-MA',
    'Tennessee': 'US-TN', 'Indiana': 'US-IN', 'Missouri': 'US-MO',
    'Maryland': 'US-MD', 'Wisconsin': 'US-WI', 'Colorado': 'US-CO',
    'Minnesota': 'US-MN', 'South Carolina': 'US-SC', 'Alabama': 'US-AL',
    'Louisiana': 'US-LA', 'Kentucky': 'US-KY', 'Oregon': 'US-OR',
    'Oklahoma': 'US-OK', 'Connecticut': 'US-CT', 'Utah': 'US-UT',
    'Iowa': 'US-IA', 'Nevada': 'US-NV', 'Arkansas': 'US-AR',
    'Mississippi': 'US-MS', 'Kansas': 'US-KS', 'New Mexico': 'US-NM',
    'Nebraska': 'US-NE', 'West Virginia': 'US-WV', 'Idaho': 'US-ID',
    'Hawaii': 'US-HI', 'New Hampshire': 'US-NH', 'Maine': 'US-ME',
    'Montana': 'US-MT', 'Rhode Island': 'US-RI', 'Delaware': 'US-DE',
    'South Dakota': 'US-SD', 'North Dakota': 'US-ND', 'Alaska': 'US-AK',
    'Vermont': 'US-VT', 'Wyoming': 'US-WY',
}


def _safe_int(val, default=0):
    try:
        return int(val)
    except (TypeError, ValueError):
        return default


def fetch_google_trends(keywords, timeframe='today 7-d', geo='US', us_state='all'):
    final_geo = geo
    if us_state and us_state != 'all':
        final_geo = STATE_TO_GEO.get(us_state, 'US')

    result = {
        'keywords': list(keywords),
        'timeframe': timeframe,
        'geo': final_geo,
        'us_state': us_state,
        'interest_over_time': [],
        'related_queries': {},
        'interest_by_region': [],
    }

    try:
        from pytrends.request import TrendReq
        pytrends = TrendReq(hl='en-US', tz=360)
        pytrends.build_payload(list(keywords), cat=0, timeframe=timeframe, geo=final_geo, gprop='')
    except Exception:
        return result

    # Section A: Interest over time
    try:
        iot_df = pytrends.interest_over_time()
        if iot_df is not None and not iot_df.empty:
            points = []
            for idx, row in iot_df.iterrows():
                try:
                    date_str = idx.strftime('%Y-%m-%d')
                except Exception:
                    date_str = str(idx)
                entry = {'date': date_str}
                for kw in keywords:
                    if kw in iot_df.columns:
                        entry[kw] = _safe_int(row[kw])
                    else:
                        entry[kw] = 0
                points.append(entry)
            result['interest_over_time'] = points
    except Exception:
        pass

    time.sleep(1)

    # Section B: Related queries
    try:
        related = pytrends.related_queries() or {}
        rq = {}
        for kw in keywords:
            kw_data = related.get(kw) or {}
            rising_df = kw_data.get('rising')
            top_df = kw_data.get('top')
            rising_list = []
            top_list = []
            if rising_df is not None and not rising_df.empty:
                for _, r in rising_df.head(5).iterrows():
                    rising_list.append({
                        'query': str(r.get('query', '')),
                        'value': _safe_int(r.get('value')),
                    })
            if top_df is not None and not top_df.empty:
                for _, r in top_df.head(5).iterrows():
                    top_list.append({
                        'query': str(r.get('query', '')),
                        'value': _safe_int(r.get('value')),
                    })
            rq[kw] = {'rising': rising_list, 'top': top_list}
        result['related_queries'] = rq
    except Exception:
        pass

    time.sleep(1)

    # Section C: Interest by region (US states)
    try:
        ibr_df = pytrends.interest_by_region(resolution='REGION', inc_low_vol=True)
        if ibr_df is not None and not ibr_df.empty:
            regions = []
            for region, row in ibr_df.iterrows():
                values = {}
                for kw in keywords:
                    if kw in ibr_df.columns:
                        values[kw] = _safe_int(row[kw])
                    else:
                        values[kw] = 0
                regions.append({'region': str(region), 'values': values})
            result['interest_by_region'] = regions
    except Exception:
        pass

    return result
