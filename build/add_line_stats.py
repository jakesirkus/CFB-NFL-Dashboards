"""Add per-game offensive-line / defensive-line aggregates from PFF player data to every box score (box[team]['line']).
Reads the weekly cache written by pff_fetch.py (build/pff/raw/{lg}/wN_*.json). Each PFF game is matched to a dashboard game
(same teams, final score, week within +-1); PFF franchises are mapped to dashboard team names by those matches.
OL = T/G/C, DL = DI/ED.  Per team-game:
  olPbGrade  snap-weighted PFF pass-block grade      olPbSnaps  OL pass-block snaps
  olPbe      pass-blocking efficiency = 100 - 100*(sacks + 0.75*(hits+hurries)) / pass-block snaps
  olPressPct pressures allowed per 100 OL pass-block snaps
  olRbGrade  snap-weighted run-block grade           olRbSnaps  OL run-block snaps
  dlPrGrade  snap-weighted pass-rush grade           dlPrSnaps  DL pass-rush snaps
  dlPrwr     pass-rush win rate (wins / opportunities)
  dlPressPct pressures per 100 DL pass-rush snaps
  dlRdGrade  snap-weighted run-defense grade         dlRunSnaps DL run-defense snaps
  dlStopPct  run stops / run-stop opportunities
Idempotent (replaces 'line'). Games with no PFF match keep no 'line' (the stats just skip them).
usage: add_line_stats.py nfl|cfb IN.html OUT.html"""
import sys, os, json, glob, re, difflib
from collections import defaultdict
HERE = os.path.dirname(os.path.abspath(__file__))
LG, SRC, DST = sys.argv[1:4]
TAG = '<script id="dashboard-data" type="application/json">'
s = open(SRC).read(); a0 = s.index(TAG) + len(TAG); b0 = s.index('</script>', a0); D = json.loads(s[a0:b0])
RAW = os.path.join(HERE, 'pff', 'raw', LG)
weeks = sorted({int(re.match(r'w(\d+)_', os.path.basename(p)).group(1)) for p in glob.glob(os.path.join(RAW, 'w*_games.json'))})
if not weeks:
    print(f'WARNING {LG}: no PFF cache in {RAW} - run pff_fetch.py; line stats skipped'); open(DST, 'w').write(s); sys.exit(0)
def load(w, n):
    p = os.path.join(RAW, f'w{w}_{n}.json'); return json.load(open(p)) if os.path.exists(p) else []

# ---------- our games: (week, home, away, home score, away score) ----------
OURS = []
for gk, v in D['boxscores'].items():
    ts = [t for t in v if t != 'driveChart']
    if len(ts) != 2: continue
    h = next((t for t in ts if v[t]['meta']['home']), ts[0]); aw = ts[1] if h == ts[0] else ts[0]
    OURS.append((gk, v[h]['meta']['week'], h, aw, v[h]['meta']['ts'], v[h]['meta']['os']))
def norm(x): return re.sub(r'[^a-z ]', '', x.lower().replace('state', 'st').replace('&', '').replace('university', ''))
def sim(pt, ours):
    names = [pt.get('city') or '', (pt.get('city') or '') + ' ' + (pt.get('nickname') or ''), pt.get('nickname') or '', pt.get('abbreviation') or '']
    return max(difflib.SequenceMatcher(None, norm(n), norm(ours)).ratio() for n in names if n)

# ---------- match PFF games to ours ----------
votes = defaultdict(lambda: defaultdict(float)); cand = []
for w in weeks:
    for g in load(w, 'games'):
        sc = g.get('score') or {}; hs, as_ = sc.get('home_team'), sc.get('away_team')
        if hs is None or as_ is None: continue
        for (gk, ow, h, aw, ths, tas) in OURS:
            if abs(ow - w) > 1: continue
            for flip in (False, True):          # neutral sites: home/away may be labelled differently
                H, A, HS, AS = (h, aw, ths, tas) if not flip else (aw, h, tas, ths)
                if (HS, AS) != (hs, as_): continue
                sc_ = sim(g['home_team'], H) + sim(g['away_team'], A)
                if sc_ < 1.0: continue
                cand.append((sc_, w, g['home_franchise_id'], g['away_franchise_id'], gk, H, A))
                votes[g['home_franchise_id']][H] += sc_; votes[g['away_franchise_id']][A] += sc_
FID = {}
for f, vs in votes.items():
    t = max(vs, key=vs.get); FID[f] = t
dup = defaultdict(list)
for f, t in FID.items(): dup[t].append(f)
for t, fs in dup.items():                    # one team <- several franchises: keep the strongest vote
    if len(fs) > 1:
        keep = max(fs, key=lambda f: votes[f][t])
        for f in fs:
            if f != keep: del FID[f]
GAME = {}                                     # (pff week, franchise) -> (our gk, our team)
for sc_, w, hf, af, gk, H, A in sorted(cand, reverse=True):
    if FID.get(hf) == H and FID.get(af) == A:
        GAME.setdefault((w, hf), (gk, H)); GAME.setdefault((w, af), (gk, A))

