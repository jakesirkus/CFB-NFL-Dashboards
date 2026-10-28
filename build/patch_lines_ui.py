"""Offensive / defensive line UI (reads DATA.teamsAdj[*].adjRank ol/dl/... and .lineVals from opp_adjust.py):
  * 'Lines' tab: OL or DL table - overall rank (half team play-by-play, half PFF player composite), the team-stats rank,
    the PFF rank, pass pro / run block (pass rush / run D) ranks, and every stat with its rank; values follow the
    Raw / Opponent-adjusted switch, ranks of the composites are always adjusted.
  * third team-header chip: OL #, DL # (pass pro / run block / pass rush / run D in the tooltip)
  * Rankings tab: OL and DL columns
  * Matchup tab: OL vs DL rank rows + a 'Trenches' card (each OL stat vs the other team's DL, both ways)
Run after patch_matchup_ui.py. Idempotent. usage: patch_lines_ui.py PAGE.html [PAGE.html ...]"""
import sys, re
BTN = '<button class="tab-btn" id="tabBtnLines" data-target="lines" role="tab" aria-selected="false">Lines</button>'
VIEW = '''<div data-view="lines">
    <div class="lb-controls">
      <div class="control">
        <label for="lnUnit">Unit</label>
        <select id="lnUnit"><option value="ol">Offensive line</option><option value="dl">Defensive line</option></select>
      </div>
      <div class="control">
        <label for="lnConfFilter">Conference</label>
        <select id="lnConfFilter"></select>
      </div>
      <div class="control">
        <label for="lnSearch">Search</label>
        <input id="lnSearch" placeholder="Filter by team name…" autocomplete="off">
      </div>
    </div>
    <div class="scope-note" id="lnNote" style="max-width:none"></div>
    <div class="lb-table-wrap">
      <table class="lb" id="lnTable">
        <thead><tr id="lnHead"></tr></thead>
        <tbody id="lnBody"></tbody>
      </table>
    </div>
  </div>

  '''
