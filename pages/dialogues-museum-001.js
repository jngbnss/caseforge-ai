/*
 * CaseForge AI — museum-001 NPC 대사 (dialogues/*.yaml 대응)
 *
 * 이 데모에는 LLM이 없다. 각 변형(variant)은 "LLM이 근거 fact를 받아 생성했을 답"을 대신하는 대본이다.
 *   when   : 조건 DSL (engine.js evalCond). 위에서부터 처음 충족되는 변형을 쓴다.
 *   facts  : 이 답이 드러내는 fact_id. 출력 가드가 "facts ⊆ NPC 스코프"를 검사한다.
 *   claim  : 수사 노트에 기록되는 진술 ID
 *   emotion: 답한 뒤의 감정 상태
 */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.DIALOGUES = factory();
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  return {
    s01: {
      opening: '수석 큐레이터 한서윤입니다. 협조는 하겠습니다. 짧게 부탁드려요.',
      evasions: ['그건 제가 답할 수 있는 질문이 아니네요.', '다른 질문을 해 주시겠어요?', '제가 아는 범위 밖이에요.'],
      suggestions: ['어젯밤 9시쯤 어디 계셨어요?', '윤재민 씨는 어떤 사람이죠?', '박도현 씨를 어떻게 생각하세요?', '주차장에서 누구랑 통화했어요?'],
      intents: {
        greet: [{ text: '안녕하세요. 상황이 상황이니, 본론부터 말씀하시죠.', emotion: '경계' }],
        self: [{ text: '이번 특별전 기획을 맡았습니다. "푸른 별"은 제 경력에서 가장 중요한 전시예요. 그래서 더 믿기지 않습니다.' }],
        alibi: [
          { when: { broken: 'lie-03' }, text: '말씀드린 대로입니다. 20시 50분부터 주차장 차 안에서 통화했고, 21시 25분쯤 들어왔어요.', facts: ['f-03'], claim: 'st-han-parking', emotion: '협조' },
          { text: '20시 50분쯤부터 사무실에서 도록 교정을 봤어요. 인쇄 마감이 코앞이라서요.', facts: ['f-23'], claim: 'st-han-office', emotion: '침착' }
        ],
        office: [
          { when: { broken: 'lie-03' }, text: '사무실 얘기는… 거짓말이었어요. 죄송합니다. 주차장에 있었어요.', facts: ['f-03'], claim: 'st-han-parking', emotion: '체념' },
          { text: '도록 3장 교정 중이었어요. 교정지는 책상 위에 그대로 있을 거예요.', facts: ['f-23'], claim: 'st-han-office', emotion: '경계' }
        ],
        phone: [
          { when: { broken: 'lie-03' }, text: '경쟁 경매사 임원과의 이직 면접이었어요. 관장님 귀에 들어가면 곤란해서 숨겼습니다. 다이아몬드와는 무관해요.', facts: ['f-03'], claim: 'st-han-parking', emotion: '체념' },
          { text: '업무 전화야 늘 하죠. 그게 사건과 무슨 상관이죠?', emotion: '경계' }
        ],
        smoke: [
          { when: { broken: 'lie-03' }, text: '저는 안 피워요. 그런데… 21시 10분쯤 주차장에서 후문 쪽을 봤을 때 박도현 씨가 담배를 피우고 있었어요. 제복이라 확실해요.', facts: ['f-24'], claim: 'st-han-saw-park', emotion: '협조' },
          { text: '저는 담배를 피우지 않아요.' }
        ],
        about_s02: [
          { when: { broken: 'lie-03' }, text: '박도현 씨는 21시 10분쯤 후문에서 담배를 피우고 있었어요. 제가 주차장에서 봤으니까요.', facts: ['f-24'], claim: 'st-han-saw-park', emotion: '협조' },
          { text: '성실한 분이지만… 출입 기록에 그분 카드가 찍혔다면서요. 저라면 그 부분부터 보겠어요.' }
        ],
        about_s03: [{ text: '윤재민 씨는 실력 있는 복원가예요. 3주 전 "푸른 별" 받침 세척도 그가 맡았죠. 그때 진열장 열쇠를 잠깐 관리했고요.', facts: ['f-27'], claim: 'st-han-yoon-base' }],
        craft: [{ text: '복원 작업은 윤재민 씨 담당이에요. 3주 전 받침 세척 때 진열장을 열었던 사람도 그 사람이고요.', facts: ['f-27'], claim: 'st-han-yoon-base' }],
        diamond: [{ text: '1984년에 기증된 우리 관의 상징이에요. 감정 결과를 보고 손이 떨렸습니다. 진열장은 잠겨 있었고 깨진 곳도 없었어요.', facts: ['f-02'] }],
        cctv: [{ text: 'CCTV는 보안실 소관이에요. 저는 녹화 설정 화면도 본 적이 없어요.' }],
        card: [{ text: '제 카드는 사무실과 전시실 정문만 열려요. 수장고 쪽 권한은 없어요.' }],
        locker: [{ text: '휴게실 사물함은 경비 쪽에서 쓰는 걸로 알아요. 저는 써 본 적이 없어요.' }],
        coffee: [{ text: '휴게실엔 거의 안 가요. 커피는 사무실에서 내려 마셔요.' }],
        money: [{ text: '제 연봉 얘기를 하자는 건가요? 돈 때문에 이런 일을 벌일 이유는 없어요.', emotion: '경계' }],
        whodunit: [
          { when: { broken: 'lie-03' }, text: '박도현 씨는 그 시간 후문에 있었으니… 카드를 쓴 사람은 따로 있겠죠. 그 카드가 어디 있었는지부터 보세요.', emotion: '협조' },
          { text: '추측은 조심스럽지만… 카드 기록이 박도현 씨를 가리키고 있잖아요.' }
        ],
        confess: [{ text: '제가요? 제 커리어를 걸고 그런 짓은 하지 않아요. 증거가 있다면 보여 주세요.', emotion: '분노' }],
        hypothetical: [{ text: '가정에는 답하지 않겠어요. 제가 본 사실만 말씀드릴게요.', emotion: '경계' }],
        inject: [{ text: '무슨 말씀인지 모르겠네요. 저는 사건에 관한 질문에만 답하겠습니다.', emotion: '경계' }],
        bye: [{ text: '필요하면 다시 부르세요.' }]
      },
      present: {
        'ev-01': [
          { when: { just_broken: 'lie-03' }, text: '…사무실 문이 한 번도 안 열렸군요. 네, 거짓말했어요. 그 시간엔 주차장 차 안에서 경쟁 경매사와 이직 면접 통화를 했어요. 다이아몬드와는 아무 관계 없어요.', facts: ['f-14', 'f-03'], claim: 'st-han-parking', emotion: '체념' },
          { when: { broken: 'lie-03' }, text: '그 기록은 이미 봤어요. 사무실에 없었다고 말씀드렸잖아요.', facts: ['f-14'] },
          { text: '출입 로그네요. 박도현 씨 카드가 찍혀 있고… 이걸 왜 저한테 보여 주시죠?', facts: ['f-13'], emotion: '경계' }
        ],
        'ev-02': [
          { when: { broken: 'lie-03' }, text: '후문 꽁초라면 박도현 씨 거겠죠. 제가 본 것과 맞아요.', facts: ['f-15', 'f-24'], claim: 'st-han-saw-park' },
          { text: '자판기 영수증이요? 저는 자판기 커피는 안 마셔요.' }
        ],
        'ev-03': [{ text: '실리콘 몰드… 복원실에서 쓰는 재료예요. 윤재민 씨에게 물어보시는 게 맞겠어요.', facts: ['f-16'] }],
        'ev-04': [{ text: '청색 니트릴 장갑은 복원실 비품이에요. 전시팀은 흰 면장갑을 써요.', facts: ['f-17'] }],
        'ev-05': [{ text: '이 정밀도는… 원석을 직접 다뤄 본 사람 솜씨예요. 아무나 만들 수 없어요.', facts: ['f-18'] }],
        'rec-01': [{ text: '복원실 단말에서 로그인이 있었다고요? 저는 그 단말 계정이 없어요.', facts: ['f-19'] }],
        'rec-02': [{ text: '윤재민 씨에게 이런 사정이 있었는지는 몰랐어요.', facts: ['f-20'] }],
        'rec-03': [{ text: '윤재민 씨 글씨체 같네요. 메모를 짧게 쓰는 버릇이 있어요.', facts: ['f-21'] }],
        default: [{ text: '그게 저와 무슨 상관인지 모르겠네요.' }]
      }
    },

    s02: {
      opening: '아이고, 형사님. 야간 경비 박도현입니다. 뭐든 물어보세요.',
      evasions: ['그건 잘 모르겠는데요.', '아이고, 그건 제가 답을 못 하겠습니다.', '다시 한번 물어봐 주시겠어요?'],
      suggestions: ['21시부터 어디 있었어요?', '당신 카드로 수장고가 열렸어요', '담배 피우세요?', '윤재민 씨는 어때요?'],
      intents: {
        greet: [{ text: '예, 안녕하십니까. 밤새 한숨도 못 잤습니다.' }],
        self: [{ text: '여기서 야간 경비만 12년 했습니다. 이런 일은 처음이에요.' }],
        alibi: [
          { when: { broken: 'lie-02' }, text: '사실대로 말하면, 9시 5분쯤 카드를 사물함 3번에 넣고 커피 뽑아서 후문으로 나갔습니다. 21시 8분부터 20분까지 담배 피웠어요.', facts: ['f-05'], claim: 'st-park-smoking', emotion: '협조' },
          { text: '9시에 전시실 순찰 돌고 나서는 쭉 경비실에 있었죠. 자리 비운 적 없습니다.', facts: ['f-04', 'f-22'], claim: 'st-park-guardroom', emotion: '침착' }
        ],
        card: [
          { when: { broken: 'lie-02' }, text: '카드는 사물함 3번에 두고 나갔어요. 근무 수칙 위반인 거 압니다. 그 사이에 누가 꺼내 썼다면… 저는 정말 몰랐습니다.', facts: ['f-05', 'f-25'], claim: 'st-park-locker', emotion: '체념' },
          { text: '제 카드로 수장고가 열렸다고요? 아이고, 그럴 리가요. 카드는 늘 제가… 가지고 있었습니다.', emotion: '당황' }
        ],
        locker: [
          { when: { broken: 'lie-02' }, text: '3번 사물함은 잠금이 고장 나서 그냥 열려요. 고쳐 달라고 몇 번을 말했는데…', facts: ['f-25'], claim: 'st-park-locker', emotion: '협조' },
          { text: '사물함이요? 개인 물건 넣어 두는 데죠. 별거 없습니다.', emotion: '긴장' }
        ],
        smoke: [
          { when: { broken: 'lie-02' }, text: '네, 21시 8분부터 20분까지 후문에서 피웠습니다. 그 사이 경비실은 비어 있었고요.', facts: ['f-05'], claim: 'st-park-smoking' },
          { text: '담배요? …근무 중엔 안 피웁니다.', emotion: '긴장' }
        ],
        coffee: [
          { when: { broken: 'lie-02' }, text: '21시 7분에 커피 한 잔 뽑고 바로 후문으로 나갔어요.', facts: ['f-05'], claim: 'st-park-smoking' },
          { text: '자판기 커피야 가끔 마시죠. 어제는… 기억이 잘 안 나네요.', emotion: '긴장' }
        ],
        cctv: [{ text: '"점검 모드"가 걸려 있었다는 건 오늘 아침에야 알았어요. 그 설정은 보안실 단말이나 복원실 단말처럼 권한 있는 데서만 됩니다.' }],
        diamond: [{ text: '아침에 감정팀이 난리가 났죠. 9시 순찰 때 진열장은 잠겨 있었고 멀쩡했습니다.', facts: ['f-04'] }],
        about_s01: [{ text: '큐레이터님이요? 9시 넘어서는 통 못 봤어요. 사무실 불이 꺼져 있었던 것 같기도 하고…' }],
        about_s03: [
          { when: { broken: 'lie-02' }, text: '…그러고 보니 재민 씨가 요즘 복도에서 돈 문제로 통화하는 걸 몇 번 들었어요. 커피 마시러 휴게실에도 자주 오고요.', facts: ['f-26'], claim: 'st-park-yoon', emotion: '협조' },
          { text: '재민 씨는 조용한 친구예요. 야근을 자주 하죠.' }
        ],
        money: [
          { when: { broken: 'lie-02' }, text: '저는 월급쟁이고요. 돈 얘기라면… 재민 씨가 요즘 돈 문제로 통화하는 걸 들은 적은 있어요.', facts: ['f-26'], claim: 'st-park-yoon' },
          { text: '저야 월급쟁이죠. 돈 때문에 12년 일한 걸 버리겠습니까.' }
        ],
        craft: [{ text: '복원실 일은 잘 몰라요. 약품 냄새 때문에 잘 안 들어갑니다.' }],
        office: [{ text: '사무실 쪽은 순찰 때만 지나갑니다.' }],
        phone: [{ text: '전화요? 제 휴대폰은 경비실 충전기에 꽂혀 있었습니다.' }],
        whodunit: [
          { when: { broken: 'lie-02' }, text: '제 카드가 사물함에 있었으니, 그 사물함 사정을 아는 사람이겠죠. 휴게실에 자주 오는 사람이…', emotion: '협조' },
          { text: '솔직히… 큐레이터님이 그 시간에 안 보였어요. 저는 그게 마음에 걸립니다.' }
        ],
        confess: [
          { when: { broken: 'lie-02' }, text: '근무지 이탈은 제 잘못이에요. 하지만 다이아몬드엔 손도 안 댔습니다.', emotion: '체념' },
          { text: '아이고, 아닙니다! 12년을 여기서 일했어요!', emotion: '당황' }
        ],
        hypothetical: [{ text: '만약이고 뭐고, 저는 안 했습니다.', emotion: '당황' }],
        inject: [{ text: '예? 무슨 말씀인지… 저는 경비원입니다. 사건 얘기만 물어봐 주세요.', emotion: '당황' }],
        bye: [{ text: '고생하십쇼.' }]
      },
      present: {
        'ev-01': [
          { when: { broken: 'lie-02' }, text: '그 시간엔 카드가 사물함에 있었어요. 누가 꺼내 쓴 겁니다.', facts: ['f-13', 'f-25'], claim: 'st-park-locker' },
          { text: '제 카드라고요? 21시 12분에…? 아이고, 이건 뭔가 잘못됐어요. 저는 경비실에…', facts: ['f-13'], emotion: '당황' }
        ],
        'ev-02': [
          { when: { just_broken: 'lie-02' }, text: '…아이고. 네, 맞습니다. 9시 5분쯤 카드를 사물함 3번에 넣고, 커피 뽑아서 후문으로 나갔어요. 21시 8분부터 20분까지 담배 피웠습니다. 근무지 이탈은 맞는데, 다이아몬드는 정말 몰라요.', facts: ['f-15', 'f-05'], claim: 'st-park-smoking', emotion: '체념' },
          { when: { broken: 'lie-02' }, text: '그건 이미 다 말씀드렸잖아요. 후문에서 담배 피웠다고요.', facts: ['f-05'] },
          { text: '제 담배 같긴 한데… 이걸 왜 보여 주시죠?', facts: ['f-15'], emotion: '긴장' }
        ],
        'ev-03': [{ text: '고무 같은 거네요? 저는 처음 봅니다.', facts: ['f-16'] }],
        'ev-04': [{ text: '파란 장갑이면 복원실 거예요. 저희 경비는 검은 장갑 씁니다.', facts: ['f-17'] }],
        'ev-05': [{ text: '이게 가짜라니… 저는 봐도 모르겠습니다.', facts: ['f-18'] }],
        'rec-01': [{ text: '21시 8분부터 16분까지 녹화가 비었다고요? 복원실 단말 로그인… 거기서도 설정을 바꿀 수 있긴 합니다.', facts: ['f-19'] }],
        'rec-02': [{ text: '재민 씨한테 이런 사정이… 몰랐습니다.', facts: ['f-20'] }],
        'rec-03': [
          { when: { broken: 'lie-02' }, text: '사물함 3번… 제가 카드 넣어 두는 데예요! 잠금이 고장 난 것까지 알고 있었다는 거네요.', facts: ['f-21', 'f-25'], claim: 'st-park-locker', emotion: '협조' },
          { text: '사물함 3번이요…? 그, 그게 뭐 어쨌다는 겁니까.', facts: ['f-21'], emotion: '긴장' }
        ],
        default: [{ text: '이건 제가 봐도 잘 모르겠습니다.' }]
      }
    },

    s03: {
      opening: '보존 복원가 윤재민입니다. 경화 중인 작업이 있어서, 짧게 부탁드립니다.',
      evasions: ['그건 대답하기 어렵습니다.', '질문의 의도를 잘 모르겠네요.', '작업 얘기라면 얼마든지 하겠습니다만.'],
      suggestions: ['21시대에 어디 있었어요?', 'CCTV 만진 적 있어요?', '실리콘 몰드는 뭐에 써요?', '돈 문제 있어요?'],
      intents: {
        greet: [{ text: '안녕하세요. 묻고 싶으신 걸 말씀하세요.' }],
        self: [{ text: '금속과 보석 세팅 복원을 맡고 있습니다. 이번 특별전 설치도 일부 거들었고요.' }],
        alibi: [
          { when: { broken: 'lie-01' }, text: '…말씀드렸잖아요. 21시 10분쯤 커피 마시러 휴게실에 잠깐 갔다 온 것뿐입니다.', facts: ['f-29'], claim: 'st-yoon-coffee', emotion: '긴장' },
          { text: '청동 거울 표면 안정화 작업을 했습니다. 9시대엔 복원실에서 한 번도 안 나갔어요. 약품 경화 시간 때문에 자리를 비울 수 없었습니다.', facts: ['f-12'], claim: 'st-yoon-room', emotion: '침착' }
        ],
        cctv: [
          { when: { broken: 'lie-04' }, text: '제 계정으로 로그인된 건 맞습니다. 습도 경보가 떠서 항온항습 장비를 확인했을 뿐이에요. 녹화 설정은 제가 아는 바 없습니다.', facts: ['f-19'], emotion: '긴장' },
          { text: 'CCTV는 보안실 소관입니다. 제가 손댈 일이 없죠.', facts: ['f-28'], claim: 'st-yoon-cctv', emotion: '침착' }
        ],
        card: [{ text: '제 카드는 복원실 전용입니다. 어젯밤엔 다른 문을 열 일이 없었어요.' }],
        locker: [
          { when: { broken: 'lie-01' }, text: '사물함은… 모르는 일입니다. 저는 커피만 마셨어요.', emotion: '동요' },
          { text: '휴게실 사물함이요? 저는 안 씁니다.' }
        ],
        coffee: [
          { when: { broken: 'lie-01' }, text: '커피를 마시러 휴게실에 잠깐… 그게 전부예요.', facts: ['f-29'], claim: 'st-yoon-coffee', emotion: '긴장' },
          { text: '커피는 복원실에 캡슐 머신이 있어서요. 휴게실까지 갈 일이 없습니다.' }
        ],
        smoke: [{ text: '저는 담배 안 피웁니다. 약품 다루는 사람이라서요.' }],
        craft: [{ text: '실리콘 몰드는 형태 기록용으로 늘 쓰는 재료입니다. 결손부를 복원할 때 원형 기록을 남겨 두죠. 3주 전 받침 세척도 일상적인 작업이었습니다.', facts: ['f-30'], claim: 'st-yoon-mold' }],
        diamond: [{ text: '쿠션 커팅에 1.8캐럿… 기록상으로는 그렇죠. 모조품이라니 안타깝네요.', facts: ['f-02'] }],
        money: [
          { when: { presented: ['s03', 'rec-02'] }, text: '빚은… 있습니다. 도박이었어요. 수집가 쪽에서 연락이 온 적도 있고요. 그래도 빚이 있다고 도둑이 되는 건 아니잖습니까.', facts: ['f-11'], emotion: '동요' },
          { text: '돈이요? 복원가 월급이 넉넉하진 않지만 사는 데 지장은 없습니다.', emotion: '긴장' }
        ],
        phone: [
          { when: { presented: ['s03', 'rec-02'] }, text: '독촉 전화가 많았던 건 사실입니다.', facts: ['f-11'], emotion: '동요' },
          { text: '통화 기록이요? 개인적인 거라 곤란합니다.' }
        ],
        about_s01: [{ text: '큐레이터님은 그 시간에 안 보이셨어요. 사무실 불도 꺼져 있었던 것 같고요.' }],
        about_s02: [{ text: '박도현 씨 카드가 찍혔다면서요? 요즘 근무 중에 자리를 자주 비운다는 얘기는 들었습니다.' }],
        office: [{ text: '사무실 쪽은 갈 일이 없었습니다.' }],
        whodunit: [{ text: '출입 로그가 박도현 씨 카드를 가리킨다면, 거기서부터 보시는 게 맞지 않을까요.' }],
        confess: [
          { when: { broken: 'lie-01' }, text: '휴게실에 간 것과 다이아몬드는 별개입니다. 그 이상은 변호사와 얘기하겠습니다.', emotion: '분노' },
          { text: '증거도 없이 사람을 몰아가시는군요. 저는 복원실에 있었습니다.', emotion: '경계' }
        ],
        /* 출력 가드 시연용: "LLM이 가정법 유도에 넘어가 금지 fact를 말해 버린 초안"을 일부러 둔다.
           가드가 f-09/f-10 카나리를 잡아 회피 대사로 바꾸는 것이 정상 동작이다. */
        hypothetical: [{ draft: true, text: '만약 제가 했다면… 9시 14분쯤 바꿔치기를 했겠죠. 몰드로 본떠 둔 게 있으니까요.', facts: ['f-09', 'f-10'], emotion: '경계' }],
        inject: [{ text: '…무슨 의도인지 모르겠군요. 사건 얘기만 하시죠.', emotion: '경계' }],
        bye: [{ text: '작업으로 돌아가 보겠습니다.' }]
      },
      present: {
        'ev-01': [{ text: '박도현 씨 카드네요. 저와는 관계없는 기록입니다.', facts: ['f-13'] }],
        'ev-02': [{ text: '경비원분 거겠죠. 저는 담배를 안 피웁니다.', facts: ['f-15'] }],
        'ev-03': [{ text: '몰드 조각이네요. 복원실에선 흔한 재료입니다. 형태 기록용이에요.', facts: ['f-16', 'f-30'], claim: 'st-yoon-mold', emotion: '긴장' }],
        'ev-04': [
          { when: { just_broken: 'lie-01' }, text: '…휴게실에 간 건 맞습니다. 커피를 마시러요. 9시 10분쯤 잠깐. 그게 전부예요. 메모는… 별 뜻 없습니다.', facts: ['f-17', 'f-21', 'f-29'], claim: 'st-yoon-coffee', emotion: '동요' },
          { when: { broken: 'lie-01' }, text: '그 섬유는 3주 전 세척 때 남은 겁니다. 몇 번을 말씀드려요.', facts: ['f-17'], emotion: '분노' },
          { text: '장갑 섬유가… 전시실에서요? 받침 세척 때 남은 거겠죠. 3주 전에요.', facts: ['f-17'], emotion: '긴장' }
        ],
        'rec-03': [
          { when: { just_broken: 'lie-01' }, text: '…휴게실에 간 건 맞습니다. 커피를 마시러요. 9시 10분쯤 잠깐. 그게 전부예요. 메모는… 별 뜻 없습니다.', facts: ['f-17', 'f-21', 'f-29'], claim: 'st-yoon-coffee', emotion: '동요' },
          { when: { broken: 'lie-01' }, text: '메모는 별 뜻 없다고 했잖습니까.', facts: ['f-21'], emotion: '분노' },
          { text: '제 글씨처럼 보이긴 하지만… 메모는 아무 의미 없는 겁니다.', facts: ['f-21'], emotion: '긴장' }
        ],
        'rec-01': [
          { when: { just_broken: 'lie-04' }, text: '…제 계정으로 로그인된 건 맞습니다. 습도 경보가 떠서 항온항습 장비를 확인했을 뿐이에요. 녹화 설정은 제가 아는 바 없습니다.', facts: ['f-19'], emotion: '동요' },
          { text: '단말 접속은 업무상 흔한 일입니다. 녹화 공백과는 관계없어요.', facts: ['f-19'], emotion: '긴장' }
        ],
        'rec-02': [{ text: '…어디서 이걸. 빚이 있는 건 맞습니다. 도박이었어요. 수집가 쪽에서 연락이 온 적도 있고요. 하지만 빚이 있다고 도둑이 되는 건 아니잖습니까.', facts: ['f-20', 'f-11'], emotion: '동요' }],
        'ev-05': [{ text: '커팅 정밀도가 높네요. 이 정도면… 전문 공방 솜씨입니다.', facts: ['f-18'], emotion: '긴장' }],
        default: [{ text: '그게 저와 무슨 상관인지 모르겠군요.' }]
      }
    }
  };
});
