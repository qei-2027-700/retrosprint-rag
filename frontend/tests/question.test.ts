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
