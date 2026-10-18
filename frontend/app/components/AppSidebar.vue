<script setup lang="ts">
defineEmits<{ navigate: [] }>()
</script>

<template>
  <div class="sidebar-content">
    <div class="sidebar-top">
      <p class="brand">Retrosprint<span>振り返りを、次の一歩へ。</span></p>
      <nav aria-label="メニュー">
        <NuxtLink to="/" aria-current="page" @click="$emit('navigate')">接続テスト</NuxtLink>
      </nav>
    </div>
    <section class="session-list" aria-labelledby="history-title">
      <h2 id="history-title">過去のセッション</h2>
      <p>会話履歴はまだありません</p>
    </section>
    <p class="sidebar-footer">開発用の疎通確認画面</p>
  </div>
</template>
