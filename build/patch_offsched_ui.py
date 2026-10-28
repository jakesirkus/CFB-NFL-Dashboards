"""Off-schedule runs in the UI (data from add_offsched.py):
 - box score Rushing section: 'Off-Schedule Runs' count (rate) right after 'Opportunity Runs (Yds>=4)'
 - Leaderboard: 'Off-Sched Run % (Off)' (lower = better) and '(Def)' (higher = better); follow the Raw / Adjusted switch
Idempotent. usage: patch_offsched_ui.py PAGE.html [PAGE.html ...]"""
import sys
BOX_A = "      + bsRow('OL Line Yards*', bn(r1.lineYardsTotal,1), bn(r2.lineYardsTotal,1))\n"
BOX_N = ("      + bsRow('Off-Schedule Runs', r1.offSchedRuns==null?'—':bi(r1.offSchedRuns)+' ('+bn(r1.offSchedRate,0)+'%)', "
         "r2.offSchedRuns==null?'—':bi(r2.offSchedRuns)+' ('+bn(r2.offSchedRate,0)+'%)')\n")
LB_A = "    { key:'ppoDef', label:'Pts/Opp (Def)', type:'num', decimals:2, get:function(t){ return t.ppoAllowed; }, asc:true },\n"
LB_N = ("    { key:'offSched', label:'Off-Sched Run % (Off)', type:'pct1', get:function(t){ return t.offSchedPct; }, asc:true },\n"
        "    { key:'offSchedD', label:'Off-Sched Run % (Def)', type:'pct1', get:function(t){ return t.offSchedPctAllowed; } },\n")
for p in sys.argv[1:]:
    s = open(p).read()
    if "'Off-Schedule Runs'" in s: print(p, 'already patched'); continue
    assert s.count(BOX_A) == 1, (p, 'box anchor'); assert s.count(LB_A) == 1, (p, 'leaderboard anchor')
    s = s.replace(BOX_A, BOX_N + BOX_A).replace(LB_A, LB_A + LB_N)
    open(p, 'w').write(s); print(p, 'patched')
