"""Regenerate one week's drive charts with the current builder into OUT (copy of SRC), only for games whose
new chart ends on the box final."""
import sys, json, glob, shutil, os, contextlib, io, pandas as pd; sys.path.insert(0,'.')
from boxscore import build_drives
from multiprocessing import Pool
WEEK=sys.argv[1]; SRC=sys.argv[2]; OUT=sys.argv[3]
df=pd.read_pickle('prepped_to.pkl')
def work(gk):
    g=df[df.GameId==int(gk.split('_')[1])]
    if g.empty: return gk,None
    with contextlib.redirect_stdout(io.StringIO()):
        ch=[{k:v for k,v in x.items() if not k.startswith('_')} for x in build_drives(g)]
    for x in ch:
        if x['result'] in ('Muffed Kickoff','Muffed Punt') or (x['plays']==0 and x['result']=='Fumble'): x['spot1']=None; x['spot2']=None
    return gk,json.loads(json.dumps(ch,default=float))
if __name__=='__main__':
    if SRC!=OUT:
        if os.path.exists(OUT): shutil.rmtree(OUT)
        shutil.copytree(SRC,OUT)
    T='<script id="dashboard-data" type="application/json">'
    s=open(OUT+'/index.html').read(); a=s.index(T)+len(T); b=s.index('</script>',a); D=json.loads(s[a:b])
    gks=[k for k in D['boxscores'] if k.split('_')[0]==WEEK]
    with Pool(4) as p: res=dict(p.map(work,gks))
    n=0
    for f in glob.glob(OUT+'/drivecharts/*.json'):
        d=json.load(open(f)); ch=False
        for gk in list(d):
            new=res.get(gk)
            if not new: continue
            fin={t:x['meta']['ts'] for t,x in D['boxscores'][gk].items() if t!='driveChart'}
            last=[x for x in new if x.get('teamScore') is not None][-1]
            if {last['team']:last['teamScore'],last['opponent']:last['oppScore']}!=fin: print('skip',gk); continue
            if d[gk]!=new: d[gk]=new; ch=True; n+=1
        if ch: json.dump(d,open(f,'w'),separators=(',',':'))
    json.dump(gks,open(OUT+f'/added_week{WEEK}.json','w'))
    print('week',WEEK,'charts replaced',n,'of',len(gks))
