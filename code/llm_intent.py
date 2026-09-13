"""
llm_intent.py — Natural Language Intent Extractor
Extracts structured financial request details from free-text user messages.
Uses Google Gemini (primary) → OpenAI (optional fallback) → regex fallback.
"""

import os
import re
import json
from datetime import date, timedelta
from typing import Optional

# Load .env so GEMINI_API_KEY / OPENAI_API_KEY are available
try:
    from dotenv import load_dotenv
    _env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    load_dotenv(_env_path)
except ImportError:
    pass  # python-dotenv not installed; rely on OS environment

# ─── Google Gemini client (primary) ────────────────────────────────────────
try:
    from google import genai as _google_genai
    _GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
    _HAS_GEMINI = bool(_GEMINI_API_KEY and _GEMINI_API_KEY != 'your_gemini_api_key_here')
    if _HAS_GEMINI:
        _gemini_client = _google_genai.Client(api_key=_GEMINI_API_KEY)
    else:
        _gemini_client = None
except ImportError:
    _HAS_GEMINI = False
    _gemini_client = None

# ─── OpenAI client (optional fallback) ─────────────────────────────────────
try:
    from openai import OpenAI
    _OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
    _HAS_OPENAI = bool(_OPENAI_API_KEY)
    _openai_client = OpenAI(api_key=_OPENAI_API_KEY) if _HAS_OPENAI else None
except ImportError:
    _openai_client = None
    _HAS_OPENAI = False

INTENT_SYSTEM_PROMPT = """You are a financial intent extractor for a personal finance AI assistant.
Given a user message, extract the following and return ONLY valid JSON:
{
  "amount": <float or null>,
  "currency": <"INR"|"USD"|"EUR"|"IDR"|"ZAR"|"GBP"|null>,
  "item_description": <string describing what they want to buy/pay>,
  "desired_date": <"YYYY-MM-DD" or null if not specified>,
  "allows_partial": <boolean, true if they'd accept partial payment>,
  "request_type": <"purchase"|"bill_payment"|"loan"|"travel"|"subscription"|"other">,
  "follow_up_needed": <boolean, true if amount or key info is missing>,
  "follow_up_question": <string or null — the question to ask the user>
}

Rules:
- If amount is missing or vague, set follow_up_needed=true and ask for it
- If currency is not mentioned, infer from context (₹/Rs = INR, $ = USD, € = EUR, Rp = IDR, R = ZAR)
- Convert written numbers: "50k" = 50000, "1.5 lakh" = 150000, "2 crore" = 20000000
- For dates: "this weekend" = next Saturday, "next month" = 1st of next month, "Diwali 2024" = 2024-11-01
- Always be helpful — if you can make a reasonable inference, do it rather than asking
"""

# Currency symbol / keyword patterns for regex fallback
CURRENCY_PATTERNS = [
    (r'₹|rs\.?|inr|rupee', 'INR'),
    (r'\$(?!idr)|usd|dollar', 'USD'),
    (r'€|eur|euro', 'EUR'),
    (r'rp\.?|idr|rupiah', 'IDR'),
    (r'\bzar\b|rand', 'ZAR'),
    (r'£|gbp|pound', 'GBP'),
]

AMOUNT_PATTERNS = [
    r'(\d+(?:\.\d+)?)\s*(?:crore|cr)',   # crore
    r'(\d+(?:\.\d+)?)\s*(?:lakh|lac|l)', # lakh
    r'(\d+(?:\.\d+)?)\s*k\b',            # k = 1000
    r'(\d[\d,]*(?:\.\d+)?)',              # plain number
]

REQUEST_TYPE_KEYWORDS = {
    'purchase': ['buy', 'purchase', 'get', 'afford', 'order', 'spend on'],
    'bill_payment': ['bill', 'invoice', 'electricity', 'water', 'phone', 'utility', 'emi', 'loan'],
    'travel': ['trip', 'vacation', 'flight', 'hotel', 'travel', 'holiday'],
    'subscription': ['subscription', 'membership', 'netflix', 'spotify', 'plan', 'renewal'],
}

