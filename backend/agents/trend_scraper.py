import time
import json
import traceback


def fetch_google_trends(keywords, timeframe='today 7-d', geo='US', us_state='all'):
    print(f"[trends] Starting fetch for keywords={keywords}, timeframe={timeframe}, geo={geo}, us_state={us_state}")

    result = {
        "keywords": keywords,
        "timeframe": timeframe,
        "geo": geo,
        "us_state": us_state,
        "interest_over_time": [],
        "related_queries": {},
        "interest_by_region": []
    }

    STATE_MAP = {
        'Alabama': 'US-AL', 'Alaska': 'US-AK', 'Arizona': 'US-AZ',
        'Arkansas': 'US-AR', 'California': 'US-CA', 'Colorado': 'US-CO',
        'Connecticut': 'US-CT', 'Delaware': 'US-DE', 'Florida': 'US-FL',
        'Georgia': 'US-GA', 'Hawaii': 'US-HI', 'Idaho': 'US-ID',
        'Illinois': 'US-IL', 'Indiana': 'US-IN', 'Iowa': 'US-IA',
        'Kansas': 'US-KS', 'Kentucky': 'US-KY', 'Louisiana': 'US-LA',
        'Maine': 'US-ME', 'Maryland': 'US-MD', 'Massachusetts': 'US-MA',
        'Michigan': 'US-MI', 'Minnesota': 'US-MN', 'Mississippi': 'US-MS',
        'Missouri': 'US-MO', 'Montana': 'US-MT', 'Nebraska': 'US-NE',
        'Nevada': 'US-NV', 'New Hampshire': 'US-NH', 'New Jersey': 'US-NJ',
        'New Mexico': 'US-NM', 'New York': 'US-NY', 'North Carolina': 'US-NC',
        'North Dakota': 'US-ND', 'Ohio': 'US-OH', 'Oklahoma': 'US-OK',
        'Oregon': 'US-OR', 'Pennsylvania': 'US-PA', 'Rhode Island': 'US-RI',
        'South Carolina': 'US-SC', 'South Dakota': 'US-SD', 'Tennessee': 'US-TN',
        'Texas': 'US-TX', 'Utah': 'US-UT', 'Vermont': 'US-VT',
        'Virginia': 'US-VA', 'Washington': 'US-WA', 'West Virginia': 'US-WV',
        'Wisconsin': 'US-WI', 'Wyoming': 'US-WY'
    }

    final_geo = STATE_MAP.get(us_state, 'US') if us_state != 'all' else 'US'
    print(f"[trends] Using geo={final_geo}")

    try:
        from pytrends.request import TrendReq
        pytrends = TrendReq(
            hl='en-US',
            tz=360,
            timeout=(10, 25),
            retries=2,
            backoff_factor=0.5
        )

        # Cap at 5 keywords (pytrends hard limit)
        kw_list = keywords[:5]
        print(f"[trends] Building payload for kw_list={kw_list}")

        pytrends.build_payload(
            kw_list,
            cat=0,
            timeframe=timeframe,
            geo=final_geo,
            gprop=''
        )
        print("[trends] Payload built successfully")
        time.sleep(1)

        # INTEREST OVER TIME
        try:
            print("[trends] Fetching interest_over_time...")
            iot_df = pytrends.interest_over_time()
            print(f"[trends] interest_over_time shape: {iot_df.shape}")
            print(f"[trends] interest_over_time columns: {list(iot_df.columns)}")

            if iot_df is not None and not iot_df.empty:
                iot_df = iot_df.drop(columns=['isPartial'], errors='ignore')
                iot_df.index = iot_df.index.astype(str)
                records = []
                for date, row in iot_df.iterrows():
                    point = {"date": str(date)[:10]}
                    for kw in kw_list:
                        if kw in row:
                            point[kw] = int(row[kw])
                        else:
                            point[kw] = 0
                    records.append(point)
                result["interest_over_time"] = records
                print(f"[trends] Converted {len(records)} data points")
            else:
                print("[trends] interest_over_time returned empty dataframe")
        except Exception as e:
            print(f"[trends] interest_over_time failed: {e}")
            traceback.print_exc()

        time.sleep(1)

        # RELATED QUERIES
        try:
            print("[trends] Fetching related_queries...")
            rq = pytrends.related_queries()
            print(f"[trends] related_queries keys: {list(rq.keys()) if rq else 'None'}")

            related = {}
            if rq:
                for kw in kw_list:
                    if kw in rq and rq[kw]:
                        rising_df = rq[kw].get('rising')
                        top_df = rq[kw].get('top')
                        related[kw] = {
                            "rising": rising_df.head(5).to_dict('records') if rising_df is not None and not rising_df.empty else [],
                            "top": top_df.head(5).to_dict('records') if top_df is not None and not top_df.empty else []
                        }
                    else:
                        related[kw] = {"rising": [], "top": []}
            result["related_queries"] = related
            print(f"[trends] related_queries processed for {len(related)} keywords")
        except Exception as e:
            print(f"[trends] related_queries failed: {e}")
            traceback.print_exc()

        time.sleep(1)

        # INTEREST BY REGION
        try:
            print("[trends] Fetching interest_by_region...")
            ibr_df = pytrends.interest_by_region(
                resolution='REGION',
                inc_low_vol=True,
                inc_geo_code=False
            )
            print(f"[trends] interest_by_region shape: {ibr_df.shape if ibr_df is not None else 'None'}")

            if ibr_df is not None and not ibr_df.empty:
                ibr_df = ibr_df.sort_values(
                    by=kw_list[0] if kw_list[0] in ibr_df.columns else ibr_df.columns[0],
                    ascending=False
                ).head(10)
                region_records = []
                for region, row in ibr_df.iterrows():
                    values = {}
                    for kw in kw_list:
                        if kw in row:
                            values[kw] = int(row[kw])
                    region_records.append({"region": str(region), "values": values})
                result["interest_by_region"] = region_records
                print(f"[trends] Converted {len(region_records)} region records")
            else:
                print("[trends] interest_by_region returned empty dataframe")
        except Exception as e:
            print(f"[trends] interest_by_region failed: {e}")
            traceback.print_exc()

    except Exception as e:
        print(f"[trends] Fatal error in fetch_google_trends: {e}")
        traceback.print_exc()
        result["error"] = str(e)

    print(f"[trends] Returning result with {len(result['interest_over_time'])} time points")
    return result
