import pandas as pd

samples = pd.read_csv('dataset/sample_requests.csv')
for idx, r in samples.iterrows():
    print(f"{r['request_id']} | User: {r['user_id']} | Date: {r['request_date']} | ReqAmt: {r['requested_amount']} | SafeAmt: {r['amount_safe_to_pay']} | Status: {r['affordability_status']} | Method: {r['recommended_payment_method']} | Plan: {r['payment_plan']} | EarliestFull: {r['earliest_date_for_full_payment']} | Changes: {r['spending_changes_needed']}")
