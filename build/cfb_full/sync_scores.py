"""Final consistency step for the CFB dashboard (run on every build before publishing).
The box score's final comes from a play-by-play scoring tally, which survives feed glitches
(duplicated touchdown rows, swapped kickoff scores). Game-log scores/results and the season
W-L are re-derived from it so the three can never disagree.
usage: sync_scores.py in.html out.html"""
import sys, json
TAG='<script id="dashboard-data" type="application/json">'
src,dst=sys.argv[1:3]
s=open(src).read(); a=s.index(TAG)+len(TAG); b=s.index('</script>',a)
d=json.loads(s[a:b])
box={}
for gk,v in d['boxscores'].items():
    for t,x in v.items():
        if isinstance(x,dict) and 'meta' in x: box[(t,x['meta']['week'],x['meta']['opp'])]=x['meta']
changed=[]
for t,L in d['games'].items():
    for g in L:
        m=box.get((t,g['week'],g['opp']))
        if m and (m['ts'],m['os'],m['result'])!=(g['ts'],g['os'],g['result']):
            changed.append((t,g['week'],g['opp'],f"{g['ts']}-{g['os']} {g['result']}",f"{m['ts']}-{m['os']} {m['result']}"))
            g['ts'],g['os'],g['result']=m['ts'],m['os'],m['result']
for t,L in d['games'].items():
    tm=d['teams'].get(t)
    if not tm: continue
    w=sum(g['result']=='W' for g in L); l=sum(g['result']=='L' for g in L)
    if (tm['wins'],tm['losses'])!=(w,l): changed.append((t,'record',f"{tm['wins']}-{tm['losses']}",f"{w}-{l}"))
    tm['wins'],tm['losses']=w,l
for c in changed: print(c)
js=json.dumps(d,separators=(',',':'),ensure_ascii=False).replace('</','<\\/')
open(dst,'w').write(s[:a]+js+s[b:])
print('changes',len(changed))
