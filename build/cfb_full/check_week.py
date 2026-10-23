import sys, json, glob, collections
OUT=sys.argv[1]; WEEK=int(sys.argv[2])
T='<script id="dashboard-data" type="application/json">'
s=open(OUT+'/index.html').read(); a=s.index(T)+len(T); b=s.index('</script>',a); D=json.loads(s[a:b])
OF=json.load(open('official_finals.json')); new=json.load(open(OUT+f'/added_week{WEEK}.json'))
CH={}; [CH.update(json.load(open(f))) for f in glob.glob(OUT+'/drivecharts/*.json')]
PE={}; [PE.update(json.load(open(f))) for f in glob.glob(OUT+'/periods/*.json')]
def t2s(t): m,s_=str(t).split(':'); return int(m)*60+int(s_)
issues=collections.defaultdict(list)
TO={'Interception','Interception (Pick-6)','Fumble','Fumble (Defensive TD)','Muffed Punt','Muffed Kickoff'}
SCORE_END={'Missed FG (Return TD)','Touchdown','Field Goal','Safety','Interception (Pick-6)','Fumble (Defensive TD)','Punt (Return TD)','Blocked Punt (TD)','Blocked FG (TD)','Kickoff (Return TD)','End of Half','End of Regulation','Muffed Punt','Muffed Kickoff','Two-Point (Turnover)'}
for gk in new:
    v=D['boxscores'][gk]; gid=gk.split('_')[1]; fin=OF.get(gid) or {t:x['meta']['ts'] for t,x in v.items() if t!='driveChart'}
    teams=[t for t in v if t!='driveChart']
    if len(teams)!=2: issues['box teams'].append((gk,teams))
    for t in teams:
        m=v[t]['meta']
        if (m['ts'],m['os'])!=(fin[t],fin[m['opp']]): issues['box final'].append((gk,t))
        if t in D['games']:
            gl=[x for x in D['games'][t] if x['week']==WEEK and x['opp']==m['opp']]
            if len(gl)!=1 or (gl[0]['ts'],gl[0]['os'],gl[0]['result'])!=(m['ts'],m['os'],m['result']): issues['game log'].append((gk,t))
        for sec in ('overall','production','rushing','situational','drives','defensive','turnovers','conversions','opportunities'):
            if sec not in v[t]: issues['box section missing'].append((gk,t,sec))
        if gk not in PE or any(t not in PE[gk][sp] for sp in ('q1','q2','q3','q4','h1','h2','thru3')): issues['period splits'].append((gk,t))
    ch=CH.get(gk)
    if not ch: issues['no drive chart'].append(gk); continue
    cur={t:0 for t in teams}; prev=None
    for x in ch:
        t=x['team']; o=x['opponent']
        if x.get('teamScore') is not None:
            if x['teamScore']<cur[t] or x['oppScore']<cur[o]: issues['score goes down'].append((gk,x['n']))
            if (x['teamScore']-cur[t])+(x['oppScore']-cur[o])>9: issues['score jump >9'].append((gk,x['n'],x['result']))
            gained=(x['teamScore']-cur[t]); lost=(x['oppScore']-cur[o])
            if x['result']=='Touchdown' and gained<6: issues['TD without points'].append((gk,x['n']))
            if x['result']=='Field Goal' and gained!=3: issues['FG not 3'].append((gk,x['n'],gained))
            if x['result'] in ('Punt','Turnover on Downs','Missed FG','Interception','Fumble') and (gained or lost): issues['points on non-scoring drive'].append((gk,x['n'],x['result'],gained,lost))
            cur[t],cur[o]=x['teamScore'],x['oppScore']
        if prev:
            if (x['q1'],-t2s(x['t1'])+3)<(prev['q1'],-t2s(prev['t1'])): issues['drive order'].append((gk,prev['n'],x['n']))
            if prev['team']==t and prev['result'] not in SCORE_END and not (prev.get('q2')==2 and x['q1']==3) and not (x['q1']>=5 and x['q1']!=prev['q1']): issues['same team twice (missing turnover?)'].append((gk,prev['n'],prev['result'],x['n']))
        if x.get('spot1') is not None and x.get('spot2') is not None and x['yards']>100-x['spot1']+5 and x['yards']-(x['spot2']-x['spot1'])>15 and sum('PENALTY' in p['text'] for p in x['playList'])<2:
            issues['drive yards > field'].append((gk,x['n'],x['yards'],x['spot1']))
        if (x['yards']>100 and not any('PENALTY' in p['text'] for p in x['playList'])) or x['yards']<-40: issues['impossible drive yards'].append((gk,x['n'],x['yards']))
        prev=x
    if cur!={t:fin[t] for t in teams}: issues['chart final'].append((gk,cur,fin))
    for t in teams:
        tov=sum(1 for x in ch if x['team']==t and x['result'] in TO)
        g=v[t]['turnovers']['giveaways']
        if tov!=g: issues['turnovers chart vs box'].append((gk,t,tov,g))
        pts=v[t]['opportunities']['points']
        if pts>fin[t]: issues['opportunity points > final'].append((gk,t,pts,fin[t]))
# whole-season consistency
for t,L in D['games'].items():
    w=sum(x['result']=='W' for x in L); l=sum(x['result']=='L' for x in L)
    if (D['teams'][t]['wins'],D['teams'][t]['losses'])!=(w,l): issues['record'].append(t)
    wk=[x['week'] for x in L]
    if len(wk)!=len(set((x['week'],x['opp']) for x in L)): issues['duplicate game log'].append(t)
    if D['teams'][t]['gp']!=len(L): issues['gp vs game logs'].append((t,D['teams'][t]['gp'],len(L)))
print('Week',WEEK,'games checked:',len(new))
for k,v in issues.items(): print(f'{k}: {len(v)}', v[:8])
pg=collections.defaultdict(set)
for k,v in issues.items():
    for it in v:
        if isinstance(it,tuple) and str(it[0]).count('_')==1: pg[it[0]].add((k,)+tuple(str(z) for z in it[1:2]))
json.dump({g:sorted(map(list,s_)) for g,s_ in pg.items()},open(OUT+f'/issues_week{WEEK}.json','w'))
if not issues: print('no issues')
