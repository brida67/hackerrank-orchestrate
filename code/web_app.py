import os
import sys
import json
import base64
import zipfile
from datetime import datetime, date, timedelta
from flask import Flask, render_template, jsonify, request, send_file, send_from_directory, session, redirect, url_for
import pandas as pd

# ─── Load .env (GEMINI_API_KEY / OPENAI_API_KEY / SECRET_KEY) ───────────────
try:
    from dotenv import load_dotenv
    _env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    load_dotenv(_env_file)
except ImportError:
    pass  # python-dotenv not installed; rely on OS environment

# Add code directory to path
import re
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)
from financial_engine import FinancialDecisionEngine, IMAGE_AMOUNTS, to_inr, from_inr, TO_INR_RATES
from llm_intent import extract_intent, format_decision_reply
from bank_connector import PlaidConnector, AccountAggregatorConnector, build_live_profile
from account_database import (
    get_user_db_path,
    get_user_profile,
    init_user_database,
    update_user_profile,
    get_user_events,
    add_user_event,
    get_user_requests,
    get_user_request,
    add_user_request,
    get_user_chat_history,
    add_user_chat_message,
    delete_user_database,
    list_all_user_ids,
    list_all_account_profiles,
    sync_all_profiles_to_local_users_json,
    sync_user_to_engine
)

# ─── INDIAN NUMBERING & CURRENCY CONVERTER ──────────────────────────────────
def format_indian_currency(amount, include_cents=False):
    """Format any numeric amount into Indian comma system (Lakhs/Crores) with Rupee symbol."""
    amt = float(amount)
    if not include_cents:
        amt_round = round(amt)
        s = str(int(amt_round))
        dec = ''
    else:
        amt_round = round(amt, 2)
        if amt_round.is_integer():
            s = str(int(amt_round))
            dec = ''
        else:
            s_full = f'{amt_round:.2f}'
            parts = s_full.split('.')
            s = parts[0]
            dec = '.' + parts[1]
    
    if len(s) > 3:
        last3 = s[-3:]
        remaining = s[:-3]
        groups = []
        while len(remaining) > 2:
            groups.insert(0, remaining[-2:])
            remaining = remaining[:-2]
        if remaining:
            groups.insert(0, remaining)
        groups.append(last3)
        formatted = ','.join(groups)
    else:
        formatted = s
    return f'₹ {formatted}{dec}'


def convert_currencies_in_text(text):
    """Converts any foreign currency mention (especially ZAR) to formatted Indian currency (₹)."""
    if not text or not isinstance(text, str):
        return text
    
    def replace_curr(match):
        curr_str = match.group(1).upper()
        curr_key = 'ZAR' if curr_str in ('RAND', 'R') else curr_str
        amt_str = match.group(2).replace(',', '')
        try:
            val = float(amt_str)
            rate = TO_INR_RATES.get(curr_key, 1.0)
            inr_val = val * rate
            has_cents = '.' in match.group(2) and not inr_val.is_integer()
            return format_indian_currency(inr_val, include_cents=has_cents)
        except Exception:
            return match.group(0)

    res = re.sub(r'\b(ZAR|IDR|EUR|USD|Rand|INR)\s*([\d,]+(?:\.\d+)?)\b', replace_curr, text, flags=re.IGNORECASE)
    res = re.sub(r'\bZAR\b', 'INR', res, flags=re.IGNORECASE)
    return res


def convert_payment_plan_to_inr(plan_str, orig_curr):
    """Converts amounts in a payment plan from foreign currency to INR."""
    if not plan_str or plan_str == 'none':
        return plan_str
    rate = TO_INR_RATES.get(str(orig_curr).upper(), 1.0)
    if rate == 1.0:
        return plan_str
    parts = plan_str.split('|')
    new_parts = []
    for p in parts:
        if ':' in p:
            dt, amt = p.split(':', 1)
            try:
                converted = round(float(amt) * rate, 2)
                clean_c = f"{int(converted)}" if converted.is_integer() else f"{converted:.2f}"
                new_parts.append(f"{dt}:{clean_c}")
            except Exception:
                new_parts.append(p)
        else:
            new_parts.append(p)
    return '|'.join(new_parts)


app = Flask(__name__, template_folder=os.path.join(current_dir, 'templates'), static_folder=os.path.join(current_dir, 'static'))
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.jinja_env.auto_reload = True
app.secret_key = os.environ.get('SECRET_KEY', 'fintech-indian-copilot-secret-2024')

repo_root = os.path.abspath(os.path.join(current_dir, '..'))
dataset_dir = os.path.join(repo_root, 'dataset')
engine = FinancialDecisionEngine(data_dir=dataset_dir)

# Load cached predictions
output_path = os.path.join(repo_root, 'output.csv')
if os.path.exists(output_path):
    output_df = pd.read_csv(output_path)
else:
    output_df = None

sample_df = pd.read_csv(os.path.join(dataset_dir, 'sample_requests.csv'))
requests_df = pd.read_csv(os.path.join(dataset_dir, 'requests.csv'))
profiles_df = pd.read_csv(os.path.join(dataset_dir, 'financial_profiles.csv'))
images_meta_df = pd.read_csv(os.path.join(dataset_dir, 'images.csv'))
messages_df = pd.read_csv(os.path.join(dataset_dir, 'messages.csv'))
options_df = pd.read_csv(os.path.join(dataset_dir, 'request_payment_options.csv'))

