/**
 * 화면 그림: 용의자 초상화, 증거 아이콘, 단계 아이콘. 모두 SVG로 직접 그려 외부 이미지 라이선스가 없다.
 * 그림은 이름·직업·감정 같은 공개 정보로만 고른다 (정답과 무관). 장식이므로 스크린리더에서는 숨긴다.
 */

import { type IconKind, iconFor, lookFor } from './artData'

function Face({ emotion }: { emotion: string }) {
  // 눈썹 기울기, 입 모양, 땀방울로 감정을 보인다
  const brow =
    emotion === 'angry' || emotion === 'defensive'
      ? { l: 'M41 50 L53 54', r: 'M79 50 L67 54' }
      : emotion === 'nervous' || emotion === 'shaken' || emotion === 'sad'
        ? { l: 'M41 54 L53 50', r: 'M79 54 L67 50' }
        : { l: 'M41 52 L53 51', r: 'M79 52 L67 51' }
  const mouth =
    emotion === 'angry'
      ? 'M52 82 Q60 76 68 82'
      : emotion === 'shaken'
        ? 'M54 80 Q60 88 66 80 Q60 84 54 80'
        : emotion === 'nervous' || emotion === 'sad'
          ? 'M52 82 Q56 79 60 82 Q64 85 68 81'
          : emotion === 'defensive'
            ? 'M52 81 L68 81'
            : 'M52 79 Q60 85 68 79'
  return (
    <g stroke="#2a1d16" strokeWidth={2.4} strokeLinecap="round" fill="none">
      <path d={brow.l} />
      <path d={brow.r} />
      <circle cx={47} cy={61} r={2.6} fill="#2a1d16" stroke="none" />
      <circle cx={73} cy={61} r={2.6} fill="#2a1d16" stroke="none" />
      <path d={mouth} />
      {(emotion === 'nervous' || emotion === 'shaken') && (
        <path d="M86 46 Q90 54 86 57 Q82 54 86 46 Z" fill="#8fc6ea" stroke="#5a9cc8" strokeWidth={1.2} />
      )}
      {emotion === 'angry' && (
        <g stroke="#d9534f" strokeWidth={1.6}>
          <path d="M38 70 l6 0" />
          <path d="M76 70 l6 0" />
        </g>
      )}
    </g>
  )
}

export function Portrait({
  role,
  index,
  emotion = 'calm',
  size = 72,
  className = '',
}: {
  role: string
  index: number
  emotion?: string
  size?: number
  className?: string
}) {
  const look = lookFor(role, index)
  return (
    <svg
      viewBox="0 0 120 120"
      width={size}
      height={size}
      aria-hidden
      className={`shrink-0 ${className}`}
      data-emotion={emotion}
    >
      <rect width={120} height={120} rx={14} fill="var(--portrait-bg)" />
      {/* 몸 */}
      <path d="M18 120 Q22 92 60 90 Q98 92 102 120 Z" fill={look.coat} />
      <path d="M50 90 L60 104 L70 90 Z" fill="#f4efe6" />
      {/* 목·얼굴 */}
      <rect x={52} y={78} width={16} height={14} fill={look.skin} />
      <ellipse cx={60} cy={60} rx={25} ry={28} fill={look.skin} />
      {/* 머리 */}
      {look.style === 'bun' && (
        <g fill={look.hair}>
          <circle cx={60} cy={24} r={11} />
          <path d="M34 58 Q32 30 60 30 Q88 30 86 58 Q80 40 60 40 Q40 40 34 58 Z" />
        </g>
      )}
      {look.style === 'short' && (
        <path d="M35 56 Q34 32 60 32 Q86 32 85 56 Q80 44 60 44 Q40 44 35 56 Z" fill={look.hair} />
      )}
      {look.style === 'messy' && (
        <path
          d="M34 58 Q30 34 46 30 Q50 22 60 28 Q70 20 76 30 Q92 32 86 58 Q82 42 70 44 Q62 38 54 44 Q42 40 34 58 Z"
          fill={look.hair}
        />
      )}
      {look.extra === 'cap' && (
        <g>
          <path d="M33 46 Q34 26 60 26 Q86 26 87 46 Z" fill="#23384f" />
          <rect x={30} y={44} width={60} height={6} rx={3} fill="#1a2a3b" />
          <circle cx={60} cy={36} r={4} fill="#e2ad4a" />
        </g>
      )}
      {look.extra === 'glasses' && (
        <g fill="none" stroke="#2a1d16" strokeWidth={1.8}>
          <circle cx={47} cy={61} r={7} />
          <circle cx={73} cy={61} r={7} />
          <path d="M54 61 L66 61" />
        </g>
      )}
      <Face emotion={emotion} />
      {look.extra === 'loupe' && (
        <g>
          <path d="M36 46 Q60 36 84 46" stroke="#3b3b3b" strokeWidth={3} fill="none" />
          <circle cx={80} cy={50} r={6} fill="#cfe6f2" stroke="#3b3b3b" strokeWidth={2.4} />
        </g>
      )}
      {look.extra === 'cap' && <rect x={74} y={100} width={10} height={8} rx={2} fill="#e2ad4a" />}
    </svg>
  )
}

