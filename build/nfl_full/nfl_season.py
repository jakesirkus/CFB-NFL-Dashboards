import pandas as pd, numpy as np, json
NAME={'ARI':'Arizona Cardinals','ATL':'Atlanta Falcons','BAL':'Baltimore Ravens','BUF':'Buffalo Bills','CAR':'Carolina Panthers','CHI':'Chicago Bears','CIN':'Cincinnati Bengals','CLE':'Cleveland Browns','DAL':'Dallas Cowboys','DEN':'Denver Broncos','DET':'Detroit Lions','GB':'Green Bay Packers','HOU':'Houston Texans','IND':'Indianapolis Colts','JAX':'Jacksonville Jaguars','KC':'Kansas City Chiefs','LA':'Los Angeles Rams','LAC':'Los Angeles Chargers','LV':'Las Vegas Raiders','MIA':'Miami Dolphins','MIN':'Minnesota Vikings','NE':'New England Patriots','NO':'New Orleans Saints','NYG':'New York Giants','NYJ':'New York Jets','PHI':'Philadelphia Eagles','PIT':'Pittsburgh Steelers','SEA':'Seattle Seahawks','SF':'San Francisco 49ers','TB':'Tampa Bay Buccaneers','TEN':'Tennessee Titans','WAS':'Washington Commanders'}
def flags(p):
    p=p.copy()
    f=lambda c: p[c].fillna(0).astype(int)==1
    p['is_rush']=f('rush_attempt')&~f('qb_kneel')&~f('qb_scramble')
    p['is_db']=f('qb_dropback')
    p['is_scrim']=p.is_rush|p.is_db
    p['is_passatt']=f('pass_attempt')
    p['yds']=p.yards_gained.fillna(0)
    return p
def r(x,n): return None if x is None or (isinstance(x,float) and np.isnan(x)) else round(float(x),n)
def div(a,b): return a/b if b else None

def flags2(p):
    p=flags(p)
    f=lambda c: p[c].fillna(0).astype(int)==1
    p['is_db']=f('qb_dropback')|f('qb_spike')          # the original counted spikes as dropbacks
    p['is_scrim']=p.is_rush|p.is_db
    p['is_comp']=f('complete_pass')
    p['give']=f('interception')|f('fumble_lost')
    p['expl']=(p.is_rush&(p.yds>=10))|(p.is_db&(p.yds>=15))
    p['expl_pass']=p.is_db&(p.yds>=15); p['expl_rush']=p.is_rush&(p.yds>=10)
    p['succ']=p.success.fillna(0).astype(int)==1
    return p

def line_yards(y):
    if y<0: return 1.2*y
    if y<=4: return y
    if y<=10: return 4+0.5*(y-4)
    return 7.0

def _f(x,c): return x[c].fillna(0).astype(int)==1
def conv3(x): return _f(x,'third_down_converted')|_f(x,'touchdown')|_f(x,'first_down_penalty')    # penalty first downs count, like the original
def conv4(x): return _f(x,'fourth_down_converted')|_f(x,'touchdown')|_f(x,'first_down_penalty')
def giveaways(w,T):
    # interceptions thrown + fumbles lost by the team that fumbled, on any play (incl. kick/punt returns)
    return int(((w.interception.fillna(0)==1)&(w.posteam==T)).sum()+((w.fumble_lost.fillna(0)==1)&(w.fumbled_1_team==T)).sum())
def takeaways(w,T):
    games=w[(w.posteam==T)|(w.defteam==T)]
    opp=set(games.posteam.dropna())|set(games.defteam.dropna()); opp.discard(T)
    tot=0
    for gid,g in games.groupby('game_id'):
        o=[t for t in set(g.posteam.dropna())|set(g.defteam.dropna()) if t!=T]
        for t in o: tot+=giveaways(g,t)
    return tot
def team_season(w, ab):
    o=w[w.posteam==ab]; dd=w[w.defteam==ab]
    os_=o[o.is_scrim]; ds=dd[dd.is_scrim]
    orr=o[o.is_rush]; dr=dd[dd.is_rush]; odb=o[o.is_db]; ddb=dd[dd.is_db]; opa=o[o.is_passatt]; dpa=dd[dd.is_passatt]
    m={}
    m['plays']=len(os_); m['totalYds']=int(os_.yds.sum()); m['rushAtt']=len(orr); m['rushYds']=int(orr.yds.sum())
    m['rushTD']=int(o[_f(o,'rush_attempt')].rush_touchdown.fillna(0).sum()); m['passAtt']=len(odb); m['comp']=int(odb.is_comp.sum()); m['passYds']=int(odb.yds.sum())
    m['passTD']=int(odb.pass_touchdown.fillna(0).sum())
    m['explosivePlays']=int(os_.expl.sum()); m['playsAllowed']=len(ds); m['totalYdsAllowed']=int(ds.yds.sum())
    m['rushYdsAllowed']=int(dr.yds.sum()); m['rushTDAllowed']=int(dd[_f(dd,'rush_attempt')].rush_touchdown.fillna(0).sum()); m['rushAttAllowed']=len(dr)
    m['passAttAllowed']=len(ddb); m['passYdsAllowed']=int(ddb.yds.sum()); m['passTDAllowed']=int(ddb.pass_touchdown.fillna(0).sum())
    m['explosivePlaysAllowed']=int(ds.expl.sum())
    m['epaPerRush']=r(orr.epa.mean(),3); m['epaPerPass']=r(opa.epa.mean(),3); m['epaPerRushAllowed']=r(dr.epa.mean(),3); m['epaPerPassAllowed']=r(dpa.epa.mean(),3)
    m['epaPerDropback']=r(odb.epa.mean(),3); m['epaPerDropbackAllowed']=r(ddb.epa.mean(),3)
    m['sacksAllowed']=int(o.sack.fillna(0).sum()); m['sacks']=int(dd.sack.fillna(0).sum())
    m['giveaways']=giveaways(w,ab); m['takeaways']=sum(giveaways(w,t) for t in w[w.posteam==ab].defteam.dropna().unique()) if False else takeaways(w,ab); m['turnoverMargin']=m['takeaways']-m['giveaways']
    t3=os_[os_.down==3]; t4=os_[os_.down==4]; t3d=ds[ds.down==3]
    m['thirdConv']=int(conv3(t3).sum()); m['thirdSnaps']=len(t3)
    m['fourthConv']=int(conv4(t4).sum()); m['fourthSnaps']=len(t4)
    m['thirdSnapsD']=len(t3d); m['thirdStops']=len(t3d)-int(conv3(t3d).sum())
    e=os_[os_.down.isin([1,2])]; ed=ds[ds.down.isin([1,2])]
    m['earlyPlays']=len(e); m['earlyPlaysAllowed']=len(ed)
    m['earlySR']=r(100*e.succ.mean(),1); m['earlySRAllowed']=r(100*ed.succ.mean(),1)
    m['_o']=o; m['_d']=dd
    return m
