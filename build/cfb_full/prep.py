import pandas as pd, numpy as np
RUSH={'Rush','Rushing Touchdown','Two Point Rush'}
PASS={'Pass Reception','Pass Incompletion','Passing Touchdown','Sack','Interception','Pass Interception Return','Interception Return Touchdown','Two Point Pass','Pass Completion'}
COMP={'Pass Reception','Passing Touchdown'}
FUM={'Fumble','Fumble Recovery (Own)','Fumble Recovery (Opponent)','Fumble Return Touchdown'}
INT={'Interception','Pass Interception Return','Interception Return Touchdown'}
def prep(df):
    df=df.copy()
    t=df['PlayText'].fillna('')
    kneel=t.str.contains('kneel',case=False)
    nop=t.str.contains('NO PLAY',case=False)
    dn=df['Down'].isin([1,2,3,4])
    df['is_rush']=df.PlayType.isin(RUSH)&~kneel
    df['is_pass']=df.PlayType.isin(PASS)
    df['is_fumrow']=df.PlayType.isin(FUM)&dn
    df['is_penplay']=(df.PlayType=='Penalty')&~nop&dn
    df['is_rp']=df.is_rush|df.is_pass                      # rush/pass plays (rates, SR, EPA)
    df['is_scrim']=df.is_rp|df.is_fumrow|df.is_penplay     # play count definition
    df['yds']=np.where(df.is_penplay,0,df.YardsGained.fillna(0))
    df['is_comp']=df.PlayType.isin(COMP)
    df['is_sack']=df.PlayType=='Sack'
    df['expl_rush']=df.is_rush&(df.YardsGained>=10)
    df['expl_pass']=df.is_comp&(df.YardsGained>=15)
    df['expl']=df.expl_rush|df.expl_pass
    d=df.Down; dist=df.Distance; g=df.YardsGained
    sc=df.Scoring.fillna(False).astype(bool)
    succ=np.select([sc, d==1, d==2, d.isin([3,4])],[True, g>=0.5*dist, g>=0.7*dist, g>=dist],False)
    df['succ']=np.where(df.is_rp,succ,False).astype(bool)
    df['early']=d.isin([1,2]); df['late']=d.isin([3,4])
    df['passdown']=((d==2)&(dist>=8))|(d.isin([3,4])&(dist>=5))
    df['int']=df.PlayType.isin(INT)
    df['fum_lost']=df.PlayType.isin({'Fumble Recovery (Opponent)','Fumble Return Touchdown'})
    df['fum_own']=df.PlayType=='Fumble Recovery (Own)'
    df['giveaway']=df['int']|df['fum_lost']
    df['clock']=df['Clock Minutes'].fillna(0)*60+df['Clock Seconds'].fillna(0)
    return df.sort_values('Id')
