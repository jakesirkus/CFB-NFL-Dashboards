import numpy as np, pandas as pd
KNOTS = np.arange(0, 101, 5)
def _hat(y):
    y = np.clip(np.asarray(y, float), 0, 100)
    B = np.zeros((len(y), len(KNOTS)))
    i = np.minimum((y // 5).astype(int), len(KNOTS) - 2)
    w = (y - KNOTS[i]) / 5.0
    B[np.arange(len(y)), i] = 1 - w; B[np.arange(len(y)), i + 1] = w
    return B
def features(down, dist, ytg):
    down = np.asarray(down, int); dist = np.clip(np.asarray(dist, float), 1, 30); ytg = np.asarray(ytg, float)
    H = _hat(ytg); k = H.shape[1]
    X = np.zeros((len(down), 4 * (k + 2)))
    for d in range(1, 5):
        m = down == d; o = (d - 1) * (k + 2)
        X[m, o:o + k] = H[m]
        X[m, o + k] = np.log(dist[m]); X[m, o + k + 1] = np.minimum(dist[m], 20) / 10
    return X
class EP:
    def fit(self, df):
        d = df[df.is_rp & df.Down.isin([1,2,3,4]) & df.Distance.notna() & df.YardsToGoal.between(1, 99) & df.Ppa.notna()].copy()
        d = d.sort_values('Id')
        nxt = d.groupby(['GameId', 'DriveId']).shift(-1)
        # rows between consecutive plays (penalties etc.) would contaminate the pair -> require adjacency in the full feed
        full = df.sort_values('Id'); pos = pd.Series(np.arange(len(full)), index=full.Id.values)
        gap = pos.reindex(nxt.Id.values).values - pos.reindex(d.Id.values).values
        sc = d.Scoring.fillna(False).astype(bool).values
        td = sc & d.PlayType.isin(['Rushing Touchdown', 'Passing Touchdown']).values
        to = d.giveaway.values
        pair = (~np.isnan(nxt.Down.values)) & (gap == 1) & ~sc & ~to & (nxt.Offense.values == d.Offense.values)
        X0 = features(d.Down.values, d.Distance.values, d.YardsToGoal.values)
        Xp = X0[pair]; Xn = features(nxt.Down.values[pair], nxt.Distance.values[pair], nxt.YardsToGoal.values[pair])
        A = np.vstack([Xn - Xp, -X0[td]])
        b = np.concatenate([d.Ppa.values[pair], d.Ppa.values[td] - 7.0])
        lam = 1e-3
        self.w = np.linalg.solve(A.T @ A + lam * np.eye(A.shape[1]), A.T @ b)
        pred = A @ self.w
        self.r2 = 1 - ((b - pred) ** 2).sum() / ((b - b.mean()) ** 2).sum()
        self.n = len(b)
        return self
    def ep(self, down, dist, ytg):
        return features(down, dist, ytg) @ self.w
