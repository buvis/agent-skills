import { defineConfig } from '@playwright/test'

// Only the browser smoke runs under Playwright; the node:test suites keep
// their own runner (`npm test`). The brief is a single file opened from disk,
// so there is no webServer: the spec writes a rendered page and opens it via
// file://, which is how the product is actually delivered.
export default defineConfig({
  testMatch: 'smoke.browser.test.js',
  reporter: 'list',
})
