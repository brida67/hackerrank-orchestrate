import pandas as pd

events = pd.read_csv('dataset/financial_events.csv')
salary_events = events[events['category'] == 'salary']
print("Salary settlement dates:")
print(salary_events[['user_id', 'description', 'amount', 'settlement_date', 'status']].head(30))
