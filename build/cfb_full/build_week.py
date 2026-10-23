"""Add one week of CFB games to the dashboard.
usage: build_week.py WEEK GAMEIDS_FILE SRC_DIR OUT_DIR
 - season stats come from final_teams.json (full_pipeline -> winloss_and_radar -> finalize_radar on combined_raw_fixed.pkl)
 - new games: box scores, quarter splits and drive charts from boxscore.game_boxes (prepped_to.pkl)
 - finals for every new game come from official_finals.json (verified), never from the feed's score fields
"""
import sys, os, json, pickle, shutil, contextlib, io, numpy as np, pandas as pd
sys.path.insert(0,'.')
from boxscore import game_boxes
from multiprocessing import Pool
WEEK=int(sys.argv[1]); GIDS=[int(x) for x in open(sys.argv[2]).read().split()]; SRC=sys.argv[3]; OUT=sys.argv[4]
OF=json.load(open('official_finals.json'))
FBS=set(json.load(open('../nfl_rebuild/cfb_team_list.json')))
df=pd.read_pickle('prepped_to.pkl'); raw=pd.read_pickle('combined_raw_fixed.pkl')

def work(gid):
    g=df[df.GameId==gid]; h,a=g.Home.iloc[0],g.Away.iloc[0]
    with contextlib.redirect_stdout(io.StringIO()):
        full,per,chart=game_boxes(g,h,a)
    return gid,(full,per,chart)

