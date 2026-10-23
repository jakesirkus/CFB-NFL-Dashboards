import pandas as pd, numpy as np
NONPLAY={'Timeout','End Period','End of Half','End of Game','End of Regulation','Kickoff','Kickoff Return (Offense)','Kickoff Return Touchdown','Uncategorized'}
def r1(x,n=1): 
    return None if x is None or (isinstance(x,float) and np.isnan(x)) else round(float(x),n)
def sdiv(a,b): return a/b if b else None
def mmss(s): s=int(max(s,0)); return f"{s//60}:{s%60:02d}"

def line_yards(g):
    if g<0: return 1.2*g
    if g<=4: return g
    if g<=10: return 4+0.5*(g-4)
    return 7.0

def drive_result(rows, team):
    last=rows.iloc[-1]; pt=last.PlayType; txt=str(last.PlayText)
    types=set(rows.PlayType)
    if 'Interception Return Touchdown' in types: return 'Interception (Pick-6)'
    if 'Fumble Return Touchdown' in types: return 'Fumble'
    if ({'Passing Touchdown','Rushing Touchdown'}&types) or (rows.Scoring.fillna(False).astype(bool)&rows.is_rp).any(): return 'Touchdown'
    if types & {'Interception','Pass Interception Return'}: return 'Interception'
    if 'Fumble Recovery (Opponent)' in types: return 'Fumble'
    if 'Field Goal Good' in types: return 'Field Goal'
    if types & {'Field Goal Missed','Blocked Field Goal','Missed Field Goal Return','Blocked Field Goal Touchdown'}: return 'Missed FG'
    if types & {'Punt','Blocked Punt','Punt Return Touchdown','Blocked Punt Touchdown'}: return 'Punt'
    if 'Safety' in types: return 'Safety'
    rp=rows[rows.is_rp]
    if len(rp) and rp.iloc[-1].Down==4 and not rp.iloc[-1].succ: return 'Turnover on Downs'
    per=int(rows.Period.max())
    return 'End of Half' if per==2 else ('End of Game' if per>=4 else 'End of Quarter')
COLOR={'Touchdown':'blue','Field Goal':'blue','Interception (Pick-6)':'blue','Punt':'gray','End of Half':'gray','End of Game':'gray','End of Quarter':'gray','Incomplete':'gray',
       'Interception':'red','Fumble':'red','Turnover on Downs':'red','Missed FG':'red','Safety':'red'}
HOW={'Punt':'PUNT','Interception':'INT','Interception (Pick-6)':'KO','Fumble':'FUMB','Turnover on Downs':'DOWNS','Missed FG':'MISS','Touchdown':'KO','Field Goal':'KO','Safety':'KO','End of Half':'KO','End of Game':None,'End of Quarter':None}

