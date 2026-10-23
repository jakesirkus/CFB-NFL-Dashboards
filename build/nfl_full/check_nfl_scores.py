import sys, json, pandas as pd; sys.path.insert(0,'.')
from nfl_season import NAME
D=json.load(open(sys.argv[1])); p=pd.read_pickle(sys.argv[2])
bad=[]
for gk,v in D['boxscores'].items():
    meta={t:x['meta'] for t,x in v.items() if t!='driveChart'}
    fin={t:m['ts'] for t,m in meta.items()}
    g=p[p.game_id==gk]; h=NAME[g.home_team.iloc[0]]; a=NAME[g.away_team.iloc[0]]
    off={h:int(g.home_score.iloc[0]),a:int(g.away_score.iloc[0])}   # official final from the nflverse schedule
    if fin!=off: bad.append((gk,'box vs official',fin,off))
    for t,m in meta.items():
        gl=[x for x in D['games'][t] if x['week']==m['week'] and x['opp']==m['opp']]
        if not gl or (gl[0]['ts'],gl[0]['os'],gl[0]['result'])!=(m['ts'],m['os'],m['result']): bad.append((gk,'log',t))
    cur={t:0 for t in fin}; prob=[]
    for x in v['driveChart']:
        if x.get('teamScore') is None: continue
        t=x['team']; o=x['opponent']
        if x['teamScore']<cur[t] or x['oppScore']<cur[o]: prob.append(('down',x['n']))
        if (x['teamScore']-cur[t])+(x['oppScore']-cur[o])>9: prob.append(('jump',x['n']))
        cur[t],cur[o]=x['teamScore'],x['oppScore']
    if cur!=fin: prob.append(('final',cur,fin))
    if prob: bad.append((gk,'chart',prob))
for t,L in D['games'].items():
    w=sum(x['result']=='W' for x in L); l=sum(x['result']=='L' for x in L); tm=D['teams'][t]
    if (tm['wins'],tm['losses'],tm['pf'],tm['pa'])!=(w,l,sum(x['ts'] for x in L),sum(x['os'] for x in L)): bad.append((t,'record'))
print(len(D['boxscores']),'games; problems:',len(bad))
for b in bad: print(b)