function IconShape({ kind }: { kind: IconKind }) {
  const ink = 'var(--ink)'
  switch (kind) {
    case 'receipt':
      return (
        <g>
          <path d="M18 8 H46 V56 L41 52 L36 56 L32 52 L27 56 L23 52 L18 56 Z" fill="#fffdf6" stroke={ink} strokeWidth={2} />
          <path d="M23 18 H41 M23 26 H41 M23 34 H35" stroke={ink} strokeWidth={2} />
          <path d="M23 42 H41" stroke="var(--bad)" strokeWidth={2} />
        </g>
      )
    case 'log':
      return (
        <g>
          <rect x={10} y={12} width={44} height={30} rx={3} fill="#1f2e3d" stroke={ink} strokeWidth={2} />
          <path d="M15 20 H38 M15 26 H44 M15 32 H30" stroke="#7fe0a0" strokeWidth={2} />
          <path d="M26 42 V50 M38 42 V50 M20 52 H44" stroke={ink} strokeWidth={2.4} />
        </g>
      )
    case 'camera':
      return (
        <g>
          <path d="M10 22 L42 16 L46 32 L14 38 Z" fill="#d8d2c4" stroke={ink} strokeWidth={2} />
          <circle cx={42} cy={26} r={4} fill="#1f2e3d" />
          <path d="M28 36 L30 48 M20 50 H40" stroke={ink} strokeWidth={2.4} />
          <circle cx={16} cy={26} r={2.5} fill="var(--bad)" />
        </g>
      )
    case 'mold':
      return (
        <g>
          <path d="M10 40 Q12 22 32 22 Q52 22 54 40 Q52 50 32 50 Q12 50 10 40 Z" fill="#c7a6d9" stroke={ink} strokeWidth={2} />
          <path d="M22 36 L32 28 L42 36 L32 44 Z" fill="#8fb8e8" stroke={ink} strokeWidth={1.6} />
        </g>
      )
    case 'glove':
      return (
        <g>
          <path
            d="M20 54 V30 Q20 26 24 26 V14 Q24 10 28 10 Q32 10 32 14 V24 V12 Q32 8 36 8 Q40 8 40 12 V26 Q44 22 48 26 L42 40 V54 Z"
            fill="#6f95c9"
            stroke={ink}
            strokeWidth={2}
          />
          <circle cx={14} cy={46} r={2} fill="#bbb" />
          <circle cx={10} cy={52} r={1.6} fill="#bbb" />
        </g>
      )
    case 'diamond':
      return (
        <g>
          <path d="M14 24 L24 12 H40 L50 24 L32 54 Z" fill="#9fd0f2" stroke={ink} strokeWidth={2} />
          <path d="M14 24 H50 M24 12 L32 24 L40 12 M32 24 V54" stroke={ink} strokeWidth={1.4} fill="none" />
        </g>
      )
    case 'letter':
      return (
        <g>
          <rect x={10} y={16} width={44} height={32} rx={2} fill="#fffdf6" stroke={ink} strokeWidth={2} />
          <path d="M10 18 L32 34 L54 18" fill="none" stroke={ink} strokeWidth={2} />
          <rect x={36} y={36} width={14} height={8} fill="var(--bad)" opacity={0.85} />
        </g>
      )
    case 'memo':
      return (
        <g>
          <path d="M12 12 H34 L30 22 L36 30 L32 52 H12 Z" fill="#fff4b8" stroke={ink} strokeWidth={2} />
          <path d="M38 14 H52 V52 H36 L40 40 L34 30 L40 22 Z" fill="#fff4b8" stroke={ink} strokeWidth={2} />
          <path d="M16 22 H26 M16 30 H28 M42 30 H48" stroke={ink} strokeWidth={1.8} />
        </g>
      )
    default:
      return (
        <g>
          <circle cx={28} cy={28} r={14} fill="#e8f2f8" stroke={ink} strokeWidth={3} />
          <path d="M38 38 L52 52" stroke={ink} strokeWidth={5} strokeLinecap="round" />
        </g>
      )
  }
}

export function EvidenceIcon({ name, size = 40 }: { name: string; size?: number }) {
  return (
    <svg viewBox="0 0 64 64" width={size} height={size} aria-hidden className="shrink-0">
      <IconShape kind={iconFor(name)} />
    </svg>
  )
}

/** 폴라로이드처럼 생긴 증거 사진. */
export function Polaroid({
  name,
  caption,
  tilt = 0,
  size = 64,
}: {
  name: string
  caption?: string
  tilt?: number
  size?: number
}) {
  return (
    <span
      className="inline-flex flex-col items-center gap-1 self-start bg-white px-1.5 pt-1.5 pb-1 shadow-md"
      style={{ transform: `rotate(${tilt}deg)` }}
      aria-hidden
    >
      <span className="flex items-center justify-center bg-[var(--photo)]" style={{ width: size, height: size }}>
        <EvidenceIcon name={name} size={size * 0.8} />
      </span>
      {caption && <span className="max-w-[80px] truncate font-hand text-[10px] text-[#3a2c20]">{caption}</span>}
    </span>
  )
}

/** 화면 단계 아이콘 (폴더 탭). */
export function StepIcon({ step }: { step: string }) {
  const paths: Record<string, string> = {
    briefing: 'M5 4 H15 L19 8 V20 H5 Z M8 11 H16 M8 15 H16',
    scene: 'M10 4 A6 6 0 1 1 9.9 4 Z M14.5 14.5 L20 20',
    puzzles: 'M4 4 H11 V8 A2 2 0 1 0 11 12 V20 H4 Z M13 4 H20 V20 H13 V14 A2 2 0 1 0 13 10 Z',
    interrogation: 'M4 5 H20 V15 H10 L6 19 V15 H4 Z',
    board: 'M3 5 H21 V19 H3 Z M7 9 L12 14 L17 9',
    deduction: 'M12 3 L14.5 9 L21 9.5 L16 13.5 L17.5 20 L12 16.5 L6.5 20 L8 13.5 L3 9.5 L9.5 9 Z',
  }
  return (
    <svg viewBox="0 0 24 24" width={16} height={16} aria-hidden className="shrink-0">
      <path d={paths[step] ?? paths.briefing} fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinejoin="round" />
    </svg>
  )
}
