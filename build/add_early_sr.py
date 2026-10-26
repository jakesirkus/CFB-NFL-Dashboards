"""Early-down (1st & 2nd) success rate, passes and rushes combined, for every box score and every quarter/half split.
Derived from the stored early-down counts and rates (earlyPass/earlyRush x earlyPassSuccessRate/earlyRushSuccessRate,
which recover the success counts exactly). Adds
  overall.earlySuccessRate      {value (3 dp, like successRate), pct (percentile within that split, build convention)}
  situational.earlySuccessRate  value (1 dp)
Idempotent (always recomputes). Run after the boxes are final (after add_ppo / before add_xpts is fine).
usage: add_early_sr.py cfb OUT_DIR          (OUT_DIR/index.html + OUT_DIR/periods/*.json)
       add_early_sr.py nfl IN.html OUT.html (splits live inside each box as box['periods'])"""
import sys, json, glob, numpy as np
TAG = '<script id="dashboard-data" type="application/json">'
LG = sys.argv[1]
if LG == 'cfb': SRC = DST = sys.argv[2] + '/index.html'
else: SRC, DST = sys.argv[2], sys.argv[3]
s = open(SRC).read(); a = s.index(TAG) + len(TAG); b = s.index('</script>', a); D = json.loads(s[a:b])

def V(x): return x['value'] if isinstance(x, dict) and 'value' in x else x
def esr(bx):
    st = bx.get('situational') or {}; n = succ = 0
    for side in ('Pass', 'Rush'):
        c = V(st.get('early' + side)); r = V(st.get('early' + side + 'SuccessRate'))
        if not c: continue
        n += c; succ += round(c * (r or 0) / 100)
    return (100.0 * succ / n) if n else None

# collect every team-box per split
splits = {}                                   # split -> list of team-box dicts
for gk, v in D['boxscores'].items():
    for t, bx in v.items():
        if t == 'driveChart': continue
        splits.setdefault('full', []).append(bx)
        for sp, pb in (bx.get('periods') or {}).items(): splits.setdefault(sp, []).append(pb)
shards = {}
if LG == 'cfb':
    for f in glob.glob(sys.argv[2] + '/periods/*.json'):
        d = json.load(open(f)); shards[f] = d
        for gk, per in d.items():
            for sp, teams in per.items():
                for t, pb in teams.items(): splits.setdefault(sp, []).append(pb)
n = 0
for sp, boxes in splits.items():
    vals = [(bx, esr(bx)) for bx in boxes]
    pool = np.sort(np.array([x for _, x in vals if x is not None]))
    for bx, x in vals:
        pct = None if x is None or not len(pool) else round(float(100 * np.searchsorted(pool, x, side='right') / len(pool)), 1)
        ov = bx.setdefault('overall', {})
        new = {}
        for k, val in ov.items():               # keep it right after successRate in the stored order
            if k == 'earlySuccessRate': continue
            new[k] = val
            if k == 'successRate': new['earlySuccessRate'] = {'value': None if x is None else round(x, 3), 'pct': pct}
        if 'earlySuccessRate' not in new: new['earlySuccessRate'] = {'value': None if x is None else round(x, 3), 'pct': pct}
        bx['overall'] = new
        bx.setdefault('situational', {})['earlySuccessRate'] = None if x is None else round(x, 1)
        n += 1
js = json.dumps(D, separators=(',', ':'), ensure_ascii=False, allow_nan=False).replace('</', '<\\/')
open(DST, 'w').write(s[:a] + js + s[b:])
for f, d in shards.items(): json.dump(d, open(f, 'w'), separators=(',', ':'))
print(f'{LG} early-down success rate: {n} team-boxes across {len(splits)} splits ({", ".join(sorted(splits))})')
