"""Apply verified official finals to box metas, then repair any drive chart whose running score
doesn't match its box final (copy scores from the regenerated chart)."""
import sys, json, glob, subprocess
src=sys.argv[1]
TAG='<script id="dashboard-data" type="application/json">'
s=open(src+'/index.html').read(); a=s.index(TAG)+len(TAG); b=s.index('</script>',a)
D=json.loads(s[a:b]); of=json.load(open('official_finals.json'))
n=0
for gk,v in D['boxscores'].items():
    fin=of.get(gk.split('_')[1])
    if not fin: continue
    for t,x in v.items():
        if isinstance(x,dict) and 'meta' in x and t in fin:
            o=x['meta']['opp']; ts,os_=fin[t],fin[o]
            r='W' if ts>os_ else ('L' if ts<os_ else 'T')
            if (x['meta']['ts'],x['meta']['os'],x['meta']['result'])!=(ts,os_,r): n+=1
            x['meta'].update(ts=ts,os=os_,result=r)
print('box metas changed',n)
open(src+'/index.html','w').write(s[:a]+json.dumps(D,separators=(',',':'),ensure_ascii=False).replace('</','<\\/')+s[b:])
# charts
regen=json.load(open('regen_all.json'))
out=subprocess.run(['python3','scan_chart_scores.py',src],capture_output=True,text=True).stdout.splitlines()[1:]
flag=[l.split()[0] for l in out]
key=lambda x:(x['team'],x['q1'],x['t1'])
fixed=replaced=skipped=0
for f in sorted(glob.glob(src+'/drivecharts/*.json')):
    d=json.load(open(f)); ch=False
    for gk in flag:
        if gk not in d: continue
        new=regen.get(gk)
        if not new: skipped+=1; print('no regen',gk); continue
        old=d[gk]; nm={key(x):x for x in new}
        if sum(key(x) in nm for x in old)>=len(old)*0.95:
            for x in old:
                y=nm.get(key(x))
                if y: x['teamScore'],x['oppScore'],x['result'],x['color'],x['scored']=y['teamScore'],y['oppScore'],y['result'],y['color'],y['scored']
            fixed+=1
        else: d[gk]=new; replaced+=1
        ch=True
    if ch: json.dump(d,open(f,'w'),separators=(',',':'))
print('charts fixed',fixed,'replaced',replaced,'skipped',skipped)
