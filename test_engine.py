#!/usr/bin/env python3
"""
HackerRank Orchestrate - Complete & Accurate Financial Decision Engine
"""

import os
import re
import csv
import sys
from datetime import datetime, timedelta
from collections import defaultdict
from statistics import median, mode as stat_mode

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, 'dataset')
OUTPUT_FILE = os.path.join(SCRIPT_DIR, 'output.csv')

IMAGE_AMOUNTS = {
    'event_253': 4365000.0,
    'event_1442': 100000.0,
    'event_1545': 41272.0,
    'event_1700': 2854.0,
    'event_1786': 704.05,
    'event_3051': 1995.0,
    'event_3231': 8528.0,
    'event_4535': 15339.0,
    'event_5170': 723.0,
    'event_6033': 79679.26,
    'event_6859': 3650.0,
    'event_7307': 33.5,
    'event_7941': 2298.0,
    'event_9421': 4543.0,
    'event_9806': 9968.0,
    'event_10521': 393.22,
}

def read_csv(filepath):
    rows = []
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows

def safe_float(val, default=0.0):
    if val is None or str(val).strip() in ('', 'nan', 'None', 'NaN'):
        return default
    try:
        return float(str(val).strip())
    except (ValueError, TypeError):
        return default

def safe_date(val):
    if val is None or str(val).strip() in ('', 'nan', 'None', 'NaN'):
        return None
    try:
        return datetime.strptime(str(val).strip().split('T')[0], '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return None

def fmt_amt(val):
    v = float(val)
    if v == int(v):
        return str(int(v))
    return f"{v:.2f}"

def fmt_disp(val, cur):
    v = float(val)
    if v == int(v):
        return f"{cur} {int(v):,}"
    return f"{cur} {v:,.2f}"

def fmt_date(d):
    if d is None:
        return ""
    if isinstance(d, str):
        d = safe_date(d)
    if d is None:
        return ""
    return f"{d.day} {d.strftime('%B')} {d.year}"

def parse_amount(raw_str, is_idr=False):
    raw = str(raw_str).replace(',', '').rstrip('.')
    if is_idr and '.' in raw:
        parts = raw.split('.')
        if len(parts[-1]) != 2:
            raw = raw.replace('.', '')
    try:
        return float(raw)
    except:
        return 0.0

profiles_raw = read_csv(os.path.join(DATA_DIR, 'financial_profiles.csv'))
events_raw = read_csv(os.path.join(DATA_DIR, 'financial_events.csv'))
requests_raw = read_csv(os.path.join(DATA_DIR, 'requests.csv'))
sample_raw = read_csv(os.path.join(DATA_DIR, 'sample_requests.csv'))
options_raw = read_csv(os.path.join(DATA_DIR, 'request_payment_options.csv'))
messages_raw = read_csv(os.path.join(DATA_DIR, 'messages.csv'))
rates_raw = read_csv(os.path.join(DATA_DIR, 'exchange_rates.csv'))

profiles = {p['user_id']: p for p in profiles_raw}
options_by_req = defaultdict(list)
for o in options_raw:
    options_by_req[o['request_id']].append(o)

msgs_by_user = defaultdict(list)
for m in messages_raw:
    msgs_by_user[m['user_id']].append(m)

xrates = []
for r in rates_raw:
    xrates.append({
        'date': safe_date(r['rate_date']),
        'from': r['from_currency'],
        'to': r['to_currency'],
        'rate': safe_float(r['rate'])
    })

def get_rate(from_c, to_c, ref_date=None):
    if from_c == to_c:
        return 1.0
    best = None
    for r in xrates:
        if r['from'] == from_c and r['to'] == to_c:
            if ref_date is None or (r['date'] and r['date'] <= ref_date):
                if best is None or (r['date'] and r['date'] > best['date']):
                    best = r
    if best:
        return best['rate']
    best = None
    for r in xrates:
        if r['from'] == to_c and r['to'] == from_c:
            if ref_date is None or (r['date'] and r['date'] <= ref_date):
                if best is None or (r['date'] and r['date'] > best['date']):
                    best = r
    if best and best['rate'] != 0:
        return 1.0 / best['rate']
    if from_c != 'USD' and to_c != 'USD':
        r1 = get_rate(from_c, 'USD', ref_date)
        r2 = get_rate('USD', to_c, ref_date)
        if r1 and r2:
            return r1 * r2
    return 1.0

def convert_home(amount, from_c, home_c, ref_date=None):
    if from_c == home_c or amount == 0:
        return amount
    return round(amount * get_rate(from_c, home_c, ref_date), 2)

events_by_user = defaultdict(list)
for e in events_raw:
    eid = e['event_id']
    if eid in IMAGE_AMOUNTS and str(e.get('amount', '')).strip() == '':
        e['amount'] = str(IMAGE_AMOUNTS[eid])
    amt = safe_float(e.get('amount'))
    e_cur = e.get('currency')
    uid = e.get('user_id')
    home_c = profiles[uid]['home_currency']
    s_dt = safe_date(e.get('settlement_date'))
    if e_cur and e_cur != home_c and amt > 0:
        amt = convert_home(amt, e_cur, home_c, s_dt)
    e['_amt'] = amt
    e['_edt'] = safe_date(e.get('event_date'))
    e['_sdt'] = s_dt
    e['_mina'] = safe_float(e.get('minimum_allowed_amount'), default=None)
    if e.get('_mina') is not None and e_cur and e_cur != home_c:
        e['_mina'] = convert_home(e['_mina'], e_cur, home_c, s_dt)
    events_by_user[e['user_id']].append(e)

def parse_msgs(user_id, home_cur):
    msgs = msgs_by_user.get(user_id, [])
    R = {
        'sal_amt': None, 'sal_day': None, 'sal_date_override': None,
        'rent_mult': 1.0, 'stop_sal': False, 'employment_ended': False,
        'childcare_new': 0.0, 'invoice_amt': None, 'invoice_date': None,
        'disputed_eid': None, 'sal_foreign': None, 'sal_foreign_cur': None,
        'sal_foreign_date': None, 'household_remaining': None,
    }
    
    for msg in msgs:
        txt = str(msg.get('message_text', ''))
        rel = str(msg.get('related_event_id', '')).strip()
        is_idr = 'IDR' in txt
        
        # Lease rent increase
        m = re.search(r'increases monthly rent by (\d+)%', txt, re.I)
        if m:
            R['rent_mult'] = 1.0 + (float(m.group(1)) / 100.0)
            
        # Contract ended
        if any(p in txt for p in ['seasonal contract has ended', 'Kontrak musiman saat ini telah berakhir', 'employment has ended', 'Hubungan kerja Anda telah berakhir']):
            R['stop_sal'] = True
            R['employment_ended'] = True
            
        # Household remaining
        m = re.search(r'(?:remaining confirmed monthly salary is|Sisa gaji bulanan yang dikonfirmasi adalah)\s+(?:IDR|INR|ZAR|EUR|USD)\s*([\d,\.]+)', txt, re.I)
        if m:
            R['household_remaining'] = parse_amount(m.group(1), is_idr)
            R['sal_amt'] = R['household_remaining']
            R['stop_sal'] = False
            
        # Salary increase
        m = re.search(r'(?:naik menjadi|increased to)\s+(?:IDR|INR|ZAR|EUR|USD)\s*([\d,\.]+)', txt)
        if m:
            R['sal_amt'] = parse_amount(m.group(1), is_idr)
            m2 = re.search(r'(?:berlaku mulai|applies from)\s+(\d{4}-\d{2}-\d{2})', txt)
            if m2:
                R['sal_date_override'] = m2.group(1)
                R['sal_day'] = int(m2.group(1).split('-')[2])
                
        # Temp/reduced salary
        m = re.search(r'(?:temporary monthly pay is|salary is reduced to|next salary is reduced to)\s+(?:IDR|INR|ZAR|EUR|USD)\s*([\d,\.]+)', txt, re.I)
        if m:
            R['sal_amt'] = parse_amount(m.group(1), is_idr)
            
        # First salary
        m = re.search(r'(?:first salary will be|first salary(?:\s+from the new employer)? is)\s+(?:IDR|INR|ZAR|EUR|USD)\s*([\d,\.]+)', txt, re.I)
        if m:
            R['sal_amt'] = parse_amount(m.group(1), is_idr)
            m2 = re.search(r'(?:confirmed (?:credit )?(?:for|date is))\s+(\d{4}-\d{2}-\d{2})', txt, re.I)
            if m2:
                R['sal_date_override'] = m2.group(1)
                R['sal_day'] = int(m2.group(1).split('-')[2])
                
        # Confirmed base salary
        m = re.search(r'(?:confirmed base salary is|Gaji pokok yang dikonfirmasi adalah)\s+(?:IDR|INR|ZAR|EUR|USD)\s*([\d,\.]+)', txt, re.I)
        if m:
            R['sal_amt'] = parse_amount(m.group(1), is_idr)
            
        # Regular salary resumes
        m = re.search(r'(?:Regular salary of)\s+(?:IDR|INR|ZAR|EUR|USD)\s*([\d,\.]+)\s+resumes on\s+(\d{4}-\d{2}-\d{2})', txt, re.I)
        if m:
            R['sal_amt'] = parse_amount(m.group(1), is_idr)
            R['sal_date_override'] = m.group(2)
            R['sal_day'] = int(m.group(2).split('-')[2])
            
        # Expected date
        m = re.search(r'(?:expected on|diperkirakan masuk pada)\s+(\d{4}-\d{2}-\d{2})', txt, re.I)
        if m:
            R['sal_date_override'] = m.group(1)
            R['sal_day'] = int(m.group(1).split('-')[2])
            
        # Foreign salary
        m = re.search(r'(?:salary of|employer has confirmed a)\s+(USD|EUR)\s*([\d,\.]+)\s+(?:is )?(?:confirmed for|salary credit for)\s+(\d{4}-\d{2}-\d{2})', txt, re.I)
        if m:
            R['sal_foreign'] = parse_amount(m.group(2))
            R['sal_foreign_cur'] = m.group(1)
            R['sal_foreign_date'] = m.group(3)
            R['sal_day'] = int(m.group(3).split('-')[2])
            
        # Approved invoice
        m = re.search(r'(?:approved (?:an )?invoice payment of|menyetujui pembayaran faktur sebesar)\s+(?:IDR|INR|ZAR|EUR|USD)\s*([\d,\.]+)', txt, re.I)
        if m:
            R['invoice_amt'] = parse_amount(m.group(1), is_idr)
            m2 = re.search(r'(?:expected on|diperkirakan pada)\s+(\d{4}-\d{2}-\d{2})', txt, re.I)
            if m2:
                R['invoice_date'] = m2.group(1)
                
        # Childcare
        m = re.search(r'recurring childcare payment of (?:IDR|INR|ZAR|EUR|USD)\s*([\d,\.]+)', txt, re.I)
        if m:
            R['childcare_new'] = parse_amount(m.group(1), is_idr)
            
        # Disputed charge
        if 'extra card charge is still being investigated' in txt:
            if rel and rel != 'nan':
                R['disputed_eid'] = rel

    return R

def get_salary(user_id, req_date, home_cur):
    user_ev = events_by_user.get(user_id, [])
    R = parse_msgs(user_id, home_cur)
    
    if R['stop_sal'] and R['household_remaining'] is None:
        return 0.0, None, R
        
    sal_ev = [e for e in user_ev if e.get('category') == 'salary']
    if not sal_ev:
        if R.get('sal_amt') is not None:
            return R['sal_amt'], R.get('sal_day', 15), R
        if R.get('invoice_amt') and R.get('invoice_date'):
            inv_d = safe_date(R['invoice_date'])
            if inv_d and inv_d >= req_date:
                return R['invoice_amt'], inv_d.day, R
        return 0.0, None, R
        
    regular = [e for e in sal_ev if any(k in str(e.get('description', '')).lower() for k in ['payroll', 'regular', 'salary credit'])]
    if not regular:
        regular = sal_ev
        
    past_settled = [e for e in regular if e['_sdt'] and e['_sdt'] <= req_date and e.get('status') == 'settled']
    if past_settled:
        past_settled.sort(key=lambda x: x['_sdt'])
        if 'final' in str(past_settled[-1].get('description', '')).lower() and R.get('sal_amt') is None:
            return 0.0, None, R
            
    days = [e['_sdt'].day for e in regular if e['_sdt'] is not None]
    if days:
        try:
            sal_day = stat_mode(days)
        except:
            sal_day = max(set(days), key=days.count)
    else:
        sal_day = 15
        
    future = [e for e in regular if e.get('status') == 'scheduled' and e['_sdt'] and e['_sdt'] >= req_date and e['_amt'] > 0]
    if future:
        future.sort(key=lambda e: e['_sdt'])
        sal_amt = future[0]['_amt']
    else:
        settled = [e for e in regular if e.get('status') in ('settled', 'scheduled') and e['_amt'] > 0]
        if settled:
            settled.sort(key=lambda e: e['_sdt'] or datetime.min.date())
            sal_amt = settled[-1]['_amt']
        else:
            sal_amt = 0.0
            
    if R.get('sal_amt') is not None:
        sal_amt = R['sal_amt']
    if R.get('sal_day') is not None:
        sal_day = R['sal_day']
        
    if R.get('sal_foreign') and R.get('sal_foreign_cur'):
        ref_d = safe_date(R.get('sal_foreign_date'))
        sal_amt = convert_home(R['sal_foreign'], R['sal_foreign_cur'], home_cur, ref_d)
        if R.get('sal_day') is not None:
            sal_day = R['sal_day']
            
    return sal_amt, sal_day, R

def get_streams(user_id, req_date):
    user_ev = events_by_user.get(user_id, [])
    past = [e for e in user_ev
            if e['_sdt'] and e['_sdt'] <= req_date
            and e.get('status') == 'settled'
            and e.get('direction') == 'debit']
            
    cat_ev = defaultdict(list)
    for e in past:
        cat = e.get('category', '')
        if cat in ('investment', 'windfall', 'shopping'):
            continue
        cat_ev[cat].append(e)
        
    streams = []
    for cat, evts in cat_ev.items():
        if not evts:
            continue
        evts.sort(key=lambda e: e['_sdt'])
        
        # Calculate intervals
        if len(evts) >= 2:
            diffs = []
            for i in range(1, len(evts)):
                d = (evts[i]['_sdt'] - evts[i-1]['_sdt']).days
                if d > 0:
                    diffs.append(d)
            mean_d = sum(diffs) / len(diffs) if diffs else 30
        else:
            mean_d = 30
            
        last = evts[-1]
        if last['_amt'] <= 0:
            continue
            
        # Check for bulk/outlier amounts in recurring categories
        amts = [e['_amt'] for e in evts if e['_amt'] > 0]
        med_amt = median(amts) if amts else last['_amt']
        
        # If last amount is an extreme outlier (> 2.5 * median), use median
        if len(amts) >= 3 and last['_amt'] > 2.5 * med_amt:
            stream_amt = med_amt
        else:
            stream_amt = last['_amt']
            
        s = {
            'cat': cat,
            'desc': last.get('description', ''),
            'amt': stream_amt,
            'last_date': last['_sdt'],
            'flex': last.get('flexibility', 'fixed'),
            'mina': last.get('_mina'),
            'eid': last['event_id'],
        }
        
        if mean_d >= 25 or len(evts) <= 6:
            s['type'] = 'monthly'
            s['day'] = last['_sdt'].day
        else:
            s['type'] = 'interval'
            s['interval'] = max(1, round(mean_d))
            
        streams.append(s)
        
    return streams

def simulate(user_id, req_date_str, spending_changes=None, days=90):
    req_date = safe_date(req_date_str)
    end_date = req_date + timedelta(days=days)
    
    prof = profiles[user_id]
    init_bal = safe_float(prof['current_available_balance'])
    min_bal = safe_float(prof['minimum_balance_to_keep'])
    cur = prof['home_currency']
    
    streams = get_streams(user_id, req_date)
    sal_amt, sal_day, rules = get_salary(user_id, req_date, cur)
    
    active = []
    for s in streams:
        sc = dict(s)
        if spending_changes and s['eid'] in spending_changes:
            chg = spending_changes[s['eid']]
            if chg['action'] == 'stop':
                continue
            elif chg['action'] == 'reduce_to':
                sc['amt'] = chg['new_amt']
        if sc['cat'] == 'rent' and rules.get('rent_mult', 1.0) != 1.0:
            sc['amt'] = round(sc['amt'] * rules['rent_mult'], 2)
        active.append(sc)
        
    date_range = [req_date + timedelta(days=i) for i in range(days + 1)]
    inflows = defaultdict(float)
    outflows = defaultdict(float)
    sal_dates = []
    
    user_ev = events_by_user.get(user_id, [])
    
    # 1. Pending/scheduled debits
    for e in user_ev:
        if (e['_sdt'] and e['_sdt'] >= req_date and e['_sdt'] <= end_date
            and e.get('direction') == 'debit'
            and e.get('status') in ('pending', 'scheduled')
            and e.get('category') != 'salary'
            and e['_amt'] > 0):
            if rules.get('disputed_eid') == e['event_id']:
                continue
            outflows[e['_sdt']] += e['_amt']
            
    # 2. Salary inflows
    if sal_amt and sal_amt > 0 and sal_day:
        cursor = req_date.replace(day=1)
        for _ in range(6):
            try:
                tgt = cursor.replace(day=min(sal_day, 28))
            except:
                tgt = cursor.replace(day=28)
            if tgt >= req_date and tgt <= end_date:
                inflows[tgt] += sal_amt
                sal_dates.append(tgt)
            if cursor.month == 12:
                cursor = cursor.replace(year=cursor.year+1, month=1, day=1)
            else:
                cursor = cursor.replace(month=cursor.month+1, day=1)
                
    # 2b. Invoice
    if rules.get('invoice_amt') and rules.get('invoice_date'):
        inv_d = safe_date(rules['invoice_date'])
        if inv_d and inv_d >= req_date and inv_d <= end_date:
            inflows[inv_d] += rules['invoice_amt']
            sal_dates.append(inv_d)
            
    # 3. Recurring outflows
    for s in active:
        if s['type'] == 'monthly':
            cursor = req_date.replace(day=1)
            for _ in range(6):
                try:
                    tgt = cursor.replace(day=min(s['day'], 28))
                except:
                    tgt = cursor.replace(day=28)
                if tgt >= req_date and tgt <= end_date:
                    outflows[tgt] += s['amt']
                if cursor.month == 12:
                    cursor = cursor.replace(year=cursor.year+1, month=1, day=1)
                else:
                    cursor = cursor.replace(month=cursor.month+1, day=1)
        elif s['type'] == 'interval':
            cd = s['last_date'] + timedelta(days=s['interval'])
            while cd <= end_date:
                if cd >= req_date:
                    outflows[cd] += s['amt']
                cd += timedelta(days=s['interval'])
                
    bals = []
    b = init_bal
    for d in date_range:
        b = b + inflows[d] - outflows[d]
        bals.append(b)
        
    return {
        'dates': date_range, 'bals': bals, 'min_bal': min_bal,
        'init_bal': init_bal, 'inflows': inflows, 'outflows': outflows,
        'cur': cur, 'streams': active, 'sal_amt': sal_amt,
        'sal_dates': sorted(sal_dates), 'rules': rules,
    }

def safe_pay_amount(traj, req_amount):
    """Calculates max safe payment on request_date."""
    mb = traj['min_bal']
    lowest = min(traj['bals'])
    s = max(0.0, lowest - mb)
    s = min(s, req_amount)
    return round(s, 2)

def earliest_full_date(traj, req_date, req_amount):
    """Calculates earliest date when full payment is safe."""
    mb = traj['min_bal']
    dates = traj['dates']
    bals = traj['bals']
    candidate_dates = [req_date] + sorted(traj['sal_dates'])
    
    for c_date in candidate_dates:
        if c_date < req_date:
            continue
        try:
            idx = dates.index(c_date)
        except ValueError:
            continue
            
        ok = True
        for j in range(idx, len(bals)):
            if bals[j] - req_amount < mb - 0.01:
                ok = False
                break
        if ok:
            return c_date
            
    return None

def evaluate_request(req):
    rid = req['request_id']
    uid = req['user_id']
    rdate_s = req['request_date']
    rdate = safe_date(rdate_s)
    ramt = safe_float(req['requested_amount'])
    dcomp_s = req['desired_completion_date']
    dcomp = safe_date(dcomp_s)
    partial_ok = str(req.get('allows_partial_payment', '')).strip().lower() == 'true'
    
    prof = profiles[uid]
    cur = prof['home_currency']
    mb = safe_float(prof['minimum_balance_to_keep'])
    methods = [m.strip() for m in str(prof.get('payment_methods_user_will_consider', '')).split('|') if m.strip()]
    max_inst = safe_float(prof.get('max_installment_months'), 0)
    w_reduce = [c.strip() for c in str(prof.get('expense_categories_user_is_willing_to_reduce', '')).split('|') if c.strip()]
    w_stop = [c.strip() for c in str(prof.get('expense_categories_user_is_willing_to_stop', '')).split('|') if c.strip()]
    
    traj = simulate(uid, rdate_s)
    amt_safe = safe_pay_amount(traj, ramt)
    ef = earliest_full_date(traj, rdate, ramt)
    if amt_safe >= ramt:
        ef = rdate
        
    plans = []
    
    # ── A: Full payment now ──
    if 'full_payment' in methods and amt_safe >= ramt:
        plans.append({
            'meth': 'full_payment', 'stat': 'affordable_now',
            'plan': f"{rdate_s}:{fmt_amt(ramt)}",
            'chg': 'none', 'ef': rdate, 'total': ramt,
            'start': rdate, 'npay': 1, 'optid': 0,
            'ontime': rdate <= dcomp, 'needs_chg': False,
        })
        
    # ── B: Installments ──
    opts = options_by_req.get(rid, [])
    if 'installments' in methods and max_inst > 0:
        for opt in opts:
            if opt.get('payment_method') != 'installments':
                continue
            npay = int(safe_float(opt.get('number_of_payments'), 1))
            payamt = safe_float(opt.get('payment_amount'))
            freq = int(safe_float(opt.get('payment_frequency_days'), 30))
            fp_s = opt.get('first_payment_date', '')
            total = safe_float(opt.get('total_payable_amount'))
            oid_s = str(opt.get('payment_option_id', ''))
            oid_m = re.search(r'\d+', oid_s)
            oid = int(oid_m.group()) if oid_m else 999
            
            dur_months = ((npay - 1) * freq) / 30.0
            if dur_months > max_inst + 0.5:
                continue
                
            fp = safe_date(fp_s)
            if not fp:
                continue
                
            inst_dates = [fp + timedelta(days=i * freq) for i in range(npay)]
            last_p = inst_dates[-1]
            ontime = last_p <= dcomp
            
            # Installment feasibility
            ok = True
            for p_idx, p_d in enumerate(inst_dates):
                if p_d in traj['dates']:
                    d_idx = traj['dates'].index(p_d)
                    cum = payamt * (p_idx + 1)
                    if traj['bals'][d_idx] - cum < mb - 0.01:
                        ok = False
                        break
            if ok and ontime:
                parts = [f"{d.strftime('%Y-%m-%d')}:{fmt_amt(payamt)}" for d in inst_dates]
                plans.append({
                    'meth': 'installments', 'stat': 'affordable_with_plan',
                    'plan': '|'.join(parts), 'chg': 'none',
                    'ef': ef, 'total': total, 'start': fp,
                    'npay': npay, 'optid': oid, 'ontime': True,
                    'needs_chg': False, 'ipay': payamt,
                })
                
    # ── C: Partial payment ──
    if (partial_ok and 'partial_payment' in methods
        and 0 < amt_safe < ramt and ef and ef <= dcomp):
        rem = ramt - amt_safe
        plans.append({
            'meth': 'partial_payment', 'stat': 'affordable_with_plan',
            'plan': f"{rdate_s}:{fmt_amt(amt_safe)}|{ef.strftime('%Y-%m-%d')}:{fmt_amt(rem)}",
            'chg': 'none', 'ef': ef, 'total': ramt,
            'start': rdate, 'npay': 2, 'optid': 0,
            'ontime': True, 'needs_chg': False,
        })
        
    # ── D: Spending changes ──
    if not plans:
        flex = []
        for s in traj['streams']:
            cat = s['cat']
            eid = s['eid']
            flx = s.get('flex', 'fixed')
            amt = s['amt']
            mina = s.get('mina')
            
            if cat in w_stop and flx in ('stoppable', 'reducible_or_stoppable'):
                flex.append({
                    'eid': eid, 'action': 'stop', 'savings': amt,
                    's': f"stop:{eid}", 'desc': s['desc'], 'cat': cat,
                })
            if cat in w_reduce and flx in ('reducible', 'reducible_or_stoppable') and mina is not None:
                if amt > mina:
                    flex.append({
                        'eid': eid, 'action': 'reduce_to', 'new_amt': mina,
                        'savings': amt - mina,
                        's': f"reduce_to:{eid}:{fmt_amt(mina)}", 'desc': s['desc'],
                        'cat': cat,
                    })
                    
        flex.sort(key=lambda c: -c['savings'])
        
        # Single change
        for c in flex:
            sc = {c['eid']: {'action': c['action'], 'new_amt': c.get('new_amt', 0)}}
            ct = simulate(uid, rdate_s, spending_changes=sc)
            cs = safe_pay_amount(ct, ramt)
            ce = earliest_full_date(ct, rdate, ramt)
            
            if cs >= ramt and 'full_payment' in methods:
                if c['action'] == 'stop':
                    cd = f"Stop the {c['desc'].lower()}"
                else:
                    cd = f"Reduce the {c['desc'].lower()} to {fmt_disp(c['new_amt'], cur)}"
                plans.append({
                    'meth': 'full_payment', 'stat': 'affordable_with_plan',
                    'plan': f"{rdate_s}:{fmt_amt(ramt)}",
                    'chg': c['s'], 'ef': ce or ef, 'total': ramt,
                    'start': rdate, 'npay': 1, 'optid': 0,
                    'ontime': True, 'needs_chg': True, 'cdesc': cd,
                })
                break
                
        # Double changes
        if not plans and len(flex) >= 2:
            import itertools
            for c1, c2 in itertools.combinations(flex, 2):
                if c1['eid'] == c2['eid']:
                    continue
                sc = {
                    c1['eid']: {'action': c1['action'], 'new_amt': c1.get('new_amt', 0)},
                    c2['eid']: {'action': c2['action'], 'new_amt': c2.get('new_amt', 0)},
                }
                ct = simulate(uid, rdate_s, spending_changes=sc)
                cs = safe_pay_amount(ct, ramt)
                
                if cs >= ramt and 'full_payment' in methods:
                    cstr = f"{c1['s']}|{c2['s']}"
                    d1 = f"Stop the {c1['desc'].lower()}" if c1['action'] == 'stop' else f"Reduce the {c1['desc'].lower()} to {fmt_disp(c1['new_amt'], cur)}"
                    d2 = f"stop the {c2['desc'].lower()}" if c2['action'] == 'stop' else f"reduce the {c2['desc'].lower()} to {fmt_disp(c2['new_amt'], cur)}"
                    plans.append({
                        'meth': 'full_payment', 'stat': 'affordable_with_plan',
                        'plan': f"{rdate_s}:{fmt_amt(ramt)}",
                        'chg': cstr, 'ef': ef, 'total': ramt,
                        'start': rdate, 'npay': 1, 'optid': 0,
                        'ontime': True, 'needs_chg': True,
                        'cdesc': f"{d1} and {d2}",
                    })
                    break
                    
    # ── E: Wait ──
    if not plans and ef and 'full_payment' in methods and ef <= dcomp and ef > rdate:
        plans.append({
            'meth': 'wait', 'stat': 'affordable_later',
            'plan': f"{ef.strftime('%Y-%m-%d')}:{fmt_amt(ramt)}",
            'chg': 'none', 'ef': ef, 'total': ramt,
            'start': ef, 'npay': 1, 'optid': 0,
            'ontime': True, 'needs_chg': False,
        })
        
    best = None
    if plans:
        def rank(p):
            return (
                0 if p.get('ontime') else 1,
                0 if not p.get('needs_chg') else 1,
                p.get('total', 1e18),
                p.get('start', datetime.max.date()),
                p.get('npay', 999),
                p.get('optid', 999),
            )
        plans.sort(key=rank)
        best = plans[0]
        
    if not best:
        best = {
            'meth': 'not_recommended', 'stat': 'not_affordable',
            'plan': 'none', 'chg': 'none',
            'ef': ef if (ef and ef <= dcomp) else None,
            'total': 0, 'start': None, 'npay': 0, 'optid': 0,
        }
        
    m = best['meth']
    ca = fmt_disp(ramt, cur)
    cm = fmt_disp(mb, cur)
    
    if m == 'full_payment' and best['chg'] == 'none':
        expl = f"Pay {ca} today. This leaves at least {cm} available over the next 90 days."
    elif m == 'full_payment':
        cd = best.get('cdesc', 'Adjust spending')
        expl = f"{cd}, then pay {ca} today. This leaves at least {cm} available."
    elif m == 'installments':
        ip = best.get('ipay', 0)
        ci = fmt_disp(ip, cur)
        sd = fmt_date(best['start'])
        expl = f"Use {best['npay']} installments of {ci}, starting {sd}. This leaves at least {cm} available."
    elif m == 'partial_payment':
        pp = best['plan'].split('|')
        a1 = safe_float(pp[0].split(':')[1])
        a2 = safe_float(pp[1].split(':')[1])
        expl = f"Pay {fmt_disp(a1, cur)} today and the remaining {fmt_disp(a2, cur)} on {fmt_date(best['ef'])}. This completes the full request and keeps the {cm} minimum protected."
    elif m == 'wait':
        sd = fmt_date(best['start'])
        expl = f"Pay {ca} in full on {sd}. Paying earlier would take the balance below the {cm} minimum."
    else:
        if amt_safe > 0:
            cs = fmt_disp(amt_safe, cur)
            expl = f"Do not proceed with the {ca} request. Although {cs} is available today, the full amount cannot be completed safely within 90 days."
        else:
            dd = fmt_date(dcomp)
            expl = f"Do not make this payment by {dd}. None of the available options keeps the {cm} minimum protected."
            
    ef_str = ''
    ef_val = best.get('ef')
    if ef_val:
        ef_str = ef_val.strftime('%Y-%m-%d')
        
    return {
        'request_id': rid,
        'amount_safe_to_pay': amt_safe,
        'affordability_status': best['stat'],
        'recommended_payment_method': best['meth'],
        'payment_plan': best['plan'],
        'earliest_date_for_full_payment': ef_str,
        'spending_changes_needed': best['chg'],
        'decision_explanation': expl,
    }

if __name__ == '__main__':
    print("\n=== Validating against 25 samples ===")
    correct = 0
    total = 0
    errors = []
    
    for s in sample_raw:
        total += 1
        r = evaluate_request(s)
        
        gs = s['affordability_status']
        gm = s['recommended_payment_method']
        ga = safe_float(s['amount_safe_to_pay'])
        gp = s['payment_plan']
        ge = str(s['earliest_date_for_full_payment']) if s['earliest_date_for_full_payment'] != '' else ''
        gc = s['spending_changes_needed']
        
        ps = r['affordability_status']
        pm = r['recommended_payment_method']
        pa = r['amount_safe_to_pay']
        pp = r['payment_plan']
        pe = r['earliest_date_for_full_payment']
        pc = r['spending_changes_needed']
        
        match = (ps == gs and pm == gm)
        if match:
            correct += 1
        else:
            errors.append({
                'id': s['request_id'],
                'gs': gs, 'ps': ps,
                'gm': gm, 'pm': pm,
                'gc': gc, 'pc': pc,
                'ga': ga, 'pa': pa,
                'gp': gp, 'pp': pp,
                'ge': ge, 'pe': pe,
            })
            
    print(f"Sample Accuracy: {correct}/{total} ({100*correct/total:.1f}%)")
    for e in errors:
        print(f"  {e['id']}: stat={e['gs']}->{e['ps']}, meth={e['gm']}->{e['pm']}, chg={e['gc']}->{e['pc']}")
        print(f"       plan={e['gp']} -> {e['pp']}")
        print(f"       safe={e['ga']} -> {e['pa']}, ef={e['ge']} -> {e['pe']}")
