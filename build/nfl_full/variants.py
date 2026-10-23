import sys; sys.path.insert(0,'.')
import pandas as pd, numpy as np, json, collections
from nfl_season import flags2, NAME, _f, line_yards
from nfl_drives import build_drives
d=json.load(open('live_data.json')); p=flags2(pd.read_pickle('pbp.pkl')).sort_values('play_id')
AB={v:k for k,v in NAME.items()}
score=collections.Counter(); tot=collections.Counter()
def chk(name, mine, live, tol=0.051):
    tot[name]+=1
    if mine is None or live is None: score[name]+= (mine is None and live is None); return
    score[name]+= abs(mine-live)<=tol
for gk,b in d['boxscores'].items():
    g=p[p.game_id==gk]
    for tm,box in b.items():
        if tm=='driveChart': continue
        T=AB[tm]; o=g[g.posteam==T]; os_=o[o.is_scrim]; dd=g[(g.posteam!=T)&g.posteam.notna()]; ds=dd[dd.is_scrim]
        S=box['situational']; E=box['explosiveness']; D=box['defensive']; P=box['production']; R=box['rushing']
        # successPlays
        chk('succ all o epa>0', float((o.epa>0).sum()), S['successPlays'])
        chk('succ o success', float(_f(o,'success').sum()), S['successPlays'])
        chk('succ o play_type notna success', float(_f(o[o.play_type.notna()&(o.play_type!='no_play')],'success').sum()), S['successPlays'])
        chk('succ scrim+pen', float(_f(o[o.is_scrim|(o.play_type=='no_play')&o.down.notna()],'success').sum()), S['successPlays'])
        # passdown
        for nm,pdn in {'2&8,34&5':((os_.down==2)&(os_.ydstogo>=8))|(os_.down.isin([3,4])&(os_.ydstogo>=5)),
                       '2&10,34&7?':((os_.down==2)&(os_.ydstogo>=10))|(os_.down.isin([3,4])&(os_.ydstogo>=7)),
                       '2&8,3&5 only':((os_.down==2)&(os_.ydstogo>=8))|((os_.down==3)&(os_.ydstogo>=5)),
                       '2&8,34&5 excl4':((os_.down==2)&(os_.ydstogo>=8))|((os_.down==3)&(os_.ydstogo>=5)),
                       '2&9,34&5':((os_.down==2)&(os_.ydstogo>=9))|(os_.down.isin([3,4])&(os_.ydstogo>=5)),
                       '2&8,34&6':((os_.down==2)&(os_.ydstogo>=8))|(os_.down.isin([3,4])&(os_.ydstogo>=6)),
                       '2&10,34&5':((os_.down==2)&(os_.ydstogo>=10))|(os_.down.isin([3,4])&(os_.ydstogo>=5)),
                       '2&8,34&5 xGTG':(((os_.down==2)&(os_.ydstogo>=8))|(os_.down.isin([3,4])&(os_.ydstogo>=5)))}.items():
            chk('pd '+nm, float(pdn.sum()), S['passDownPlays'])
        # playsTotal
        chk('pt o notna type', float(o.play_type.notna().sum()), E['playsTotal'])
        chk('pt o excl no_play', float((o.play_type.notna()&(o.play_type!='no_play')).sum()), E['playsTotal'])
        chk('pt o excl timeouts', float((~o.desc.str.startswith('Timeout')).sum()), E['playsTotal'])
        chk('pt o excl to & no_play', float((o.play_type.notna()&~o.desc.str.startswith('Timeout')).sum()), E['playsTotal'])
        chk('pt o not special', float((o.play_type.isin(['run','pass','qb_kneel','qb_spike','no_play','punt','field_goal'])).sum()), E['playsTotal'])
        chk('pt o down notna', float(o.down.notna().sum()), E['playsTotal'])
        # ypp exclusions
        for th in [4,5,6]:
            chk(f'ypp ex <{th}', float((os_.yardline_100<th).sum()), P['yppExcludedPlays'])
            chk(f'ypp ex ytg<{th}', float((os_.ydstogo<th).sum()), P['yppExcludedPlays'])
        chk('ypp ex gtg&<=5', float(((os_.goal_to_go==1)&(os_.yardline_100<=5)).sum()), P['yppExcludedPlays'])
        # scrambles
        chk('scr qb_scramble', float(_f(o,'qb_scramble').sum()), P['scrambles'])
        chk('scr scrim', float(_f(os_,'qb_scramble').sum()), P['scrambles'])
        chk('scr no pen', float((_f(o,'qb_scramble')&(o.play_type!='no_play')).sum()), P['scrambles'])
        chk('scr rush_attempt', float((_f(o,'qb_scramble')&_f(o,'rush_attempt')).sum()), P['scrambles'])
        # havoc
        def hv(x):
            sk=_f(x,'sack'); it=_f(x,'interception'); pb=x.pass_defense_1_player_id.notna(); tf=_f(x,'tackled_for_loss'); ff=_f(x,'fumble_forced')
            return sk,it,pb,tf,ff
        sk,it,pb,tf,ff=hv(ds)
        chk('hp sk|it|pb', float((sk|it|pb).sum()), D['havocPass'])
        chk('hp db&(sk|it|pb)', float((ds.is_db&(sk|it|pb)).sum()), D['havocPass'])
        chk('hp db&(sk|it|pb|ff|tf)', float((ds.is_db&(sk|it|pb|ff|tf)).sum()), D['havocPass'])
        chk('hp passatt&(sk|it|pb|ff)', float((ds.is_passatt&(sk|it|pb|ff)).sum()), D['havocPass'])
        chk('hr rush&tf', float((ds.is_rush&tf).sum()), D['havocRush'])
        chk('hr rush&(tf|ff)', float((ds.is_rush&(tf|ff)).sum()), D['havocRush'])
        chk('hr rush&(yds<0|ff)', float((ds.is_rush&((ds.yds<0)|ff)).sum()), D['havocRush'])
        chk('hr rush&(yds<=0|ff)', float((ds.is_rush&((ds.yds<=0)|ff)).sum()), D['havocRush'])
        chk('hr rush&(yds<0)', float((ds.is_rush&(ds.yds<0)).sum()), D['havocRush'])
        chk('hr rush+scr&(tf|ff)', float(((ds.is_rush|_f(ds,'qb_scramble'))&(tf|ff)).sum()), D['havocRush'])
        chk('ff', float(ff.sum()), D['ff'])
        chk('ff all dd', float(_f(dd,'fumble_forced').sum()), D['ff'])
        # line yards / highlight
        rr=os_[os_.is_rush]; gy=rr.yds
        def lyA(y): return 1.2*y if y<0 else (y if y<=3 else (3+0.5*(y-3) if y<=8 else 5.5))
        def lyB(y): return 1.2*y if y<0 else (y if y<=4 else (4+0.5*(y-4) if y<=10 else 7.0))
        chk('ly B', float(gy.apply(lyB).sum()), R['lineYardsTotal'],0.06)
        chk('ly rushing_yards', float(rr.rushing_yards.fillna(rr.yds).apply(lyB).sum()), R['lineYardsTotal'],0.06)
        chk('ly A', float(gy.apply(lyA).sum()), R['lineYardsTotal'],0.06)
        op=gy[gy>=4]
        chk('hl CFB', float(op.apply(lambda y:0.5*(min(y,10)-4)+max(y-10,0)).sum()), R['highlightYardsTotal'],0.06)
        chk('hl yards-lineyards', float((op-op.apply(lyB)).sum()), R['highlightYardsTotal'],0.06)
        chk('hl 4-10 half,>10 full from 4?', float(op.apply(lambda y:0.5*(min(y,10)-4)+max(y-10,0)).sum()), R['highlightYardsTotal'],0.06)
        # availYards
        dr=[x for x in build_drives(g) if x['_tm']==T and x['_scrim']>0] if False else None
print('\n'.join(f'{k:35s} {score[k]}/{tot[k]}' for k in tot))
