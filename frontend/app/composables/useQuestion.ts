import { computed, ref } from 'vue'
import type { createApiClient } from '../api/client'
import type { components } from '../api/generated/schema'

type Result = components['schemas']['Answered'] | components['schemas']['InsufficientEvidence']
export function useQuestion(client: ReturnType<typeof createApiClient>) {
  const input = ref('')
  const submitted = ref('')
  const result = ref<Result>()
  const state = ref<'idle' | 'pending' | 'success' | 'validation' | 'http' | 'network'>('idle')
  const error = ref('')
  const pending = computed(() => state.value === 'pending')
  function reset() {
    if (pending.value) return
    input.value = ''; submitted.value = ''; result.value = undefined; error.value = ''; state.value = 'idle'
  }
  async function send() {
    if (pending.value) return
    result.value = undefined; error.value = ''
    const question = input.value.trim()
    if (!question || [...question].length > 2000) {
      state.value = 'validation'
      error.value = '質問は前後の空白を除いて1〜2,000文字で入力してください。'
      return
    }
    submitted.value = question
    state.value = 'pending'
    try {
      const { data, response } = await client.POST('/api/questions', {
        body: { question }, signal: AbortSignal.timeout(10000),
      })
      if (data) { result.value = data; state.value = 'success' }
      else if (response.status === 422) {
        state.value = 'validation'; error.value = '質問は前後の空白を除いて1〜2,000文字で入力してください。'
      } else {
        state.value = 'http'; error.value = '回答処理に失敗しました。もう一度送信してください。'
      }
    } catch {
      state.value = 'network'; error.value = '通信できませんでした。接続を確認して再送してください。'
    }
  }
  return { input, submitted, result, state, error, pending, reset, send }
}
