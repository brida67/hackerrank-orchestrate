import pandas as pd

events = pd.read_csv('dataset/financial_events.csv')
print("Unique categories:", events['category'].unique())
print("Unique event_types:", events['event_type'].unique())
print("Unique directions:", events['direction'].unique())
print("Unique statuses:", events['status'].unique())
print("Unique flexibilities:", events['flexibility'].unique())

# Let's inspect user_01 again, grouped by category and description
u1 = events[events['user_id'] == 'user_01']
for desc, grp in u1.groupby('description'):
    print(f"Desc: {desc:35s} | Count: {len(grp):2d} | Category: {grp['category'].iloc[0]:15s} | Statuses: {grp['status'].unique()} | Dates: {list(grp['settlement_date'])[:4]}")
