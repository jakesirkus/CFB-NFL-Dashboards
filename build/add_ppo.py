"""Add season Points per Opportunity (offense + defense) to a CFB or NFL dashboard page:
team fields ppo / ppoAllowed (+ trips/points), radar percentiles ('ppo' spoke), ranks, and the
leaderboard columns. Season totals come from the per-game box-score 'opportunities' sections
(a scoring opportunity = a drive with a play inside the opponent's 30), so they always match the box scores.
Idempotent: safe to run on every build.
usage: add_ppo.py in.html out.html [--data-only|--js-only]"""
import sys, json, re
import numpy as np
src, dst = sys.argv[1], sys.argv[2]; mode = sys.argv[3] if len(sys.argv) > 3 else ''
s = open(src).read()
T = '<script id="dashboard-data" type="application/json">'
a = s.index(T) + len(T); b = s.index('</script>', a)
D = json.loads(s[a:b]); NFL = D.get('meta', {}).get('league') == 'NFL'

if mode != '--js-only':
    tot = {t: [0, 0, 0, 0] for t in D['teams']}
    for gk, v in D['boxscores'].items():
        for t, bx in v.items():
            if t not in tot or not isinstance(bx, dict) or 'opportunities' not in bx: continue
            o = bx['opportunities']
            tot[t][0] += o.get('trips', 0) or 0; tot[t][1] += o.get('points', 0) or 0
            tot[t][2] += o.get('tripsAllowed', 0) or 0; tot[t][3] += o.get('pointsAllowed', 0) or 0
    teams = sorted(D['teams'])
    off = {t: (tot[t][1] / tot[t][0] if tot[t][0] else None) for t in teams}
    dfn = {t: (tot[t][3] / tot[t][2] if tot[t][2] else None) for t in teams}
    def pcts(vals, high_good):
        ok = [t for t in teams if vals[t] is not None]; arr = np.array([vals[t] for t in ok]); n = len(arr); out = {}
        for t in ok:
            v = vals[t]
            if NFL:   # same method as the NFL radar: (average rank - 1) / (n - 1)
                below = (arr < v).sum() if high_good else (arr > v).sum(); ties = (arr == v).sum()
                out[t] = round(100 * (below + (ties - 1) / 2) / (n - 1), 1)
            else:     # same method as the CFB radar: share of teams this one is at least as good as
                out[t] = round(100 * ((arr <= v).sum() if high_good else (arr >= v).sum()) / n, 1)
        return out
    po, pd_ = pcts(off, True), pcts(dfn, False)
    def ranks(vals, high_good):   # 'min' method, like the other ranks
        ok = [t for t in teams if vals[t] is not None]
        return {t: 1 + sum(1 for u in ok if (vals[u] > vals[t] if high_good else vals[u] < vals[t])) for t in ok}
    ro, rd = ranks(off, True), ranks(dfn, False)
    for t in teams:
        x = D['teams'][t]
        x['oppTrips'], x['oppPoints'], x['oppTripsAllowed'], x['oppPointsAllowed'] = tot[t]
        x['ppo'] = None if off[t] is None else round(off[t], 2)
        x['ppoAllowed'] = None if dfn[t] is None else round(dfn[t], 2)
        r = x.setdefault('radar', {})
        r.setdefault('off', {})['ppo'] = po.get(t); r.setdefault('offRaw', {})['ppo'] = x['ppo']
        r.setdefault('def', {})['ppo'] = pd_.get(t); r.setdefault('defRaw', {})['ppo'] = x['ppoAllowed']
        x.setdefault('ranks', {})['ppo'] = ro.get(t); x['ranks']['ppoAllowed'] = rd.get(t)
    s = s[:a] + json.dumps(D, separators=(',', ':'), ensure_ascii=False, allow_nan=False).replace('</', '<\\/') + s[b:]

if mode != '--data-only':
    # radar spoke right after Opportunity %
    if "'ppo'" not in s[s.index('var RADAR_METRICS'):s.index('var RADAR_METRICS') + 600]:
        s = s.replace("'opportunityPct',", "'opportunityPct','ppo',", 1)
        s = s.replace("opportunityPct:'Opportunity %',", "opportunityPct:'Opportunity %', ppo:'Points/Opp',", 1)
    # leaderboard columns after Series Conv % Allowed
    if "key:'ppoOff'" not in s:
        m = re.search(r"(\n(\s*)\{ key:'seriesD',[^\n]*\n)", s)
        ind = m.group(2)
        add = (f"{ind}{{ key:'ppoOff', label:'Pts/Opp (Off)', type:'num', decimals:2, get:function(t){{ return t.ppo; }} }},\n"
               f"{ind}{{ key:'ppoDef', label:'Pts/Opp (Def)', type:'num', decimals:2, get:function(t){{ return t.ppoAllowed; }}, asc:true }},\n")
        s = s[:m.end()] + add + s[m.end():]
    assert "'opportunityPct','ppo'" in s and "key:'ppoOff'" in s and "ppo:'Points/Opp'" in s
open(dst, 'w').write(s)
if mode != '--js-only':
    best = sorted([t for t in D['teams'] if D['teams'][t]['ppo'] is not None], key=lambda t: -D['teams'][t]['ppo'])
    print('teams', len(D['teams']), '| top PPO', [(t, D['teams'][t]['ppo'], D['teams'][t]['oppTrips']) for t in best[:3]],
          '| best PPO allowed', sorted([(D['teams'][t]['ppoAllowed'], t) for t in D['teams'] if D['teams'][t]['ppoAllowed'] is not None])[:3])
