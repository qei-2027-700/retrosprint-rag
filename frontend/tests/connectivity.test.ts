import { expect, test, vi } from 'vitest'
import { createApiClient } from '../app/api/client'
import { useConnectivity } from '../app/composables/useConnectivity'

test('pending state prevents duplicate requests and editing; response comes from the server', async () => {
  let finish: (response: Response) => void = () => { throw new Error('request not started') }
  const fetch = vi.fn(() => new Promise<Response>(resolve => { finish = resolve }))
  vi.stubGlobal('fetch', fetch)
  try {
    const state = useConnectivity(createApiClient('http://localhost:8000'))
    state.updateMessage('input')
    const pending = state.sendEcho()
    expect(state.echoState.value).toBe('pending')
    state.updateMessage('other')
    await state.sendEcho()
    expect(state.message.value).toBe('input')
    expect(fetch).toHaveBeenCalledTimes(1)
    finish(Response.json({ message: 'server response' }))
    await pending
    expect(state.reply.value).toBe('server response')
    state.updateMessage('new input')
    expect(state.reply.value).toBe('')
    expect(state.echoState.value).toBe('idle')
  } finally {
    vi.unstubAllGlobals()
  }
})
