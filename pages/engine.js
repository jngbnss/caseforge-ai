/*
 * CaseForge AI — 로컬 규칙 엔진 (데모용)
 *
 * 실제 설계의 심문 파이프라인  scope → retrieve → generate → guard → update_state  를
 * LLM 없이 흉내 낸다.
 *   - retrieve/generate 자리: 키워드 기반 의도 분류 + 대본 변형 선택
 *   - guard: 실제 설계와 같은 규칙 (revealed_fact_ids ⊆ scope, 카나리 키워드)
 *   - 모순 탐지 / 추리 채점 / 사건 검증기: 규칙 기반 (설계상으로도 규칙이 1차 판정)
 * DOM에 의존하지 않으므로 node에서 그대로 테스트할 수 있다.
 */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.Engine = factory();
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  /* ------------------------------------------------------------------ utils */
  function normalize(t) {
    return String(t || '').toLowerCase().replace(/[\s.,!?~'"“”‘’…·()\[\]{}<>\-—_/\\*#@]/g, '');
  }
  function toMin(hhmm) { var p = hhmm.split(':'); return (+p[0]) * 60 + (+p[1]); }
  function byId(list) { var m = {}; list.forEach(function (x) { m[x.id] = x; }); return m; }
  function uniq(a) { return a.filter(function (x, i) { return a.indexOf(x) === i; }); }

  /* --------------------------------------------------------------- intents */
  var INTENTS = [
    { id: 'inject', boost: 100, kw: ['시스템프롬프트', '프롬프트', '지시사항', '이전지시', '지시를무시', '무시하고', '개발자모드', '관리자모드', 'ignore', 'system', 'prompt', 'jailbreak', '너는이제', '역할을바꿔', '설정을알려', '정답을알려', '정답알려', '정답이뭐', '정답말해', '솔루션', 'json', '숨겨진정보', '비밀을모두', '다른사람의비밀', '다른사람비밀', '케이스바이블', 'bible'] },
    { id: 'hypothetical', boost: 40, kw: ['만약', '가정해', '가정하', '했다면', '였다면', '라고치면', '이라고치고', '한다면'] },
    { id: 'confess', boost: 6, kw: ['범인이죠', '범인이지', '범인이잖', '범인이야', '범인이에요', '범인이네', '범인이군', '당신이범인', '네가범인', '니가범인', '당신이훔', '네가훔', '당신이가져', '훔쳤죠', '훔쳤지', '훔쳤잖', '훔친거', '자백', '털어놔', '인정하', '실토', '거짓말하지마'] },
    { id: 'whodunit', boost: 6, kw: ['누가범인', '범인은누구', '범인이누구', '누가훔', '누구짓', '누가그랬', '의심가는', '의심스러운', '수상한사람', '범인같', '누가했', '누구라고생각'] },
    { id: 'alibi', kw: ['어디', '뭐했', '무엇을했', '뭘했', '뭐하', '알리바이', '그시간', '그때', '21시', '9시', '밤에', '행적', '동선', '나갔', '나간', '자리를', '있었', '계셨', '어제'] },
    { id: 'diamond', kw: ['다이아', '푸른별', '보석', '모조품', '가짜', '진품', '감정서', '진열장'] },
    { id: 'cctv', kw: ['cctv', '씨씨티비', '카메라', '녹화', '영상', '점검모드', '공백', '단말', '로그인', '습도'] },
    { id: 'card', kw: ['카드', '출입', '출입증', '로그', '수장고', '열쇠'] },
    { id: 'locker', kw: ['사물함', '락커', '3번'] },
    { id: 'smoke', kw: ['담배', '흡연', '꽁초', '후문', '피우', '피워', '피웠'] },
    { id: 'coffee', kw: ['커피', '자판기', '영수증', '휴게실'] },
    { id: 'phone', kw: ['전화', '통화', '이직', '면접', '경매', '주차장', '휴대폰'] },
    { id: 'money', kw: ['돈', '빚', '채무', '도박', '동기', '독촉', '수집가', '금전', '대출', '월급'] },
    { id: 'craft', kw: ['몰드', '실리콘', '본뜨', '본떠', '복원', '연마', '장갑', '니트릴', '받침', '세척', '작업'] },
    { id: 'office', kw: ['사무실', '도록', '교정'] },
    { id: 'self', kw: ['자기소개', '누구세요', '누구야', '당신은누구', '무슨일을', '하는일', '직업', '소개', '어떤일'] },
    { id: 'greet', kw: ['안녕', '처음뵙', '반갑'] },
    { id: 'bye', kw: ['고마', '감사', '수고', '다음에', '이만'] }
  ];

  function classify(CASE, npcId, text) {
    var n = normalize(text);
    var intents = INTENTS.slice();
    CASE.suspects.forEach(function (s) {
      if (s.id === npcId) return; // 자기 자신에 대한 언급은 다른 의도로 해석한다
      intents.push({ id: 'about_' + s.id, kw: [s.name, s.name.slice(1)].concat(s.aliases || []) });
    });
    var best = { intent: 'unknown', score: 0, matched: [] };
    intents.forEach(function (it, order) {
      var matched = it.kw.filter(function (k) { return n.indexOf(normalize(k)) !== -1; });
      if (!matched.length) return;
      var score = matched.reduce(function (a, k) { return a + normalize(k).length; }, 0) + (it.boost || 0);
      if (score > best.score) best = { intent: it.id, score: score, matched: matched };
    });
    return best;
  }

  /* ----------------------------------------------------------------- state */
  function createGame(CASE, DIALOGUES) {
    var F = byId(CASE.facts), EV = byId(CASE.evidence), ST = byId(CASE.statements);
    var LIES = CASE.lies, PZ = byId(CASE.puzzles), SUS = byId(CASE.suspects), CL = byId(CASE.clues);

    var state = {
      collected: [], clues: [], solved: [], inspected: [],
      presented: {}, broken: [], justBroken: [],
      statements: [], heardFacts: [],
      npc: {}, log: [], guardLog: [], turn: 0, contradictionsSeen: [], hintsUsed: {}
    };
    CASE.suspects.forEach(function (s) {
      state.presented[s.id] = [];
      state.npc[s.id] = { emotion: '침착', history: [], evasionIdx: 0, questions: 0 };
    });
    CASE.evidence.forEach(function (e) { if (e.start) state.collected.push(e.id); });

    /* ---- Condition DSL ---- */
    function evalCond(c) {
      if (!c) return true;
      if (c.always) return true;
      if (c.all) return c.all.every(evalCond);
      if (c.any) return c.any.some(evalCond);
      if (c.not) return !evalCond(c.not);
      if (c.ev) return state.collected.indexOf(c.ev) !== -1;
      if (c.clue) return state.clues.indexOf(c.clue) !== -1;
      if (c.puzzle) return state.solved.indexOf(c.puzzle) !== -1;
      if (c.presented) return state.presented[c.presented[0]].indexOf(c.presented[1]) !== -1;
      if (c.broken) return state.broken.indexOf(c.broken) !== -1;
      if (c.just_broken) return state.justBroken.indexOf(c.just_broken) !== -1;
      if (c.heard) return state.statements.indexOf(c.heard) !== -1;
      throw new Error('Unknown condition: ' + JSON.stringify(c));
    }

    /* ---- KnowledgeScope.build(session, npc) ---- */
    function scope(npcId) {
      var s = {};
      CASE.facts.forEach(function (f) {
        if (f.public) s[f.id] = 'public';
        else if (f.never_reveal) return; // 범인 전용 사실: NPC가 알고는 있어도 말할 수 있는 스코프에는 절대 넣지 않는다
        else if (f.known_by.indexOf(npcId) !== -1 && (!f.reveal_when || evalCond(f.reveal_when))) s[f.id] = f.reveal_when ? 'secret-unlocked' : 'own';
        else if (f.evidence && state.presented[npcId].indexOf(f.evidence) !== -1) s[f.id] = 'presented';
      });
      return s;
    }

    /* ---- 출력 가드 ---- */
    function guard(npcId, variant) {
      var sc = scope(npcId), violations = [];
      (variant.facts || []).forEach(function (fid) {
        if (!sc[fid]) violations.push({ fact: fid, rule: 'scope', detail: fid + '는 이 NPC의 현재 스코프 밖' });
      });
      var n = normalize(variant.text);
      CASE.facts.forEach(function (f) {
        if (!f.canaries || sc[f.id]) return;
        f.canaries.forEach(function (k) {
          if (n.indexOf(normalize(k)) !== -1) violations.push({ fact: f.id, rule: 'canary', detail: '카나리 "' + k + '" 감지 (' + f.id + ')' });
        });
      });
      return violations;
    }

    function evasion(npcId) {
      var d = DIALOGUES[npcId], st = state.npc[npcId];
      var t = d.evasions[st.evasionIdx % d.evasions.length];
      st.evasionIdx++;
      return t;
    }

    function pickVariant(list) {
      if (!list) return null;
      for (var i = 0; i < list.length; i++) if (evalCond(list[i].when)) return list[i];
      return null;
    }

    function contradictions() {
      return CASE.contradictions.filter(function (c) {
        var aHeard = state.statements.indexOf(c.a) !== -1;
        var bOk = c.b.evidence ? state.collected.indexOf(c.b.evidence) !== -1 : state.statements.indexOf(c.b.statement) !== -1;
        return aHeard && bOk;
      }).map(function (c) {
        var lie = LIES.filter(function (l) { return l.statement === c.a; })[0];
        return { id: c.id, type: c.type, a: ST[c.a], b: c.b.evidence ? { evidence: EV[c.b.evidence] } : { statement: ST[c.b.statement] },
          explain: c.explain, npc: ST[c.a].npc, resolved: !!(lie && state.broken.indexOf(lie.id) !== -1), source: 'rule',
          lie: lie ? lie.id : null };
      });
    }

    /* 응답 확정 + 상태 갱신 (update_state) */
    function finalize(npcId, kind, input, variant, meta) {
      var violations = variant ? guard(npcId, variant) : [];
      var blocked = violations.length > 0;
      var text, facts = [], claim = null;
      if (!variant) { text = evasion(npcId); }
      else if (blocked) { text = evasion(npcId); }
      else { text = variant.text; facts = variant.facts || []; claim = variant.claim || null; }

      var npc = state.npc[npcId];
      if (variant && variant.emotion) npc.emotion = variant.emotion;
      var newStatement = null;
      if (claim && state.statements.indexOf(claim) === -1) { state.statements.push(claim); newStatement = ST[claim]; }
      facts.forEach(function (f) { if (state.heardFacts.indexOf(f) === -1) state.heardFacts.push(f); });

      var before = state.contradictionsSeen.slice();
      var cs = contradictions();
      var fresh = cs.filter(function (c) { return before.indexOf(c.id) === -1; });
      fresh.forEach(function (c) { state.contradictionsSeen.push(c.id); });

      var g = { stage: meta.inputBlocked ? 'input' : 'output', blocked: blocked || !!meta.inputBlocked, violations: violations };
      if (g.blocked) state.guardLog.push({ turn: state.turn, npc: npcId, input: input, stage: g.stage, violations: violations, draft: variant && variant.draft });

      var res = {
        npc: npcId, kind: kind, input: input, text: text, emotion: npc.emotion,
        intent: meta.intent, score: meta.score, matched: meta.matched || [],
        revealed_fact_ids: facts, guard: g, newStatement: newStatement,
        newContradictions: fresh, brokenLies: meta.brokenLies || [], note: meta.note || null,
        draftText: blocked && variant ? variant.text : null
      };
      npc.history.push(res);
      state.log.push(res);
      state.justBroken = [];
      return res;
    }

    function ask(npcId, text) {
      if (!SUS[npcId]) throw new Error('unknown npc');
      state.turn++;
      state.npc[npcId].questions++;
      var c = classify(CASE, npcId, text);
      var d = DIALOGUES[npcId];
      var meta = { intent: c.intent, score: c.score, matched: c.matched };
      if (c.intent === 'inject') meta.inputBlocked = true;
      var list = d.intents[c.intent];
      var v = pickVariant(list);
      return finalize(npcId, 'ask', text, v, meta);
    }

    function present(npcId, evId) {
      if (state.collected.indexOf(evId) === -1) throw new Error('evidence not collected: ' + evId);
      state.turn++;
      var pres = state.presented[npcId];
      if (pres.indexOf(evId) === -1) pres.push(evId);
      var broken = [], note = null;
      LIES.forEach(function (l) {
        if (l.npc !== npcId || state.broken.indexOf(l.id) !== -1 || l.breaks_on.indexOf(evId) === -1) return;
        var heard = state.statements.indexOf(l.statement) !== -1;
        var enough = l.mode === 'all' ? l.breaks_on.every(function (e) { return pres.indexOf(e) !== -1; }) : true;
        if (!heard) { note = '이 증거는 이 사람의 어떤 진술과 부딪힐 것 같다. 먼저 그 진술을 끌어내 보자 (예: 그 시간의 행적).'; return; }
        if (!enough) {
          var missing = l.breaks_on.filter(function (e) { return pres.indexOf(e) === -1; });
          var have = missing.filter(function (e) { return state.collected.indexOf(e) !== -1; });
          note = '흔들리고 있다. 진술 「' + l.claim + '」을 무너뜨리려면 증거가 하나 더 필요하다' + (have.length ? ' (이미 가진 증거 중에 있다).' : '.');
          return;
        }
        state.broken.push(l.id); state.justBroken.push(l.id); broken.push(l.id);
      });
      var d = DIALOGUES[npcId];
      var v = pickVariant(d.present[evId]) || pickVariant(d.present.default);
      return finalize(npcId, 'present', evId, v, { intent: 'present:' + evId, score: 0, brokenLies: broken, note: note });
    }

    /* ---- 현장 조사 ---- */
    function inspect(hotspotId) {
      var hs = null, scene = null;
      CASE.scenes.forEach(function (sc) { sc.hotspots.forEach(function (h) { if (h.id === hotspotId) { hs = h; scene = sc; } }); });
      if (!hs) throw new Error('unknown hotspot');
      var got = null;
      if (state.inspected.indexOf(hs.id) === -1) state.inspected.push(hs.id);
      if (hs.gives && hs.gives.evidence && state.collected.indexOf(hs.gives.evidence) === -1) { state.collected.push(hs.gives.evidence); got = { evidence: EV[hs.gives.evidence] }; }
      if (hs.gives && hs.gives.clue && state.clues.indexOf(hs.gives.clue) === -1) { state.clues.push(hs.gives.clue); got = { clue: CL[hs.gives.clue] }; }
      var before = state.contradictionsSeen.slice();
      var fresh = contradictions().filter(function (c) { return before.indexOf(c.id) === -1; });
      fresh.forEach(function (c) { state.contradictionsSeen.push(c.id); });
      return { hotspot: hs, scene: scene.id, got: got, puzzle: hs.puzzle || null, newContradictions: fresh };
    }

    /* ---- 퍼즐 ---- */
    function puzzleAvailable(pid) { return evalCond(PZ[pid].requires); }
    function attemptPuzzle(pid, answer) {
      var p = PZ[pid];
      if (state.solved.indexOf(pid) !== -1) return { ok: true, already: true };
      if (!puzzleAvailable(pid)) return { ok: false, locked: true };
      var ok = Array.isArray(p.answer) ? JSON.stringify(answer) === JSON.stringify(p.answer) : String(answer) === p.answer;
      if (!ok) return { ok: false };
      state.solved.push(pid);
      if (state.collected.indexOf(p.reward) === -1) state.collected.push(p.reward);
      var before = state.contradictionsSeen.slice();
      var fresh = contradictions().filter(function (c) { return before.indexOf(c.id) === -1; });
      fresh.forEach(function (c) { state.contradictionsSeen.push(c.id); });
      return { ok: true, unlocked: EV[p.reward], newContradictions: fresh };
    }
    function hint(pid) {
      var p = PZ[pid]; var i = state.hintsUsed[pid] || 0;
      state.hintsUsed[pid] = Math.min(i + 1, p.hints.length);
      return p.hints[Math.min(i, p.hints.length - 1)];
    }

    /* ---- 추리 채점 ---- */
    function score(sub) {
      var sol = CASE.solution, flags = [], parts = {};
      parts.culprit = sub.culprit === sol.culprit ? 40 : 0;
      parts.motive = sub.motive === sol.motive ? 20 : 0;
      var m = sub.method || [];
      var mc = m.filter(function (x) { return sol.method.indexOf(x) !== -1; }).length;
      var mw = m.length - mc;
      parts.method = Math.max(0, Math.round(mc * 20 / sol.method.length - mw * 5));
      var ev = (sub.evidence || []).filter(function (e) { return state.collected.indexOf(e) !== -1; });
      var keyHit = ev.filter(function (e) { return sol.key_evidence.indexOf(e) !== -1; });
      var red = ev.filter(function (e) { return EV[e].role === 'red_herring'; });
      parts.evidence = Math.max(0, keyHit.length * (20 / sol.key_evidence.length) - red.length * 5);
      red.forEach(function (e) { flags.push({ type: 'red_herring', text: EV[e].name + '은(는) 함정 증거다. 카드가 쓰였다는 사실만 보여 줄 뿐, 누가 썼는지는 증명하지 않는다.' }); });
      if (parts.culprit && keyHit.length === 0) flags.push({ type: 'unsupported_guess', text: '범인은 맞혔지만 그를 가리키는 핵심 증거를 하나도 연결하지 않았다 (증거 없는 정답).' });

      // 모순 검사: 고른 범인이 이미 확보한 증거/진술과 충돌하는가
      var penalty = 0;
      if (sub.culprit === 's02' && (state.collected.indexOf('ev-02') !== -1 || state.statements.indexOf('st-han-saw-park') !== -1)) {
        flags.push({ type: 'contradiction', text: '박도현은 21:08~21:20 후문에 있었다는 증거(영수증·꽁초, 한서윤의 목격)가 이미 있다. 이 추리는 확보한 증거와 모순된다.' }); penalty += 10;
      }
      if (sub.culprit === 's01' && state.broken.indexOf('lie-03') !== -1) {
        flags.push({ type: 'contradiction', text: '한서윤의 공백은 주차장 이직 통화로 설명됐고, 그녀에게는 모조품을 만들 수단(복원 기술·받침 접근)이 없다.' }); penalty += 10;
      }
      if (m.indexOf('ms-own-card') !== -1 && m.indexOf('ms-card') !== -1) {
        flags.push({ type: 'contradiction', text: '"자기 카드로 출입"과 "경비 카드 도용"을 동시에 골랐다. 서로 모순되는 수법이다.' }); penalty += 5;
      }
      var total = Math.max(0, Math.min(100, Math.round(parts.culprit + parts.motive + parts.method + parts.evidence - penalty)));
      var grade = total >= 90 ? 'S' : total >= 75 ? 'A' : total >= 55 ? 'B' : total >= 35 ? 'C' : 'F';
      var missed = sol.key_evidence.filter(function (e) { return keyHit.indexOf(e) === -1; }).map(function (e) {
        return { evidence: EV[e], collected: state.collected.indexOf(e) !== -1 };
      });
      return {
        total: total, grade: grade, parts: parts, penalty: penalty, flags: flags, correct: sub.culprit === sol.culprit,
        missed: missed, solution: sol, culprit: SUS[sol.culprit],
        stats: { turns: state.turn, broken: state.broken.length, lies: LIES.length, contradictions: contradictions().length,
          totalContradictions: CASE.contradictions.length, guardBlocks: state.guardLog.length, collected: state.collected.length, totalEvidence: CASE.evidence.length }
      };
    }

    return {
      state: state, evalCond: evalCond, scope: scope, guard: guard, ask: ask, present: present,
      inspect: inspect, attemptPuzzle: attemptPuzzle, puzzleAvailable: puzzleAvailable, hint: hint,
      contradictions: contradictions, score: score,
      classify: function (npcId, t) { return classify(CASE, npcId, t); }
    };
  }

  /* --------------------------------------------------------- Case Validator */
  function validateCase(CASE) {
    var out = [];
    function rule(id, name, ok, detail) { out.push({ id: id, name: name, ok: !!ok, detail: detail }); }
    var F = byId(CASE.facts), EV = byId(CASE.evidence), LOC = byId(CASE.locations), SUS = byId(CASE.suspects);
    var ST = byId(CASE.statements), PZ = byId(CASE.puzzles), CL = byId(CASE.clues);

    // V01 참조 무결성
    var bad = [];
    CASE.facts.forEach(function (f) { (f.known_by || []).forEach(function (n) { if (!SUS[n]) bad.push(f.id + '→' + n); }); if (f.evidence && !EV[f.evidence]) bad.push(f.id + '→' + f.evidence); });
    CASE.evidence.forEach(function (e) { if (!LOC[e.location]) bad.push(e.id + '→' + e.location); e.proves.forEach(function (f) { if (!F[f]) bad.push(e.id + '→' + f); }); });
    CASE.lies.forEach(function (l) { if (!F[l.fact] || !ST[l.statement]) bad.push(l.id); l.breaks_on.forEach(function (e) { if (!EV[e]) bad.push(l.id + '→' + e); }); });
    CASE.statements.forEach(function (s) { if (!F[s.fact] || !SUS[s.npc]) bad.push(s.id); });
    CASE.timeline.forEach(function (t) { if (!SUS[t.actor] || !LOC[t.location]) bad.push(t.id); });
    CASE.solution.key_evidence.concat(CASE.solution.acceptable_evidence).forEach(function (e) { if (!EV[e]) bad.push('solution→' + e); });
    if (!SUS[CASE.solution.culprit]) bad.push('solution.culprit');
    rule('V01', '참조 ID 무결성', bad.length === 0, bad.length ? '깨진 참조: ' + bad.join(', ') : '모든 fact/evidence/location/suspect 참조 존재');

    // 발견 가능성: 시작 상태에서 도달 가능한 단서/퍼즐 고정점 계산
    var clues = {}, solved = {}, changed = true;
    CASE.scenes.forEach(function (sc) { sc.hotspots.forEach(function (h) { if (h.gives && h.gives.clue) clues[h.gives.clue] = true; }); });
    function reach(c) {
      if (!c) return true; if (c.always) return true;
      if (c.all) return c.all.every(reach); if (c.any) return c.any.some(reach);
      if (c.clue) return !!clues[c.clue]; if (c.puzzle) return !!solved[c.puzzle];
      return true;
    }
    while (changed) { changed = false; CASE.puzzles.forEach(function (p) { if (!solved[p.id] && reach(p.requires)) { solved[p.id] = true; changed = true; } }); }
    var sceneEv = {};
    CASE.scenes.forEach(function (sc) { sc.hotspots.forEach(function (h) { if (h.gives && h.gives.evidence) sceneEv[h.gives.evidence] = true; }); });
    function discoverable(eid) {
      var e = EV[eid]; if (!e) return false;
      if (e.start) return true;
      if (e.discoverable.always) return !!sceneEv[eid];
      if (e.discoverable.puzzle) return !!solved[e.discoverable.puzzle] && PZ[e.discoverable.puzzle].reward === eid;
      return false;
    }
    var undisc = CASE.solution.key_evidence.filter(function (e) { return !discoverable(e); });
    rule('V02', '핵심 증거 발견 가능', undisc.length === 0, undisc.length ? '발견 불가: ' + undisc.join(', ') : '핵심 증거 ' + CASE.solution.key_evidence.length + '개 모두 시작 상태에서 도달 가능');

    // V03 퍼즐 선행조건 순환 / 도달
    var unreachable = CASE.puzzles.filter(function (p) { return !solved[p.id]; }).map(function (p) { return p.id; });
    rule('V03', '퍼즐 선행조건 순환 없음 · 전부 도달', unreachable.length === 0, unreachable.length ? '도달 불가: ' + unreachable.join(', ') : '퍼즐 ' + CASE.puzzles.length + '개 모두 도달 가능');

    // V04 퍼즐 정답 유일성
    var v04 = [];
    CASE.puzzles.forEach(function (p) {
      var count = 0;
      if (p.type === 'sequence') {
        var times = p.items.map(function (it) { return it.clock[0] * 60 + it.clock[1]; });
        var distinct = uniq(times).length === times.length;
        var sorted = p.items.slice().sort(function (a, b) { return (a.clock[0] * 60 + a.clock[1]) - (b.clock[0] * 60 + b.clock[1]); }).map(function (x) { return x.id; });
        count = distinct && JSON.stringify(sorted) === JSON.stringify(p.answer) ? 1 : (distinct ? 0 : 2);
      } else if (p.type === 'code') {
        var y = p.constraint.years, pad = function (n) { return ('0' + (n % 100)).slice(-2); };
        for (var i = 0; i < 10000; i++) { var code = ('000' + i).slice(-4); if (code.slice(0, 2) === pad(y.founded) && code.slice(2) === pad(y.star)) { count++; if (code !== p.answer) count += 100; } }
      } else if (p.type === 'arrangement') {
        var re = new RegExp(p.pattern);
        permute(p.items).forEach(function (perm) {
          if (re.test(perm.map(function (x) { return x.label; }).join(''))) { count++; if (JSON.stringify(perm.map(function (x) { return x.id; })) !== JSON.stringify(p.answer)) count += 100; }
        });
      }
      v04.push(p.id + ': 해 ' + (count === 1 ? '1개' : count + ' (오류)'));
      if (count !== 1) v04.bad = true;
    });
    rule('V04', '퍼즐 정답 유일', !v04.bad, v04.join(' · '));

    // V05 시작 정보만으로 범인 특정 불가
    var startSubjects = [];
    CASE.evidence.forEach(function (e) { if (e.start) startSubjects = startSubjects.concat(e.subjects || []); });
    var pubTimeline = CASE.timeline.filter(function (t) { return t.public && t.crime; });
    var v05 = startSubjects.indexOf(CASE.solution.culprit) === -1 && pubTimeline.length === 0;
    rule('V05', '시작 정보만으로 범인 특정 불가', v05, v05 ? '브리핑·시작 증거에 범인을 가리키는 정보 없음' : '시작 정보가 범인을 직접 가리킴');

    // V06 거짓말마다 깨뜨릴 증거 존재
    var v06 = CASE.lies.filter(function (l) { return !l.breaks_on.length || !l.breaks_on.every(discoverable); }).map(function (l) { return l.id; });
    rule('V06', '모든 거짓말에 발견 가능한 반증', v06.length === 0, v06.length ? '반증 없음: ' + v06.join(', ') : '거짓말 ' + CASE.lies.length + '개 모두 반증 가능');

    // V07 비밀 공개 조건 충족 가능
    var breakable = {};
    CASE.lies.forEach(function (l) { if (l.breaks_on.every(discoverable)) breakable[l.id] = true; });
    function sat(c) {
      if (!c) return true;
      if (c.all) return c.all.every(sat); if (c.any) return c.any.some(sat);
      if (c.broken) return !!breakable[c.broken];
      if (c.presented) return discoverable(c.presented[1]);
      return true;
    }
    var v07 = CASE.facts.filter(function (f) { return f.reveal_when && !sat(f.reveal_when); }).map(function (f) { return f.id; });
    rule('V07', '비밀 공개 조건 충족 가능', v07.length === 0, v07.length ? '충족 불가: ' + v07.join(', ') : CASE.facts.filter(function (f) { return f.reveal_when; }).length + '개 비밀 모두 공개 가능');

    // T01 동시에 두 장소 금지
    var t01 = [];
    var byActor = {};
    CASE.timeline.forEach(function (t) { (byActor[t.actor] = byActor[t.actor] || []).push(t); });
    Object.keys(byActor).forEach(function (a) {
      var ev = byActor[a];
      for (var i = 0; i < ev.length; i++) for (var j = i + 1; j < ev.length; j++) {
        var x = ev[i], y = ev[j];
        if (x.location !== y.location && toMin(x.start) < toMin(y.end) && toMin(y.start) < toMin(x.end)) t01.push(x.id + '×' + y.id);
      }
    });
    rule('T01', '한 사람이 같은 시간에 두 장소에 없음', t01.length === 0, t01.length ? '충돌: ' + t01.join(', ') : '시간선 ' + CASE.timeline.length + '개 이벤트 충돌 없음');

    // T03 이동 가능성 (최단 이동시간)
    function dist(a, b) {
      if (a === b) return 0;
      var d = {}, done = {}; CASE.locations.forEach(function (l) { d[l.id] = Infinity; }); d[a] = 0;
      var adj = {}; CASE.locations.forEach(function (l) { adj[l.id] = adj[l.id] || {}; Object.keys(l.adj).forEach(function (k) { adj[l.id][k] = l.adj[k]; adj[k] = adj[k] || {}; adj[k][l.id] = Math.min(adj[k][l.id] || Infinity, l.adj[k]); }); });
      for (;;) {
        var u = null; Object.keys(d).forEach(function (k) { if (!done[k] && (u === null || d[k] < d[u])) u = k; });
        if (u === null || d[u] === Infinity) break; done[u] = true;
        Object.keys(adj[u] || {}).forEach(function (v) { if (d[u] + adj[u][v] < d[v]) d[v] = d[u] + adj[u][v]; });
      }
      return d[b];
    }
    var t03 = [];
    Object.keys(byActor).forEach(function (a) {
      var ev = byActor[a].slice().sort(function (x, y) { return toMin(x.start) - toMin(y.start); });
      for (var i = 1; i < ev.length; i++) {
        var gap = toMin(ev[i].start) - toMin(ev[i - 1].end), need = dist(ev[i - 1].location, ev[i].location);
        if (gap < need) t03.push(ev[i - 1].id + '→' + ev[i].id + ' (' + gap + '분 < ' + need + '분)');
      }
    });
    rule('T03', '장소 간 이동 시간 충족', t03.length === 0, t03.length ? '불가능한 이동: ' + t03.join(', ') : '모든 연속 이동이 최소 이동시간 이상');

    // U01 유일 범인: 기회 ∧ 수단 ∧ 증거 체인
    var win = CASE.crime.window.map(toMin), crimeLocs = [CASE.crime.location, 'loc-vault'];
    var need = uniq(CASE.solution.key_evidence.map(function (e) { return EV[e].establishes; }));
    function analyse(keyEv) {
      return CASE.suspects.map(function (s) {
        var evs = byActor[s.id] || [];
        var atScene = evs.some(function (t) { return crimeLocs.indexOf(t.location) !== -1 && toMin(t.start) <= win[1] && toMin(t.end) >= win[0]; });
        var alibi = evs.some(function (t) { return crimeLocs.indexOf(t.location) === -1 && toMin(t.start) <= win[0] && toMin(t.end) >= win[1]; });
        var opportunity = atScene || !alibi;
        var means = !!(s.means.replica && s.means.access_case);
        var covered = uniq(keyEv.filter(function (e) { return (EV[e].subjects || []).indexOf(s.id) !== -1; }).map(function (e) { return EV[e].establishes; }));
        var chain = need.every(function (k) { return covered.indexOf(k) !== -1; });
        return { id: s.id, opportunity: opportunity, means: means, chain: chain, all: opportunity && means && chain };
      });
    }
    var a = analyse(CASE.solution.key_evidence);
    var guilty = a.filter(function (x) { return x.all; }).map(function (x) { return x.id; });
    rule('U01', '기회∧수단∧증거를 모두 만족하는 용의자가 범인 하나뿐', guilty.length === 1 && guilty[0] === CASE.solution.culprit,
      a.map(function (x) { return SUS[x.id].name + ' ' + (x.opportunity ? '기회○' : '기회×') + (x.means ? '수단○' : '수단×') + (x.chain ? '증거○' : '증거×'); }).join(' · '));

    // U02 핵심 증거가 하나라도 빠지면 U01이 깨진다
    var notNeeded = CASE.solution.key_evidence.filter(function (e) {
      var rest = CASE.solution.key_evidence.filter(function (x) { return x !== e; });
      return analyse(rest).filter(function (x) { return x.all; }).length === 1;
    });
    rule('U02', '핵심 증거는 모두 필수 (최소 증명 집합)', notNeeded.length === 0, notNeeded.length ? '없어도 되는 증거: ' + notNeeded.join(', ') : '어느 하나를 빼도 유일 범인 증명이 깨짐');

    // G01 누설 가드 정적 점검: never_reveal fact에는 카나리가 있어야 한다
    var noCanary = CASE.facts.filter(function (f) { return f.never_reveal && !(f.canaries && f.canaries.length); }).map(function (f) { return f.id; });
    rule('G01', '누설 금지 fact마다 카나리 키워드 정의', noCanary.length === 0, noCanary.length ? '카나리 없음: ' + noCanary.join(', ') : CASE.facts.filter(function (f) { return f.never_reveal; }).length + '개 금지 fact 모두 카나리 보유');

    return { ok: out.every(function (r) { return r.ok; }), rules: out };
  }

  function permute(arr) {
    if (arr.length <= 1) return [arr.slice()];
    var res = [];
    arr.forEach(function (x, i) {
      var rest = arr.slice(0, i).concat(arr.slice(i + 1));
      permute(rest).forEach(function (p) { res.push([x].concat(p)); });
    });
    return res;
  }

  return { createGame: createGame, validateCase: validateCase, classify: classify, normalize: normalize, INTENTS: INTENTS, toMin: toMin };
});
