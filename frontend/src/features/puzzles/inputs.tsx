import { useState } from 'react'

import { Button } from '../../components/ui'

export interface Option {
  id: string
  label: string
}

/** 선택지를 눌러 순서를 만든다. 모든 선택지를 고르면 제출할 수 있다. */
export function SequenceInput({
  options,
  disabled,
  onSubmit,
}: {
  options: Option[]
  disabled?: boolean
  onSubmit: (order: string[]) => void
}) {
  const [order, setOrder] = useState<string[]>([])
  const label = (id: string) => options.find((o) => o.id === id)?.label ?? id
  const complete = order.length === options.length

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap gap-2">
        {options.map((o) => {
          const used = order.includes(o.id)
          return (
            <button
              key={o.id}
              type="button"
              disabled={used || disabled}
              onClick={() => setOrder([...order, o.id])}
              className="rounded-md border border-line bg-paper px-3 py-2 text-left text-sm hover:border-accent disabled:opacity-35"
            >
              {o.label}
            </button>
          )
        })}
      </div>
      <ol aria-label="고른 순서" className="flex min-h-10 flex-col gap-1 rounded-md bg-soft p-3 text-sm">
        {order.length === 0 && <li className="text-muted">위에서 순서대로 고른다.</li>}
        {order.map((id, i) => (
          <li key={id} className="flex gap-2">
            <span className="font-mono text-accent">{i + 1}.</span>
            {label(id)}
          </li>
        ))}
      </ol>
      <div className="flex flex-wrap gap-2">
        <Button
          onClick={() => {
            onSubmit(order)
            setOrder([])
          }}
          disabled={!complete || disabled}
        >
          이 순서로 확인
        </Button>
        <Button variant="ghost" onClick={() => setOrder(order.slice(0, -1))} disabled={!order.length}>
          하나 되돌리기
        </Button>
        <Button variant="ghost" onClick={() => setOrder([])} disabled={!order.length}>
          처음부터
        </Button>
      </div>
    </div>
  )
}

/** 숫자 코드 입력. 길이를 채워야 제출할 수 있다. */
export function CodeInput({
  length,
  disabled,
  onSubmit,
}: {
  length: number
  disabled?: boolean
  onSubmit: (code: string) => void
}) {
  const [code, setCode] = useState('')
  return (
    <form
      className="flex flex-wrap items-center gap-2"
      onSubmit={(e) => {
        e.preventDefault()
        if (code.length === length) {
          onSubmit(code)
          setCode('')
        }
      }}
    >
      <label className="sr-only" htmlFor="code-input">
        {length}자리 암호
      </label>
      <input
        id="code-input"
        inputMode="numeric"
        autoComplete="off"
        value={code}
        maxLength={length}
        onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, length))}
        placeholder={'0'.repeat(length)}
        className="w-32 rounded-md border border-line bg-sheet px-3 py-2 font-mono text-lg tracking-[0.4em]"
        disabled={disabled}
      />
      <Button type="submit" disabled={code.length !== length || disabled}>
        금고 열기
      </Button>
    </form>
  )
}
