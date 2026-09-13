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
messages = pd.read_csv('dataset/messages.csv')

for eid, amt in IMAGE_AMOUNTS.items():
    mask = events['event_id'] == eid
    events.loc[mask, 'amount'] = amt

def get_message_info(user_id):
    u_msgs = messages[messages['user_id'] == user_id]
    info = {
        'salary_amount': None,
        'salary_date': None,
        'rent_multiplier': 1.0,
    }
    for _, msg in u_msgs.iterrows():
        txt = str(msg['message_text'])
        m_rent = re.search(r'increases monthly rent by (\d+)%', txt, re.IGNORECASE)
        if m_rent:
            info['rent_multiplier'] = 1.0 + (float(m_rent.group(1)) / 100.0)
            
        m_sal_date = re.search(r'expected on (\d{4}-\d{2}-\d{2})', txt, re.IGNORECASE)
        if m_sal_date:
            info['salary_date'] = m_sal_date.group(1)
        m_sal_date2 = re.search(r'berlaku mulai (\d{4}-\d{2}-\d{2})', txt, re.IGNORECASE)
        if m_sal_date2:
            info['salary_date'] = m_sal_date2.group(1)
            
        m_sal_eur = re.search(r'(?:pay is|salary is reduced to|first salary will be|salary of) EUR ([\d\.]+)', txt, re.IGNORECASE)
        if m_sal_eur:
            info['salary_amount'] = float(m_sal_eur.group(1))
            
        m_sal_idr = re.search(r'(?:naik menjadi|dikonfirmasi adalah) IDR ([\d\.]+)', txt, re.IGNORECASE)
        if m_sal_idr:
            info['salary_amount'] = float(m_sal_idr.group(1).replace('.', ''))
            
    return info

def simulate_user(user_id, req_date_str, days=90):
    req_date = datetime.strptime(req_date_str, '%Y-%m-%d').date()
    end_date = req_date + timedelta(days=days)
    prof = profiles[profiles['user_id'] == user_id].iloc[0]
    curr_bal = float(prof['current_available_balance'])
    min_bal = float(prof['minimum_balance_to_keep'])
    
    msg_info = get_message_info(user_id)
    
    u_ev = events[events['user_id'] == user_id].copy()
    u_ev['s_dt'] = pd.to_datetime(u_ev['settlement_date']).dt.date
    u_ev['e_dt'] = pd.to_datetime(u_ev['event_date']).dt.date
    
    # 1. Past settled events (history)
    past = u_ev[(u_ev['s_dt'] <= req_date) & (u_ev['status'] == 'settled')].copy()
    
    # 2. Future events in CSV (pending debits, next confirmed salary)
    future = u_ev[(u_ev['s_dt'] >= req_date) & (u_ev['s_dt'] <= end_date)].copy()
    
    # Identify recurring patterns from history
    recurring_streams = []
    
    # Monthly categories
    monthly_cats = ['rent', 'utilities', 'debt_repayment', 'education', 'insurance', 'housing', 
                    'entertainment', 'music_subscription', 'delivery_membership', 'streaming', 
                    'cloud_storage', 'gym', 'salary']
                    
    for cat in past['category'].unique():
        if cat in ['investment', 'windfall']:
            continue
        c_events = past[past['category'] == cat].sort_values('s_dt')
        if len(c_events) < 2 and cat not in ['salary']:
            continue
            
        diffs = c_events['s_dt'].diff().dropna().apply(lambda x: x.days).tolist()
        mean_diff = sum(diffs)/len(diffs) if diffs else 30
        
        last_ev = c_events.iloc[-1]
        last_date = last_ev['s_dt']
        last_amt = float(last_ev['amount'])
        direction = last_ev['direction']
        desc = last_ev['description']
        flexibility = last_ev['flexibility']
        min_allowed = float(last_ev['minimum_allowed_amount']) if pd.notna(last_ev['minimum_allowed_amount']) else None
        event_id = last_ev['event_id']
        
        if mean_diff >= 25:
            # Monthly recurring
            recurring_streams.append({
                'type': 'monthly',
                'category': cat,
                'description': desc,
                'day': last_date.day,
                'amount': last_amt,
                'direction': direction,
                'last_date': last_date,
                'flexibility': flexibility,
                'min_allowed': min_allowed,
                'event_id': event_id
            })
        else:
            # Fixed interval (e.g. 5, 7, 10, 14, 21 days)
            interval = round(mean_diff)
            recurring_streams.append({
                'type': 'interval',
                'category': cat,
                'description': desc,
                'interval': interval,
                'amount': last_amt,
                'direction': direction,
                'last_date': last_date,
                'flexibility': flexibility,
                'min_allowed': min_allowed,
                'event_id': event_id
            })

    return recurring_streams, msg_info

print("Simulator draft ready.")
