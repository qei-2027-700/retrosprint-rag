<script setup lang="ts">
import { createApiClient } from '~/api/client'
const config = useRuntimeConfig()
const { healthState, echoState, message, reply, echoError, canSend, checkHealth, sendEcho, updateMessage }
  = useConnectivity(createApiClient(config.public.apiBaseUrl))
</script>

<template>
  <div class="page-heading">
    <p class="eyebrow">DEVELOPMENT / 接続テスト</p>
    <h1>APIとの接続を確かめる</h1>
    <p class="description">接続確認とメッセージの送受信を試せます。</p>
    <p class="endpoint">接続先：{{ config.public.apiBaseUrl }}</p>
  </div>
  <div class="cards">
    <ConnectivityApiHealthCard :state="healthState" @check="checkHealth" />
    <ConnectivityEchoFormCard :message="message" :state="echoState" :reply="reply"
      :error="echoError" :can-send="canSend" @update="updateMessage" @send="sendEcho" />
  </div>
</template>
