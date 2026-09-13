import pandas as pd
from datetime import datetime, timedelta

events = pd.read_csv('dataset/financial_events.csv')
profiles = pd.read_csv('dataset/financial_profiles.csv')
samples = pd.read_csv('dataset/sample_requests.csv')

# Look at user_01
req = samples.iloc[0]
user_id = 'user_01'
req_date = datetime.strptime('2024-03-03', '%Y-%m-%d').date()
init_balance = 58481.1
min_balance = 18000.0

# What recurring monthly expenses exist for user_01?
# In Feb 2024 (the month before March 2024):
# rent: on the 2nd: 5148
# utilities: on the 6th: 1541.75
# education: on the 8th: 1821.6
# debt_repayment: on the 11th: 3487
# music_subscription: on the 11th: 235.4
# delivery_membership: on the 13th: 306.9
# salary: on the 15th: 23320.0
# transport: weekly ~430
# groceries: weekly ~770
# dining: biweekly ~1100

print("Initial balance:", init_balance)
print("Requested amount:", req['requested_amount'])
print("Amount safe to pay (ground truth):", req['amount_safe_to_pay'])
print("Earliest full date (ground truth):", req['earliest_date_for_full_payment'])

# Let's see the balance trajectory if user pays 25256 on 2024-03-03
