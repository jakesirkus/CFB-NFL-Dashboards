"""Offline single-file CFB dashboard: out dir's index.html data + every period/drivechart shard inlined.
usage: build_offline.py OUT_DIR TEMPLATE_OFFLINE.html DEST.html"""
import sys, json, glob
OUT, TPL, DEST = sys.argv[1:4]
def blk(s, tag):
    o=f'<script id="{tag}" type="application/json">'; a=s.index(o)+len(o); return a, s.index('</script>',a)
def dump(x): return json.dumps(x,separators=(',',':'),ensure_ascii=False).replace('</','<\\/')
src=open(OUT+'/index.html').read(); t=open(TPL).read()
D=json.loads(src.slice if False else src[slice(*blk(src,'dashboard-data'))])
CH={}; [CH.update(json.load(open(f))) for f in glob.glob(OUT+'/drivecharts/*.json')]
PE={}; [PE.update(json.load(open(f))) for f in glob.glob(OUT+'/periods/*.json')]
for gk,v in D['boxscores'].items():
    if gk in CH: v['driveChart']=CH[gk]
new={'dashboard-data':dump(D),'period-index-data':src[slice(*blk(src,'period-index-data'))],
     'drivechart-index-data':src[slice(*blk(src,'drivechart-index-data'))],'period-data-inline':dump(PE)}
for tag in ('dashboard-data','period-index-data','period-data-inline','drivechart-index-data'):
    a,b=blk(t,tag); t=t[:a]+new[tag]+t[b:]
open(DEST,'w').write(t)
print('games',len(D['boxscores']),'charts',sum('driveChart' in v for v in D['boxscores'].values()),'periods',len(PE))
