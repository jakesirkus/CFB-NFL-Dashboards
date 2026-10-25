import pandas as pd, numpy as np
NONPLAY={'Timeout','End Period','End of Half','End of Game','End of Regulation','Kickoff','Kickoff Return (Offense)','Kickoff Return Touchdown'}
def r1(x,n=1): 
    return None if x is None or (isinstance(x,float) and np.isnan(x)) else round(float(x),n)
def sdiv(a,b): return a/b if b else None
def mmss(s): s=int(max(s,0)); return f"{s//60}:{s%60:02d}"

def line_yards(g):
    if g<0: return 1.2*g
    if g<=4: return g
    if g<=10: return 4+0.5*(g-4)
    return 7.0

PUNT_T={'Punt','Punt Return','Punt Return Touchdown','Blocked Punt','Blocked Punt Touchdown'}
MISS_T={'Field Goal Missed','Blocked Field Goal','Blocked Field Goal Touchdown','Missed Field Goal Return'}
FUM_T={'Fumble','Fumble Recovery (Opponent)','Fumble Return Touchdown'}
def drive_result(rows, team, next_team, amap=None):
    # play types are only trusted on rows that weren't overturned and aren't the opening kickoff
    # (a kickoff the receiving team fumbled is the KICKING team's row, handled as its own entry)
    _txt=rows.PlayText.fillna('')
    _ok=~_txt.str.contains(r'overturned|is reversed', case=False, regex=True) & ~(_txt.str.contains('kickoff', case=False) & ~rows.is_rp)
    types=set(rows[_ok].PlayType); last=rows.iloc[-1]
    lt0=str(last.PlayText).lower()
    types0=set(rows.PlayType)
    if ((types0 & PUNT_T) or 'punt' in lt0) and ('muff' in lt0 or 'fumbled' in lt0) and next_team==team: return 'Muffed Punt'
    # turnovers come from turnovers.flag_game (play text + who had the ball next), not the feed's label
    own=rows[rows.Offense==team]          # only this offense's own turnovers end its drive
    if 'fum_td' in rows and own.fum_td.any(): return 'Fumble (Defensive TD)'
    if 'int_td' in rows and own.int_td.any(): return 'Interception (Pick-6)'
    if 'touchdown' in lt0 and last.PlayType not in ('Rushing Touchdown','Passing Touchdown') and not _re.search(r'overturned|is reversed|nullified|no play', lt0):
        if 'intercepted' in lt0: return 'Interception (Pick-6)'
        if 'fumble' in lt0 and 'recovered by' in lt0 and td_scorer(last, amap or {}) != team: return 'Fumble (Defensive TD)'
    if (rows.Scoring.fillna(False).astype(bool) & rows.is_rp & ~rows.giveaway).any(): return 'Touchdown'
    if ('touchdown' in lt0 or 'for a td' in lt0 or (last.Scoring==True and _re.search(r'\d+ yd .*\((.*kick|.*pat|.*two)', lt0))) and not _re.search(r'no play|nullified|overturned|reversed', lt0) and last.PlayType not in PUNT_T and td_scorer(last, amap or {})==team:
        return 'Touchdown'          # e.g. the offense recovers its own fumble in the end zone
    if own['int'].any(): return 'Interception'
    if own.fum_lost.any(): return 'Fumble'
    if 'Interception Return Touchdown' in types: return 'Interception (Pick-6)'
    if 'Fumble Return Touchdown' in types: return 'Fumble (Defensive TD)'
    if 'Punt Return Touchdown' in types: return 'Punt (Return TD)'
    if any(kick_return_td(r_) and 'punt' in str(r_.PlayText).lower() for r_ in rows.itertuples()): return 'Punt (Return TD)'
    # missed field goal caught in the end zone and run back for a TD (the feed types it as a kickoff)
    if any(kick_return_td(r_) and 'field goal attempt' in str(r_.PlayText).lower() for r_ in rows.itertuples()): return 'Missed FG (Return TD)'
    if 'Blocked Punt Touchdown' in types: return 'Blocked Punt (TD)'
    if 'Blocked Field Goal Touchdown' in types: return 'Blocked FG (TD)'
    if (rows.Scoring.fillna(False).astype(bool) & rows.is_rp & ~rows.giveaway).any() or ({'Passing Touchdown','Rushing Touchdown'} & types): return 'Touchdown'
    if types & {'Interception','Pass Interception Return'}: return 'Interception'
    if 'Fumble Recovery (Opponent)' in types: return 'Fumble'
    lt=str(last.PlayText).lower()
    if 'safety' in lt and 'no play' not in lt and 'Safety' not in types: return 'Safety'
    if 'touchdown' in lt and next_team is not None and ('fumble' in lt or 'intercepted' in lt) and last.PlayType not in ('Rushing Touchdown','Passing Touchdown') and not _re.search(r'overturned|is reversed|nullified|no play', lt):
        if ('recovered by' in lt or 'intercepted' in lt) and td_scorer(last, amap or {})!=team:   # an offense recovering its own fumble in the end zone is ITS touchdown
            return 'Interception (Pick-6)' if 'intercepted' in lt else 'Fumble (Defensive TD)'
    # the feed sometimes tags a LOST fumble as 'Fumble Recovery (Own)'; the possession change is the reliable signal
    # text fallback only when the play says the OTHER team recovered and nothing was overturned
    _rv=_re.compile(r'recovered by\s+([A-Za-z&\.\'\-]+)').findall(str(last.PlayText))
    _ovr=bool(_re.search(r'overturned|reversed|nullified|no play', lt))
    if 'fumble' in lt and _rv and (amap or {}).get(_rv[-1]) not in (None,team) and not _ovr and next_team is not None and next_team != team and not (types & (PUNT_T|MISS_T|{'Field Goal Good'})) and 'punt' not in lt: return 'Fumble'
    if 'intercepted' in lt and not _ovr and next_team is not None and next_team != team: return 'Interception'
    _fg=rows[rows.PlayType=='Field Goal Good']
    if len(_fg) and 'no good' in str(_fg.iloc[-1].PlayText).lower():
        _t=str(_fg.iloc[-1].PlayText).lower()
        return ('Blocked FG (TD)' if 'touchdown' in _t else 'Blocked FG') if 'blocked' in _t else 'Missed FG'
    if 'Field Goal Good' in types: return 'Field Goal'
    if 'Blocked Field Goal' in types: return 'Blocked FG'
    if types & MISS_T: return 'Missed FG'
    if types & PUNT_T: return 'Punt'
    if 'Safety' in types: return 'Safety'
    rp=rows[rows.is_rp]
    per=int(rows.Period.max())
    if len(rp) and rp.iloc[-1].Down==4 and not rp.iloc[-1].succ and next_team is not None and next_team != team: return 'Turnover on Downs'
    if per==2 or 'End of Half' in types: return 'End of Half'
    if per>=4: return 'End of Game'
    if next_team is not None and next_team != team and len(rp) and rp.iloc[-1].Down==4: return 'Turnover on Downs'
    if 'turnover on downs' in lt: return 'Turnover on Downs'
    return 'End of Quarter'
