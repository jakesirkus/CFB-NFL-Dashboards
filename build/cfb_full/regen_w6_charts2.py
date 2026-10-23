import sys, json, glob, os, pandas as pd, collections; sys.path.insert(0,'.')
from boxscore import build_drives
from multiprocessing import Pool
df=pd.read_pickle('prepped_to.pkl')
shards={}
for f in sorted(glob.glob('out4/drivecharts/*.json')):
    d=json.load(open(f)); w6=[k for k in d if k.startswith('6_')]
    if w6: shards[f]=d
def work(gk):
    g=df[df.GameId==int(gk.split('_')[1])]
    return gk,[{k:v for k,v in x.items() if not k.startswith('_')} for x in build_drives(g)]
if __name__=='__main__':
    gks=[k for d in shards.values() for k in d if k.startswith('6_')]
    with Pool(4) as p: res=dict(p.map(work,gks))
    diff=collections.Counter(); ex=collections.defaultdict(list)
    for f,d in shards.items():
        for gk in list(d):
            if not gk.startswith('6_'): continue
            old,new=d[gk],res[gk]
            if len(old)!=len(new): diff['len']+=1; ex['len'].append(gk)
            else:
                for a,b in zip(old,new):
                    for k in set(a)|set(b):
                        if a.get(k)!=b.get(k): diff[k]+=1; ex[k].append(gk)
            d[gk]=new
        json.dump(d,open(f,'w'),separators=(',',':'))
    print(len(gks),dict(diff)); print({k:sorted(set(v))[:12] for k,v in ex.items()})
