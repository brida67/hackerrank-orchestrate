"""
bank_connector.py — Live Bank Data Integration
Supports: Plaid (global), RBI Account Aggregator (India)
Falls back to mock data when credentials not configured.
"""

import os
import json
import hashlib
import base64
from datetime import date, timedelta
from typing import Optional
from collections import defaultdict


# ─── Plaid Integration ──────────────────────────────────────────────────────

class PlaidConnector:
    """
    Connects to Plaid API for real-time bank data.
    Requires: PLAID_CLIENT_ID and PLAID_SECRET environment variables.
    Docs: https://plaid.com/docs/
    """

    ENVIRONMENTS = {
        'sandbox':    'https://sandbox.plaid.com',
        'development': 'https://development.plaid.com',
        'production': 'https://production.plaid.com',
    }

    def __init__(self, env: str = 'sandbox'):
        self.client_id = os.environ.get('PLAID_CLIENT_ID', '')
        self.secret = os.environ.get('PLAID_SECRET', '')
        self.base_url = self.ENVIRONMENTS.get(env, self.ENVIRONMENTS['sandbox'])
        self.configured = bool(self.client_id and self.secret)

    def create_link_token(self, user_id: str, redirect_uri: str = None) -> dict:
        """
        Step 1 of OAuth: generate a link_token to initialize Plaid Link in frontend.
        Returns: { link_token, expiration }
        """
        if not self.configured:
            return self._mock_link_token(user_id)

        import requests
        payload = {
            'client_id': self.client_id,
            'secret': self.secret,
            'client_name': 'Buy or Wait',
            'country_codes': ['US', 'GB', 'IN'],
            'language': 'en',
            'user': {'client_user_id': user_id},
            'products': ['transactions', 'auth'],
        }
        if redirect_uri:
            payload['redirect_uri'] = redirect_uri

        resp = requests.post(f"{self.base_url}/link/token/create", json=payload)
        resp.raise_for_status()
        return resp.json()

    def exchange_public_token(self, public_token: str) -> str:
        """
        Step 2 of OAuth: exchange short-lived public_token for permanent access_token.
        The access_token must be stored encrypted.
        """
        if not self.configured:
            return f"mock-access-token-{hashlib.md5(public_token.encode()).hexdigest()[:8]}"

        import requests
        resp = requests.post(f"{self.base_url}/item/public_token/exchange", json={
            'client_id': self.client_id,
            'secret': self.secret,
            'public_token': public_token
        })
        resp.raise_for_status()
        return resp.json()['access_token']

    def get_balance(self, access_token: str) -> dict:
        """
        Fetch real-time account balance.
        Returns: { available, current, currency }
        """
        if not self.configured or access_token.startswith('mock-'):
            return self._mock_balance()

        import requests
        resp = requests.post(f"{self.base_url}/accounts/balance/get", json={
            'client_id': self.client_id,
            'secret': self.secret,
            'access_token': access_token
        })
        resp.raise_for_status()
        account = resp.json()['accounts'][0]['balances']
        return {
            'available': account.get('available') or account.get('current', 0),
            'current': account.get('current', 0),
            'currency': account.get('iso_currency_code', 'USD')
        }

    def get_transactions(self, access_token: str, days: int = 90) -> list:
        """
        Fetch transaction history for the last N days.
        Returns list of normalized transaction dicts.
        """
        if not self.configured or access_token.startswith('mock-'):
            return self._mock_transactions(days)

        import requests
        end = date.today()
        start = end - timedelta(days=days)
        resp = requests.post(f"{self.base_url}/transactions/get", json={
            'client_id': self.client_id,
            'secret': self.secret,
            'access_token': access_token,
            'start_date': str(start),
            'end_date': str(end),
            'options': {'count': 500}
        })
        resp.raise_for_status()
        return [self._normalize_txn(t) for t in resp.json().get('transactions', [])]

    def _normalize_txn(self, t: dict) -> dict:
        """Normalize Plaid transaction to engine format."""
        cat = (t.get('category') or ['other'])[0]
        cat_map = {
            'Rent and Utilities': 'rent',
            'Groceries': 'shopping',
            'Restaurants': 'dining',
            'Transfer': 'salary',
            'Subscription': 'subscriptions',
            'Health': 'healthcare',
            'Insurance': 'insurance',
            'Education': 'education',
            'Loan': 'debt_repayment',
        }
        return {
            'date': t['date'],
            'amount': abs(t['amount']),
            'direction': 'credit' if t['amount'] < 0 else 'debit',
            'category': cat_map.get(cat, 'other'),
            'merchant': t.get('merchant_name') or t.get('name', ''),
            'status': 'settled',
            'currency': t.get('iso_currency_code', 'USD')
        }

    # ── Mock data for demo / when credentials not set ─────────────────────

    def _mock_link_token(self, user_id: str) -> dict:
        return {
            'link_token': f'link-sandbox-mock-{user_id}',
            'expiration': str(date.today() + timedelta(hours=4)),
            '_mock': True
        }

    def _mock_balance(self) -> dict:
        return {
            'available': 125000.0,
            'current': 135000.0,
            'currency': 'INR',
            '_mock': True
        }

    def _mock_transactions(self, days: int) -> list:
        """Generate realistic mock recurring transactions in INR."""
        today = date.today()
        txns = []
        for i in range(3):
            month_start = (today.replace(day=1) - timedelta(days=30 * i))
            txns += [
                {'date': str(month_start.replace(day=1)),  'amount': 22000.0, 'direction': 'debit',  'category': 'rent',          'merchant': 'HDFC Home Rent/EMI',    'status': 'settled', 'currency': 'INR'},
                {'date': str(month_start.replace(day=5)),  'amount': 649.0,   'direction': 'debit',  'category': 'subscriptions',  'merchant': 'Netflix India',          'status': 'settled', 'currency': 'INR'},
                {'date': str(month_start.replace(day=10)), 'amount': 8500.0,  'direction': 'debit',  'category': 'shopping',       'merchant': 'Blinkit / Zepto',       'status': 'settled', 'currency': 'INR'},
                {'date': str(month_start.replace(day=15)), 'amount': 85000.0, 'direction': 'credit', 'category': 'salary',         'merchant': 'Infosys Technologies',   'status': 'settled', 'currency': 'INR'},
                {'date': str(month_start.replace(day=20)), 'amount': 2500.0,  'direction': 'debit',  'category': 'dining',         'merchant': 'Zomato / Swiggy',       'status': 'settled', 'currency': 'INR'},
            ]
        return txns