COLOR={'Missed FG (Return TD)':'blue','Muffed Punt':'red','Touchdown':'blue','Field Goal':'blue','Interception (Pick-6)':'blue','Fumble (Defensive TD)':'blue','Punt (Return TD)':'blue','Blocked Punt (TD)':'blue',
       'Blocked FG (TD)':'blue','Kickoff (Return TD)':'blue','Blocked FG':'red','Punt':'gray','End of Half':'gray','End of Game':'gray','Incomplete':'gray',
       'Interception':'red','Fumble':'red','Turnover on Downs':'red','Missed FG':'red','Safety':'red'}
HOW={'Muffed Punt':'FUMB','Muffed Kickoff':'FUMB','Fumble (Defensive TD)':'KO','Punt (Return TD)':'KO','Blocked Punt (TD)':'KO','Blocked FG (TD)':'KO','Kickoff (Return TD)':'KO','Blocked FG':'MISS','Punt':'PUNT','Interception':'INT','Interception (Pick-6)':'KO','Fumble':'FUMB','Turnover on Downs':'DOWNS','Missed FG':'MISS','Touchdown':'KO','Field Goal':'KO','Safety':'KO','End of Half':'KO','End of Game':None}

import re as _re
def pat_points(txt):
    t=str(txt).lower()
    if _re.search(r'(pass|rush|run) attempt (failed|no good|unsuccessful|incomplete)', t): return 0
    if _re.search(r'(pass|rush|run) attempt (successful|good|is good)', t): return 2
    if _re.search(r'two[- ]point|2pt|2-pt|two point', t):
        return 0 if _re.search(r'fail|no good|unsuccessful|incomplete', t) else 2
    if _re.search(r'pat (missed|blocked|failed|no good)|kick (missed|blocked|failed|no good)|kick attempt (failed|missed|no good|blocked)|extra point (failed|missed|no good|blocked)', t): return 0
    return 1

import re as _re2
_KRET=_re2.compile(r'return(?:ed)?\s+(?:for\s+)?-?\d+\s+yards?\s+to the \S*?00\b[^()]*?touchdown')
KICK_T={'Kickoff','Kickoff Return (Offense)','Punt','Punt Return','Kickoff Return Touchdown','Punt Return Touchdown','Missed Field Goal Return'}
def kick_return_td(r):
    """kickoff/punt returned for a TD by the RECEIVING team (no fumble on the return)"""
    tl=str(r.PlayText).lower()
    if r.PlayType in ('Kickoff Return Touchdown','Punt Return Touchdown'): return 'fumble' not in tl and 'nullified' not in tl
    return r.PlayType in KICK_T and 'no play' not in tl and 'nullified' not in tl and 'fumble' not in tl and 'muff' not in tl and bool(_KRET.search(tl))
