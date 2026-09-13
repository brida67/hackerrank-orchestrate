import pandas as pd

events = pd.read_csv('dataset/financial_events.csv')
u6_ev = events[events['user_id'] == 'user_06'].copy()
print(f"User 06 total events: {len(u6_ev)}")
print(u6_ev[['event_id', 'description', 'category', 'direction', 'amount', 'event_date', 'settlement_date', 'status', 'flexibility']].to_string())
