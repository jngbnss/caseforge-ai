import type { ButtonHTMLAttributes, ReactNode } from 'react'

const EMOTION_LABEL: Record<string, string> = {
  calm: '침착',
  nervous: '불안',
  defensive: '경계',
  angry: '분노',
  sad: '침울',
  shaken: '동요',
}

const EMOTION_CLASS: Record<string, string> = {
  calm: 'bg-soft text-muted',
  nervous: 'bg-tag-soft text-tag',
  defensive: 'bg-soft text-accent',
  angry: 'bg-bad/15 text-bad',
  sad: 'bg-soft text-muted',
  shaken: 'bg-bad/15 text-bad',
}

export function EmotionBadge({ emotion }: { emotion: string }) {
  return (
    <span
      className={`rounded-full px-2 py-0.5 text-xs whitespace-nowrap ${EMOTION_CLASS[emotion] ?? 'bg-soft text-muted'}`}
    >
      {EMOTION_LABEL[emotion] ?? emotion}
    </span>
  )
}

export function Eyebrow({ children }: { children: ReactNode }) {
  return <p className="text-xs font-medium tracking-wide text-accent">{children}</p>
}

export function Panel({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <section className={`rounded-lg border border-line bg-sheet p-5 ${className}`}>{children}</section>
  )
}

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & { variant?: 'primary' | 'ghost' }

export function Button({ variant = 'primary', className = '', ...props }: ButtonProps) {
  const base =
    'rounded-md px-4 py-2 text-sm font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-40'
  const look =
    variant === 'primary'
      ? 'bg-accent text-accent-ink hover:opacity-90'
      : 'border border-accent text-accent hover:bg-soft'
  return <button type="button" className={`${base} ${look} ${className}`} {...props} />
}

export function EvidenceTag({ id }: { id: string }) {
  return <span className="shrink-0 font-mono text-xs whitespace-nowrap text-tag">{id}</span>
}

export function Empty({ children }: { children: ReactNode }) {
  return <p className="text-sm text-muted">{children}</p>
}
