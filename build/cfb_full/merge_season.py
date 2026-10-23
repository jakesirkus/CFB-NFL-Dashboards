import pandas as pd, json
df = pd.read_pickle('combined_raw_fixed.pkl')
RUSH_TYPES = {'Rush','Rushing Touchdown','Two Point Rush'}
PASS_TYPES = {'Pass Reception','Pass Incompletion','Passing Touchdown','Sack','Interception',
              'Pass Interception Return','Interception Return Touchdown','Two Point Pass','Pass Completion'}
kneel = df['PlayText'].str.contains('kneel', case=False, na=False)
df['is_scrim'] = (df['PlayType'].isin(RUSH_TYPES) & ~kneel) | df['PlayType'].isin(PASS_TYPES)
sc = df[df['is_scrim']]

recs = json.load(open('final_teams.json'))
live = json.load(open('live/data.json'))
wk6 = json.load(open('week6_game_entries.json'))

for t, r in recs.items():
    o = sc[sc['Offense']==t]; d = sc[sc['Defense']==t]
    on = o[o['YardsToGoal']>5]; dn = d[d['YardsToGoal']>5]
    r['yppAllPlays'] = r['ypp']
    r['yppAllowedAllPlays'] = r['yppAllowed']
    r['yppExcludedPlays'] = int(len(o)-len(on))
    r['ypp'] = round(on['YardsGained'].sum()/len(on),2) if len(on) else 0
    r['yppAllowed'] = round(dn['YardsGained'].sum()/len(dn),2) if len(dn) else 0
# re-rank ypp / yppAllowed with new definitions
ts = list(recs)
for i,t in enumerate(sorted(ts, key=lambda t:-recs[t]['ypp'])): recs[t]['ranks']['ypp']=i+1
for i,t in enumerate(sorted(ts, key=lambda t:recs[t]['yppAllowed'])): recs[t]['ranks']['yppAllowed']=i+1

missing_keys=set()
for t, old in live['teams'].items():
    new = recs[t]
    out = {}
    for k in old.keys():
        if k in ('conf','confLabel'): out[k]=old[k]
        elif k in new: out[k]=new[k]
        else: missing_keys.add(k); out[k]=old[k]
    live['teams'][t]=out
print('keys not recomputed (kept old):', missing_keys)

added=0
for t, e in wk6.items():
    g = live['games'].setdefault(t, [])
    if not any(x['week']==6 and x['opp']==e['opp'] for x in g):
        g.append(e); added+=1
print('week6 game-log rows added:', added)
live['meta']['weeks']=[1,2,3,4,5,6]
live['meta']['scope']='Week 1-6 combined, FBS-involved games only'
for t,r in live['teams'].items():
    for side in ('offRaw','defRaw'):
        if isinstance(r['radar'][side].get('epaPlay'),float): r['radar'][side]['epaPlay']=round(r['radar'][side]['epaPlay'],3)
json.dump(live, open('data_new.json','w'), separators=(',',':'), default=float)
a=live['teams']['Alabama']; print({k:a[k] for k in ['gp','wins','losses','ypp','yppAllPlays','yppExcludedPlays','passYds','seriesRate']})
print('missouri/texas a&m games:', [g['week'] for g in live['games']['Missouri']], [g['week'] for g in live['games']['Texas A&M']])
print('mizzou gp', live['teams']['Missouri']['gp'], 'tamu gp', live['teams']['Texas A&M']['gp'])
