import pandas as pd, numpy as np, json

df = pd.read_pickle('combined_raw_fixed.pkl')
with open('../nfl_rebuild/cfb_team_list.json') as f:
    FBS_TEAMS = set(json.load(f))

RUSH_TYPES = {'Rush','Rushing Touchdown','Two Point Rush'}
PASS_TYPES = {'Pass Reception','Pass Incompletion','Passing Touchdown','Sack','Interception',
              'Pass Interception Return','Interception Return Touchdown','Two Point Pass','Pass Completion'}
df['is_kneel'] = df['PlayText'].str.contains('kneel', case=False, na=False)
df['is_rush'] = df['PlayType'].isin(RUSH_TYPES) & ~df['is_kneel']
df['is_pass'] = df['PlayType'].isin(PASS_TYPES)
df['is_scrim'] = df['is_rush'] | df['is_pass']

def success(row):
    if row['Scoring'] == True or row['Scoring']==1: return True
    d, dist, g = row['Down'], row['Distance'], row['YardsGained']
    if pd.isna(dist) or pd.isna(g): return np.nan
    if dist<=0: return g>=dist
    if d==1: return g>=0.5*dist
    elif d==2: return g>=0.7*dist
    else: return g>=dist
mask_dd = df['is_scrim'] & df['Down'].isin([1,2,3,4]) & df['Distance'].notna()
df.loc[mask_dd,'success'] = df.loc[mask_dd].apply(success, axis=1)
df['success_b'] = df['success'].fillna(False).astype(bool)
df['is_early'] = df['Down'].isin([1,2])

with open('full_season_with_wl_ranks.json') as f:
    recs = json.load(f)

for t in FBS_TEAMS:
    off = df[df['Offense']==t]; deff = df[df['Defense']==t]
    off_scrim = off[off['is_scrim']]; def_scrim = deff[deff['is_scrim']]
    off_rush = off[off['is_rush']]; def_rush = deff[deff['is_rush']]
    early_off = off_scrim[off_scrim['is_early']]; early_def = def_scrim[def_scrim['is_early']]
    rushSR_off = 100*off_rush['success_b'].sum()/len(off_rush) if len(off_rush) else 0
    rushSR_def = 100*def_rush['success_b'].sum()/len(def_rush) if len(def_rush) else 0
    off_pass = off[off['is_pass']]; def_pass = deff[deff['is_pass']]
    passSR_off = 100*off_pass['success_b'].sum()/len(off_pass) if len(off_pass) else 0
    passSR_def = 100*def_pass['success_b'].sum()/len(def_pass) if len(def_pass) else 0
    earlyEpa_off = float(early_off['Ppa'].mean()) if len(early_off) else 0
    earlyEpa_def = float(early_def['Ppa'].mean()) if len(early_def) else 0
    r = recs[t]
    r['_rushSR_off']=round(rushSR_off,3); r['_rushSR_def']=round(rushSR_def,3)
    r['_passSR_off']=round(passSR_off,3); r['_passSR_def']=round(passSR_def,3)
    r['_earlyEpa_off']=round(earlyEpa_off,3); r['_earlyEpa_def']=round(earlyEpa_def,3)

# ---- build radar/radarRaw with percentiles ----
RAW_KEYS_OFF = {
  'epaPlay':'_epaPlay_off','earlyEpa':'_earlyEpa_off','lateSR':'_lateSR_off','avgDist3rd':'_avgDist3rd_off',
  'rushEpa':'epaPerRush','stuffPct':'_stuffPct_off','lineYards':'_lineYards_off','opportunityPct':'_opportunityPct_off',
  'explosivePct':'explosiveRate','passExplPct':'_passExplPct_off','rushExplPct':'_rushExplPct_off','nonExplEpa':'_nonExplEpa_off',
  'passEpa':'epaPerPass','ydsPerDb':'_ydsPerDb_off','passSR':'_passSR_off','earlySR':'earlySR','seriesRate':'seriesRate','rushSR':'_rushSR_off',
}
RAW_KEYS_DEF = {
  'epaPlay':'_epaPlay_def','earlyEpa':'_earlyEpa_def','lateSR':'_lateSR_def','avgDist3rd':'_avgDist3rd_def',
  'rushEpa':'epaPerRushAllowed','stuffPct':'_stuffPct_def','lineYards':'_lineYards_def','opportunityPct':'_opportunityPct_def',
  'explosivePct':'explosiveRateAllowed','passExplPct':'_passExplPct_def','rushExplPct':'_rushExplPct_def','nonExplEpa':'_nonExplEpa_def',
  'passEpa':'epaPerPassAllowed','ydsPerDb':'_ydsPerDb_def','passSR':'_passSR_def','earlySR':'earlySRAllowed','seriesRate':'seriesRateAllowed','rushSR':'_rushSR_def',
}
# For offense: higher raw = better, EXCEPT stuffPct and avgDist3rd (being stuffed/short distance isn't directly "bad raw=low" -- but avgDist3rd for OFFENSE: shorter distance needed on 3rd down is good, so LOWER is better for offense)
OFF_LOW_BETTER = {'stuffPct','avgDist3rd'}
# For defense: lower raw = better (less EPA allowed, less yards, etc), EXCEPT stuffPct/lineYards-allowed-is-low-good already consistent,
# avgDist3rd allowed: forcing opponent into LONGER distance is good for defense -> higher raw = better for defense (opposite of offense)
DEF_HIGH_BETTER = {'avgDist3rd','stuffPct','lateSR'}
# lateSR for defense = opponent's late down SR allowed -> lower is better (not high). Remove from DEF_HIGH_BETTER except avgDist3rd/stuffPct
DEF_HIGH_BETTER = {'avgDist3rd','stuffPct'}

teams = list(FBS_TEAMS)
for metric in RAW_KEYS_OFF:
    off_vals = {t: recs[t][RAW_KEYS_OFF[metric]] for t in teams}
    def_vals = {t: recs[t][RAW_KEYS_DEF[metric]] for t in teams}
    arr_off = np.array(list(off_vals.values()))
    arr_def = np.array(list(def_vals.values()))
    for t in teams:
        r = recs[t]
        v_off = off_vals[t]
        if metric in OFF_LOW_BETTER:
            pct = round(100*(arr_off>=v_off).sum()/len(arr_off),1)
        else:
            pct = round(100*(arr_off<=v_off).sum()/len(arr_off),1)
        r.setdefault('radar',{}).setdefault('off',{})[metric]=pct
        r.setdefault('radar',{}).setdefault('offRaw',{})[metric]=v_off

        v_def = def_vals[t]
        if metric in DEF_HIGH_BETTER:
            pctd = round(100*(arr_def<=v_def).sum()/len(arr_def),1)
        else:
            pctd = round(100*(arr_def>=v_def).sum()/len(arr_def),1)
        r.setdefault('radar',{}).setdefault('def',{})[metric]=pctd
        r.setdefault('radar',{}).setdefault('defRaw',{})[metric]=v_def

# strip internal underscore helper fields before saving
for t in teams:
    recs[t] = {k:v for k,v in recs[t].items() if not k.startswith('_')}

with open('final_teams.json','w') as f:
    json.dump(recs, f)
print('Alabama final:')
print(json.dumps(recs['Alabama'], indent=2)[:2500])
