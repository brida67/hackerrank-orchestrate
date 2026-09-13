import pandas as pd
import datetime

events = pd.read_csv('dataset/financial_events.csv')
samples = pd.read_csv('dataset/sample_requests.csv')
profiles = pd.read_csv('dataset/financial_profiles.csv')

# Let's see what events exist between request_date and request_date + 90 days for user_01, user_02, user_03, user_06, user_19
for r_id in ['request_01', 'request_02', 'request_03', 'request_06', 'request_11', 'request_19', 'request_21']:
    req = samples[samples['request_id'] == r_id].iloc[0]
    u_id = req['user_id']
    prof = profiles[profiles['user_id'] == u_id].iloc[0]
    r_date = req['request_date']
    end_date = str((pd.to_datetime(r_date) + pd.Timedelta(days=90)).date())
    
    u_ev = events[events['user_id'] == u_id].copy()
    in_range = u_ev[(u_ev['settlement_date'] >= r_date) & (u_ev['settlement_date'] <= end_date)]
    
    print(f"\n==================== {r_id} ({u_id}) ====================")
    print(f"Req Date: {r_date}, 90d End: {end_date}, Current Bal: {prof['current_available_balance']}, Min Bal: {prof['minimum_balance_to_keep']}")
    print(f"Safe to Pay: {req['amount_safe_to_pay']}, Earliest Full: {req['earliest_date_for_full_payment']}")
    print(f"Events in 90-day window ({len(in_range)} events):")
    for _, ev in in_range.iterrows():
        print(f"  {ev['event_id']} | {ev['settlement_date']} | {ev['event_type']} | {ev['category']} | {ev['direction']} | {ev['amount']} | {ev['status']} | {ev['flexibility']} | {ev['description']}")
