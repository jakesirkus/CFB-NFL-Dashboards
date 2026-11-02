"""Pace + projected score UI (data: add_pace.py -> box/teams pace fields, add_totals.py -> DATA.meta.totals).
 - box score Drives section: Time of Possession, Sec/Play (tempo)
 - team page tiles: Sec / play (adj) on offense, Pace faced (adj) on defense
 - Leaderboard: Sec/Play Adj, Neutral Sec/Play, Pace Faced Adj, Plays/G, Drives/G, Plays/Drive, TOP/G
 - Matchup tab: Site picker (A home / B home / neutral) + 'Projected score & pace' card (model score, total, spread, possessions,
   pace comparison, backtest accuracy).
Run after patch_matchup_ui / patch_offsched_ui. Idempotent. usage: patch_pace_ui.py PAGE.html [PAGE.html ...]"""
import sys
BOX_A = "      + bsRow('Available Yards %*', bp(d1.availYardsPct), bp(d2.availYardsPct));"
BOX_N = ("      + bsRow('Available Yards %*', bp(d1.availYardsPct), bp(d2.availYardsPct))\n"
         "      + bsRow('Time of Possession', pcMMSS(a.pace&&a.pace.topSec), pcMMSS(b.pace&&b.pace.topSec))\n"
         "      + bsRow('Sec/Play (tempo)*', a.pace&&a.pace.secPlay!=null?a.pace.secPlay.toFixed(1):'\\u2014', b.pace&&b.pace.secPlay!=null?b.pace.secPlay.toFixed(1):'\\u2014');")
FN_A = "  function buildDrivesSection(a, b, heads){"
FN = ("  function pcMMSS(s){ if(s==null||isNaN(s)||!s) return '\\u2014'; s=Math.round(s); return Math.floor(s/60)+':'+('0'+(s%60)).slice(-2); }\n")
TILE_O = "    tile(offTiles,'Rush + pass TD', (t.rushTD+t.passTD), 'off');"
TILE_D = "    tile(defTiles,'Explosive allowed', t.explosivePlaysAllowed, 'def');"
LB_A = "    { key:'offSchedD', label:'Off-Sched Run % (Def)', type:'pct1', get:function(t){ return t.offSchedPctAllowed; } },\n"
LB_N = ("    { key:'paceAdj', label:'Sec/Play Adj (Off)', type:'num', decimals:1, get:function(t){ return t.secPlayAdj; }, asc:true },\n"
        "    { key:'paceNeu', label:'Neutral Sec/Play (Off)', type:'num', decimals:1, get:function(t){ return t.secPlayNeutral; }, asc:true },\n"
        "    { key:'paceFaced', label:'Pace Faced Adj (Def)', type:'num', decimals:1, get:function(t){ return t.secPlayFacedAdj; }, asc:true },\n"
        "    { key:'playsPG', label:'Plays/G', type:'num', decimals:1, get:function(t){ return t.playsPG; } },\n"
        "    { key:'drivesPG', label:'Drives/G', type:'num', decimals:1, get:function(t){ return t.drivesPG; } },\n"
        "    { key:'playsPerDrive', label:'Plays/Drive', type:'num', decimals:2, get:function(t){ return t.playsPerDrive; } },\n"
        "    { key:'topPG', label:'TOP/G (min)', type:'num', decimals:1, get:function(t){ return t.topPG==null?null:t.topPG/60; } },\n")
SITE_A = '<datalist id="mtTeams"></datalist>'
SITE_N = ('<div class="control"><label for="mtSite">Site</label><select id="mtSite"><option value="a">Team A at home</option>'
          '<option value="b">Team B at home</option><option value="n">Neutral site</option></select></div>\n      ' + SITE_A)
