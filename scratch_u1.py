import pandas as pd

events = pd.read_csv('dataset/financial_events.csv')
u1_events = events[events['user_id'] == 'user_01'].copy()
print(u1_events[['event_id', 'event_type', 'description', 'category', 'direction', 'amount', 'settlement_date', 'status', 'flexibility']].to_string())
