import pandas as pd

events = pd.read_csv('dataset/financial_events.csv')
u6 = events[events['user_id'] == 'user_06']
# Request date is 2026-01-03
# Let's see all recurring debits for user_06
debits = u6[(u6['direction'] == 'debit') & (u6['status'] == 'settled')].copy()
# Group by category and description
summary = debits.groupby(['category', 'description', 'flexibility']).agg(
    count=('amount', 'count'),
    mean_amt=('amount', 'mean'),
    min_amt=('amount', 'min'),
    max_amt=('amount', 'max')
).reset_index()
print(summary)
