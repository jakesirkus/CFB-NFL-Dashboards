import sys; sys.path.insert(0,'.')
import pandas as pd, json, collections
from nfl_season import flags2
from nfl_drives import build_drives
d=json.load(open('live_data.json')); p=flags2(pd.read_pickle('pbp.pkl'))
c=collections.Counter(); ex=collections.defaultdict(list)
for gk,b in d['boxscores'].items():
    live=b['driveChart']; mine=build_drives(p[p.game_id==gk])
    if len(mine)!=len(live): continue
    for a,l in zip(mine,live):
        if len(a['playList'])!=len(l['playList']): continue
        for x,y in zip(a['playList'],l['playList']):
            for k in set(x)|set(y):
                if x.get(k)!=y.get(k): c[k]+=1; ex[k].append((x.get(k),y.get(k),y['text'][:60]))
print(c)
for k in c: print(k, ex[k][:5])
