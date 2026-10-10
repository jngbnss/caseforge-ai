import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { CodeInput, SequenceInput } from '../src/features/puzzles/inputs'

const options = [
  { id: 'b', label: '두 번째' },
  { id: 'a', label: '첫 번째' },
  { id: 'c', label: '세 번째' },
]

describe('SequenceInput', () => {
  it('모든 선택지를 골라야 제출할 수 있고, 고른 순서대로 보낸다', async () => {
    const onSubmit = vi.fn()
    render(<SequenceInput options={options} onSubmit={onSubmit} />)
    const submit = screen.getByRole('button', { name: '이 순서로 확인' })
    expect(submit).toBeDisabled()

    await userEvent.click(screen.getByRole('button', { name: '첫 번째' }))
    await userEvent.click(screen.getByRole('button', { name: '세 번째' }))
    expect(submit).toBeDisabled()
    await userEvent.click(screen.getByRole('button', { name: '하나 되돌리기' }))
    await userEvent.click(screen.getByRole('button', { name: '두 번째' }))
    await userEvent.click(screen.getByRole('button', { name: '세 번째' }))
    expect(submit).toBeEnabled()

    await userEvent.click(submit)
    expect(onSubmit).toHaveBeenCalledWith(['a', 'b', 'c'])
    expect(screen.getByText('위에서 순서대로 고른다.')).toBeInTheDocument()
  })

  it('고른 선택지는 다시 고를 수 없다', async () => {
    render(<SequenceInput options={options} onSubmit={() => {}} />)
    const first = screen.getByRole('button', { name: '첫 번째' })
    await userEvent.click(first)
    expect(first).toBeDisabled()
  })
})

describe('CodeInput', () => {
  it('숫자만 받고 길이를 채워야 제출한다', async () => {
    const onSubmit = vi.fn()
    render(<CodeInput length={4} onSubmit={onSubmit} />)
    const input = screen.getByLabelText('4자리 암호')
    await userEvent.type(input, '07a8')
    expect(input).toHaveValue('078')
    expect(screen.getByRole('button', { name: '금고 열기' })).toBeDisabled()
    await userEvent.type(input, '45')
    expect(input).toHaveValue('0784')
    await userEvent.click(screen.getByRole('button', { name: '금고 열기' }))
    expect(onSubmit).toHaveBeenCalledWith('0784')
  })
})
