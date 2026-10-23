import pandas as pd, numpy as np
from nfl_season import NAME, _f

HOW={'KICKOFF':'KO','PUNT':'PUNT','INTERCEPTION':'INT','FUMBLE':'FUMB','MUFFED_PUNT':'MUFF','MUFFED_KICKOFF':'MUFF'}
COLOR={'Touchdown':'blue','Field Goal':'blue','Interception (Pick-6)':'blue','Fumble (Defensive TD)':'blue',
       'Punt':'gray','End of Game':'gray','End of Half':'gray'}

def spot_from(s, team):
    """'ARI 30' -> yards from own goal for team"""
    if not isinstance(s,str) or not s.strip(): return None
    s=s.strip()
    if s=='50' or s.endswith(' 50'): return 50.0
    side,yl=s.rsplit(' ',1); yl=float(yl)
    return yl if side==team else 100-yl

def nz(x):
    return None if x is None or (isinstance(x,float) and np.isnan(x)) else x

def play_entry(r):
    pen=bool(r.penalty==1)
    e={'q':int(r.qtr),'text':r.desc,'scoring':bool(r.sp==1),'penalty':pen,
       'down':None if pd.isna(r.down) else int(r.down),'distance':0 if pd.isna(r.ydstogo) else int(r.ydstogo),
       'goalToGo':bool(r.goal_to_go==1),'yardline100':None if pd.isna(r.yardline_100) else int(r.yardline_100)}
    if pen:
        e['penaltyTeam']=nz(r.penalty_team); e['penaltyType']=nz(r.penalty_type)
        e['penaltyYards']=None if pd.isna(r.penalty_yards) else int(r.penalty_yards)
    return e

END={'BLOCKED_FG':'Blocked FG','BLOCKED_PUNT':'Blocked Punt','DOWNS':'Turnover on Downs','END_GAME':'End of Game','END_HALF':'End of Half',
     'FIELD_GOAL':'Field Goal','FUMBLE':'Fumble','INTERCEPTION':'Interception','MISSED_FG':'Missed FG','PUNT':'Punt','SAFETY':'Safety','TOUCHDOWN':'Touchdown',
     'MUFFED_PUNT':'Punt','FUMBLE_SAFETY':'Safety','BLOCKED_FG_TD':'Blocked FG','BLOCKED_PUNT_TD':'Blocked Punt'}
def drive_result(pr, team, trans, fdr):
    t=str(trans).split(',')[0]
    res=END.get(t)
    if res is None:
        res={'Touchdown':'Touchdown','Field goal':'Field Goal','Punt':'Punt','Turnover on downs':'Turnover on Downs','Missed field goal':'Missed FG',
             'Safety':'Safety','End of half':'End of Half','Turnover':'Fumble','Opp touchdown':'Fumble'}.get(fdr, str(fdr))
    opp_td=((pr.touchdown.fillna(0)==1)&pr.td_team.notna()&(pr.td_team!=team)&((pr.interception.fillna(0)==1)|(pr.fumble_lost.fillna(0)==1))).any()
    if res=='Interception' and opp_td: res='Interception (Pick-6)'
    if res=='Fumble' and opp_td: res='Fumble (Defensive TD)'
    return res