JS = """
  // ---------- Lines tab (OL / DL: team play-by-play + PFF player composites) ----------
  var LN_LABEL = { sackPct:'Sack %', lineYards:'Line Yds', stuffPct:'Stuff %', opportunityPct:'Opp %', powerPct:'Power %',
    olPbGrade:'PB Grade', olPbe:'PBE', olPressPct:'Press %', olRbGrade:'RB Grade',
    dlPrGrade:'PR Grade', dlPrwr:'PR Win %', dlPressPct:'Press %', dlRdGrade:'RD Grade', dlStopPct:'Stop %' };
  var LN_TIP = { sackPct:'Sacks per dropback (OL: allowed; DL: generated)', lineYards:'Line yards per carry (OL: gained; DL: allowed)',
    stuffPct:'Runs stopped at or behind the line (OL: suffered; DL: made)', opportunityPct:'Runs gaining 4+ yards (OL: gained; DL: allowed)',
    powerPct:'3rd/4th-and-short run conversion rate (OL: converted; DL: allowed)',
    olPbGrade:'PFF pass-block grade, OL snap-weighted', olPbe:'PFF pass-blocking efficiency: 100 - (sacks + 0.75 x hits/hurries) per 100 OL pass-block snaps',
    olPressPct:'Pressures allowed by the OL per 100 OL pass-block snaps', olRbGrade:'PFF run-block grade, OL snap-weighted',
    dlPrGrade:'PFF pass-rush grade, DL/edge snap-weighted', dlPrwr:'PFF pass-rush win rate (DL + edge)', dlPressPct:'Pressures per 100 DL/edge pass-rush snaps',
    dlRdGrade:'PFF run-defense grade, DL/edge snap-weighted', dlStopPct:'Run stops per run-stop opportunity (DL + edge)' };
  var LN_UNITS = {
    ol: { side:'o', ranks:[['ol','OL','Overall OL: half team play-by-play stats, half PFF player composite'],['olStats','Team Stats','Play-by-play: sack rate 40%, line yards 25%, stuff rate 15%, opportunity rate 12%, power 8%'],
          ['olPff','PFF','PFF OL players: pass-block grade 30%, PBE 20%, pressure rate 10%, run-block grade 40%'],['passPro','Pass Pro','Sack rate 50%, PB grade 20%, PBE 20%, pressure rate 10%'],['runBlock','Run Block','Line yards 20%, stuff 12%, opportunity 10%, power 8%, RB grade 50%']],
          stats:['sackPct','lineYards','stuffPct','opportunityPct','powerPct','olPbGrade','olPbe','olPressPct','olRbGrade'] },
    dl: { side:'d', ranks:[['dl','DL','Overall DL: half team play-by-play stats, half PFF player composite'],['dlStats','Team Stats','Play-by-play: sack rate 40%, line yards 25%, stuff rate 15%, opportunity rate 12%, power 8% (allowed/generated)'],
          ['dlPff','PFF','PFF DL/edge players: pass-rush grade 20%, win rate 20%, pressure rate 10%, run-defense grade 30%, stop rate 20%'],['passRush','Pass Rush','Sack rate 40%, PR grade 20%, win rate 25%, pressure rate 15%'],['runDef','Run D','Line yards 20%, stuff 12%, opportunity 10%, power 8%, RD grade 30%, stop rate 20%']],
          stats:['sackPct','lineYards','stuffPct','opportunityPct','powerPct','dlPrGrade','dlPrwr','dlPressPct','dlRdGrade','dlStopPct'] } };
  function lnLow(){ var o=(DATA.meta&&DATA.meta.oppAdj&&DATA.meta.oppAdj.lowBetterForOffense)||[]; var r={}; o.forEach(function(m){r[m]=1;}); return r; }
  function lnHighBetter(m, side){ var low=lnLow()[m]===1; return side==='o' ? !low : low; }
  function lnVal(t, m, side){ var A=DATA.teamsAdj; var e=A&&A[t]&&A[t].lineVals&&A[t].lineVals[m]; if(!e) return null;
    var k = side + ((typeof adjMode!=='undefined' && adjMode) ? 'a' : ''); return e[k]==null ? null : e[k]; }
  function lnFmt(m, v){ if(v===null||v===undefined||isNaN(v)) return '\\u2014'; if(m==='lineYards') return v.toFixed(2);
    if(/Grade$|Pbe$/.test(m)) return v.toFixed(1); return v.toFixed(1)+'%'; }
  function lnRanks(m, side){ var hb=lnHighBetter(m, side), vals={}, arr=[];
    teamKeys.forEach(function(t){ var v=lnVal(t,m,side); if(v!==null){ vals[t]=v; arr.push(v); } });
    var r={}; Object.keys(vals).forEach(function(t){ var v=vals[t]; r[t]=1+arr.filter(function(x){ return hb ? x>v+1e-9 : x<v-1e-9; }).length; }); return { rank:r, n:arr.length }; }
  var lnSort = { key:'ol', dir:1 };
  var lnConf = document.getElementById('lnConfFilter'), lnSearch = document.getElementById('lnSearch'), lnUnit = document.getElementById('lnUnit');
  (function(){ var o=document.createElement('option'); o.value='all'; o.textContent='All conferences'; lnConf.appendChild(o);
    confs.forEach(function(c){ var x=document.createElement('option'); x.value=c; x.textContent=c; lnConf.appendChild(x); }); lnConf.value='all'; })();
  function renderLines(){
    var A = DATA.teamsAdj; if(!A) return;
    var U = LN_UNITS[lnUnit.value], side = U.side;
    if(!U.ranks.some(function(r){ return r[0]===lnSort.key; }) && U.stats.indexOf(lnSort.key)<0){ lnSort = { key:U.ranks[0][0], dir:1 }; }
    var ls = (DATA.meta && DATA.meta.lineStats) || {};
    document.getElementById('lnNote').textContent = (lnUnit.value==='ol' ? 'Offensive line' : 'Defensive line') + ' rankings, 1 = best (hover a column for its recipe). '
      + 'Rank columns are opponent-adjusted; stat columns follow the Raw / Opponent-adjusted switch ('+((typeof adjMode!=='undefined'&&adjMode)?'adjusted':'raw')+' now), small number = rank. '
      + 'Team Stats = play-by-play; PFF = PFF player grades/charting for '+(lnUnit.value==='ol'?'tackles, guards and centers':'interior DL and edge rushers')+', snap-weighted per game.'
      + (ls.covered!=null ? ' PFF data on '+ls.covered+' of '+ls.teamGames+' team-games.' : '');
    var cols = [{key:'pos',label:'#'},{key:'team',label:'Team'},{key:'conf',label:'Conf'},{key:'record',label:'W-L'}]
      .concat(U.ranks.map(function(r){ return {key:r[0], label:r[1], tip:r[2], type:'rank'}; }))
      .concat(U.stats.map(function(m){ return {key:m, label:LN_LABEL[m], tip:LN_TIP[m], type:'stat'}; }));
    var SR = {}; U.stats.forEach(function(m){ SR[m] = lnRanks(m, side); });
    var tr = document.getElementById('lnHead'); tr.innerHTML='';
    cols.forEach(function(col){
      var th=document.createElement('th'); th.textContent=col.label; if(col.tip) th.title=col.tip;
      if(col.key===lnSort.key){ th.classList.add('sorted'); var ar=document.createElement('span'); ar.className='arrow'; ar.textContent=lnSort.dir===1?'\\u25B2':'\\u25BC'; th.appendChild(ar); }
      if(col.type){ th.addEventListener('click', function(){ if(lnSort.key===col.key) lnSort.dir*=-1; else lnSort={key:col.key, dir:1}; renderLines(); }); }
      tr.appendChild(th); });
    var q=(lnSearch.value||'').toLowerCase(), cf=lnConf.value;
    var rows = teamKeys.filter(function(k){ return A[k] && A[k].adjRank && A[k].adjRank[U.ranks[0][0]]!=null && (cf==='all' || DATA.teams[k].confLabel===cf) && (!q || k.toLowerCase().indexOf(q)>-1); })
      .map(function(k){ var t=DATA.teams[k], row={team:k, conf:t.confLabel, record:t.wins+'-'+t.losses, _v:{}};
        U.ranks.forEach(function(r){ row[r[0]] = A[k].adjRank[r[0]]; });
        U.stats.forEach(function(m){ row[m] = SR[m].rank[k]!=null ? SR[m].rank[k] : null; row._v[m] = lnVal(k, m, side); });
        return row; });
    rows.sort(function(a,b){ var av=a[lnSort.key], bv=b[lnSort.key]; av=(av==null)?Infinity*lnSort.dir:av; bv=(bv==null)?Infinity*lnSort.dir:bv; return lnSort.dir*(av-bv); });
    var body=document.getElementById('lnBody'); body.innerHTML='';
    rows.forEach(function(row,i){ var r=document.createElement('tr');
      cols.forEach(function(col){ var td=document.createElement('td'), v=row[col.key];
        if(col.key==='pos'){ td.className='rk'; td.textContent=i+1; }
        else if(!col.type){ td.textContent=v; }
        else if(col.type==='rank'){ td.className='num'; td.textContent=v==null?'\\u2014':v; }
        else { td.className='num'; td.innerHTML = lnFmt(col.key, row._v[col.key]) + (v==null?'':' <span style=\"color:var(--ink-muted);font-size:11px\">'+v+'</span>'); }
        r.appendChild(td); });
      body.appendChild(r); });
  }
  lnUnit.addEventListener('change', function(){ lnSort = { key: LN_UNITS[lnUnit.value].ranks[0][0], dir:1 }; renderLines(); });
  lnConf.addEventListener('change', renderLines);
  lnSearch.addEventListener('input', renderLines);
  if(!DATA.teamsAdj || !DATA.teamsAdj[teamKeys[0]] || !DATA.teamsAdj[teamKeys[0]].lineVals){ document.getElementById('tabBtnLines').style.display='none'; }
"""
CHIP_HTML = '\n        <span class="chip" id="adjLineChip" hidden></span>'
CHIP_JS = """
    var alc = document.getElementById('adjLineChip');
    if(alc){ if(t.adjRank && t.adjRank.ol){ alc.hidden = false;
        alc.textContent = 'OL #'+t.adjRank.ol+' \\u00b7 DL #'+t.adjRank.dl;
        alc.title = 'Opponent-adjusted line ranks (half team play-by-play, half PFF player composite). OL: team stats #'+t.adjRank.olStats+', PFF #'+t.adjRank.olPff+', pass pro #'+t.adjRank.passPro+', run block #'+t.adjRank.runBlock
          +'. DL: team stats #'+t.adjRank.dlStats+', PFF #'+t.adjRank.dlPff+', pass rush #'+t.adjRank.passRush+', run D #'+t.adjRank.runDef+'. Full table: Lines tab.';
      } else { alc.hidden = true; } }"""
