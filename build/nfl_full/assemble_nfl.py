"""Rebuild the full NFL dashboard data (all weeks) from nflverse pbp and swap it into the live page.
usage: assemble_nfl.py pbp.pkl live_data.json live.html out.html out.json week1 week2 ..."""
import sys, json, pickle; sys.path.insert(0,'.')
import pandas as pd, numpy as np
from nfl_season import flags2, NAME
from nfl_box import game_boxes
from nfl_drives import build_drives
from nfl_build_season import build_teams, game_entries
from nfl_radar import radar_raw

pbp, live_json, live_html, out_html, out_json = sys.argv[1:6]
WEEKS=[int(x) for x in sys.argv[6:]]
AB={v:k for k,v in NAME.items()}
live=json.load(open(live_json))
p=flags2(pd.read_pickle(pbp)).sort_values('play_id'); p=p[p.week.isin(WEEKS)]

# ---- box scores ----
B={}; DR={}
for gk,g in p.groupby('game_id'):
    B[gk]=game_boxes(g); DR[gk]=build_drives(g)

# templates (key order / key sets) from an existing box
tmpl=next(iter(live['boxscores'].values())); tname=[k for k in tmpl if k!='driveChart'][0]
TFULL=tmpl[tname]; TPER=TFULL['periods']['q1']
def shape(box, t):
    out={}
    for sec,keys in t.items():
        if sec in('meta','periods'): continue
        if box.get(sec) is None: out[sec]=None; continue
        out[sec]={k:box[sec].get(k) for k in keys}
    return out

# percentiles: share of team-games in the dataset at or below this value, per split and metric
def pools(split):
    P={}
    for gk,(full,per,_) in B.items():
        src=full if split=='full' else per[split]
        for t,bx in src.items():
            for k,v in bx['overall'].items():
                if v['_raw'] is not None: P.setdefault(k,[]).append(v['_raw'])
    return {k:np.array(v) for k,v in P.items()}
POOL={s:pools(s) for s in ['full','q1','q2','q3','q4','h1','h2','thru3']}
def add_pct(bx, split):
    for k,v in bx['overall'].items():
        raw=v.pop('_raw',None)
        v['pct']=None if raw is None else round(float(100*(POOL[split][k]<=raw+1e-12).mean()),1)

boxscores={}
for gk in sorted(B, key=lambda k:(int(k[5:7]),k)):
    full,per,chart=B[gk]; g=p[p.game_id==gk]
    home=g.home_team.iloc[0]; away=g.away_team.iloc[0]
    hs=int(g.total_home_score.max()); as_=int(g.total_away_score.max())
    rec={}
    for T,O in [(home,away),(away,home)]:
        add_pct(full[T],'full')
        for k in per: add_pct(per[k][T],k)
        ts,os_=(hs,as_) if T==home else (as_,hs)
        bx={'meta':{'opp':NAME[O],'week':int(gk[5:7]),'home':T==home,'result':'W' if ts>os_ else ('L' if ts<os_ else 'T'),'ts':ts,'os':os_}}
        bx.update(shape(full[T],TFULL))
        bx['periods']={k:shape(per[k][T],TPER) for k in TFULL['periods']}
        rec[NAME[T]]=bx
    rec['driveChart']=chart
    boxscores[gk]=rec

# ---- season team table ----
teams=build_teams(p,B,WEEKS,live['teams'])
for name,t in teams.items():
    ab=AB[name]
    td=[x for gk,L in DR.items() for x in L if x['_tm']==ab and x['_scrim']>0]
    od=[x for gk,L in DR.items() for x in L if ab in gk.split('_')[2:] and x['_tm']!=ab and x['_tm'] is not None and x['_scrim']>0]
    t.pop('_drives'); t.pop('_depa')
    t['_epd']=sum(x['_epa'] for x in td)/len(td) if td else None
    t['_epda']=sum(x['_epa'] for x in od)/len(od) if od else None
df=pd.DataFrame(teams).T
RANKS=[('epaPerRush',False),('epaPerPass',False),('epaPerRushAllowed',True),('epaPerPassAllowed',True),('explosiveRate',False),('explosiveRateAllowed',True),
       ('ypp',False),('yppAllowed',True),('thirdPct',False),('thirdPctD',False),('seriesRate',False),('seriesRateAllowed',True),
       ('epaPerDropback',False),('epaPerDropbackAllowed',True),('epaPerDrive',False),('epaPerDriveAllowed',True)]
