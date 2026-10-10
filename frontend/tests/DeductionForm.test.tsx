import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, it, vi } from 'vitest'

import { DeductionForm } from '../src/features/deduction/DeductionForm'

const ev = (evidence_id: string, name: string) => ({
  evidence_id,
  name,
  description: '',
  spot: '',
  location_name: '',
  facts: [],
})

const props = {
  suspects: [
    { suspect_id: 's1', name: '한서윤', role: '큐레이터', public_profile: '' },
    { suspect_id: 's3', name: '윤재민', role: '복원가', public_profile: '' },
  ],
  motives: [{ id: 'm1', text: '도박 빚' }],
  methods: [{ id: 'x1', text: '바꿔치기' }],
  evidence: [ev('ev-03', '실리콘 몰드 조각'), ev('ev-01', '출입 로그')],
}

it('필수 항목을 고르고 확인 단계를 거쳐야 제출한다', async () => {
  const onSubmit = vi.fn()
  render(<DeductionForm {...props} onSubmit={onSubmit} />)
  expect(screen.getByRole('button', { name: '추리 제출' })).toBeDisabled()
  expect(screen.getByText('범인, 동기, 수법을(를) 골라야 제출할 수 있다.')).toBeInTheDocument()

  await userEvent.click(screen.getByLabelText(/윤재민/))
  await userEvent.selectOptions(screen.getByLabelText('동기'), 'm1')
  await userEvent.selectOptions(screen.getByLabelText('수법'), 'x1')
  await userEvent.click(screen.getByLabelText(/실리콘 몰드 조각/))
  await userEvent.type(screen.getByLabelText('추리 과정'), '  몰드로 만든 모조품  ')

  await userEvent.click(screen.getByRole('button', { name: '추리 제출' }))
  expect(onSubmit).not.toHaveBeenCalled()
  expect(screen.getByRole('alert')).toHaveTextContent('제출하면 수사가 끝나고')

  await userEvent.click(screen.getByRole('button', { name: '확정하고 제출' }))
  expect(onSubmit).toHaveBeenCalledWith({
    culprit_id: 's3',
    motive_id: 'm1',
    method_id: 'x1',
    evidence_ids: ['ev-03'],
    narrative: '몰드로 만든 모조품',
  })
})

it('더 수사하기를 누르면 확인 단계가 취소된다', async () => {
  render(<DeductionForm {...props} onSubmit={() => {}} />)
  await userEvent.click(screen.getByLabelText(/한서윤/))
  await userEvent.selectOptions(screen.getByLabelText('동기'), 'm1')
  await userEvent.selectOptions(screen.getByLabelText('수법'), 'x1')
  await userEvent.click(screen.getByRole('button', { name: '추리 제출' }))
  await userEvent.click(screen.getByRole('button', { name: '더 수사하기' }))
  expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  expect(screen.getByRole('button', { name: '추리 제출' })).toBeEnabled()
})
