<script setup lang="ts">
defineProps<{ message: string; state: string; reply: string; error: string; canSend: boolean }>()
const emit = defineEmits<{ send: []; update: [value: string] }>()
function onInput(event: Event) {
  if (event.target instanceof HTMLTextAreaElement) emit('update', event.target.value)
}
</script>

<template>
  <section class="card" aria-labelledby="echo-title">
    <p class="eyebrow">02 / ECHO</p>
    <h2 id="echo-title">メッセージ送信</h2>
    <p class="description">入力した内容をAPIに送り、返ってきた応答を表示します。</p>
    <form :aria-busy="state === 'pending'" @submit.prevent="$emit('send')">
      <label for="message">メッセージ</label>
      <p id="message-hint" class="hint">前後の空白を除いて1〜200文字。内容は保存されません。</p>
      <textarea id="message" :value="message" rows="5" :disabled="state === 'pending'"
        :aria-invalid="state === 'validation'" aria-describedby="message-hint echo-error"
        placeholder="例：疎通確認" @input="onInput" />
      <button class="primary" :disabled="!canSend" type="submit">
        {{ state === 'pending' ? '送信中…' : '送信する' }}
      </button>
    </form>
    <div role="status" aria-live="polite" class="echo-result">
      <p id="echo-error" class="error">{{ error }}</p>
      <p v-if="state === 'pending'">応答を待っています…</p>
      <template v-else-if="state === 'success'">
        <h3>APIからの応答</h3>
        <p class="response" data-testid="echo-response">{{ reply }}</p>
      </template>
      <p v-else-if="state === 'idle'" class="hint">送信すると、ここにAPIの応答が表示されます。</p>
    </div>
  </section>
</template>
