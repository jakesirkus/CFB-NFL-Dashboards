import json, glob, sys
T='<script id="dashboard-data" type="application/json">'
s=open('out5/index.html').read(); a=s.index(T)+len(T); b=s.index('</script>',a); D=json.loads(s[a:b]); fbs=set(D['teams'])
CH={}; [CH.update(json.load(open(f))) for f in glob.glob('out5/drivecharts/*.json')]
want=sys.argv[1]; kinds=sys.argv[2].split(',') if len(sys.argv)>2 else None
for w in '1234567':
    for g,iss in sorted(json.load(open(f'out5/issues_week{w}.json')).items()):
        teams=[t for t in D['boxscores'][g] if t!='driveChart']
        if ('FBS' if any(t in fbs for t in teams) else 'FCS')!=want: continue
        for i in iss:
            if kinds and i[0] not in kinds: continue
            print(f'## {g} {" vs ".join(teams)} | {i}')
            ch=CH[g]
            try: n=int(i[1])
            except: 
                print('   box giveaways', {t:D['boxscores'][g][t]['turnovers']['giveaways'] for t in teams}); 
                for x in ch:
                    if x['result'] in ('Interception','Interception (Pick-6)','Fumble','Fumble (Defensive TD)','Muffed Punt','Muffed Kickoff'): print(f"   {x['n']} {x['team'][:12]} {x['result']} | {(x['playText'] or '')[:150]}")
                continue
            for x in ch:
                if n-1<=x['n']<=n+1: print(f"   {x['n']} {x['team'][:12]} Q{x['q1']} {x['t1']} sp{x['spot1']} {x['plays']}p {x['yards']}y {x['result']} {x['teamScore']}-{x['oppScore']} | {(x['playText'] or '')[:150]}")
