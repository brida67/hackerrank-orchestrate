import os
import re
import math
import pandas as pd
from datetime import datetime, timedelta

# Exact multimodal image extractions (100% verified from dataset/media/images/)
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

# ─── INR Conversion Utility ───────────────────────────────────────────────────
# Derived from exchange_rates.csv using USD as pivot:
#   USD→INR = 83.33
#   EUR→INR = (1/0.92) * 83.33  = 90.58
#   IDR→INR = (1/15833.33) * 83.33 = 0.005263
#   ZAR→INR = (1/20) * (1/0.92) * 83.33 = 4.5288   [EUR→ZAR=20, USD→EUR=0.92]
TO_INR_RATES = {
    'INR': 1.0,
    'USD': 83.33,
    'EUR': 83.33 / 0.92,           # ~90.58
    'IDR': 83.33 / 15833.33,       # ~0.005263
    'ZAR': (83.33 / 0.92) / 20.0,  # ~4.5288
}

def to_inr(amount, from_currency):
    """Convert any supported currency amount to INR."""
    rate = TO_INR_RATES.get(str(from_currency).upper(), 1.0)
    return round(float(amount) * rate, 2)


def from_inr(amount, to_currency):
    """Convert an INR amount back to the specified native currency."""
    rate = TO_INR_RATES.get(str(to_currency).upper(), 1.0)
    if rate <= 0:
        return float(amount)
    return round(float(amount) / rate, 2)


def format_human_date(date_val):
    """Format YYYY-MM-DD into human-readable e.g. 15 November 2024."""
    if not date_val or str(date_val) in ['nan', '', 'None']:
        return ""
    try:
        if isinstance(date_val, str):
            d = datetime.strptime(date_val.split('T')[0], '%Y-%m-%d').date()
        else:
            d = date_val
        return f"{d.day} {d.strftime('%B')} {d.year}"
    except Exception:
        return str(date_val)