MT_ROWS_A = """
        + mtRankRow(a+' OL vs '+b+' DL', a, ra.ol, b, rb.dl, n, 'mt-a', 'mt-b')
        + mtRankRow(a+' pass pro vs '+b+' pass rush', a, ra.passPro, b, rb.passRush, n, 'mt-a', 'mt-b')
        + mtRankRow(a+' run block vs '+b+' run D', a, ra.runBlock, b, rb.runDef, n, 'mt-a', 'mt-b')"""
MT_ROWS_B = """
        + mtRankRow(b+' OL vs '+a+' DL', b, rb.ol, a, ra.dl, n, 'mt-b', 'mt-a')
        + mtRankRow(b+' pass pro vs '+a+' pass rush', b, rb.passPro, a, ra.passRush, n, 'mt-b', 'mt-a')
        + mtRankRow(b+' run block vs '+a+' run D', b, rb.runBlock, a, ra.runDef, n, 'mt-b', 'mt-a')"""
MT_TRENCH = """
  function mtTrench(o, d, oCls, dCls){           // o's OL stats vs d's DL stats, percentiles across all teams
    var pairs = [['sackPct','sackPct'],['lineYards','lineYards'],['stuffPct','stuffPct'],['opportunityPct','opportunityPct'],['powerPct','powerPct'],
                 ['olPbGrade','dlPrGrade','Pass block grade vs pass rush grade'],['olPressPct','dlPressPct','Pressure rate allowed vs generated'],['olRbGrade','dlRdGrade','Run block grade vs run defense grade']];
    var rows='';
    pairs.forEach(function(p){ var ro=lnRanks(p[0],'o'), rd=lnRanks(p[1],'d'); var vo=lnVal(o,p[0],'o'), vd=lnVal(d,p[1],'d');
      if(vo===null||vd===null) return;
      var po = 100*(1-(ro.rank[o]-1)/Math.max(1,ro.n-1)), pd = 100*(1-(rd.rank[d]-1)/Math.max(1,rd.n-1));
      rows += '<tr><td>'+(p[2]||LN_LABEL[p[0]])+'</td><td class=\"num\">'+lnFmt(p[0],vo)+'<span class=\"pc\">#'+ro.rank[o]+'</span></td><td class=\"num\">'+lnFmt(p[1],vd)+'<span class=\"pc\">#'+rd.rank[d]+'</span></td>'+mtEdge(po,pd,o,d,oCls,dCls)+'</tr>'; });
    if(!rows) return '';
    return '<div class=\"mt-card\"><h3>Trenches: <span class=\"'+oCls+'\">'+o+'</span> OL vs <span class=\"'+dCls+'\">'+d+'</span> DL</h3><div class=\"mt-sub\">Small number = rank among all teams (OL stats vs DL stats). Stats follow the Raw / Opponent-adjusted switch.</div>'
      + '<div class=\"mt-wrap\"><table class=\"mt\"><thead><tr><th>Stat</th><th>'+o+' OL</th><th>'+d+' DL</th><th>Edge</th></tr></thead><tbody>'+rows+'</tbody></table></div></div>';
  }"""
