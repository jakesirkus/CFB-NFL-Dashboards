"""Add a 'Matchup' tab: pick two teams; their opponent-adjusted unit ranks face off (O vs D, rush O vs rush D, pass O vs
pass D), then every radar stat lines up offense-vs-defense both ways with an edge call from the percentile gap
(>=20 'Edge', >=40 'Big edge'). Stats follow the Raw / Opponent-adjusted switch; ranks are always adjusted.
Run after patch_schedule_ui.py. Idempotent. usage: patch_matchup_ui.py PAGE.html [PAGE.html ...]"""
import sys, re
BTN = '<button class="tab-btn" id="tabBtnMatchup" data-target="matchup" role="tab" aria-selected="false">Matchup</button>'
VIEW = '''<div data-view="matchup">
    <style>
      .mt-pick{ display:flex; flex-wrap:wrap; gap:10px 14px; align-items:flex-end; }
      .mt-swap{ font:inherit; font-size:13px; font-weight:600; padding:7px 12px; border-radius:8px; border:1px solid var(--line); background:var(--surface-2); color:var(--ink-2); cursor:pointer; }
      .mt-card{ border:1px solid var(--line); border-radius:12px; background:var(--surface); padding:14px 16px; }
      .mt-card h3{ margin:0 0 4px; font-size:16px; }
      .mt-sub{ font-size:12px; color:var(--ink-muted); margin-bottom:10px; }
      table.mt{ border-collapse:collapse; width:100%; font-size:13px; }
      table.mt th, table.mt td{ padding:6px 8px; border-bottom:1px solid var(--line); text-align:right; white-space:nowrap; }
      table.mt th{ font-size:10.5px; text-transform:uppercase; letter-spacing:0.04em; color:var(--ink-muted); font-weight:600; }
      table.mt td:first-child, table.mt th:first-child{ text-align:left; }
      table.mt td.grp{ text-align:left; font-weight:700; font-size:11px; text-transform:uppercase; letter-spacing:0.05em; color:var(--ink-muted); background:var(--surface-2); }
      table.mt .pc{ color:var(--ink-muted); font-size:11px; margin-left:4px; }
      table.mt td.edge{ text-align:left; font-weight:600; }
      .mt-a{ color:var(--off); } .mt-b{ color:var(--def); } .mt-even{ color:var(--ink-muted); font-weight:400; }
      .mt-bar{ display:inline-block; height:8px; border-radius:4px; vertical-align:middle; margin-right:6px; }
      .mt-wrap{ overflow-x:auto; }
    </style>
    <div class="mt-pick">
      <div class="control"><label for="mtA">Team A</label><input id="mtA" list="mtTeams" placeholder="Start typing…" autocomplete="off"></div>
      <button class="mt-swap" id="mtSwap" type="button" title="Swap teams">\u21C4 Swap</button>
      <div class="control"><label for="mtB">Team B</label><input id="mtB" list="mtTeams" placeholder="Start typing…" autocomplete="off"></div>
      <datalist id="mtTeams"></datalist>
    </div>
    <div class="scope-note" id="mtNote" style="max-width:none"></div>
    <div id="mtOut"></div>
  </div>

  '''