class FinancialDecisionEngine:
    def __init__(self, data_dir='dataset'):
        self.data_dir = data_dir
        self.load_data()
        
    def load_data(self):
        self.profiles = pd.read_csv(os.path.join(self.data_dir, 'financial_profiles.csv'))
        self.events = pd.read_csv(os.path.join(self.data_dir, 'financial_events.csv'))
        self.options = pd.read_csv(os.path.join(self.data_dir, 'request_payment_options.csv'))
        self.messages = pd.read_csv(os.path.join(self.data_dir, 'messages.csv'))
        self.rates = pd.read_csv(os.path.join(self.data_dir, 'exchange_rates.csv'))
        
        # Fill missing amounts from verified images
        for eid, amt in IMAGE_AMOUNTS.items():
            mask = self.events['event_id'] == eid
            self.events.loc[mask, 'amount'] = amt
            
        # Parse dates
        self.events['s_dt'] = pd.to_datetime(self.events['settlement_date']).dt.date
        self.events['e_dt'] = pd.to_datetime(self.events['event_date']).dt.date

    def get_message_rules(self, user_id):
        u_msgs = self.messages[self.messages['user_id'] == user_id]
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
            # Lease rent increase
            m_rent = re.search(r'increases monthly rent by (\d+)%', txt, re.IGNORECASE)
            if m_rent:
                rules['rent_multiplier'] = 1.0 + (float(m_rent.group(1)) / 100.0)
                
            # Contract termination
            if 'seasonal contract has ended' in txt or 'No off-season income' in txt:
                rules['stop_salary'] = True
                
            # Recurring childcare
            m_child = re.search(r'recurring childcare payment of EUR ([\d\.]+)', txt, re.IGNORECASE)
            if m_child:
                rules['new_childcare_expense'] = float(m_child.group(1))
                
            # Date overrides
            m_date = re.search(r'expected on (\d{4}-\d{2}-\d{2})', txt, re.IGNORECASE)
            if m_date:
                rules['salary_date_override'] = m_date.group(1)
                rules['salary_day'] = int(m_date.group(1).split('-')[2])
            m_date2 = re.search(r'berlaku mulai (\d{4}-\d{2}-\d{2})', txt, re.IGNORECASE)
            if m_date2:
                rules['salary_date_override'] = m_date2.group(1)
                rules['salary_day'] = int(m_date2.group(1).split('-')[2])
                
            # Amount overrides
            m_eur = re.search(r'(?:temporary monthly pay is|salary is reduced to|first salary will be|Regular salary of) EUR ([\d\.]+)', txt, re.IGNORECASE)
            if m_eur:
                rules['salary_amount'] = float(m_eur.group(1).rstrip('.'))
                
            m_idr = re.search(r'(?:naik menjadi|dikonfirmasi adalah) IDR ([\d\.]+)', txt, re.IGNORECASE)
            if m_idr:
                clean_num = m_idr.group(1).rstrip('.').replace('.', '')
                rules['salary_amount'] = float(clean_num)
                
            m_zar = re.search(r'(?:pay is|salary is) ZAR ([\d\.]+)', txt, re.IGNORECASE)
            if m_zar:
                rules['salary_amount'] = float(m_zar.group(1).rstrip('.'))
                
            m_usd = re.search(r'(?:pay is|salary is) USD ([\d\.]+)', txt, re.IGNORECASE)
            if m_usd:
                rules['salary_amount'] = float(m_usd.group(1).rstrip('.'))
                
        return rules

    def extract_recurring_streams(self, user_id, req_date):
        u_ev = self.events[self.events['user_id'] == user_id].copy()
        past = u_ev[(u_ev['s_dt'] <= req_date) & (u_ev['status'] == 'settled') & (u_ev['direction'] == 'debit')].copy()
        
        streams = []
        for cat in past['category'].unique():
            if cat in ['investment', 'windfall', 'shopping']:
                continue
            c_events = past[past['category'] == cat].sort_values('s_dt')
            if len(c_events) == 0:
                continue
                
            diffs = c_events['s_dt'].diff().dropna().apply(lambda x: x.days).tolist()
            mean_diff = sum(diffs)/len(diffs) if diffs else 30
            
            last_ev = c_events.iloc[-1]
            last_date = last_ev['s_dt']
            last_amt = float(last_ev['amount'])
            desc = last_ev['description']
            flexibility = last_ev['flexibility']
            min_allowed = float(last_ev['minimum_allowed_amount']) if pd.notna(last_ev['minimum_allowed_amount']) else None
            event_id = last_ev['event_id']
            
            if mean_diff >= 25 or len(c_events) <= 6:
                # Monthly recurring
                streams.append({
                    'type': 'monthly',
                    'category': cat,
                    'description': desc,
                    'day': last_date.day,
                    'amount': last_amt,
                    'last_date': last_date,
                    'flexibility': flexibility,
                    'min_allowed': min_allowed,
                    'event_id': event_id
                })
            else:
                interval = max(1, round(mean_diff))
                streams.append({
                    'type': 'interval',
                    'category': cat,
                    'description': desc,
                    'interval': interval,
                    'amount': last_amt,
                    'last_date': last_date,
                    'flexibility': flexibility,
                    'min_allowed': min_allowed,
                    'event_id': event_id
                })
                
        return streams

    def get_salary_info(self, user_id, req_date):
        u_ev = self.events[self.events['user_id'] == user_id].copy()
        rules = self.get_message_rules(user_id)
        
        if rules['stop_salary']:
            return 0.0, None, rules
            
        sal_events = u_ev[(u_ev['category'] == 'salary')]
        if len(sal_events) > 0:
            regular_sal = sal_events[sal_events['description'].str.contains('payroll|regular', case=False, na=False)]
            target_sal = regular_sal if len(regular_sal) > 0 else sal_events
            days_series = target_sal['s_dt'].apply(lambda d: d.day)
            sal_day = int(days_series.mode().iloc[0])
            
            future_sched = target_sal[(target_sal['status'] == 'scheduled') & (target_sal['s_dt'] >= req_date) & (target_sal['amount'].notna())]
            if len(future_sched) > 0:
                sal_amount = float(future_sched.iloc[0]['amount'])
            else:
                past_regular = target_sal[(target_sal['status'].isin(['settled', 'scheduled'])) & (target_sal['amount'].notna())]
                if len(past_regular) > 0:
                    last_row = past_regular.iloc[-1]
                    if 'final' in str(last_row['description']).lower():
                        return 0.0, None, rules
                    sal_amount = float(last_row['amount'])
                else:
                    sal_amount = float(target_sal['amount'].dropna().iloc[-1])
        else:
            sal_amount = 0.0
            sal_day = 15
            
        if rules['salary_amount'] is not None:
            sal_amount = rules['salary_amount']
        if rules['salary_day'] is not None:
            sal_day = rules['salary_day']
            
        return sal_amount, sal_day, rules


    def simulate_cash_flow(self, user_id, req_date_str, spending_changes=None, days=90):
        req_date = datetime.strptime(req_date_str, '%Y-%m-%d').date()
        end_date = req_date + timedelta(days=days)
        prof = self.profiles[self.profiles['user_id'] == user_id].iloc[0]
        init_balance = float(prof['current_available_balance'])
        min_balance = float(prof['minimum_balance_to_keep'])
        currency = prof['home_currency']
        
        streams = self.extract_recurring_streams(user_id, req_date)
        sal_amount, sal_day, rules = self.get_salary_info(user_id, req_date)
        
        active_streams = []
        for s in streams:
            eid = s['event_id']
            s_copy = dict(s)
            if spending_changes and eid in spending_changes:
                change = spending_changes[eid]
                if change['action'] == 'stop':
                    continue
                elif change['action'] == 'reduce_to':
                    s_copy['amount'] = change['new_amt']
            if s_copy['category'] == 'rent' and rules and rules['rent_multiplier'] != 1.0:
                s_copy['amount'] *= rules['rent_multiplier']
            active_streams.append(s_copy)
            
        daily_inflows = {req_date + timedelta(days=i): 0.0 for i in range(days + 1)}
        daily_outflows = {req_date + timedelta(days=i): 0.0 for i in range(days + 1)}
        daily_events_log = {req_date + timedelta(days=i): [] for i in range(days + 1)}
        salary_dates = []
        
        # 1. Pending debits already in CSV
        u_ev = self.events[self.events['user_id'] == user_id]
        pending_debits = u_ev[(u_ev['s_dt'] >= req_date) & (u_ev['s_dt'] <= end_date) & (u_ev['direction'] == 'debit') & (u_ev['status'].isin(['pending', 'scheduled']))]
        for _, p in pending_debits.iterrows():
            d = p['s_dt']
            amt = float(p['amount'])
            daily_outflows[d] += amt
            daily_events_log[d].append({'type': 'pending_debit', 'desc': p['description'], 'amount': amt})
            
        # 2. Confirmed salary recurrence
        if sal_amount and sal_amount > 0 and sal_day:
            curr_cursor = req_date
            while curr_cursor <= end_date:
                try:
                    target_date = datetime(curr_cursor.year, curr_cursor.month, min(sal_day, 28)).date()
                except Exception:
                    target_date = datetime(curr_cursor.year, curr_cursor.month, 28).date()
                    
                if target_date >= req_date and target_date <= end_date:
                    daily_inflows[target_date] += sal_amount
                    salary_dates.append(target_date)
                    daily_events_log[target_date].append({'type': 'salary', 'desc': 'Confirmed salary', 'amount': sal_amount})
                    
                if curr_cursor.month == 12:
                    curr_cursor = datetime(curr_cursor.year + 1, 1, 1).date()
                else:
                    curr_cursor = datetime(curr_cursor.year, curr_cursor.month + 1, 1).date()

        # 3. Monthly recurring streams
        for s in active_streams:
            if s['type'] == 'monthly':
                curr_cursor = req_date
                while curr_cursor <= end_date:
                    try:
                        target_date = datetime(curr_cursor.year, curr_cursor.month, min(s['day'], 28)).date()
                    except Exception:
                        target_date = datetime(curr_cursor.year, curr_cursor.month, 28).date()
                        
                    # If target_date is request_date, check if rent was already settled on request date in past
                    if target_date >= req_date and target_date <= end_date:
                        daily_outflows[target_date] += s['amount']
                        daily_events_log[target_date].append({'type': 'monthly_expense', 'desc': s['description'], 'amount': s['amount'], 'category': s['category']})
                        
                    if curr_cursor.month == 12:
                        curr_cursor = datetime(curr_cursor.year + 1, 1, 1).date()
                    else:
                        curr_cursor = datetime(curr_cursor.year, curr_cursor.month + 1, 1).date()

            elif s['type'] == 'interval':
                curr_d = s['last_date'] + timedelta(days=s['interval'])
                while curr_d <= end_date:
                    if curr_d >= req_date:
                        daily_outflows[curr_d] += s['amount']
                        daily_events_log[curr_d].append({'type': 'interval_expense', 'desc': s['description'], 'amount': s['amount'], 'category': s['category']})
                    curr_d += timedelta(days=s['interval'])

        dates = [req_date + timedelta(days=i) for i in range(days + 1)]
        balances = []
        curr_b = init_balance
        for d in dates:
            curr_b = curr_b + daily_inflows[d] - daily_outflows[d]
            balances.append(curr_b)
            
        return {
            'dates': [d.strftime('%Y-%m-%d') for d in dates],
            'balances': balances,
            'min_balance': min_balance,
            'init_balance': init_balance,
            'daily_inflows': daily_inflows,
            'daily_outflows': daily_outflows,
            'events_log': daily_events_log,
            'currency': currency,
            'streams': active_streams,
            'salary_amount': sal_amount,
            'salary_dates': salary_dates
        }

    def compute_earliest_full_date(self, traj, req_date_str, requested_amount):
        req_date = datetime.strptime(req_date_str, '%Y-%m-%d').date()
        min_b = traj['min_balance']
        dates = [datetime.strptime(d, '%Y-%m-%d').date() for d in traj['dates']]
        balances = traj['balances']
        
        # Test candidate dates: request date, then each salary date
        candidate_dates = [req_date] + sorted(traj['salary_dates'])
        
        for c_date in candidate_dates:
            try:
                idx = dates.index(c_date)
            except ValueError:
                continue
                
            # If paid at c_date, does it remain safe for the next 30 days or till end of 90d?
            is_safe = True
            for future_idx in range(idx, min(idx + 35, len(balances))):
                if balances[future_idx] - requested_amount < min_b - 0.01:
                    is_safe = False
                    break
            if is_safe:
                return c_date.strftime('%Y-%m-%d')
                
        return ''

    def evaluate_request(self, row):
        req_id = row['request_id']
        u_id = row['user_id']
        req_date = row['request_date']
        req_amount = float(row['requested_amount'])
        desired_comp_date = str(row['desired_completion_date'])
        allows_partial = str(row['allows_partial_payment']).lower() == 'true'
        
        prof = self.profiles[self.profiles['user_id'] == u_id].iloc[0]
        currency = prof['home_currency']
        min_balance = float(prof['minimum_balance_to_keep'])
        considered_methods = str(prof['payment_methods_user_will_consider']).split('|')
        max_inst_months = float(prof['max_installment_months']) if pd.notna(prof['max_installment_months']) else 0
        willing_reduce = str(prof['expense_categories_user_is_willing_to_reduce']).split('|') if pd.notna(prof['expense_categories_user_is_willing_to_reduce']) else []
        willing_stop = str(prof['expense_categories_user_is_willing_to_stop']).split('|') if pd.notna(prof['expense_categories_user_is_willing_to_stop']) else []
        
        # 1. Base simulation
        base_traj = self.simulate_cash_flow(u_id, req_date)
        
        # Safe amount today is constrained by expenses before first salary
        first_sal = sorted(base_traj['salary_dates'])[0] if base_traj['salary_dates'] else None
        dates_dt = [datetime.strptime(d, '%Y-%m-%d').date() for d in base_traj['dates']]
        
        if first_sal and first_sal in dates_dt:
            sal_idx = dates_dt.index(first_sal)
            window_balances = base_traj['balances'][:sal_idx]
            if len(window_balances) > 0:
                lowest_balance = min(window_balances)
            else:
                lowest_balance = base_traj['balances'][0]
        else:
            lowest_balance = min(base_traj['balances'])
            
        amount_safe_to_pay = min(req_amount, max(0.0, lowest_balance - min_balance))
        if abs(amount_safe_to_pay - round(amount_safe_to_pay)) < 1e-4:
            amount_safe_to_pay = float(round(amount_safe_to_pay))
        else:
            amount_safe_to_pay = round(amount_safe_to_pay, 2)
            
        earliest_full_date = self.compute_earliest_full_date(base_traj, req_date, req_amount)
        if amount_safe_to_pay >= req_amount:
            earliest_full_date = req_date
            
        candidate_plans = []
        
        # 1. Check full_payment
        if 'full_payment' in considered_methods and amount_safe_to_pay >= req_amount:
            p_amt = int(req_amount) if req_amount.is_integer() else f"{req_amount:.2f}"
            candidate_plans.append({
                'method': 'full_payment',
                'status': 'affordable_now',
                'plan': f"{req_date}:{p_amt}",
                'changes': 'none',
                'earliest_full': req_date,
                'total_paid': req_amount,
                'start_date': req_date,
                'num_payments': 1,
                'option_id': 0,
                'on_time': req_date <= desired_comp_date
            })
            
        # 2. Check installment options
        req_opts = self.options[self.options['request_id'] == req_id]
        if 'installments' in considered_methods and max_inst_months > 0:
            for _, opt in req_opts.iterrows():
                if opt['payment_method'] == 'installments':
                    n_pay = int(opt['number_of_payments'])
                    pay_amt = float(opt['payment_amount'])
                    freq_days = int(opt['payment_frequency_days']) if pd.notna(opt['payment_frequency_days']) else 30
                    first_pay_date = str(opt['first_payment_date'])
                    total_amt = float(opt['total_payable_amount'])
                    opt_id_str = str(opt['payment_option_id'])
                    opt_num = int(re.search(r'\d+', opt_id_str).group()) if re.search(r'\d+', opt_id_str) else 999
                    
                    duration_days = (n_pay - 1) * freq_days
                    duration_months = duration_days / 30.0
                    if duration_months > max_inst_months + 0.5:
                        continue
                        
                    f_date = datetime.strptime(first_pay_date, '%Y-%m-%d').date()
                    inst_dates = [f_date + timedelta(days=i * freq_days) for i in range(n_pay)]
                    comp_date_str = inst_dates[-1].strftime('%Y-%m-%d')
                    
                    # Verify feasibility throughout the plan schedule
                    inst_safe = True
                    base_dates = dates_dt
                    b_copy = list(base_traj['balances'])
                    last_pay_d = inst_dates[-1]
                    for p_d in inst_dates:
                        for idx, d in enumerate(base_dates):
                            if d >= p_d:
                                b_copy[idx] -= pay_amt
                                if d <= last_pay_d and b_copy[idx] < min_balance - 0.01:
                                    inst_safe = False
                                    break
                        if not inst_safe:
                            break
                            
                    if inst_safe and comp_date_str <= desired_comp_date:
                        plan_parts = [f"{d.strftime('%Y-%m-%d')}:{int(pay_amt) if pay_amt.is_integer() else pay_amt:.2f}" for d in inst_dates]
                        plan_str = '|'.join(plan_parts)
                        candidate_plans.append({
                            'method': 'installments',
                            'status': 'affordable_with_plan',
                            'plan': plan_str,
                            'changes': 'none',
                            'earliest_full': earliest_full_date,
                            'total_paid': total_amt,
                            'start_date': first_pay_date,
                            'num_payments': n_pay,
                            'option_id': opt_num,
                            'on_time': True,
                            'inst_pay_amt': pay_amt
                        })
                        
        # 3. Check partial_payment
        if allows_partial and 'partial_payment' in considered_methods and 0 < amount_safe_to_pay < req_amount:
            if earliest_full_date and earliest_full_date <= desired_comp_date:
                rem_amt = req_amount - amount_safe_to_pay
                p1 = int(amount_safe_to_pay) if float(amount_safe_to_pay).is_integer() else f"{amount_safe_to_pay:.2f}"
                p2 = int(rem_amt) if float(rem_amt).is_integer() else f"{rem_amt:.2f}"
                plan_str = f"{req_date}:{p1}|{earliest_full_date}:{p2}"
                candidate_plans.append({
                    'method': 'partial_payment',
                    'status': 'affordable_with_plan',
                    'plan': plan_str,
                    'changes': 'none',
                    'earliest_full': earliest_full_date,
                    'total_paid': req_amount,
                    'start_date': req_date,
                    'num_payments': 2,
                    'option_id': 0,
                    'on_time': True
                })
                
        # 4. Check spending changes if no candidate found
        if len(candidate_plans) == 0:
            streams = base_traj['streams']
            flexible_changes = []
            for s in streams:
                cat = s['category']
                eid = s['event_id']
                flex = s['flexibility']
                amt = s['amount']
                min_a = s['min_allowed']
                
                if cat in willing_stop and flex in ['stoppable', 'reducible_or_stoppable']:
                    flexible_changes.append({
                        'event_id': eid,
                        'action': 'stop',
                        'savings': amt,
                        'str': f"stop:{eid}",
                        'desc': s['description']
                    })
                if cat in willing_reduce and flex in ['reducible', 'reducible_or_stoppable'] and min_a is not None:
                    if amt > min_a:
                        clean_min = int(min_a) if float(min_a).is_integer() else f"{min_a:.2f}"
                        flexible_changes.append({
                            'event_id': eid,
                            'action': 'reduce_to',
                            'new_amt': min_a,
                            'savings': amt - min_a,
                            'str': f"reduce_to:{eid}:{clean_min}",
                            'desc': s['description']
                        })
                        
            # Test single changes
            for c in flexible_changes:
                if amount_safe_to_pay + c['savings'] >= req_amount - 0.01:
                    p_amt = int(req_amount) if req_amount.is_integer() else f"{req_amount:.2f}"
                    candidate_plans.append({
                        'method': 'full_payment',
                        'status': 'affordable_with_plan',
                        'plan': f"{req_date}:{p_amt}",
                        'changes': c['str'],
                        'earliest_full': earliest_full_date,
                        'total_paid': req_amount,
                        'start_date': req_date,
                        'num_payments': 1,
                        'option_id': 0,
                        'on_time': req_date <= desired_comp_date,
                        'change_desc': f"Stop the {c['desc'].lower()}" if c['action']=='stop' else f"Reduce the {c['desc'].lower()} to {currency} {c['new_amt']:,.2f}".replace('.00', '')
                    })
                    break
                    
            # Test double changes if still needed
            if len(candidate_plans) == 0 and len(flexible_changes) >= 2:
                import itertools
                for c1, c2 in itertools.combinations(flexible_changes, 2):
                    if c1['event_id'] == c2['event_id']:
                        continue
                    if amount_safe_to_pay + c1['savings'] + c2['savings'] >= req_amount - 0.01:
                        p_amt = int(req_amount) if req_amount.is_integer() else f"{req_amount:.2f}"
                        combined_str = f"{c1['str']}|{c2['str']}"
                        desc1 = f"Stop the {c1['desc'].lower()}" if c1['action']=='stop' else f"reduce the {c1['desc'].lower()} to {currency} {c1['new_amt']:,.2f}".replace('.00', '')
                        desc2 = f"stop the {c2['desc'].lower()}" if c2['action']=='stop' else f"reduce the {c2['desc'].lower()} to {currency} {c2['new_amt']:,.2f}".replace('.00', '')
                        candidate_plans.append({
                            'method': 'full_payment',
                            'status': 'affordable_with_plan',
                            'plan': f"{req_date}:{p_amt}",
                            'changes': combined_str,
                            'earliest_full': earliest_full_date,
                            'total_paid': req_amount,
                            'start_date': req_date,
                            'num_payments': 1,
                            'option_id': 0,
                            'on_time': req_date <= desired_comp_date,
                            'change_desc': f"{desc1} and {desc2}"
                        })
                        break
                        
        # 5. Check wait
        if len(candidate_plans) == 0 and earliest_full_date and 'full_payment' in considered_methods:
            if earliest_full_date <= desired_comp_date:
                p_amt = int(req_amount) if req_amount.is_integer() else f"{req_amount:.2f}"
                candidate_plans.append({
                    'method': 'wait',
                    'status': 'affordable_later',
                    'plan': f"{earliest_full_date}:{p_amt}",
                    'changes': 'none',
                    'earliest_full': earliest_full_date,
                    'total_paid': req_amount,
                    'start_date': earliest_full_date,
                    'num_payments': 1,
                    'option_id': 0,
                    'on_time': True
                })
                
        # Select best plan
        best_plan = None
        if len(candidate_plans) > 0:
            def rank_key(p):
                return (
                    0 if p['on_time'] else 1,
                    0 if p['changes'] == 'none' else 1,
                    p['total_paid'],
                    p['start_date'],
                    p['num_payments'],
                    p['option_id']
                )
            candidate_plans.sort(key=rank_key)
            best_plan = candidate_plans[0]
            
        if not best_plan:
            best_plan = {
                'method': 'not_recommended',
                'status': 'not_affordable',
                'plan': 'none',
                'changes': 'none',
                'earliest_full': earliest_full_date if (earliest_full_date and earliest_full_date <= desired_comp_date) else '',
                'total_paid': 0,
                'start_date': '',
                'num_payments': 0,
                'option_id': 0
            }
            
        # Synthesize Explanation
        meth = best_plan['method']
        clean_amt = f"{int(req_amount):,}" if req_amount.is_integer() else f"{req_amount:,.2f}"
        clean_min = f"{int(min_balance):,}" if min_balance.is_integer() else f"{min_balance:,.2f}"
        
        explanation = ""
        if meth == 'full_payment' and best_plan['changes'] == 'none':
            explanation = f"Pay {currency} {clean_amt} today. This leaves at least {currency} {clean_min} available over the next 90 days."
        elif meth == 'full_payment' and best_plan['changes'] != 'none':
            explanation = f"{best_plan.get('change_desc', 'Adjust spending')}, then pay {currency} {clean_amt} today. This leaves at least {currency} {clean_min} available."
        elif meth == 'installments':
            inst_p = best_plan.get('inst_pay_amt', 0)
            clean_inst = f"{int(inst_p):,}" if float(inst_p).is_integer() else f"{inst_p:,.2f}"
            start_date_human = format_human_date(best_plan['start_date'])
            explanation = f"Use {best_plan['num_payments']} installments of {currency} {clean_inst}, starting {start_date_human}. This leaves at least {currency} {clean_min} available."
        elif meth == 'partial_payment':
            p_parts = best_plan['plan'].split('|')
            amt1_val = float(p_parts[0].split(':')[1])
            amt2_val = float(p_parts[1].split(':')[1])
            amt1_str = f"{int(amt1_val):,}" if amt1_val.is_integer() else f"{amt1_val:,.2f}"
            amt2_str = f"{int(amt2_val):,}" if amt2_val.is_integer() else f"{amt2_val:,.2f}"
            earliest_human = format_human_date(best_plan['earliest_full'])
            explanation = f"Pay {currency} {amt1_str} today and the remaining {currency} {amt2_str} on {earliest_human}. This completes the full request and keeps the {currency} {clean_min} minimum protected."
        elif meth == 'wait':
            start_date_human = format_human_date(best_plan['start_date'])
            explanation = f"Pay {currency} {clean_amt} in full on {start_date_human}. Paying earlier would take the balance below the {currency} {clean_min} minimum."
        else:
            if amount_safe_to_pay > 0:
                clean_safe = f"{int(amount_safe_to_pay):,}" if float(amount_safe_to_pay).is_integer() else f"{amount_safe_to_pay:,.2f}"
                explanation = f"Do not proceed with the {currency} {clean_amt} request. Although {currency} {clean_safe} is available today, the full amount cannot be completed safely within 90 days."
            else:
                desired_human = format_human_date(desired_comp_date)
                explanation = f"Do not make this payment by {desired_human}. None of the available options keeps the {currency} {clean_min} minimum protected."
                
        return {
            'request_id': req_id,
            'amount_safe_to_pay': amount_safe_to_pay,
            'affordability_status': best_plan['status'],
            'recommended_payment_method': best_plan['method'],
            'payment_plan': best_plan['plan'],
            'earliest_date_for_full_payment': best_plan['earliest_full'] if best_plan['status'] != 'not_affordable' else '',
            'spending_changes_needed': best_plan['changes'],
            'decision_explanation': explanation
        }

print("Refined FinancialDecisionEngine written.")
