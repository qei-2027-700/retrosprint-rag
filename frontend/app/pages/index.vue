<script setup lang="ts">
import { createApiClient } from '~/api/client'
useHead({ title: 'チャット | Retrosprint' })
const config = useRuntimeConfig()
const { retrievalMode, reflectionMonth, input, submitted, result, state, error, pending, reset, send } = useQuestion(createApiClient(config.public.apiBaseUrl))
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
          <p class="hint">月の振り返りは2026年9月を選び「この月の成果と悩みを整理して」で確認できます。関連検索は代表質問をお試しください。</p>
        </div>
        <template v-else>
          <article class="question-bubble"><h2>あなた</h2><p>{{ submitted }}</p></article>
          <article v-if="result" class="answer-block">
            <h2><span class="answer-mark" aria-hidden="true">✳</span> Retrosprint <small>fake</small></h2>
            <p>用途：{{ result.retrieval_mode === 'monthly_reflection' ? '月の振り返り' : '関連する経験の検索' }} · 対象月：{{ result.reflection_month || '指定なし' }}</p>
            <p>取得範囲：{{ result.coverage.scope === 'month_documents' ? '対象月の文書全文' : '関連箇所（最大5箇所・網羅しません）' }}</p>
            <p>取得 {{ result.coverage.documents_retrieved }}件 / 生成入力 {{ result.coverage.documents_used }}件 · 全文入力：{{ result.coverage.complete ? '完了' : '対象外または未完了' }} · 省略：{{ result.coverage.omitted ? 'あり' : 'なし' }}</p>
            <p>状態：{{ result.status }} · 確認日時：{{ result.coverage.checked_at }}</p>
            <p v-if="result.message">{{ result.message }}</p>
            <template v-if="result.status === 'answered'">
              <p class="answer-text">{{ result.answer.text }}</p>
              <section class="citations" aria-label="回答の出典">
                <h3>回答の根拠</h3>
                <div v-for="citation in result.citations" :key="citation.id" class="citation">
                  <p class="citation-title">[{{ citation.id }}] {{ citation.document_name || '名称未設定' }}</p>
                  <blockquote>{{ citation.quote }}</blockquote>
                  <details><summary>出典を確認</summary>
                    <dl><dt>文書ID / 版</dt><dd>{{ citation.document_id }} / {{ citation.content_version }}</dd>
                    <dt>対象年月 / 見出し</dt><dd>{{ citation.reflection_month }} / {{ citation.heading || '未設定' }}</dd></dl>
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
        <div class="retrieval-controls">
          <div><label for="retrieval-mode">用途</label>
            <select id="retrieval-mode" v-model="retrievalMode" :disabled="pending">
              <option value="related_search">関連する経験の検索</option><option value="monthly_reflection">月の振り返り</option>
            </select></div>
          <div><label for="reflection-month">対象年月{{ retrievalMode === 'monthly_reflection' ? '（必須）' : '（任意）' }}</label>
            <input id="reflection-month" v-model="reflectionMonth" type="month" min="0001-01" max="9999-12" :disabled="pending">
          </div>
        </div>
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
