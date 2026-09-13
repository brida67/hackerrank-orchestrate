import pandas as pd

events = pd.read_csv('dataset/financial_events.csv')
for eid in ['event_646', 'event_647', 'event_648', 'event_649', 'event_677', 'event_703', 'event_716']:
    r = events[events['event_id'] == eid].iloc[0]
    print(eid, r['description'], r['amount'], r['settlement_date'])