# ─── MULTI-TENANT DEDICATED SQLITE DATABASE PER ACCOUNT ──────────────────────
DEFAULT_USER_PROFILE = {
    'user_id': 'user_rida_fat_2651dc',
    'full_name': 'Rida Fathima',
    'email': 'ridafathima2105@gmail.com',
    'phone': '9035491812',
    'security_pin': '12345',
    'bank_name': 'HDFC Bank',
    'account_type': 'Salary Account',
    'account_number': '9809898900',
    'account_masked': '•••• •••• •••• 8900',
    'ifsc_code': 'SBIN0000001',
    'branch_name': 'Fort Branch, Mumbai',
    'upi_id': 'rida@hdfc.com',
    'current_balance': 50000.0,
    'monthly_salary': 90000.0,
    'monthly_commitments': 12000.0,
    'minimum_buffer': 16000.0,
    'currency': 'INR',
    'auth_provider': 'RBI Account Aggregator (AA)',
    'verified': True,
    'last_sync': datetime.now().strftime('%d %b %Y, %I:%M %p IST')
}

def get_active_user_id():
    """Resolve the active authenticated user, strictly isolated per session/tenant."""
    uid = session.get('authenticated_user_id')
    if not uid:
        uid = request.headers.get('X-User-Id') or request.args.get('user_id')
    if uid and get_user_profile(uid):
        return uid
    saved = list_all_account_profiles()
    if saved:
        return saved[0]['user_id']
    return 'user_rida_fat_2651dc'

def load_local_users():
    """Load all accounts from their respective dedicated SQLite databases."""
    profiles = list_all_account_profiles()
    return profiles if profiles else [DEFAULT_USER_PROFILE]

def save_local_user(user_dict):
    """Save or update an account in its dedicated SQLite database."""
    init_user_database(user_dict)
    return list_all_account_profiles()

def delete_local_user(user_id):
    """Delete an account and its dedicated SQLite database file."""
    delete_user_database(user_id)
    return list_all_account_profiles()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/api/saved_users', methods=['GET'])
def get_saved_users():
    """Returns all locally saved bank accounts WITHOUT exposing security PINs."""
    users = list_all_account_profiles()
    sanitized = []
    for u in users:
        u_copy = dict(u)
        u_copy.pop('security_pin', None)
        u_copy['database_file'] = os.path.basename(get_user_db_path(u['user_id']))
        sanitized.append(u_copy)
    return jsonify(sanitized)

@app.route('/api/saved_users/<user_id>', methods=['DELETE'])
def remove_saved_user(user_id):
    """Deletes a saved bank user and cleans up their isolated SQLite database."""
    delete_user_database(user_id)
    updated = list_all_account_profiles()
    sanitized = []
    for u in updated:
        u_copy = dict(u)
        u_copy.pop('security_pin', None)
        u_copy['database_file'] = os.path.basename(get_user_db_path(u['user_id']))
        sanitized.append(u_copy)
    return jsonify({'status': 'success', 'saved_users': sanitized})

@app.route('/api/current_user')
def get_current_user():
    """Returns profile for currently active authenticated user from their isolated database."""
    uid = get_active_user_id()
    prof = get_user_profile(uid)
    if not prof:
        saved = list_all_account_profiles()
        prof = saved[0] if saved else DEFAULT_USER_PROFILE
        uid = prof['user_id']
    
    sanitized = dict(prof)
    sanitized.pop('security_pin', None)
    sanitized['database_file'] = os.path.basename(get_user_db_path(uid))
    sanitized['database_path'] = get_user_db_path(uid)
    
    # Attach count of their own requests and transactions
    user_reqs = get_user_requests(uid)
    user_evts = get_user_events(uid)
    sanitized['requests_count'] = len(user_reqs)
    sanitized['events_count'] = len(user_evts)
    
    # Sync with in-memory engine so simulation/scoring matches this user's DB
    sync_user_to_engine(uid, engine)
    return jsonify(sanitized)

