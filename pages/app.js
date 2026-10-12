/* CaseForge AI — 데모 UI. 게임 규칙은 전부 engine.js에 있고, 여기는 표현만 담당한다. */
(function () {
  'use strict';
  var CASE = window.CASE, D = window.DIALOGUES, Engine = window.Engine;
  var game, ui;
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var app = $('#app');
  var EV = {}, SUS = {}, ST = {}, LOC = {}, PZ = {};
  CASE.evidence.forEach(function (e) { EV[e.id] = e; });
  CASE.suspects.forEach(function (s) { SUS[s.id] = s; });
  CASE.statements.forEach(function (s) { ST[s.id] = s; });
  CASE.locations.forEach(function (l) { LOC[l.id] = l; });
  CASE.puzzles.forEach(function (p) { PZ[p.id] = p; });

  function esc(s) { return String(s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function avatar(s, size) { return '<span class="avatar" style="background:' + s.color + (size ? ';width:' + size + 'px;height:' + size + 'px' : '') + '">' + esc(s.name[0]) + '</span>'; }
  var ROLE_TAG = { key: '<span class="tag key">핵심</span>', red_herring: '', supporting: '' };

  function reset() {
    game = Engine.createGame(CASE, D);
    ui = { tab: 'briefing', scene: CASE.scenes[0].id, npc: 's01', lastInspect: null, seq: [], memo: [], code: '', fb: {}, result: null,
      dev: /[?&]dev=1/.test(location.search), unseenBoard: false, chat: { s01: [], s02: [], s03: [] } };
    CASE.suspects.forEach(function (s) { ui.chat[s.id].push({ type: 'npc', text: D[s.id].opening }); });
  }

  /* ---------------------------------------------------------------- toasts */
  function toast(text, kind) {
    var t = document.createElement('div');
    t.className = 'toast ' + (kind || '');
    t.textContent = text;
    var box = $('#toasts');
    box.appendChild(t);
    while (box.children.length > 3) box.removeChild(box.firstChild);
    setTimeout(function () { t.remove(); }, 3600);
  }
  function announceContradictions(list) {
    list.forEach(function (c) { toast('모순 발견: ' + SUS[c.npc].name + ' — ' + c.type, 'contra'); });
    if (list.length && ui.tab !== 'board') ui.unseenBoard = true;
  }

  /* ---------------------------------------------------------------- header */
  function renderProgress() {
    var s = game.state;
    var cs = game.contradictions();
    $('#progress').innerHTML =
      '<span class="pill">증거 <b>' + s.collected.length + '</b>/' + CASE.evidence.length + '</span>' +
      '<span class="pill">퍼즐 <b>' + s.solved.length + '</b>/' + CASE.puzzles.length + '</span>' +
      '<span class="pill">진술 <b>' + s.statements.length + '</b></span>' +
      '<span class="pill">모순 <b>' + cs.length + '</b>/' + CASE.contradictions.length + '</span>' +
      '<span class="pill">무너진 거짓말 <b>' + s.broken.length + '</b>/' + CASE.lies.length + '</span>' +
      '<span class="pill">가드 차단 <b>' + s.guardLog.length + '</b></span>';
    Array.prototype.forEach.call(document.querySelectorAll('#tabs button'), function (b) {
      b.setAttribute('aria-current', b.dataset.tab === ui.tab ? 'page' : 'false');
      var dot = b.dataset.tab === 'board' && ui.unseenBoard;
      var has = b.querySelector('.dot');
      if (dot && !has) b.insertAdjacentHTML('beforeend', '<span class="dot" aria-label="새 모순"></span>');
      if (!dot && has) has.remove();
    });
    $('#btn-dev').setAttribute('aria-pressed', ui.dev ? 'true' : 'false');
  }

  function render() {
    if (ui.tab === 'board') ui.unseenBoard = false;
    renderProgress();
    var html = ({ briefing: viewBriefing, scene: viewScene, puzzles: viewPuzzles, interrogation: viewInterrogation, board: viewBoard, accuse: viewAccuse })[ui.tab]();
    app.innerHTML = html;
    if (ui.tab === 'interrogation') { var log = $('.chat-log'); if (log) log.scrollTop = log.scrollHeight; }
    renderDev();
  }
  function go(tab) { ui.tab = tab; render(); window.scrollTo({ top: 0, behavior: 'smooth' }); }

  /* -------------------------------------------------------------- briefing */
  function viewBriefing() {
    var b = CASE.briefing;
    var sus = CASE.suspects.map(function (s) {
      return '<div class="card suspect-card">' + avatar(s) + '<div><h3>' + esc(s.name) + ' <span class="role">' + esc(s.role) + ' · ' + s.age + '세</span></h3>' +
        '<p class="sus">혐의: ' + esc(s.surface) + '</p><p>' + esc(s.persona) + '</p></div></div>';
    }).join('');
    return '<section class="hero">' +
      '<div class="card"><span class="kicker">사건 파일 · ' + esc(CASE.case_id) + '</span><h2>' + esc(CASE.title) + '</h2>' +
      '<p class="lead">' + esc(b.summary) + '</p>' +
      '<ul class="facts-list"><li><b>장소</b>' + esc(b.place) + '</li><li><b>시점</b>' + esc(b.when) + '</li><li><b>범행</b>' + esc(b.crime_window) + '</li></ul>' +
      '<div class="row" style="margin-top:16px"><button class="btn" data-go="scene" type="button">수사 시작 →</button>' +
      '<button class="btn secondary" data-action="validator" type="button">이 사건의 검증 결과 보기</button></div></div>' +
      '<div class="card"><h3 style="font-size:16px;margin-bottom:10px">수사 목표</h3><ol class="goals">' +
      b.goals.map(function (g) { return '<li>' + esc(g) + '</li>'; }).join('') + '</ol>' +
      '<p class="small muted" style="margin:14px 0 0">용의자는 진실을 알고 있지만 스스로 털어놓지 않습니다. 질문은 자유롭게 타이핑하세요. 증거를 제시하면 거짓말이 무너질 수 있습니다.</p></div>' +
      '</section><div class="section-title" style="margin-top:22px"><h2>용의자</h2><p>폐관 후 관내에 남아 있던 세 사람</p></div><div class="grid-3">' + sus + '</div>';
  }

  /* ----------------------------------------------------------------- scene */
  var BACKDROPS = {
    'loc-gallery': '<svg viewBox="0 0 160 100" preserveAspectRatio="none" width="100%" height="100%"><defs><radialGradient id="g1" cx="50%" cy="35%" r="60%"><stop offset="0" stop-color="#3b4a63"/><stop offset="1" stop-color="#151b22"/></radialGradient></defs><rect width="160" height="100" fill="url(#g1)"/><rect x="0" y="70" width="160" height="30" fill="#1b2027"/><rect x="66" y="40" width="28" height="30" fill="#2a3442" stroke="#5b6b82" stroke-width=".6"/><rect x="62" y="70" width="36" height="6" fill="#3a4556"/><path d="M80 30 l5 6 -5 6 -5 -6z" fill="#7fb3ff" opacity=".9"/><rect x="18" y="20" width="16" height="20" fill="#2a3442" stroke="#5b6b82" stroke-width=".5"/><rect x="126" y="22" width="18" height="24" fill="#24303c"/></svg>',
    'loc-restoration': '<svg viewBox="0 0 160 100" preserveAspectRatio="none" width="100%" height="100%"><rect width="160" height="100" fill="#1d2622"/><rect x="0" y="66" width="160" height="34" fill="#151b18"/><rect x="40" y="50" width="80" height="8" fill="#55483a"/><rect x="44" y="58" width="4" height="20" fill="#3a3128"/><rect x="112" y="58" width="4" height="20" fill="#3a3128"/><rect x="70" y="30" width="20" height="14" fill="#2b3b44" stroke="#6a8a8f" stroke-width=".6"/><path d="M100 50 l10 -22" stroke="#c9b27a" stroke-width="1"/><circle cx="110" cy="27" r="4" fill="#f2d48a" opacity=".85"/><rect x="122" y="28" width="22" height="24" fill="#3b3f44" stroke="#777" stroke-width=".5"/><rect x="24" y="64" width="12" height="14" fill="#2f2f2f"/></svg>',
    'loc-security': '<svg viewBox="0 0 160 100" preserveAspectRatio="none" width="100%" height="100%"><rect width="160" height="100" fill="#141a22"/>' +
      (function () { var s = ''; for (var r = 0; r < 3; r++) for (var c = 0; c < 4; c++) s += '<rect x="' + (78 + c * 18) + '" y="' + (12 + r * 14) + '" width="16" height="12" fill="' + ((r + c) % 3 ? '#20405a' : '#2d5a7a') + '" stroke="#4a7fa8" stroke-width=".4"/>'; return s; })() +
      '<rect x="20" y="36" width="34" height="22" fill="#232c36" stroke="#4e5d6b" stroke-width=".5"/><rect x="0" y="72" width="160" height="28" fill="#10151b"/><rect x="96" y="66" width="40" height="18" fill="#3a3326"/></svg>',
    'loc-lounge': '<svg viewBox="0 0 160 100" preserveAspectRatio="none" width="100%" height="100%"><rect width="160" height="100" fill="#211d1a"/><rect x="0" y="70" width="160" height="30" fill="#17140f"/><rect x="10" y="18" width="12" height="40" fill="#3d4650"/><rect x="23" y="18" width="12" height="40" fill="#4a5560" stroke="#f2c14e" stroke-width=".5"/><rect x="36" y="18" width="12" height="40" fill="#3d4650"/><rect x="58" y="30" width="18" height="34" fill="#a33" opacity=".75"/><rect x="61" y="34" width="12" height="10" fill="#fdd" opacity=".5"/><rect x="118" y="20" width="34" height="50" fill="#0b0f14"/><rect x="118" y="20" width="34" height="50" fill="none" stroke="#5b5146" stroke-width="1.2"/><circle cx="135" cy="58" r="1.4" fill="#f60"/></svg>'
  };
  function viewScene() {
    var sc = CASE.scenes.filter(function (s) { return s.id === ui.scene; })[0];
    var st = game.state;
    var tabs = CASE.scenes.map(function (s) {
      var left = s.hotspots.filter(function (h) { return st.inspected.indexOf(h.id) === -1; }).length;
      return '<button type="button" data-scene="' + s.id + '" aria-pressed="' + (s.id === ui.scene) + '">' + esc(s.name) + (left ? ' · ' + left : ' ✓') + '</button>';
    }).join('');
    var hs = sc.hotspots.map(function (h) {
      return '<button type="button" class="hotspot' + (st.inspected.indexOf(h.id) !== -1 ? ' done' : '') + '" data-hotspot="' + h.id + '" style="left:' + h.x + '%;top:' + h.y + '%">' + esc(h.label) + '</button>';
    }).join('');
    var res = '';
    if (ui.lastInspect && ui.lastInspect.scene === sc.id) {
      var r = ui.lastInspect, h = r.hotspot;
      res = '<div class="inspect-result' + (r.got ? ' found' : '') + '"><b>' + esc(h.label) + '</b> — ' + esc(h.text);
      if (r.got && r.got.evidence) res += '<div style="margin-top:6px"><b>' + r.got.evidence.icon + ' 증거 확보: ' + esc(r.got.evidence.name) + '</b><br><span class="small">' + esc(r.got.evidence.desc) + '</span></div>';
      if (r.got && r.got.clue) res += '<div style="margin-top:6px"><b>🔎 단서: ' + esc(r.got.clue.name) + '</b><br><span class="small">' + esc(r.got.clue.desc) + '</span></div>';
      if (r.puzzle) res += '<div style="margin-top:8px"><button class="btn" type="button" data-go="puzzles">퍼즐 열기: ' + esc(PZ[r.puzzle].title) + ' →</button></div>';
      res += '</div>';
    } else {
      res = '<div class="inspect-result muted">빛나는 지점을 눌러 조사하세요.</div>';
    }
    return '<div class="section-title"><h2>현장 조사</h2><p>네 구역을 돌며 증거와 단서를 모으세요.</p></div>' +
      '<div class="grid-2"><div><div class="scene-tabs">' + tabs + '</div>' +
      '<div class="stage"><div class="backdrop">' + BACKDROPS[sc.id] + '</div><span class="label">' + esc(sc.name).toUpperCase() + '</span>' + hs + '<span class="mood">' + esc(sc.mood) + '</span></div>' + res + '</div>' +
      '<div>' + evidencePanel() + cluePanel() + '</div></div>';
  }
  function evidencePanel() {
    var st = game.state;
    var items = st.collected.map(function (id) {
      var e = EV[id];
      return '<div class="ev-item"><span class="ev-icon">' + e.icon + '</span><div><h4>' + esc(e.name) + ' <span class="tag">' + e.id + '</span></h4><p>' + esc(e.desc) + '</p></div></div>';
    }).join('');
    return '<div class="card"><h3 style="font-size:15px;margin-bottom:10px">수집한 증거 (' + st.collected.length + '/' + CASE.evidence.length + ')</h3>' + (items || '<div class="empty">아직 없음</div>') + '</div>';
  }
  function cluePanel() {
    var st = game.state;
    if (!st.clues.length) return '';
    return '<div class="card"><h3 style="font-size:15px;margin-bottom:10px">퍼즐 단서</h3>' + st.clues.map(function (id) {
      var c = CASE.clues.filter(function (x) { return x.id === id; })[0];
      return '<div class="ev-item"><span class="ev-icon">🔎</span><div><h4>' + esc(c.name) + '</h4><p>' + esc(c.desc) + '</p></div></div>';
    }).join('') + '</div>';
  }

  /* --------------------------------------------------------------- puzzles */
  function clock(h, m) {
    var ha = ((h % 12) + m / 60) * 30, ma = m * 6;
    var ticks = '';
    for (var i = 0; i < 60; i++) { var a = i * 6 * Math.PI / 180, r1 = i % 5 ? 26 : 23; ticks += '<line x1="' + (32 + r1 * Math.sin(a)).toFixed(2) + '" y1="' + (32 - r1 * Math.cos(a)).toFixed(2) + '" x2="' + (32 + 28 * Math.sin(a)).toFixed(2) + '" y2="' + (32 - 28 * Math.cos(a)).toFixed(2) + '" stroke="#e9e4d8" stroke-opacity="' + (i % 5 ? .55 : 1) + '" stroke-width="' + (i % 15 ? (i % 5 ? .6 : 1.2) : 2) + '"/>'; }
    return '<svg viewBox="0 0 64 64" aria-label="벽시계"><circle cx="32" cy="32" r="30" fill="#0d1216" stroke="#e9e4d8" stroke-width="1.5"/>' + ticks +
      '<line x1="32" y1="32" x2="32" y2="17" stroke="#e9e4d8" stroke-width="3" stroke-linecap="round" transform="rotate(' + ha + ' 32 32)"/>' +
      '<line x1="32" y1="32" x2="32" y2="8" stroke="#f2c14e" stroke-width="1.6" stroke-linecap="round" transform="rotate(' + ma + ' 32 32)"/><circle cx="32" cy="32" r="2" fill="#f2c14e"/></svg>';
  }
  function puzzleHead(p, solved, avail) {
    return '<h3>' + esc(p.title) + ' <span class="tag">' + esc(LOC[p.location].name) + '</span>' +
      (solved ? '<span class="tag ok">해결 → ' + esc(EV[p.reward].name) + '</span>' : avail ? '<span class="tag info">풀 수 있음</span>' : '<span class="tag warn">단서 필요</span>') + '</h3>';
  }
  function hintBtn(p) { return '<button class="btn secondary" type="button" data-hint="' + p.id + '">힌트</button>'; }
  function viewPuzzles() {
    var st = game.state;
    var out = '<div class="section-title"><h2>퍼즐</h2><p>풀면 잠긴 기록이 증거로 추가됩니다. 정답 판정은 엔진이 합니다.</p></div>';
    CASE.puzzles.forEach(function (p) {
      var solved = st.solved.indexOf(p.id) !== -1, avail = game.puzzleAvailable(p.id);
      var fb = ui.fb[p.id] || '';
      var body = '';
      if (solved) {
        var e = EV[p.reward];
        body = '<div class="inspect-result found"><b>' + e.icon + ' ' + esc(e.name) + '</b><br><span class="small">' + esc(e.desc) + '</span></div>';
      } else if (!avail) {
        body = '<div class="empty">' + (p.id === 'pz-02' ? '복원실의 개인 금고를 먼저 조사하세요.' : '메모 조각을 모두 찾아야 합니다. (복원실 서랍, 휴게실 휴지통)') + '</div>';
      } else if (p.type === 'sequence') {
        body = '<div class="frames">' + p.items.map(function (it) {
          var idx = ui.seq.indexOf(it.id);
          return '<button type="button" class="frame' + (idx !== -1 ? ' picked' : '') + '" data-frame="' + it.id + '">' + (idx !== -1 ? '<span class="order">' + (idx + 1) + '</span>' : '') +
            clock(it.clock[0], it.clock[1]) + (it.frozen ? '<span class="frozen-tag">● 점검 모드</span><span class="frozen"></span>' : '') + '<span>' + esc(it.label) + '</span></button>';
        }).join('') + '</div><div class="row" style="margin-top:10px"><button class="btn" type="button" data-submit="pz-01"' + (ui.seq.length !== 4 ? ' disabled' : '') + '>순서 제출</button><button class="btn secondary" type="button" data-reset="seq">다시 고르기</button>' + hintBtn(p) + '</div>';
      } else if (p.type === 'code') {
        var clues = ['clue-safe-note', 'clue-cards'].filter(function (c) { return st.clues.indexOf(c) !== -1; }).map(function (c) {
          return '<div class="clue-box">🔎 ' + esc(CASE.clues.filter(function (x) { return x.id === c; })[0].desc) + '</div>';
        }).join('');
        if (st.clues.indexOf('clue-cards') === -1) clues += '<div class="clue-box" style="background:var(--paper-2)">연도가 필요해 보인다. 전시실에 단서가 있을지도.</div>';
        body = clues + '<form class="code-input" data-codeform="pz-02"><input id="code" inputmode="numeric" maxlength="4" autocomplete="off" placeholder="····" value="' + esc(ui.code) + '" aria-label="4자리 비밀번호"><button class="btn" type="submit">열기</button></form><div class="row" style="margin-top:8px">' + hintBtn(p) + '</div>';
      } else if (p.type === 'arrangement') {
        body = '<div class="memo-pieces">' + p.items.map(function (it) {
          return '<button type="button" class="memo-piece" data-memo="' + it.id + '"' + (ui.memo.indexOf(it.id) !== -1 ? ' disabled' : '') + '>' + esc(it.label) + '</button>';
        }).join('') + '</div><div class="memo-preview">' + (ui.memo.length ? esc(ui.memo.map(function (id) { return p.items.filter(function (x) { return x.id === id; })[0].label; }).join('')) : '<span class="muted" style="font-family:system-ui;font-size:13px">조각을 순서대로 누르세요</span>') + '</div>' +
          '<div class="row"><button class="btn" type="button" data-submit="pz-03"' + (ui.memo.length !== 4 ? ' disabled' : '') + '>맞춰 보기</button><button class="btn secondary" type="button" data-reset="memo">다시</button>' + hintBtn(p) + '</div>';
      }
      out += '<div class="card puzzle' + (!avail && !solved ? ' locked' : '') + '">' + puzzleHead(p, solved, avail) + '<p class="prompt">' + esc(p.prompt) + '</p>' + body +
        '<div class="feedback ' + (fb.indexOf('정답') === 0 ? 'ok' : 'bad') + '">' + esc(fb) + '</div></div>';
    });
    return out;
  }
  function submitPuzzle(pid, answer) {
    var r = game.attemptPuzzle(pid, answer);
    if (r.ok && r.unlocked) {
      ui.fb[pid] = '정답! ' + r.unlocked.name + '을(를) 확보했다.';
      toast('증거 확보: ' + r.unlocked.icon + ' ' + r.unlocked.name, 'found');
      announceContradictions(r.newContradictions || []);
    } else if (r.locked) {
      ui.fb[pid] = '아직 단서가 부족하다.';
    } else {
      ui.fb[pid] = '맞지 않는다. 다시 생각해 보자.';
      if (pid === 'pz-01') ui.seq = [];
      if (pid === 'pz-03') ui.memo = [];
    }
    render();
  }

  /* --------------------------------------------------------- interrogation */
  function viewInterrogation() {
    var st = game.state, npc = SUS[ui.npc], ns = st.npc[ui.npc];
    var list = CASE.suspects.map(function (s) {
      return '<button type="button" class="npc-btn" data-npc="' + s.id + '" aria-pressed="' + (s.id === ui.npc) + '">' + avatar(s) + '<span><b>' + esc(s.name) + '</b><span>' + esc(s.role) + ' · ' + esc(st.npc[s.id].emotion) + '</span></span></button>';
    }).join('');
    var log = ui.chat[ui.npc].map(function (m) {
      if (m.type === 'me') return '<div class="msg me">' + esc(m.text) + '</div>';
      if (m.type === 'present') return '<div class="msg present">' + EV[m.ev].icon + ' 증거 제시: ' + esc(EV[m.ev].name) + '</div>';
      if (m.type === 'npc') return '<div class="msg npc">' + esc(m.text) + (m.emotion ? '<span class="meta">' + esc(npc.name) + ' · ' + esc(m.emotion) + '</span>' : '') + '</div>';
      if (m.type === 'dev') return ui.dev ? '<div class="dev-meta">' + m.html + '</div>' : '';
      return '<div class="sys ' + m.type + '">' + esc(m.text) + '</div>';
    }).join('');
    var opts = st.collected.map(function (id) { return '<option value="' + id + '">' + EV[id].icon + ' ' + esc(EV[id].name) + (st.presented[ui.npc].indexOf(id) !== -1 ? ' (제시함)' : '') + '</option>'; }).join('');
    var chips = D[ui.npc].suggestions.map(function (q) { return '<button type="button" class="chip" data-suggest="' + esc(q) + '">' + esc(q) + '</button>'; }).join('');
    return '<div class="section-title"><h2>심문</h2><p>자유롭게 질문하고, 증거를 제시해 진술의 빈틈을 찌르세요.</p></div>' +
      '<div class="interro"><div class="npc-list">' + list + '</div>' +
      '<div class="card chat"><div class="chat-head">' + avatar(npc) + '<div><h3>' + esc(npc.name) + '</h3><p>' + esc(npc.role) + ' · ' + esc(npc.persona) + '</p></div><span class="emotion">' + esc(ns.emotion) + '</span></div>' +
      '<div class="chat-log" aria-live="polite">' + log + '</div>' +
      '<div class="chat-foot"><div class="chips">' + chips + '</div>' +
      '<form class="ask-row" id="ask-form"><input id="ask-input" autocomplete="off" maxlength="200" placeholder="' + esc(npc.name) + '에게 질문하기…" aria-label="질문"><button class="btn" type="submit">질문</button></form>' +
      '<div class="present-row"><select id="present-select" aria-label="제시할 증거">' + opts + '</select><button class="btn secondary" type="button" id="present-btn">증거 제시</button></div></div></div></div>';
  }
  function pushResult(r) {
    var c = ui.chat[r.npc];
    if (r.kind === 'ask') c.push({ type: 'me', text: r.input }); else c.push({ type: 'present', ev: r.input });
    if (r.guard.blocked && r.guard.stage === 'input') c.push({ type: 'guard', text: '입력 가드: 프롬프트 공격·정답 요구 패턴 감지 → 캐릭터 회피 대사로 대체' });
    if (r.guard.blocked && r.guard.stage === 'output') c.push({ type: 'guard', text: '출력 가드: 답변 초안이 금지된 사실(' + uniq(r.guard.violations.map(function (v) { return v.fact; })).join(', ') + ')을 말하려 해 차단 → 회피 대사로 대체' });
    c.push({ type: 'npc', text: r.text, emotion: r.emotion });
    var dev = '의도=<b>' + esc(r.intent) + '</b>' + (r.matched.length ? ' · 키워드=' + esc(r.matched.join(',')) : '') +
      ' · revealed_fact_ids=[' + esc(r.revealed_fact_ids.join(', ')) + '] · 가드=' + (r.guard.blocked ? '<b>차단(' + r.guard.stage + ')</b>' : '통과');
    if (r.draftText) dev += '<br>차단된 초안: <s>' + esc(r.draftText) + '</s><br>' + esc(r.guard.violations.map(function (v) { return v.detail; }).filter(function (x, i, a) { return a.indexOf(x) === i; }).join(' / '));
    c.push({ type: 'dev', html: dev });
    if (r.note) c.push({ type: 'note', text: r.note });
    r.brokenLies.forEach(function (lid) {
      var l = CASE.lies.filter(function (x) { return x.id === lid; })[0];
      c.push({ type: 'break', text: '거짓말 붕괴: 「' + l.claim + '」' });
      toast(SUS[r.npc].name + '의 거짓말이 무너졌다!', 'break');
    });
    if (r.newStatement) c.push({ type: 'stmt', text: '수사 노트에 진술 기록: ' + r.newStatement.text });
    r.newContradictions.forEach(function (x) { c.push({ type: 'contra', text: '모순 감지 (' + x.type + '): ' + x.explain }); });
    announceContradictions(r.newContradictions);
  }
  function uniq(a) { return a.filter(function (x, i) { return a.indexOf(x) === i; }); }

  /* ----------------------------------------------------------------- board */
  function viewBoard() {
    var st = game.state, cs = game.contradictions();
    var stmts = CASE.suspects.map(function (s) {
      var mine = st.statements.filter(function (id) { return ST[id].npc === s.id; });
      if (!mine.length) return '';
      return mine.map(function (id) {
        var x = ST[id];
        var lie = CASE.lies.filter(function (l) { return l.statement === id; })[0];
        var isBroken = lie && st.broken.indexOf(lie.id) !== -1;
        return '<div class="stmt' + (isBroken ? ' lie' : '') + '"><div class="who">' + avatar(s, 18) + esc(s.name) + (x.time ? ' · ' + esc(x.time) : '') + (isBroken ? ' <span class="tag bad">거짓말</span>' : '') + '</div><span class="q">' + esc(x.text) + '</span></div>';
      }).join('');
    }).join('');
    var contras = cs.map(function (c) {
      return '<div class="contra' + (c.resolved ? ' resolved' : '') + '"><div class="row"><b>' + esc(c.type) + ' 모순</b><span class="tag">' + esc(SUS[c.npc].name) + '</span>' +
        (c.resolved ? '<span class="tag ok">추궁 성공</span>' : '<span class="tag warn">추궁 전</span>') + '<span class="tag info">판정: 규칙</span></div>' +
        '<div class="vs"><div>진술: ' + esc(c.a.text) + '</div><div>' + (c.b.evidence ? '증거: ' + c.b.evidence.icon + ' ' + esc(c.b.evidence.name) : '진술: ' + esc(c.b.statement.text)) + '</div></div>' +
        '<div class="small">' + esc(c.explain) + '</div>' +
        (!c.resolved && c.lie && c.b.evidence ? '<div class="small muted" style="margin-top:4px">→ 심문에서 ' + esc(SUS[c.npc].name) + '에게 이 증거를 제시해 보자.</div>' : '') + '</div>';
    }).join('');
    // 확인된 시각: 수집한 증거 + 들은 진술
    var times = [];
    st.collected.forEach(function (id) { var e = EV[id]; if (e.time) times.push({ t: e.time, text: e.icon + ' ' + e.name, sub: e.desc }); });
    st.statements.forEach(function (id) { var x = ST[id]; if (x.time) times.push({ t: x.time, text: SUS[x.npc].name + ' 진술', sub: x.text }); });
    times.sort(function (a, b) { return a.t.localeCompare(b.t); });
    var tl = times.map(function (x) { return '<div class="tl-item"><b>' + esc(x.t) + '</b>' + esc(x.text) + '<div class="small muted">' + esc(x.sub) + '</div></div>'; }).join('');
    var ev = game.state.collected.map(function (id) { var e = EV[id]; return '<div class="ev-item"><span class="ev-icon">' + e.icon + '</span><div><h4>' + esc(e.name) + '</h4><p>' + esc(e.desc) + '</p></div></div>'; }).join('');
    return '<div class="section-title"><h2>수사 보드</h2><p>진술이 증거·다른 진술과 부딪히면 규칙 엔진이 모순으로 표시합니다.</p></div>' +
      '<div class="board"><div class="card"><h3>⚠ 모순 (' + cs.length + '/' + CASE.contradictions.length + ')</h3>' + (contras || '<div class="empty">아직 없음. 용의자의 행적을 묻고, 반대되는 증거를 모아 보세요.</div>') + '</div>' +
      '<div class="card"><h3>🗣 진술 (' + st.statements.length + ')</h3>' + (stmts || '<div class="empty">심문하면 중요한 진술이 자동으로 기록됩니다.</div>') + '</div>' +
      '<div class="card"><h3>🕘 확인된 시각</h3>' + (tl ? '<div class="timeline">' + tl + '</div>' : '<div class="empty">시각이 찍힌 증거·진술이 여기 쌓입니다.</div>') +
      '<h3 style="margin-top:16px">📁 증거 (' + st.collected.length + ')</h3>' + ev + '</div></div>';
  }

  /* ---------------------------------------------------------------- accuse */
  function viewAccuse() {
    if (ui.result) return viewResult();
    var st = game.state, A = CASE.accusation;
    var sus = CASE.suspects.map(function (s) { return '<label class="choice"><input type="radio" name="culprit" value="' + s.id + '">' + avatar(s, 30) + '<span><b>' + esc(s.name) + '</b><br><span class="small muted">' + esc(s.role) + '</span></span></label>'; }).join('');
    var mot = A.motives.map(function (m) { return '<label class="choice"><input type="radio" name="motive" value="' + m.id + '"><span>' + esc(m.label) + '</span></label>'; }).join('');
    var met = A.methods.map(function (m) { return '<label class="choice"><input type="checkbox" name="method" value="' + m.id + '"><span>' + esc(m.label) + '</span></label>'; }).join('');
    var ev = CASE.evidence.map(function (e) {
      var has = st.collected.indexOf(e.id) !== -1;
      return '<label class="choice' + (has ? '' : ' disabled') + '"><input type="checkbox" name="evidence" value="' + e.id + '"' + (has ? '' : ' disabled') + '><span>' + (has ? e.icon + ' ' + esc(e.name) : '<span class="muted">미확보 증거</span>') + '</span></label>';
    }).join('');
    return '<div class="section-title"><h2>최종 추리</h2><p>제출하면 사건이 종료되고 해설이 열립니다.</p></div>' +
      '<form class="card" id="accuse-form">' +
      '<div class="form-block" style="margin-top:0"><h3>1. 범인</h3><div class="choice-grid">' + sus + '</div></div>' +
      '<div class="form-block"><h3>2. 동기</h3><div class="choice-grid">' + mot + '</div></div>' +
      '<div class="form-block"><h3>3. 수법 (해당하는 것을 모두)</h3><div class="choice-grid">' + met + '</div></div>' +
      '<div class="form-block"><h3>4. 범인을 증명하는 핵심 증거</h3><div class="choice-grid">' + ev + '</div></div>' +
      '<div class="form-block"><h3>5. 추리 서술 (선택)</h3><textarea name="essay" maxlength="1000" placeholder="사건을 어떻게 재구성했는지 적어 보세요."></textarea>' +
      '<p class="small muted">자유 서술은 해설 화면에 함께 표시되며 점수에는 반영하지 않습니다. 실제 설계에서는 구조 채점이 점수를 정하고, LLM은 논리 비약·근거 없는 주장만 표시합니다.</p></div>' +
      '<div class="row" style="margin-top:14px"><button class="btn" type="submit">추리 제출</button><span class="small muted" id="accuse-msg"></span></div></form>';
  }
  function viewResult() {
    var r = ui.result, sol = r.solution, A = CASE.accusation;
    var label = function (list, id) { var x = list.filter(function (m) { return m.id === id; })[0]; return x ? x.label : '—'; };
    var bars = [['범인', r.parts.culprit, 40], ['동기', r.parts.motive, 20], ['수법', r.parts.method, 20], ['증거', r.parts.evidence, 20]].map(function (b) {
      return '<div class="bar"><span>' + b[0] + '</span><span class="track"><span class="fill" style="width:' + (b[1] / b[2] * 100) + '%"></span></span><span class="num">' + Math.round(b[1]) + '/' + b[2] + '</span></div>';
    }).join('') + (r.penalty ? '<div class="bar"><span>모순 감점</span><span></span><span class="num" style="color:var(--bad)">−' + r.penalty + '</span></div>' : '');
    var flags = r.flags.map(function (f) { return '<div class="flag">' + esc(f.text) + '</div>'; }).join('');
    var missed = r.missed.map(function (m) { return '<li>' + m.evidence.icon + ' ' + esc(m.evidence.name) + ' — ' + (m.collected ? '확보했지만 연결하지 않음' : '확보하지 못함') + '</li>'; }).join('');
    var tl = CASE.timeline.slice().sort(function (a, b) { return a.start.localeCompare(b.start); }).map(function (t) {
      return '<div class="tl-item' + (t.crime ? ' crime' : '') + '"><b>' + t.start + (t.end !== t.start ? '–' + t.end : '') + '</b>' + esc(SUS[t.actor].name) + ' · ' + esc(LOC[t.location].name) + '<div class="small muted">' + esc(t.action) + '</div></div>';
    }).join('');
    var s = r.stats;
    return '<div class="card"><div class="result-hero"><div class="grade ' + r.grade + '">' + r.grade + '</div><div><span class="kicker">' + (r.correct ? '사건 해결' : '미해결 — 진범은 따로 있었다') + '</span>' +
      '<h2 style="font-size:26px;margin-top:4px">' + r.total + '점 / 100</h2><p class="small muted" style="margin:4px 0 0">진범: ' + esc(r.culprit.name) + ' (' + esc(r.culprit.role) + ') · 동기: ' + esc(label(A.motives, sol.motive)) + '</p></div></div>' +
      '<div class="bars">' + bars + '</div>' + flags + '</div>' +
      '<div class="grid-2" style="margin-top:14px"><div class="card"><h3 style="font-size:16px;margin-bottom:10px">해설 — 무슨 일이 있었나</h3><ol class="narrative">' + sol.narrative.map(function (n) { return '<li>' + esc(n) + '</li>'; }).join('') + '</ol>' +
      '<h3 style="font-size:15px;margin:16px 0 6px">나머지 두 사람</h3><p class="small">' + esc(sol.innocents.s01) + '</p><p class="small">' + esc(sol.innocents.s02) + '</p>' +
      '<h3 style="font-size:15px;margin:16px 0 6px">정답 수법 · 핵심 증거</h3><ul class="small">' + sol.method.map(function (m) { return '<li>' + esc(label(A.methods, m)) + '</li>'; }).join('') + '</ul>' +
      '<p class="small">' + sol.key_evidence.map(function (e) { return EV[e].icon + ' ' + esc(EV[e].name); }).join(' · ') + '</p>' +
      (missed ? '<h3 style="font-size:15px;margin:16px 0 6px">놓친 핵심 증거</h3><ul class="small">' + missed + '</ul>' : '') +
      (ui.essay ? '<h3 style="font-size:15px;margin:16px 0 6px">나의 추리 서술</h3><p class="small" style="white-space:pre-wrap">' + esc(ui.essay) + '</p>' : '') + '</div>' +
      '<div class="card"><h3 style="font-size:16px;margin-bottom:10px">전체 시간선 (진실)</h3><div class="timeline">' + tl + '</div>' +
      '<h3 style="font-size:15px;margin:16px 0 6px">수사 기록</h3><ul class="small"><li>행동 ' + s.turns + '회 · 증거 ' + s.collected + '/' + s.totalEvidence + '</li><li>무너뜨린 거짓말 ' + s.broken + '/' + s.lies + ' · 발견한 모순 ' + s.contradictions + '/' + s.totalContradictions + '</li><li>누설 가드 차단 ' + s.guardBlocks + '회</li></ul>' +
      '<div class="row" style="margin-top:12px"><button class="btn" type="button" data-action="restart">처음부터 다시</button><a class="btn secondary" style="text-decoration:none" href="https://github.com/jngbnss/caseforge-ai" target="_blank" rel="noopener">설계 문서 보기 ↗</a></div></div></div>';
  }

  /* ------------------------------------------------------------- dev/modal */
  function renderDev() {
    var p = $('#devpanel');
    p.hidden = !ui.dev;
    if (!ui.dev) return;
    var st = game.state;
    var sc = game.scope(ui.npc);
    var h = '<h4>현재 NPC 스코프 — ' + esc(SUS[ui.npc].name) + ' (KnowledgeScope)</h4><div>' + Object.keys(sc).map(function (k) { return k + ':' + sc[k]; }).join(' · ') + '</div>';
    h += '<h4>가드 기록 (' + st.guardLog.length + ')</h4>' + (st.guardLog.map(function (g) {
      return '<div class="entry">#' + g.turn + ' ' + esc(SUS[g.npc].name) + ' · ' + g.stage + ' · "' + esc(g.input) + '"' + (g.violations.length ? '<br>' + esc(uniq(g.violations.map(function (v) { return v.detail; })).join(' / ')) : '') + '</div>';
    }).join('') || '<div class="muted">없음</div>');
    var last = st.log[st.log.length - 1];
    if (last) h += '<h4>마지막 응답 JSON</h4><pre style="white-space:pre-wrap;margin:0">' + esc(JSON.stringify({ npc: last.npc, intent: last.intent, score: last.score, emotion: last.emotion, revealed_fact_ids: last.revealed_fact_ids, guard: { stage: last.guard.stage, blocked: last.guard.blocked }, contradiction_detected: last.newContradictions.map(function (c) { return c.id; }), contradiction_source: 'rule' }, null, 1)) + '</pre>';
    $('#devbody').innerHTML = h;
  }
  function showValidator() {
    var rep = Engine.validateCase(CASE);
    $('#modal-title').textContent = '사건 검증기 — ' + CASE.case_id + (rep.ok ? ' · 전부 통과' : ' · 실패 있음');
    $('#modal-body').innerHTML = '<p class="small muted" style="margin-top:0">docs/mvp-proposal.md 4절의 규칙을 브라우저에서 이 사건 데이터에 실제로 실행한 결과입니다. 게임을 시작하기 전에 사건이 풀 수 있고, 답이 하나뿐이며, 시간선이 물리적으로 가능한지 확인합니다.</p>' +
      rep.rules.map(function (r) { return '<div class="rule"><span class="rid ' + (r.ok ? 'ok' : 'bad') + '">' + (r.ok ? '✔' : '✖') + ' ' + r.id + '</span><div><b>' + esc(r.name) + '</b><div class="muted">' + esc(r.detail) + '</div></div></div>'; }).join('') +
      '<p class="small muted">L01(LLM 비평)은 설계상 경고 전용이라 이 데모에서는 실행하지 않습니다.</p>';
    $('#modal').hidden = false;
  }

  /* --------------------------------------------------------------- events */
  document.addEventListener('click', function (e) {
    var t = e.target.closest('button, [data-go]');
    if (!t) { if (e.target.id === 'modal') $('#modal').hidden = true; return; }
    var d = t.dataset;
    if (d.tab) return go(d.tab);
    if (d.go) return go(d.go);
    if (t.id === 'btn-validator' || d.action === 'validator') return showValidator();
    if (t.id === 'modal-close') { $('#modal').hidden = true; return; }
    if (t.id === 'btn-dev' || t.id === 'dev-close') { ui.dev = t.id === 'btn-dev' ? !ui.dev : false; return render(); }
    if (d.action === 'restart') { reset(); $('#toasts').innerHTML = ''; return go('briefing'); }
    if (d.scene) { ui.scene = d.scene; return render(); }
    if (d.hotspot) {
      var r = game.inspect(d.hotspot);
      ui.lastInspect = r;
      if (r.got && r.got.evidence) toast('증거 확보: ' + r.got.evidence.icon + ' ' + r.got.evidence.name, 'found');
      if (r.got && r.got.clue) toast('단서 발견: ' + r.got.clue.name);
      announceContradictions(r.newContradictions);
      return render();
    }
    if (d.frame) { var i = ui.seq.indexOf(d.frame); if (i === -1) ui.seq.push(d.frame); else ui.seq.splice(i, 1); ui.fb['pz-01'] = ''; return render(); }
    if (d.memo) { ui.memo.push(d.memo); ui.fb['pz-03'] = ''; return render(); }
    if (d.reset) { if (d.reset === 'seq') ui.seq = []; else ui.memo = []; return render(); }
    if (d.submit) return submitPuzzle(d.submit, d.submit === 'pz-01' ? ui.seq.slice() : ui.memo.slice());
    if (d.hint) { ui.fb[d.hint] = '힌트: ' + game.hint(d.hint); return render(); }
    if (d.npc) { ui.npc = d.npc; return render(); }
    if (d.suggest) { var inp = $('#ask-input'); inp.value = d.suggest; inp.focus(); return; }
    if (t.id === 'present-btn') {
      var ev = $('#present-select').value;
      if (!ev) return;
      pushResult(game.present(ui.npc, ev));
      return render();
    }
  });
  document.addEventListener('submit', function (e) {
    e.preventDefault();
    var f = e.target;
    if (f.id === 'ask-form') {
      var q = $('#ask-input').value.trim();
      if (!q) return;
      pushResult(game.ask(ui.npc, q));
      render();
      var inp = $('#ask-input'); if (inp && window.matchMedia('(min-width: 900px)').matches) inp.focus();
      return;
    }
    if (f.dataset.codeform) { ui.code = $('#code').value.replace(/\D/g, ''); return submitPuzzle('pz-02', ui.code); }
    if (f.id === 'accuse-form') {
      var fd = new FormData(f);
      if (!fd.get('culprit') || !fd.get('motive')) { $('#accuse-msg').textContent = '범인과 동기를 골라 주세요.'; return; }
      ui.essay = String(fd.get('essay') || '').trim();
      ui.result = game.score({ culprit: fd.get('culprit'), motive: fd.get('motive'), method: fd.getAll('method'), evidence: fd.getAll('evidence') });
      render();
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  });
  document.addEventListener('input', function (e) { if (e.target.id === 'code') { e.target.value = e.target.value.replace(/\D/g, '').slice(0, 4); ui.code = e.target.value; } });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') $('#modal').hidden = true; });

  reset();
  render();
})();