def build_drives(g):
    """g: full game rows (prepped, sorted by Id). Returns list of drive dicts (chronological)."""
    drives=[]
    for did, rows in g.groupby('DriveId', sort=False):
        rows=rows.sort_values('Id')
        body=rows[~rows.PlayType.isin(NONPLAY)]
        rp=body[body.is_scrim]
        if len(rp)==0 and not len(body): continue
        team = rp.Offense.mode().iloc[0] if len(rp) else body.Offense.mode().iloc[0]
        opp = rows.Defense[rows.Offense==team].iloc[0] if (rows.Offense==team).any() else rows.Offense.iloc[0]
        first = body.iloc[0]; last = body.iloc[-1]
        res = drive_result(body, team)
        start_ytg = float(first.YardsToGoal)
        if res=='Touchdown': end_spot=100
        elif res in ('Field Goal','Missed FG','Punt'): end_spot=int(100-last.YardsToGoal)
        elif len(rp): 
            lr=rp.iloc[-1]; end_spot=int(100-lr.YardsToGoal+ (lr.YardsGained if res not in ('Interception','Fumble','Interception (Pick-6)') else 0))
        else: end_spot=int(100-start_ytg)
        end_spot=max(0,min(100,end_spot))
        # score after drive from team's perspective
        lastrow=rows.iloc[-1]
        if lastrow.Offense==team: ts,os_=lastrow.OffenseScore,lastrow.DefenseScore
        else: ts,os_=lastrow.DefenseScore,lastrow.OffenseScore
        q1,q2=int(first.Period),int(last.Period); c1,c2=first.clock,last.clock
        top = (c1-c2) if q1==q2 else (c1 + (q2-q1-1)*900 + (900-c2))
        pl=[]
        for _,p in body.iterrows():
            pen = p.PlayType=='Penalty'
            isplay = p.is_scrim or p.PlayType not in ('Penalty',)
            pl.append({'q':int(p.Period),'text':str(p.PlayText),'scoring':bool(p.Scoring) if pd.notna(p.Scoring) else False,'penalty':bool(pen),
                       'down':int(p.Down) if (p.is_scrim or pen) and pd.notna(p.Down) and p.Down>0 else None,
                       'distance':int(p.Distance) if (p.is_scrim or pen) and pd.notna(p.Distance) and p.Down>0 else None,
                       'goalToGo':bool(pd.notna(p.Distance) and pd.notna(p.YardsToGoal) and p.Down>0 and p.Distance>=p.YardsToGoal),
                       'yardline100':int(p.YardsToGoal) if (p.is_scrim or pen) and pd.notna(p.YardsToGoal) else None,
                       **({'penaltyTeam':None,'penaltyType':None,'penaltyYards':None} if pen else {})})
        nplays=int((body.PlayType!='Penalty').sum() + body.is_penplay.sum())
        drives.append({'team':team,'opponent':opp,'q1':q1,'t1':mmss(c1),'spot1':float(100-start_ytg),'q2':q2,'t2':mmss(c2),'spot2':end_spot,
                       'plays':nplays,'yards':int(rp[rp.is_rp].YardsGained.sum()),'top':mmss(top),'result':res,'color':COLOR.get(res,'gray'),'clickable':True,
                       'opp30':bool((body.YardsToGoal<=30).any() and len(rp)>0),'playText':str(last.PlayText),'playList':pl,
                       'teamScore':int(ts),'oppScore':int(os_),'scored':res in ('Touchdown','Field Goal'),
                       '_rows':rows,'_start_ytg':start_ytg,'_min_ytg':float(body.YardsToGoal.min()) if len(body) else start_ytg,
                       '_epa':float(rp.Ppa.sum(skipna=True)),'_scrim':int(rp.is_scrim.sum()),'_yds':float(rp.yds.sum())})
    # 'how' = how previous drive ended (from the receiving team's view)
    prev=None
    for i,d in enumerate(drives):
        d['n']=i+1
        if prev is None or d['q1']!=prev['q2'] and d['q1']==3: d['how']='KO'
        else: d['how']=HOW.get(prev['result'],'KO')
        prev=d
    return drives

def series_counts(rows):
    # flags come from prep2: a series starts at each fresh set of downs; it converts on a
    # gained first down, a first down by penalty, or a touchdown
    return int(rows.series_start.sum()), int(rows.conv.sum())

