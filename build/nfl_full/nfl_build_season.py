import sys, pickle; sys.path.insert(0,'.')
import pandas as pd, numpy as np
from nfl_season import NAME, flags2, team_season, r
AB={v:k for k,v in NAME.items()}
def sd(a,b): return a/b if b else None
def build_teams(p, B, weeks, conf):
    w=p[p.week.isin(weeks)]
    games=[gk for gk in B if int(gk[5:7]) in weeks]
    teams={}
    for ab,name in NAME.items():
        m=team_season(w,ab); o=m.pop('_o'); dd=m.pop('_d')
        gl=[]; pf=pa=wins=losses=ties=0
        for gk in games:
            full,per,chart=B[gk]
            if ab not in full: continue
            g=w[w.game_id==gk]; home=g.home_team.iloc[0]; opp=g.away_team.iloc[0] if home==ab else home
            hs=int(g.total_home_score.max()); as_=int(g.total_away_score.max())
            ts,os_=(hs,as_) if home==ab else (as_,hs)
            pf+=ts; pa+=os_; wins+=ts>os_; losses+=ts<os_; ties+=ts==os_
        gp=wins+losses+ties
        os_=o[o.is_scrim]; ds=dd[dd.is_scrim]
        exo=(os_.goal_to_go==1)&(os_.yardline_100<=5); exd=(ds.goal_to_go==1)&(ds.yardline_100<=5)
        sboxes=[B[gk][0][ab] for gk in games if ab in B[gk][0]]
        ser=sum(b['conversions']['series'] for b in sboxes); serc=sum(b['conversions']['seriesConv'] for b in sboxes)
        sera=sum(b['conversions']['seriesAllowed'] for b in sboxes); serca=sum(b['conversions']['seriesConvAllowed'] for b in sboxes)
        nd=sum(b['drives']['total'] for b in sboxes)
        t=dict(conf=conf[name]['conf'],confLabel=conf[name]['confLabel'],gp=gp,wins=wins,losses=losses)
        if ties: t['ties']=ties
        t.update(pf=pf,pa=pa,ppg=r(sd(pf,gp),1),papg=r(sd(pa,gp),1))
        t.update(plays=m['plays'],totalYds=m['totalYds'],ypp=r(sd(os_[~exo].yds.sum(),(~exo).sum()),2),
                 rushAtt=m['rushAtt'],rushYds=m['rushYds'],rushTD=m['rushTD'],ypr=r(sd(m['rushYds'],m['rushAtt']),2),
                 passAtt=m['passAtt'],comp=m['comp'],passYds=m['passYds'],passTD=m['passTD'],compPct=r(sd(100*m['comp'],m['passAtt']),1),
                 ypa=r(sd(m['passYds'],m['passAtt']),2),explosivePlays=m['explosivePlays'],explosiveRate=r(sd(100*m['explosivePlays'],m['plays']),1),
                 playsAllowed=m['playsAllowed'],totalYdsAllowed=m['totalYdsAllowed'],yppAllowed=r(sd(ds[~exd].yds.sum(),(~exd).sum()),2),
                 rushYdsAllowed=m['rushYdsAllowed'],rushTDAllowed=m['rushTDAllowed'],yprAllowed=r(sd(m['rushYdsAllowed'],m['rushAttAllowed']),2),
                 rushAttAllowed=m['rushAttAllowed'],passAttAllowed=m['passAttAllowed'],ypaAllowed=r(sd(m['passYdsAllowed'],m['passAttAllowed']),2),
                 passYdsAllowed=m['passYdsAllowed'],passTDAllowed=m['passTDAllowed'],explosivePlaysAllowed=m['explosivePlaysAllowed'],
                 explosiveRateAllowed=r(sd(100*m['explosivePlaysAllowed'],m['playsAllowed']),1),
                 epaPerRush=m['epaPerRush'],epaPerPass=m['epaPerPass'],epaPerRushAllowed=m['epaPerRushAllowed'],epaPerPassAllowed=m['epaPerPassAllowed'],
                 sacksAllowed=m['sacksAllowed'],sacks=m['sacks'],giveaways=m['giveaways'],takeaways=m['takeaways'],turnoverMargin=m['turnoverMargin'],
                 thirdConv=m['thirdConv'],thirdSnaps=m['thirdSnaps'],thirdPct=r(sd(100*m['thirdConv'],m['thirdSnaps']),1),
                 fourthConv=m['fourthConv'],fourthSnaps=m['fourthSnaps'],thirdStops=m['thirdStops'],thirdSnapsD=m['thirdSnapsD'],
                 thirdPctD=r(sd(100*m['thirdStops'],m['thirdSnapsD']),1),
                 epaPerDropback=m['epaPerDropback'],epaPerDropbackAllowed=m['epaPerDropbackAllowed'],
                 seriesConv=int(serc),series=int(ser),seriesRate=r(sd(100*serc,ser),1),seriesConvAllowed=int(serca),seriesAllowed=int(sera),seriesRateAllowed=r(sd(100*serca,sera),1),
                 yppAllPlays=r(sd(m['totalYds'],m['plays']),2),yppExcludedPlays=int(exo.sum()),yppAllowedAllPlays=r(sd(m['totalYdsAllowed'],m['playsAllowed']),2),
                 earlySR=m['earlySR'],earlySRAllowed=m['earlySRAllowed'],earlyPlays=m['earlyPlays'],earlyPlaysAllowed=m['earlyPlaysAllowed'])
        t['_drives']=nd; t['_depa']=sum(b['drives']['epaPerDrive']*b['drives']['total'] for b in sboxes if b['drives']['epaPerDrive'] is not None)
        teams[name]=t
    return teams

