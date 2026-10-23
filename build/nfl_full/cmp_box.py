import sys; sys.path.insert(0,'.')
import pandas as pd, json
from nfl_season import flags2, NAME
from nfl_box import game_boxes
from compare import report
d=json.load(open('live_data.json')); p=flags2(pd.read_pickle('pbp.pkl'))
AB={v:k for k,v in NAME.items()}
pairs=[]; ppairs=[]
for gk,b in d['boxscores'].items():
    full,per,chart=game_boxes(p[p.game_id==gk])
    for tm,box in b.items():
        if tm=='driveChart': continue
        mine=full[AB[tm]]
        pairs.append((gk+':'+tm, mine, {k:v for k,v in box.items() if k not in('meta','periods')}))
        if 'periods' in sys.argv:
            for k in box['periods']: ppairs.append((gk+':'+tm+':'+k, per[k][AB[tm]], box['periods'][k]))
report(pairs)
if ppairs: print('--- periods'); report(ppairs)