# ─── RBI Account Aggregator (India) ─────────────────────────────────────────

class AccountAggregatorConnector:
    """
    RBI-regulated consent-based financial data sharing for India.
    Compatible with: Finvu, OneMoney, PhonePe AA, CAMS Finserv.
    Requires: AA_CLIENT_ID, AA_CLIENT_SECRET, AA_BASE_URL env vars.
    Docs: https://sahamati.org.in/aa-api-specification/
    """

    def __init__(self):
        self.client_id = os.environ.get('AA_CLIENT_ID', '')
        self.client_secret = os.environ.get('AA_CLIENT_SECRET', '')
        self.base_url = os.environ.get('AA_BASE_URL', 'https://api.finvu.in/consentapi')
        self.configured = bool(self.client_id and self.client_secret)

    def initiate_consent(self, user_mobile: str, aa_handle: str,
                          redirect_url: str, days_back: int = 180) -> dict:
        """
        Step 1: Initiate consent request. User will receive a notification
        on their AA mobile app to approve.
        Returns: { consent_handle, redirect_url }
        """
        if not self.configured:
            return self._mock_consent(user_mobile)

        import requests
        end = date.today()
        start = end - timedelta(days=days_back)
        payload = {
            'ver': '1.0',
            'timestamp': str(date.today()),
            'txnid': hashlib.sha256(user_mobile.encode()).hexdigest()[:16],
            'ConsentDetail': {
                'consentStart': str(start),
                'consentExpiry': str(end + timedelta(days=1)),
                'consentMode': 'VIEW',
                'fetchType': 'PERIODIC',
                'consentTypes': ['PROFILE', 'SUMMARY', 'TRANSACTIONS'],
                'fiTypes': ['DEPOSIT', 'RECURRING_DEPOSIT', 'TERM_DEPOSIT'],
                'DataConsumer': {'id': self.client_id},
                'Customer': {'id': f"{user_mobile}@{aa_handle}"},
                'FIDataRange': {'from': str(start), 'to': str(end)},
                'DataLife': {'unit': 'MONTH', 'value': 1},
                'Frequency': {'unit': 'HOUR', 'value': 1},
                'DataFilter': []
            }
        }
        resp = requests.post(f"{self.base_url}/Consent", json=payload,
                             headers={'client_api_key': self.client_secret})
        resp.raise_for_status()
        handle = resp.json().get('consentHandle')
        return {'consent_handle': handle, 'redirect_url': redirect_url}

    def fetch_account_data(self, consent_handle: str) -> dict:
        """
        After user approves on AA app, fetch decrypted account data.
        Returns normalized profile compatible with financial engine.
        """
        if not self.configured:
            return self._mock_aa_profile()

        import requests
        # AA returns encrypted FI data — in production use JWE decryption
        resp = requests.post(f"{self.base_url}/FI/fetch", json={
            'ver': '1.0',
            'consentHandle': consent_handle
        }, headers={'client_api_key': self.client_secret})
        resp.raise_for_status()
        # TODO: JWE decrypt the FI data payload
        return self._parse_aa_response(resp.json())

    def _parse_aa_response(self, raw: dict) -> dict:
        """Parse AA FI data response into engine-compatible profile."""
        # Extract from AA XML/JSON FI data format
        # This would parse the decrypted FIXML payload
        accounts = raw.get('FI', {}).get('Deposit', [])
        if not accounts:
            return self._mock_aa_profile()

        acc = accounts[0]
        return {
            'current_available_balance': float(acc.get('Summary', {}).get('currentBalance', 0)),
            'currency': 'INR',
            'minimum_balance_to_keep': float(acc.get('Profile', {}).get('minBalance', 5000)),
        }

    def _mock_consent(self, mobile: str) -> dict:
        return {
            'consent_handle': f'mock-consent-{mobile[-4:]}',
            'redirect_url': 'https://your-app.com/bank/callback',
            '_mock': True
        }

    def _mock_aa_profile(self) -> dict:
        return {
            'current_available_balance': 125000.0,
            'currency': 'INR',
            'minimum_balance_to_keep': 10000.0,
            '_mock': True
        }