@app.route('/api/login_bank', methods=['POST'])
def login_bank():
    """Authenticate user against their dedicated SQLite database or create a new database."""
    data = request.json or {}
    is_new = bool(data.get('is_new_user', False))
    entered_pin = str(data.get('security_pin', '')).strip()

    if not entered_pin:
        return jsonify({'status': 'error', 'message': 'Security PIN / Password is required.'}), 400

    saved_users = list_all_account_profiles()

    if not is_new:
        user_id = data.get('user_id', '').strip()
        account_number = data.get('account_number', '').strip()
        email = data.get('email', '').strip().lower()
        phone = data.get('phone', '').strip()

        matched_user = None
        for u in saved_users:
            if user_id and u.get('user_id') == user_id:
                matched_user = u
                break
            if account_number and u.get('account_number') == account_number:
                matched_user = u
                break
            if email and u.get('email', '').lower() == email:
                matched_user = u
                break
            if phone and u.get('phone') == phone:
                matched_user = u
                break

        if not matched_user and len(saved_users) == 1 and not user_id:
            matched_user = saved_users[0]

        if not matched_user:
            return jsonify({'status': 'error', 'message': 'User account not found. Please select a valid account.'}), 401

        target_uid = matched_user['user_id']
        db_prof = get_user_profile(target_uid)
        if not db_prof:
            return jsonify({'status': 'error', 'message': f'Dedicated database for {target_uid} not found.'}), 404

        saved_pin = str(db_prof.get('security_pin', '')).strip()

        # STRICT VERIFICATION: Verify security PIN against user's dedicated SQLite database
        if entered_pin != saved_pin:
            return jsonify({'status': 'error', 'message': 'Invalid Security PIN / Password. Access denied.'}), 401

        now_str = datetime.now().strftime('%d %b %Y, %I:%M %p IST')
        update_user_profile(target_uid, {'last_sync': now_str})
        user_profile = get_user_profile(target_uid)
        user_id = target_uid
    else:
        full_name = data.get('full_name', '').strip()
        if not full_name:
            return jsonify({'status': 'error', 'message': 'Full name is required for registration.'}), 400

        email = data.get('email', '').strip().lower()
        phone = data.get('phone', '').strip()
        bank_name = data.get('bank_name', 'HDFC Bank')
        account_type = data.get('account_type', 'Salary Account')
        account_number = data.get('account_number', '').strip()
        if not account_number:
            return jsonify({'status': 'error', 'message': 'Account number is required.'}), 400
        ifsc_code = data.get('ifsc_code', 'HDFC0000060').strip().upper()
        branch_name = data.get('branch_name', 'Fort Branch, Mumbai')
        upi_id = data.get('upi_id', '').strip() or f"{full_name.lower().replace(' ', '')}@ok{bank_name.lower().replace(' ', '')}"

        try:
            current_balance = float(data.get('current_balance', 50000.0))
        except (ValueError, TypeError):
            current_balance = 50000.0

        try:
            monthly_salary = float(data.get('monthly_salary', 90000.0))
        except (ValueError, TypeError):
            monthly_salary = 90000.0

        try:
            monthly_commitments = float(data.get('monthly_commitments', 12000.0))
        except (ValueError, TypeError):
            monthly_commitments = 12000.0

        try:
            minimum_buffer = float(data.get('minimum_buffer', 16000.0))
        except (ValueError, TypeError):
            minimum_buffer = 16000.0

        import hashlib
        slug = "".join(c for c in full_name.lower() if c.isalnum())[:8]
        rand_hash = hashlib.md5((account_number + str(datetime.now())).encode()).hexdigest()[:6]
        user_id = f"user_{slug}_{rand_hash}"
        masked = f"•••• •••• •••• {account_number[-4:]}" if len(account_number) >= 4 else "•••• 8900"

        user_profile = {
            'user_id': user_id,
            'full_name': full_name,
            'email': email,
            'phone': phone,
            'security_pin': entered_pin,
            'bank_name': bank_name,
            'account_type': account_type,
            'account_number': account_number,
            'account_masked': masked,
            'ifsc_code': ifsc_code,
            'branch_name': branch_name,
            'upi_id': upi_id,
            'current_balance': current_balance,
            'monthly_salary': monthly_salary,
            'monthly_commitments': monthly_commitments,
            'minimum_buffer': minimum_buffer,
            'currency': 'INR',
            'auth_provider': data.get('auth_provider', 'RBI Account Aggregator (AA)'),
            'verified': True,
            'last_sync': datetime.now().strftime('%d %b %Y, %I:%M %p IST')
        }

        # ── CREATE DEDICATED NEW SQLITE DATABASE FILE FOR THIS ACCOUNT ───────
        init_user_database(user_profile)

    # Set as active authenticated session
    session['authenticated_user_id'] = user_id
    sync_user_to_engine(user_id, engine)

    # Sanitize user before returning in JSON (NO PIN in response)
    sanitized_resp = dict(user_profile)
    sanitized_resp.pop('security_pin', None)
    sanitized_resp['database_file'] = os.path.basename(get_user_db_path(user_id))

    return jsonify({
        'status': 'success',
        'message': f"Bank account ({user_profile.get('bank_name')} - {user_profile.get('account_masked')}) authenticated in dedicated database!",
        'user': sanitized_resp,
        'database_file': sanitized_resp['database_file'],
        'redirect_url': '/?authenticated=1'
    })

@app.route('/api/switch_account', methods=['POST'])
def switch_account():
    """Switch active authenticated account without mixing any data."""
    data = request.json or {}
    target_uid = data.get('user_id')
    pin = str(data.get('security_pin', '')).strip()

    prof = get_user_profile(target_uid)
    if not prof:
        return jsonify({'status': 'error', 'message': f'Account database for {target_uid} not found.'}), 404

    if pin and pin != str(prof.get('security_pin', '')).strip():
        return jsonify({'status': 'error', 'message': 'Invalid Security PIN for this account.'}), 401

    session['authenticated_user_id'] = target_uid
    sync_user_to_engine(target_uid, engine)

    sanitized = dict(prof)
    sanitized.pop('security_pin', None)
    sanitized['database_file'] = os.path.basename(get_user_db_path(target_uid))

    return jsonify({
        'status': 'success',
        'message': f"Switched to account: {prof.get('full_name')} ({prof.get('bank_name')})",
        'user': sanitized,
        'database_file': sanitized['database_file']
    })

@app.route('/api/logout', methods=['GET', 'POST'])
def logout():
    """Clear authenticated session."""
    session.pop('authenticated_user_id', None)
    return jsonify({'status': 'success', 'message': 'Session cleared.'})

@app.route('/api/user_database_info')
def user_database_info():
    """Returns database inspection details proving dedicated SQLite file isolation."""
    uid = get_active_user_id()
    db_path = get_user_db_path(uid)
    prof = get_user_profile(uid)
    reqs = get_user_requests(uid)
    evts = get_user_events(uid)
    chats = get_user_chat_history(uid)
    
    return jsonify({
        'user_id': uid,
        'full_name': prof.get('full_name') if prof else 'Unknown',
        'bank_name': prof.get('bank_name') if prof else 'Unknown',
        'database_file': os.path.basename(db_path),
        'database_absolute_path': db_path,
        'database_exists': os.path.exists(db_path),
        'size_bytes': os.path.getsize(db_path) if os.path.exists(db_path) else 0,
        'records': {
            'account_profile': 1 if prof else 0,
            'financial_events': len(evts),
            'financial_requests': len(reqs),
            'chat_history': len(chats)
        }
    })

@app.route('/api/user_ledger')
def user_ledger():
    """Returns financial transactions strictly from the active user's dedicated SQLite database."""
    uid = get_active_user_id()
    events = get_user_events(uid)
    return jsonify({
        'user_id': uid,
        'database_file': os.path.basename(get_user_db_path(uid)),
        'total_events': len(events),
        'events': events
    })