RET_TD={'Kickoff Return Touchdown','Punt Return Touchdown','Blocked Punt Touchdown','Blocked Field Goal Touchdown','Interception Return Touchdown','Fumble Return Touchdown'}
_REC=_re.compile(r'recovered by\s+([A-Za-z&\.\'\-]+)')
def td_scorer(r, amap):
    """Who scored on a touchdown row. Returns team or None."""
    t=str(r.PlayText); tl=t.lower()
    if r.PlayType in RET_TD:
        # the feed types an offense recovering its OWN fumble in the end zone as 'Fumble Return Touchdown'
        m=_REC.search(t) if 'fumbl' in tl else None
        if m and amap.get(m.group(1))==r.Offense: return r.Offense
        return r.Defense
    if kick_return_td(r): return r.Defense
    if 'blocked' in tl and 'return' in tl and 'fumble' not in tl and r.PlayType not in ('Rushing Touchdown','Passing Touchdown'): return r.Defense   # blocked kick returned for a TD
    if 'blocked' in tl and 'fumble' not in tl and r.PlayType in ('Punt','Field Goal Missed','Blocked Punt','Blocked Field Goal','Punt Return'):
        m=_REC.search(t)                          # blocked kick recovered in the end zone ('blocked by #5 ... recovered by UC #5 ... TOUCHDOWN')
        return (amap.get(m.group(1)) if m else None) or r.Defense
    if 'intercepted' in tl and ('return' in tl or 'touchdown' in tl) and r.PlayType not in ('Rushing Touchdown','Passing Touchdown'): return r.Defense
    if 'fumble' in tl and r.PlayType not in ('Rushing Touchdown','Passing Touchdown'):
        m=_REC.search(t)
        if m:
            tm=amap.get(m.group(1))
            if tm is not None: return tm
            return r.Defense if 'return' in tl else r.Offense
    return r.Offense
def score_events(order, amap):
    """(DriveNumber, team, points) for every score, in possession order."""
    ev=[]
    for _,r in order.iterrows():
        pt=r.PlayType; tl=str(r.PlayText).lower()
        ov=SCORE_OVERRIDES.get(str(int(r.Id))) if 'Id' in r else None
        if ov is not None:                      # hand-verified scoring for plays the feed gets wrong / leaves out
            for e in ov['events']: ev.append((r.DriveNumber, e[0], int(e[1])))
            continue
        is_td = pt in RET_TD or pt in ('Rushing Touchdown','Passing Touchdown') or (r.Scoring==True and ('touchdown' in tl or 'for a td' in tl)) or kick_return_td(r)
        # 'TOUCHDOWN nullified by penalty' (make_tables rewrites it to SCORE NULLIFIED) is not a score, even when the
        # feed still types the row as a touchdown
        if is_td and 'score nullified' in tl and 'touchdown' not in tl: is_td=False
        if is_td and (pt not in ('Field Goal Good','Safety') or 'no good' in tl):
            ev.append((r.DriveNumber, td_scorer(r, amap), 6+pat_points(r.PlayText)))
        elif (pt=='Field Goal Good' or (r.Scoring==True and 'field goal' in tl and 'good' in tl)) and 'no good' not in tl: ev.append((r.DriveNumber, r.Offense, 3))
        elif pt=='Safety' or (r.Scoring==True and 'safety' in tl): ev.append((r.DriveNumber, r.Defense, 2))
        elif pt=='Defensive 2pt Conversion': ev.append((r.DriveNumber, r.Defense, 2))
    return ev

import os as _os, json as _json
_OF=_os.path.join(_os.path.dirname(_os.path.abspath(__file__)),'official_finals.json')
OFFICIAL_FINALS=_json.load(open(_OF)) if _os.path.exists(_OF) else {}
_SO=_os.path.join(_os.path.dirname(_os.path.abspath(__file__)),'score_overrides.json')
SCORE_OVERRIDES=_json.load(open(_SO)) if _os.path.exists(_SO) else {}
_SPOT=_re.compile(r'(?:\bat|to the|from)\s+(?:the\s+)?([A-Za-z&\.\']+?)\s?(\d{1,2})\b')
def _spot_from_text(txt, team, amap):
    """yards to goal for `team` from a play's 'at NAVY45' / 'to the Tulsa06' (where the play STARTED is the
    first such mention for kneels/spikes; for other plays we only use it when it is the ball spot)"""
    t=str(txt)
    m=_SPOT.search(t)
    if not m or not amap: return None
    ab=m.group(1).lower(); side=next((v for k,v in amap.items() if str(k).lower()==ab),None)
    if side is None and str(team).lower().startswith(ab): side=team
    if side is None: return None
    n=int(m.group(2))
    if 'kneel' not in t.lower(): return None          # only trust it for kneel-downs (spot = where the ball was)
    return 100-n if side==team else n
