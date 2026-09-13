import pandas as pd

events = pd.read_csv('dataset/financial_events.csv')
u15 = events[events['user_id'] == 'user_15'].copy()
print("User 15 events in Dec 2025 - Jan 2026:")
u15['s_dt'] = pd.to_datetime(u15['settlement_date']).dt.date
print(u15[(u15['s_dt'] >= pd.to_datetime('2025-12-01').date()) & (u15['s_dt'] <= pd.to_datetime('2026-01-15').date())][['event_id', 'description', 'category', 'amount', 'settlement_date']])
