<script setup lang="ts">
const route = useRoute()
const drawer = ref<HTMLDialogElement>()
const menu = ref<HTMLButtonElement>()
function openDrawer() { drawer.value?.showModal() }
function closeDrawer() { drawer.value?.close() }
function restoreFocus() { menu.value?.focus() }
function backdrop(event: MouseEvent) {
  if (event.target === drawer.value) closeDrawer()
}
function trapFocus(event: KeyboardEvent) {
  if (event.key !== 'Tab') return
  const controls = drawer.value?.querySelectorAll<HTMLElement>('button:not([disabled]), a[href]')
  const first = controls?.[0]
  const last = controls?.[controls.length - 1]
  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault()
    last?.focus()
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault()
    first?.focus()
  }
}
let desktop: MediaQueryList | undefined
function onBreakpoint(event: MediaQueryListEvent) {
  if (event.matches) closeDrawer()
}
onMounted(() => {
  desktop = window.matchMedia('(min-width: 768px)')
  desktop.addEventListener('change', onBreakpoint)
})
onBeforeUnmount(() => desktop?.removeEventListener('change', onBreakpoint))
</script>

<template>
  <a href="#main" class="skip-link">本文へ移動</a>
  <div class="app-shell">
    <aside class="desktop-sidebar"><AppSidebar /></aside>
    <div class="main-shell">
      <header class="mobile-header">
        <button ref="menu" aria-label="メニューを開く" aria-controls="mobile-drawer"
          aria-haspopup="dialog" class="menu-button" @click="openDrawer">☰</button>
        <span>{{ route.path === "/" ? "チャット" : "Retrosprint" }}</span>
      </header>
      <main id="main" tabindex="-1"><slot /></main>
    </div>
  </div>
  <dialog id="mobile-drawer" ref="drawer" aria-label="メニュー" @click="backdrop" @close="restoreFocus" @keydown="trapFocus">
    <div class="drawer-panel">
      <button class="close-button secondary" autofocus aria-label="メニューを閉じる" @click="closeDrawer">閉じる ×</button>
      <AppSidebar @navigate="closeDrawer" />
    </div>
  </dialog>
</template>