for p in sys.argv[1:]:
    s = open(p).read()
    if 'id="tabBtnLines"' in s: print(p, 'already patched'); continue
    assert 'id="tabBtnMatchup"' in s, (p, 'run patch_matchup_ui.py first')
    # --- tab ---
    m = re.search(r'(<button class="tab-btn" id="tabBtnMatchup"[^>]*>Matchup</button>)', s); assert m, (p, 'tab anchor')
    s = s[:m.end()] + '\n      ' + BTN + s[m.end():]
    a = '<div data-view="leaderboard">'; assert s.count(a) == 1, (p, 'view anchor'); s = s.replace(a, VIEW + a)
    a = "document.getElementById('tabBtnMatchup')];"; assert s.count(a) == 1, (p, 'tabBtns anchor')
    s = s.replace(a, "document.getElementById('tabBtnMatchup'), document.getElementById('tabBtnLines')];")
    a = "matchup: document.querySelector('[data-view=\"matchup\"]') };"; assert s.count(a) == 1, (p, 'views anchor')
    s = s.replace(a, "matchup: document.querySelector('[data-view=\"matchup\"]'), lines: document.querySelector('[data-view=\"lines\"]') };")
    a = "if(target==='matchup') renderMatchup();"; assert s.count(a) == 1, (p, 'setTab anchor')
    s = s.replace(a, a + " if(target==='lines') renderLines();")
    a = "    if(views.matchup && views.matchup.classList.contains('active')) renderMatchup();\n"; assert s.count(a) == 1, (p, 'setMode anchor')
    s = s.replace(a, a + "    if(views.lines && views.lines.classList.contains('active')) renderLines();\n")
    a = "\n  confFilter.value = 'all';"; assert s.count(a) == 1, (p, 'init anchor')
    s = s.replace(a, JS + MT_TRENCH + a)
    # --- header chip ---
    a = '<span class="chip" id="adjUnitChip" hidden></span>'; assert s.count(a) == 1, (p, 'unit chip html')
    s = s.replace(a, a + CHIP_HTML)
    a = "      } else { auc.hidden = true; } }"; assert s.count(a) == 1, (p, 'unit chip js')
    s = s.replace(a, a + CHIP_JS)
    # --- rankings tab: OL / DL columns ---
    a = "{ key:'sos', label:'Schedule', type:'rank' }"; assert s.count(a) == 1, (p, 'rk cols')
    s = s.replace(a, "{ key:'ol', label:'OL', type:'rank' }, { key:'dl', label:'DL', type:'rank' },\n    " + a)
    a = "rushDef:r.rushDef, passDef:r.passDef,"; assert s.count(a) == 1, (p, 'rk row')
    s = s.replace(a, a + " ol:r.ol, dl:r.dl,")
    a = "sos:'Average opponent power rating over the games used"; assert s.count(a) == 1, (p, 'rk tips')
    s = s.replace(a, "ol:'Offensive line: half team play-by-play (sack rate, line yards, stuff/opportunity/power), half PFF OL grades (see Lines tab)', dl:'Defensive line: same, for the DL/edge', " + a)
    # --- matchup: OL vs DL rank rows + trenches cards ---
    a = "        + mtRankRow(a+' pass O vs '+b+' pass D', a, ra.passOff, b, rb.passDef, n, 'mt-a', 'mt-b')"; assert s.count(a) == 1, (p, 'mt rows a')
    s = s.replace(a, a + MT_ROWS_A)
    a = "        + mtRankRow(b+' pass O vs '+a+' pass D', b, rb.passOff, a, ra.passDef, n, 'mt-b', 'mt-a')"; assert s.count(a) == 1, (p, 'mt rows b')
    s = s.replace(a, a + MT_ROWS_B)
    a = "    out.innerHTML = html;\n  }"; assert s.count(a) == 1, (p, 'mt out')
    s = s.replace(a, "    if(typeof mtTrench==='function'){ html += mtTrench(a, b, 'mt-a', 'mt-b') + mtTrench(b, a, 'mt-b', 'mt-a'); }\n" + a)
    open(p, 'w').write(s); print(p, 'patched')
