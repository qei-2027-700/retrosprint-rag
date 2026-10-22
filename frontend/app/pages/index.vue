<script setup lang="ts">
import { createApiClient } from '~/api/client'
useHead({ title: 'チャット | Retrosprint' })
const config = useRuntimeConfig()
const { input, submitted, result, state, error, pending, reset, send } = useQuestion(createApiClient(config.public.apiBaseUrl))
const chatBusy = useState('chat-busy', () => false)
const chatReset = useState('chat-reset', () => 0)
watch(pending, value => { chatBusy.value = value }, { flush: 'sync' })
watch(chatReset, reset)
onBeforeUnmount(() => { chatBusy.value = false })
function example() { if (!pending.value) input.value = '最近うまくいったことは？' }
</script>

<template>
  <section class="chat-page" aria-labelledby="chat-title">
    <header class="chat-header">
      <h1 id="chat-title">チャット</h1>
      <span class="demo-badge">合成資料を使ったデモ · 回答はfake</span>
    </header>
    <div class="chat-transcript" :aria-busy="pending">
      <div class="chat-column">
        <div v-if="!submitted" class="chat-welcome">
          <p class="eyebrow">REFLECT & MOVE FORWARD</p>
          <h2>振り返りから、<br>次の一歩を見つける。</h2>
          <p>記録をもとに質問し、回答の根拠を確かめられます。</p>
          <button class="example-question secondary" @click="example">最近うまくいったことは？ <span aria-hidden="true">↗</span></button>
          <p class="hint">この代表質問で回答を確認できます。ほかの質問は根拠不足になります。</p>
        </div>
        <template v-else>
          <article class="question-bubble"><h2>あなた</h2><p>{{ submitted }}</p></article>
          <article v-if="result" class="answer-block">
            <h2><span class="answer-mark" aria-hidden="true">✳</span> Retrosprint <small>fake</small></h2>
            <p v-if="result.status === 'insufficient_evidence'">回答の根拠となる資料が見つかりませんでした。質問を変えてお試しください。</p>
            <template v-else>
              <p class="answer-text">{{ result.answer.text }}</p>
              <section class="citations" aria-label="回答の出典">
                <h3>回答の根拠</h3>
                <div v-for="citation in result.citations" :key="citation.id" class="citation">
                  <p class="citation-title">[{{ citation.id }}] {{ citation.document_name }}</p>
                  <blockquote>{{ citation.quote }}</blockquote>
                  <details><summary>出典を確認</summary>
                    <dl><dt>文書ID / 版</dt><dd>{{ citation.document_id }} / {{ citation.content_version }}</dd>
                    <dt>対象年月 / 見出し</dt><dd>{{ citation.reflection_month }} / {{ citation.heading }}</dd></dl>
                    <h3>合成原文</h3><pre class="original-text">{{ citation.original_text }}</pre>
                  </details>
                </div>
              </section>
            </template>
          </article>
        </template>
        <p role="status" aria-live="polite" class="pending-status">{{ pending ? '回答を準備しています…' : '' }}</p>
      </div>
    </div>
    <footer class="composer-area">
      <form class="chat-column composer" @submit.prevent="send">
        <label for="question-input">質問</label>
        <textarea id="question-input" v-model="input" rows="2" placeholder="振り返りについて質問する"
          :disabled="pending" :aria-invalid="state === 'validation'" aria-describedby="question-help question-error" />
        <div class="composer-actions"><span id="question-help">Enterで改行 · 2,000文字まで</span>
          <button type="submit" class="chat-send" :disabled="pending">{{ pending ? '送信中…' : '送信' }} <span aria-hidden="true">↑</span></button></div>
        <p id="question-error" role="alert" class="error">{{ error }}</p>
      </form>
      <p class="chat-footnote">単一質問のデモです。会話・入力は保存されません。</p>
    </footer>
  </section>
</template>
