import { expect, test } from '@playwright/test'
import { spawn, type ChildProcess } from 'node:child_process'
import { openSync, closeSync, mkdirSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

const root = fileURLToPath(new URL('../../../', import.meta.url))
let backend: ChildProcess | undefined
async function startBackend() {
  // A pre-existing server must never make this test pass accidentally.
  try {
    await fetch('http://localhost:8000/health')
    throw new Error('Port 8000 is already in use; stop the existing API before running E2E')
  } catch (error) {
    if (!(error instanceof TypeError)) throw error
  }
  mkdirSync(new URL('../../../.logs/', import.meta.url), { recursive: true })
  const log = openSync(new URL('../../../.logs/e2e-backend.log', import.meta.url), 'a')
  backend = spawn('uv', ['run', '--directory', 'backend', 'uvicorn', 'retrosprint_rag.main:create_app',
    '--factory', '--host', 'localhost', '--port', '8000'], {
    cwd: root, env: { ...process.env, RETROSPRINT_ENABLE_DEV_API: 'true', RETROSPRINT_CORS_ORIGINS: '["http://localhost:3000"]' },
    detached: true, stdio: ['ignore', log, log],
  })
  closeSync(log)
  await expect.poll(async () => {
    if (backend?.exitCode !== null) throw new Error('Backend exited; see .logs/e2e-backend.log')
    try { return (await fetch('http://localhost:8000/health')).status } catch { return 0 }
  }).toBe(200)
}
async function stopBackend() {
  const current = backend
  backend = undefined
  if (!current?.pid || current.exitCode !== null) return
  const stopped = new Promise<void>(resolve => current.once('exit', () => resolve()))
  process.kill(-current.pid, 'SIGTERM')
  await stopped
}

test.beforeAll(startBackend)
test.afterAll(stopBackend)

for (const width of [320, 390, 768, 1280]) {
  test(`real API and responsive layout at ${width}px`, async ({ page }, testInfo) => {
    const errors: string[] = []
    page.on('pageerror', error => errors.push(error.message))
    await page.setViewportSize({ width, height: 850 })
    await page.goto('/dev/connectivity')
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible()
    await expect(page.getByText('未確認です')).toBeVisible()
    await page.keyboard.press('Tab')
    await expect(page.getByRole('link', { name: '本文へ移動' })).toBeFocused()
    await expect(page.getByRole('link', { name: '本文へ移動' })).toHaveCSS('opacity', '1')
    await page.getByRole('button', { name: '接続を確認' }).click()
    await expect(page.getByText('接続できました', { exact: true })).toBeVisible()
    if (width < 768) {
      const open = page.getByRole('button', { name: 'メニューを開く' })
      await open.click()
      const dialog = page.getByRole('dialog')
      await expect(dialog).toBeVisible()
      // Native modal dialog keeps keyboard focus inside the drawer.
      for (let i = 0; i < 4; i++) {
        await page.keyboard.press('Tab')
        expect(await dialog.evaluate(node => node.contains(document.activeElement))).toBe(true)
      }
      await page.keyboard.press('Escape')
      await expect(dialog).not.toBeVisible()
      await expect(open).toBeFocused()
      await open.click()
      await page.getByRole('button', { name: 'メニューを閉じる' }).click()
      await expect(open).toBeFocused()
      await open.click()
      await page.mouse.click(width - 5, 400)
      await expect(dialog).not.toBeVisible()
      await open.click()
      await dialog.getByRole('link', { name: '接続テスト（開発用）' }).click()
      await expect(dialog).not.toBeVisible()
    }
    const message = `  https://example.com/${'a'.repeat(150)}  `
    await page.getByLabel('メッセージ', { exact: true }).fill(message)
    const response = page.waitForResponse(r => r.url().endsWith('/api/v1/dev/echo') && r.status() === 200)
    await page.getByRole('button', { name: '送信する' }).click()
    await response
    await expect(page.getByTestId('echo-response')).toHaveText(message.trim())
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
    await page.screenshot({ path: testInfo.outputPath(`connectivity-${width}.png`), fullPage: true })
    expect(errors).toEqual([])
  })
}

for (const width of [320, 390, 768, 1280]) {
  test(`real 422, stopped backend and retry at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 850 })
    const errors: string[] = []
    page.on('pageerror', error => errors.push(error.message))
    await page.goto('/dev/connectivity')
    const input = page.getByLabel('メッセージ', { exact: true })
    const send = page.getByRole('button', { name: '送信する' })
    await input.fill('a'.repeat(201))
    const invalid = page.waitForResponse(r => r.url().endsWith('/api/v1/dev/echo') && r.status() === 422)
    await send.click()
    await invalid
    await expect(page.getByText('メッセージは前後の空白を除いて1〜200文字で入力してください。')).toBeVisible()
    await expect(input).toHaveAttribute('aria-invalid', 'true')
    await expect(input).toHaveValue('a'.repeat(201))
    await input.fill('再送の確認')
    await stopBackend()
    await send.click()
    await expect(page.getByText('通信できませんでした。APIの起動と接続先を確認して再送してください。')).toBeVisible()
    await expect(input).toHaveValue('再送の確認')
    await page.getByRole('button', { name: '接続を確認' }).click()
    await expect(page.getByText('接続できませんでした。APIの起動と接続先を確認してください。')).toBeVisible()
    await startBackend()
    await send.click()
    await expect(page.getByTestId('echo-response')).toHaveText('再送の確認')
    await input.fill('新しい入力')
    await expect(page.getByTestId('echo-response')).toHaveCount(0)
    expect(errors).toEqual([])
  })
}

for (const width of [320, 390, 768, 1280]) {
  test(`question, evidence and failures at ${width}px`, async ({ page }, testInfo) => {
    await page.setViewportSize({ width, height: 850 })
    await page.goto('/')
    const input = page.getByLabel('質問', { exact: true })
    const send = page.getByRole('button', { name: '送信', exact: true })
    await page.getByRole('button', { name: '最近うまくいったことは？' }).click()
    const answered = page.waitForResponse(r => r.url().endsWith('/api/questions') && r.status() === 200)
    await send.click()
    await answered
    await expect(page.getByText('作業を小さく分けることで、着手しやすくなっています。')).toBeVisible()
    await page.getByText('出典を確認', { exact: true }).click()
    await expect(page.getByRole('heading', { name: '合成原文' })).toBeVisible()
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
    const transcript = page.locator('.chat-transcript')
    const composer = page.locator('.composer-area')
    const t = await transcript.boundingBox(); const c = await composer.boundingBox()
    expect(t!.y + t!.height).toBeLessThanOrEqual(c!.y + 1)
    await page.screenshot({ path: testInfo.outputPath(`chat-source-${width}.png`), fullPage: true })
    await input.fill('根拠のない質問')
    await send.click()
    await expect(page.getByText('回答の根拠となる資料が見つかりませんでした。質問を変えてお試しください。')).toBeVisible()
    await input.fill('処理失敗の確認')
    await send.click()
    await expect(page.getByRole('alert')).toHaveText('回答処理に失敗しました。もう一度送信してください。')
    await expect(input).toHaveValue('処理失敗の確認')
    await input.fill('a'.repeat(2001)); await send.click()
    await expect(input).toHaveAttribute('aria-invalid', 'true')
    await input.fill('最近うまくいったことは？')
    await stopBackend(); await send.click()
    await expect(page.getByRole('alert')).toHaveText('通信できませんでした。接続を確認して再送してください。')
    await expect(input).toHaveValue('最近うまくいったことは？')
    await startBackend(); await send.click()
    await expect(page.getByText('作業を小さく分けることで、着手しやすくなっています。')).toBeVisible()
    if (width < 768) await page.getByRole('button', { name: 'メニューを開く' }).click()
    await page.getByRole('button', { name: '新しいチャット' }).filter({ visible: true }).click()
    await expect(input).toHaveValue('')
    await expect(page.getByText('振り返りから、')).toBeVisible()
  })
}
