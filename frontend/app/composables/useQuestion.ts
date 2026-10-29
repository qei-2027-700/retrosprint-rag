import { computed, ref } from 'vue'
import type { createApiClient } from '../api/client'
import type { components } from '../api/generated/schema'

type Result = components['schemas']['Answered'] | components['schemas']['InsufficientEvidence']
export function useQuestion(client: ReturnType<typeof createApiClient>) {
  const input = ref('')
  const retrievalMode = ref<'monthly_reflection' | 'related_search'>('related_search')
  const reflectionMonth = ref('')
  const submitted = ref('')
  const result = ref<Result>()
  const state = ref<'idle' | 'pending' | 'success' | 'validation' | 'http' | 'network'>('idle')
  const error = ref('')
  const pending = computed(() => state.value === 'pending')
  function reset() {
    if (pending.value) return
    retrievalMode.value = 'related_search'; reflectionMonth.value = ''
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
    if ((retrievalMode.value === 'monthly_reflection' && !reflectionMonth.value) ||
      (reflectionMonth.value && !/^(?!0000)[0-9]{4}-(0[1-9]|1[0-2])$/.test(reflectionMonth.value))) {
      state.value = 'validation'; error.value = '用途と対象年月を確認してください。月の振り返りには年月が必要です。'
      return
    }
    submitted.value = question
    state.value = 'pending'
    try {
      const { data, response, error: apiError } = await client.POST('/api/questions', {
        body: { question, retrieval_mode: retrievalMode.value, reflection_month: reflectionMonth.value || null }, signal: AbortSignal.timeout(65000),
      })
      if (data) { result.value = data; state.value = 'success' }
      else if (response.status === 422) {
        state.value = 'validation'; error.value = '質問・用途・対象年月を確認してください。'
      } else {
        state.value = 'http'; error.value = apiError && 'message' in apiError ? apiError.message : '回答処理に失敗しました。もう一度送信してください。'
      }
    } catch {
      state.value = 'network'; error.value = '通信できませんでした。接続を確認して再送してください。'
    }
  }
  return { retrievalMode, reflectionMonth, input, submitted, result, state, error, pending, reset, send }
}
