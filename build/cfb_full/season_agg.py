import pandas as pd
import numpy as np
import json

df = pd.read_pickle('combined_raw_w1_6.pkl')
with open('../nfl_rebuild/cfb_team_list.json') as f:
    FBS_TEAMS = set(json.load(f))

RUSH_TYPES = {'Rush','Rushing Touchdown','Two Point Rush'}
PASS_TYPES = {'Pass Reception','Pass Incompletion','Passing Touchdown','Sack','Interception',
              'Pass Interception Return','Interception Return Touchdown','Two Point Pass','Pass Completion'}
COMP_TYPES = {'Pass Reception','Passing Touchdown'}

df['is_kneel'] = df['PlayText'].str.contains('kneel', case=False, na=False)
df['is_rush'] = df['PlayType'].isin(RUSH_TYPES) & ~df['is_kneel']
df['is_pass'] = df['PlayType'].isin(PASS_TYPES)
df['is_scrim'] = df['is_rush'] | df['is_pass']
df['is_comp'] = df['PlayType'].isin(COMP_TYPES)
df['is_sack'] = df['PlayType'] == 'Sack'
df['is_explosive'] = (df['is_rush'] & (df['YardsGained']>=10)) | (df['PlayType'].isin(COMP_TYPES) & (df['YardsGained']>=15))

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
df['is_early'] = df['Down'].isin([1,2])
df['is_late'] = df['Down'].isin([3,4])

giveaway_kw = df['PlayText'].str.contains('fumble', case=False, na=False) | df['PlayType'].str.contains('Interception', case=False, na=False)
df['is_turnover_play'] = df['PlayType'].isin(['Interception','Pass Interception Return','Interception Return Touchdown','Fumble Recovery (Opponent)'])

teams = sorted(FBS_TEAMS)
recs = {}
for t in teams:
    off = df[(df['Offense']==t)]
    deff = df[(df['Defense']==t)]
    off_scrim = off[off['is_scrim']]
    def_scrim = deff[deff['is_scrim']]
    off_rush = off[off['is_rush']]; off_pass = off[off['is_pass']]
    def_rush = deff[deff['is_rush']]; def_pass = deff[deff['is_pass']]

    plays = len(off_scrim); totalYds = int(off_scrim['YardsGained'].sum())
    playsAllowed = len(def_scrim); totalYdsAllowed = int(def_scrim['YardsGained'].sum())
    rushAtt=len(off_rush); rushYds=int(off_rush['YardsGained'].sum()); rushTD=int((off_rush['PlayType']=='Rushing Touchdown').sum())
    passAtt=len(off_pass); comp=int(off[off['is_comp']].shape[0]); passYds=int(off_pass['YardsGained'].sum()); passTD=int((off_pass['PlayType']=='Passing Touchdown').sum())
    rushAttD=len(def_rush); rushYdsD=int(def_rush['YardsGained'].sum()); rushTDD=int((def_rush['PlayType']=='Rushing Touchdown').sum())
    passAttD=len(def_pass); passYdsD=int(def_pass['YardsGained'].sum()); passTDD=int((def_pass['PlayType']=='Passing Touchdown').sum())
    expl=int(off['is_explosive'].sum()); explD=int(deff['is_explosive'].sum())
    sacks=int(off_pass['is_sack'].sum()); sacksAllowed=int(def_pass['is_sack'].sum())
    giveaways=int(off['is_turnover_play'].sum()); takeaways=int(deff['is_turnover_play'].sum())
    thirdoff=off_scrim[off_scrim['Down']==3]; fourthoff=off_scrim[off_scrim['Down']==4]
    thirdSnaps=len(thirdoff); thirdConv=int(thirdoff['success'].fillna(False).astype(bool).sum())
    fourthSnaps=len(fourthoff); fourthConv=int(fourthoff['success'].fillna(False).astype(bool).sum())
    thirdoffD=def_scrim[def_scrim['Down']==3]
    thirdSnapsD=len(thirdoffD); thirdStops=thirdSnapsD-int(thirdoffD['success'].fillna(False).astype(bool).sum())
    earlyOff=off_scrim[off_scrim['is_early']]; earlyDef=def_scrim[def_scrim['is_early']]
    earlyPlays=len(earlyOff); earlySRnum=int(earlyOff['success'].fillna(False).astype(bool).sum())
    earlyPlaysD=len(earlyDef); earlySRDnum=int(earlyDef['success'].fillna(False).astype(bool).sum())

    rec = {
      'gp': off['GameId'].nunique(),
      'plays': plays, 'totalYds': totalYds, 'ypp': round(totalYds/plays,2) if plays else 0,
      'rushAtt': rushAtt, 'rushYds': rushYds, 'rushTD': rushTD, 'ypr': round(rushYds/rushAtt,2) if rushAtt else 0,
      'passAtt': passAtt, 'comp': comp, 'passYds': passYds, 'passTD': passTD,
      'compPct': round(100*comp/passAtt,1) if passAtt else 0, 'ypa': round(passYds/passAtt,2) if passAtt else 0,
      'explosivePlays': expl, 'explosiveRate': round(100*expl/plays,1) if plays else 0,
      'playsAllowed': playsAllowed, 'totalYdsAllowed': totalYdsAllowed, 'yppAllowed': round(totalYdsAllowed/playsAllowed,2) if playsAllowed else 0,
      'rushYdsAllowed': rushYdsD, 'rushTDAllowed': rushTDD, 'yprAllowed': round(rushYdsD/rushAttD,2) if rushAttD else 0,
      'rushAttAllowed': rushAttD, 'passAttAllowed': passAttD, 'ypaAllowed': round(passYdsD/passAttD,2) if passAttD else 0,
      'passYdsAllowed': passYdsD, 'passTDAllowed': passTDD,
      'explosivePlaysAllowed': explD, 'explosiveRateAllowed': round(100*explD/playsAllowed,1) if playsAllowed else 0,
      'epaPerRush': round(float(off_rush['Ppa'].mean()),3) if len(off_rush) else 0,
      'epaPerPass': round(float(off_pass['Ppa'].mean()),3) if len(off_pass) else 0,
      'epaPerRushAllowed': round(float(def_rush['Ppa'].mean()),3) if len(def_rush) else 0,
      'epaPerPassAllowed': round(float(def_pass['Ppa'].mean()),3) if len(def_pass) else 0,
      'sacksAllowed': sacks, 'sacks': sacksAllowed,
      'giveaways': giveaways, 'takeaways': takeaways, 'turnoverMargin': takeaways-giveaways,
      'thirdConv': thirdConv, 'thirdSnaps': thirdSnaps, 'thirdPct': round(100*thirdConv/thirdSnaps,1) if thirdSnaps else 0,
      'fourthConv': fourthConv, 'fourthSnaps': fourthSnaps,
      'thirdStops': thirdStops, 'thirdSnapsD': thirdSnapsD, 'thirdPctD': round(100*thirdStops/thirdSnapsD,1) if thirdSnapsD else 0,
      'earlySR': round(100*earlySRnum/earlyPlays,1) if earlyPlays else 0, 'earlySRAllowed': round(100*earlySRDnum/earlyPlaysD,1) if earlyPlaysD else 0,
      'earlyPlays': earlyPlays, 'earlyPlaysAllowed': earlyPlaysD,
    }
    recs[t] = rec

with open('season_recompute.json','w') as f:
    json.dump(recs, f)
print('computed', len(recs), 'teams')
print(json.dumps(recs['Alabama'], indent=2))