def build_drives(g):
    """g: full game rows (prepped). Possessions follow the feed's DriveNumber sequence -- play Ids
    are NOT reliably chronological (late data corrections get appended with higher Ids), so
    ordering by Id scrambles drives. Plays within a drive are ordered by quarter, clock, then Id."""
    g=g.copy(); g['_ord_clock']=-g['clock']
    g['_kneel']=(g.PlayType=='Rush')&g.PlayText.fillna('').str.contains('kneel',case=False)
    g['_snap']=g.is_scrim|g._kneel
    order=g.sort_values(['DriveNumber','Period','_ord_clock','Id']).copy()
    teams=list(pd.unique(pd.concat([g.Offense,g.Defense])))
    # final score = the score fields on the LAST play in game-clock order. (The max over all rows is
    # not safe: the feed sometimes carries a bogus score on a stray row, e.g. VT-Cal 2026 wk6 showed
    # VT with 25 on an early row, which made a 20-25 loss look like a 25-25 tie.)
    tim=g[g.OffenseScore.notna()&g.DefenseScore.notna()].sort_values(['Period','_ord_clock','Id'])
    final={t:0 for t in teams}
    if len(tim):
        lr=tim.iloc[-1]; final[lr.Offense]=int(lr.OffenseScore); final[lr.Defense]=int(lr.DefenseScore)
    # verified official finals (official_finals.json) override the feed when the feed's score fields are wrong
    ov=OFFICIAL_FINALS.get(str(int(g.GameId.iloc[0]))) if 'GameId' in g and len(g) else None
    if ov and set(ov)==set(teams): final=dict(ov)
    dns=sorted(order.DriveNumber.dropna().unique())
    # score after each possession: rebuilt from the scoring plays; if that tally doesn't land on the
    # final, fall back to the feed's score on the last row (in clock order) up to the end of each
    # possession, kept non-decreasing and capped at the final
    from penalties import learn_abbr_map
    amap=learn_abbr_map(g, None, None)
    evs=score_events(order, amap)
    tally={t:0 for t in teams}; after={}
    for dn in dns:
        for e in evs:
            if e[0]==dn and e[1] is not None: tally[e[1]]=tally.get(e[1],0)+e[2]
        after[dn]=dict(tally)
    # when the scoring-play tally agrees with the feed's max score, that's the final (the last row can be stale)
    if not (ov and set(ov)==set(teams)):
        fmax={t:0 for t in teams}
        for r in tim.itertuples():
            fmax[r.Offense]=max(fmax.get(r.Offense,0),int(r.OffenseScore)); fmax[r.Defense]=max(fmax.get(r.Defense,0),int(r.DefenseScore))
        if all(tally.get(t,0)==fmax.get(t,0) for t in teams): final={t:tally.get(t,0) for t in teams}
    if any(tally.get(t,0)!=final.get(t,0) for t in teams):
        after={}; prev={t:0 for t in teams}
        tim=tim.assign(_k=list(zip(tim.Period,tim._ord_clock)))
        for dn in dns:
            dr=order[order.DriveNumber==dn]
            endk=max(zip(dr.Period,dr._ord_clock)) if len(dr) else None
            rr=tim[[(k<endk) or (k==endk and d_<=dn) for k,d_ in zip(tim._k,tim.DriveNumber)]] if endk is not None else tim.iloc[0:0]   # OT drives can share a clock
            sc=dict(prev)
            if len(rr):
                r=rr.iloc[-1]; sc[r.Offense]=int(r.OffenseScore); sc[r.Defense]=int(r.DefenseScore)
            sc={t:min(max(sc.get(t,0),prev.get(t,0)),final.get(t,0)) for t in teams}
            after[dn]=sc; prev=sc
        after[dns[-1]]=dict(final)
    tally_after=after
    _need_rescore=any(tally.get(t,0)!=final.get(t,0) for t in teams)
    cand=[]
    for dn in dns:
        rows=order[order.DriveNumber==dn]
        body=rows[~rows.PlayType.isin(NONPLAY)]
        rp=body[body._snap]
        if len(rp)==0:
            kr=rows[[ (p=='Kickoff Return Touchdown') or (kick_return_td(r_) and 'kickoff' in str(r_.PlayText).lower()) for p,r_ in zip(rows.PlayType,rows.itertuples())]]
            if len(kr): cand.append([dn,kr.iloc[0].Offense,rows,kr,rp.iloc[0:0]]); continue   # kickoff returned for a TD
            kick=body[body.PlayType.isin(PUNT_T|MISS_T|{'Field Goal Good','Safety'})]
            if len(kick): cand.append([dn,kick.iloc[0].Offense,rows,kick,rp.iloc[0:0]])        # e.g. FG right after a takeaway
            continue                      # kickoff-only / timeout-only rows are not possessions
        team=rp.Offense.mode().iloc[0]
        body=body[(body.Offense==team)|body.PlayType.isin(PUNT_T|MISS_T|FUM_T|{'Pass Interception Return','Interception Return Touchdown','Interception','Uncategorized'})]
        cand.append([dn,team,rows,body,rp[rp.Offense==team]])
    # the feed sometimes splits one possession in two at a quarter break: merge them back
    merged=[]
    for c in cand:
        if merged and merged[-1][1]==c[1] and len(c[4]) and len(merged[-1][4]):
            m=merged[-1]
            if drive_result(m[3], m[1], c[1], amap) in ('End of Quarter',):
                merged[-1]=[c[0],m[1],pd.concat([m[2],c[2]]),pd.concat([m[3],c[3]]),pd.concat([m[4],c[4]])]
                continue
        merged.append(c)
    cand=[tuple(c) for c in merged]
    drives=[]
    for i,(dn,team,rows,body,rp) in enumerate(cand):
        opp=[t for t in teams if t!=team]; opp=opp[0] if opp else None
        next_team=cand[i+1][1] if i+1<len(cand) else None
        first=body.iloc[0]; last=body.iloc[-1]
        res='Kickoff (Return TD)' if (len(rp)==0 and any((p=='Kickoff Return Touchdown') or (kick_return_td(r_) and 'kickoff' in str(r_.PlayText).lower()) for p,r_ in zip(body.PlayType,body.itertuples()))) else drive_result(body, team, next_team, amap)
        start_ytg=float(rp.iloc[0].YardsToGoal) if len(rp) else float(first.YardsToGoal)   # first snap, after any pre-snap/return penalty
        if not (start_ytg>0) and len(rp):
            ok=rp[rp.YardsToGoal>0]
            sp=_spot_from_text(rp.iloc[0].PlayText, team, amap)
            if sp is not None: start_ytg=float(sp)
            elif len(ok):
                before=rp.loc[:ok.index[0]].iloc[:-1]
                start_ytg=float(ok.iloc[0].YardsToGoal)+float(before.yds.sum())
                if not (0<start_ytg<100): start_ytg=float(ok.iloc[0].YardsToGoal)
            else: start_ytg=float('nan')
        if res=='Touchdown': end_spot=100
        elif res in ('Field Goal','Missed FG','Punt'): end_spot=int(100-last.YardsToGoal)
        elif len(rp):
            lr=rp.iloc[-1]; end_spot=int(100-lr.YardsToGoal+(lr.YardsGained if res not in ('Interception','Fumble','Interception (Pick-6)') and pd.notna(lr.YardsGained) else 0))
        else: end_spot=int(100-start_ytg)
        end_spot=max(0,min(100,end_spot))
        ts,os_=tally_after[dn].get(team,0),tally_after[dn].get(opp,0)
        c1,c2=first.clock,last.clock; q1,q2=int(first.Period),int(last.Period)
        top=(c1-c2) if q1==q2 else (c1+(q2-q1-1)*900+(900-c2))
        pl=[]
        for _,p in body.iterrows():
            pen=p.PlayType=='Penalty'
            pl.append({'q':int(p.Period),'text':str(p.PlayText),'scoring':bool(p.Scoring==True),'penalty':bool(pen),
                       'down':int(p.Down) if (p.is_scrim or pen) and pd.notna(p.Down) and p.Down>0 else None,
                       'distance':int(p.Distance) if (p.is_scrim or pen) and pd.notna(p.Distance) and p.Down>0 else None,
                       'goalToGo':bool(pd.notna(p.Distance) and pd.notna(p.YardsToGoal) and p.Down>0 and p.Distance>=p.YardsToGoal),
                       'yardline100':int(p.YardsToGoal) if (p.is_scrim or pen) and pd.notna(p.YardsToGoal) else None,
                       **({'penaltyTeam':None,'penaltyType':None,'penaltyYards':None} if pen else {})})
        nplays=int((body.PlayType!='Penalty').sum()+body.is_penplay.sum())
        tsnap=rp[rp.is_scrim & ~rp._kneel & ~rp.PlayText.fillna('').str.contains('NO PLAY')]
        min_snap=float(tsnap.YardsToGoal.min()) if len(tsnap) else 999.0
        if res=='Touchdown':
            tdr_=body[(body.Scoring==True)&(body.Offense==team)]; dpts=6+pat_points(tdr_.iloc[-1].PlayText if len(tdr_) else '')
        else: dpts=3 if res=='Field Goal' else 0
        q1=int(first.Period); q2=int(last.Period)
        drives.append({'_dn':dn,'team':team,'opponent':opp,'q1':q1,'t1':mmss(c1),'spot1':(float(100-start_ytg) if start_ytg==start_ytg else None),'q2':q2,'t2':mmss(c2),'spot2':end_spot,
                       'plays':nplays,'yards':int(rp[rp.is_rp & ~rp.giveaway & ~rp.PlayText.fillna('').str.contains('NO PLAY')].YardsGained.sum()),'top':mmss(max(top,0)),'result':res,'color':COLOR.get(res,'gray'),'clickable':True,
                       'opp30':bool(min_snap<=30),'playText':str(last.PlayText),'playList':pl,
                       'teamScore':int(ts),'oppScore':int(os_),'scored':res in ('Touchdown','Field Goal','Safety') or COLOR.get(res)=='blue',
                       '_trip':bool(min_snap<=30),'_pts':dpts,'_min_snap':min_snap,
                       '_rows':rows,'_start_ytg':start_ytg,'_min_ytg':float(body.YardsToGoal.min()),
                       '_epa':float(rp.Ppa.sum(skipna=True)),'_scrim':int(rp.is_scrim.sum()),'_yds':float(rp.yds.sum())})
    # Muffed / fumbled kicks the KICKING team recovered: show them as a 1-play possession for the
    # receiving team (same convention as the original Week 1-5 drive charts), so the chart explains
    # why the kicking team has the ball again.
    if 'st_lost' in order:
        ins=[]
        for ix,r in order[order.st_lost].iterrows():
            recv=r.Defense; kick=r.Offense; tl=str(r.PlayText).lower()
            is_punt='punt' in tl and 'kickoff' not in tl
            scrim=not is_punt and 'kickoff' not in tl and not _re.search(r'field goal|kick attempt', tl.split('fumbl')[0])
            res=('Muffed Punt' if is_punt else 'Muffed Kickoff') if 'muff' in tl else 'Fumble'
            if 'touchdown' in tl and 'no play' not in tl: res='Fumble (Defensive TD)'     # kicking team scooped it in
            _m=_re.match(r'\((\d{1,2}):(\d{2})\)',str(r.PlayText)); _clk=(int(_m.group(1))*60+int(_m.group(2))) if _m else r.clock
            if scrim and 'touchdown' in tl: continue
            ins.append((r.DriveNumber, is_punt or scrim, {'_dn':r.DriveNumber,'team':recv,'opponent':kick,'q1':int(r.Period),'t1':mmss(_clk),'spot1':None,
                'q2':int(r.Period),'t2':mmss(_clk),'spot2':None,'plays':0,'yards':0,'top':'0:00','result':res,'color':'red','clickable':True,'opp30':False,
                'playText':str(r.PlayText),'playList':[{'q':int(r.Period),'text':str(r.PlayText),'scoring':False,'penalty':False,'down':None,'distance':None,'goalToGo':False,'yardline100':None}],
                'teamScore':None,'oppScore':None,'scored':False,'_trip':False,'_pts':0,'_min_snap':999.0,'_rows':order.iloc[0:0],'_start_ytg':0.0,'_min_ytg':999.0,'_epa':0.0,'_scrim':0,'_yds':0.0}))
        for dn,is_punt,e in ins:
            if is_punt:
                # the punting team's drive ends with the punt; the muff entry goes right after it
                k=next((i for i,d in enumerate(drives) if d['_dn']==dn and d['team']==e['opponent']), None)
                if k is None: continue
                if drives[k]['result']=='Muffed Punt': drives[k]['result']='Punt'; drives[k]['color']='gray'
                # (scrimmage double turnover: the defense's fumble-back goes right after the offense's turnover)
                pos=k+1
            else:
                # kickoff muff: goes right before the kicking team's ensuing possession
                pos=next((i for i,d in enumerate(drives) if d['_dn']>dn or (d['_dn']==dn and d['team']==e['opponent'])), len(drives))
            prev=drives[pos-1] if pos>0 else None
            if e['result']=='Fumble (Defensive TD)':
                e['color']='blue'; e['scored']=True
                if dn in tally_after: e['teamScore']=int(tally_after[dn].get(e['team'],0)); e['oppScore']=int(tally_after[dn].get(e['opponent'],0))
                drives.insert(pos,e); continue
            if prev is None: e['teamScore']=0; e['oppScore']=0
            elif prev.get('teamScore') is not None:
                same=prev['team']==e['team']
                e['teamScore']=prev['teamScore'] if same else prev['oppScore']; e['oppScore']=prev['oppScore'] if same else prev['teamScore']
            drives.insert(pos,e)
    for a_,b_ in zip(drives, drives[1:]):
        def sec(t): m,s_=t.split(':'); return int(m)*60+int(s_)
        if b_['q1']==a_['q2'] and b_['q2']>b_['q1'] and sec(b_['t1'])>sec(a_['t2'])+120 and b_['q1']<4:
            bump=b_['q1']+1
            if b_['q2']==b_['q1']: b_['q2']=bump
            b_['q1']=bump
            for p in b_['playList']:
                if p['q']<bump: p['q']=bump
    for d in drives:
        def sec(t): m,s_=t.split(':'); return int(m)*60+int(s_)
        if d['q1']==d['q2'] and d['q1']>1 and sec(d['t1'])<sec(d['t2']):   # first snap carries the next quarter's label
            d['q1']-=1
            if d['playList'] and d['playList'][0]['q']>d['q1']: d['playList'][0]['q']=d['q1']
    def _sec(t): m,s_=t.split(':'); return int(m)*60+int(s_)
    for i_,d_ in enumerate(drives[:-1]):
        nx=drives[i_+1]
        if d_['plays']==0 and d_['result'] in ('Fumble','Muffed Kickoff','Muffed Punt','Fumble (Defensive TD)') and nx['q1']==d_['q1'] and _sec(nx['t1'])>_sec(d_['t1']):
            d_['t1']=d_['t2']=nx['t1']
    for a_,b_ in zip(drives, drives[1:]):
        if a_['result']=='End of Game' and b_['q1']>=5: a_['result']='End of Regulation'
    prev=None
    for i,d in enumerate(drives):
        d['n']=i+1
        if prev is None or (d['q1']==3 and prev['q2']<=2): d['how']='KO'
        else: d['how']=HOW.get(prev['result'],'KO')
        prev=d
    def _anoms(ds):
        run={t:0 for t in teams}; n=0
        for d in ds:
            if d.get('teamScore') is None: continue
            t=d['team']; o=d['opponent']; gn=d['teamScore']-run.get(t,0); ls=d['oppScore']-run.get(o,0)
            if gn<0 or ls<0: n+=1
            if d['result'] in ('Punt','Turnover on Downs','Missed FG','Interception','Fumble','End of Half','End of Game','Blocked FG') and (gn or ls): n+=1
            if d['result']=='Touchdown' and gn<6: n+=1
            if d['result']=='Field Goal' and gn!=3: n+=1
            run[t]=d['teamScore']; run[o]=d['oppScore']
        return n,run
    if not _need_rescore and _anoms(drives)[0]:
        import copy
        from rescore import rescore
        alt=copy.deepcopy([{k:v for k,v in d.items() if k!='_rows'} for d in drives])
        with __import__('contextlib').redirect_stdout(__import__('io').StringIO()): rescore(alt, {t:final.get(t,0) for t in teams})
        na,ra=_anoms(alt)
        if na==0 and all(ra.get(t,0)==final.get(t,0) for t in teams):
            for d,a in zip(drives,alt): d['teamScore'],d['oppScore']=a['teamScore'],a['oppScore']
    if _need_rescore:
        from rescore import rescore
        rescore(drives, {t:final.get(t,0) for t in teams}, tim.assign(clock=-tim._ord_clock) if '_ord_clock' in tim else tim)
    # points a possession produced = the change in the team's own score on the (final-reconciled) chart
    run={t:0 for t in teams}
    for d in drives:
        if d.get('teamScore') is None: continue
        t=d['team']; o=d['opponent']
        if d['result'] in ('Touchdown','Field Goal'): d['_pts']=max(0,int(d['teamScore'])-run.get(t,0))
        run[t]=int(d['teamScore']); run[o]=int(d['oppScore'])
    return drives

