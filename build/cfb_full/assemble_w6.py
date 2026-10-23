import sys,json,pickle,os,numpy as np,pandas as pd; sys.path.insert(0,'.')
from boxscore import game_boxes
P=pickle.load(open('all_boxes.pkl','rb')); res=P['res']; wk6=P['wk6']
df=pd.read_pickle('prepped.pkl')
# add any week-6 games not yet generated (neither team in FBS list) -- mirror original coverage
meta=df[df.GameId.isin(wk6)].groupby('GameId').agg(home=('Home','first'),away=('Away','first'))
for gid,r in meta.iterrows():
    if gid not in res:
        res[gid]=game_boxes(df[df.GameId==gid], r.home, r.away)
assert 401856716 not in res or 401856716 not in wk6
# final scores
idx=df.groupby('GameId')['Id'].idxmax(); fin=df.loc[idx].set_index('GameId')
def score(gid,team):
    f=fin.loc[gid]; return int(f.OffenseScore if f.Offense==team else f.DefenseScore)
# percentile pools per split from all generated games (weeks 1-6)
SPL=['full','q1','q2','q3','q4','h1','h2','thru3']
pools={s:{} for s in SPL}
def boxes(r,s): return r[0] if s=='full' else r[1][s]
for gid,r in res.items():
    for s in SPL:
        for t,b in boxes(r,s).items():
            for k,v in b['overall'].items():
                if v['value'] is not None: pools[s].setdefault(k,[]).append(v['value'])
pools={s:{k:np.sort(np.array(v)) for k,v in d.items()} for s,d in pools.items()}
def fill(b,s):
    for k,v in b['overall'].items():
        if v['value'] is None: continue
        a=pools[s][k]; v['pct']=round(100*np.searchsorted(a,v['value'],side='right')/len(a),1)
live=json.load(open('data_new.json'))
pidx=json.load(open('live/period_index.json')); didx=json.load(open('live/drive_index.json'))
os.makedirs('out/periods',exist_ok=True); os.makedirs('out/drivecharts',exist_ok=True)
next_shard=max(int(v.split('_')[1].split('.')[0]) for v in pidx.values())+1
gks=[]; pshard={}; dshard={}
for gid in sorted(wk6):
    r=res[gid]; gk=f'6_{gid}'; m=meta.loc[gid]; full,per,chart=r
    entry={}
    for t,b in full.items():
        fill(b,'full'); opp=m.away if t==m.home else m.home
        ts,os_=score(gid,t),score(gid,opp)
        entry[t]={'meta':{'opp':opp,'week':6,'home':bool(t==m.home),'result':'W' if ts>os_ else 'L' if ts<os_ else 'T','ts':ts,'os':os_},**b}
    live['boxscores'][gk]=entry
    for s,tb in per.items():
        for t,b in tb.items(): fill(b,s)
    gks.append(gk); pshard[gk]=per; dshard[gk]=chart
files=[]
for i in range(0,len(gks),4):
    n=next_shard+i//4; name=f'shard_{n:03d}.json'
    chunk=gks[i:i+4]
    json.dump({g:pshard[g] for g in chunk}, open('out/periods/'+name,'w'), separators=(',',':'))
    json.dump({g:dshard[g] for g in chunk}, open('out/drivecharts/'+name,'w'), separators=(',',':'))
    for g in chunk: pidx[g]='periods/'+name; didx[g]='drivecharts/'+name
    files+=['periods/'+name,'drivecharts/'+name]
print('week6 box score games:',len(gks),'new shard files:',len(files))
src='../artifact-files/0288758d-457f-4949-98e0-a167547e40ce/index.html'
c=open(src).read()
def put(c,tag,obj):
    o=f'<script id="{tag}" type="application/json">'; s=c.index(o)+len(o); e=c.index('</script>',s)
    t=json.dumps(obj,separators=(',',':'), default=float); assert '</script' not in t
    return c[:s]+t+c[e:]
c=put(c,'dashboard-data',live)
c=put(c,'period-index-data',pidx); c=put(c,'drivechart-index-data',didx)
open('out/index.html','w').write(c)
json.dump(files,open('out/files.json','w'))
print('html bytes',len(c))
a=live['boxscores'][[g for g in gks if 'Alabama' in live['boxscores'][g]][0]]['Alabama']
print(a['meta'], a['overall']['epaPlay'], a['conversions']['seriesRate'])
