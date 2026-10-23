import sys; sys.path.insert(0,'.')
import pandas as pd, numpy as np, json, collections
from nfl_season import flags2, NAME, _f
d=json.load(open('live_data.json')); p=flags2(pd.read_pickle('pbp.pkl')).sort_values('play_id')
AB={v:k for k,v in NAME.items()}
score=collections.Counter(); tot=collections.Counter()
def chk(name, mine, live, tol=0.051):
    tot[name]+=1
    if mine is None or live is None or (isinstance(mine,float) and np.isnan(mine)): score[name]+= (live is None); return
    score[name]+= abs(mine-live)<=tol
LY={'C 4+0.5(y-5)':lambda y:1.2*y if y<0 else (y if y<=4 else (4+0.5*(y-5) if y<=10 else 6.5)),
    'D 0.5 from y>4 cap 10':lambda y:1.2*y if y<0 else (y if y<=4 else 4+0.5*(min(y,10)-4)),
    'E 1-3 full':lambda y:1.2*y if y<0 else (y if y<=3 else 3+0.5*(min(y,10)-3)),
    'F 0-4 full,5-10 half of y':lambda y:1.2*y if y<0 else (y if y<=4 else (0.5*y if y<=10 else 5)),
    'G int part':lambda y:1.2*y if y<0 else (y if y<=4 else 4+0.5*(min(y,11)-5)),
   }
for gk,b in d['boxscores'].items():
    g=p[p.game_id==gk]
    for tm,box in b.items():
        if tm=='driveChart': continue
        T=AB[tm]; o=g[g.posteam==T]; os_=o[o.is_scrim]
        S=box['situational']; R=box['rushing']
        gy=os_[os_.is_rush].yds
        for k,f in LY.items(): chk('ly '+k, float(gy.apply(f).sum()), R['lineYardsTotal'],0.06)
        for a in [8,9,10]:
          for c in [4,5,6]:
            for one in [False,True]:
                pdn=((os_.down==2)&(os_.ydstogo>=a))|(os_.down.isin([3,4])&(os_.ydstogo>=c))
                if one: pdn=pdn|((os_.down==1)&(os_.ydstogo>10))
                chk(f'pd 2&{a} 34&{c} 1st>10={one}', float(pdn.sum()), S['passDownPlays'])
        # mid8
        q=os_
        for nm,m in {'q2<=240|q3>=660':((q.qtr==2)&(q.quarter_seconds_remaining<=240))|((q.qtr==3)&(q.quarter_seconds_remaining>=660)),
                     'q2<240|q3>660':((q.qtr==2)&(q.quarter_seconds_remaining<240))|((q.qtr==3)&(q.quarter_seconds_remaining>660)),
                     'game 1560-2040':(q.game_seconds_remaining<=2040)&(q.game_seconds_remaining>=1560),
                     'q2 last4 only':((q.qtr==2)&(q.quarter_seconds_remaining<=240)),
                     'q2<=120|q3>=780':((q.qtr==2)&(q.quarter_seconds_remaining<=120))|((q.qtr==3)&(q.quarter_seconds_remaining>=780)),
                     'q2 <=480':((q.qtr==2)&(q.quarter_seconds_remaining<=480)),
                     'q2<=240|q4<=240':((q.qtr==2)&(q.quarter_seconds_remaining<=240))|((q.qtr==4)&(q.quarter_seconds_remaining<=240)),
                     }.items():
            mm=q[m]
            chk('m8 '+nm+' epa', float(round(mm.epa.sum(),1)), S['mid8Epa'],0.051)
            chk('m8 '+nm+' pass', float(mm.is_passatt.sum()), S['mid8Pass'],0)
            chk('m8 '+nm+' rush', float(mm.is_rush.sum()), S['mid8Rush'],0)
print('\n'.join(f'{k:40s} {score[k]}/{tot[k]}' for k in tot if score[k]>tot[k]*0.3))
