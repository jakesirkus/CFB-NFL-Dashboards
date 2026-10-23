"""Recompute the scoring-opportunity sections (full game + splits) of one week's box scores from the current builder."""
import sys, json, glob, contextlib, io, pandas as pd; sys.path.insert(0,'.')
from boxscore import game_boxes
from multiprocessing import Pool
WEEK=sys.argv[1]; OUT=sys.argv[2]
df=pd.read_pickle('prepped_to.pkl')
def work(gk):
    g=df[df.GameId==int(gk.split('_')[1])]
    if g.empty: return gk,None
    with contextlib.redirect_stdout(io.StringIO()): full,per,_=game_boxes(g,g.Home.iloc[0],g.Away.iloc[0])
    return gk,(json.loads(json.dumps({t:b['opportunities'] for t,b in full.items()},default=float)),json.loads(json.dumps({s:{t:b['opportunities'] for t,b in per[s].items()} for s in per},default=float)))
if __name__=='__main__':
    T='<script id="dashboard-data" type="application/json">'
    s=open(OUT+'/index.html').read(); a=s.index(T)+len(T); b=s.index('</script>',a); D=json.loads(s[a:b])
    gks=[k for k in D['boxscores'] if k.split('_')[0]==WEEK and (len(sys.argv)<4 or k in sys.argv[3].split(','))]
    with Pool(4) as p: res=dict(p.map(work,gks))
    n=0
    for gk in gks:
        if not res[gk]: continue
        for t,o in res[gk][0].items():
            if t in D['boxscores'][gk] and D['boxscores'][gk][t].get('opportunities')!=o: D['boxscores'][gk][t]['opportunities']=o; n+=1
    open(OUT+'/index.html','w').write(s[:a]+json.dumps(D,separators=(',',':'),ensure_ascii=False).replace('</','<\\/')+s[b:])
    m=0
    for f in glob.glob(OUT+'/periods/*.json'):
        d=json.load(open(f)); ch=False
        for gk in d:
            if gk not in res or not res[gk]: continue
            for sp,tm in res[gk][1].items():
                for t,o in tm.items():
                    if t in d[gk].get(sp,{}) and d[gk][sp][t].get('opportunities')!=o and d[gk][sp][t].get('opportunities') is not None:
                        d[gk][sp][t]['opportunities']=o; ch=True; m+=1
        if ch: json.dump(d,open(f,'w'),separators=(',',':'))
    print('week',WEEK,'full-game opportunity sections updated',n,'| split sections',m)
