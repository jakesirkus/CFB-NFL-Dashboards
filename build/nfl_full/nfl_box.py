import pandas as pd, numpy as np
from nfl_season import NAME, flags2, conv3, conv4, _f
def line_yards(y):
    if y<0: return 1.2*y
    y=min(y,11)
    return y if y<=4 else (4+0.5*(y-4) if y<=8 else 6+0.25*(y-8))

def r1(x,n=1):
    if x is None: return None
    try:
        if np.isnan(x): return None
    except TypeError: pass
    return round(float(x),n)
def sdiv(a,b): return a/b if b else None

def hl(y): return y-line_yards(y)

def series_tbl(g, T, ps=None):
    # a series belongs to the team on the first row carrying it (a kickoff row can share a series number);
    # in quarter/half splits a series goes to the quarter of its first real play
    first=g[g.posteam.notna()].groupby('series').posteam.first()
    o=g[g.series.isin(first[first==T].index)&(g.posteam==T)]
    s=o.groupby('series').agg(res=('series_result','first'),succ=('series_success','max'),snaps=('is_scrim','sum'))
    s['q']=o[o.play_type.notna()].groupby('series').qtr.first()
    s=s[~s.res.isin(['QB kneel','End of half'])&~((s.snaps==0)&(s.res=='Opp touchdown'))]
    return s if ps is None else s[s.q.isin(ps)]

def give_tbl(g, T):
    """turnover rows given away by team T (INT thrown, or a fumble T lost on any play)"""
    i=(g.interception.fillna(0)==1)&(g.posteam==T)
    f=(g.fumble_lost.fillna(0)==1)&(g.fumbled_1_team==T)
    return i, f

