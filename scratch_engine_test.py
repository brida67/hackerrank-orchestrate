import os
import re
import math
import pandas as pd
from datetime import datetime, timedelta

# Exact verified multimodal image amounts
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

print("Events loaded and image amounts filled.")

# Let's check user messages that update salary or rent or warn about unconfirmed income
def parse_messages(user_id, req_date):
    u_msgs = messages[messages['user_id'] == user_id]
    info = {
        'salary_amount_override': None,
        'salary_date_override': None,
        'rent_multiplier': 1.0,
        'ignore_unconfirmed': True
    }
    for _, msg in u_msgs.iterrows():
        txt = str(msg['message_text'])
        # Rent increase e.g. "increases monthly rent by 12%"
        m_rent = re.search(r'increases monthly rent by (\d+)%', txt, re.IGNORECASE)
        if m_rent:
            pct = float(m_rent.group(1))
            info['rent_multiplier'] = 1.0 + (pct / 100.0)
        
        # Salary update e.g. "Gaji bulanan Anda naik menjadi IDR 42750000. Perubahan ini berlaku mulai 2025-08-15."
        # or "Your confirmed salary is now expected on 2024-09-23."
        # or "Your temporary monthly pay is EUR 1037.52."
        m_sal_date = re.search(r'expected on (\d{4}-\d{2}-\d{2})', txt, re.IGNORECASE)
        if m_sal_date:
            info['salary_date_override'] = m_sal_date.group(1)
            
        m_sal_date2 = re.search(r'berlaku mulai (\d{4}-\d{2}-\d{2})', txt, re.IGNORECASE)
        if m_sal_date2:
            info['salary_date_override'] = m_sal_date2.group(1)
            
        m_sal_eur = re.search(r'(?:pay is|salary is reduced to|first salary will be|salary of) EUR ([\d\.]+)', txt, re.IGNORECASE)
        if m_sal_eur:
            info['salary_amount_override'] = float(m_sal_eur.group(1))
            
        m_sal_idr = re.search(r'(?:naik menjadi|dikonfirmasi adalah) IDR ([\d\.]+)', txt, re.IGNORECASE)
        if m_sal_idr:
            info['salary_amount_override'] = float(m_sal_idr.group(1).replace('.', ''))

    return info

print("Message parser test for user_02:", parse_messages('user_02', '2025-08-05'))
print("Message parser test for user_07:", parse_messages('user_07', '2024-09-05'))
print("Message parser test for user_16:", parse_messages('user_16', '2023-08-12'))
