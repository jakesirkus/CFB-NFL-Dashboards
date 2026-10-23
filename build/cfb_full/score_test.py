import sys, json, pandas as pd, collections; sys.path.insert(0,'.')
from boxscore import score_events
from penalties import learn_abbr_map
df=pd.read_pickle('prepped_to.pkl')
s=open('out4/index.html').read(); T='<script id="dashboard-data" type="application/json">'; a=s.index(T)+len(T); b=s.index('</script>',a)
D=json.loads(s[a:b])
weeks=[int(x) for x in sys.argv[1:]] or [6]
res=collections.Counter(); bad=[]
for gk,v in D['boxscores'].items():
    if int(gk.split('_')[0]) not in weeks: continue
    meta={t:x['meta']['ts'] for t,x in v.items() if isinstance(x,dict) and 'meta' in x}
    g=df[df.GameId==int(gk.split('_')[1])].copy()
    if g.empty: continue
    g['_oc']=-g['clock']; order=g.sort_values(['DriveNumber','Period','_oc','Id'])
    teams=list(meta)
    ev=score_events(order, learn_abbr_map(g,None,None))
    tally=collections.Counter()
    for e in ev:
        if e[1] is not None: tally[e[1]]+=e[2]
    fmax={t:0 for t in teams}
    for r in order.itertuples():
        if r.Offense in fmax and pd.notna(r.OffenseScore): fmax[r.Offense]=max(fmax[r.Offense],int(r.OffenseScore))
        if r.Defense in fmax and pd.notna(r.DefenseScore): fmax[r.Defense]=max(fmax[r.Defense],int(r.DefenseScore))
    sc=g[g.OffenseScore.notna()].sort_values(['Period','_oc','Id'])
    last=sc.iloc[-1]; lastsc={last.Offense:int(last.OffenseScore),last.Defense:int(last.DefenseScore)}
    t={k:tally.get(k,0) for k in teams}; l={k:lastsc.get(k) for k in teams}
    res[('tally==meta',t==meta)]+=1; res[('fmax==meta',fmax==meta)]+=1; res[('last==meta',l==meta)]+=1
    if t!=meta: bad.append((gk,'meta',meta,'tally',t,'max',fmax,'last',l))
print(res); 
for x in bad[:15]: print(x)