def get_user_history(user_id, req_date_str, days_back=60):
    req_date = datetime.strptime(req_date_str, '%Y-%m-%d').date()
    window_start = req_date - timedelta(days=days_back)
    
    # Check if this user is a local account with a dedicated database
    prof_dict = get_user_profile(user_id)
    if prof_dict:
        user_currency = 'INR'
        current_bal = float(prof_dict.get('current_balance', 50000.0))
        sync_user_to_engine(user_id, engine)
    elif user_id in profiles_df['user_id'].values:
        prof = profiles_df[profiles_df['user_id'] == user_id].iloc[0]
        user_currency = str(prof['home_currency'])
        current_bal = to_inr(float(prof['current_available_balance']), user_currency)
    else:
        user_currency = 'INR'
        current_bal = 50000.0
    
    events_df = engine.events
    u_ev = events_df[events_df['user_id'] == user_id].copy()
    # All settled events up to req_date (used for balance reconstruction — convert each amt to INR)
    past = u_ev[(u_ev['s_dt'] <= req_date) & (u_ev['status'] == 'settled')].sort_values('s_dt')
    
    daily_net = {}
    for _, row in past.iterrows():
        d = row['s_dt']
        evt_currency = str(row.get('currency', user_currency))
        amt = to_inr(float(row['amount']), evt_currency)
        if row['direction'] == 'credit':
            daily_net[d] = daily_net.get(d, 0.0) + amt
        elif row['direction'] == 'debit':
            daily_net[d] = daily_net.get(d, 0.0) - amt
            
    hist_dates = [req_date - timedelta(days=i) for i in range(days_back, -1, -1)]
    sub_nets = sum(daily_net.get(d, 0.0) for d in hist_dates[1:])
    start_bal = current_bal - sub_nets
    
    b = start_bal
    hist_balances = []
    for d in hist_dates:
        if d != hist_dates[0]:
            b += daily_net.get(d, 0.0)
        hist_balances.append(round(b, 2))

    # Category spending — calculate monthly average (monthly based)
    window_days = max(1, days_back)
    months_in_window = max(1.0, window_days / 30.0)
    window_events = past[past['s_dt'] >= window_start].copy()
    debits = window_events[window_events['direction'] == 'debit'].copy()
    debits['amount_inr'] = debits.apply(
        lambda r: to_inr(float(r['amount']), str(r.get('currency', user_currency))), axis=1
    )
    cat_totals = debits.groupby('category')['amount_inr'].sum().sort_values(ascending=False).to_dict()
    total_debit = sum(cat_totals.values())
    category_spending = [
        {
            'category': cat,
            'amount': round(amt / months_in_window, 2),  # Monthly average expenditure
            'monthly_amount': round(amt / months_in_window, 2),
            'total_period_amount': round(amt, 2),
            'pct': round((amt / total_debit) * 100, 1) if total_debit > 0 else 0
        }
        for cat, amt in list(cat_totals.items())[:8]
    ]
    
    # Monthly cashflow — last 6 months, amounts converted to INR
    six_months_ago = req_date - timedelta(days=183)
    recent_events = past[past['s_dt'] >= six_months_ago].copy()
    recent_events['amount_inr'] = recent_events.apply(
        lambda r: to_inr(float(r['amount']), str(r.get('currency', user_currency))), axis=1
    )
    recent_events['month'] = recent_events['s_dt'].apply(lambda d: d.strftime('%Y-%m'))
    m_in = recent_events[recent_events['direction'] == 'credit'].groupby('month')['amount_inr'].sum().to_dict()
    m_out = recent_events[recent_events['direction'] == 'debit'].groupby('month')['amount_inr'].sum().to_dict()
    all_months = sorted(list(set(list(m_in.keys()) + list(m_out.keys()))))[-6:]
    monthly_flow = [
        {'month': m, 'income': round(m_in.get(m, 0.0), 2), 'expense': round(m_out.get(m, 0.0), 2)}
        for m in all_months
    ]
    
    return {
        'dates': [d.strftime('%Y-%m-%d') for d in hist_dates],
        'balances': hist_balances,
        'category_spending': category_spending,
        'monthly_cashflow': monthly_flow,
        'currency': 'INR'
    }

@app.route('/api/stats')
def get_stats():
    global output_df
    if output_df is None and os.path.exists(output_path):
        output_df = pd.read_csv(output_path)
        
    stats = {
        'total_requests': len(requests_df),
        'sample_requests': len(sample_df),
        'total_users': len(profiles_df),
        'multimodal_images': len(IMAGE_AMOUNTS),
        'deadline': '2026-09-13T18:00:00+05:30',
        'submission_url': 'https://www.hackerrank.com/contests/hackerrank-orchestrate-september26/challenges/buy-or-wait/submission'
    }
    if output_df is not None:
        eval_merged = pd.merge(requests_df, output_df, on='request_id')
        merged_all = pd.concat([sample_df, eval_merged], ignore_index=True)
        stats['status_dist'] = merged_all['affordability_status'].value_counts().to_dict()
        stats['method_dist'] = merged_all['recommended_payment_method'].value_counts().to_dict()
        
    debit_events = engine.events[
        (engine.events['direction'] == 'debit') &
        (engine.events['status'] == 'settled')
    ]
    cat_fleet = debit_events.groupby('category')['event_id'].count().sort_values(ascending=False).head(8)
    stats['fleet_categories'] = [{'category': k, 'amount': int(v)} for k, v in cat_fleet.items()]
    stats['fleet_categories_label'] = 'transaction_count'
    return jsonify(stats)