def jl(x): return json.loads(json.dumps(x,default=float))
if __name__=='__main__':
    for gid in GIDS: assert str(gid) in OF, f'no verified final for {gid}'
    with Pool(4) as p: NEW=dict(p.map(work,GIDS))
    c=open(SRC+'/index.html').read()
    def get(tag):
        o=f'<script id="{tag}" type="application/json">'; s=c.index(o)+len(o); e=c.index('</script>',s); return json.loads(c[s:e])
    def put(c,tag,obj):
        o=f'<script id="{tag}" type="application/json">'; s=c.index(o)+len(o); e=c.index('</script>',s)
        t=json.dumps(obj,separators=(',',':'),default=float,ensure_ascii=False).replace('</','<\\/'); return c[:s]+t+c[e:]
    data=get('dashboard-data'); pidx=get('period-index-data'); didx=get('drivechart-index-data')
    if os.path.exists(OUT): shutil.rmtree(OUT)
    shutil.copytree(SRC,OUT)
    # ---------- percentile pools: every regenerated game so far + the new week ----------
    P=pickle.load(open('all_boxes3.pkl','rb'))['res']
    added_prev=pickle.load(open('boxes_added.pkl','rb')) if os.path.exists('boxes_added.pkl') else {}
    P.update(added_prev); P.update(NEW)
    SPL=['full','q1','q2','q3','q4','h1','h2','thru3']; pools={s:{} for s in SPL}
    for gid,(full,per,chart) in P.items():
        if isinstance(full,tuple) or not isinstance(full,dict): continue
        for s in SPL:
            for t,b in (full if s=='full' else per[s]).items():
                for k,v in b['overall'].items():
                    if v['value'] is not None: pools[s].setdefault(k,[]).append(v['value'])
    pools={s:{k:np.sort(np.array(v)) for k,v in d.items()} for s,d in pools.items()}
    def fill(b,s):
        for k,v in b['overall'].items():
            v.pop('_raw',None)
            if v['value'] is not None: arr=pools[s][k]; v['pct']=round(100*np.searchsorted(arr,v['value'],side='right')/len(arr),1)
        return b
    # ---------- new box scores, splits, drive charts ----------
    next_p=max(int(v.split('_')[1].split('.')[0]) for v in pidx.values())+1
    new_keys=[]
    for i,gid in enumerate(sorted(GIDS)):
        gk=f'{WEEK}_{gid}'; assert gk not in data['boxscores']
        full,per,chart=NEW[gid]; g=df[df.GameId==gid]; h,a=g.Home.iloc[0],g.Away.iloc[0]
        fin=OF[str(gid)]
        last=[x for x in chart if x.get('teamScore') is not None][-1]
        cf={last['team']:last['teamScore'],last['opponent']:last['oppScore']}
        assert cf=={h:fin[h],a:fin[a]}, f'drive chart final {cf} != official {fin} ({gid})'
        rec={}
        for t in full:
            o=a if t==h else h
            meta={'opp':o,'week':WEEK,'home':bool(t==h),'result':'W' if fin[t]>fin[o] else ('L' if fin[t]<fin[o] else 'T'),'ts':int(fin[t]),'os':int(fin[o])}
            rec[t]={'meta':meta,**fill(jl(full[t]),'full')}
        data['boxscores'][gk]=rec
        path=f'shard_{next_p+i//4:03d}.json'; pidx[gk]='periods/'+path; didx[gk]='drivecharts/'+path; new_keys.append(gk)
        psh=json.load(open(OUT+'/periods/'+path)) if os.path.exists(OUT+'/periods/'+path) else {}
        psh[gk]={s:{t:fill(jl(per[s][t]),s) for t in per[s]} for s in per}
        json.dump(psh,open(OUT+'/periods/'+path,'w'),separators=(',',':'),default=float)
        for x in chart:
            if x['result'] in ('Muffed Kickoff','Muffed Punt') or (x['plays']==0 and x['result']=='Fumble'): x['spot1']=None; x['spot2']=None
        dsh=json.load(open(OUT+'/drivecharts/'+path)) if os.path.exists(OUT+'/drivecharts/'+path) else {}
        dsh[gk]=jl(chart); json.dump(dsh,open(OUT+'/drivecharts/'+path,'w'),separators=(',',':'),default=float)
    # ---------- season table ----------
    recs=json.load(open('final_teams.json'))
    RUSH={'Rush','Rushing Touchdown','Two Point Rush'}; PASS={'Pass Reception','Pass Incompletion','Passing Touchdown','Sack','Interception','Pass Interception Return','Interception Return Touchdown','Two Point Pass','Pass Completion'}
    kneel=raw.PlayText.str.contains('kneel',case=False,na=False)
    sc=raw[(raw.PlayType.isin(RUSH)&~kneel)|raw.PlayType.isin(PASS)]
    for t,r in recs.items():
        o=sc[sc.Offense==t]; d=sc[sc.Defense==t]; on=o[o.YardsToGoal>5]; dn=d[d.YardsToGoal>5]
        r['yppAllPlays']=r['ypp']; r['yppAllowedAllPlays']=r['yppAllowed']; r['yppExcludedPlays']=int(len(o)-len(on))
        r['ypp']=round(on.YardsGained.sum()/len(on),2) if len(on) else 0
        r['yppAllowed']=round(dn.YardsGained.sum()/len(dn),2) if len(dn) else 0
        gv=int(df[df.Offense==t].giveaway.sum())+int(df[(df.Defense==t)&df.st_lost].shape[0]); tk=int(df[df.Defense==t].giveaway.sum())+int(df[(df.Offense==t)&df.st_lost].shape[0])
        r['giveaways']=gv; r['takeaways']=tk; r['turnoverMargin']=tk-gv
    ts_=list(recs)
    for i,t in enumerate(sorted(ts_,key=lambda t:-recs[t]['ypp'])): recs[t]['ranks']['ypp']=i+1
    for i,t in enumerate(sorted(ts_,key=lambda t:recs[t]['yppAllowed'])): recs[t]['ranks']['yppAllowed']=i+1
    for t,old in data['teams'].items():
        new=recs[t]; data['teams'][t]={k:(old[k] if k in ('conf','confLabel') or k not in new else new[k]) for k in old}
        for side in ('offRaw','defRaw'):
            if isinstance(data['teams'][t]['radar'][side].get('epaPlay'),float): data['teams'][t]['radar'][side]['epaPlay']=round(data['teams'][t]['radar'][side]['epaPlay'],3)
    # ---------- game logs for the new week ----------
    COMP={'Pass Reception','Passing Touchdown'}
    added=0
    for gk in new_keys:
        gid=int(gk.split('_')[1]); g=raw[raw.GameId==gid].copy(); gp=df[df.GameId==gid]
        k=g.PlayText.str.contains('kneel',case=False,na=False)
        g['is_rush']=g.PlayType.isin(RUSH)&~k; g['is_pass']=g.PlayType.isin(PASS); g['is_scrim']=g.is_rush|g.is_pass
        g['is_expl']=(g.is_rush&(g.YardsGained>=10))|(g.PlayType.isin(COMP)&(g.YardsGained>=15))
        def succ(r):
            if r.Scoring==True or r.Scoring==1: return True
            d_,dist,y=r.Down,r.Distance,r.YardsGained
            if pd.isna(dist) or pd.isna(y): return False
            if dist<=0: return y>=dist
            return y>=(0.5*dist if d_==1 else 0.7*dist if d_==2 else dist)
        g['succ']=[succ(r) if (s and r.Down in (1,2,3,4)) else False for r,s in zip(g.itertuples(),g.is_scrim)]
        def series(x):
            n=cv=0
            for _,grp in x.groupby('DriveId'):
                started=scored=False
                for dn_,s_ in zip(grp.sort_values('Id').Down,grp.sort_values('Id').Scoring.fillna(False).astype(bool)):
                    if dn_==1:
                        if started: cv+=1
                        n+=1; started=True; scored=False
                    if s_: scored=True
                if started and scored: cv+=1
            return n,cv
        for t,b in data['boxscores'][gk].items():
            if t not in data['games']: continue
            m=b['meta']; o=m['opp']
            off=g[g.Offense==t]; de=g[g.Defense==t]; os_=off[off.is_scrim]; ds_=de[de.is_scrim]
            orr=off[off.is_rush]; opa=off[off.is_pass]; drr=de[de.is_rush]; dpa=de[de.is_pass]
            t3=os_[os_.Down==3]; t4=os_[os_.Down==4]; sN,sC=series(os_); dN,dC=series(ds_)
            mean=lambda s: round(float(s.mean()),3) if len(s) else 0
            to=(int(gp[gp.Offense==t].giveaway.sum())+int(gp[(gp.Defense==t)&gp.st_lost].shape[0]))-(int(gp[gp.Defense==t].giveaway.sum())+int(gp[(gp.Offense==t)&gp.st_lost].shape[0]))
            e={'week':WEEK,'opp':o,'home':m['home'],'result':m['result'],'ts':m['ts'],'os':m['os'],
               'plays':len(os_),'ypp':round(os_.YardsGained.sum()/len(os_),2) if len(os_) else 0,'exp':int(off.is_expl.sum()),'expAllowed':int(de.is_expl.sum()),
               'epaRush':mean(orr.Ppa),'epaPass':mean(opa.Ppa),'epaRushAllowed':mean(drr.Ppa),'epaPassAllowed':mean(dpa.Ppa),
               'rushYds':int(orr.YardsGained.sum()),'passYds':int(opa.YardsGained.sum()),
               'thirdPct':round(100*t3.succ.sum()/len(t3),1) if len(t3) else 0,'to':to,
               'thirdConv':int(t3.succ.sum()),'thirdAtt':len(t3),'fourthConv':int(t4.succ.sum()),'fourthAtt':len(t4),
               'seriesRate':round(100*sC/sN,1) if sN else 0,'seriesRateAllowed':round(100*dC/dN,1) if dN else 0}
            L=data['games'][t]; assert not any(x['week']==WEEK and x['opp']==o for x in L); L.append(e); added+=1
    data['meta']['weeks']=sorted(set(data['meta']['weeks'])|{WEEK})
    data['meta']['scope']=f"Week 1-{max(data['meta']['weeks'])} combined, FBS-involved games only"
    c2=put(put(put(c,'dashboard-data',data),'period-index-data',pidx),'drivechart-index-data',didx)
    open(OUT+'/index.html','w').write(c2)
    json.dump(new_keys,open(OUT+f'/added_week{WEEK}.json','w'))
    added_prev.update(NEW); pickle.dump(added_prev,open('boxes_added_pending.pkl','wb'))   # promoted to boxes_added.pkl once published
    print('new games',len(new_keys),'game-log rows',added,'shards',sorted(set(pidx[k] for k in new_keys)))
