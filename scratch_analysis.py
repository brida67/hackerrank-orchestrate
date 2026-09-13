import pandas as pd
import datetime

samples = pd.read_csv('dataset/sample_requests.csv')
profiles = pd.read_csv('dataset/financial_profiles.csv')
events = pd.read_csv('dataset/financial_events.csv')
options = pd.read_csv('dataset/request_payment_options.csv')
rates = pd.read_csv('dataset/exchange_rates.csv')
messages = pd.read_csv('dataset/messages.csv')

print(f"Loaded {len(samples)} sample requests.")

# Let's inspect request_01 in detail
r1 = samples.iloc[0]
u1 = profiles[profiles['user_id'] == r1['user_id']].iloc[0]
print("--- Request 01 ---")
print(r1)
print("\n--- User 01 Profile ---")
print(u1)

# Check user 01 events around request_date (2024-03-03)
u1_events = events[events['user_id'] == r1['user_id']].copy()
print(f"\nUser 01 total events: {len(u1_events)}")
print(f"User 01 event date range: {u1_events['event_date'].min()} to {u1_events['event_date'].max()}")
print(f"Settlement date range: {u1_events['settlement_date'].min()} to {u1_events['settlement_date'].max()}")

# Future events on or after request_date
future_events = u1_events[u1_events['settlement_date'] >= r1['request_date']]
print(f"\nFuture events (>= 2024-03-03):\n{future_events[['event_id', 'event_type', 'category', 'direction', 'amount', 'currency', 'settlement_date', 'status']]}")

# Messages for user 01
u1_msgs = messages[messages['user_id'] == r1['user_id']]
print(f"\nUser 01 messages:\n{u1_msgs[['message_id', 'sent_at', 'message_text']]}")
