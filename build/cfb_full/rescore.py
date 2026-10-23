"""Running score for a drive chart, rebuilt from each possession's RESULT and reconciled to the final.
Used when the play-by-play scoring tally doesn't add up to the final (duplicated / missing scoring rows,
lagging score fields)."""
import itertools, re
from boxscore import pat_points
OWN={'Touchdown':'td','Field Goal':'fg'}
OPP={'Interception (Pick-6)':'td','Fumble (Defensive TD)':'td','Punt (Return TD)':'td','Blocked Punt (TD)':'td',
     'Blocked FG (TD)':'td','Kickoff (Return TD)':'td','Safety':'saf','Two-Point (Turnover)':'d2'}
PATKEY=re.compile(r'kick|pat|extra point|two[- ]point|2pt|conversion|attempt (failed|good|successful)',re.I)
def _pat(d):
    txt=' '.join(p.get('text','') for p in (d.get('playList') or [])[-3:])+' '+(d.get('playText') or '')
    known=bool(PATKEY.search(txt))
    return (pat_points(txt) if known else 1), known
def rescore(drives, final, tim=None):
    teams=list(final)
    ev=[]   # [drive index, team, kind, pts, pat_known]
    for i,d in enumerate(drives):
        r=d.get('result'); t=d['team']; o=d.get('opponent') or [x for x in teams if x!=t][0]
        if t not in final: continue
        if r in OWN: who,k=t,OWN[r]
        elif r in OPP: who,k=o,OPP[r]
        else: continue
        if k=='td': p,kn=_pat(d); ev.append([i,who,'td',6+p,kn,r])
        elif k=='fg': ev.append([i,who,'fg',3,True,r])
        else: ev.append([i,who,k,2,True,r])
    drop=set(); missing={}
    for tm in teams:
        mine=[e for e in ev if e[1]==tm]
        diff=final[tm]-sum(e[3] for e in mine)
        if diff==0: continue
        tds=[e for e in mine if e[2]=='td']
        done=False
        # 1) change extra-point results (unparsed ones first), fewest changes
        order=sorted(tds,key=lambda e:e[4])
        for n in range(1,len(order)+1):
            for combo in itertools.combinations(order,n):
                for vals in itertools.product([6,7,8],repeat=n):
                    if sum(v-e[3] for v,e in zip(vals,combo))==diff:
                        for v,e in zip(vals,combo): e[3]=v
                        done=True; break
                if done: break
            if done or n>=3: break
        if done: continue
        # 2) a score credited that didn't happen (duplicate / mislabeled return TD), optionally with one PAT change
        cands=sorted(mine,key=lambda e:(e[5]=='Touchdown' or e[5]=='Field Goal', -e[0]))
        for e in cands:
            if -e[3]==diff: drop.add(id(e)); done=True; break
        if done: continue
        if diff>0: missing[tm]=diff        # a score the feed never logged as a play (e.g. return TD on a punt row)
        else: print('rescore: could not reconcile',tm,'diff',diff)
    # place each missing score at the first possession where the feed's own score field shows it
    feed=[]
    for d in drives:
        rows=d.get('_rows')
        if tim is not None and rows is not None and len(rows):
            k=max(zip(rows.Period,-rows.clock))
            rr=tim[[x<=k for x in zip(tim.Period,-tim.clock)]]
            f={}
            for r in rr.itertuples(): f[r.Offense]=int(r.OffenseScore); f[r.Defense]=int(r.DefenseScore)
            feed.append(f)
        else: feed.append(None)
    run={t:0 for t in teams}; pts_by={}
    for e in ev:
        if id(e) in drop: continue
        pts_by.setdefault(e[0],[]).append(e)
    pending=dict(missing)
    for i,d in enumerate(drives):
        t=d['team']
        if t not in final: continue
        o=d.get('opponent') or [x for x in teams if x!=t][0]
        for e in pts_by.get(i,[]): run[e[1]]+=e[3]
        for tm,amt in list(pending.items()):
            last=all(x['team'] not in final for x in drives[i+1:])
            if (feed[i] and feed[i].get(tm,0)>=run[tm]+amt) or last or i==len(drives)-1:
                run[tm]+=amt; del pending[tm]
        if d.get('teamScore') is not None or d.get('result') not in ('Muffed Punt','Muffed Kickoff'):
            d['teamScore'],d['oppScore']=run[t],run[o]
    for e in ev:
        if id(e) in drop:   # the result label claimed a score that never happened
            d=drives[e[0]]; d['result']={'Fumble (Defensive TD)':'Fumble','Interception (Pick-6)':'Interception'}.get(d['result'],d['result'])
    return run
