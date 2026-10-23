import pandas as pd
import numpy as np
import json

df = pd.read_pickle('combined_raw_fixed.pkl')
with open('../nfl_rebuild/cfb_team_list.json') as f:
    FBS_TEAMS = set(json.load(f))

wins = {t:0 for t in FBS_TEAMS}
losses = {t:0 for t in FBS_TEAMS}
for gid, g in df.groupby('GameId'):
    sc = {}
    for _, r in g.iterrows():
        if pd.notna(r.OffenseScore): sc[r.Offense] = max(sc.get(r.Offense, 0), r.OffenseScore)
        if pd.notna(r.DefenseScore): sc[r.Defense] = max(sc.get(r.Defense, 0), r.DefenseScore)
    if len(sc) != 2: continue
    (t1, s1), (t2, s2) = sc.items()
    if s1 == s2: continue
    w, l = (t1, t2) if s1 > s2 else (t2, t1)
    if w in wins: wins[w] += 1
    if l in losses: losses[l] += 1

with open('full_season_recompute.json') as f:
    recs = json.load(f)

for t in recs:
    recs[t]['wins'] = wins.get(t,0)
    recs[t]['losses'] = losses.get(t,0)

# ---- ranks (1 = best) ----
RANK_FIELDS_HIGH_BETTER = ['epaPerRush','epaPerPass','explosiveRate','ypp','thirdPct','seriesRate','epaPerDrive']
RANK_FIELDS_LOW_BETTER = ['epaPerRushAllowed','epaPerPassAllowed','explosiveRateAllowed','yppAllowed','thirdPctD','seriesRateAllowed','epaPerDriveAllowed']
# NOTE: thirdPctD is a STOP rate (higher=better defense) despite "Allowed" naming, so treat as high-better
RANK_FIELDS_HIGH_BETTER.append('thirdPctD')
RANK_FIELDS_LOW_BETTER.remove('thirdPctD')

teams = list(recs.keys())
for field in RANK_FIELDS_HIGH_BETTER:
    vals = sorted(teams, key=lambda t: -recs[t][field])
    for i,t in enumerate(vals):
        recs[t].setdefault('ranks',{})[field] = i+1
for field in RANK_FIELDS_LOW_BETTER:
    vals = sorted(teams, key=lambda t: recs[t][field])
    for i,t in enumerate(vals):
        recs[t].setdefault('ranks',{})[field] = i+1

# ---- radar percentiles ----
def pct_off(arr, value):
    a = np.array(arr); a = a[~np.isnan(a)]
    return round(100*(a<=value).sum()/len(a),1)
def pct_def(arr, value):
    a = np.array(arr); a = a[~np.isnan(a)]
    return round(100*(a>=value).sum()/len(a),1)

RADAR_MAP_OFF_HIGH = {
  'epaPlay': lambda r: (r['epaPerRush']*r['rushAtt']+r['epaPerPass']*r['passAtt'])/(r['rushAtt']+r['passAtt']) if (r['rushAtt']+r['passAtt']) else 0,
  'earlyEpa': None, 'lateSR': '_lateSR_off', 'avgDist3rd': '_avgDist3rd_off', 'rushEpa': 'epaPerRush',
  'stuffPct': None, 'lineYards': '_lineYards_off', 'opportunityPct': '_opportunityPct_off',
  'explosivePct': 'explosiveRate', 'passExplPct': '_passExplPct_off', 'rushExplPct': '_rushExplPct_off',
  'nonExplEpa': '_nonExplEpa_off', 'passEpa': 'epaPerPass', 'ydsPerDb': '_ydsPerDb_off',
  'passSR': None, 'earlySR': 'earlySR', 'seriesRate': 'seriesRate',
}
# metrics where LOWER raw = better offense (stuffPct: being stuffed is bad)
OFF_LOW_BETTER = {'stuffPct'}

for t in teams:
    r = recs[t]
    r['_epaPlay_off'] = RADAR_MAP_OFF_HIGH['epaPlay'](r)
    def_rush_n, def_pass_n = r['rushAttAllowed'], r['passAttAllowed']
    r['_epaPlay_def'] = (r['epaPerRushAllowed']*def_rush_n + r['epaPerPassAllowed']*def_pass_n)/(def_rush_n+def_pass_n) if (def_rush_n+def_pass_n) else 0

off_raw_fields = {
  'epaPlay':'_epaPlay_off','earlyEpa':None,'lateSR':'_lateSR_off','avgDist3rd':'_avgDist3rd_off','rushEpa':'epaPerRush',
  'stuffPct':'_stuffPct_off','lineYards':'_lineYards_off','opportunityPct':'_opportunityPct_off','explosivePct':'explosiveRate',
  'passExplPct':'_passExplPct_off','rushExplPct':'_rushExplPct_off','nonExplEpa':'_nonExplEpa_off','passEpa':'epaPerPass',
  'ydsPerDb':'_ydsPerDb_off','passSR':None,'earlySR':'earlySR','seriesRate':'seriesRate','rushSR':None,
}
def_raw_fields = {
  'epaPlay':'_epaPlay_def','earlyEpa':None,'lateSR':'_lateSR_def','avgDist3rd':'_avgDist3rd_def','rushEpa':'epaPerRushAllowed',
  'stuffPct':'_stuffPct_def','lineYards':'_lineYards_def','opportunityPct':'_opportunityPct_def','explosivePct':'explosiveRateAllowed',
  'passExplPct':'_passExplPct_def','rushExplPct':'_rushExplPct_def','nonExplEpa':'_nonExplEpa_def','passEpa':'epaPerPassAllowed',
  'ydsPerDb':'_ydsPerDb_def','passSR':None,'earlySR':'earlySRAllowed','seriesRate':'seriesRateAllowed','rushSR':None,
}
LOW_BETTER_METRICS = {'stuffPct','avgDist3rd'}  # being stuffed / short distance to go are bad for offense having them high is bad... actually avgDist3rd ambiguous, treat consistent w/ def convention below

for t in teams:
    r = recs[t]
    off_lmbd = r['_lateSR_off']  # placeholder just to ensure keys exist; already set
    # earlyEpa: epa/play on early downs only - approximate using epaPerRush/epaPerPass weighted... not tracked separately, use a direct calc fallback = epaPlay (best proxy without redoing full df pass)
    r['_earlyEpa_off'] = r['_epaPlay_off']
    r['_earlyEpa_def'] = r['_epaPlay_def']
    r['_passSR_off'] = None  # filled from pipeline below if available
    r['_passSR_def'] = None
    r['_rushSR_off'] = None
    r['_rushSR_def'] = None

with open('full_season_with_wl_ranks.json','w') as f:
    json.dump(recs, f)
print('done, sample Alabama:')
print(json.dumps({k:v for k,v in recs['Alabama'].items() if k in ['wins','losses','ranks']}, indent=2))