def team_box(g, T, O, drives, period=False, gfull=None, ps=None, gfull_drives=None):
    o=g[g.posteam==T]; d=g[g.posteam==O]
    os_=o[o.is_scrim]; orush=o[o.is_rush]; odb=o[o.is_db]; opa=o[o.is_passatt]
    ds_=d[d.is_scrim]; drush=d[d.is_rush]; ddb=d[d.is_db]
    n=len(os_); yards=float(os_.yds.sum()); epa=float(os_.epa.sum())
    exm=(os_.goal_to_go==1)&(os_.yardline_100<=5); ex=os_[exm]; inn=os_[~exm]
    if period: inn=os_; odb=os_[os_.is_passatt]     # quarter/half splits: no goal-line exclusion; pass = pass attempts
    if period: inn=os_; odb=os_[os_.is_passatt]     # quarter/half splits: no goal-line exclusion; pass = pass attempts
    prod={'scrimPlays':float(n),'yards':yards,'ypp':r1(sdiv(inn.yds.sum(),len(inn)),3),'yppExcludedPlays':float(len(ex)),
          'epa':r1(epa,1),'epaPlay':r1(sdiv(epa,n),3),
          'passYds':float(odb.yds.sum()),'passYpp':r1(sdiv(odb.yds.sum(),len(odb)),3),
          'dbEpa':r1(odb.epa.sum(),1),'dbEpaPlay':r1(sdiv(odb.epa.sum(),len(odb)),3),'scrambles':float(_f(os_,'qb_scramble').sum()),
          'passEpa':r1(opa.epa.sum(),1),'passEpaPlay':r1(sdiv(opa.epa.sum(),len(opa)),3),
          'rushYds':float(orush.yds.sum()),'rushYpp':r1(sdiv(orush.yds.sum(),len(orush)),3),'rushEpa':r1(orush.epa.sum(),1),'rushEpaPlay':r1(sdiv(orush.epa.sum(),len(orush)),3)}
    ra=len(orush); gy=orush.yds
    power=orush[(orush.ydstogo<=2)&orush.down.isin([3,4])]
    pconv=(_f(power,'first_down')|_f(power,'touchdown'))
    opp_runs=orush[gy>=4]
    ly=gy.apply(line_yards); hy=opp_runs.yds.apply(hl)
    rush={'scrimPlays':float(n),'rushAtt':float(ra),'rushShare':sdiv(100*ra,n),'powerAtt':float(len(power)),'powerRate':r1(sdiv(100*pconv.sum(),len(power))),
          'stuffedRuns':float((gy<=0).sum()),'stuffRate':r1(sdiv(100*(gy<=0).sum(),ra)),'stoppedRuns':float((gy<=2).sum()),'stoppedRate':r1(sdiv(100*(gy<=2).sum(),ra)),
          'opportunityRuns':float(len(opp_runs)),'opportunityRate':r1(sdiv(100*len(opp_runs),ra)),'lineYardsTotal':r1(ly.sum(),1),'lineYardsPerCarry':r1(sdiv(ly.sum(),ra),3),
          'highlightYardsTotal':r1(hy.sum(),1),'highlightYardsPerOpp':r1(sdiv(hy.sum(),len(opp_runs)),3)}
    ne=os_[~os_.expl]
    expl={'playsTotal':float((o.play_type.notna()&~o.desc.fillna('').str.startswith('Timeout')).sum()),'scrimPlays':float(n),'explosivePlays':float(os_.expl.sum()),'explPass':float(os_.expl_pass.sum()),'explRush':float(os_.expl_rush.sum()),
          'nonExplEpaPlay':r1(sdiv(ne.epa.sum(),len(ne)),3),'nonExplPassEpaPlay':r1(sdiv(ne[ne.is_passatt].epa.sum(),ne.is_passatt.sum()),3),'nonExplRushEpaPlay':r1(sdiv(ne[ne.is_rush].epa.sum(),ne.is_rush.sum()),3)}
    e=os_[os_.down.isin([1,2])]; l=os_[os_.down.isin([3,4])]
    win=lambda x: x[((x.qtr==2)&(x.quarter_seconds_remaining<=240))|((x.qtr==3)&(x.quarter_seconds_remaining>=660))]
    m8=win(os_); m8all=win(o[o.play_type.notna()&~o.desc.fillna('').str.startswith('Timeout')])
    def sr(x): return r1(sdiv(100*x.succ.sum(),len(x)))
    P=lambda x: x[x.is_passatt]; Rr=lambda x: x[x.is_rush]
    pdn=os_.down.isna()|((os_.down==2)&(os_.ydstogo>=9))|(os_.down.isin([3,4])&(os_.ydstogo>=5))   # two-point tries count as passing downs
    sit={'successPlays':float(_f(o,'success').sum()),'successPlaysRate':sr(os_),'successPassRate':sr(P(os_)),'successRushRate':sr(Rr(os_)),
         'stdDownPlays':float((~pdn).sum()),'passDownPlays':float(pdn.sum()),
         'earlyDownFirstDowns':float((_f(e,'first_down')|_f(e,'touchdown')).sum()),
         'earlyEpa':r1(e.epa.sum()),'earlyEpaPlay':r1(sdiv(e.epa.sum(),len(e)),3),'earlyPass':float(len(P(e))),'earlyRush':float(len(Rr(e))),
         'earlyPassSuccessRate':sr(P(e)),'earlyRushSuccessRate':sr(Rr(e)),
         'lateEpa':r1(l.epa.sum()),'lateEpaPlay':r1(sdiv(l.epa.sum(),len(l)),3),'latePass':float(len(P(l))),'lateRush':float(len(Rr(l))),
         'latePassSuccessRate':sr(P(l)),'lateRushSuccessRate':sr(Rr(l)),
         'avgDist3rd':r1(os_[os_.down==3].ydstogo.mean()) if (os_.down==3).any() else None,
         'mid8Epa':r1(m8all.epa.sum()),'mid8EpaPlay':r1(sdiv(m8all.epa.sum(),len(m8all)),3),'mid8Pass':float(len(P(m8))),'mid8Rush':float(len(Rr(m8))),
         'mid8PassSuccessRate':sr(P(m8)),'mid8RushSuccessRate':sr(Rr(m8))}
    tdr=[x for x in drives if x['_tm']==T and x['_scrim']>0]; odr=[x for x in drives if x['_tm']==O and x['_scrim']>0]
    dsum=lambda ds,k: sum(x[k] for x in ds)
    av=[x for x in tdr if x['spot1'] is not None and (x['spot1']>9 if period else 100-x['spot1']>5)]
    depa=sum(x['_epa'] for x in tdr); depa_o=sum(x['_epa'] for x in odr)
    if period: depa=epa; depa_o=float(ds_.epa.sum())     # splits: period EPA over drives that started in the period
    drv={'total':len(tdr),'avgStartFP':r1(sdiv(sum(x['spot1'] for x in tdr if x['spot1'] is not None),sum(1 for x in tdr if x['spot1'] is not None))),
         'playsPerDrive':sdiv(float(n),len(tdr)),'yardsPerDrive':sdiv(yards,len(tdr)),
         'availYardsPct':r1(sdiv(100*sum(x['yards']/(100-x['spot1']) for x in av),len(av))),'epaPerDrive':r1(sdiv(depa,len(tdr)),2)}
    POINTS={'Touchdown','Field goal','Opp touchdown','Safety'}
    stops=[x for x in odr if x['_fdr'] not in POINTS]
    tfl=int((drush.yds<0).sum()); sacks=int(_f(ddb,'sack').sum()); pbu=int(d.pass_defense_1_player_id.notna().sum())
    ints=int(_f(d,'interception').sum()); ff=int(_f(d,'fumble_forced').sum())
    sk,it,pb,ffm=_f(ds_,'sack'),_f(ds_,'interception'),ds_.pass_defense_1_player_id.notna(),_f(ds_,'fumble_forced')
    hpm=ds_.is_passatt&(sk|it|pb|ffm); hrm=ds_.is_rush&((ds_.yds<=0)|ffm)
    hp=int(hpm.sum()); hr=int(hrm.sum())
    ffo=int((_f(d,'fumble_forced')&~d.index.isin(ds_[hpm|hrm].index)).sum())   # forced fumbles on other snaps
    ffs=int((_f(ds_,'fumble_forced')&~ds_.index.isin(ds_[hpm|hrm].index)).sum())   # e.g. strip on a scramble
    hv=hp+hr+ffo
    dfn={'scrimPlays':float(len(ds_)),'stopRate':r1(sdiv(100*len(stops),len(odr))),'havocPlays':float(hv),'havocRate':r1(sdiv(100*(hp+hr+ffs),len(ds_))),
         'havocPass':float(hp),'havocRush':float(hr),'tflRush':float(tfl),'sacks':float(sacks),'pbu':float(pbu),'ints':float(ints),'ff':float(ff),
         'epaPerDriveAllowed':r1(sdiv(depa_o,len(odr)),2)}
    gi,gf=give_tbl(g,T); ti,tf=give_tbl(g,O)
    fum_ev=((g.fumble.fillna(0)==1)&(g.fumbled_1_team==T))
    give=int(gi.sum()+gf.sum()); take=int(ti.sum()+tf.sum())
    tov={'giveaways':float(give),'takeaways':float(take),'fumbleEvents':float(fum_ev.sum()),'fumblesLost':float(gf.sum()),'fumblesOwnRecov':float(fum_ev.sum()-gf.sum()),
         'ints':float(gi.sum()),'margin':float(take-give)}
    t3=os_[os_.down==3]; t4=os_[os_.down==4]; c3=int(conv3(t3).sum()); c4=int(conv4(t4).sum())
    so=series_tbl(gfull if period else g,T,ps); sd=series_tbl(gfull if period else g,O,ps); sn,sc=len(so),int(so.succ.sum()); snd,scd=len(sd),int(sd.succ.sum())
    conv={'thirdConv':float(c3),'thirdAtt':float(len(t3)),'thirdRate':r1(sdiv(100*c3,len(t3))),'fourthConv':float(c4),'fourthAtt':float(len(t4)),
          'fourthRate':r1(sdiv(100*c4,len(t4))),'seriesConv':float(sc),'series':float(sn),'seriesRate':r1(sdiv(100*sc,sn)),
          'seriesConvAllowed':float(scd),'seriesAllowed':float(snd),'seriesRateAllowed':r1(sdiv(100*scd,snd))}
    def opps(ds):
        tr=[x for x in ds if x['opp30']]
        pts=sum(x['_pts'] for x in tr)
        return tr,pts,sum(x['result']=='Touchdown' for x in tr),sum(x['result']=='Field Goal' for x in tr)
    tr,pts,tds,fgs=opps(tdr); tra,ptsa,tdsa,fgsa=opps(odr)
    oppd={'trips':len(tr),'points':pts,'ppo':r1(sdiv(pts,len(tr)),2),'tds':tds,'fgs':fgs,'busts':sum(1 for x in tr if x['_pts']==0),
          'tripsAllowed':len(tra),'pointsAllowed':ptsa,'ppoAllowed':r1(sdiv(ptsa,len(tra)),2),'tdsAllowed':tdsa,'fgsAllowed':fgsa,
          'stopsInside30':sum(1 for x in tra if x['_pts']==0)}
    rz=[x for x in tdr if x['_rz']]
    rzv=sdiv(100*sum(x['_rztd'] for x in rz),len(rz))
    if period:   # splits: red-zone trips/TDs from snaps inside the period
        from nfl_season import _f as F
        rzr=g[(g.is_scrim|F(g,'two_point_attempt'))&(g.yardline_100<=20)]
        dset=[x for x in gfull_drives if x['_tm']==T and x['n'] in set(rzr.fixed_drive)]
        tds=set(g[g.is_scrim&(g.yardline_100<=20)&F(g,'touchdown')].fixed_drive)
        rzv=sdiv(100*sum(x['n'] in tds for x in dset),len(dset))
    ov_vals={'epaPlay':prod['epaPlay'],'successRate':sdiv(100*os_.succ.sum(),n),'ypp':prod['ypp'],'passEpaPlay':prod['passEpaPlay'],'dbEpaPlay':prod['dbEpaPlay'],
             'rushEpaPlay':prod['rushEpaPlay'],'passYpp':prod['passYpp'],'explosiveRate':sdiv(100*os_.expl.sum(),n),'thirdRate':sdiv(100*c3,len(t3)),
             'seriesRate':sdiv(100*sc,sn),'seriesRateAllowed':sdiv(100*scd,snd),'rzRate':rzv,
             'stuffRate_def':sdiv(100*(drush.yds<=0).sum(),len(drush)),'havocRate_def':sdiv(100*(hp+hr+ffs),len(ds_)),
             'epaPerDrive':sdiv(depa,len(tdr)),'epaPerDriveAllowed':sdiv(depa_o,len(odr))}
    ov={k:{'value':r1(v,3),'pct':None,'_raw':(None if v is None else float(v))} for k,v in ov_vals.items()}
    return {'overall':ov,'production':prod,'rushing':rush,'explosiveness':expl,'situational':sit,'drives':drv,'defensive':dfn,'turnovers':tov,'conversions':conv,'opportunities':oppd}

SPLITS={'q1':[1],'q2':[2],'q3':[3],'q4':[4],'h1':[1,2],'h2':[3,4],'thru3':[1,2,3]}
def game_boxes(g):
    from nfl_drives import build_drives
    g=g.sort_values('play_id')
    home=g.home_team.iloc[0]; away=g.away_team.iloc[0]
    drives=build_drives(g)
    full={home:team_box(g,home,away,drives), away:team_box(g,away,home,drives)}
    per={}
    for k,ps in SPLITS.items():
        gs=g[g.qtr.isin(ps)]; ds=[x for x in drives if x['q1'] in ps]
        per[k]={home:team_box(gs,home,away,ds,True,g,ps,drives), away:team_box(gs,away,home,ds,True,g,ps,drives)}
        for t in (home,away):
            o_=per[k][t]['opportunities']
            if o_['trips']==0 and o_['tripsAllowed']==0: per[k][t]['opportunities']=None
    chart=[{k:v for k,v in x.items() if not k.startswith('_')} for x in drives]
    return full, per, chart