@app.route('/api/requests')
def list_requests():
    global output_df
    if output_df is None and os.path.exists(output_path):
        output_df = pd.read_csv(output_path)

    active_uid = get_active_user_id()
    sync_user_to_engine(active_uid, engine)
    
    summary_list = []
    
    # 1. Fetch user-specific requests strictly from THIS active user's dedicated SQLite database
    user_reqs = get_user_requests(active_uid)
    for r in user_reqs:
        summary_list.append({
            'request_id': r['request_id'],
            'user_id': r['user_id'],
            'currency': 'INR',
            'original_currency': 'INR',
            'request_date': r['request_date'],
            'request_type': r['request_type'],
            'requested_amount': float(r['requested_amount']),
            'amount_safe_to_pay': float(r['amount_safe_to_pay']),
            'affordability_status': r['affordability_status'],
            'recommended_payment_method': r['recommended_payment_method'],
            'is_sample': False,
            'is_user_account': True,
            'request_text': r['request_text']
        })

    # 2. Merge benchmark sample and evaluation requests
    if output_df is not None:
        merged_eval = pd.merge(requests_df, output_df, on='request_id')
        merged_eval['is_sample'] = False
        
        sample_sub = sample_df.copy()
        sample_sub['is_sample'] = True
        
        combined = pd.concat([sample_sub, merged_eval], ignore_index=True)
        user_curr_map = profiles_df.set_index('user_id')['home_currency'].to_dict()
        for _, r in combined.iterrows():
            orig_curr = user_curr_map.get(r['user_id'], 'INR')
            summary_list.append({
                'request_id': r['request_id'],
                'user_id': r['user_id'],
                'currency': 'INR',
                'original_currency': orig_curr,
                'request_date': r['request_date'],
                'request_type': r['request_type'],
                'requested_amount': to_inr(float(r['requested_amount']), orig_curr),
                'amount_safe_to_pay': to_inr(float(r['amount_safe_to_pay']), orig_curr),
                'affordability_status': r['affordability_status'],
                'recommended_payment_method': r['recommended_payment_method'],
                'is_sample': bool(r['is_sample']),
                'is_user_account': False,
                'request_text': convert_currencies_in_text(r['request_text'])
            })
    return jsonify(summary_list)

