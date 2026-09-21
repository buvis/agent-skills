// The duplicate-rendering test below relies on the each_key_duplicate regression note atop smoke.repos.test.js.
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { PAYLOAD, render } from './smoke.harness.js'

test('Work tab and RepoDetail panel render both instances of a duplicated issue label, not once', async () => {
  const payload = structuredClone(PAYLOAD)
  payload.data.repos[0].issues = [
    { number: 7, title: 'Some issue', created: '2026-08-01', comments: 0, labels: ['bug', 'bug'] },
  ]

  const { doc, openTab, flush } = render(payload)

  await openTab('Work')
  assert.ok(doc.querySelector('main').textContent.trim().length > 0, 'Work tab is blank')
  const workChips = [...doc.querySelectorAll('main span.lbl')].filter(
    (n) => n.textContent.trim() === 'bug',
  )
  assert.equal(workChips.length, 2, `expected 2 "bug" chips on Work tab, got ${workChips.length}`)

  await openTab('Repos')
  const repoButton = doc.querySelector('button.card')
  assert.ok(repoButton, 'missing repo card button')
  repoButton.click()
  await flush()
  const panel = doc.querySelector('div.panel[role="dialog"]')
  assert.ok(panel, 'missing repo detail panel')
  const panelChips = [...panel.querySelectorAll('span.lbl')].filter(
    (n) => n.textContent.trim() === 'bug',
  )
  assert.equal(panelChips.length, 2, `expected 2 "bug" chips in RepoDetail panel, got ${panelChips.length}`)
})

test('Work tab shows the external PR lookup error instead of an empty section', async () => {
  const payload = structuredClone(PAYLOAD)
  payload.data.external = { error: 'gh auth login', review_requested: [], authored: [] }

  const { doc, openTab } = render(payload)
  await openTab('Work')
  const mainText = doc.querySelector('main').textContent
  assert.match(mainText, /Waiting on you elsewhere/, 'external-PR section heading missing')
  assert.match(mainText, /gh auth login/, 'external lookup error message not shown')
})

test('Work tab has no "Waiting on you elsewhere" section when there is no external data', async () => {
  const { doc, openTab } = render()
  await openTab('Work')
  const mainText = doc.querySelector('main').textContent
  assert.doesNotMatch(mainText, /Waiting on you elsewhere/)
})

test('Work tab shows "No CI runs." on the CI wall when no repo has CI data', async () => {
  // The default PAYLOAD repo carries no `ci` key at all (the "never
  // fetched" case), which derives ciRows to an empty array — the CI wall
  // must render an empty-state message instead of going blank.
  const { doc, openTab } = render()
  await openTab('Work')
  const mainText = doc.querySelector('main').textContent
  assert.match(mainText, /No CI runs/)
})

test('Work tab names a never-fetched-CI repo below the wall, alongside the wall\'s own empty state', async () => {
  // The default PAYLOAD repo carries no `ci` key at all — CI was never
  // fetched for it, distinct from a fetched-but-empty `ci: []`. The wall
  // itself is empty (no repo has a `ci` array with rows), so both the
  // "No CI runs." empty state and the exclusion line naming the repo must
  // show up together.
  const { doc, openTab } = render()
  await openTab('Work')
  const mainText = doc.querySelector('main').textContent
  assert.match(mainText, /No CI runs/)
  assert.match(mainText, /not collected this run/)
  assert.match(mainText, /buvis\/demo/)
})

test('Work tab does not name a repo with `ci: []` as not collected this run', async () => {
  // `ci: []` means CI was fetched and came back empty — a different case
  // from the default payload's missing `ci` key. The wall still renders its
  // empty state, but the repo must not appear in the exclusion line.
  const payload = structuredClone(PAYLOAD)
  payload.data.repos[0].ci = []

  const { doc, openTab } = render(payload)
  await openTab('Work')
  const mainText = doc.querySelector('main').textContent
  assert.match(mainText, /No CI runs/)
  assert.doesNotMatch(mainText, /not collected this run/)
})

test('Work tab shows the not-collected-this-run line even when the CI wall has rows from another repo', async () => {
  // The exclusion line and the wall's empty state are independent: a wall
  // that already has rows (repo A's fetched, non-empty `ci` array) must still
  // carry the "not collected this run" line for a different repo (repo B,
  // with no `ci` key at all).
  const payload = structuredClone(PAYLOAD)
  payload.data.repos = [
    {
      owner: 'acme', name: 'widget-a', org: 'acme',
      ci: [
        { workflow: 'deploy-prod', status: 'completed', conclusion: 'success', url: 'https://example.org/run/1', date: new Date(0).toISOString() },
      ],
    },
    { owner: 'acme', name: 'widget-b', org: 'acme' },
  ]

  const { doc, openTab } = render(payload)
  await openTab('Work')
  const mainText = doc.querySelector('main').textContent
  assert.match(mainText, /deploy-prod/, 'wall does not show the fetched repo\'s workflow row')
  assert.match(mainText, /not collected this run/)
  assert.match(
    mainText,
    /1 not collected this run:\s*acme\/widget-b/,
    'exclusion line should name only the never-fetched repo',
  )
  assert.doesNotMatch(mainText, /No CI runs/, 'empty state should not show once the wall has rows')
})
