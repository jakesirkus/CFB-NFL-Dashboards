import sys, json, pickle, os, glob, numpy as np, pandas as pd; sys.path.insert(0,'.')
from boxscore import build_drives
from multiprocessing import Pool
A='../artifact-files/0288758d-457f-4949-98e0-a167547e40ce/'
P=pickle.load(open('all_boxes3.pkl','rb'))['res']
df=pd.read_pickle('prepped_to.pkl')
c=open('out2/index.html').read()
def get(tag):
    o=f'<script id="{tag}" type="application/json">'; s=c.index(o)+len(o); e=c.index('</script>',s); return json.loads(c[s:e])
def put(c,tag,obj):
    o=f'<script id="{tag}" type="application/json">'; s=c.index(o)+len(o); e=c.index('</script>',s)
    t=json.dumps(obj,separators=(',',':'),default=float); assert '</script' not in t; return c[:s]+t+c[e:]
data=get('dashboard-data'); pidx=get('period-index-data'); didx=get('drivechart-index-data')
_season=json.load(open('data_new.json'))          # season stats + game logs rebuilt from the corrected play table
data['teams']=_season['teams']; data['games']=_season['games']; data['meta']=_season['meta']
# Ohio 29, Jacksonville State 27 (4OT, Sept. 12) -- the original Week 2 game log/box score had a corrupt 1414-34 score
for t,o,ts,os_ in (('Ohio','Jacksonville State',29,27),('Jacksonville State','Ohio',27,29)):
    for gm in data['games'][t]:
        if gm['opp']==o and gm['week']==2: gm.update(ts=ts,os=os_,result='W' if ts>os_ else 'L')
    bk=data['boxscores'].get('2_401866418',{}).get(t)
    if bk: bk['meta'].update(ts=ts,os=os_,result='W' if ts>os_ else 'L')
assert not any(k.endswith('401856716') for k in data['boxscores'])
# ---------- percentile pools (all regenerated games, per stat window) ----------
SPL=['full','q1','q2','q3','q4','h1','h2','thru3']
pools={s:{} for s in SPL}
for gid,(full,per,chart) in P.items():
    for s in SPL:
        for t,b in (full if s=='full' else per[s]).items():
            for k,v in b['overall'].items():
                if v['value'] is not None: pools[s].setdefault(k,[]).append(v['value'])
pools={s:{k:np.sort(np.array(v)) for k,v in d.items()} for s,d in pools.items()}
def fill(b,s):
    for k,v in b['overall'].items():
        if v['value'] is not None: a=pools[s][k]; v['pct']=round(100*np.searchsorted(a,v['value'],side='right')/len(a),1)
    return b
stats=dict(w6_box=0,old_tov=0,old_tov_changed=0,old_period_tov=0,dc_relabeled=0)
# ---------- add Week 6 games that weren't on the dashboard yet (re-pulled Week 6 file) ----------
wk6=sorted(gid for gid in P if gid not in {int(k.split('_')[1]) for k in data['boxscores']})
next_p=max(int(v.split('_')[1].split('.')[0]) for v in pidx.values())+1
new_games=[]
for i,gid in enumerate(wk6):
    gk=f'6_{gid}'; g=df[df.GameId==gid]; full=P[gid][0]
    home,away=g.Home.iloc[0],g.Away.iloc[0]; sc={}
    for o_,os__,d_,ds_ in zip(g.Offense,g.OffenseScore,g.Defense,g.DefenseScore): sc[o_]=max(sc.get(o_,0),os__); sc[d_]=max(sc.get(d_,0),ds_)
    data['boxscores'][gk]={t:{'meta':{'opp':(away if t==home else home),'week':6,'home':bool(t==home),'result':'W' if sc[t]>sc[(away if t==home else home)] else 'L','ts':int(sc[t]),'os':int(sc[(away if t==home else home)])}} for t in full}
    path=f'shard_{next_p+i//4:03d}.json'; pidx[gk]='periods/'+path; didx[gk]='drivecharts/'+path; new_games.append(gk)
print('new Week 6 games added:', new_games)
# ---------- box scores ----------
for gk,v in data['boxscores'].items():
    gid=int(gk.split('_')[1]); full,per,chart=P[gid]
    for t in list(v):
        if t not in full: continue
        if gk.startswith('6_'):
            meta=v[t]['meta']; v[t]={'meta':meta,**fill(json.loads(json.dumps(full[t],default=float)),'full')}; stats['w6_box']+=1
        else:
            new=dict(full[t]['turnovers']); old=v[t]['turnovers']
            fe=max(old.get('fumbleEvents') or 0, new['fumblesLost'])     # keep the original fumble count, it already handled the text
            new['fumbleEvents']=float(fe); new['fumblesOwnRecov']=float(fe-new['fumblesLost'])
            stats['old_tov']+=1; stats['old_tov_changed']+= any(new[k]!=old.get(k) for k in ('giveaways','takeaways','fumblesLost','ints')); v[t]['turnovers']=new
