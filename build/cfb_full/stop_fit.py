import json, itertools, numpy as np, pandas as pd, sys; sys.path.insert(0,'.')
from boxscore import build_drives
from multiprocessing import Pool
df=pd.read_pickle('prepped.pkl')
live=json.load(open('live/data.json'))['boxscores']
def work(gk):
    gid=int(gk.split('_')[1]); g=df[df.GameId==gid]; dr=build_drives(g); out=[]
    for t,b in live[gk].items():
        c=b['defensive']['stopRate']
        od=[d for d in dr if d['team']!=t and d['_scrim']>0]
        if c is None or not od: continue
        out.append((c,[d['result'] for d in od]))
    return out
if __name__=='__main__':
    keys=[k for k in live if not k.startswith('6_')]
    with Pool(2) as p: rows=[x for y in p.map(work,keys,chunksize=8) for x in y]
    cats=sorted({r for _,rs in rows for r in rs}); print(cats)
    M=np.array([[rs.count(c) for c in cats] for _,rs in rows]); old=np.array([o for o,_ in rows])
    tot=M.sum(1)
    best=[]
    noncore=[c for c in cats if c not in ('Touchdown','Field Goal')]
    idx={c:i for i,c in enumerate(cats)}
    for den_ex in [(),('End of Half',),('End of Half','End of Game'),('End of Game',)]:
        den=tot-sum(M[:,idx[c]] for c in den_ex if c in idx)
        for k in range(len(noncore)+1):
            for sub in itertools.combinations(noncore,k):
                num=sum((M[:,idx[c]] for c in sub), np.zeros(len(rows)))
                with np.errstate(divide='ignore',invalid='ignore'):
                    v=np.where(den>0,100*num/den,np.nan)
                acc=np.mean(np.abs(v-old)<0.06)
                best.append((acc,den_ex,sub))
    best.sort(key=lambda x:-x[0])
    for b in best[:5]: print('%.1f%%'%(100*b[0]),'denominator excludes',b[1],'| stops =',b[2])
