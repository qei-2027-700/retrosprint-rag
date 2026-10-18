import { execFileSync } from 'node:child_process'

const paths = ['frontend/openapi', 'frontend/app/api/generated']
const status = execFileSync('git', ['status', '--porcelain', '--untracked-files=all', '--', ...paths], { encoding: 'utf8' })
if (status.trim()) {
  console.error('Generated API files differ from Git. Regenerate and commit them:\n' + status)
  process.exitCode = 1
}