# ---------- period shards ----------
os.makedirs('out3/periods',exist_ok=True); os.makedirs('out3/drivecharts',exist_ok=True)
by_shard={}
for gk,path in pidx.items(): by_shard.setdefault(path,[]).append(gk)
for path,gks in by_shard.items():
    src='out/'+path if any(g.startswith('6_') for g in gks) else A+path
    sh=json.load(open(src)) if os.path.exists(src) else {}
    for gk in gks:
        gid=int(gk.split('_')[1]); per=P[gid][1]
        if gk not in sh: sh[gk]={s:{} for s in per}
        for s in per:
            sh[gk].setdefault(s,{})
            for t in per[s]:
                if gk.startswith('6_'): sh[gk][s][t]=fill(json.loads(json.dumps(per[s][t],default=float)),s)
                elif t not in sh[gk][s]: continue
                else:
                    new=dict(per[s][t]['turnovers']); old=sh[gk][s][t].get('turnovers') or {}
                    fe=max(old.get('fumbleEvents') or 0, new['fumblesLost']); new['fumbleEvents']=float(fe); new['fumblesOwnRecov']=float(fe-new['fumblesLost'])
                    sh[gk][s][t]['turnovers']=new; stats['old_period_tov']+=1
    json.dump(sh,open('out3/'+path,'w'),separators=(',',':'),default=float)
# ---------- drive charts ----------
FUM={'Fumble':'red','Fumble (Defensive TD)':'blue'}
by_shard={}
for gk,path in didx.items(): by_shard.setdefault(path,[]).append(gk)
relabels=[]
for path,gks in by_shard.items():
    src='out2/'+path if any(g.startswith('6_') for g in gks) else A+path
    sh=json.load(open(src)) if os.path.exists(src) else {}
    for gk in gks:
        gid=int(gk.split('_')[1]); mine=P[gid][2]
        if gk.startswith('6_'):
            for x in mine:
                if x['result'] in ('Muffed Kickoff','Muffed Punt') or (x['plays']==0 and x['result']=='Fumble'): x['spot1']=None; x['spot2']=None
            sh[gk]=mine; continue
        chart=sorted(sh[gk], key=lambda x:x['n'])
        for i,d in enumerate(chart):
            m=[x for x in mine if x['team']==d['team'] and x['playText']==d['playText']] or [x for x in mine if x['team']==d['team'] and x['q1']==d['q1'] and x['t1']==d['t1']]
            if len(m)!=1: continue
            r=m[0]['result']
            if r in FUM and d['result'] in ('Incomplete','End of Half','End of Game','Fumble') and d['result']!=r:
                relabels.append((gk,d['team'],d['n'],d['result'],r)); d['result']=r; d['color']=FUM[r]; d['scored']= r=='Fumble (Defensive TD)'
                if i+1<len(chart) and chart[i+1]['team']!=d['team']: chart[i+1]['how']='FUMB' if r=='Fumble' else 'KO'
    json.dump(sh,open('out3/'+path,'w'),separators=(',',':'),default=float)
stats['dc_relabeled']=len(relabels)
# ---------- season turnovers + game-log turnover margin ----------
for t,rec in data['teams'].items():
    gv=int(df[df.Offense==t].giveaway.sum())+int(df[(df.Defense==t)&df.st_lost].shape[0]); tk=int(df[df.Defense==t].giveaway.sum())+int(df[(df.Offense==t)&df.st_lost].shape[0])
    rec['giveaways']=gv; rec['takeaways']=tk; rec['turnoverMargin']=tk-gv
key2gid={}
for gk,v in data['boxscores'].items():
    for t,b in v.items(): key2gid[(t,b['meta']['week'],b['meta']['opp'])]=int(gk.split('_')[1])
gl_changed=gl_missing=0
for t,games in data['games'].items():
    for gm in games:
        gid=key2gid.get((t,gm['week'],gm['opp']))
        if gid is None: gl_missing+=1; continue
        g=df[df.GameId==gid]
        to=(int(g[g.Offense==t].giveaway.sum())+int(g[(g.Defense==t)&g.st_lost].shape[0]))-(int(g[g.Defense==t].giveaway.sum())+int(g[(g.Offense==t)&g.st_lost].shape[0]))   # giveaways - takeaways (original convention)
        gl_changed+= gm['to']!=to; gm['to']=to
c2=put(put(put(c,'dashboard-data',data),'period-index-data',pidx),'drivechart-index-data',didx)
open('out3/index.html','w').write(c2)
json.dump(sorted(set(pidx.values())),open('out3/period_files.json','w')); json.dump(sorted(set(didx.values())),open('out3/dc_files.json','w'))
json.dump(relabels,open('out3/relabels.json','w'))
print(stats, '| game-log rows changed', gl_changed, 'missing', gl_missing, '| html bytes', len(c2))
print('sample relabels:', relabels[:6])
a=data['teams']['Alabama']; print('Alabama season giveaways/takeaways/margin:', a['giveaways'],a['takeaways'],a['turnoverMargin'])