df['epaPerDrive']=df['_epd']; df['epaPerDriveAllowed']=df['_epda']
rk={k:df[k].astype(float).rank(ascending=asc,method='min') for k,asc in RANKS}
# radar
raw={'off':{},'def':{}}
for name in teams:
    ab=AB[name]; t=teams[name]
    raw['off'][name]=radar_raw(p[p.posteam==ab], 100*t['seriesConv']/t['series'] if t['series'] else None)
    raw['def'][name]=radar_raw(p[p.defteam==ab], 100*t['seriesConvAllowed']/t['seriesAllowed'] if t['seriesAllowed'] else None)
LOWBETTER={'avgDist3rd','stuffPct'}
pct={}
for side in ['off','def']:
    R=pd.DataFrame(raw[side]).T.astype(float); pct[side]={}
    for k in R.columns:
        sgn=1 if side=='off' else -1
        if k in LOWBETTER: sgn=-sgn
        s=R[k]*sgn
        pct[side][k]=(100*s.rank(pct=True)) if k=='rushSR' else 100*(s.rank(method='average')-1)/(len(s)-1)
radar_keys=list(next(iter(live['teams'].values()))['radar']['off'].keys())
team_keys=[k for k in next(iter(live['teams'].values())).keys()]
out_teams={}
for name,t in teams.items():
    o={}
    for k in team_keys:
        if k=='ranks': o[k]={kk:int(rk[kk][name]) for kk,_ in RANKS}
        elif k=='radar':
            o[k]={'off':{kk:round(float(pct['off'][kk][name]),1) for kk in radar_keys},'offRaw':{kk:round(raw['off'][name][kk],3) for kk in radar_keys},
                  'def':{kk:round(float(pct['def'][kk][name]),1) for kk in radar_keys},'defRaw':{kk:round(raw['def'][name][kk],3) for kk in radar_keys}}
        elif k=='epaPerDrive': o[k]=round(t['_epd'],3)
        elif k=='epaPerDriveAllowed': o[k]=round(t['_epda'],3)
        else: o[k]=t.get(k)
    if 'ties' in t: o['ties']=t['ties']
    out_teams[name]=o

games=game_entries(p,B,WEEKS)
games={n:games[n] for n in live['games']}
n5=p[p.week==max(WEEKS)].game_id.nunique()
meta={'scope':f'Week {WEEKS[0]}-{WEEKS[-1]} combined, all NFL games','weeks':WEEKS,'league':'NFL',
      'note':(f'Week {WEEKS[-1]} includes the {n5} games completed and published by the data source at build time; the remaining Week {WEEKS[-1]} games will be added once they are final.'
              if len(sys.argv)>0 and n5<int(__import__('os').environ.get('FULLWEEK','15')) else 'All games for the weeks above were published by the data source at build time.')}
data={'teams':out_teams,'games':games,'totalTeams':32,'meta':meta,'boxscores':boxscores}
s=json.dumps(data,separators=(',',':'),allow_nan=False).replace('</','<\\/')
json.dump(data,open(out_json,'w'))
h=open(live_html).read(); a=h.index('<script id="dashboard-data" type="application/json">')+len('<script id="dashboard-data" type="application/json">'); b=h.index('</script>',a)
open(out_html,'w').write(h[:a]+s+h[b:])
print('games',len(boxscores),'teams',len(out_teams),meta)
import subprocess as _sp; _sp.run(['python3','-I','../add_ppo.py',out_html,out_html,'--data-only'],check=True)
_sp.run(['python3','-I','../add_early_sr.py','nfl',out_html,out_html],check=True)   # early-down success rate (Oct 26)
# box-score expected score (fixed model in ../xpts_model.json); PREV=<previous published nfl_vNN.html> keeps unchanged games' values
_x=['python3','-I','../add_xpts.py','nfl',out_html,out_html,'--all']+(['--prev',__import__('os').environ['PREV']] if __import__('os').environ.get('PREV') else [])
_sp.run(_x,check=True)
# opponent adjustments (user's power ratings, blend 0.25 (25% at-the-time / 75% current); Oct 27)
_sp.run(['python3','-I','../patch_oppadj_ui.py',out_html],check=True)
_sp.run(['python3','-I','../patch_rankings_ui.py',out_html],check=True)   # Rankings tab (Oct 27)
_sp.run(['python3','-I','../patch_schedule_ui.py',out_html],check=True)   # Schedule tab (Oct 27)
_sp.run(['python3','-I','../patch_matchup_ui.py',out_html],check=True)    # Matchup tab (Oct 27)
_sp.run(['python3','-I','../opp_adjust.py','nfl',out_html,out_html,'--blend','0.25'],check=True)
