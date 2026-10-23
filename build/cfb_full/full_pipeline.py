import pandas as pd
import numpy as np
import json

df = pd.read_pickle('combined_raw_fixed.pkl')
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
df['is_explosive_rush'] = df['is_rush'] & (df['YardsGained']>=10)
df['is_explosive_pass'] = df['PlayType'].isin(COMP_TYPES) & (df['YardsGained']>=15)
df['is_explosive'] = df['is_explosive_rush'] | df['is_explosive_pass']

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
df['is_late'] = df['Down'].isin([3,4])
df['is_turnover_play'] = df['PlayType'].isin(['Interception','Pass Interception Return','Interception Return Touchdown','Fumble Recovery (Opponent)'])

def line_yards(g):
    if g<0: return g
    if g<=4: return g
    if g<=8: return 4+0.5*(g-4)
    if g<=10: return 6+0.25*(g-8)
    return 6.5
df['line_yards'] = np.where(df['is_rush'], df['YardsGained'].apply(line_yards), np.nan)

def compute_series(sub):
    sub = sub.sort_values('Id')
    series_n = 0; conv_n = 0; cur_scored = False; started = False
    for down, scoring in zip(sub['Down'], sub['Scoring'].fillna(False).astype(bool)):
        if down == 1:
            if started: conv_n += 1
            series_n += 1; started = True; cur_scored = False
        if scoring: cur_scored = True
    if started and cur_scored: conv_n += 1
    return series_n, conv_n

def series_stats(scrim_df):
    series=0; conv=0
    for (gid,did), grp in scrim_df.groupby(['GameId','DriveId']):
        s,c = compute_series(grp)
        series+=s; conv+=c
    return series, conv

