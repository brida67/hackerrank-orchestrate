import os
import re
import math
import pandas as pd
from datetime import datetime, timedelta

IMAGE_AMOUNTS = {
    'event_253': 4365000.0,    # image_01 (IDR)
    'event_1442': 100000.0,    # image_02 (INR)
    'event_1545': 41272.0,     # image_03 (INR)
    'event_1700': 2854.0,      # image_04 (INR)
    'event_1786': 704.05,      # image_05 (INR)
    'event_3051': 1995.0,      # image_06 (INR)
    'event_3231': 8528.0,      # image_07 (INR)
    'event_4535': 15339.0,     # image_08 (INR)
    'event_5170': 723.0,       # image_09 (INR)
    'event_6033': 79679.26,    # image_10 (INR)
    'event_6859': 3650.0,      # image_11 (INR)
    'event_7307': 33.5,        # image_12 (USD)
    'event_7941': 2298.0,      # image_13 (INR)
    'event_9421': 4543.0,      # image_14 (INR)
    'event_9806': 9968.0,      # image_15 (INR)
    'event_10521': 393.22,     # image_16 (INR)
}

samples = pd.read_csv('dataset/sample_requests.csv')
profiles = pd.read_csv('dataset/financial_profiles.csv')
events = pd.read_csv('dataset/financial_events.csv')
options = pd.read_csv('dataset/request_payment_options.csv')
messages = pd.read_csv('dataset/messages.csv')
rates = pd.read_csv('dataset/exchange_rates.csv')

# Fill image amounts into events
for eid, amt in IMAGE_AMOUNTS.items():
    mask = events['event_id'] == eid
    events.loc[mask, 'amount'] = amt

def get_message_rules(user_id):
    u_msgs = messages[messages['user_id'] == user_id]
    rules = {
        'salary_amount': None,
        'salary_day': None,
        'salary_date_override': None,
        'rent_multiplier': 1.0,
        'stop_salary': False,
        'new_childcare_expense': 0.0,
    }
    for _, msg in u_msgs.iterrows():
        txt = str(msg['message_text'])
        m_rent = re.search(r'increases monthly rent by (\d+)%', txt, re.IGNORECASE)
        if m_rent:
            rules['rent_multiplier'] = 1.0 + (float(m_rent.group(1)) / 100.0)
            
        if 'seasonal contract has ended' in txt or 'No off-season income' in txt:
            rules['stop_salary'] = True
            
        m_child = re.search(r'recurring childcare payment of EUR ([\d\.]+)', txt, re.IGNORECASE)
        if m_child:
            rules['new_childcare_expense'] = float(m_child.group(1))
            
        m_date = re.search(r'expected on (\d{4}-\d{2}-\d{2})', txt, re.IGNORECASE)
        if m_date:
            rules['salary_date_override'] = m_date.group(1)
            rules['salary_day'] = int(m_date.group(1).split('-')[2])
        m_date2 = re.search(r'berlaku mulai (\d{4}-\d{2}-\d{2})', txt, re.IGNORECASE)
        if m_date2:
            rules['salary_date_override'] = m_date2.group(1)
            rules['salary_day'] = int(m_date2.group(1).split('-')[2])
            
        m_eur = re.search(r'(?:temporary monthly pay is|salary is reduced to|first salary will be|Regular salary of) EUR ([\d\.]+)', txt, re.IGNORECASE)
        if m_eur:
            rules['salary_amount'] = float(m_eur.group(1))
            
        m_idr = re.search(r'(?:naik menjadi|dikonfirmasi adalah) IDR ([\d\.]+)', txt, re.IGNORECASE)
        if m_idr:
            clean_num = m_idr.group(1).replace('.', '')
            rules['salary_amount'] = float(clean_num)
            
        m_zar = re.search(r'(?:pay is|salary is) ZAR ([\d\.]+)', txt, re.IGNORECASE)
        if m_zar:
            rules['salary_amount'] = float(m_zar.group(1))
            
        m_usd = re.search(r'(?:pay is|salary is) USD ([\d\.]+)', txt, re.IGNORECASE)
        if m_usd:
            rules['salary_amount'] = float(m_usd.group(1))
            
    return rules

print("Setup completed successfully.")