def series_counts(rows):
    rows=rows[rows.is_rp]
    n=c=0
    for _,dr in rows.groupby('DriveId',sort=False):
        started=False; scored=False
        for down,sc in zip(dr.Down, dr.Scoring.fillna(False).astype(bool)):
            if down==1:
                if started: c+=1
                n+=1; started=True; scored=False
            if sc: scored=True
        if started and scored: c+=1
    return n,c

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
    power=orush[(orush.Distance<=2)&orush.Down.isin([3,4])]
    opp_runs=orush[gy>=4]
    ly=gy.apply(line_yards)
    hy=opp_runs.YardsGained.apply(lambda y: 0.5*(min(y,10)-4)+max(y-10,0))
    rush={'scrimPlays':float(n),'rushAtt':float(ra),'rushShare':sdiv(100*ra,n),'powerAtt':float(len(power)),'powerRate':r1(sdiv(100*power.succ.sum(),len(power))),
          'stuffedRuns':float((gy<=0).sum()),'stuffRate':r1(sdiv(100*(gy<=0).sum(),ra)),'stoppedRuns':float((gy<=2).sum()),'stoppedRate':r1(sdiv(100*(gy<=2).sum(),ra)),
          'opportunityRuns':float(len(opp_runs)),'opportunityRate':r1(sdiv(100*len(opp_runs),ra)),'lineYardsTotal':r1(ly.sum(),0),'lineYardsPerCarry':r1(sdiv(ly.sum(),ra),2),
          'highlightYardsTotal':r1(hy.sum(),0),'highlightYardsPerOpp':r1(sdiv(hy.sum(),len(opp_runs)),2)}
    ne=orp[~orp.expl]
    expl={'playsTotal':float(len(o)),'scrimPlays':float(n),'explosivePlays':float(o.expl.sum()),'explPass':float(o.expl_pass.sum()),'explRush':float(o.expl_rush.sum()),
          'nonExplEpaPlay':r1(sdiv(ne.Ppa.sum(),len(ne)),2),'nonExplPassEpaPlay':r1(sdiv(ne[ne.is_pass].Ppa.sum(),ne.is_pass.sum()),2),'nonExplRushEpaPlay':r1(sdiv(ne[ne.is_rush].Ppa.sum(),ne.is_rush.sum()),2)}
    e=orp[orp.early]; l=orp[orp.late]
    m8=orp[((orp.Period==2)&(orp.clock<=240))|((orp.Period==3)&(orp.clock>=660))]
    # Situational panel is labeled "Successful Plays (EPA>0)" -- EPA-based, as in the Week 1-5 box scores
    def sr(x): return r1(sdiv(100*(x.Ppa>0).sum(),len(x)))
    sit={'successPlays':float((orp.Ppa>0).sum()),'successPlaysRate':sr(orp),'successPassRate':sr(orp[orp.is_pass]),'successRushRate':sr(orp[orp.is_rush]),
         'stdDownPlays':float((~orp.passdown).sum()),'passDownPlays':float(orp.passdown.sum()),
         'earlyDownFirstDowns':float(((e.YardsGained>=e.Distance)|e.Scoring.fillna(False).astype(bool)).sum()),
         'earlyEpa':r1(e.Ppa.sum()),'earlyEpaPlay':r1(sdiv(e.Ppa.sum(),len(e)),3),'earlyPass':float(e.is_pass.sum()),'earlyRush':float(e.is_rush.sum()),
         'earlyPassSuccessRate':sr(e[e.is_pass]),'earlyRushSuccessRate':sr(e[e.is_rush]),
         'lateEpa':r1(l.Ppa.sum()),'lateEpaPlay':r1(sdiv(l.Ppa.sum(),len(l)),2),'latePass':float(l.is_pass.sum()),'lateRush':float(l.is_rush.sum()),
         'latePassSuccessRate':sr(l[l.is_pass]),'lateRushSuccessRate':sr(l[l.is_rush]),
         'avgDist3rd':r1(orp[orp.Down==3].Distance.mean()) if (orp.Down==3).any() else None,
         'mid8Epa':r1(m8.Ppa.sum()),'mid8EpaPlay':r1(sdiv(m8.Ppa.sum(),len(m8)),2),'mid8Pass':float(m8.is_pass.sum()),'mid8Rush':float(m8.is_rush.sum()),
         'mid8PassSuccessRate':sr(m8[m8.is_pass]),'mid8RushSuccessRate':sr(m8[m8.is_rush])}
    tdr=[x for x in drives if x['team']==team and x['_scrim']>0]; odr=[x for x in drives if x['team']==opp and x['_scrim']>0]
    dsum=lambda ds,k: sum(x[k] for x in ds)
    drv={'total':len(tdr),'avgStartFP':r1(sdiv(sum(x['spot1'] for x in tdr),len(tdr))),'playsPerDrive':sdiv(dsum(tdr,'_scrim'),len(tdr)),
         'yardsPerDrive':sdiv(dsum(tdr,'_yds'),len(tdr)),'availYardsPct':r1(sdiv(100*dsum(tdr,'_yds'),dsum(tdr,'_start_ytg'))),'epaPerDrive':r1(sdiv(epa,len(tdr)),2)}
    # stop = opponent possession that ended with no points scored by either side (matches the Week 1-5 box scores)
    POINTS={'Touchdown','Field Goal','Interception (Pick-6)','Fumble (Defensive TD)','Punt (Return TD)','Blocked Punt (TD)','Blocked FG (TD)','Kickoff (Return TD)','Safety'}
    stops=[x for x in odr if x['result'] not in POINTS]
    dtxt=drp.PlayText.fillna('')
    tfl=int((drush.YardsGained<=0).sum()); sacks=int(dpass.is_sack.sum()); pbu=int(dtxt.str.contains('broken up',case=False).sum())
    ints=int(d['int'].sum()); ff=int(d.PlayText.fillna('').str.contains('forced by',case=False).sum())
    hp=sacks+pbu+ints; hr=tfl
    dfn={'scrimPlays':float(len(ds_)),'stopRate':r1(sdiv(100*len(stops),len(odr))),'havocPlays':float(hp+hr+ff),'havocRate':r1(sdiv(100*(hp+hr+ff),len(ds_))),
         'havocPass':float(hp),'havocRush':float(hr),'tflRush':float(tfl),'sacks':float(sacks),'pbu':float(pbu),'ints':float(ints),'ff':float(ff),
         'epaPerDriveAllowed':r1(sdiv(float(ds_.Ppa.sum()),len(odr)),2)}
    ot=o.PlayText.fillna('').str.lower()
    fum_ev=o[(o.is_rp|o.is_fumrow|(o.PlayType=='Uncategorized')) & ot.str.contains('fumble') & ~ot.str.contains('no play|overturned')]
    fl=int(o.fum_lost.sum()); fo=max(int(len(fum_ev))-fl,0); gi=int(o['int'].sum())
    stg=int(g[(g.Defense==team)&g.st_lost].shape[0]) if 'st_lost' in g else 0      # muffed punts / kick-return fumbles lost
    stt=int(g[(g.Offense==team)&g.st_lost].shape[0]) if 'st_lost' in g else 0
    give=fl+gi+stg; take=int(d.fum_lost.sum()+d['int'].sum())+stt
    tov={'giveaways':float(give),'takeaways':float(take),'fumbleEvents':float(fl+fo),'fumblesLost':float(fl),'fumblesOwnRecov':float(fo),'ints':float(gi),'margin':float(take-give)}
    t3=orp[orp.Down==3]; t4=orp[orp.Down==4]
    sn,sc=series_counts(o); snd,scd=series_counts(d)
    conv={'thirdConv':float(t3.succ.sum()),'thirdAtt':float(len(t3)),'thirdRate':r1(sdiv(100*t3.succ.sum(),len(t3))),'fourthConv':float(t4.succ.sum()),'fourthAtt':float(len(t4)),
          'fourthRate':r1(sdiv(100*t4.succ.sum(),len(t4))),'seriesConv':float(sc),'series':float(sn),'seriesRate':r1(sdiv(100*sc,sn)),
          'seriesConvAllowed':float(scd),'seriesAllowed':float(snd),'seriesRateAllowed':r1(sdiv(100*scd,snd))}
    # Scoring opportunity ("trip") = the offense ran a scrimmage play at or inside the opponent 30
    # (field goal tries and kneel-downs don't count); points are what the trip actually produced.
    def opps(ds):
        trips=[x for x in ds if x['_trip']]
        pts=sum(x['_pts'] for x in trips)
        tds=sum(x['result']=='Touchdown' for x in trips); fgs=sum(x['result']=='Field Goal' for x in trips)
        return trips,pts,tds,fgs
    tr,pts,tds,fgs=opps(tdr); tra,ptsa,tdsa,fgsa=opps(odr)
    oppd={'trips':len(tr),'points':pts,'ppo':r1(sdiv(pts,len(tr)),2),'tds':tds,'fgs':fgs,'busts':sum(1 for x in tr if x['_pts']==0),
          'tripsAllowed':len(tra),'pointsAllowed':ptsa,'ppoAllowed':r1(sdiv(ptsa,len(tra)),2),'tdsAllowed':tdsa,'fgsAllowed':fgsa,
          'stopsInside30':sum(1 for x in tra if x['_pts']==0)}
    rz=[x for x in tdr if x['_min_snap']<=20]
    ov_vals={'epaPlay':prod['epaPlay'],'successRate':sdiv(100*orp.succ.sum(),n),'ypp':prod['ypp'],'passEpaPlay':prod['passEpaPlay'],'rushEpaPlay':prod['rushEpaPlay'],
             'passYpp':prod['passYpp'],'explosiveRate':sdiv(100*o.expl.sum(),n),'thirdRate':sdiv(100*t3.succ.sum(),len(t3)),'seriesRate':sdiv(100*sc,sn),
             'seriesRateAllowed':sdiv(100*scd,snd),'rzRate':sdiv(100*sum(x['result']=='Touchdown' for x in rz),len(rz)),
             'stuffRate_def':sdiv(100*(drush.YardsGained<=0).sum(),len(drush)),'havocRate_def':dfn['havocRate'],
             'epaPerDrive':sdiv(epa,len(tdr)),'epaPerDriveAllowed':sdiv(float(ds_.Ppa.sum()),len(odr))}
    ov={k:{'value':r1(v,3),'pct':None} for k,v in ov_vals.items()}
    return {'overall':ov,'production':prod,'rushing':rush,'explosiveness':expl,'situational':sit,'drives':drv,'defensive':dfn,'turnovers':tov,'conversions':conv,'opportunities':oppd}

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
