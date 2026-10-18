<script setup lang="ts">
defineProps<{ state: string }>()
defineEmits<{ check: [] }>()
</script>

<template>
  <section class="card" aria-labelledby="health-title">
    <p class="eyebrow">01 / HEALTH</p>
    <h2 id="health-title">API接続</h2>
    <p class="description">バックエンドが応答できるか確認します。</p>
    <div class="status-box" role="status" aria-live="polite">
      <span v-if="state === 'idle'">未確認です</span>
      <span v-else-if="state === 'pending'">接続を確認しています…</span>
      <span v-else-if="state === 'success'" class="success">接続できました</span>
      <span v-else class="error">接続できませんでした。APIの起動と接続先を確認してください。</span>
    </div>
    <button class="secondary" :disabled="state === 'pending'" @click="$emit('check')">
      {{ state === 'pending' ? '確認中…' : '接続を確認' }}
    </button>
  </section>
</template>
