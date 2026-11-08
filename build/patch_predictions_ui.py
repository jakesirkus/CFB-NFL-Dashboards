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
  #prTable th:nth-child(2), #prTable td:nth-child(2), #prTable th:nth-child(6), #prTable td:nth-child(6){ text-align:left; }
'''
JS = r'''
  // ---------- Predictions tab ----------
  var PR = DATA.meta && DATA.meta.predictions;
  var prMin = document.getElementById('prMin'), prConf = document.getElementById('prConf'), prSearch = document.getElementById('prSearch');
  var prSort = { key:'absEdge', dir:-1 };
  function prLine(team, s){ if(s===null||s===undefined) return '—'; if(Math.abs(s)<0.05) return 'Pick’em'; return team+' '+(s>0?'+':'−')+Math.abs(s).toFixed(1).replace(/\.0$/,''); }
  function prFav(g, s){ return s<=0 ? prLine(g.home, s) : prLine(g.away, -s); }       // home-perspective spread -> "Fav -x"
  function prKick(g){ var d = new Date(g.start); if(isNaN(d)) return ''; var day = d.toLocaleDateString('en-US',{weekday:'short', month:'numeric', day:'numeric', timeZone:'America/New_York'});
    return g.tbd ? day+' · TBD' : day+' · '+d.toLocaleTimeString('en-US',{hour:'numeric', minute:'2-digit', timeZone:'America/New_York'}); }
  var PR_COLS = [
    { key:'start', label:'Kickoff (ET)', get:function(g){ return g.start; } },
    { key:'match', label:'Matchup', get:function(g){ return g.away+' @ '+g.home; } },
    { key:'model', label:'Model line', get:function(g){ return g.model; }, title:'Your power ratings: home rating − away rating + home-field advantage (0 at neutral sites)' },
    { key:'market', label:'Market line', get:function(g){ return g.market; } },
    { key:'absEdge', label:'Edge (pts)', get:function(g){ return g.edge===null ? -1 : Math.abs(g.edge); }, title:'Market spread − model spread: how many points of value the model sees' },
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
      var mv = (g.marketOpen!==null && g.market!==null && Math.abs(g.marketOpen-g.market)>=0.25) ? '<span class="pr-sub">open '+prFav(g, g.marketOpen)+'</span>' : '';
      var fw = g.homeWin>=50 ? g.home : g.away, fp = Math.max(g.homeWin, 100-g.homeWin);
      var rt = function(r, ok){ return ok ? (r>0?'+':'')+r.toFixed(1) : 'FCS '+r.toFixed(0); };
      return '<tr>'
        + '<td style="white-space:nowrap">'+prKick(g)+'</td>'
        + '<td><span class="team-name">'+g.away+'</span> @ <span class="team-name">'+g.home+'</span>'+(g.neutral?'<span class="pr-n" title="Neutral site">N</span>':'')+'</td>'
        + '<td class="num">'+prFav(g, g.model)+'</td>'
        + '<td class="num">'+(g.market===null?'<span style="color:var(--ink-muted)">no line yet</span>':prFav(g, g.market))+mv+'</td>'
        + '<td class="num"><span class="pr-edge'+cls+'">'+(ae===null?'—':ae.toFixed(1))+'</span></td>'
        + '<td class="pr-pick">'+side+'</td>'
        + '<td class="num">'+fp.toFixed(0)+'%<span class="pr-sub">'+fw+'</span></td>'
        + '<td class="num">'+rt(g.awayRating, g.awayRated)+' / '+rt(g.homeRating, g.homeRated)+(g.neutral?'':' <span class="pr-sub">+'+g.hfa.toFixed(1)+' HFA</span>')+'</td>'
        + '</tr>'; }).join('');
    var nAll = PR.games.length, nLine = PR.games.filter(function(g){ return g.market!==null; }).length;
    var upd = new Date(PR.updated); var updTxt = isNaN(upd) ? PR.updated : upd.toLocaleString('en-US',{month:'short', day:'numeric', hour:'numeric', minute:'2-digit', timeZone:'America/New_York'})+' ET';
    document.getElementById('prNote').innerHTML = '<b>Week '+PR.week+'</b> · '+rows.length+' of '+nAll+' games shown ('+nLine+' with a market line). '
      + 'Model line = power ratings through Week '+PR.ratingsThroughWeek+': home rating − away rating + the home team’s home-field advantage (0 at neutral sites; FCS teams rated '+PR.model.fcsRating+'). '
      + 'Market = '+PR.source+', updated '+updTxt+'. Edge = points between the market spread and the model spread; <span class="pr-edge v3">3+</span> and <span class="pr-edge v5">5+</span> highlight value. Model side = the team the model likes against the current number.';
  }
  if(PR){
    var prC = {}; PR.games.forEach(function(g){ if(g.homeConf) prC[g.homeConf]=1; if(g.awayConf) prC[g.awayConf]=1; });
    prConf.innerHTML = '<option value="all">All conferences</option>' + Object.keys(prC).sort().map(function(c){ return '<option value="'+c+'">'+c+'</option>'; }).join('');
    prMin.addEventListener('change', renderPreds); prConf.addEventListener('change', renderPreds); prSearch.addEventListener('input', renderPreds);
  } else { document.getElementById('tabBtnPreds').style.display='none'; }
'''
for p in sys.argv[1:]:
    s = open(p).read()
    if 'id="tabBtnPreds"' in s: print(p, 'already patched'); continue
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