MT_A = "    var html = '';\n    if(R && R[a] && R[b] && R[a].adjRank && R[b].adjRank){"
MT_N = "    var html = mtProjection(a, b);\n    if(R && R[a] && R[b] && R[a].adjRank && R[b].adjRank){"
MT_FN_A = "  function renderMatchup(){"
MT_FN = r"""  function mtProjection(a, b){            // projected score / total (DATA.meta.totals) + pace comparison
    var M = DATA.meta && DATA.meta.totals; if(!M || !M.teams || !M.teams[a] || !M.teams[b]) return '';
    var site = (document.getElementById('mtSite')||{}).value || 'a', ha = site==='a' ? 1 : (site==='b' ? -1 : 0);
    var A = M.teams[a], B = M.teams[b], poss = M.muD + A[2] + B[2];
    var kc = (M.calib||0)/2, pa = Math.max(0, poss/2*(M.mu + M.h*ha + A[0] + B[1]) - kc), pb = Math.max(0, poss/2*(M.mu - M.h*ha + B[0] + A[1]) - kc);
    var fav = pa>=pb ? a : b, spr = Math.abs(pa-pb);
    var siteTxt = ha===1 ? a+' at home' : (ha===-1 ? b+' at home' : 'neutral site');
    var TA = teams[a] || {}, TB = teams[b] || {};
    function f1(v){ return v==null||isNaN(v) ? '—' : Number(v).toFixed(1); }
    function rk(t, k){ var r = t.paceRanks && t.paceRanks[k]; return r ? '<span class="pc">#'+r+'</span>' : ''; }
    function row(lab, va, vb, tip){ return '<tr'+(tip?' title="'+tip+'"':'')+'><td>'+lab+'</td><td class="num">'+va+'</td><td class="num">'+vb+'</td></tr>'; }
    var bt = M.backtest || {};
    var h = '<div class="mt-card"><h3>Projected score &amp; pace</h3>'
      + '<div class="mt-sub">Model ('+siteTxt+'): built from each team’s opponent-adjusted <b>deserved</b> points per drive (turnovers, return TDs and red-zone luck stripped out) times the projected number of possessions from both teams’ pace.'
      + (bt.games ? ' Backtest (every game predicted only from earlier weeks, '+bt.games+' games): average miss on the total '+f1(bt.modelMaeSameGames!=null?bt.modelMaeSameGames:bt.mae)+' pts'+(bt.vegasMae!=null?' vs Vegas closing totals '+f1(bt.vegasMae)+' pts':'')+'.' : '')
      + '</div>'
      + '<div style="display:flex;flex-wrap:wrap;gap:18px;align-items:baseline;margin:6px 0 10px">'
      + '<div><span class="mt-a" style="font-size:22px;font-weight:700">'+f1(pa)+'</span> <span style="color:var(--ink-muted)">'+a+'</span></div>'
      + '<div><span class="mt-b" style="font-size:22px;font-weight:700">'+f1(pb)+'</span> <span style="color:var(--ink-muted)">'+b+'</span></div>'
      + '<div><b>Total '+f1(pa+pb)+'</b></div><div>'+(spr<0.05?'Even':fav+' by '+f1(spr))+'</div>'
      + '<div style="color:var(--ink-muted)">'+f1(poss)+' possessions</div></div>'
      + '<div class="mt-wrap"><table class="mt"><thead><tr><th>Pace</th><th>'+a+'</th><th>'+b+'</th></tr></thead><tbody>'
      + row('Sec/play, situation-adjusted', f1(TA.secPlayAdj)+rk(TA,'secPlayAdj'), f1(TB.secPlayAdj)+rk(TB,'secPlayAdj'), 'Seconds between snaps with the clock running, adjusted for score, quarter, play type and opponent. Lower = faster (#1 = fastest).')
      + row('Sec/play, neutral situations', f1(TA.secPlayNeutral), f1(TB.secPlayNeutral), 'Quarters 1-3, score within 7')
      + row('Sec/play, raw', f1(TA.secPlay), f1(TB.secPlay))
      + row('Pace faced on defense (adj.)', f1(TA.secPlayFacedAdj)+rk(TA,'secPlayFacedAdj'), f1(TB.secPlayFacedAdj)+rk(TB,'secPlayFacedAdj'), 'Tempo opponents ran against this defense')
      + row('Plays / game', f1(TA.playsPG)+rk(TA,'playsPG'), f1(TB.playsPG)+rk(TB,'playsPG'))
      + row('Drives / game', f1(TA.drivesPG)+rk(TA,'drivesPG'), f1(TB.drivesPG)+rk(TB,'drivesPG'))
      + row('Plays / drive', TA.playsPerDrive==null?'—':TA.playsPerDrive.toFixed(2), TB.playsPerDrive==null?'—':TB.playsPerDrive.toFixed(2))
      + row('Time of possession / game', pcMMSS(TA.topPG), pcMMSS(TB.topPG))
      + row('Plays allowed / game', f1(TA.playsAllowedPG), f1(TB.playsAllowedPG))
      + '</tbody></table></div></div>';
    return h;
  }
"""
for p in sys.argv[1:]:
    s = open(p).read()
    if 'function mtProjection(' in s: print(p, 'already patched'); continue
    for a_, nm in ((BOX_A, 'box'), (FN_A, 'drives fn'), (TILE_O, 'off tile'), (TILE_D, 'def tile'), (LB_A, 'leaderboard'), (SITE_A, 'site'), (MT_A, 'matchup html'), (MT_FN_A, 'matchup fn')):
        assert s.count(a_) == 1, (p, nm, s.count(a_))
    s = s.replace(BOX_A, BOX_N).replace(FN_A, FN + FN_A)
    s = s.replace(TILE_O, TILE_O + "\n    tile(offTiles,'Sec / play (adj)', t.secPlayAdj==null?'\\u2014':t.secPlayAdj.toFixed(1)+(t.paceRanks&&t.paceRanks.secPlayAdj?' (#'+t.paceRanks.secPlayAdj+')':''), 'off');")
    s = s.replace(TILE_D, TILE_D + "\n    tile(defTiles,'Pace faced (adj s/play)', t.secPlayFacedAdj==null?'\\u2014':t.secPlayFacedAdj.toFixed(1), 'def');")
    s = s.replace(LB_A, LB_A + LB_N).replace(SITE_A, SITE_N).replace(MT_A, MT_N).replace(MT_FN_A, MT_FN + MT_FN_A)
    s = s.replace("  mtA.addEventListener('change', renderMatchup);", "  mtA.addEventListener('change', renderMatchup); document.getElementById('mtSite').addEventListener('change', renderMatchup);", 1)
    assert "document.getElementById('mtSite').addEventListener" in s, (p, 'site listener')
    open(p, 'w').write(s); print(p, 'patched')
