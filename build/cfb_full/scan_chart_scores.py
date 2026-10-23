import json,glob,sys
src=sys.argv[1]
s=open(src+'/index.html').read(); T='<script id="dashboard-data" type="application/json">'; a=s.index(T)+len(T); b=s.index('</script>',a)
D=json.loads(s[a:b])
fin={gk:{t:x['meta'] for t,x in v.items() if isinstance(x,dict) and 'meta' in x} for gk,v in D['boxscores'].items()}
bad={}
for f in sorted(glob.glob(src+'/drivecharts/*.json')):
    for gk,ch in json.load(open(f)).items():
        m=fin.get(gk); 
        if not m or not ch: continue
        cur={t:0 for t in m}; probs=[]
        for x in ch:
            t=x['team']; o=x.get('opponent') or [k for k in m if k!=t][0]
            ts,os_=x.get('teamScore'),x.get('oppScore')
            if ts is None: continue
            if t not in cur or o not in cur: continue
            if ts<cur[t] or os_<cur[o]: probs.append(('down',x.get('n')))
            if (ts-cur[t])+(os_-cur[o])>9: probs.append(('jump',x.get('n'),ts-cur[t],os_-cur[o]))
            cur[t],cur[o]=ts,os_
        if any(cur[t]!=m[t]['ts'] for t in m): probs.append(('final',cur,{t:m[t]['ts'] for t in m}))
        if probs: bad[gk]=probs
print(len(bad)); 
for k,v in bad.items(): print(k, v[:3])
