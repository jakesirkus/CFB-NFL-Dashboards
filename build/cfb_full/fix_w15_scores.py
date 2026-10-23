import sys, json, glob, re, pandas as pd, collections; sys.path.insert(0,'.')
from boxscore import build_drives
from multiprocessing import Pool
df=pd.read_pickle('prepped_to.pkl')
flag=[l.split()[0] for l in open('flagged.txt').read().splitlines()[1:]]
s=open('out4/index.html').read(); T='<script id="dashboard-data" type="application/json">'; a=s.index(T)+len(T); b=s.index('</script>',a)
D=json.loads(s[a:b])
def work(gk):
    g=df[df.GameId==int(gk.split('_')[1])]
    return gk,(build_drives(g) if len(g) else None)
if __name__=='__main__':
    with Pool(4) as p: res=dict(p.map(work,flag))
    stats=collections.Counter(); applied=[]
    for f in sorted(glob.glob('out4/drivecharts/*.json')):
        d=json.load(open(f)); ch=False
        for gk in flag:
            if gk not in d or res.get(gk) is None: continue
            old=d[gk]; new=[x for x in res[gk]]
            meta={t:x['meta']['ts'] for t,x in D['boxscores'][gk].items() if isinstance(x,dict) and 'meta' in x}
            last=new[-1]; nf={last['team']:last['teamScore'], [t for t in meta if t!=last['team']][0]:last['oppScore']}
            if nf!=meta: stats['new final != box']+=1; print('skip(final)',gk,nf,meta); continue
            # map by (team, quarter, start clock) so differences in drive splitting don't misalign
            key=lambda x:(x['team'],x['q1'],x['t1'])
            nm={key(x):x for x in new}
            hit=sum(key(x) in nm for x in old)
            if hit<len(old)*0.9: stats['structure differs']+=1; print('skip(struct)',gk,hit,len(old)); continue
            prev=None
            for x in old:
                y=nm.get(key(x))
                if y and y['teamScore'] is not None: x['teamScore'],x['oppScore']=y['teamScore'],y['oppScore']
                elif prev and x.get('teamScore') is not None:
                    same=prev['team']==x['team']; x['teamScore']=prev['teamScore'] if same else prev['oppScore']; x['oppScore']=prev['oppScore'] if same else prev['teamScore']
                if x.get('teamScore') is not None: prev=x
            stats['fixed']+=1; applied.append(gk); ch=True
        if ch: json.dump(d,open(f,'w'),separators=(',',':'))
    print(dict(stats))
