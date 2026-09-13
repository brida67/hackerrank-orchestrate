import os
import sqlite3
import json
from datetime import datetime, date, timedelta

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASES_DIR = os.path.join(CURRENT_DIR, 'user_databases')
LOCAL_USERS_FILE = os.path.join(CURRENT_DIR, 'local_users.json')

os.makedirs(DATABASES_DIR, exist_ok=True)

def get_user_db_path(user_id):
    """Return the absolute path to a user's dedicated SQLite database."""
    safe_uid = "".join(c for c in user_id if c.isalnum() or c in ('_', '-'))
    return os.path.join(DATABASES_DIR, f"{safe_uid}.db")

def get_db_connection(user_id):
    """Open a connection to the user's dedicated database."""
    db_path = get_user_db_path(user_id)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_user_database(profile_data):
    """
    Initialize a user's isolated SQLite database.
    Creates tables: account_profile, financial_events, financial_requests, chat_history, simulations.
    Inserts or updates the profile_data.
    """
    user_id = profile_data['user_id']
    db_path = get_user_db_path(user_id)
    is_new = not os.path.exists(db_path)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 1. Profile Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS account_profile (
            user_id TEXT PRIMARY KEY,
            full_name TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            security_pin TEXT NOT NULL,
            bank_name TEXT NOT NULL,
            account_type TEXT DEFAULT 'Savings Account',
            account_number TEXT NOT NULL,
            account_masked TEXT,
            ifsc_code TEXT,
            branch_name TEXT,
            upi_id TEXT,
            current_balance REAL DEFAULT 0.0,
            monthly_salary REAL DEFAULT 0.0,
            monthly_commitments REAL DEFAULT 0.0,
            minimum_buffer REAL DEFAULT 0.0,
            currency TEXT DEFAULT 'INR',
            financial_priorities TEXT DEFAULT 'emergency_savings|debt_repayment',
            expense_categories_to_protect TEXT DEFAULT 'rent|utilities|groceries',
            expense_categories_user_is_willing_to_reduce TEXT DEFAULT 'dining|shopping',
            expense_categories_user_is_willing_to_stop TEXT DEFAULT 'entertainment',
            payment_methods_user_will_consider TEXT DEFAULT 'full_payment|partial_payment|installments',
            max_installment_months INTEGER DEFAULT 6,
            auth_provider TEXT DEFAULT 'RBI Account Aggregator (AA)',
            verified INTEGER DEFAULT 1,
            last_sync TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 2. Financial Events / Transactions Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS financial_events (
            event_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            category TEXT NOT NULL,
            amount REAL NOT NULL,
            currency TEXT DEFAULT 'INR',
            direction TEXT NOT NULL,
            status TEXT DEFAULT 'settled',
            event_date TEXT NOT NULL,
            settlement_date TEXT,
            description TEXT,
            is_recurring INTEGER DEFAULT 0,
            recurring_day INTEGER
        )
    ''')

    # 3. Financial Requests Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS financial_requests (
            request_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            request_date TEXT NOT NULL,
            request_type TEXT NOT NULL,
            requested_amount REAL NOT NULL,
            desired_completion_date TEXT,
            allows_partial_payment INTEGER DEFAULT 1,
            request_text TEXT,
            amount_safe_to_pay REAL,
            affordability_status TEXT,
            recommended_payment_method TEXT,
            payment_plan TEXT,
            earliest_date_for_full_payment TEXT,
            spending_changes_needed TEXT,
            decision_explanation TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 4. Chat History Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_history (
            message_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            sender TEXT NOT NULL,
            message_text TEXT NOT NULL,
            intent_json TEXT,
            decision_json TEXT,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 5. Simulations Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS simulations (
            sim_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            request_date TEXT NOT NULL,
            requested_amount REAL NOT NULL,
            desired_date TEXT,
            spending_changes_json TEXT,
            result_json TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Insert or Replace Profile
    now_str = datetime.now().strftime('%d %b %Y, %I:%M %p IST')
    cursor.execute('''
        INSERT OR REPLACE INTO account_profile (
            user_id, full_name, email, phone, security_pin, bank_name,
            account_type, account_number, account_masked, ifsc_code,
            branch_name, upi_id, current_balance, monthly_salary,
            monthly_commitments, minimum_buffer, currency,
            financial_priorities, expense_categories_to_protect,
            expense_categories_user_is_willing_to_reduce,
            expense_categories_user_is_willing_to_stop,
            payment_methods_user_will_consider, max_installment_months,
            auth_provider, verified, last_sync, updated_at
        ) VALUES (
            :user_id, :full_name, :email, :phone, :security_pin, :bank_name,
            :account_type, :account_number, :account_masked, :ifsc_code,
            :branch_name, :upi_id, :current_balance, :monthly_salary,
            :monthly_commitments, :minimum_buffer, :currency,
            :financial_priorities, :expense_categories_to_protect,
            :expense_categories_user_is_willing_to_reduce,
            :expense_categories_user_is_willing_to_stop,
            :payment_methods_user_will_consider, :max_installment_months,
            :auth_provider, :verified, :last_sync, :updated_at
        )
    ''', {
        'user_id': user_id,
        'full_name': profile_data.get('full_name', ''),
        'email': profile_data.get('email', ''),
        'phone': profile_data.get('phone', ''),
        'security_pin': str(profile_data.get('security_pin', '')).strip(),
        'bank_name': profile_data.get('bank_name', 'HDFC Bank'),
        'account_type': profile_data.get('account_type', 'Savings Account'),
        'account_number': profile_data.get('account_number', ''),
        'account_masked': profile_data.get('account_masked', f"•••• {profile_data.get('account_number', '0000')[-4:]}"),
        'ifsc_code': profile_data.get('ifsc_code', 'SBIN0000001'),
        'branch_name': profile_data.get('branch_name', 'Fort Branch, Mumbai'),
        'upi_id': profile_data.get('upi_id', ''),
        'current_balance': float(profile_data.get('current_balance', 50000.0)),
        'monthly_salary': float(profile_data.get('monthly_salary', 90000.0)),
        'monthly_commitments': float(profile_data.get('monthly_commitments', 12000.0)),
        'minimum_buffer': float(profile_data.get('minimum_buffer', 16000.0)),
        'currency': profile_data.get('currency', 'INR'),
        'financial_priorities': profile_data.get('financial_priorities', 'emergency_savings|debt_repayment'),
        'expense_categories_to_protect': profile_data.get('expense_categories_to_protect', 'rent|utilities|groceries'),
        'expense_categories_user_is_willing_to_reduce': profile_data.get('expense_categories_user_is_willing_to_reduce', 'dining|shopping'),
        'expense_categories_user_is_willing_to_stop': profile_data.get('expense_categories_user_is_willing_to_stop', 'entertainment'),
        'payment_methods_user_will_consider': profile_data.get('payment_methods_user_will_consider', 'full_payment|partial_payment|installments'),
        'max_installment_months': int(profile_data.get('max_installment_months', 6)),
        'auth_provider': profile_data.get('auth_provider', 'RBI Account Aggregator (AA)'),
        'verified': 1 if profile_data.get('verified', True) else 0,
        'last_sync': profile_data.get('last_sync', now_str),
        'updated_at': now_str
    })

    conn.commit()

    # If new database, seed starter transactions and sample requests matching this user's profile
    cursor.execute("SELECT COUNT(*) FROM financial_events WHERE user_id = ?", (user_id,))
    events_count = cursor.fetchone()[0]
    if events_count == 0:
        seed_user_events_and_requests(conn, user_id, profile_data)

    conn.close()
    sync_all_profiles_to_local_users_json()
    return db_path

def seed_user_events_and_requests(conn, user_id, p):
    """Seed initial realistic events and personalized requests tailored to this user's balance and salary."""
    cursor = conn.cursor()
    sal = float(p.get('monthly_salary', 90000.0))
    bal = float(p.get('current_balance', 50000.0))
    commitments = float(p.get('monthly_commitments', 12000.0))
    buffer_amt = float(p.get('minimum_buffer', 16000.0))
    today = date(2026, 9, 13)

    # Calculate reasonable breakdown of commitments
    rent = round(commitments * 0.55, 2)
    utilities = round(commitments * 0.15, 2)
    groceries = round(commitments * 0.20, 2)
    sub_emi = round(commitments * 0.10, 2)

    # Seed past 3 months settled events
    events = []
    for m_offset in range(3, -1, -1):
        # Salary credit on 30th / 28th
        sal_date = (today - timedelta(days=m_offset * 30)).replace(day=1) - timedelta(days=1)
        if sal_date <= today:
            events.append((
                f"evt_{user_id}_sal_{sal_date.strftime('%Y%m')}",
                user_id, 'salary', 'income', sal, 'INR', 'credit', 'settled',
                sal_date.strftime('%Y-%m-%d'), sal_date.strftime('%Y-%m-%d'),
                f"Monthly Salary Credit - {p.get('bank_name', 'Bank')}", 1, 30
            ))
        
        # Rent debit on 5th
        rent_date = (today - timedelta(days=m_offset * 30)).replace(day=5)
        if rent_date <= today:
            events.append((
                f"evt_{user_id}_rent_{rent_date.strftime('%Y%m')}",
                user_id, 'rent', 'rent', rent, 'INR', 'debit', 'settled',
                rent_date.strftime('%Y-%m-%d'), rent_date.strftime('%Y-%m-%d'),
                "Monthly House Rent Transfer", 1, 5
            ))

        # Utilities on 10th
        util_date = (today - timedelta(days=m_offset * 30)).replace(day=10)
        if util_date <= today:
            events.append((
                f"evt_{user_id}_util_{util_date.strftime('%Y%m')}",
                user_id, 'utilities', 'utilities', utilities, 'INR', 'debit', 'settled',
                util_date.strftime('%Y-%m-%d'), util_date.strftime('%Y-%m-%d'),
                "Electricity & High-Speed Internet Bill", 1, 10
            ))

        # Groceries on 15th
        groc_date = (today - timedelta(days=m_offset * 30)).replace(day=15)
        if groc_date <= today:
            events.append((
                f"evt_{user_id}_groc_{groc_date.strftime('%Y%m')}",
                user_id, 'groceries', 'groceries', groceries, 'INR', 'debit', 'settled',
                groc_date.strftime('%Y-%m-%d'), groc_date.strftime('%Y-%m-%d'),
                "Supermarket & Essential Household Supplies", 1, 15
            ))

    # Upcoming confirmed salary credit
    next_sal = date(2026, 9, 30)
    events.append((
        f"evt_{user_id}_sal_next",
        user_id, 'salary', 'income', sal, 'INR', 'credit', 'confirmed',
        next_sal.strftime('%Y-%m-%d'), next_sal.strftime('%Y-%m-%d'),
        "Upcoming Confirmed Monthly Salary Credit", 1, 30
    ))

    cursor.executemany('''
        INSERT OR IGNORE INTO financial_events (
            event_id, user_id, event_type, category, amount, currency,
            direction, status, event_date, settlement_date, description,
            is_recurring, recurring_day
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', events)

    # Personalized Requests based on wealth and cash flow
    if bal > 1000000:
        # High net worth profile (e.g. Samruddhi)
        reqs = [
            (
                f"req_{user_id}_01", user_id, "2026-09-13", "Luxury EV / SUV Down Payment",
                1500000.0, "2026-09-20", 1,
                "Planning to pay the initial down payment for a premium electric vehicle. Current liquid balance is over ₹ 89 Lakhs.",
                1500000.0, "affordable_now", "full_payment", "2026-09-13:1500000.00",
                "2026-09-13", "none",
                f"Safe to pay in full immediately. Post-purchase balance will be ₹ {bal - 1500000:,.2f}, which comfortably exceeds your ₹ {buffer_amt:,.2f} safety floor with ongoing ₹ {sal:,.2f}/mo net income."
            ),
            (
                f"req_{user_id}_02", user_id, "2026-09-13", "Commercial Real Estate Token Investment",
                4500000.0, "2026-10-15", 1,
                "Looking to invest ₹ 45 Lakhs into a Grade-A commercial office space fund.",
                4500000.0, "affordable_now", "full_payment", "2026-09-13:4500000.00",
                "2026-09-13", "none",
                f"Full payment is fully affordable. Your liquid reserves remain at ₹ {bal - 4500000:,.2f}, well above your buffer floor of ₹ {buffer_amt:,.2f}."
            ),
            (
                f"req_{user_id}_03", user_id, "2026-09-13", "Luxury International Holiday Tour",
                450000.0, "2026-09-25", 1,
                "Family holiday package to Switzerland & France for autumn.",
                450000.0, "affordable_now", "full_payment", "2026-09-13:450000.00",
                "2026-09-13", "none",
                "Easily affordable now with zero impact on fixed monthly commitments."
            )
        ]
    else:
        # Standard salaried profile (e.g. Rida)
        safe_now = max(0.0, bal - buffer_amt)
        reqs = [
            (
                f"req_{user_id}_01", user_id, "2026-09-13", "Ergonomic Workstation & Chair",
                12000.0, "2026-09-18", 1,
                "Need an ergonomic chair and monitor stand for home office setup.",
                12000.0, "affordable_now", "full_payment", "2026-09-13:12000.00",
                "2026-09-13", "none",
                f"Safe to pay in full today. Remaining balance will be ₹ {bal - 12000:,.2f}, remaining above your protected floor of ₹ {buffer_amt:,.2f}."
            ),
            (
                f"req_{user_id}_02", user_id, "2026-09-13", "MacBook Air M3 Laptop",
                48000.0, "2026-10-31", 1,
                "Can I afford this laptop for development work? It costs ₹ 48,000.",
                min(safe_now, 34000.0), "affordable_with_plan", "installments",
                "2026-09-13:16000.00|2026-09-30:16000.00|2026-10-30:16000.00",
                "2026-09-30", "none",
                f"A one-time payment today would drop your balance below your ₹ {buffer_amt:,.2f} emergency buffer. An interest-free 3-part installment plan of ₹ 16,000/mo aligned with your monthly ₹ {sal:,.2f} salary on the 30th is 100% safe."
            ),
            (
                f"req_{user_id}_03", user_id, "2026-09-13", "International Vacation Tour",
                85000.0, "2026-10-15", 0,
                "Trip to Dubai during the holidays with upfront package fee.",
                0.0, "affordable_later", "wait", "none",
                "2026-10-30", "reduce_to:dining:2000|stop:entertainment",
                f"Exceeds current liquid headroom. Earliest safe full payment date is 2026-10-30 after two salary cycles and curtailing flexible dining/entertainment expenses."
            )
        ]

    cursor.executemany('''
        INSERT OR IGNORE INTO financial_requests (
            request_id, user_id, request_date, request_type, requested_amount,
            desired_completion_date, allows_partial_payment, request_text,
            amount_safe_to_pay, affordability_status, recommended_payment_method,
            payment_plan, earliest_date_for_full_payment, spending_changes_needed,
            decision_explanation
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', reqs)

    conn.commit()

def get_user_profile(user_id):
    """Retrieve user profile from their dedicated database."""
    db_path = get_user_db_path(user_id)
    if not os.path.exists(db_path):
        return None
    conn = get_db_connection(user_id)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM account_profile WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None

def update_user_profile(user_id, updates):
    """Update fields in the user's profile table."""
    conn = get_db_connection(user_id)
    cursor = conn.cursor()
    fields = []
    values = []
    for k, v in updates.items():
        if k != 'user_id':
            fields.append(f"{k} = ?")
            values.append(v)
    fields.append("updated_at = ?")
    now_str = datetime.now().strftime('%d %b %Y, %I:%M %p IST')
    values.append(now_str)
    values.append(user_id)

    cursor.execute(f"UPDATE account_profile SET {', '.join(fields)} WHERE user_id = ?", values)
    conn.commit()
    conn.close()
    sync_all_profiles_to_local_users_json()

def get_user_events(user_id, status=None, limit=100):
    """Retrieve financial events strictly from this user's database."""
    conn = get_db_connection(user_id)
    cursor = conn.cursor()
    if status:
        cursor.execute("SELECT * FROM financial_events WHERE user_id = ? AND status = ? ORDER BY event_date DESC LIMIT ?", (user_id, status, limit))
    else:
        cursor.execute("SELECT * FROM financial_events WHERE user_id = ? ORDER BY event_date DESC LIMIT ?", (user_id, limit))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def add_user_event(user_id, event_dict):
    """Insert a new financial event into this user's database."""
    conn = get_db_connection(user_id)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO financial_events (
            event_id, user_id, event_type, category, amount, currency,
            direction, status, event_date, settlement_date, description,
            is_recurring, recurring_day
        ) VALUES (
            :event_id, :user_id, :event_type, :category, :amount, :currency,
            :direction, :status, :event_date, :settlement_date, :description,
            :is_recurring, :recurring_day
        )
    ''', {
        'event_id': event_dict.get('event_id', f"evt_{user_id}_{int(datetime.now().timestamp())}"),
        'user_id': user_id,
        'event_type': event_dict.get('event_type', 'expense'),
        'category': event_dict.get('category', 'general'),
        'amount': float(event_dict.get('amount', 0.0)),
        'currency': event_dict.get('currency', 'INR'),
        'direction': event_dict.get('direction', 'debit'),
        'status': event_dict.get('status', 'settled'),
        'event_date': event_dict.get('event_date', date.today().strftime('%Y-%m-%d')),
        'settlement_date': event_dict.get('settlement_date', date.today().strftime('%Y-%m-%d')),
        'description': event_dict.get('description', ''),
        'is_recurring': 1 if event_dict.get('is_recurring') else 0,
        'recurring_day': event_dict.get('recurring_day', None)
    })
    conn.commit()
    conn.close()

def get_user_requests(user_id):
    """Retrieve financial requests strictly from this user's database."""
    conn = get_db_connection(user_id)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM financial_requests WHERE user_id = ? ORDER BY request_date DESC, created_at DESC", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_user_request(user_id, request_id):
    """Retrieve a single request from this user's database."""
    conn = get_db_connection(user_id)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM financial_requests WHERE user_id = ? AND request_id = ?", (user_id, request_id))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def add_user_request(user_id, req_dict):
    """Save a financial request and its decision in this user's database."""
    conn = get_db_connection(user_id)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO financial_requests (
            request_id, user_id, request_date, request_type, requested_amount,
            desired_completion_date, allows_partial_payment, request_text,
            amount_safe_to_pay, affordability_status, recommended_payment_method,
            payment_plan, earliest_date_for_full_payment, spending_changes_needed,
            decision_explanation
        ) VALUES (
            :request_id, :user_id, :request_date, :request_type, :requested_amount,
            :desired_completion_date, :allows_partial_payment, :request_text,
            :amount_safe_to_pay, :affordability_status, :recommended_payment_method,
            :payment_plan, :earliest_date_for_full_payment, :spending_changes_needed,
            :decision_explanation
        )
    ''', {
        'request_id': req_dict.get('request_id', f"req_{user_id}_{int(datetime.now().timestamp())}"),
        'user_id': user_id,
        'request_date': req_dict.get('request_date', date.today().strftime('%Y-%m-%d')),
        'request_type': req_dict.get('request_type', 'General Expense'),
        'requested_amount': float(req_dict.get('requested_amount', 0.0)),
        'desired_completion_date': req_dict.get('desired_completion_date', ''),
        'allows_partial_payment': 1 if req_dict.get('allows_partial_payment', True) else 0,
        'request_text': req_dict.get('request_text', ''),
        'amount_safe_to_pay': float(req_dict.get('amount_safe_to_pay', 0.0)),
        'affordability_status': req_dict.get('affordability_status', 'not_affordable'),
        'recommended_payment_method': req_dict.get('recommended_payment_method', 'wait'),
        'payment_plan': req_dict.get('payment_plan', 'none'),
        'earliest_date_for_full_payment': req_dict.get('earliest_date_for_full_payment', ''),
        'spending_changes_needed': req_dict.get('spending_changes_needed', 'none'),
        'decision_explanation': req_dict.get('decision_explanation', '')
    })
    conn.commit()
    conn.close()

def get_user_chat_history(user_id, limit=50):
    """Retrieve chat conversation strictly from this user's database."""
    conn = get_db_connection(user_id)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM chat_history WHERE user_id = ? ORDER BY message_id ASC LIMIT ?", (user_id, limit))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def add_user_chat_message(user_id, sender, text, intent=None, decision=None):
    """Store a chat message and decision in this user's database."""
    conn = get_db_connection(user_id)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO chat_history (user_id, sender, message_text, intent_json, decision_json)
        VALUES (?, ?, ?, ?, ?)
    ''', (
        user_id,
        sender,
        text,
        json.dumps(intent) if intent else None,
        json.dumps(decision) if decision else None
    ))
    conn.commit()
    conn.close()

def delete_user_database(user_id):
    """Safely delete this user's database file and clean up."""
    db_path = get_user_db_path(user_id)
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except Exception as e:
            print(f"Error removing db file {db_path}: {e}")
    sync_all_profiles_to_local_users_json()

def list_all_user_ids():
    """Find all user databases currently on disk."""
    if not os.path.exists(DATABASES_DIR):
        return []
    uids = []
    for f in os.listdir(DATABASES_DIR):
        if f.endswith('.db'):
            uid = f[:-3]
            uids.append(uid)
    return uids

def list_all_account_profiles():
    """List profiles from all individual user databases."""
    uids = list_all_user_ids()
    profiles = []
    for uid in uids:
        p = get_user_profile(uid)
        if p:
            profiles.append(p)
    return profiles

def sync_all_profiles_to_local_users_json():
    """Keep local_users.json in sync with all user database files."""
    profiles = list_all_account_profiles()
    if profiles:
        try:
            with open(LOCAL_USERS_FILE, 'w', encoding='utf-8') as f:
                json.dump(profiles, f, indent=2)
        except Exception as e:
            print(f"Error updating local_users.json: {e}")

def seed_from_existing_local_users_json():
    """Bootstraps isolated databases for any accounts already present in local_users.json."""
    if os.path.exists(LOCAL_USERS_FILE):
        try:
            with open(LOCAL_USERS_FILE, 'r', encoding='utf-8') as f:
                saved = json.load(f)
                if isinstance(saved, list):
                    for u in saved:
                        if isinstance(u, dict) and u.get('user_id'):
                            init_user_database(u)
        except Exception as e:
            print(f"Error seeding from local_users.json: {e}")

def sync_user_to_engine(user_id, engine):
    """Sync a user's dedicated SQLite profile and events into the in-memory FinancialDecisionEngine."""
    prof = get_user_profile(user_id)
    if not prof:
        return
    import pandas as pd
    
    # 1. Update engine.profiles row for this user
    prof_row = {
        'user_id': user_id,
        'home_currency': 'INR',
        'current_available_balance': float(prof['current_balance']),
        'minimum_balance_to_keep': float(prof['minimum_buffer']),
        'financial_priorities': prof.get('financial_priorities', 'emergency_savings|debt_repayment'),
        'expense_categories_to_protect': prof.get('expense_categories_to_protect', 'rent|utilities|groceries'),
        'expense_categories_user_is_willing_to_reduce': prof.get('expense_categories_user_is_willing_to_reduce', 'dining|shopping'),
        'expense_categories_user_is_willing_to_stop': prof.get('expense_categories_user_is_willing_to_stop', 'entertainment'),
        'payment_methods_user_will_consider': prof.get('payment_methods_user_will_consider', 'full_payment|partial_payment|installments'),
        'max_installment_months': int(prof.get('max_installment_months', 6))
    }
    if hasattr(engine, 'profiles') and engine.profiles is not None:
        engine.profiles = engine.profiles[engine.profiles['user_id'] != user_id]
        engine.profiles = pd.concat([engine.profiles, pd.DataFrame([prof_row])], ignore_index=True)

    # 2. Update engine.events with this user's transactions from their SQLite database
    events = get_user_events(user_id, limit=200)
    if events and hasattr(engine, 'events') and engine.events is not None:
        ev_rows = []
        for e in events:
            try:
                s_dt = datetime.strptime(str(e['settlement_date']), '%Y-%m-%d').date() if e.get('settlement_date') else date.today()
            except Exception:
                s_dt = date.today()
            try:
                e_dt = datetime.strptime(str(e['event_date']), '%Y-%m-%d').date() if e.get('event_date') else date.today()
            except Exception:
                e_dt = date.today()

            ev_rows.append({
                'event_id': e['event_id'],
                'user_id': user_id,
                'event_type': e['event_type'],
                'category': e['category'],
                'amount': float(e['amount']),
                'currency': e.get('currency', 'INR'),
                'direction': e['direction'],
                'status': e['status'],
                'event_date': e['event_date'],
                'settlement_date': e.get('settlement_date', e['event_date']),
                'description': e.get('description', ''),
                's_dt': s_dt,
                'e_dt': e_dt
            })
        engine.events = engine.events[engine.events['user_id'] != user_id]
        engine.events = pd.concat([engine.events, pd.DataFrame(ev_rows)], ignore_index=True)

# Run automatic seed check on import
seed_from_existing_local_users_json()