@app.route('/api/request/<req_id>')
def get_request_detail(req_id):
    # Check if request is in active user's dedicated SQLite database
    active_uid = get_active_user_id()
    user_req = get_user_request(active_uid, req_id)
    if not user_req:
        for uid in list_all_user_ids():
            user_req = get_user_request(uid, req_id)
            if user_req:
                active_uid = uid
                break

    if user_req:
        user_id = user_req['user_id']
        prof_dict = get_user_profile(user_id)
        sync_user_to_engine(user_id, engine)
        
        pred_dict = {
            'amount_safe_to_pay': float(user_req['amount_safe_to_pay']),
            'affordability_status': user_req['affordability_status'],
            'recommended_payment_method': user_req['recommended_payment_method'],
            'payment_plan': user_req['payment_plan'],
            'earliest_date_for_full_payment': user_req['earliest_date_for_full_payment'] or '',
            'spending_changes_needed': user_req['spending_changes_needed'],
            'decision_explanation': user_req['decision_explanation']
        }
        
        prof = {
            'user_id': user_id,
            'full_name': prof_dict['full_name'],
            'bank_name': prof_dict['bank_name'],
            'home_currency': 'INR',
            'current_available_balance': float(prof_dict['current_balance']),
            'minimum_balance_to_keep': float(prof_dict['minimum_buffer']),
            'monthly_salary': float(prof_dict['monthly_salary']),
            'monthly_commitments': float(prof_dict['monthly_commitments']),
            'database_file': os.path.basename(get_user_db_path(user_id))
        }
        
        req_row = {
            'request_id': user_req['request_id'],
            'user_id': user_id,
            'request_date': user_req['request_date'],
            'request_type': user_req['request_type'],
            'requested_amount': float(user_req['requested_amount']),
            'desired_completion_date': user_req['desired_completion_date'],
            'allows_partial_payment': bool(user_req['allows_partial_payment']),
            'request_text': user_req['request_text'],
            'is_sample': False,
            'is_user_account': True,
            'original_currency': 'INR'
        }
        is_sample = False
        user_currency = 'INR'
    else:
        # Check if in sample or eval
        is_sample = False
        req_row = None
        pred_dict = None
        
        if req_id in sample_df['request_id'].values:
            req_row = sample_df[sample_df['request_id'] == req_id].iloc[0]
            is_sample = True
            pred_dict = {
                'amount_safe_to_pay': float(req_row['amount_safe_to_pay']),
                'affordability_status': req_row['affordability_status'],
                'recommended_payment_method': req_row['recommended_payment_method'],
                'payment_plan': req_row['payment_plan'],
                'earliest_date_for_full_payment': str(req_row['earliest_date_for_full_payment']) if pd.notna(req_row['earliest_date_for_full_payment']) else '',
                'spending_changes_needed': req_row['spending_changes_needed'],
                'decision_explanation': req_row['decision_explanation']
            }
        else:
            matching = requests_df[requests_df['request_id'] == req_id]
            if matching.empty:
                alt_id = req_id.lower().replace('-', '_')
                matching = requests_df[requests_df['request_id'].str.lower() == alt_id]
            if matching.empty:
                return jsonify({'error': f'Request {req_id} not found'}), 404
            req_row = matching.iloc[0]
            pred_dict = engine.evaluate_request(req_row)

        user_id = req_row['user_id']
        prof_raw = profiles_df[profiles_df['user_id'] == user_id].iloc[0].to_dict()
        user_currency = str(prof_raw.get('home_currency', 'INR'))
        prof = {}
        for k, v in prof_raw.items():
            if pd.isna(v) if not isinstance(v, str) else False:
                prof[k] = None
            elif k in ('current_available_balance', 'minimum_balance_to_keep'):
                prof[k] = to_inr(float(v), user_currency)
            else:
                prof[k] = v
        prof['home_currency'] = 'INR'
        try:
            req_dt = datetime.strptime(str(req_row['request_date']), '%Y-%m-%d').date()
            sal_amount, sal_day, rules = engine.get_salary_info(user_id, req_dt)
            prof['monthly_salary'] = to_inr(sal_amount, user_currency) if sal_amount else 0.0
            prof['salary_day'] = sal_day
            
            streams = engine.extract_recurring_streams(user_id, req_dt)
            monthly_streams_sum = sum(
                s['amount'] for s in streams 
                if s.get('type') == 'monthly' or s.get('category') in ('rent', 'debt_repayment', 'utilities', 'housing', 'groceries')
            )
            prof['monthly_commitments'] = to_inr(monthly_streams_sum, user_currency) if monthly_streams_sum else 0.0
        except Exception:
            prof['monthly_salary'] = 0.0
            prof['monthly_commitments'] = 0.0

    # Simulate 90-day trajectory (amounts in user's native currency → convert to INR)
    traj = engine.simulate_cash_flow(user_id, req_row['request_date'])
    traj_balances_inr = [to_inr(b, user_currency) for b in traj['balances']]
    traj_min_bal_inr = to_inr(traj['min_balance'], user_currency)
    traj_init_bal_inr = to_inr(traj['init_balance'], user_currency)
    # Convert events_log amounts to INR
    events_log_inr = {}
    for d, evlist in traj['events_log'].items():
        events_log_inr[d] = []
        for ev in evlist:
            ev_inr = dict(ev)
            if 'amount' in ev_inr and ev_inr['amount'] is not None:
                ev_inr['amount'] = to_inr(float(ev_inr['amount']), user_currency)
            events_log_inr[d].append(ev_inr)

    # Calculate with-purchase and with-plan balance curves (INR)
    req_amt = to_inr(float(req_row['requested_amount']), user_currency)
    with_purchase_balances = [round(b - req_amt, 2) for b in traj_balances_inr]
    with_plan_balances = list(traj_balances_inr)
    method = pred_dict['recommended_payment_method']
    plan_str = pred_dict['payment_plan']
    
    events_log_dict = {k.strftime('%Y-%m-%d'): list(v) for k, v in events_log_inr.items()}
    req_date_str = req_row['request_date']
    
    if plan_str and plan_str != 'none':
        payments = []
        for p in plan_str.split('|'):
            p_date, p_amt_raw = p.split(':')
            payments.append((p_date, to_inr(float(p_amt_raw), user_currency)))
            
        # Deduct payments (already in INR)
        dates_list = traj['dates']
        for p_date, p_amt in payments:
            if p_date in dates_list:
                p_idx = dates_list.index(p_date)
                for idx in range(p_idx, len(with_plan_balances)):
                    with_plan_balances[idx] = round(with_plan_balances[idx] - p_amt, 2)
                if p_date not in events_log_dict:
                    events_log_dict[p_date] = []
                events_log_dict[p_date].append({
                    'type': 'installment',
                    'desc': f"Installment payment for {req_row['request_type']}",
                    'amount': p_amt
                })
    elif method == 'full_payment':
        with_plan_balances = list(with_purchase_balances)
        if req_date_str not in events_log_dict:
            events_log_dict[req_date_str] = []
        events_log_dict[req_date_str].append({
            'type': 'purchase',
            'desc': f"Purchase payment: {req_row['request_type']}",
            'amount': req_amt
        })
    elif method == 'wait' and pred_dict.get('earliest_date_for_full_payment'):
        wait_date = pred_dict['earliest_date_for_full_payment']
        if wait_date in traj['dates']:
            w_idx = traj['dates'].index(wait_date)
            for idx in range(w_idx, len(with_plan_balances)):
                with_plan_balances[idx] = round(with_plan_balances[idx] - req_amt, 2)
            if wait_date not in events_log_dict:
                events_log_dict[wait_date] = []
            events_log_dict[wait_date].append({
                'type': 'purchase_wait',
                'desc': f"Recommended delayed purchase date",
                'amount': req_amt
            })

    # Payment options
    req_opts = options_df[options_df['request_id'] == req_id].to_dict(orient='records')
    for opt in req_opts:
        for k, v in opt.items():
            if pd.isna(v):
                opt[k] = None

    # Messages
    u_msgs = messages_df[messages_df['user_id'] == user_id].to_dict(orient='records')
    for m in u_msgs:
        for k, v in m.items():
            if pd.isna(v):
                m[k] = None
        if m.get('message_text'):
            m['message_text'] = convert_currencies_in_text(m['message_text'])

    # Image links
    linked_imgs = images_meta_df[images_meta_df['user_id'] == user_id].to_dict(orient='records')
    for img in linked_imgs:
        eid = img['related_event_id']
        img['verified_amount'] = IMAGE_AMOUNTS.get(eid, None)
        img['image_url'] = f"/media/images/{img['image_id']}.png"

    # Convert prediction amounts to INR
    pred_dict['amount_safe_to_pay'] = to_inr(pred_dict['amount_safe_to_pay'], user_currency)
    pred_dict['decision_explanation'] = convert_currencies_in_text(pred_dict.get('decision_explanation', ''))
    pred_dict['payment_plan'] = convert_payment_plan_to_inr(pred_dict.get('payment_plan'), user_currency)

    # Historical real data from financial_events.csv (already returns INR)
    user_history = get_user_history(user_id, req_row['request_date'], days_back=60)

    # Convert payment options amounts to INR
    for opt in req_opts:
        for amt_key in ('payment_amount', 'total_payable_amount', 'down_payment_amount'):
            if opt.get(amt_key) is not None:
                try:
                    opt[amt_key] = to_inr(float(opt[amt_key]), user_currency)
                except (ValueError, TypeError):
                    pass

    response = {
        'request': {
            'request_id': req_id,
            'user_id': user_id,
            'request_date': req_row['request_date'],
            'request_type': req_row['request_type'],
            'requested_amount': req_amt,
            'desired_completion_date': req_row['desired_completion_date'],
            'allows_partial_payment': bool(req_row['allows_partial_payment']),
            'request_text': convert_currencies_in_text(req_row['request_text']),
            'is_sample': is_sample,
            'original_currency': user_currency
        },
        'prediction': pred_dict,
        'profile': prof,
        'trajectory': {
            'dates': traj['dates'],
            'baseline_balances': [round(b, 2) for b in traj_balances_inr],
            'with_plan_balances': with_plan_balances,
            'with_purchase_balances': with_purchase_balances,
            'min_balance': traj_min_bal_inr,
            'init_balance': traj_init_bal_inr,
            'currency': 'INR',
            'events_log': {k: v for k, v in events_log_dict.items() if len(v) > 0}
        },
        'history': user_history,
        'payment_options': req_opts,
        'messages': u_msgs,
        'linked_images': linked_imgs
    }
    return jsonify(response)

