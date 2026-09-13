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
options = pd.read_csv('dataset/request_payment_options.csv')
messages = pd.read_csv('dataset/messages.csv')
rates = pd.read_csv('dataset/exchange_rates.csv')

for eid, amt in IMAGE_AMOUNTS.items():
    mask = events['event_id'] == eid
    events.loc[mask, 'amount'] = amt

def get_user_recurring_forecast(user_id, req_date_str, days=90):
    req_date = datetime.strptime(req_date_str, '%Y-%m-%d').date()
    end_date = req_date + timedelta(days=days)
    
    u_events = events[events['user_id'] == user_id].copy()
    u_events['settlement_date_dt'] = pd.to_datetime(u_events['settlement_date']).dt.date
    u_events['event_date_dt'] = pd.to_datetime(u_events['event_date']).dt.date
    
    # 1. Past settled debits
    past_settled = u_events[(u_events['settlement_date_dt'] <= req_date) & (u_events['status'] == 'settled') & (u_events['direction'] == 'debit')].copy()
    
    # Future events already in CSV: pending debits, scheduled salary
    future_csv = u_events[(u_events['settlement_date_dt'] > req_date) & (u_events['settlement_date_dt'] <= end_date)].copy()
    
    # Daily cash flow map: date -> net flow (+ for credit, - for debit)
    daily_flows = {req_date + timedelta(days=i): 0.0 for i in range(days + 1)}
    
    # Apply future pending debits
    for _, r in future_csv.iterrows():
        d = r['settlement_date_dt']
        if r['direction'] == 'debit' and r['status'] in ['pending', 'scheduled']:
            daily_flows[d] -= float(r['amount'])
        elif r['direction'] == 'credit' and r['status'] == 'scheduled' and r['category'] == 'salary':
            daily_flows[d] += float(r['amount'])
            
    return daily_flows

print("Test forecast structure built.")