JS = """
  // ---------- Matchup tab ----------
  var MT_GROUPS = [
    ['Overall', ['epaPlay','earlyEpa','earlySR','lateSR','seriesRate','avgDist3rd','ppo','explosivePct','nonExplEpa']],
    ['Rushing', ['rushEpa','rushSR','opportunityPct','lineYards','stuffPct','rushExplPct']],
    ['Passing', ['passEpa','dbEpa','passSR','ydsPerDb','passExplPct']]
  ];
  var MT_PCT = { lateSR:1, seriesRate:1, earlySR:1, stuffPct:1, opportunityPct:1, explosivePct:1, passExplPct:1, rushExplPct:1, passSR:1, rushSR:1 };
  var mtA = document.getElementById('mtA'), mtB = document.getElementById('mtB');
  (function(){ var dl=document.getElementById('mtTeams'); teamKeys.slice().sort().forEach(function(k){ var o=document.createElement('option'); o.value=k; dl.appendChild(o); });
    mtA.value = teamKeys.indexOf('Alabama')>=0 ? 'Alabama' : teamKeys[0]; mtB.value = teamKeys.filter(function(k){return k!==mtA.value;})[0]; })();
  function mtFmt(m, v){ if(v===null||v===undefined||isNaN(v)) return '\\u2014';
    if(m==='avgDist3rd'||m==='lineYards'||m==='ydsPerDb'||m==='ppo') return v.toFixed(2);
    if(MT_PCT[m]) return v.toFixed(1)+'%'; return (v>0?'+':'')+v.toFixed(3); }
  function mtEdge(offPct, defPct, offName, defName, offCls, defCls){
    if(offPct==null||defPct==null) return '<td class=\"edge mt-even\">\\u2014</td>';
    var d = offPct - defPct, a = Math.abs(d), who = d>0 ? offName : defName, cls = d>0 ? offCls : defCls;
    if(a < 20) return '<td class=\"edge mt-even\"><span class=\"mt-bar\" style=\"width:'+Math.max(4,a)+'px;background:var(--line)\"></span>Even</td>';
    return '<td class=\"edge '+cls+'\"><span class=\"mt-bar\" style=\"width:'+a+'px;background:currentColor;opacity:.55\"></span>'+(a>=40?'Big edge: ':'Edge: ')+who+' ('+(d>0?'+':'\\u2212')+a.toFixed(0)+')</td>';
  }
  function mtSide(off, def, offName, defName, offCls, defCls){
    var head = '<tr><th>Stat</th><th>'+offName+' offense</th><th>'+defName+' defense</th><th>Edge</th></tr>';
    var rows = '', cnt = {o:0, d:0, e:0};
    MT_GROUPS.forEach(function(g){
      var ms = g[1].filter(function(m){ return off.radar.offRaw[m]!==undefined && def.radar.defRaw[m]!==undefined; });
      if(!ms.length) return;
      rows += '<tr><td class=\"grp\" colspan=\"4\">'+g[0]+'</td></tr>';
      ms.forEach(function(m){
        var op = off.radar.off[m], dp = def.radar.def[m];
        if(op!=null && dp!=null){ var d=op-dp; if(d>=20) cnt.o++; else if(d<=-20) cnt.d++; else cnt.e++; }
        rows += '<tr><td>'+(RADAR_LABELS[m]||m)+'</td>'
          + '<td class=\"num\">'+mtFmt(m, off.radar.offRaw[m])+'<span class=\"pc\">'+(op==null?'':Math.round(op)+'p')+'</span></td>'
          + '<td class=\"num\">'+mtFmt(m, def.radar.defRaw[m])+'<span class=\"pc\">'+(dp==null?'':Math.round(dp)+'p')+'</span></td>'
          + mtEdge(op, dp, offName, defName, offCls, defCls) + '</tr>';
      });
    });
    return { html: '<div class=\"mt-wrap\"><table class=\"mt\"><thead>'+head+'</thead><tbody>'+rows+'</tbody></table></div>', cnt: cnt };
  }
  function mtRankRow(label, aName, aRank, bName, bRank, n, aCls, bCls){
    if(aRank==null||bRank==null) return '';
    var pa = 100*(1-(aRank-1)/(n-1)), pb = 100*(1-(bRank-1)/(n-1));
    return '<tr><td>'+label+'</td><td class=\"num\">#'+aRank+'</td><td class=\"num\">#'+bRank+'</td>'+mtEdge(pa, pb, aName, bName, aCls, bCls)+'</tr>';
  }
  function renderMatchup(){
    var a = mtA.value, b = mtB.value, out = document.getElementById('mtOut');
    if(!teams[a] || !teams[b] || a===b){ out.innerHTML = '<div class=\"mt-card\">Pick two different teams.</div>'; return; }
    var A = teams[a], B = teams[b], n = teamKeys.length, R = DATA.teamsAdj;
    document.getElementById('mtNote').textContent = (adjModeLabel()) + ' Percentiles: higher = better for that unit (offense or defense). Edge = gap in percentile points; 20+ = edge, 40+ = big edge.';
    var html = '';
    if(R && R[a] && R[b] && R[a].adjRank && R[b].adjRank){
      var ra = R[a].adjRank, rb = R[b].adjRank;
      html += '<div class=\"mt-card\"><h3>Unit vs unit (opponent-adjusted ranks)</h3><div class=\"mt-sub\">Lower rank = better. Schedule: '+a+' #'+(R[a].sos?R[a].sos.rank:'?')+', '+b+' #'+(R[b].sos?R[b].sos.rank:'?')+' (1 = hardest).</div>'
        + '<div class=\"mt-wrap\"><table class=\"mt\"><thead><tr><th>Matchup</th><th>Attacking</th><th>Defending</th><th>Edge</th></tr></thead><tbody>'
        + mtRankRow(a+' offense vs '+b+' defense', a, ra.off, b, rb.def, n, 'mt-a', 'mt-b')
        + mtRankRow(a+' rush O vs '+b+' rush D', a, ra.rushOff, b, rb.rushDef, n, 'mt-a', 'mt-b')
        + mtRankRow(a+' pass O vs '+b+' pass D', a, ra.passOff, b, rb.passDef, n, 'mt-a', 'mt-b')
        + mtRankRow(b+' offense vs '+a+' defense', b, rb.off, a, ra.def, n, 'mt-b', 'mt-a')
        + mtRankRow(b+' rush O vs '+a+' rush D', b, rb.rushOff, a, ra.rushDef, n, 'mt-b', 'mt-a')
        + mtRankRow(b+' pass O vs '+a+' pass D', b, rb.passOff, a, ra.passDef, n, 'mt-b', 'mt-a')
        + '</tbody></table></div></div>';
    }
    var s1 = mtSide(A, B, a, b, 'mt-a', 'mt-b'), s2 = mtSide(B, A, b, a, 'mt-b', 'mt-a');
    html += '<div class=\"mt-card\"><h3><span class=\"mt-a\">'+a+'</span> offense vs <span class=\"mt-b\">'+b+'</span> defense</h3>'
      + '<div class=\"mt-sub\">Edges: '+a+' offense '+s1.cnt.o+' \\u00b7 '+b+' defense '+s1.cnt.d+' \\u00b7 even '+s1.cnt.e+'</div>'+s1.html+'</div>';
    html += '<div class=\"mt-card\"><h3><span class=\"mt-b\">'+b+'</span> offense vs <span class=\"mt-a\">'+a+'</span> defense</h3>'
      + '<div class=\"mt-sub\">Edges: '+b+' offense '+s2.cnt.o+' \\u00b7 '+a+' defense '+s2.cnt.d+' \\u00b7 even '+s2.cnt.e+'</div>'+s2.html+'</div>';
    out.innerHTML = html;
  }
  function adjModeLabel(){ return (typeof adjMode!=='undefined' && adjMode) ? 'Stats: opponent-adjusted.' : 'Stats: raw (switch to Opponent-adjusted at the top for schedule-adjusted numbers).'; }
  mtA.addEventListener('change', renderMatchup); mtB.addEventListener('change', renderMatchup);
  mtA.addEventListener('input', function(){ if(teams[mtA.value]) renderMatchup(); });
  mtB.addEventListener('input', function(){ if(teams[mtB.value]) renderMatchup(); });
  document.getElementById('mtSwap').addEventListener('click', function(){ var t=mtA.value; mtA.value=mtB.value; mtB.value=t; renderMatchup(); });
"""
for p in sys.argv[1:]:
    s = open(p).read()
    if 'id="tabBtnMatchup"' in s: print(p, 'already patched'); continue
    assert 'id="tabBtnSchedule"' in s, (p, 'run patch_schedule_ui.py first')
    m = re.search(r'(<button class="tab-btn" id="tabBtnSchedule"[^>]*>Schedule</button>)', s); assert m, (p, 'tab anchor')
    s = s[:m.end()] + '\n      ' + BTN + s[m.end():]
    a = '<div data-view="leaderboard">'; assert s.count(a) == 1, (p, 'view anchor')
    s = s.replace(a, VIEW + a)
    a = "document.getElementById('tabBtnSchedule')];"; assert s.count(a) == 1, (p, 'tabBtns anchor')
    s = s.replace(a, "document.getElementById('tabBtnSchedule'), document.getElementById('tabBtnMatchup')];")
    a = "schedule: document.querySelector('[data-view=\"schedule\"]') };"; assert s.count(a) == 1, (p, 'views anchor')
    s = s.replace(a, "schedule: document.querySelector('[data-view=\"schedule\"]'), matchup: document.querySelector('[data-view=\"matchup\"]') };")
    a = "if(target==='schedule') renderSchedule();"; assert s.count(a) == 1, (p, 'setTab anchor')
    s = s.replace(a, a + " if(target==='matchup') renderMatchup();")
    # re-render when the Raw / Adjusted switch flips while the Matchup tab is open
    a = "    if(views.leaderboard.classList.contains('active')) renderLeaderboard();\n  }"
    assert s.count(a) == 1, (p, 'setMode anchor')
    s = s.replace(a, "    if(views.leaderboard.classList.contains('active')) renderLeaderboard();\n    if(views.matchup && views.matchup.classList.contains('active')) renderMatchup();\n  }")
    a = "\n  confFilter.value = 'all';"; assert s.count(a) == 1, (p, 'init anchor')
    s = s.replace(a, JS + a)
    open(p, 'w').write(s); print(p, 'patched')