def build_drives(g):
    g=g.sort_values('play_id')
    home=g.home_team.iloc[0]; away=g.away_team.iloc[0]
    out=[]; n=0; ph,pa=0,0
    ids=[x for x in g.fixed_drive.dropna().unique()]
    for k,fd in enumerate(ids):
        rows=g[g.fixed_drive==fd]
        pr=rows[rows.play_type.notna()]
        if len(pr)==0: continue
        team=rows.posteam.dropna().iloc[0] if rows.posteam.notna().any() else None
        if team is None: continue
        opp=away if team==home else home
        f0=rows[rows.drive_quarter_start.notna()].iloc[0] if rows.drive_quarter_start.notna().any() else rows.iloc[0]
        fdr=f0.fixed_drive_result
        scrim=pr[pr.is_scrim]          # every scrimmage snap in the drive group, as the original did
        last_q=int(f0.drive_quarter_end) if not pd.isna(f0.drive_quarter_end) else int(rows.qtr.max())
        tr=pr[pr.drive_end_transition.notna()]
        res=drive_result(pr, team, tr.drive_end_transition.iloc[0] if len(tr) else None, fdr)
        how=HOW.get(str(f0.drive_start_transition).split(',')[0], 'DOWNS')
        snaps=pr[(pr.posteam==team)&pr.down.notna()&~pr.play_type.isin(['field_goal','punt'])&~_f(pr,'qb_kneel')]
        last=g[g.index.isin(rows.index)].iloc[-1]
        nto=pr[~pr.desc.str.startswith('Timeout #')]
        lp=nto.iloc[-1] if len(nto) else pr.iloc[-1]
        sv=pr[pr.posteam_score_post.notna()&pr.posteam.notna()]
        if len(sv):
            sc=sv.iloc[-1]
            hs,as_=(sc.posteam_score_post,sc.defteam_score_post) if sc.posteam==home else (sc.defteam_score_post,sc.posteam_score_post)
        else:
            sc=pr[pr.total_home_score.notna()].iloc[-1]; hs,as_=sc.total_home_score,sc.total_away_score
        hs,as_=int(hs),int(as_)
        ts,os_=(hs,as_) if team==home else (as_,hs)
        f_sc=pr[pr.total_home_score.notna()].iloc[0]
        pre=(f_sc.total_home_score-(0),)
        start_ytg=None if pd.isna(f0.drive_start_yard_line) else spot_from(f0.drive_start_yard_line, team)
        d={'n':float(fd),'team':NAME[team],'opponent':NAME[opp],'how':how,
           'q1':int(f0.drive_quarter_start),'t1':f0.drive_game_clock_start,'spot1':spot_from(f0.drive_start_yard_line,team),
           'q2':last_q,'t2':f0.drive_game_clock_end,'spot2':spot_from(f0.drive_end_yard_line,team),
           'plays':int(len(scrim)),'yards':int(scrim.yds.sum()),'top':f0.drive_time_of_possession,
           'result':res,'color':COLOR.get(res,'red'),'clickable':True,
           'opp30':bool(((pr.is_scrim|(pr.two_point_attempt.fillna(0)==1))&(pr.yardline_100<=30)).any()),
           'playText':lp.desc,'playList':[play_entry(r) for r in pr.itertuples()],
           'teamScore':None if pd.isna(ts) else int(ts),'oppScore':None if pd.isna(os_) else int(os_),
           'scored':bool((pr.sp.fillna(0)==1).any())}
        rzm=(pr.is_scrim|(pr.two_point_attempt.fillna(0)==1))&(pr.yardline_100<=20)
        d['_rz']=bool(rzm.any()); d['_rztd']=bool((pr.is_scrim&(pr.yardline_100<=20)&(pr.touchdown.fillna(0)==1)).any())
        d['_epa']=float(scrim.epa.sum()); d['_scrim']=len(scrim); d['_fdr']=fdr; d['_tm']=team
        d['_pts']=(hs-ph) if team==home else (as_-pa); ph,pa=hs,as_
        d['_min_ytg']=float(snaps.yardline_100.min()) if len(snaps) else 999
        d['_avail']=100-(d['spot1'] or 0)
        n+=1; out.append(d)
    # muffed punt / kickoff recovered by the kicking team: show a one-entry possession for the receiving team
    fin=[]
    for i,d in enumerate(out):
        fin.append(d)
        nx=out[i+1] if i+1<len(out) else None
        if nx and nx['how']=='MUFF' and nx['team']==d['team']:
            lp=d['playList'][-1]
            kind='Muffed Kickoff' if 'kicks' in lp['text'] else 'Muffed Punt'
            import re
            m=re.match(r'\((\d*):(\d\d)\)',lp['text']); clk=f"{int(m.group(1) or 0):02d}:{m.group(2)}" if m else d['t2']
            fin.append({'n':d['n']+0.5,'team':d['opponent'],'opponent':d['team'],'how':'KO' if kind=='Muffed Kickoff' else 'PUNT',
                'q1':lp['q'],'t1':clk,'spot1':None,'q2':lp['q'],'t2':clk,'spot2':None,'plays':0,'yards':0,'top':None,
                'result':kind,'color':'red','clickable':True,'opp30':False,'playText':lp['text'],'playList':[lp],
                'teamScore':None,'oppScore':None,'scored':False,'_scrim':0,'_fdr':'Turnover','_tm':None,'_min_ytg':999,'_avail':0})
    return fin