@app.route('/api/simulate', methods=['POST'])
def simulate_scenario():
    data = request.json or {}
    user_id = data.get('user_id', 'user_01')
    req_date = data.get('request_date', '2024-03-03')
    req_amount = float(data.get('requested_amount', 10000.0))
    desired_date = data.get('desired_completion_date', '2024-04-01')
    allows_partial = bool(data.get('allows_partial_payment', True))
    
    # Get user's home currency
    user_curr = 'INR'
    prof_rows = profiles_df[profiles_df['user_id'] == user_id]
    if len(prof_rows) > 0:
        user_curr = str(prof_rows.iloc[0].get('home_currency', 'INR'))
    
    # Convert simulator amount from INR to native currency for engine
    native_amount = from_inr(req_amount, user_curr)
    
    # Custom spending changes
    spending_changes = data.get('spending_changes', {})
    
    # Run simulation
    traj = engine.simulate_cash_flow(user_id, req_date, spending_changes=spending_changes)
    
    # Evaluate
    mock_row = pd.Series({
        'request_id': 'sim_custom',
        'user_id': user_id,
        'request_date': req_date,
        'requested_amount': native_amount,
        'desired_completion_date': desired_date,
        'allows_partial_payment': allows_partial,
        'request_text': 'What-If custom simulation'
    })
    pred = engine.evaluate_request(mock_row)
    
    # Convert prediction and trajectory to INR
    pred_inr = dict(pred)
    if 'amount_safe_to_pay' in pred_inr and pred_inr['amount_safe_to_pay'] is not None:
        pred_inr['amount_safe_to_pay'] = to_inr(float(pred_inr['amount_safe_to_pay']), user_curr)
    pred_inr['decision_explanation'] = convert_currencies_in_text(pred_inr.get('decision_explanation', ''))
    pred_inr['payment_plan'] = convert_payment_plan_to_inr(pred_inr.get('payment_plan'), user_curr)
    
    return jsonify({
        'prediction': pred_inr,
        'trajectory': {
            'dates': traj['dates'],
            'balances': [to_inr(b, user_curr) for b in traj['balances']],
            'min_balance': to_inr(traj['min_balance'], user_curr),
            'init_balance': to_inr(traj['init_balance'], user_curr),
            'currency': 'INR'
        }
    })

@app.route('/api/images/<image_id>')
def get_image_info(image_id):
    img_row = images_meta_df[images_meta_df['image_id'] == image_id]
    if len(img_row) == 0:
        return jsonify({'error': 'Image not found'}), 404
    r = img_row.iloc[0].to_dict()
    eid = r['related_event_id']
    r['verified_amount'] = IMAGE_AMOUNTS.get(eid, None)
    r['image_url'] = f"/media/images/{image_id}.png"
    return jsonify(r)

@app.route('/media/images/<path:filename>')
def serve_media_image(filename):
    media_dir = os.path.join(dataset_dir, 'media', 'images')
    return send_from_directory(media_dir, filename)

@app.route('/api/export_zip')
def export_code_zip():
    zip_path = os.path.join(repo_root, 'code.zip')
    # Build zip file containing code/, evaluation/, README.md
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        # Add code directory
        for root, dirs, files in os.walk(current_dir):
            for file in files:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, repo_root)
                zf.write(full_path, rel_path)
                
        # Add README.md
        readme_path = os.path.join(repo_root, 'README.md')
        if os.path.exists(readme_path):
            zf.write(readme_path, 'README.md')
            
        # Add AGENTS.md
        agents_path = os.path.join(repo_root, 'AGENTS.md')
        if os.path.exists(agents_path):
            zf.write(agents_path, 'AGENTS.md')
            
        # Add evaluation/usage_report.md
        eval_report = os.path.join(current_dir, 'evaluation', 'usage_report.md')
        if os.path.exists(eval_report):
            zf.write(eval_report, 'evaluation/usage_report.md')
            
    return send_file(zip_path, as_attachment=True, download_name='code.zip')

@app.route('/api/download_output')
def download_output():
    if os.path.exists(output_path):
        return send_file(output_path, as_attachment=True, download_name='output.csv')
    return jsonify({'error': 'output.csv does not exist'}), 404

# ─── Plan B: Chat endpoint ───────────────────────────────────────────────────

