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

function assertSafeAnchors(doc) {
  for (const a of doc.querySelectorAll('a[href]')) {
    assert.ok(
      a.protocol === 'https:' || a.protocol === 'http:',
      `anchor href "${a.getAttribute('href')}" has unsafe protocol "${a.protocol}"`,
    )
  }
}

test('no anchor on any tab carries a javascript: or data: URL from the payload', async () => {
  const payload = structuredClone(PAYLOAD)
  // Duplicate backlog/wip entries in the shared PAYLOAD trip the each_key_duplicate
  // crash on todo-keyed tabs (Todo, Matrix); reset as smoke.todos.test.js does.
  payload.data.repos[0].prds = { backlog: [], wip: [], done_count: 0 }
  payload.data.repos[0].ci = [
    { workflow: 'hostile-deploy', status: 'completed', conclusion: 'failure', url: 'javascript:window.__m=1', date: new Date(0).toISOString() },
    { workflow: 'safe-deploy', status: 'completed', conclusion: 'success', url: 'https://example.org/run/safe', date: new Date(0).toISOString() },
  ]
  payload.data.repos[0].security = [
    { severity: 'critical', title: 'Hostile security alert', url: 'javascript:window.__m=1' },
    { severity: 'critical', title: 'Safe security alert', url: 'https://example.org/security/safe' },
  ]
  payload.data.external = {
    error: null,
    review_requested: [
      { number: 7, title: 'Hostile external PR', repo: 'acme/widget', url: 'data:text/html,x', created: '2026-08-01' },
      { number: 8, title: 'Safe external PR', repo: 'acme/widget', url: 'https://example.org/pr/safe', created: '2026-08-01' },
    ],
    authored: [],
  }
  payload.epics.todos = [
    { id: 't1', repo: 'buvis/demo', action: 'Hostile todo action', url: 'data:text/html,x' },
    { id: 't2', repo: 'buvis/demo', action: 'Safe todo action', url: 'https://example.org/todo/safe' },
  ]
  const { doc, openTab, flush } = render(payload)
  const hrefs = () => [...doc.querySelectorAll('a[href]')].map((a) => a.getAttribute('href'))
  await openTab('Todo')
  assertSafeAnchors(doc)
  assert.match(doc.querySelector('main').textContent, /Hostile todo action/, 'hostile todo label missing from Todo tab')
  assert.ok(hrefs().includes('https://example.org/todo/safe'), 'safe todo anchor missing its href')
  await openTab('Work')
  assertSafeAnchors(doc)
  const workText = doc.querySelector('main').textContent
  assert.match(workText, /hostile-deploy/, 'hostile CI label missing from Work tab')
  assert.match(workText, /Hostile external PR/, 'hostile external PR label missing from Work tab')
  assert.ok(hrefs().includes('https://example.org/run/safe'), 'safe CI anchor missing its href')
  assert.ok(hrefs().includes('https://example.org/pr/safe'), 'safe external PR anchor missing its href')
  await openTab('Matrix')
  assertSafeAnchors(doc)
  assert.match(doc.querySelector('main').textContent, /Hostile security alert/, 'hostile security label missing from Matrix tab')
  assert.ok(hrefs().includes('https://example.org/todo/safe'), 'safe todo anchor missing its href on Matrix tab')
  await openTab('Repos')
  const repoButton = doc.querySelector('button.card')
  assert.ok(repoButton, 'missing repo card button')
  repoButton.click()
  await flush()
  const panel = doc.querySelector('div.panel[role="dialog"]')
  assert.ok(panel, 'missing repo detail panel')
  assertSafeAnchors(doc)
  const panelHrefs = [...panel.querySelectorAll('a[href]')].map((a) => a.getAttribute('href'))
  assert.ok(panelHrefs.includes('https://example.org/security/safe'), 'safe security anchor missing its href in RepoDetail panel')
  assert.ok(panelHrefs.includes('https://example.org/run/safe'), 'safe CI anchor missing its href in RepoDetail panel')
  assert.match(panel.textContent, /Hostile security alert/, 'hostile security label missing from RepoDetail panel')
  assert.match(panel.textContent, /hostile-deploy/, 'hostile workflow name missing from RepoDetail panel')
})
