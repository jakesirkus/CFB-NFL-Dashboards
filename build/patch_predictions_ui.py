"""Predictions tab (CFB): the user's power-rating model line vs the current market for the upcoming week; edge = market - model.
Data: DATA.meta.predictions (add_predictions.py). Tab hides itself when there is no predictions block.
Run after patch_lines_ui.py. Idempotent.  usage: patch_predictions_ui.py PAGE.html [PAGE.html ...]"""
import sys, re
BTN = '<button class="tab-btn" id="tabBtnPreds" data-target="preds" role="tab" aria-selected="false">Predictions</button>'
VIEW = '''<div data-view="preds">
    <div class="lb-controls">
      <div class="control">
        <label for="prMin">Show</label>
        <select id="prMin"><option value="0">All games</option><option value="1">Edge 1+ pts</option><option value="2">Edge 2+ pts</option>
          <option value="3" selected>Edge 3+ pts (value)</option><option value="5">Edge 5+ pts</option></select>
      </div>
      <div class="control">
        <label for="prConf">Conference</label>
        <select id="prConf"></select>
      </div>
      <div class="control">
        <label for="prSearch">Search</label>
        <input id="prSearch" placeholder="Filter by team name…" autocomplete="off">
      </div>
    </div>
    <div class="scope-note" id="prNote" style="max-width:none"></div>
    <div class="lb-table-wrap">
      <table class="lb" id="prTable">
        <thead><tr id="prHead"></tr></thead>
        <tbody id="prBody"></tbody>
      </table>
    </div>
  </div>

  '''
