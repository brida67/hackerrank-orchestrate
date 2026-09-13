import os, csv
from solve import *

sample_raw = read_csv(os.path.join(DATA_DIR, 'sample_requests.csv'))

for s in sample_raw:
    rid = s['request_id']
    uid = s['user_id']
    r = evaluate(s)
    
    gs = s['affordability_status']
    gm = s['recommended_payment_method']
    ga = safe_float(s['amount_safe_to_pay'])
    gp = s['payment_plan']
    ge = s['earliest_date_for_full_payment']
    gc = s['spending_changes_needed']
    
    ps = r['affordability_status']
    pm = r['recommended_payment_method']
    pa = r['amount_safe_to_pay']
    pp = r['payment_plan']
    pe = r['earliest_date_for_full_payment']
    pc = r['spending_changes_needed']
    
    if ps != gs or pm != gm or abs(pa - ga) > 1:
        print(f"=== {rid} ({uid}) ===")
        print(f"  GT: stat={gs}, meth={gm}, safe={ga}, plan={gp}, ef={ge}, chg={gc}")
        print(f"  PR: stat={ps}, meth={pm}, safe={pa}, plan={pp}, ef={pe}, chg={pc}")
        prof = profiles[uid]
        print(f"  Profile: init_bal={prof['current_available_balance']}, min_bal={prof['minimum_balance_to_keep']}, methods={prof['payment_methods_user_will_consider']}")
        traj = simulate(uid, s['request_date'])
        print(f"  Salary detected: amt={traj['sal_amt']}, dates={traj['sal_dates']}")
        print(f"  Streams: {len(traj['streams'])}")
        for st in traj['streams']:
            print(f"    stream {st['eid']}: cat={st['cat']}, amt={st['amt']}, type={st['type']}, last={st.get('last_date')}, flex={st.get('flex')}, min={st.get('mina')}")
        print(f"  Traj min bal: {min(traj['bals'])} at date {traj['dates'][traj['bals'].index(min(traj['bals']))]}")
        print(f"  First 10 traj: {list(zip([d.strftime('%Y-%m-%d') for d in traj['dates'][:10]], [round(b, 2) for b in traj['bals'][:10]]))}")
        user_msgs = msgs_by_user.get(uid, [])
        for m in user_msgs:
            print(f"  Msg: {m.get('message_text')}")
        print()
