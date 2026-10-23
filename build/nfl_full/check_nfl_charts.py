"""Drive-chart sanity checks for the NFL dashboard (same rules as the CFB check_week).
usage: check_nfl_charts.py out.json [week ...]"""
import sys, json, collections
D=json.load(open(sys.argv[1])); WK={int(w) for w in sys.argv[2:]}
def t2s(t): m,s=str(t).split(':'); return int(m)*60+int(s)
TO={'Interception','Interception (Pick-6)','Fumble','Fumble (Defensive TD)','Muffed Punt','Fumbled Kickoff','Fumbled Punt','Muffed Kickoff'}
SCORE_END={'Punt (Return TD)','Fumbled Punt','Muffed Kickoff','Touchdown','Field Goal','Safety','Interception (Pick-6)','Fumble (Defensive TD)','End of Half','End of Game','Muffed Punt','Fumbled Kickoff','Blocked Punt','Blocked FG'}
iss=collections.defaultdict(list)
for gk,v in D['boxscores'].items():
    teams=[t for t in v if t!='driveChart']; wk=v[teams[0]]['meta']['week']
    if WK and wk not in WK: continue
    fin={t:v[t]['meta']['ts'] for t in teams}; cur={t:0 for t in teams}; prev=None
    for x in v['driveChart']:
        t,o=x['team'],x['opponent']
        if x.get('teamScore') is not None:
            g=x['teamScore']-cur[t]; l=x['oppScore']-cur[o]
            if g<0 or l<0: iss['score down'].append((gk,x['n']))
            if x['result']=='Touchdown' and g<6: iss['TD without points'].append((gk,x['n']))
            if x['result']=='Field Goal' and g!=3: iss['FG not 3'].append((gk,x['n']))
            if x['result'] in ('Punt','Turnover on Downs','Missed FG','Interception','Fumble') and (g or l): iss['points on non-scoring drive'].append((gk,x['n'],x['result'],g,l))
            cur[t],cur[o]=x['teamScore'],x['oppScore']
        if prev:
            if (x['q1'],-t2s(x['t1'])+3)<(prev['q1'],-t2s(prev['t1'])): iss['drive order'].append((gk,prev['n'],x['n']))
            if prev['team']==t and prev['result'] not in SCORE_END and not (prev.get('q2')==2 and x['q1']==3) and not (x['q1']>=5 and x['q1']!=prev['q1']):
                iss['same team twice'].append((gk,prev['n'],prev['result'],x['n']))
        if x.get('spot1') is not None and (x['yards']>100 or x['yards']<-40) and not any(p.get('penalty') for p in x['playList']): iss['impossible yards'].append((gk,x['n'],x['yards']))
        prev=x
    if cur!=fin: iss['chart final'].append((gk,cur,fin))
    for t in teams:
        tov=sum(1 for x in v['driveChart'] if x['team']==t and x['result'] in TO); g=v[t]['turnovers']['giveaways']
        if tov!=g: iss['turnovers chart vs box'].append((gk,t,tov,g))
        if v[t]['opportunities'].get('points',0)>fin[t]: iss['opp points > final'].append((gk,t))
for t,L in D['games'].items():
    w=sum(x['result']=='W' for x in L); l=sum(x['result']=='L' for x in L)
    if (D['teams'][t]['wins'],D['teams'][t]['losses'])!=(w,l): iss['record'].append(t)
print('checked', 'weeks '+','.join(map(str,sorted(WK))) if WK else 'all')
for k,v in iss.items(): print(f'{k}: {len(v)}', v[:10])
if not iss: print('no issues')
