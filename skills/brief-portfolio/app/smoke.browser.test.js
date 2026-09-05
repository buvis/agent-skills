import { mkdtempSync, readFileSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { pathToFileURL } from 'node:url'
import { expect, test } from '@playwright/test'
import { PAYLOAD, TEMPLATE } from './smoke.harness.js'

// The jsdom smokes prove the bundle mounts under a simulated DOM. This one
// proves the delivered artifact, a single HTML file opened from disk, mounts
// in a real browser on a file:// origin, where storage and clipboard behave
// differently from jsdom's https://example.org/.
test('the brief mounts in a real browser from a file:// page', async ({ page }) => {
  const html = readFileSync(TEMPLATE, 'utf8').replace(
    '__PORTFOLIO_PAYLOAD__',
    JSON.stringify(PAYLOAD).replace(/<\//g, '<\\/'),
  )
  const file = join(mkdtempSync(join(tmpdir(), 'brief-')), 'index.html')
  writeFileSync(file, html)

  const errors = []
  page.on('pageerror', (e) => errors.push(e.message))
  await page.goto(pathToFileURL(file).href)

  const nav = page.getByRole('navigation', { name: 'Sections' })
  await expect(nav).toBeVisible()
  await expect(nav.getByRole('button').first()).toBeVisible()
  expect(errors).toEqual([])
})
