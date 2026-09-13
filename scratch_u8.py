import pandas as pd

events = pd.read_csv('dataset/financial_events.csv')
u8 = events[events['user_id'] == 'user_08'].copy()
# Let's see all recurring debits for user_08
print("User 08 events in Jan-Feb 2025:")
print(u8[(u8['settlement_date'] >= '2025-01-01') & (u8['settlement_date'] <= '2025-02-15')][['event_id', 'description', 'category', 'direction', 'amount', 'settlement_date', 'status']])
