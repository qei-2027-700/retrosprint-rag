import { computed, ref } from 'vue'
import type { createApiClient } from '../api/client'

type State = 'idle' | 'pending' | 'success' | 'validation' | 'http' | 'network'

export function useConnectivity(client: ReturnType<typeof createApiClient>) {
  const healthState = ref<State>('idle')
  const echoState = ref<State>('idle')
  const message = ref('')
  const reply = ref('')
  const echoError = ref('')
  const canSend = computed(() => message.value.trim().length > 0 && echoState.value !== 'pending')

  async function checkHealth() {
    if (healthState.value === 'pending') return
    healthState.value = 'pending'
    try {
      const { data } = await client.GET('/health', { signal: AbortSignal.timeout(10000) })
      healthState.value = data?.status === 'ok' ? 'success' : 'http'
    } catch {
      healthState.value = 'network'
    }
  }

  async function sendEcho() {
    if (!canSend.value) return
    echoState.value = 'pending'
    reply.value = ''
    echoError.value = ''
    try {
      const { data, error, response } = await client.POST('/api/v1/dev/echo', {
        body: { message: message.value },
        signal: AbortSignal.timeout(10000),
      })
      if (data) {
        reply.value = data.message
        echoState.value = 'success'
      } else if (response.status === 422 && error?.detail) {
        // The validation response is inferred from the generated OpenAPI contract.
        echoError.value = error.detail.some(issue => issue.loc.includes('message'))
          ? 'メッセージは前後の空白を除いて1〜200文字で入力してください。'
          : '入力内容を確認してください。'
        echoState.value = 'validation'
      } else {
        echoError.value = `APIがエラーを返しました（HTTP ${response.status}）。設定を確認して再送してください。`
        echoState.value = 'http'
      }
    } catch {
      echoError.value = '通信できませんでした。APIの起動と接続先を確認して再送してください。'
      echoState.value = 'network'
    }
  }

  function updateMessage(value: string) {
    if (echoState.value === 'pending') return
    message.value = value
    reply.value = ''
    echoError.value = ''
    echoState.value = 'idle'
  }

  return { healthState, echoState, message, reply, echoError, canSend, checkHealth, sendEcho, updateMessage }
}
