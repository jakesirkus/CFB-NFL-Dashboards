"""Per-game (value, weight) for every season stat / radar metric that gets an opponent adjustment.
Each function takes ONE team's box score for one game (that team on offense) and returns (value, weight);
the same function on the opponent's box gives what this team's defense allowed.
Season value = sum(w*v)/sum(w) over games, which reproduces the season numbers (see opp_adjust.py --check)."""

def V(x): return x['value'] if isinstance(x, dict) and 'value' in x else x
def _n(x): return float(V(x) or 0)
def drop(b): return _n(b['production']['scrimPlays']) - _n(b['rushing']['rushAtt'])          # dropbacks (incl. sacks/scrambles)
def ratio(num, den): return (100.0 * num / den) if den else None
def comb(b, a, ra, c, rc):                                                                    # combine two sub-rates by count
    s = b['situational']; n1, n2 = _n(s[a]), _n(s[c]); n = n1 + n2
    return ((n1 * _n(s[ra]) + n2 * _n(s[rc])) / n if n else None), n

M = {
 # ---- radar / season (key: (fn, kind)); kind 'rate%' or 'per' only for formatting/rounding ----
 'epaPlay':        lambda b: (V(b['overall']['epaPlay']),             _n(b['production']['scrimPlays'])),
 'earlyEpa':       lambda b: (V(b['situational']['earlyEpaPlay']),    _n(b['situational']['earlyPass']) + _n(b['situational']['earlyRush'])),
 'earlySR':        lambda b: comb(b, 'earlyPass', 'earlyPassSuccessRate', 'earlyRush', 'earlyRushSuccessRate'),
 'lateSR':         lambda b: comb(b, 'latePass', 'latePassSuccessRate', 'lateRush', 'lateRushSuccessRate'),
 'seriesRate':     lambda b: (ratio(_n(b['conversions']['seriesConv']), _n(b['conversions']['series'])), _n(b['conversions']['series'])),
 'avgDist3rd':     lambda b: (V(b['situational']['avgDist3rd']),      _n(b['conversions']['thirdAtt'])),
 'rushEpa':        lambda b: (V(b['overall']['rushEpaPlay']),         _n(b['rushing']['rushAtt'])),
 'stuffPct':       lambda b: (ratio(_n(b['rushing']['stuffedRuns']), _n(b['rushing']['rushAtt'])), _n(b['rushing']['rushAtt'])),
 'lineYards':      lambda b: (V(b['rushing']['lineYardsPerCarry']),   _n(b['rushing']['rushAtt'])),
 'opportunityPct': lambda b: (ratio(_n(b['rushing']['opportunityRuns']), _n(b['rushing']['rushAtt'])), _n(b['rushing']['rushAtt'])),
 'ppo':            lambda b: (V(b['opportunities']['ppo']),           _n(b['opportunities']['trips'])),
 'explosivePct':   lambda b: (ratio(_n(b['explosiveness']['explosivePlays']), _n(b['production']['scrimPlays'])), _n(b['production']['scrimPlays'])),
 'passExplPct':    lambda b: (ratio(_n(b['explosiveness']['explPass']), drop(b)), drop(b)),
 'rushExplPct':    lambda b: (ratio(_n(b['explosiveness']['explRush']), _n(b['rushing']['rushAtt'])), _n(b['rushing']['rushAtt'])),
 'nonExplEpa':     lambda b: (V(b['explosiveness']['nonExplEpaPlay']), _n(b['production']['scrimPlays']) - _n(b['explosiveness']['explosivePlays'])),
 'passEpa':        lambda b: (V(b['overall']['passEpaPlay']),         drop(b) - _n(b['production'].get('scrambles', 0))),
 'dbEpa':          lambda b: (V(b['overall'].get('dbEpaPlay')),       drop(b)),
 'ydsPerDb':       lambda b: (V(b['overall']['passYpp']),             drop(b)),
 'passSR':         lambda b: (V(b['situational']['successPassRate']), drop(b)),
 'rushSR':         lambda b: (V(b['situational']['successRushRate']), _n(b['rushing']['rushAtt'])),
 'successRate':    lambda b: (V(b['overall']['successRate']),          _n(b['production']['scrimPlays'])),
 # ---- extra season-table stats (not on the radar) ----
 'ypp':            lambda b: (V(b['overall']['ypp']),                 _n(b['production']['scrimPlays']) - _n(b['production']['yppExcludedPlays'])),
 'ypr':            lambda b: (V(b['production']['rushYpp']),          _n(b['rushing']['rushAtt'])),
 'ypa':            lambda b: (V(b['overall']['passYpp']),             drop(b)),
 'thirdPct':       lambda b: (ratio(_n(b['conversions']['thirdConv']), _n(b['conversions']['thirdAtt'])), _n(b['conversions']['thirdAtt'])),
 'epaPerDrive':    lambda b: (V(b['overall']['epaPerDrive']),         _n(b['drives']['total'])),
}
# season-table field (offense, defense) for the non-radar stats, and for radar stats that are also season fields
SEASON = {'ypp': ('ypp', 'yppAllowed'), 'ypr': ('ypr', 'yprAllowed'), 'ypa': ('ypa', 'ypaAllowed'),
          'explosivePct': ('explosiveRate', 'explosiveRateAllowed'), 'rushEpa': ('epaPerRush', 'epaPerRushAllowed'),
          'passEpa': ('epaPerPass', 'epaPerPassAllowed'), 'dbEpa': ('epaPerDropback', 'epaPerDropbackAllowed'),
          'thirdPct': ('thirdPct', None), 'seriesRate': ('seriesRate', 'seriesRateAllowed'),
          'epaPerDrive': ('epaPerDrive', 'epaPerDriveAllowed'), 'ppo': ('ppo', 'ppoAllowed'),
          'earlySR': ('earlySR', 'earlySRAllowed')}