FOLLOW_UP_TRIGGERS = [
    r'\bsomething\b', r'\bstuff\b', r'\bthings?\b',
    r'^(can i afford|should i buy|is it ok)\.?$',
    r'\bvague\b', r'\bexpensive\b'
]


def _parse_amount(text: str) -> Optional[float]:
    """Extract numeric amount from text with multiplier support."""
    text_lower = text.lower().replace(',', '')
    
    # crore
    m = re.search(r'(\d+(?:\.\d+)?)\s*(?:crore|cr)\b', text_lower)
    if m:
        return float(m.group(1)) * 10_000_000

    # lakh
    m = re.search(r'(\d+(?:\.\d+)?)\s*(?:lakh|lac)\b', text_lower)
    if m:
        return float(m.group(1)) * 100_000

    # k
    m = re.search(r'(\d+(?:\.\d+)?)\s*k\b', text_lower)
    if m:
        return float(m.group(1)) * 1_000

    # plain number (with possible commas already stripped)
    m = re.search(r'(\d+(?:\.\d+)?)', text_lower)
    if m:
        return float(m.group(1))

    return None


def _parse_currency(text: str) -> Optional[str]:
    text_lower = text.lower()
    for pattern, currency in CURRENCY_PATTERNS:
        if re.search(pattern, text_lower):
            return currency
    return None


def _parse_date(text: str) -> Optional[str]:
    """Parse relative and absolute date references."""
    today = date.today()
    text_lower = text.lower()

    if any(k in text_lower for k in ['today', 'now', 'right now', 'immediately']):
        return str(today)
    if 'tomorrow' in text_lower:
        return str(today + timedelta(days=1))
    if 'this weekend' in text_lower:
        days_to_sat = (5 - today.weekday()) % 7 or 7
        return str(today + timedelta(days=days_to_sat))
    if 'next week' in text_lower:
        return str(today + timedelta(weeks=1))
    if 'next month' in text_lower:
        next_m = today.replace(day=1) + timedelta(days=32)
        return str(next_m.replace(day=1))
    if 'end of month' in text_lower or 'month end' in text_lower:
        next_m = today.replace(day=28) + timedelta(days=4)
        return str(next_m - timedelta(days=next_m.day))
    if 'diwali' in text_lower:
        return f"{today.year}-11-01"

    # ISO date
    m = re.search(r'\b(\d{4}-\d{2}-\d{2})\b', text)
    if m:
        return m.group(1)

    # DD/MM/YYYY or MM/DD/YYYY
    m = re.search(r'\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b', text)
    if m:
        return f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}"

    return None


def _detect_request_type(text: str) -> str:
    text_lower = text.lower()
    for rtype, keywords in REQUEST_TYPE_KEYWORDS.items():
        if any(k in text_lower for k in keywords):
            return rtype
    return 'purchase'


def _regex_extract(message: str) -> dict:
    """Fallback intent extraction using regex — no API key required."""
    amount = _parse_amount(message)
    currency = _parse_currency(message)
    desired_date = _parse_date(message)
    request_type = _detect_request_type(message)

    # Check if we need a follow-up
    follow_up_needed = amount is None
    follow_up_question = None
    if follow_up_needed:
        follow_up_question = "Could you tell me the amount you'd like to pay or spend?"

    # Best-effort item description: grab noun after buy/purchase/pay/afford
    item_desc = ''
    m = re.search(r'(?:buy|purchase|pay for|afford|get)\s+(?:an?\s+)?(.+?)(?:\s+for|\s+at|\s+this|\s+next|\?|$)',
                  message, re.IGNORECASE)
    if m:
        item_desc = m.group(1).strip()
    if not item_desc:
        item_desc = message[:60]

    return {
        "amount": amount,
        "currency": currency,
        "item_description": item_desc,
        "desired_date": desired_date,
        "allows_partial": True,
        "request_type": request_type,
        "follow_up_needed": follow_up_needed,
        "follow_up_question": follow_up_question
    }


