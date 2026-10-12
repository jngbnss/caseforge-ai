/*
 * CaseForge AI — Case Bible: museum-001 「사라진 푸른 다이아몬드」
 * docs/mvp-proposal.md 5절을 그대로 데이터로 옮긴 것이다.
 *
 * 주의: 이 정적 데모는 서버가 없으므로 정답(solution)과 퍼즐 정답이 브라우저 번들에 들어 있다.
 * 실제 설계에서는 Bible 전체를 서버만 보관하고 클라이언트에는 공개된 부분만 보낸다 (제안서 6절).
 */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.CASE = factory();
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  var C = {
    case_id: 'museum-001',
    title: '사라진 푸른 다이아몬드',
    briefing: {
      place: '한빛시립박물관 2층 특별전시실',
      when: '사건 전날 밤 20:30 폐관 이후',
      summary:
        '개장 전 정기 감정에서, 전시 중이던 "푸른 별" 다이아몬드가 정교한 모조품으로 확인됐다. ' +
        '진열장은 잠겨 있었고 깨진 흔적도 없다. 폐관 후 관내에 남아 있던 사람은 단 세 명이다.',
      goals: [
        '현장을 조사해 증거를 모은다',
        '퍼즐을 풀어 잠긴 기록을 연다',
        '세 사람을 심문하고, 증거를 제시해 거짓말을 무너뜨린다',
        '범인 · 동기 · 수법 · 핵심 증거를 모순 없이 제출한다'
      ],
      crime_window: '21:00 ~ 21:30 사이로 추정'
    },

    locations: [
      { id: 'loc-gallery', name: '2층 특별전시실', adj: { 'loc-vault': 1, 'loc-lounge': 3, 'loc-restoration': 4, 'loc-security': 3 } },
      { id: 'loc-vault', name: '수장고 출입문', adj: { 'loc-gallery': 1, 'loc-restoration': 3, 'loc-lounge': 2 } },
      { id: 'loc-restoration', name: '복원실', adj: { 'loc-lounge': 2, 'loc-vault': 3, 'loc-gallery': 4 } },
      { id: 'loc-lounge', name: '직원 휴게실', adj: { 'loc-restoration': 2, 'loc-smoking': 1, 'loc-gallery': 3, 'loc-security': 2, 'loc-vault': 2 } },
      { id: 'loc-smoking', name: '후문 흡연 구역', adj: { 'loc-lounge': 1, 'loc-parking': 2 } },
      { id: 'loc-security', name: '보안실', adj: { 'loc-lounge': 2, 'loc-gallery': 3 } },
      { id: 'loc-office', name: '큐레이터 사무실', adj: { 'loc-gallery': 2, 'loc-parking': 4 } },
      { id: 'loc-parking', name: '직원 주차장', adj: { 'loc-smoking': 2, 'loc-office': 4 } }
    ],

    suspects: [
      {
        id: 's01', name: '한서윤', role: '수석 큐레이터', age: 41, aliases: ['큐레이터'], color: '#6b5b95',
        persona: '정중하고 논리적이다. 말을 고르며, 몰리면 차가워진다.',
        surface: '20:50 ~ 21:25 행방이 확인되지 않는다.',
        means: { access_case: false, replica: false, cctv: false }
      },
      {
        id: 's02', name: '박도현', role: '야간 경비원 (12년차)', age: 56, aliases: ['경비원', '경비아저씨'], color: '#3f7d6e',
        persona: '투박하고 솔직한 편이다. 당황하면 "아이고"가 먼저 나온다.',
        surface: '21:12 그의 출입 카드로 수장고 문이 열렸다.',
        means: { access_case: true, replica: false, cctv: true }
      },
      {
        id: 's03', name: '윤재민', role: '보존 복원가', age: 34, aliases: ['복원가'], color: '#a0522d',
        persona: '조용하고 정확하다. 전문 용어를 쓰고, 긴장하면 설명이 길어진다.',
        surface: '복원실에서 혼자 야근 중이었다고 말한다.',
        means: { access_case: true, replica: true, cctv: true }
      }
    ],

    /* ---------------- Facts ----------------
       kind: truth | testimony | lie | record
       never_reveal: 해당 NPC가 어떤 상황에서도 직접 말해서는 안 되는 사실 (출력 가드 카나리 적용)
       reveal_when: Secret 조건. 충족되기 전에는 그 NPC의 스코프에 들어오지 않는다. */
    facts: [
      { id: 'f-01', kind: 'truth', content: '20:30 폐관. 관내에는 한서윤, 박도현, 윤재민 세 사람만 남았다.', known_by: ['s01', 's02', 's03'], public: true },
      { id: 'f-02', kind: 'truth', content: '"푸른 별"이 정교한 모조품으로 확인됐다.', known_by: ['s01', 's02', 's03'], public: true },
      { id: 'f-03', kind: 'truth', content: '한서윤은 20:50~21:25 주차장 차 안에서 경쟁 경매사와 이직 면접 통화를 했다.', known_by: ['s01'], reveal_when: { broken: 'lie-03' }, time: ['20:50', '21:25'], location: 'loc-parking', subjects: ['s01'] },
      { id: 'f-04', kind: 'truth', content: '박도현은 21:00에 전시실 마지막 순찰을 돌았다.', known_by: ['s02'] },
      { id: 'f-05', kind: 'truth', content: '박도현은 21:05 카드를 휴게실 사물함 3번에 두고, 21:07 커피를 산 뒤 21:08~21:20 후문에서 담배를 피웠다.', known_by: ['s02'], reveal_when: { broken: 'lie-02' }, subjects: ['s02'] },
      { id: 'f-06', kind: 'truth', content: '21:08 윤재민이 복원실 단말로 CCTV를 점검 모드로 전환했다.', known_by: ['s03'], never_reveal: true, canaries: ['점검모드로바꿨', '점검모드로전환했', '점검모드로돌렸', '녹화를껐'] },
      { id: 'f-07', kind: 'truth', content: '21:10 윤재민이 휴게실 사물함 3번에서 박도현의 카드를 가져갔다.', known_by: ['s03'], never_reveal: true, canaries: ['카드를꺼냈', '카드를가져갔', '카드를가져왔', '카드를빌렸', '카드를썼'] },
      { id: 'f-08', kind: 'truth', content: '21:12 윤재민이 박도현의 카드로 수장고 문을 열고 전시실에 들어갔다.', known_by: ['s03'], never_reveal: true, canaries: ['카드로들어갔', '수장고로들어갔', '수장고에들어갔'] },
      { id: 'f-09', kind: 'truth', content: '21:14 윤재민이 진품을 모조품으로 바꿔치기했다.', known_by: ['s03'], never_reveal: true, canaries: ['바꿔치기', '바꿔놓', '21:14', '9시14분'] },
      { id: 'f-10', kind: 'truth', content: '윤재민은 3주 전 받침 세척 작업 때 실리콘 몰드로 본을 떠 모조품을 만들었다.', known_by: ['s03'], never_reveal: true, canaries: ['본을떴', '본떠', '모조품을만들', '모조품을주문'] },
      { id: 'f-11', kind: 'truth', content: '윤재민은 도박 빚이 있고, 개인 수집가에게서 제안을 받았다.', known_by: ['s03'], reveal_when: { presented: ['s03', 'rec-02'] }, canaries: ['도박', '수집가'] },
      { id: 'f-12', kind: 'lie', content: '윤재민: "21시대에는 복원실에서 한 번도 나가지 않았다."', known_by: ['s03'] },
      { id: 'f-13', kind: 'record', content: '출입 로그: 21:12 박도현 카드로 수장고 문 개방.', known_by: [], evidence: 'ev-01' },
      { id: 'f-14', kind: 'record', content: '출입 로그: 큐레이터 사무실 문은 20:40~21:40 한 번도 열리지 않았다.', known_by: [], evidence: 'ev-01' },
      { id: 'f-15', kind: 'record', content: '21:07 휴게실 자판기 영수증과 후문 흡연 구역의 꽁초.', known_by: [], evidence: 'ev-02' },
      { id: 'f-16', kind: 'record', content: '복원실 쓰레기통의 실리콘 몰드 조각. 안쪽 면에 보석 커팅 자국이 찍혀 있다.', known_by: [], evidence: 'ev-03' },
      { id: 'f-17', kind: 'record', content: '진열장 받침의 연마 가루와 복원용 니트릴 장갑 섬유.', known_by: [], evidence: 'ev-04' },
      { id: 'f-18', kind: 'record', content: '분광 감정서: 진열장 속 "푸른 별"은 합성 스피넬 모조품.', known_by: [], evidence: 'ev-05' },
      { id: 'f-19', kind: 'record', content: '21:08~21:16 전 채널 녹화 공백. 공백 직전 복원실 단말(윤재민 계정) 로그인.', known_by: [], evidence: 'rec-01' },
      { id: 'f-20', kind: 'record', content: '윤재민 앞으로 온 채무 독촉장.', known_by: [], evidence: 'rec-02' },
      { id: 'f-21', kind: 'record', content: '윤재민 필체의 메모: "21:10 휴게실 — 사물함 3번".', known_by: [], evidence: 'rec-03' },
      { id: 'f-22', kind: 'lie', content: '박도현: "21시부터 계속 경비실(보안실)에 있었다."', known_by: ['s02'] },
      { id: 'f-23', kind: 'lie', content: '한서윤: "사무실에서 도록 교정을 하고 있었다."', known_by: ['s01'] },
      { id: 'f-24', kind: 'testimony', content: '한서윤: 21:10쯤 주차장에서 후문 쪽에 담배 피우는 박도현을 봤다.', known_by: ['s01'], reveal_when: { broken: 'lie-03' }, subjects: ['s02'] },
      { id: 'f-25', kind: 'testimony', content: '박도현: 휴게실 사물함 3번은 잠금이 고장 나 그냥 열린다.', known_by: ['s02'], reveal_when: { broken: 'lie-02' } },
      { id: 'f-26', kind: 'testimony', content: '박도현: 요즘 윤재민이 복도에서 돈 문제로 통화하는 걸 들었다. 커피 마시러 휴게실에 자주 온다.', known_by: ['s02'], reveal_when: { broken: 'lie-02' }, subjects: ['s03'] },
      { id: 'f-27', kind: 'testimony', content: '한서윤: 3주 전 "푸른 별" 받침 세척을 윤재민이 맡았다. 그때 진열장 열쇠를 잠시 관리했다.', known_by: ['s01'], subjects: ['s03'] },
      { id: 'f-28', kind: 'lie', content: '윤재민: "CCTV는 보안실 소관이라 손댄 적 없다."', known_by: ['s03'] },
      { id: 'f-29', kind: 'testimony', content: '윤재민: (거짓말이 무너진 뒤) 21:10쯤 커피를 마시러 휴게실에 잠깐 갔을 뿐이다.', known_by: ['s03'], reveal_when: { broken: 'lie-01' } },
      { id: 'f-30', kind: 'testimony', content: '윤재민: 복원 작업에서 실리콘 몰드는 형태 기록용으로 늘 쓰는 재료다.', known_by: ['s03'] }
    ],

    /* 플레이어가 들으면 수사 노트에 자동 기록되는 진술 */
    statements: [
      { id: 'st-han-office', npc: 's01', fact: 'f-23', text: '"사무실에서 도록 교정을 하고 있었어요."', time: '20:50~21:25', location: 'loc-office' },
      { id: 'st-han-parking', npc: 's01', fact: 'f-03', text: '"주차장 차 안에서 경매사와 이직 면접 통화를 했습니다."', time: '20:50~21:25', location: 'loc-parking' },
      { id: 'st-han-saw-park', npc: 's01', fact: 'f-24', text: '"21:10쯤 후문에서 박도현 씨가 담배 피우는 걸 봤어요."', time: '21:10', location: 'loc-smoking' },
      { id: 'st-han-yoon-base', npc: 's01', fact: 'f-27', text: '"3주 전 받침 세척을 윤재민 씨가 맡았어요. 진열장 열쇠도 그때 잠시 관리했죠."' },
      { id: 'st-park-guardroom', npc: 's02', fact: 'f-22', text: '"9시부터 쭉 경비실에 있었습니다."', time: '21:00~21:30', location: 'loc-security' },
      { id: 'st-park-smoking', npc: 's02', fact: 'f-05', text: '"카드는 사물함 3번에 두고, 후문에서 담배를 피웠어요. 21:08부터 21:20까지."', time: '21:08~21:20', location: 'loc-smoking' },
      { id: 'st-park-locker', npc: 's02', fact: 'f-25', text: '"사물함 3번은 잠금이 고장 나서 그냥 열려요."' },
      { id: 'st-park-yoon', npc: 's02', fact: 'f-26', text: '"재민 씨가 요즘 돈 문제로 통화하는 걸 들었어요. 커피 마시러 휴게실에 자주 오고요."' },
      { id: 'st-yoon-room', npc: 's03', fact: 'f-12', text: '"9시대엔 복원실에서 한 번도 안 나갔습니다."', time: '21:00~21:30', location: 'loc-restoration' },
      { id: 'st-yoon-cctv', npc: 's03', fact: 'f-28', text: '"CCTV는 보안실 소관이라 손댄 적 없습니다."' },
      { id: 'st-yoon-coffee', npc: 's03', fact: 'f-29', text: '"21:10쯤 커피 마시러 휴게실에 잠깐 갔을 뿐입니다."', time: '21:10', location: 'loc-lounge' },
      { id: 'st-yoon-mold', npc: 's03', fact: 'f-30', text: '"실리콘 몰드는 형태 기록용으로 늘 쓰는 재료예요."' }
    ],

    lies: [
      { id: 'lie-01', npc: 's03', fact: 'f-12', statement: 'st-yoon-room', claim: '21시대에 복원실에서 나가지 않았다', breaks_on: ['rec-03', 'ev-04'], mode: 'all' },
      { id: 'lie-02', npc: 's02', fact: 'f-22', statement: 'st-park-guardroom', claim: '21시부터 계속 경비실에 있었다', breaks_on: ['ev-02'], mode: 'any' },
      { id: 'lie-03', npc: 's01', fact: 'f-23', statement: 'st-han-office', claim: '사무실에서 도록 교정을 했다', breaks_on: ['ev-01'], mode: 'any' },
      { id: 'lie-04', npc: 's03', fact: 'f-28', statement: 'st-yoon-cctv', claim: 'CCTV에 손댄 적 없다', breaks_on: ['rec-01'], mode: 'any' }
    ],

    /* 규칙 기반 모순 탐지 정의. a는 진술, b는 증거 또는 다른 진술. */
    contradictions: [
      { id: 'c-01', type: '장소', a: 'st-yoon-room', b: { evidence: 'rec-03' }, explain: '복원실을 떠나지 않았다면서, 본인 필체 메모에는 "21:10 휴게실 — 사물함 3번"이라는 약속이 적혀 있다.' },
      { id: 'c-02', type: '물리 흔적', a: 'st-yoon-room', b: { evidence: 'ev-04' }, explain: '복원실에만 있었다는데, 전시실 진열장 받침에서 복원용 니트릴 장갑 섬유가 나왔다.' },
      { id: 'c-03', type: '장소', a: 'st-park-guardroom', b: { evidence: 'ev-02' }, explain: '경비실에 계속 있었다면서, 21:07 휴게실 영수증과 후문 꽁초가 나왔다.' },
      { id: 'c-04', type: '출입 기록', a: 'st-han-office', b: { evidence: 'ev-01' }, explain: '사무실에서 일했다면서, 출입 로그상 사무실 문은 20:40~21:40 한 번도 열리지 않았다.' },
      { id: 'c-05', type: '진술 대 진술', a: 'st-park-guardroom', b: { statement: 'st-han-saw-park' }, explain: '박도현은 경비실에 있었다고 했지만, 한서윤은 21:10쯤 후문에서 그를 봤다고 한다.' },
      { id: 'c-06', type: '시스템 기록', a: 'st-yoon-cctv', b: { evidence: 'rec-01' }, explain: 'CCTV에 손대지 않았다면서, 녹화 공백 직전 복원실 단말에 그의 계정이 로그인돼 있다.' }
    ],

    evidence: [
      { id: 'ev-01', name: '출입 로그', icon: '🗂', location: 'loc-security', role: 'red_herring', proves: ['f-13', 'f-14'], discoverable: { always: true },
        desc: '21:12 박도현의 카드로 수장고 문이 열렸다. 같은 시간대 큐레이터 사무실 문은 한 번도 열리지 않았다.', time: '21:12', subjects: ['s02', 's01'] },
      { id: 'ev-02', name: '자판기 영수증 · 꽁초', icon: '🧾', location: 'loc-smoking', role: 'supporting', proves: ['f-15'], discoverable: { always: true },
        desc: '휴게실 자판기 커피 영수증(21:07)과, 후문 흡연 구역에 떨어진 경비원과 같은 브랜드의 꽁초 여러 개.', time: '21:07', subjects: ['s02'] },
      { id: 'ev-03', name: '실리콘 몰드 조각', icon: '🧩', location: 'loc-restoration', role: 'key', establishes: 'means', proves: ['f-16'], discoverable: { always: true },
        desc: '복원실 쓰레기통 바닥에서 발견. 안쪽 면에 브릴리언트 커팅 자국이 찍혀 있다. 크기가 "푸른 별"과 같다.', subjects: ['s03'] },
      { id: 'ev-04', name: '연마 가루 · 장갑 섬유', icon: '🔬', location: 'loc-gallery', role: 'key', establishes: 'presence', proves: ['f-17'], discoverable: { always: true },
        desc: '진열장 받침 틈의 미세한 연마 가루, 그리고 복원실에서만 쓰는 청색 니트릴 장갑 섬유.', subjects: ['s03'] },
      { id: 'ev-05', name: '모조품 · 분광 감정서', icon: '💎', location: 'loc-gallery', role: 'supporting', proves: ['f-18'], discoverable: { always: true }, start: true,
        desc: '진열장 속 "푸른 별"은 합성 스피넬 모조품. 커팅 정밀도가 매우 높아 원석의 본을 떠야만 가능한 수준이다.' },
      { id: 'rec-01', name: 'CCTV 공백 기록', icon: '📼', location: 'loc-security', role: 'key', establishes: 'cctv', proves: ['f-19'], discoverable: { puzzle: 'pz-01' },
        desc: '21:08~21:16 모든 채널이 "점검 모드". 공백 직전, 복원실 단말에서 윤재민 계정이 로그인한 화면이 찍혔다.', time: '21:08', subjects: ['s03'] },
      { id: 'rec-02', name: '채무 독촉장', icon: '✉', location: 'loc-restoration', role: 'supporting', proves: ['f-20'], discoverable: { puzzle: 'pz-02' },
        desc: '복원실 개인 금고 속. 윤재민 앞으로 온 독촉장 석 장. 마지막 장에는 "이번 달 말까지"라고 적혀 있다.', subjects: ['s03'] },
      { id: 'rec-03', name: '찢어진 메모 (복원)', icon: '📝', location: 'loc-lounge', role: 'key', establishes: 'card', proves: ['f-21'], discoverable: { puzzle: 'pz-03' },
        desc: '조각을 맞추자 윤재민 필체로 "21:10 휴게실 — 사물함 3번"이라고 적혀 있다.', time: '21:10', subjects: ['s03'] }
    ],

    /* 증거가 아닌 단서 (퍼즐 재료) */
    clues: [
      { id: 'clue-cards', name: '전시 안내 카드 3장', desc: '「한빛시립박물관 1907년 개관」 「신관 증축 1962년」 「푸른 별, 1984년 이 도시에 기증」' },
      { id: 'clue-safe-note', name: '금고 옆 포스트잇', desc: '"숫자는 잊지 않게: 박물관이 문을 연 해, 그리고 별이 이곳에 온 해 — 각각 끝의 두 자리."' },
      { id: 'clue-memo-a', name: '메모 조각 A', desc: '복원실 서랍 틈에 낀 종이 조각 두 장.' },
      { id: 'clue-memo-b', name: '메모 조각 B', desc: '휴게실 휴지통 속 종이 조각 두 장. 같은 종이의 나머지 같다.' }
    ],

    scenes: [
      { id: 'loc-gallery', name: '2층 특별전시실', mood: '빈 진열장 위로 비상등만 켜져 있다.',
        hotspots: [
          { id: 'h-case', label: '진열장 받침', x: 50, y: 58, gives: { evidence: 'ev-04' }, text: '받침 틈에 고운 회색 가루가 끼어 있다. 핀셋으로 집어 보니 청색 섬유도 함께 나온다.' },
          { id: 'h-replica', label: '"푸른 별" 모조품', x: 50, y: 36, gives: { evidence: 'ev-05' }, text: '감정팀이 남긴 분광 감정서가 진열장 옆에 붙어 있다.' },
          { id: 'h-cards', label: '전시 안내 카드', x: 18, y: 30, gives: { clue: 'clue-cards' }, text: '벽에 걸린 안내 카드 세 장. 연도가 눈에 띈다.' },
          { id: 'h-floor', label: '바닥', x: 80, y: 80, text: '대리석 바닥은 깨끗하다. 강제로 침입한 흔적은 없다.' }
        ] },
      { id: 'loc-restoration', name: '복원실', mood: '약품 냄새. 작업대 위 스탠드가 아직 따뜻하다.',
        hotspots: [
          { id: 'h-trash', label: '쓰레기통', x: 20, y: 72, gives: { evidence: 'ev-03' }, text: '바닥에 말랑한 실리콘 조각이 있다. 안쪽에 정교한 각인이 남아 있다.' },
          { id: 'h-safe', label: '개인 금고', x: 82, y: 40, gives: { clue: 'clue-safe-note' }, puzzle: 'pz-02', text: '4자리 숫자 금고. 옆에 포스트잇이 붙어 있다.' },
          { id: 'h-drawer', label: '작업대 서랍', x: 50, y: 62, gives: { clue: 'clue-memo-a' }, text: '서랍 틈에 찢어진 종이 두 조각이 끼어 있다.' },
          { id: 'h-terminal', label: '작업 단말', x: 50, y: 30, text: '잠금 화면이다. 접속 기록은 보안실 쪽에서 확인할 수 있을 것 같다.' }
        ] },
      { id: 'loc-security', name: '보안실', mood: '모니터 열두 대가 푸르스름하게 깜박인다.',
        hotspots: [
          { id: 'h-log', label: '출입 로그 단말', x: 25, y: 45, gives: { evidence: 'ev-01' }, text: '어젯밤 출입 기록을 뽑았다.' },
          { id: 'h-cctv', label: 'CCTV 모니터', x: 70, y: 35, puzzle: 'pz-01', text: '녹화본에서 정지 화면 네 장을 추렸다. 순서가 뒤섞여 있다.' },
          { id: 'h-journal', label: '경비 일지', x: 70, y: 75, text: '"21:00 전시실 순찰 이상 무." 그 뒤로는 기록이 없다.' }
        ] },
      { id: 'loc-lounge', name: '휴게실 · 후문', mood: '자판기 불빛. 열린 후문 너머로 찬 바람이 들어온다.',
        hotspots: [
          { id: 'h-smoke', label: '후문 흡연 구역', x: 82, y: 55, gives: { evidence: 'ev-02' }, text: '꽁초 여러 개. 자판기 옆 휴지통에는 21:07 영수증.' },
          { id: 'h-locker', label: '사물함 3번', x: 22, y: 40, text: '잠금장치가 헐겁다. 손잡이를 당기기만 해도 열린다. 안은 비어 있다.' },
          { id: 'h-bin', label: '휴지통', x: 50, y: 72, gives: { clue: 'clue-memo-b' }, text: '구겨진 종이컵 사이에 찢어진 메모 조각 두 장.' }
        ] }
    ],

    puzzles: [
      { id: 'pz-01', title: 'CCTV 정지 화면 순서', type: 'sequence', location: 'loc-security', reward: 'rec-01',
        prompt: '네 장의 정지 화면을 벽시계가 가리키는 시간 순서대로 고르세요. (모두 오후 9시대)',
        requires: null,
        items: [
          { id: 'F-A', label: '휴게실 — 경비원이 자판기 앞에 서 있다', clock: [9, 7] },
          { id: 'F-B', label: '전시실 복도 — 손전등으로 진열장을 비춘다', clock: [9, 0] },
          { id: 'F-C', label: '모든 채널 — "점검 모드" 표시와 함께 화면 정지', clock: [9, 8], frozen: true },
          { id: 'F-D', label: '휴게실 — 경비원이 사물함을 닫는다', clock: [9, 5] }
        ],
        answer: ['F-B', 'F-D', 'F-A', 'F-C'],
        hints: ['시계의 짧은바늘은 모두 9 근처에 있다. 긴바늘만 보면 된다.', '긴바늘이 12(정각) → 1(5분) → 조금 더 → 더 조금 순서다.'] },
      { id: 'pz-02', title: '복원실 금고', type: 'code', location: 'loc-restoration', reward: 'rec-02',
        prompt: '4자리 비밀번호를 입력하세요.',
        requires: { all: [{ clue: 'clue-safe-note' }] },
        constraint: { years: { founded: 1907, extension: 1962, star: 1984 }, rule: 'last2(founded) + last2(star)' },
        answer: '0784',
        hints: ['포스트잇: "박물관이 문을 연 해, 그리고 별이 이곳에 온 해".', '전시실의 안내 카드에 연도가 있다. 1962년은 함정이다.'] },
      { id: 'pz-03', title: '찢어진 메모 맞추기', type: 'arrangement', location: 'loc-lounge', reward: 'rec-03',
        prompt: '조각을 올바른 순서로 이어 붙이세요.',
        requires: { all: [{ clue: 'clue-memo-a' }, { clue: 'clue-memo-b' }] },
        items: [
          { id: 'M-1', label: '실 — 사물' },
          { id: 'M-2', label: '21:1' },
          { id: 'M-3', label: '함 3번' },
          { id: 'M-4', label: '0 휴게' }
        ],
        pattern: '^\\d{2}:\\d{2} \\S+ — \\S+ \\d번$',
        answer: ['M-2', 'M-4', 'M-1', 'M-3'],
        hints: ['시간이 맨 앞에 온다.', '"휴게" 다음에 무엇이 와야 단어가 될까?'] }
    ],

    timeline: [
      { id: 'tl-00', start: '20:30', end: '20:46', actor: 's01', location: 'loc-office', action: '폐관 후 사무실 정리', public: true },
      { id: 'tl-01', start: '20:50', end: '21:25', actor: 's01', location: 'loc-parking', action: '주차장 차 안에서 경쟁 경매사와 이직 면접 통화', facts: ['f-03'] },
      { id: 'tl-02', start: '21:00', end: '21:02', actor: 's02', location: 'loc-gallery', action: '전시실 마지막 순찰', facts: ['f-04'] },
      { id: 'tl-03', start: '21:05', end: '21:07', actor: 's02', location: 'loc-lounge', action: '카드를 사물함 3번에 넣고 21:07 자판기 커피', facts: ['f-05'] },
      { id: 'tl-04', start: '21:08', end: '21:20', actor: 's02', location: 'loc-smoking', action: '후문에서 흡연 (근무지 이탈)', facts: ['f-05'] },
      { id: 'tl-05', start: '21:23', end: '21:30', actor: 's02', location: 'loc-security', action: '보안실 복귀' },
      { id: 'tl-06', start: '20:30', end: '21:08', actor: 's03', location: 'loc-restoration', action: '복원실 야근', public: true },
      { id: 'tl-07', start: '21:08', end: '21:08', actor: 's03', location: 'loc-restoration', action: '복원실 단말로 CCTV를 "점검 모드"로 전환', facts: ['f-06'], crime: true },
      { id: 'tl-08', start: '21:10', end: '21:10', actor: 's03', location: 'loc-lounge', action: '사물함 3번에서 박도현의 카드를 꺼냄', facts: ['f-07'], crime: true },
      { id: 'tl-09', start: '21:12', end: '21:12', actor: 's03', location: 'loc-vault', action: '박도현 카드로 수장고 문 개방', facts: ['f-08'], crime: true },
      { id: 'tl-10', start: '21:14', end: '21:14', actor: 's03', location: 'loc-gallery', action: '진품을 몰드로 만든 모조품과 바꿔치기', facts: ['f-09'], crime: true },
      { id: 'tl-11', start: '21:18', end: '21:18', actor: 's03', location: 'loc-lounge', action: '카드를 사물함에 반납', crime: true },
      { id: 'tl-12', start: '21:21', end: '21:30', actor: 's03', location: 'loc-restoration', action: '복원실 복귀' },
      { id: 'tl-13', start: '21:29', end: '21:30', actor: 's01', location: 'loc-office', action: '사무실 복귀' }
    ],

    crime: { location: 'loc-gallery', window: ['21:12', '21:16'] },

    accusation: {
      motives: [
        { id: 'm-debt', label: '도박 빚과 개인 수집가의 제안' },
        { id: 'm-job', label: '경쟁 경매사로 옮기기 위한 "선물"' },
        { id: 'm-grudge', label: '박물관에 대한 개인적 원한' },
        { id: 'm-insurance', label: '보험금을 노린 내부 공모' }
      ],
      methods: [
        { id: 'ms-cctv', label: 'CCTV를 "점검 모드"로 돌려 녹화 공백을 만들었다' },
        { id: 'ms-card', label: '휴게실 사물함의 경비 카드를 몰래 써서 수장고 문을 열었다' },
        { id: 'ms-mold', label: '복원 작업 때 뜬 몰드로 만든 모조품과 진품을 바꿨다' },
        { id: 'ms-own-card', label: '자기 출입 카드로 정면 출입했다' },
        { id: 'ms-break', label: '진열장 잠금을 강제로 열었다' },
        { id: 'ms-appraisal', label: '감정서를 위조해 진품을 빼돌렸다' }
      ]
    },

    solution: {
      culprit: 's03',
      motive: 'm-debt',
      method: ['ms-cctv', 'ms-card', 'ms-mold'],
      key_evidence: ['ev-03', 'ev-04', 'rec-01', 'rec-03'],
      acceptable_evidence: ['rec-02', 'ev-05', 'ev-02'],
      narrative: [
        '윤재민은 도박 빚에 쫓기고 있었고, 개인 수집가에게서 "푸른 별"을 넘기라는 제안을 받았다.',
        '3주 전 받침 세척 작업을 맡았을 때, 그는 실리콘 몰드로 원석의 본을 떠 정밀한 합성 스피넬 모조품을 준비했다.',
        '사건 당일 21:08, 복원실 단말로 CCTV를 "점검 모드"로 돌려 8분짜리 녹화 공백을 만들었다.',
        '21:10, 경비원 박도현이 담배를 피우러 나가며 사물함 3번(잠금 고장)에 두고 간 카드를 꺼냈다. 메모는 이 계획표였다.',
        '21:12 박도현의 카드로 수장고 문을 열고, 21:14 진품을 모조품과 바꿨다. 이때 장갑 섬유와 연마 가루가 받침에 남았다.',
        '21:18 카드를 사물함에 돌려놓고 복원실로 돌아왔다. 출입 로그의 "박도현 카드"는 그가 의도한 함정이었다.'
      ],
      innocents: {
        s01: '한서윤의 공백은 주차장에서의 이직 면접 통화였다. 사무실 문이 열리지 않은 기록은 그녀의 거짓말을 깨지만 범행과는 무관하다.',
        s02: '박도현은 21:08~21:20 후문에서 담배를 피웠다(영수증 · 꽁초 · 한서윤의 목격). 카드를 사물함에 둔 것은 근무 수칙 위반일 뿐이다.'
      }
    }
  };

  return C;
});
