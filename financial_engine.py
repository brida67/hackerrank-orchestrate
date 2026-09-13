"""
Root-level re-export for code.financial_engine.
Allows both `import financial_engine` and `from code.financial_engine import ...`
to resolve cleanly across all IDEs, linters, and scripts.
"""

from code.financial_engine import (
    IMAGE_AMOUNTS,
    TO_INR_RATES,
    to_inr,
    from_inr,
    format_human_date,
    FinancialDecisionEngine,
)

__all__ = [
    'IMAGE_AMOUNTS',
    'TO_INR_RATES',
    'to_inr',
    'from_inr',
    'format_human_date',
    'FinancialDecisionEngine',
]