def extract_intent(message: str, user_currency: str = "INR") -> dict:
    """
    Extract structured financial intent from a free-text user message.

    Priority:
      1. Google Gemini (if GEMINI_API_KEY is set in .env)
      2. OpenAI       (if OPENAI_API_KEY is set in .env)
      3. Regex fallback (always available, no key required)

    Args:
        message: User's natural language message
        user_currency: Default currency hint from user profile

    Returns:
        dict with keys: amount, currency, item_description, desired_date,
                        allows_partial, request_type, follow_up_needed, follow_up_question
    """
    system_prompt = INTENT_SYSTEM_PROMPT
    if user_currency:
        system_prompt += f"\n\nDefault currency context: {user_currency}. Always assume amounts are in {user_currency} unless the user explicitly mentions another currency."

    # ── 1. Try Gemini ────────────────────────────────────────────────────────
    if _HAS_GEMINI and _gemini_client:
        try:
            full_prompt = (
                system_prompt +
                "\n\nUser message: " + message +
                "\n\nReturn ONLY valid JSON, no markdown fences."
            )
            response = _gemini_client.models.generate_content(
                model='gemini-2.0-flash-lite',
                contents=full_prompt
            )
            raw = response.text.strip()
            # Strip optional markdown fences Gemini sometimes adds
            if raw.startswith('```'):
                raw = re.sub(r'^```(?:json)?\s*', '', raw)
                raw = re.sub(r'\s*```$', '', raw)
            result = json.loads(raw)
            result['_source'] = 'gemini'
            return result
        except Exception:
            # Fall through to OpenAI or regex
            pass

    # ── 2. Try OpenAI ────────────────────────────────────────────────────────
    if _HAS_OPENAI and _openai_client:
        try:
            resp = _openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message}
                ],
                response_format={"type": "json_object"},
                temperature=0,
                max_tokens=300
            )
            result = json.loads(resp.choices[0].message.content)
            result['_source'] = 'openai'
            return result
        except Exception as e:
            pass

    # ── 3. Regex fallback ────────────────────────────────────────────────────
    result = _regex_extract(message)
    result['_source'] = 'regex (no LLM key configured)'
    return result


def format_decision_reply(decision: dict, intent: dict) -> str:
    """
    Format a financial engine decision into a friendly conversational reply.
    
    Args:
        decision: Output from financial_engine.evaluate_request()
        intent: Extracted intent from extract_intent()
        
    Returns:
        Human-readable reply string
    """
    status = decision.get('affordability_status', 'unknown')
    explanation = decision.get('decision_explanation', '')
    method = decision.get('recommended_payment_method', '')
    plan = decision.get('payment_plan', 'none')
    changes = decision.get('spending_changes_needed', 'none')
    safe_amount = decision.get('amount_safe_to_pay', 0)
    earliest = decision.get('earliest_date_for_full_payment', '')

    status_labels = {
        'affordable_now':        ('✅ Good news!', 'You can go ahead'),
        'affordable_with_plan':  ('⚠️ Yes, with a plan', 'Here\'s how to do it safely'),
        'affordable_later':      ('🕐 Not yet, but soon', 'Wait a bit and you\'ll be fine'),
        'not_affordable':        ('❌ Not recommended', 'This would strain your finances'),
    }
    header, sub = status_labels.get(status, ('🤔 Decision', 'Here\'s the analysis'))

    reply = f"{header}\n{explanation}"

    if method == 'installments' and plan and plan != 'none':
        parts = plan.split('|')
        reply += f"\n\n📅 *Payment schedule:*"
        for p in parts:
            p_date, p_amt = p.split(':')
            reply += f"\n  • {p_date}: {float(p_amt):,.2f}"

    if method == 'wait' and earliest:
        reply += f"\n\n📆 Come back on *{earliest}* and you'll be able to pay in full."

    if changes and changes != 'none':
        reply += f"\n\n💡 *Tip:* {changes}"

    return reply


if __name__ == '__main__':
    # Quick self-test
    test_messages = [
        "Can I buy a PS5 for ₹50,000 this weekend?",
        "Should I pay my electricity bill of €120?",
        "Can I afford a new fridge next month?",
        "I want to buy something",
        "Can I spend $2500 on a MacBook Pro today?",
        "Is it safe to book a flight for 1.5 lakh rupees in November?",
    ]
    for msg in test_messages:
        result = extract_intent(msg)
        src = result.pop('_source', 'unknown')
        print(f"\n[{src}] '{msg}'")
        print(json.dumps(result, indent=2))
