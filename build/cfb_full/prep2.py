"""Adds penalty-aware columns to the prepped play table and builds a penalty-event table.
Rules (per Jake): a first down gained via a defensive penalty is a successful play and
counts as a series conversion. Penalty EPA is estimated with an EP model fit to the
source's own PPA (R^2 ~0.97), since the feed has no EPA on penalty plays."""
import sys, pickle, numpy as np, pandas as pd
sys.path.insert(0, '.')
from penalties import parse_penalties
from epmodel import EP
from multiprocessing import Pool
NONPLAY = {'Timeout','End Period','End of Half','End of Game','End of Regulation','Kickoff','Kickoff Return (Offense)','Kickoff Return Touchdown','Uncategorized'}
EPM = pickle.load(open('ep_model.pkl','rb'))
def ep(d, dist, ytg):
    return float(EPM.ep([d],[dist],[ytg])[0])

def per_game(g):
    g = g.sort_values('Id')
    home, away = g.Home.iloc[0], g.Away.iloc[0]
    evs = parse_penalties(g, home, away)
    g = g.copy(); g['pen_fd'] = False
    nop = g.PlayText.fillna('').str.contains('NO PLAY', case=False)
    live_all = g[~g.PlayType.isin(NONPLAY) & g.Down.isin([1,2,3,4]) & g.Distance.notna() & g.YardsToGoal.between(1,99)]
    live = live_all
    ids = list(live.index)
    pos = {ix: i for i, ix in enumerate(ids)}
    out = []; seen = set()
    for e in evs:
        r = g.loc[e['idx']]
        if e['fd']: g.at[e['idx'], 'pen_fd'] = True
        epa = None
        if e['idx'] in pos and e['idx'] not in seen:
            i = pos[e['idx']]
            nxt = None
            for j in range(i+1, len(ids)):
                rr = g.loc[ids[j]]
                if rr.DriveId == r.DriveId and rr.Offense == r.Offense: nxt = rr
                break
            if nxt is not None:
                if r.PlayType == 'Penalty':
                    s0 = (r.Down, r.Distance, r.YardsToGoal)
                elif r.is_rp and not (r.Scoring == True) and not r.giveaway and pd.notna(r.YardsGained):
                    gy = r.YardsGained; y1 = r.YardsToGoal - gy
                    if gy >= r.Distance: s0 = (1, min(10, y1), y1)
                    elif r.Down < 4: s0 = (r.Down + 1, r.Distance - gy, y1)
                    else: s0 = None
                    if s0 is not None and not (1 <= s0[2] <= 99): s0 = None
                else: s0 = None
                if s0 is not None:
                    epa = ep(nxt.Down, nxt.Distance, nxt.YardsToGoal) - ep(*s0)
            seen.add(e['idx'])
        out.append(dict(GameId=r.GameId, Id=r.Id, Period=r.Period, Offense=r.Offense, Defense=r.Defense,
                        team=e['team'], side=e['side'], yards=e['yards'], fd=e['fd'], epa_off=epa))
    # success / success-rate plays under the penalty rule
    pen_play = (g.PlayType == 'Penalty') & g.pen_fd & g.Down.isin([1,2,3,4])
    # a rush/pass row wiped out by an accepted/offsetting penalty ('NO PLAY') is not a play for success purposes
    g['sr_play'] = (g.is_rp & ~(nop & ~g.pen_fd)) | pen_play
    g['succ2'] = (g.succ & g.is_rp & ~g.giveaway & g.sr_play) | (g.pen_fd & g.sr_play)
    ser = g.loc[live_all.index]
    live = ser[~(nop.loc[ser.index] & ~ser.pen_fd)]
    # series conversion flag per row (offense perspective): did this snap/penalty produce a new set of downs or a TD?
    g['conv'] = False; g['series_start'] = False
    for did, dr in live.groupby('DriveId', sort=False):
        dr = dr.sort_values('Id')
        for off, rows in dr.groupby('Offense', sort=False):
            rows = rows.sort_values('Id'); idxs = list(rows.index)
            pending = True; cur_start = None; cur_conv = False
            for k, ix in enumerate(idxs):
                r = rows.loc[ix]
                if pending: g.at[ix, 'series_start'] = True; pending = False; cur_start = ix; cur_conv = False
                sc = (r.Scoring == True); td = bool(sc and r.is_rp and not r.giveaway)
                own_pen = any(e['idx'] == ix and e['side'] == 'off' for e in evs)
                if td: c = True
                elif bool(g.at[ix, 'pen_fd']): c = True
                elif r.giveaway or r.PlayType in ('Punt','Field Goal Good','Field Goal Missed','Blocked Field Goal','Blocked Punt'): c = False
                elif k + 1 < len(idxs):
                    nx = rows.loc[idxs[k+1]]
                    if nx.Down == 1 and r.Down != 1: c = True
                    elif nx.Down == 1 and r.Down == 1: c = bool(r.is_rp and pd.notna(r.YardsGained) and r.YardsGained >= r.Distance and not own_pen)
                    else: c = False
                else:
                    c = bool(r.is_rp and pd.notna(r.YardsGained) and r.YardsGained >= r.Distance and not own_pen)
                if c:
                    g.at[ix, 'conv'] = True; cur_conv = True
                    if not td: pending = True
            # a series abandoned via kneel-down (clock-killing) is excluded, per the dashboard's Downs & Series note
            if cur_start is not None and not cur_conv and not pending:
                lr = rows.loc[idxs[-1]]
                if 'kneel' in str(lr.PlayText).lower():
                    g.at[cur_start, 'series_start'] = False
    return g, out

if __name__ == '__main__':
    df = pd.read_pickle('prepped.pkl')
    groups = [g for _, g in df.groupby('GameId')]
    with Pool(2) as p: res = p.map(per_game, groups, chunksize=8)
    df2 = pd.concat([r[0] for r in res]).sort_values('Id')
    ev = pd.DataFrame([e for r in res for e in r[1]])
    df2.to_pickle('prepped2.pkl'); ev.to_pickle('pen_events.pkl')
    print('rows', len(df2), 'penalty events', len(ev), 'with EPA', ev.epa_off.notna().sum(), 'pen_fd rows', int(df2.pen_fd.sum()))
