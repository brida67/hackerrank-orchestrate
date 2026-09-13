import pandas as pd

events = pd.read_csv('dataset/financial_events.csv')
u7 = events[events['user_id'] == 'user_07'].copy()
print("User 07 debits around Sept 2024:")
u7['s_dt'] = pd.to_datetime(u7['settlement_date']).dt.date
print(u7[(u7['s_dt'] >= pd.to_datetime('2024-08-01').date()) & (u7['s_dt'] <= pd.to_datetime('2024-09-23').date())][['event_id', 'description', 'category', 'amount', 'settlement_date']])
