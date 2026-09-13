# Let's find which exact combination sums to 539.10
# Fixed known items:
# Rent = 254.10
# Water/power = 51.86
# Vehicle insurance = 26.00
# Family streaming = 19.00
# Shared storage = 5.00
# Total of monthly knowns = 355.96
# Target = 539.10
# Remainder = 539.10 - 355.96 = 183.14

# Let's see: what items make up 183.14?
# In Dec 2025:
# Weekly Groceries: ~32.69
# Weekly Transport: ~32.90
# Weekly/biweekly Dining: ~48.36
# Monthly Entertainment: ~38.33
# Shopping: ~39.88

items = [
    ('groceries_1', 32.69),
    ('groceries_2', 32.69),
    ('transport_1', 32.90),
    ('transport_2', 32.90),
    ('transport_3', 32.90),
    ('dining_1', 48.36),
    ('dining_2', 48.36),
    ('entertainment', 38.33),
    ('shopping', 39.88),
]

import itertools
for k in range(1, len(items)+1):
    for combo in itertools.combinations(items, k):
        s = sum(x[1] for x in combo)
        if abs(s - 183.14) < 1.0:
            print("MATCH:", [x[0] for x in combo], "Sum:", s)