def drive_epa(scrim_df):
    # EPA per drive: sum of Ppa per drive, then mean across drives
    d = scrim_df.groupby(['GameId','DriveId'])['Ppa'].sum()
    return float(d.mean()) if len(d) else 0.0

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
    exprush=int(off['is_explosive_rush'].sum()); exprushD=int(deff['is_explosive_rush'].sum())
    exppass=int(off['is_explosive_pass'].sum()); exppassD=int(deff['is_explosive_pass'].sum())
    sacks_off=int(off_pass['is_sack'].sum()); sacks_def=int(def_pass['is_sack'].sum())
    giveaways=int(off['is_turnover_play'].sum()); takeaways=int(deff['is_turnover_play'].sum())
    thirdoff=off_scrim[off_scrim['Down']==3]; fourthoff=off_scrim[off_scrim['Down']==4]
    thirdSnaps=len(thirdoff); thirdConv=int(thirdoff['success_b'].sum())
    fourthSnaps=len(fourthoff); fourthConv=int(fourthoff['success_b'].sum())
    thirdoffD=def_scrim[def_scrim['Down']==3]
    thirdSnapsD=len(thirdoffD); thirdConvD=int(thirdoffD['success_b'].sum()); thirdStops=thirdSnapsD-thirdConvD
    earlyOff=off_scrim[off_scrim['is_early']]; earlyDef=def_scrim[def_scrim['is_early']]
    lateOff=off_scrim[off_scrim['is_late']]; lateDef=def_scrim[def_scrim['is_late']]
    earlyPlays=len(earlyOff); earlyConv=int(earlyOff['success_b'].sum())
    earlyPlaysD=len(earlyDef); earlyConvD=int(earlyDef['success_b'].sum())
    latePlays=len(lateOff); lateConv=int(lateOff['success_b'].sum())
    latePlaysD=len(lateDef); lateConvD=int(lateDef['success_b'].sum())
    seriesN, seriesConv = series_stats(off_scrim)
    seriesND, seriesConvD = series_stats(def_scrim)
    nonexpl_off = off[~off['is_explosive'] & off['is_scrim']]
    nonexpl_def = deff[~deff['is_explosive'] & deff['is_scrim']]
    off_rush_ly = off_rush['line_yards'].dropna()
    def_rush_ly = def_rush['line_yards'].dropna()
    third3rd_dist_off = thirdoff['Distance'].dropna()
    third3rd_dist_def = thirdoffD['Distance'].dropna()

    rec = {
      'gp': int(off['GameId'].nunique()),
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
      'sacksAllowed': sacks_off, 'sacks': sacks_def,
      'giveaways': giveaways, 'takeaways': takeaways, 'turnoverMargin': takeaways-giveaways,
      'thirdConv': thirdConv, 'thirdSnaps': thirdSnaps, 'thirdPct': round(100*thirdConv/thirdSnaps,1) if thirdSnaps else 0,
      'fourthConv': fourthConv, 'fourthSnaps': fourthSnaps,
      'thirdStops': thirdStops, 'thirdSnapsD': thirdSnapsD, 'thirdPctD': round(100*thirdStops/thirdSnapsD,1) if thirdSnapsD else 0,
      'seriesConv': seriesConv, 'series': seriesN, 'seriesRate': round(100*seriesConv/seriesN,1) if seriesN else 0,
      'seriesConvAllowed': seriesConvD, 'seriesAllowed': seriesND, 'seriesRateAllowed': round(100*seriesConvD/seriesND,1) if seriesND else 0,
      'earlySR': round(100*earlyConv/earlyPlays,1) if earlyPlays else 0, 'earlySRAllowed': round(100*earlyConvD/earlyPlaysD,1) if earlyPlaysD else 0,
      'earlyPlays': earlyPlays, 'earlyPlaysAllowed': earlyPlaysD,
      'epaPerDrive': round(drive_epa(off_scrim),3), 'epaPerDriveAllowed': round(drive_epa(def_scrim),3),
      '_lateSR_off': round(100*lateConv/latePlays,3) if latePlays else 0,
      '_lateSR_def': round(100*lateConvD/latePlaysD,3) if latePlaysD else 0,
      '_avgDist3rd_off': round(float(third3rd_dist_off.mean()),3) if len(third3rd_dist_off) else 0,
      '_avgDist3rd_def': round(float(third3rd_dist_def.mean()),3) if len(third3rd_dist_def) else 0,
      '_rushEpa_off': round(float(off_rush['Ppa'].mean()),3) if len(off_rush) else 0,
      '_rushEpa_def': round(float(def_rush['Ppa'].mean()),3) if len(def_rush) else 0,
      '_stuffPct_off': round(100*(off_rush['YardsGained']<=0).sum()/rushAtt,3) if rushAtt else 0,
      '_stuffPct_def': round(100*(def_rush['YardsGained']<=0).sum()/rushAttD,3) if rushAttD else 0,
      '_lineYards_off': round(float(off_rush_ly.mean()),3) if len(off_rush_ly) else 0,
      '_lineYards_def': round(float(def_rush_ly.mean()),3) if len(def_rush_ly) else 0,
      '_opportunityPct_off': round(100*(off_rush['YardsGained']>=4).sum()/rushAtt,3) if rushAtt else 0,
      '_opportunityPct_def': round(100*(def_rush['YardsGained']>=4).sum()/rushAttD,3) if rushAttD else 0,
      '_passExplPct_off': round(100*exppass/passAtt,3) if passAtt else 0,
      '_passExplPct_def': round(100*exppassD/passAttD,3) if passAttD else 0,
      '_rushExplPct_off': round(100*exprush/rushAtt,3) if rushAtt else 0,
      '_rushExplPct_def': round(100*exprushD/rushAttD,3) if rushAttD else 0,
      '_nonExplEpa_off': round(float(nonexpl_off['Ppa'].mean()),3) if len(nonexpl_off) else 0,
      '_nonExplEpa_def': round(float(nonexpl_def['Ppa'].mean()),3) if len(nonexpl_def) else 0,
      '_ydsPerDb_off': round(off_pass['YardsGained'].sum()/passAtt,3) if passAtt else 0,
      '_ydsPerDb_def': round(def_pass['YardsGained'].sum()/passAttD,3) if passAttD else 0,
    }
    recs[t] = rec

with open('full_season_recompute.json','w') as f:
    json.dump(recs, f)
print('computed', len(recs), 'teams')
print(json.dumps(recs['Alabama'], indent=2))
