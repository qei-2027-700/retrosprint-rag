import { expect, test, vi } from 'vitest'
import { createApiClient } from '../app/api/client'
import { useQuestion } from '../app/composables/useQuestion'

test('a pending request prevents duplicate sends and reset; failure retains input', async () => {
  let finish!: (value: Response) => void
  const fetcher = vi.spyOn(globalThis, 'fetch').mockImplementation(() => new Promise(resolve => { finish = resolve }))
  const chat = useQuestion(createApiClient('http://localhost:8000'))
  chat.input.value = '最近うまくいったことは？'
  const request = chat.send()
  await vi.waitFor(() => expect(fetcher).toHaveBeenCalledTimes(1))
  await chat.send(); chat.reset()
  expect(chat.pending.value).toBe(true)
  expect(chat.input.value).toBe('最近うまくいったことは？')
  finish(new Response(JSON.stringify({ code: 'question_processing_failed' }), { status: 500 }))
  await request
  expect(chat.state.value).toBe('http')
  expect(chat.input.value).toBe('最近うまくいったことは？')
  chat.reset()
  expect(chat.input.value).toBe('')
  expect(chat.error.value).toBe('')
  fetcher.mockRestore()
})

test('monthly mode validates month, sends explicit selection and retains it on failure', async () => {
  const fetcher = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify({ code: 'retrieval_failed', message: '資料を取得できませんでした。' }), { status: 503, headers: { 'Content-Type': 'application/json' } }))
  const chat = useQuestion(createApiClient('http://localhost:8000'))
  chat.input.value = 'この月の成果と悩みを整理して'
  chat.retrievalMode.value = 'monthly_reflection'
  await chat.send()
  expect(chat.state.value).toBe('validation')
  expect(fetcher).not.toHaveBeenCalled()
  chat.reflectionMonth.value = '2026-06'
  await chat.send()
  const request = fetcher.mock.calls[0]![0] as Request
  expect(await request.json()).toEqual({ question: chat.input.value, retrieval_mode: 'monthly_reflection', reflection_month: '2026-06' })
  expect(chat.error.value).toBe('資料を取得できませんでした。')
  expect(chat.reflectionMonth.value).toBe('2026-06')
  chat.reset()
  expect(chat.reflectionMonth.value).toBe('')
  expect(chat.retrievalMode.value).toBe('related_search')
  fetcher.mockRestore()
})