def game_entries(p, B, weeks):
    from nfl_season import conv3, conv4
    w=p[p.week.isin(weeks)]
    out={n:[] for n in NAME.values()}
    for gk in sorted(B, key=lambda k:(int(k[5:7]),k)):
        if int(gk[5:7]) not in weeks: continue
        g=w[w.game_id==gk]; home=g.home_team.iloc[0]; away=g.away_team.iloc[0]
        hs=int(g.total_home_score.max()); as_=int(g.total_away_score.max())
        full=B[gk][0]
        for T,O in [(home,away),(away,home)]:
            o=g[(g.posteam==T)&g.is_scrim]; dd=g[(g.posteam==O)&g.is_scrim]
            ts,os_=(hs,as_) if T==home else (as_,hs)
            bx=full[T]; c=bx['conversions']
            t3=o[o.down==3]
            out[NAME[T]].append({'week':int(gk[5:7]),'opp':NAME[O],'home':T==home,'result':'W' if ts>os_ else ('L' if ts<os_ else 'T'),'ts':ts,'os':os_,
                'plays':len(o),'ypp':r(sd(o.yds.sum(),len(o)),2),'exp':int(o.expl.sum()),'expAllowed':int(dd.expl.sum()),
                'epaRush':r(o[o.is_rush].epa.mean(),3),'epaPass':r(o[o.is_passatt].epa.mean(),3),
                'epaRushAllowed':r(dd[dd.is_rush].epa.mean(),3),'epaPassAllowed':r(dd[dd.is_passatt].epa.mean(),3),
                'rushYds':int(o[o.is_rush].yds.sum()),'passYds':int(o[o.is_db].yds.sum()),
                'thirdPct':r(sd(100*int(conv3(t3).sum()),len(t3)),1),
                'to':int(bx['turnovers']['giveaways']-bx['turnovers']['takeaways']),'epaDb':r(o[o.is_db].epa.mean(),3),
                'thirdConv':int(c['thirdConv']),'thirdAtt':int(c['thirdAtt']),'fourthConv':int(c['fourthConv']),'fourthAtt':int(c['fourthAtt']),
                'seriesRate':c['seriesRate'],'seriesRateAllowed':c['seriesRateAllowed']})
    return out
