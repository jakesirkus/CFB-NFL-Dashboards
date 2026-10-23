"""Re-derive the turnover section (full game + splits) and game-log 'to' for the listed games from current flags."""
import sys, json, glob, contextlib, io, pandas as pd; sys.path.insert(0,'.')
from boxscore import game_boxes
OUT=sys.argv[1]; GIDS=[int(x) for x in sys.argv[2].split(',')]
df=pd.read_pickle('prepped_to.pkl')
T='<script id="dashboard-data" type="application/json">'
s=open(OUT+'/index.html').read(); a=s.index(T)+len(T); b=s.index('</script>',a); D=json.loads(s[a:b])
key={int(k.split('_')[1]):k for k in D['boxscores']}
per_new={}
for gid in GIDS:
    gk=key.get(gid)
    if not gk: continue
    g=df[df.GameId==gid]
    with contextlib.redirect_stdout(io.StringIO()): full,per,_=game_boxes(g,g.Home.iloc[0],g.Away.iloc[0])
    for t,bx in D['boxscores'][gk].items():
        if t=='driveChart' or t not in full: continue
        old=bx['turnovers']; new=dict(full[t]['turnovers'])
        print(gk,t,'giveaways',old['giveaways'],'->',new['giveaways'],'takeaways',old['takeaways'],'->',new['takeaways'])
        bx['turnovers']=json.loads(json.dumps(new,default=float))
        for gm in D['games'].get(t,[]):
            if gm['week']==bx['meta']['week'] and gm['opp']==bx['meta']['opp']: gm['to']=int(new['giveaways']-new['takeaways'])
    per_new[gk]={sp:{t:json.loads(json.dumps(per[sp][t]['turnovers'],default=float)) for t in per[sp]} for sp in per}
open(OUT+'/index.html','w').write(s[:a]+json.dumps(D,separators=(',',':'),ensure_ascii=False).replace('</','<\\/')+s[b:])
for f in glob.glob(OUT+'/periods/*.json'):
    d=json.load(open(f)); ch=False
    for gk in d:
        if gk in per_new:
            for sp,tm in per_new[gk].items():
                for t,o in tm.items():
                    if t in d[gk].get(sp,{}) and d[gk][sp][t].get('turnovers') is not None: d[gk][sp][t]['turnovers']=o; ch=True
    if ch: json.dump(d,open(f,'w'),separators=(',',':'))