CSS = '''
  .pr-edge{ font-weight:700; }
  .pr-edge.v3{ color:var(--warning); }
  .pr-edge.v5{ background:color-mix(in srgb, var(--warning) 22%, transparent); color:var(--ink); border-radius:6px; padding:2px 6px; }
  .pr-sub{ display:block; font-size:11px; color:var(--ink-muted); font-weight:400; }
  .pr-pick{ font-weight:700; white-space:nowrap; }
  .pr-n{ font-size:10px; font-weight:700; letter-spacing:0.06em; color:var(--ink-muted); border:1px solid var(--line-strong); border-radius:4px; padding:0 4px; margin-left:4px; }
  #prTable td{ vertical-align:middle; }
  .pr-mv{ display:block; font-size:10px; font-weight:700; letter-spacing:0.03em; }
  .pr-mv.toward{ color:var(--good); } .pr-mv.away{ color:var(--critical); }
  #prTable th:nth-child(2), #prTable td:nth-child(2), #prTable th:nth-child(8), #prTable td:nth-child(8){ text-align:left; }
'''
JS = r'''
  // ---------- Predictions tab ----------
  var PR = DATA.meta && DATA.meta.predictions;
  var prMin = document.getElementById('prMin'), prConf = document.getElementById('prConf'), prSearch = document.getElementById('prSearch');
  var prSort = { key:'absEdge', dir:-1 };
  function prNum(s){ return Math.abs(s).toFixed(1).replace(/\.0$/,''); }
  function prLine(team, s){ if(s===null||s===undefined) return '—'; if(Math.abs(s)<0.05) return 'Pick’em'; return team+' '+(s>0?'+':'−')+prNum(s); }
  function prFav(g, s){ return s<=0 ? prLine(g.home, s) : prLine(g.away, -s); }       // home-perspective spread -> "Fav -x"
  function prKick(g){ var d = new Date(g.start); if(isNaN(d)) return ''; var day = d.toLocaleDateString('en-US',{weekday:'short', month:'numeric', day:'numeric', timeZone:'America/New_York'});
    return g.tbd ? day+' · TBD' : day+' · '+d.toLocaleTimeString('en-US',{hour:'numeric', minute:'2-digit', timeZone:'America/New_York'}); }
  function prMove(g){                     // line movement since the open, and whether it moved toward the model's number
    if(g.market===null || g.marketOpen===null) return null;
    var mv = g.market - g.marketOpen; if(Math.abs(mv) < 0.25) return { pts:0, team:null, rel:'none' };
    var team = mv < 0 ? g.home : g.away;                       // spread fell -> money on the home side
    var rel = Math.abs(g.market - g.model) < Math.abs(g.marketOpen - g.model) - 0.01 ? 'toward' : 'away';
    return { pts:Math.abs(mv), team:team, rel:rel };
  }
  var PR_COLS = [
    { key:'start', label:'Kickoff (ET)', get:function(g){ return g.start; } },
    { key:'match', label:'Matchup', get:function(g){ return g.away+' @ '+g.home; } },
    { key:'model', label:'Model line', get:function(g){ return g.model; }, title:'Your power ratings: home rating − away rating + home-field advantage (0 at neutral sites)' },
    { key:'open', label:'Weekly opener', get:function(g){ return g.marketOpen===null ? 99 : g.marketOpen; }, title:'This week’s opening spread: DraftKings line captured Sunday after last week’s games (Bovada’s opener if DraftKings hadn’t posted yet)' },
    { key:'market', label:'Current line', get:function(g){ return g.market===null ? 99 : g.market; }, title:'DraftKings current spread (other books underneath)' },
    { key:'move', label:'Line move', get:function(g){ var m = prMove(g); return m ? (m.rel==='toward' ? m.pts : -m.pts) : -99; }, title:'Points the line has moved since it opened, and whether it moved toward your model’s number or away from it' },
    { key:'absEdge', label:'Edge (pts)', get:function(g){ return g.edge===null ? -1 : Math.abs(g.edge); }, title:'Current spread − model spread (the opener’s edge underneath)' },
    { key:'pick', label:'Model side', get:function(g){ return g.edge===null ? '' : (g.edge>0 ? g.home : g.away); } },
    { key:'win', label:'Model win %', get:function(g){ return Math.max(g.homeWin, 100-g.homeWin); }, title:'Normal distribution of the model margin, SD '+(PR&&PR.model?PR.model.sd:14)+' pts' },
    { key:'ratings', label:'Ratings (away / home + HFA)', get:function(g){ return g.homeRating-g.awayRating; } }
  ];
  function renderPreds(){
    if(!PR) return;
    var head = document.getElementById('prHead'); head.innerHTML='';
    PR_COLS.forEach(function(c){ var th=document.createElement('th'); th.textContent=c.label+(prSort.key===c.key?(prSort.dir>0?' ▲':' ▼'):''); if(c.title) th.title=c.title;
      th.style.cursor='pointer'; th.addEventListener('click', function(){ if(prSort.key===c.key) prSort.dir*=-1; else prSort={key:c.key, dir:(c.key==='start'||c.key==='match')?1:-1}; renderPreds(); }); head.appendChild(th); });
    var min = +prMin.value, conf = prConf.value, q = (prSearch.value||'').trim().toLowerCase();
    var col = PR_COLS.filter(function(c){ return c.key===prSort.key; })[0];
    var rows = PR.games.filter(function(g){
      if(min>0 && (g.edge===null || Math.abs(g.edge)<min)) return false;
      if(conf!=='all' && g.homeConf!==conf && g.awayConf!==conf) return false;
      if(q && g.home.toLowerCase().indexOf(q)<0 && g.away.toLowerCase().indexOf(q)<0) return false;
      return true; }).sort(function(x,y){ var a=col.get(x), b=col.get(y); return (a<b?-1:(a>b?1:0))*prSort.dir; });
    var body = document.getElementById('prBody');
    if(!rows.length){ body.innerHTML = '<tr><td colspan="'+PR_COLS.length+'" style="text-align:center;color:var(--ink-muted);padding:18px">No games match these filters.</td></tr>'; }
    else body.innerHTML = rows.map(function(g){
      var e = g.edge, ae = e===null ? null : Math.abs(e), cls = ae===null ? '' : (ae>=5 ? ' v5' : (ae>=3 ? ' v3' : ''));
      var side = e===null ? '—' : (e>0 ? prLine(g.home, g.market) : prLine(g.away, -g.market));
      var oth = (g.others||[]).map(function(o){ return o.book+' '+prFav(g, o.spread); }).join(' · ');
      var m = prMove(g), mv = !m ? '<span style="color:var(--ink-muted)">—</span>' : (m.rel==='none' ? '<span style="color:var(--ink-muted)">no move</span>'
          : prNum(m.pts)+' → '+m.team+'<span class="pr-mv '+m.rel+'">'+(m.rel==='toward'?'toward model':'away from model')+'</span>');
      var oe = (g.openEdge===null||g.openEdge===undefined) ? '' : '<span class="pr-sub">open '+Math.abs(g.openEdge).toFixed(1)+'</span>';
      var fw = g.homeWin>=50 ? g.home : g.away, fp = Math.max(g.homeWin, 100-g.homeWin);
      var rt = function(r, ok){ return ok ? (r>0?'+':'')+r.toFixed(1) : 'FCS '+r.toFixed(0); };
      return '<tr>'
        + '<td style="white-space:nowrap">'+prKick(g)+'</td>'
        + '<td><span class="team-name">'+g.away+'</span> @ <span class="team-name">'+g.home+'</span>'+(g.neutral?'<span class="pr-n" title="Neutral site">N</span>':'')+'</td>'
        + '<td class="num">'+prFav(g, g.model)+'</td>'
        + '<td class="num">'+(g.marketOpen===null?'<span style="color:var(--ink-muted)">—</span>':prFav(g, g.marketOpen))+(g.openSource && g.openSource.indexOf('Bovada')===0?'<span class="pr-sub">Bovada open</span>':'')+'</td>'
        + '<td class="num">'+(g.market===null?'<span style="color:var(--ink-muted)">no line yet</span>':prFav(g, g.market))+(oth?'<span class="pr-sub">'+oth+'</span>':'')+'</td>'
        + '<td class="num" style="white-space:nowrap">'+mv+'</td>'
        + '<td class="num"><span class="pr-edge'+cls+'">'+(ae===null?'—':ae.toFixed(1))+'</span>'+oe+'</td>'
        + '<td class="pr-pick">'+side+'</td>'
        + '<td class="num">'+fp.toFixed(0)+'%<span class="pr-sub">'+fw+'</span></td>'
        + '<td class="num">'+rt(g.awayRating, g.awayRated)+' / '+rt(g.homeRating, g.homeRated)+(g.neutral?'':' <span class="pr-sub">+'+g.hfa.toFixed(1)+' HFA</span>')+'</td>'
        + '</tr>'; }).join('');
    var nAll = PR.games.length, nLine = PR.games.filter(function(g){ return g.market!==null; }).length;
    var nTow = PR.games.filter(function(g){ var m = prMove(g); return m && m.rel==='toward'; }).length, nAway = PR.games.filter(function(g){ var m = prMove(g); return m && m.rel==='away'; }).length;
    var upd = new Date(PR.updated); var updTxt = isNaN(upd) ? PR.updated : upd.toLocaleString('en-US',{month:'short', day:'numeric', hour:'numeric', minute:'2-digit', timeZone:'America/New_York'})+' ET';
    document.getElementById('prNote').innerHTML = '<b>Week '+PR.week+'</b> · '+rows.length+' of '+nAll+' games shown ('+nLine+' with a market line). '
      + 'Model line = power ratings through Week '+PR.ratingsThroughWeek+': home rating − away rating + the home team’s home-field advantage (0 at neutral sites; FCS teams rated '+PR.model.fcsRating+'). '
      + 'Current line = '+PR.source+', updated '+updTxt+'. Weekly opener = the DraftKings line captured '+(PR.openSnapshot ? new Date(PR.openSnapshot).toLocaleString('en-US',{weekday:'short', month:'short', day:'numeric', hour:'numeric', minute:'2-digit', timeZone:'America/New_York'})+' ET' : 'Sunday')+' (Bovada’s opener where DraftKings hadn’t posted). Since the open, '+nTow+' lines have moved <span class="pr-mv toward" style="display:inline;margin-left:0">toward</span> your model and '+nAway+' <span class="pr-mv away" style="display:inline;margin-left:0">away</span> from it. '
      + 'Edge = points between the current spread and the model spread (opener’s edge underneath); <span class="pr-edge v3">3+</span> and <span class="pr-edge v5">5+</span> highlight value.';
  }
  if(PR){
    var prC = {}; PR.games.forEach(function(g){ if(g.homeConf) prC[g.homeConf]=1; if(g.awayConf) prC[g.awayConf]=1; });
    prConf.innerHTML = '<option value="all">All conferences</option>' + Object.keys(prC).sort().map(function(c){ return '<option value="'+c+'">'+c+'</option>'; }).join('');
    prMin.addEventListener('change', renderPreds); prConf.addEventListener('change', renderPreds); prSearch.addEventListener('input', renderPreds);
  } else { document.getElementById('tabBtnPreds').style.display='none'; }
'''
for p in sys.argv[1:]:
    s = open(p).read()
    if 'id="tabBtnPreds"' in s:
        if 'g.openSource' in s: print(p, 'already patched'); continue
        a0 = s.index('\n  // ---------- Predictions tab ----------'); b0 = s.index("\n  confFilter.value = 'all';", a0)
        s = s[:a0] + JS + s[b0:]
        c0 = s.index('\n  .pr-edge{'); c1 = s.index('text-align:left; }\n', c0) + len('text-align:left; }\n')
        s = s[:c0] + CSS + s[c1:]
        open(p, 'w').write(s); print(p, 'upgraded'); continue
    assert 'id="tabBtnLines"' in s, (p, 'run patch_lines_ui.py first')
    m = re.search(r'(<button class="tab-btn" id="tabBtnLines"[^>]*>Lines</button>)', s); assert m, (p, 'tab anchor')
    s = s[:m.end()] + '\n      ' + BTN + s[m.end():]
    a = '<div data-view="leaderboard">'; assert s.count(a) == 1, (p, 'view anchor'); s = s.replace(a, VIEW + a)
    a = "document.getElementById('tabBtnLines')];"; assert s.count(a) == 1, (p, 'tabBtns anchor')
    s = s.replace(a, "document.getElementById('tabBtnLines'), document.getElementById('tabBtnPreds')];")
    a = "lines: document.querySelector('[data-view=\"lines\"]') };"; assert s.count(a) == 1, (p, 'views anchor')
    s = s.replace(a, "lines: document.querySelector('[data-view=\"lines\"]'), preds: document.querySelector('[data-view=\"preds\"]') };")
    a = "if(target==='lines') renderLines();"; assert s.count(a) == 1, (p, 'setTab anchor')
    s = s.replace(a, a + " if(target==='preds') renderPreds();")
    a = "\n  confFilter.value = 'all';"; assert s.count(a) == 1, (p, 'init anchor')
    s = s.replace(a, JS + a)
    a = s.index('</style>', s.index('.bs-section-title{')); s = s[:a] + CSS + s[a:]
    open(p, 'w').write(s); print(p, 'patched')