# ---------- aggregate players per (week, franchise) ----------
OL, DL = {'T', 'G', 'C'}, {'DI', 'ED'}
def n(x): return float(x or 0)
agg = defaultdict(lambda: defaultdict(float))
for w in weeks:
    seen = defaultdict(int)
    for r in load(w, 'games'):
        seen[r['home_franchise_id']] += 1; seen[r['away_franchise_id']] += 1
    for r in load(w, 'pass_blocking'):
        if r.get('franchise_id') is None: continue
        k = (w, r['franchise_id']); A = agg[k]
        A['passPlays'] = max(A['passPlays'], n(r.get('snap_counts_pass_play')))
        if r.get('position') not in OL: continue
        sn = n(r.get('snap_counts_pass_block')); A['pbSn'] += sn
        if r.get('grades_pass_block') is not None and sn: A['pbG'] += sn * r['grades_pass_block']; A['pbGs'] += sn
        for f in ('sacks_allowed', 'hits_allowed', 'hurries_allowed', 'pressures_allowed'): A[f] += n(r.get(f))
    for r in load(w, 'run_blocking'):
        if r.get('position') not in OL or r.get('franchise_id') is None: continue
        A = agg[(w, r['franchise_id'])]; sn = n(r.get('snap_counts_run_block')); A['rbSn'] += sn
        if r.get('grades_run_block') is not None and sn: A['rbG'] += sn * r['grades_run_block']; A['rbGs'] += sn
    for r in load(w, 'pass_rush'):
        if r.get('position') not in DL or r.get('franchise_id') is None: continue
        A = agg[(w, r['franchise_id'])]; sn = n(r.get('snap_counts_pass_rush')); A['prSn'] += sn
        if r.get('grades_pass_rush_defense') is not None and sn: A['prG'] += sn * r['grades_pass_rush_defense']; A['prGs'] += sn
        A['wins'] += n(r.get('pass_rush_wins')); A['opps'] += n(r.get('pass_rush_opp')); A['press'] += n(r.get('total_pressures'))
    for r in load(w, 'run_defense'):
        if r.get('position') not in DL or r.get('franchise_id') is None: continue
        A = agg[(w, r['franchise_id'])]; sn = n(r.get('snap_counts_run')); A['rdSn'] += sn
        if r.get('grades_run_defense') is not None and sn: A['rdG'] += sn * r['grades_run_defense']; A['rdGs'] += sn
        A['stops'] += n(r.get('stops')); A['stopOpp'] += n(r.get('run_stop_opp'))
    for k in [k for k in agg if k[0] == w and seen.get(k[1], 0) > 1]: del agg[k]     # two games in one PFF week: ambiguous, skip

def r3(x): return None if x is None else round(x, 3)
for v in D['boxscores'].values():
    for t in v:
        if t != 'driveChart': v[t].pop('line', None)
put = 0; ours_fbs = set()
for (w, f), A in agg.items():
    if (w, f) not in GAME: continue
    gk, team = GAME[(w, f)]; box = D['boxscores'][gk][team]
    L = {'olPbSnaps': A['pbSn'], 'olRbSnaps': A['rbSn'], 'dlPrSnaps': A['prSn'], 'dlRunSnaps': A['rdSn'], 'passPlays': A['passPlays'],
         'olPressures': A['pressures_allowed'], 'olSacks': A['sacks_allowed'], 'dlPressures': A['press']}
    if A['pbGs']: L['olPbGrade'] = r3(A['pbG'] / A['pbGs'])
    if A['pbSn']:
        L['olPbe'] = r3(100 - 100 * (A['sacks_allowed'] + 0.75 * (A['hits_allowed'] + A['hurries_allowed'])) / A['pbSn'])
        L['olPressPct'] = r3(100 * A['pressures_allowed'] / A['pbSn'])
    if A['rbGs']: L['olRbGrade'] = r3(A['rbG'] / A['rbGs'])
    if A['prGs']: L['dlPrGrade'] = r3(A['prG'] / A['prGs'])
    if A['opps']: L['dlPrwr'] = r3(100 * A['wins'] / A['opps'])
    if A['prSn']: L['dlPressPct'] = r3(100 * A['press'] / A['prSn'])
    if A['rdGs']: L['dlRdGrade'] = r3(A['rdG'] / A['rdGs'])
    if A['stopOpp']: L['dlStopPct'] = r3(100 * A['stops'] / A['stopOpp'])
    box['line'] = L; put += 1
# coverage report: team-games of dashboard teams with / without PFF line data
tot = miss = 0; missing = []
for gk, v in D['boxscores'].items():
    for t in v:
        if t == 'driveChart' or t not in D['teams']: continue
        tot += 1
        if 'line' not in v[t]: miss += 1; missing.append(f'{gk}:{t}')
D['meta']['lineStats'] = {'source': 'PFF player grades/charting (OL = T/G/C, DL = DI/ED), aggregated per game',
                          'weeks': weeks, 'teamGames': tot, 'covered': tot - miss}
open(DST, 'w').write(s[:a0] + json.dumps(D, separators=(',', ':'), ensure_ascii=False, allow_nan=False).replace('</', '<\\/') + s[b0:])
print(f'{LG}: PFF line data on {put} team-games; dashboard-team games covered {tot - miss}/{tot}; franchises mapped {len(FID)}')
if missing: print('  missing:', ', '.join(missing[:40]) + (' ...' if len(missing) > 40 else ''))