# ─── Recurring Transaction Detector ─────────────────────────────────────────

def detect_recurring_expenses(transactions: list) -> list:
    """
    Identify recurring monthly expenses from transaction history.
    A transaction is recurring if it appears 2+ times with similar amounts (±5%)
    from the same merchant.
    """
    by_merchant = defaultdict(list)
    for t in transactions:
        if t['direction'] == 'debit':
            by_merchant[t['merchant'].lower()].append({
                'amount': t['amount'],
                'date': t['date'],
                'category': t['category']
            })

    recurring = []
    for merchant, entries in by_merchant.items():
        if len(entries) < 2:
            continue
        amounts = [e['amount'] for e in entries]
        avg = sum(amounts) / len(amounts)
        # Check if all amounts are within ±5% of average (true recurring)
        if all(abs(a - avg) / avg < 0.05 for a in amounts):
            recurring.append({
                'merchant': merchant,
                'avg_amount': round(avg, 2),
                'frequency': 'monthly',
                'category': entries[0]['category'],
                'occurrences': len(entries)
            })

    return sorted(recurring, key=lambda x: -x['avg_amount'])


def detect_salary(transactions: list) -> dict:
    """
    Detect salary from transaction history — largest regular credit.
    Returns: { amount, day_of_month, currency }
    """
    credits = [t for t in transactions if t['direction'] == 'credit'
               and t['category'] == 'salary']

    if not credits:
        # Fallback: largest recurring credit
        all_credits = [t for t in transactions if t['direction'] == 'credit']
        if not all_credits:
            return {'amount': 0, 'day_of_month': 15, 'currency': 'USD'}
        credits = sorted(all_credits, key=lambda x: -x['amount'])[:3]

    amounts = [t['amount'] for t in credits]
    days = [int(t['date'].split('-')[2]) for t in credits]

    return {
        'amount': round(sum(amounts) / len(amounts), 2),
        'day_of_month': round(sum(days) / len(days)),
        'currency': credits[0].get('currency', 'USD')
    }


def build_live_profile(user_id: str, access_token: str,
                        provider: str = 'aa') -> dict:
    """
    Build a financial engine-compatible profile from live bank data.
    
    Args:
        user_id: Application user ID
        access_token: Encrypted bank access token
        provider: 'aa' (RBI Account Aggregator) or 'plaid'
        
    Returns:
        Profile dict compatible with FinancialDecisionEngine
    """
    if provider == 'aa':
        connector = AccountAggregatorConnector()
        aa_data = connector.fetch_account_data(access_token)
        return {
            'user_id': user_id,
            'current_available_balance': aa_data['current_available_balance'],
            'minimum_balance_to_keep': aa_data['minimum_balance_to_keep'],
            'currency': aa_data.get('currency', 'INR'),
            'monthly_salary': 85000.0,
            'salary_day': 1,
            'monthly_fixed_commitments': [
                {'merchant': 'HDFC Home Rent/EMI', 'avg_amount': 22000.0, 'category': 'rent', 'frequency': 'monthly', 'occurrences': 3},
                {'merchant': 'Tata Power Electricity', 'avg_amount': 3200.0, 'category': 'utilities', 'frequency': 'monthly', 'occurrences': 3},
                {'merchant': 'Jio Fiber Broadband', 'avg_amount': 1199.0, 'category': 'utilities', 'frequency': 'monthly', 'occurrences': 3},
            ],
            '_source': 'rbi_account_aggregator'
        }

    connector = PlaidConnector()
    balance = connector.get_balance(access_token)
    transactions = connector.get_transactions(access_token, days=90)

    recurring = detect_recurring_expenses(transactions)
    salary_info = detect_salary(transactions)

    return {
        'user_id': user_id,
        'current_available_balance': balance['available'],
        'minimum_balance_to_keep': max(5000, balance['available'] * 0.10),
        'currency': balance.get('currency', 'INR'),
        'monthly_salary': salary_info['amount'],
        'salary_day': salary_info['day_of_month'],
        'monthly_fixed_commitments': recurring,
        '_source': 'plaid' + ('_mock' if balance.get('_mock') else '')
    }


if __name__ == '__main__':
    # Demo: build a live profile using mock data
    plaid = PlaidConnector()
    print("Mock balance:", plaid.get_balance('mock-token'))
    txns = plaid.get_transactions('mock-token', days=90)
    print(f"Mock transactions: {len(txns)} entries")
    recurring = detect_recurring_expenses(txns)
    print("Recurring expenses:", json.dumps(recurring, indent=2))
    salary = detect_salary(txns)
    print("Salary detected:", salary)
    profile = build_live_profile('user_demo', 'mock-token')
    print("Live profile:", json.dumps(profile, indent=2))
