import sys; sys.path.insert(0,'.')
import pandas as pd, numpy as np, json, collections
from nfl_season import flags2, NAME, _f
from nfl_drives import build_drives
d=json.load(open('live_data.json')); p=flags2(pd.read_pickle('pbp.pkl')).sort_values('play_id')
AB={v:k for k,v in NAME.items()}
score=collections.Counter(); tot=collections.Counter(); ex=collections.defaultdict(list)
def chk(name, mine, live, tol=0.051, tag=''):
    tot[name]+=1
    ok= (mine is None and live is None) if (mine is None or live is None) else abs(mine-live)<=tol
    score[name]+=ok
    if not ok: ex[name].append((tag,mine,live))
def sd(a,b): return a/b if b else None
for gk,b in d['boxscores'].items():
    g=p[p.game_id==gk]; drives=build_drives(g)
    for tm,box in b.items():
        if tm=='driveChart': continue
        T=AB[tm]; o=g[g.posteam==T]; os_=o[o.is_scrim]; dd=g[(g.posteam!=T)&g.posteam.notna()]; ds=dd[dd.is_scrim]
        D=box['defensive']; S=box['situational']; DR=box['drives']; OV=box['overall']
        sk,it,pb,ff=_f(ds,'sack'),_f(ds,'interception'),ds.pass_defense_1_player_id.notna(),_f(ds,'fumble_forced')
        hp=(ds.is_passatt&(sk|it|pb|ff)); hr=(ds.is_rush&((ds.yds<=0)|ff))
        chk('hv hp+hr', float(hp.sum()+hr.sum()), D['havocPlays'],0,gk+tm)
        ffo=_f(dd,'fumble_forced')&~dd.index.isin(ds[hp|hr].index)
        chk('hv hp+hr+ff other', float(hp.sum()+hr.sum()+ffo.sum()), D['havocPlays'],0,gk+tm)
        an=(sk|it|pb|ff|(ds.is_rush&(ds.yds<=0)))
        chk('hv any scrim', float(an.sum()), D['havocPlays'],0,gk+tm)
        an2=an|(_f(ds,'qb_scramble')&(ds.yds<=0))|_f(ds,'tackled_for_loss')
        chk('hv any+tfl', float(an2.sum()), D['havocPlays'],0,gk+tm)
        an3=an|_f(ds,'tackled_for_loss')
        chk('hv any|tfl col', float(an3.sum()), D['havocPlays'],0,gk+tm)
        # pass downs
        for nm,base in {'scrim':os_,'scrim+spike?':os_}.items():
            pdn=((base.down==2)&(base.ydstogo>=9))|(base.down.isin([3,4])&(base.ydstogo>=5))
            chk('pd 2&9 '+nm, float(pdn.sum()), S['passDownPlays'],0,gk+tm)
            pdn=((base.down==2)&(base.ydstogo>=8))|(base.down.isin([3,4])&(base.ydstogo>=5))
            pdn2=pdn&~((base.down==2)&(base.ydstogo==8)&(base.goal_to_go==1))
            chk('pd 2&8 not gtg ', float(pdn2.sum()), S['passDownPlays'],0,gk+tm)
        # drives
        tdr=[x for x in drives if x['_tm']==T and x['_scrim']>0]
        for nm,fn in {'yards/(100-s1)':lambda: sd(100*sum(x['yards'] for x in tdr), sum(100-x['spot1'] for x in tdr if x['spot1'] is not None)),
                      '(s2-s1)/(100-s1)':lambda: sd(100*sum((x['spot2'] or 0)-(x['spot1'] or 0) for x in tdr if x['spot1'] is not None), sum(100-x['spot1'] for x in tdr if x['spot1'] is not None)),
                      'mean (s2-s1)/(100-s1)':lambda: sd(100*sum(((x['spot2'] or 0)-x['spot1'])/(100-x['spot1']) for x in tdr if x['spot1'] is not None), sum(1 for x in tdr if x['spot1'] is not None)),
                      'mean yards/(100-s1)':lambda: sd(100*sum(x['yards']/(100-x['spot1']) for x in tdr if x['spot1'] is not None), sum(1 for x in tdr if x['spot1'] is not None)),
                      }.items():
            v=fn(); chk('ay '+nm, None if v is None else round(v,1), DR['availYardsPct'],0.051,gk+tm)
        for th in [20]:
            for nm,cond in {'any scrim<=20':lambda x: any(e['yardline100'] is not None and e['yardline100']<=20 and e['down'] is not None for e in x['playList']),
                            'spot2>=80':lambda x: (x['spot2'] or 0)>=80,
                            'opp30-like <=20':lambda x: any(e['yardline100'] is not None and e['yardline100']<=20 and (e['down'] is not None or 'TWO-POINT' in e['text']) and not e['penalty'] for e in x['playList'] ),
                            }.items():
                rz=[x for x in tdr if cond(x)]
                v=sd(100*sum(x['result']=='Touchdown' for x in rz),len(rz))
                chk('rz '+nm, None if v is None else round(v,3), OV['rzRate']['value'],0.002,gk+tm)
print('\n'.join(f'{k:35s} {score[k]}/{tot[k]}  {ex[k][:3]}' for k in tot))
