import os
import re
import math
import pandas as pd
from datetime import datetime, timedelta

IMAGE_AMOUNTS = {
    'event_253': 4365000.0,    # image_01 (IDR)
    'event_1442': 100000.0,    # image_02 (INR)
    'event_1545': 41272.0,     # image_03 (INR)
    'event_1700': 2854.0,      # image_04 (INR)
    'event_1786': 704.05,      # image_05 (INR)
    'event_3051': 1995.0,      # image_06 (INR)
    'event_3231': 8528.0,      # image_07 (INR)
    'event_4535': 15339.0,     # image_08 (INR)
    'event_5170': 723.0,       # image_09 (INR)
    'event_6033': 79679.26,    # image_10 (INR)
    'event_6859': 3650.0,      # image_11 (INR)
    'event_7307': 33.5,        # image_12 (USD)
    'event_7941': 2298.0,      # image_13 (INR)
    'event_9421': 4543.0,      # image_14 (INR)
    'event_9806': 9968.0,      # image_15 (INR)
    'event_10521': 393.22,     # image_16 (INR)
}

samples = pd.read_csv('dataset/sample_requests.csv')
profiles = pd.read_csv('dataset/financial_profiles.csv')
events = pd.read_csv('dataset/financial_events.csv')
messages = pd.read_csv('dataset/messages.csv')

for eid, amt in IMAGE_AMOUNTS.items():
    mask = events['event_id'] == eid
    events.loc[mask, 'amount'] = amt

# Let's inspect the exact dates and intervals between events for each category across users
# E.g. for user_01, user_03, user_06, user_08
for uid in ['user_01', 'user_03', 'user_06', 'user_08']:
    u_events = events[events['user_id'] == uid].copy()
    u_events = u_events[u_events['status'] == 'settled']
    u_events['s_dt'] = pd.to_datetime(u_events['settlement_date'])
    print(f"\n--- User {uid} categories and frequency ---")
    for cat, grp in u_events.groupby('category'):
        grp = grp.sort_values('s_dt')
        diffs = grp['s_dt'].diff().dt.days.dropna().tolist()
        mean_diff = sum(diffs)/len(diffs) if diffs else 0
        print(f"  {cat:20s}: count={len(grp):2d}, mean_interval={mean_diff:5.1f}d, intervals={diffs[:5]}, last_date={grp['s_dt'].iloc[-1].strftime('%Y-%m-%d')}, last_amt={grp['amount'].iloc[-1]}")