def team_box(g, team, opp, drives, ev=None):
    o=g[g.Offense==team]; d=g[g.Offense==opp]
    os_=o[o.is_scrim]; orp=o[o.is_rp]; orush=o[o.is_rush]; opass=o[o.is_pass]
    ds_=d[d.is_scrim]; drp=d[d.is_rp]; drush=d[d.is_rush]; dpass=d[d.is_pass]
    n=len(os_); yards=float(os_.yds.sum())
    ex=os_[os_.YardsToGoal<5]; nin=len(os_)-len(ex)
    epa=float(os_.Ppa.sum()); nepa=int(os_.Ppa.notna().sum()); 
    prod={'scrimPlays':float(n),'yards':yards,'ypp':r1(sdiv(os_[os_.YardsToGoal>=5].yds.sum(),nin),3),'yppExcludedPlays':float(len(ex)),
          'epa':r1(epa,1),'epaPlay':r1(sdiv(epa,nepa),3),
          'passYds':float(opass.YardsGained.sum()),'passYpp':r1(sdiv(opass.YardsGained.sum(),len(opass)),3),'passEpa':r1(opass.Ppa.sum(),1),'passEpaPlay':r1(sdiv(opass.Ppa.sum(),len(opass)),3),
          'rushYds':float(orush.YardsGained.sum()),'rushYpp':r1(sdiv(orush.YardsGained.sum(),len(orush)),3),'rushEpa':r1(orush.Ppa.sum(),1),'rushEpaPlay':r1(sdiv(orush.Ppa.sum(),len(orush)),3)}
    ra=len(orush); gy=orush.YardsGained
    power=orush[(orush.Distance<=2)&orush.Down.isin([3,4])&orush.sr_play]
    opp_runs=orush[gy>=4]
    ly=gy.apply(line_yards)
    hy=opp_runs.YardsGained.apply(lambda y: 0.5*(min(y,10)-4)+max(y-10,0))
    rush={'scrimPlays':float(n),'rushAtt':float(ra),'rushShare':sdiv(100*ra,n),'powerAtt':float(len(power)),'powerRate':r1(sdiv(100*power.succ2.sum(),len(power))),
          'stuffedRuns':float((gy<=0).sum()),'stuffRate':r1(sdiv(100*(gy<=0).sum(),ra)),'stoppedRuns':float((gy<=2).sum()),'stoppedRate':r1(sdiv(100*(gy<=2).sum(),ra)),
          'opportunityRuns':float(len(opp_runs)),'opportunityRate':r1(sdiv(100*len(opp_runs),ra)),'lineYardsTotal':r1(ly.sum(),0),'lineYardsPerCarry':r1(sdiv(ly.sum(),ra),2),
          'highlightYardsTotal':r1(hy.sum(),0),'highlightYardsPerOpp':r1(sdiv(hy.sum(),len(opp_runs)),2)}
    ne=orp[~orp.expl]
    expl={'playsTotal':float(len(o)),'scrimPlays':float(n),'explosivePlays':float(o.expl.sum()),'explPass':float(o.expl_pass.sum()),'explRush':float(o.expl_rush.sum()),
          'nonExplEpaPlay':r1(sdiv(ne.Ppa.sum(),len(ne)),2),'nonExplPassEpaPlay':r1(sdiv(ne[ne.is_pass].Ppa.sum(),ne.is_pass.sum()),2),'nonExplRushEpaPlay':r1(sdiv(ne[ne.is_rush].Ppa.sum(),ne.is_rush.sum()),2)}
    srp=o[o.sr_play]                      # rush/pass plays + first downs by penalty
    e=orp[orp.early]; l=orp[orp.late]; es=srp[srp.early]; ls=srp[srp.late]
    m8f=lambda x: x[((x.Period==2)&(x.clock<=240))|((x.Period==3)&(x.clock>=660))]
    m8=m8f(orp)
    # Situational panel = "Successful Plays (EPA>0)": a rush/pass with positive EPA, or a first down by penalty
    def esucc(x): return ((x.Ppa>0)&x.is_rp)|x.pen_fd
    def sr(x): return r1(sdiv(100*esucc(x).sum(),len(x)))
    rps=srp[srp.is_rp]
    sit={'successPlays':float(esucc(srp).sum()),'successPlaysRate':sr(srp),'successPassRate':sr(rps[rps.is_pass]),'successRushRate':sr(rps[rps.is_rush]),
         'penaltyFirstDowns':float(o.pen_fd.sum()),
         'stdDownPlays':float((~orp.passdown).sum()),'passDownPlays':float(orp.passdown.sum()),
         'earlyDownFirstDowns':float((((e.YardsGained>=e.Distance)|e.Scoring.fillna(False).astype(bool))&~e.pen_fd).sum()+es.pen_fd.sum()),
         'earlyEpa':r1(e.Ppa.sum()),'earlyEpaPlay':r1(sdiv(e.Ppa.sum(),len(e)),3),'earlyPass':float(e.is_pass.sum()),'earlyRush':float(e.is_rush.sum()),
         'earlyPassSuccessRate':sr(es[es.is_pass]),'earlyRushSuccessRate':sr(es[es.is_rush]),
         'lateEpa':r1(l.Ppa.sum()),'lateEpaPlay':r1(sdiv(l.Ppa.sum(),len(l)),2),'latePass':float(l.is_pass.sum()),'lateRush':float(l.is_rush.sum()),
         'latePassSuccessRate':sr(ls[ls.is_pass]),'lateRushSuccessRate':sr(ls[ls.is_rush]),
         'avgDist3rd':r1(orp[orp.Down==3].Distance.mean()) if (orp.Down==3).any() else None,
         'mid8Epa':r1(m8.Ppa.sum()),'mid8EpaPlay':r1(sdiv(m8.Ppa.sum(),len(m8)),2),'mid8Pass':float(m8.is_pass.sum()),'mid8Rush':float(m8.is_rush.sum()),
         'mid8PassSuccessRate':sr(m8f(rps)[m8f(rps).is_pass]),'mid8RushSuccessRate':sr(m8f(rps)[m8f(rps).is_rush])}
    tdr=[x for x in drives if x['team']==team and x['_scrim']>0]; odr=[x for x in drives if x['team']==opp and x['_scrim']>0]
    dsum=lambda ds,k: sum(x[k] for x in ds)
    drv={'total':len(tdr),'avgStartFP':r1(sdiv(sum(x['spot1'] for x in tdr),len(tdr))),'playsPerDrive':sdiv(dsum(tdr,'_scrim'),len(tdr)),
         'yardsPerDrive':sdiv(dsum(tdr,'_yds'),len(tdr)),'availYardsPct':r1(sdiv(100*dsum(tdr,'_yds'),dsum(tdr,'_start_ytg'))),'epaPerDrive':r1(sdiv(epa,len(tdr)),2)}
    stops=[x for x in odr if x['result'] in ('Punt','Interception','Interception (Pick-6)','Fumble','Turnover on Downs','Missed FG','Safety')]
    dtxt=drp.PlayText.fillna('')
    tfl=int((drush.YardsGained<=0).sum()); sacks=int(dpass.is_sack.sum()); pbu=int(dtxt.str.contains('broken up',case=False).sum())
    ints=int(d['int'].sum()); ff=int(d.PlayText.fillna('').str.contains('forced by',case=False).sum())
    hp=sacks+pbu+ints; hr=tfl
    dfn={'scrimPlays':float(len(ds_)),'stopRate':r1(sdiv(100*len(stops),len(odr))),'havocPlays':float(hp+hr+ff),'havocRate':r1(sdiv(100*(hp+hr+ff),len(ds_))),
         'havocPass':float(hp),'havocRush':float(hr),'tflRush':float(tfl),'sacks':float(sacks),'pbu':float(pbu),'ints':float(ints),'ff':float(ff),
         'epaPerDriveAllowed':r1(sdiv(float(ds_.Ppa.sum()),len(odr)),2)}
    fe=int(o.is_fumrow.sum()+o.PlayText.fillna('').str.contains('fumble',case=False)[o.is_rp].sum()); 
    fl=int(o.fum_lost.sum()); fo=int(o.fum_own.sum()); gi=int(o['int'].sum())
    give=fl+gi; take=int(d.fum_lost.sum()+d['int'].sum())
    tov={'giveaways':float(give),'takeaways':float(take),'fumbleEvents':float(max(fl+fo,0)),'fumblesLost':float(fl),'fumblesOwnRecov':float(fo),'ints':float(gi),'margin':float(take-give)}
    t3=orp[orp.Down==3]; t4=orp[orp.Down==4]
    sn,sc=series_counts(o); snd,scd=series_counts(d)
    conv={'thirdConv':float(t3.succ.sum()),'thirdAtt':float(len(t3)),'thirdRate':r1(sdiv(100*t3.succ.sum(),len(t3))),'fourthConv':float(t4.succ.sum()),'fourthAtt':float(len(t4)),
          'fourthRate':r1(sdiv(100*t4.succ.sum(),len(t4))),'seriesConv':float(sc),'series':float(sn),'seriesRate':r1(sdiv(100*sc,sn)),
          'seriesConvAllowed':float(scd),'seriesAllowed':float(snd),'seriesRateAllowed':r1(sdiv(100*scd,snd))}
    def opps(ds):
        trips=[x for x in ds if x['_min_ytg']<=40]
        pts=sum(7 if x['result']=='Touchdown' else 3 if x['result']=='Field Goal' else 0 for x in trips)
        tds=sum(x['result']=='Touchdown' for x in trips); fgs=sum(x['result']=='Field Goal' for x in trips)
        return trips,pts,tds,fgs
    tr,pts,tds,fgs=opps(tdr); tra,ptsa,tdsa,fgsa=opps(odr)
    oppd={'trips':len(tr),'points':pts,'ppo':r1(sdiv(pts,len(tr)),2),'tds':tds,'fgs':fgs,'busts':sum(1 for x in tr if not x['scored']),
          'tripsAllowed':len(tra),'pointsAllowed':ptsa,'ppoAllowed':r1(sdiv(ptsa,len(tra)),2),'tdsAllowed':tdsa,'fgsAllowed':fgsa,
          'stopsInside30':sum(1 for x in odr if x['_min_ytg']<=30 and not x['scored'])}
    rz=[x for x in tdr if x['_min_ytg']<=20]
    ov_vals={'epaPlay':prod['epaPlay'],'successRate':sdiv(100*srp.succ2.sum(),len(srp)),'ypp':prod['ypp'],'passEpaPlay':prod['passEpaPlay'],'rushEpaPlay':prod['rushEpaPlay'],
             'passYpp':prod['passYpp'],'explosiveRate':sdiv(100*o.expl.sum(),n),'thirdRate':sdiv(100*t3.succ.sum(),len(t3)),'seriesRate':sdiv(100*sc,sn),
             'seriesRateAllowed':sdiv(100*scd,snd),'rzRate':sdiv(100*sum(x['result']=='Touchdown' for x in rz),len(rz)),
             'stuffRate_def':sdiv(100*(drush.YardsGained<=0).sum(),len(drush)),'havocRate_def':dfn['havocRate'],
             'epaPerDrive':sdiv(epa,len(tdr)),'epaPerDriveAllowed':sdiv(float(ds_.Ppa.sum()),len(odr))}
    ov={k:{'value':r1(v,3),'pct':None} for k,v in ov_vals.items()}
    pen=penalty_section(ev, team, opp, g)
    return {'overall':ov,'penalties':pen,'production':prod,'rushing':rush,'explosiveness':expl,'situational':sit,'drives':drv,'defensive':dfn,'turnovers':tov,'conversions':conv,'opportunities':oppd}

