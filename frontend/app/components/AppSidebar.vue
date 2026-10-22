<script setup lang="ts">
const emit = defineEmits<{ navigate: [] }>()
const route = useRoute()
const chatBusy = useState('chat-busy', () => false)
const chatReset = useState('chat-reset', () => 0)
async function newChat() {
  if (chatBusy.value) return
  chatReset.value++
  await navigateTo('/')
  emit('navigate')
}
</script>

<template>
  <div class="sidebar-content">
    <div class="sidebar-top">
      <p class="brand">Retrosprint<span>振り返りを、次の一歩へ。</span></p>
      <nav aria-label="メニュー">
        <button class="new-chat" :disabled="chatBusy" @click="newChat"><span aria-hidden="true">＋</span> 新しいチャット</button>
      </nav>
    </div>
    <section class="session-list" aria-label="チャット履歴">
      <h2>チャット履歴</h2>
      <p>履歴保存は未対応です</p>
    </section>
    <div class="sidebar-footer"><NuxtLink to="/dev/connectivity" :aria-current="route.path === '/dev/connectivity' ? 'page' : undefined" @click="emit('navigate')">接続テスト（開発用）</NuxtLink><p>ローカル開発専用 · fake版</p></div>
  </div>
</template>
