import pandas as pd

events = pd.read_csv('dataset/financial_events.csv')
sched_salary = events[(events['category'] == 'salary') & (events['status'] == 'scheduled')]
print(f"Total users with scheduled salary: {len(sched_salary['user_id'].unique())} out of {len(events['user_id'].unique())}")
print(sched_salary[['user_id', 'description', 'amount', 'currency', 'settlement_date']].head(20))