def penalty_section(ev, team, opp, g):
    if ev is None: return None
    pers=set(g.Period.unique())
    e=ev[ev.Period.isin(pers)]
    mine=e[e.team==team]; theirs=e[e.team==opp]
    def impact(x, sign):
        # epa_off is from the snapping offense's view; committing on defense flips the sign
        v=x.dropna(subset=['epa_off'])
        return float((np.where(v.side=='off', v.epa_off, -v.epa_off)*sign).sum())
    com=impact(mine, 1.0); drw=impact(theirs, -1.0)
    return {'penalties':int(len(mine)),'penaltyYds':int(mine.yards.fillna(0).sum()),
            'offPenalties':int((mine.side=='off').sum()),'defPenalties':int((mine.side=='def').sum()),
            'fdAllowed':int(mine.fd.sum()),'fdGained':int(theirs.fd.sum()),
            'oppPenalties':int(len(theirs)),'oppPenaltyYds':int(theirs.yards.fillna(0).sum()),
            'epaCommitted':r1(com,2),'epaDrawn':r1(drw,2),'epaNet':r1(com+drw,2)}

SPLITS={'q1':[1],'q2':[2],'q3':[3],'q4':[4],'h1':[1,2],'h2':[3,4],'thru3':[1,2,3]}
def game_boxes(g, home, away, ev=None):
    drives=build_drives(g)
    full={home:team_box(g,home,away,drives,ev), away:team_box(g,away,home,drives,ev)}
    per={}
    for k,ps in SPLITS.items():
        gs=g[g.Period.isin(ps)]
        ds=[x for x in drives if x['q1'] in ps]
        per[k]={home:team_box(gs,home,away,ds,ev), away:team_box(gs,away,home,ds,ev)}
    chart=[{k:v for k,v in x.items() if not k.startswith('_')} for x in drives]
    return full, per, chart
