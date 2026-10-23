import sys; sys.path.insert(0,'.')
import pandas as pd, json, collections
from nfl_season import flags2
from nfl_drives import build_drives
d=json.load(open('live_data.json')); p=flags2(pd.read_pickle('pbp.pkl'))
cnt=collections.Counter(); bad=collections.defaultdict(list); nlen=collections.Counter()
for gk,b in d['boxscores'].items():
    live=b['driveChart']; mine=build_drives(p[p.game_id==gk])
    nlen[len(mine)-len(live)]+=1
    if len(mine)!=len(live): bad['_len'].append((gk,len(mine),len(live))); continue
    for a,l in zip(mine,live):
        for k,v in l.items():
            ok=(a.get(k)==v) if k!='playList' else (len(a[k])==len(v) and all(x==y for x,y in zip(a[k],v)))
            cnt[(k,ok)]+=1
            if not ok: bad[k].append((gk,int(l['n']),a.get(k) if k!='playList' else len(a[k]),v if k!='playList' else len(v), l['result']))
print(nlen)
for k in sorted({k for k,_ in cnt}): 
    if cnt[(k,False)]: print(k, cnt[(k,True)],'/',cnt[(k,True)]+cnt[(k,False)], bad[k][:14])
print(bad['_len'][:10])