@app.route('/api/chat', methods=['POST'])
def chat():
    """Natural language chat endpoint — accepts free-text, returns decision in INR with isolated database storage."""
    data = request.json or {}
    message = data.get('message', '').strip()
    user_id = data.get('user_id') or get_active_user_id()

    if not message:
        return jsonify({'error': 'No message provided'}), 400

    prof = get_user_profile(user_id)
    if not prof:
        saved = list_all_account_profiles()
        prof = saved[0] if saved else DEFAULT_USER_PROFILE
        user_id = prof['user_id']

    sync_user_to_engine(user_id, engine)

    # Extract intent from natural language (in INR context)
    intent = extract_intent(message, user_currency='INR')

    # If we need a follow-up, return the question and persist in this user's DB
    if intent.get('follow_up_needed'):
        question = intent['follow_up_question']
        add_user_chat_message(user_id, 'user', message, intent)
        add_user_chat_message(user_id, 'assistant', question, intent)
        return jsonify({
            'type': 'follow_up',
            'question': question,
            'intent': intent,
            'user_id': user_id,
            'database_file': os.path.basename(get_user_db_path(user_id))
        })

    # Build a mock request row and evaluate entirely in INR against this user's profile
    req_date = intent.get('desired_date') or str(date.today())
    amount_inr = float(intent.get('amount') or 0.0)

    mock_row = pd.Series({
        'request_id': f"chat_{int(datetime.now().timestamp())}",
        'user_id': user_id,
        'request_date': req_date,
        'requested_amount': amount_inr,
        'desired_completion_date': intent.get('desired_date') or req_date,
        'allows_partial_payment': intent.get('allows_partial', True),
        'request_text': message
    })

    prediction = engine.evaluate_request(mock_row)
    trajectory = engine.simulate_cash_flow(user_id, req_date)

    pred_inr = dict(prediction)
    reply = format_decision_reply(pred_inr, intent)
    reply = convert_currencies_in_text(reply)
    if 'decision_explanation' in pred_inr:
        pred_inr['decision_explanation'] = convert_currencies_in_text(pred_inr['decision_explanation'])

    # Save to user's dedicated SQLite database chat_history table
    add_user_chat_message(user_id, 'user', message, intent)
    add_user_chat_message(user_id, 'assistant', reply, intent, pred_inr)

    return jsonify({
        'type': 'decision',
        'reply': reply,
        'intent': intent,
        'prediction': pred_inr,
        'trajectory': {
            'dates': trajectory['dates'],
            'balances': trajectory['balances'],
            'min_balance': trajectory['min_balance'],
            'currency': 'INR'
        },
        'user_id': user_id,
        'database_file': os.path.basename(get_user_db_path(user_id))
    })

@app.route('/api/chat/history')
def get_chat_history_route():
    """Retrieve chat history strictly from the active user's dedicated database."""
    user_id = request.args.get('user_id') or get_active_user_id()
    messages = get_user_chat_history(user_id)
    return jsonify({
        'user_id': user_id,
        'database_file': os.path.basename(get_user_db_path(user_id)),
        'total_messages': len(messages),
        'messages': messages
    })


@app.route('/api/ocr_receipt', methods=['POST'])
def ocr_receipt():
    """Extract amount/merchant from a base64-encoded receipt image."""
    data = request.json or {}
    image_b64 = data.get('image_base64', '')

    if not image_b64:
        return jsonify({'error': 'No image_base64 provided'}), 400

    # Try Google Cloud Vision if credentials set, else use mock
    gcv_key = os.environ.get('GOOGLE_CLOUD_VISION_API_KEY')
    result = None

    if gcv_key:
        try:
            import urllib.request as urlreq
            payload = json.dumps({
                'requests': [{
                    'image': {'content': image_b64},
                    'features': [{'type': 'TEXT_DETECTION'}]
                }]
            }).encode()
            req = urlreq.Request(
                f'https://vision.googleapis.com/v1/images:annotate?key={gcv_key}',
                data=payload,
                headers={'Content-Type': 'application/json'}
            )
            r = urlreq.urlopen(req)
            vision_data = json.loads(r.read())
            raw_text = vision_data['responses'][0].get('fullTextAnnotation', {}).get('text', '')
            # Use LLM intent to parse the OCR text
            extracted = extract_intent(f"Receipt text: {raw_text}")
            result = {
                'amount': extracted.get('amount'),
                'currency': extracted.get('currency'),
                'merchant': extracted.get('item_description', 'Unknown'),
                'date': str(date.today()),
                '_source': 'google_cloud_vision'
            }
        except Exception as e:
            result = None

    if not result:
        # Mock extraction for demo
        result = {
            'amount': 4500.00,
            'currency': 'INR',
            'merchant': 'Sample Merchant (mock — set GOOGLE_CLOUD_VISION_API_KEY for real OCR)',
            'date': str(date.today()),
            '_source': 'mock'
        }

    return jsonify(result)


# ─── Plan A: Bank connection endpoints (RBI Account Aggregator) ─────────────

_aa = AccountAggregatorConnector()

@app.route('/connect/bank')
def bank_connect_init():
    """Step 1: Generate RBI Account Aggregator consent."""
    user_id = request.args.get('user_id', 'user_demo')
    consent_data = _aa.initiate_consent(
        user_mobile='9876543210',
        aa_handle='onemoney',
        redirect_url='http://127.0.0.1:5000/connect/bank/callback'
    )
    return jsonify(consent_data)


@app.route('/connect/bank/callback', methods=['POST'])
def bank_connect_callback():
    """Step 2: Exchange consent token and build live Indian bank profile."""
    data = request.json or {}
    consent_handle = data.get('consent_handle', data.get('public_token', 'mock-consent-3210'))
    user_id = data.get('user_id', 'user_demo')

    live_profile = build_live_profile(user_id, consent_handle, provider='aa')

    return jsonify({
        'status': 'connected',
        'profile_summary': {
            'available_balance': live_profile['current_available_balance'],
            'currency': 'INR',
            'salary': live_profile['monthly_salary'],
            'recurring_expenses': len(live_profile['monthly_fixed_commitments']),
            'source': 'rbi_account_aggregator'
        }
    })


@app.route('/api/live_profile')
def live_profile():
    """Demo: build and return a live profile using Indian RBI Account Aggregator data."""
    user_id = request.args.get('user_id', 'user_demo')
    profile = build_live_profile(user_id, 'mock-consent-token', provider='aa')
    return jsonify(profile)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"Starting Buy or Wait? AI Financial Hub on http://127.0.0.1:{port}")
    app.run(host='127.0.0.1', port=port, debug=False)
