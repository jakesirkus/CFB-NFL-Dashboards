import pandas as pd, numpy as np, json

df_full = pd.read_pickle('combined_raw_fixed.pkl')
wk6_file = pd.read_csv('/root/.claude/uploads/b24cbaad-1fd0-50eb-9ab4-9c0e1d6593f3/c2146c95-download_20.csv', low_memory=False)
wk6_ids_all = set(wk6_file['GameId'].unique())
EXCLUDE = set()   # Missouri-Texas A&M now complete in the re-pulled Week 6 file
wk6_ids = wk6_ids_all - EXCLUDE
wk6 = df_full[df_full['GameId'].isin(wk6_ids)].copy()

with open('../nfl_rebuild/cfb_team_list.json') as f:
    FBS_TEAMS = set(json.load(f))

RUSH_TYPES = {'Rush','Rushing Touchdown','Two Point Rush'}
PASS_TYPES = {'Pass Reception','Pass Incompletion','Passing Touchdown','Sack','Interception',
              'Pass Interception Return','Interception Return Touchdown','Two Point Pass','Pass Completion'}
COMP_TYPES = {'Pass Reception','Passing Touchdown'}
wk6['is_kneel'] = wk6['PlayText'].str.contains('kneel', case=False, na=False)
wk6['is_rush'] = wk6['PlayType'].isin(RUSH_TYPES) & ~wk6['is_kneel']
wk6['is_pass'] = wk6['PlayType'].isin(PASS_TYPES)
wk6['is_scrim'] = wk6['is_rush'] | wk6['is_pass']
wk6['is_explosive'] = (wk6['is_rush'] & (wk6['YardsGained']>=10)) | (wk6['PlayType'].isin(COMP_TYPES) & (wk6['YardsGained']>=15))

def success(row):
    if row['Scoring'] == True or row['Scoring']==1: return True
    d, dist, g = row['Down'], row['Distance'], row['YardsGained']
    if pd.isna(dist) or pd.isna(g): return np.nan
    if dist<=0: return g>=dist
    if d==1: return g>=0.5*dist
    elif d==2: return g>=0.7*dist
    else: return g>=dist
mask_dd = wk6['is_scrim'] & wk6['Down'].isin([1,2,3,4]) & wk6['Distance'].notna()
wk6.loc[mask_dd,'success'] = wk6.loc[mask_dd].apply(success, axis=1)
wk6['success_b'] = wk6['success'].fillna(False).astype(bool)

def compute_series(sub):
    sub = sub.sort_values('Id')
    series_n=0; conv_n=0; cur_scored=False; started=False
    for down, scoring in zip(sub['Down'], sub['Scoring'].fillna(False).astype(bool)):
        if down==1:
            if started: conv_n+=1
            series_n+=1; started=True; cur_scored=False
        if scoring: cur_scored=True
    if started and cur_scored: conv_n+=1
    return series_n, conv_n
def series_stats(scrim_df):
    series=0; conv=0
    for (gid,did), grp in scrim_df.groupby(['GameId','DriveId']):
        s,c = compute_series(grp)
        series+=s; conv+=c
    return series, conv

idx = wk6.groupby('GameId')['Id'].idxmax()
finals = wk6.loc[idx, ['GameId','Home','Away','Offense','Defense','OffenseScore','DefenseScore']].set_index('GameId')

game_entries = {}  # team -> entry dict
for gid in wk6['GameId'].unique():
    g = wk6[wk6['GameId']==gid]
    f = finals.loc[gid]
    home, away = f['Home'], f['Away']
    # determine final score for home/away
    off_last, def_last, os_, ds_ = f['Offense'], f['Defense'], f['OffenseScore'], f['DefenseScore']
    _sc={}
    for _o,_os,_d,_ds in zip(g.Offense,g.OffenseScore,g.Defense,g.DefenseScore):
        _sc[_o]=max(_sc.get(_o,0),_os); _sc[_d]=max(_sc.get(_d,0),_ds)
    home_score = _sc.get(home,0)   # final = each team's highest score (row Ids aren't chronological)
    away_score = _sc.get(away,0)
    for team, opp, is_home, ts, os_t in [(home, away, True, home_score, away_score), (away, home, False, away_score, home_score)]:
        if team not in FBS_TEAMS:
            continue
        off = g[g['Offense']==team]; deff = g[g['Defense']==team]
        off_scrim = off[off['is_scrim']]; def_scrim = deff[deff['is_scrim']]
        off_rush = off[off['is_rush']]; off_pass = off[off['is_pass']]
        def_rush = deff[deff['is_rush']]; def_pass = deff[deff['is_pass']]
        plays = len(off_scrim)
        ypp = round(off_scrim['YardsGained'].sum()/plays,2) if plays else 0
        exp = int(off['is_explosive'].sum()); expAllowed = int(deff['is_explosive'].sum())
        epaRush = round(float(off_rush['Ppa'].mean()),3) if len(off_rush) else 0
        epaPass = round(float(off_pass['Ppa'].mean()),3) if len(off_pass) else 0
        epaRushAllowed = round(float(def_rush['Ppa'].mean()),3) if len(def_rush) else 0
        epaPassAllowed = round(float(def_pass['Ppa'].mean()),3) if len(def_pass) else 0
        rushYds = int(off_rush['YardsGained'].sum()); passYds = int(off_pass['YardsGained'].sum())
        thirdoff = off_scrim[off_scrim['Down']==3]
        thirdAtt = len(thirdoff); thirdConv = int(thirdoff['success_b'].sum())
        thirdPct = round(100*thirdConv/thirdAtt,1) if thirdAtt else 0
        fourthoff = off_scrim[off_scrim['Down']==4]
        fourthAtt = len(fourthoff); fourthConv = int(fourthoff['success_b'].sum())
        giveaway_types = {'Interception','Pass Interception Return','Interception Return Touchdown','Fumble Recovery (Opponent)'}
        to_off = int(off['PlayType'].isin(giveaway_types).sum())
        to_def = int(deff['PlayType'].isin(giveaway_types).sum())
        sN, sConv = series_stats(off_scrim)
        sND, sConvD = series_stats(def_scrim)
        seriesRate = round(100*sConv/sN,1) if sN else 0
        seriesRateAllowed = round(100*sConvD/sND,1) if sND else 0
        result = 'W' if ts>os_t else ('L' if ts<os_t else 'T')
        game_entries[team] = {
            'week':6, 'opp':opp, 'home':is_home, 'result':result, 'ts':int(ts), 'os':int(os_t),
            'plays':plays, 'ypp':ypp, 'exp':exp, 'expAllowed':expAllowed,
            'epaRush':epaRush,'epaPass':epaPass,'epaRushAllowed':epaRushAllowed,'epaPassAllowed':epaPassAllowed,
            'rushYds':rushYds,'passYds':passYds,'thirdPct':thirdPct,'to':to_def-to_off,
            'thirdConv':thirdConv,'thirdAtt':thirdAtt,'fourthConv':fourthConv,'fourthAtt':fourthAtt,
            'seriesRate':seriesRate,'seriesRateAllowed':seriesRateAllowed,
        }

with open('week6_game_entries.json','w') as f:
    json.dump(game_entries, f)
print('teams with week6 entries:', len(game_entries))
print(json.dumps(game_entries.get('Alabama'), indent=2))
