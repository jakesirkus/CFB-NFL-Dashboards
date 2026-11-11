"""Add per-game offensive-line / defensive-line aggregates from PFF player data to every box score (box[team]['line']).
Reads the weekly cache written by pff_fetch.py (build/pff/raw/{lg}/wN_*.json). Each PFF game is matched to a dashboard game
(same teams, final score, week within +-1); PFF franchises are mapped to dashboard team names by those matches.
OL = T/G/C, DL = DI/ED.  Per team-game:
  olPbGrade  snap-weighted PFF pass-block grade      olPbSnaps  OL pass-block snaps
  olPbe      pass-blocking efficiency = 100 - 100*(sacks + 0.75*(hits+hurries)) / pass-block snaps   } SCHEME-ADJUSTED (Nov 11 2026):
  olPressPct pressures allowed per 100 OL pass-block snaps                                    } rate on true pass sets and on
             all other pass blocks (screens, play action, quick throws), re-weighted to the league-average true-pass-set share
             (so an offense that hides its line with quick game is judged as if it ran a normal mix; olPbeRaw / olPressPctRaw =
             unadjusted, olTpsShare = this game's true-pass-set share of OL pass-block snaps).  Tested on 2026 weeks 1-9/10: removes
             the scheme bias (CFB r with true-pass-set share 0.27 -> -0.01) and NFL first-half -> second-half r 0.24 -> 0.30.
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
        for f in ('sacks_allowed', 'hits_allowed', 'hurries_allowed', 'pressures_allowed'): A[f] += n(r.get(f)); A['tps_' + f] += n(r.get('true_pass_set_' + f))
        A['tpsSn'] += n(r.get('true_pass_set_snap_counts_pass_block'))
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
# league-average true-pass-set share of OL pass-block snaps (matched team-games only)
_m = [A for k, A in agg.items() if k in GAME and A['pbSn'] > 0]
LS = sum(A['tpsSn'] for A in _m) / max(1.0, sum(A['pbSn'] for A in _m))
def mixed(A, bad):
    # bad(prefix) -> count on those snaps; returns per-snap rate re-weighted to the league true-pass-set share (None: fall back to raw)
    ts, sn = A['tpsSn'], A['pbSn']
    if ts <= 0 or ts >= sn: return None
    return LS * bad('tps_') / ts + (1 - LS) * (bad('') - bad('tps_')) / (sn - ts)
for v in D['boxscores'].values():
    for t in v:
        if t != 'driveChart': v[t].pop('line', None)
put = 0; ours_fbs = set(); partial = []
for (w, f), A in agg.items():
    if (w, f) not in GAME: continue
    gk, team = GAME[(w, f)]; box = D['boxscores'][gk][team]
    L = {'olPbSnaps': A['pbSn'], 'olRbSnaps': A['rbSn'], 'dlPrSnaps': A['prSn'], 'dlRunSnaps': A['rdSn'], 'passPlays': A['passPlays'],
         'olPressures': A['pressures_allowed'], 'olSacks': A['sacks_allowed'], 'dlPressures': A['press']}
    if A['pbGs']: L['olPbGrade'] = r3(A['pbG'] / A['pbGs'])
    if A['pbSn']:
        pbe_bad = lambda q: A[q + 'sacks_allowed'] + 0.75 * (A[q + 'hits_allowed'] + A[q + 'hurries_allowed'])
        L['olPbeRaw'] = r3(100 - 100 * pbe_bad('') / A['pbSn'])
        L['olPressPctRaw'] = r3(100 * A['pressures_allowed'] / A['pbSn'])
        L['olTpsShare'] = r3(100 * A['tpsSn'] / A['pbSn'])
        mp, mb = mixed(A, lambda q: A[q + 'pressures_allowed']), mixed(A, pbe_bad)
        L['olPressPct'] = r3(100 * mp) if mp is not None else L['olPressPctRaw']
        L['olPbe'] = r3(100 - 100 * mb) if mb is not None else L['olPbeRaw']
    if A['rbGs']: L['olRbGrade'] = r3(A['rbG'] / A['rbGs'])
    if A['prGs']: L['dlPrGrade'] = r3(A['prG'] / A['prGs'])
    if A['opps']: L['dlPrwr'] = r3(100 * A['wins'] / A['opps'])
    if A['prSn']: L['dlPressPct'] = r3(100 * A['press'] / A['prSn'])
    if A['rdGs']: L['dlRdGrade'] = r3(A['rdG'] / A['rdGs'])
    if A['stopOpp']: L['dlStopPct'] = r3(100 * A['stops'] / A['stopOpp'])
    # completeness guard: PFF posts games before charting is finished (e.g. Pitt-GT wk9 had 5 GT OL rows with 1 snap each).
    # Keep the OL half only if OL snaps >= 60% of 5 x this team's dropbacks / runs, the DL half only if DL snaps >= 60% of
    # 3.5 x the opponent's dropbacks / runs; otherwise that half is dropped until a later pff_fetch.py fills it in.
    ob = next(D['boxscores'][gk][x] for x in D['boxscores'][gk] if x not in ('driveChart', team))
    def need(bx): r = bx['rushing']['rushAtt']; return bx['production']['scrimPlays'] - r, r
    db, ra = need(box); odb, ora = need(ob)
    if A['pbSn'] < 0.6 * 5 * db or A['rbSn'] < 0.6 * 5 * ra:
        L = {k: v for k, v in L.items() if not k.startswith('ol')}; partial.append(f'{gk}:{team} OL')
    if A['prSn'] < 0.6 * 3.5 * odb or A['rdSn'] < 0.6 * 3.5 * ora:
        L = {k: v for k, v in L.items() if not k.startswith('dl')}; partial.append(f'{gk}:{team} DL')
    box['line'] = L; put += 1
# coverage report: team-games of dashboard teams with / without PFF line data
tot = miss = 0; missing = []
for gk, v in D['boxscores'].items():
    for t in v:
        if t == 'driveChart' or t not in D['teams']: continue
        tot += 1
        if 'line' not in v[t]: miss += 1; missing.append(f'{gk}:{t}')
D['meta']['lineStats'] = {'source': 'PFF player grades/charting (OL = T/G/C, DL = DI/ED), aggregated per game',
                          'olSchemeAdjusted': {'stats': ['olPressPct', 'olPbe'], 'leagueTruePassSetShare': round(100 * LS, 1)},
                          'weeks': weeks, 'teamGames': tot, 'covered': tot - miss}
open(DST, 'w').write(s[:a0] + json.dumps(D, separators=(',', ':'), ensure_ascii=False, allow_nan=False).replace('</', '<\\/') + s[b0:])
print(f'{LG}: league true-pass-set share {100 * LS:.1f}%; PFF line data on {put} team-games; dashboard-team games covered {tot - miss}/{tot}; franchises mapped {len(FID)}')
if partial: print('  PFF charting incomplete (dropped):', ', '.join(partial))
if missing: print('  missing:', ', '.join(missing[:40]) + (' ...' if len(missing) > 40 else ''))
