import json, pandas as pd, sys; sys.path.insert(0,'.')
from boxscore import build_drives
from multiprocessing import Pool
df=pd.read_pickle('prepped.pkl')
live=json.load(open('live/data.json'))['boxscores']
SC={'Touchdown','Field Goal'}
def work(gk):
    gid=int(gk.split('_')[1]); g=df[df.GameId==gid]; dr=build_drives(g); out=[]
    for t,b in live[gk].items():
        c=b['defensive']['stopRate']
        if c is None: continue
        od=[d for d in dr if d['team']!=t and d['_scrim']>0]
        if not od: continue
        n=len(od)
        A=sum(d['result'] not in SC for d in od)
        B=sum(d['result'] not in SC and d['result']!='End of Half' for d in od)
        C=sum(d['result'] not in SC and d['result'] not in ('End of Half','End of Game','End of Regulation') for d in od)
        nC=sum(d['result'] not in ('End of Half','End of Game','End of Regulation') for d in od)
        oa=[d for d in dr if d['team']!=t and d['result']!='Kickoff (Return TD)']
        F=100*sum(d['result'] not in SC for d in oa)/len(oa)
        ob=[d for d in oa if d['_scrim']>0 or d['result'] in ('End of Half','End of Game','End of Regulation')]
        G=100*sum(d['result'] not in SC for d in ob)/len(ob)
        out.append(dict(F=F,G=G,old=c,A=100*A/n,B=100*B/n,C=100*C/n,D=100*C/nC if nC else None,E=100*B/sum(d['result']!='End of Half' for d in od)))
    return out
if __name__=='__main__':
    keys=[k for k in live if not k.startswith('6_')]
    with Pool(2) as p: r=pd.DataFrame([x for y in p.map(work,keys,chunksize=8) for x in y])
    for k in 'AFG': print(k, '%.1f%%'%(100*((r[k]-r.old).abs()<0.06).mean()))
