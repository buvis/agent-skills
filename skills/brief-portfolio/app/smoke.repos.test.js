// Regression: {#each} blocks keyed by a list item's own value (instead of a
// stable id or index) throw `each_key_duplicate` when two items share that
// value. On the default tab this blanks the whole page at mount; on other
// tabs, or nested panels, it silently breaks the tab/panel switch. Either
// way, duplicate-valued items should render twice, not crash.

import { test } from 'node:test'
import assert from 'node:assert/strict'
import { PAYLOAD, render } from './smoke.harness.js'

// Finds the heading/label element matching `text` among `selector` candidates
// inside `container`, then reads its next sibling `<ul>` and returns the
// `<li>` elements inside it. Doesn't assume DOM order beyond "list follows
// its heading", since that's the only layout fact given.
function backlogListItems(container, selector, text) {
  const heading = [...container.querySelectorAll(selector)].find(
    (n) => n.textContent.trim() === text,
  )
  assert.ok(heading, `no ${selector} reading "${text}"`)
  const ul = heading.nextElementSibling
  assert.ok(ul && ul.tagName === 'UL', `expected a <ul> right after ${selector} "${text}"`)
  return [...ul.querySelectorAll('li')]
}

test('PRDs tab renders both duplicate backlog entries instead of crashing', async () => {
  const { doc, openTab } = render()
  await openTab('PRDs')
  const card = doc.querySelector('main .card')
  assert.ok(card, 'missing repo card')
  const items = backlogListItems(card, 'h3', 'backlog')
  assert.equal(items.length, 2, `expected 2 backlog items, got ${items.length}`)
  for (const li of items) {
    assert.equal(li.textContent.trim(), 'Ship pagination this week.')
  }
})

test('RepoDetail panel renders both duplicate backlog entries instead of crashing', async () => {
  const { doc, openTab, flush } = render()
  await openTab('Repos')
  const repoButton = doc.querySelector('button.card')
  assert.ok(repoButton, 'missing repo card button')
  repoButton.click()
  await flush()
  const panel = doc.querySelector('div.panel[role="dialog"]')
  assert.ok(panel, 'missing repo detail panel')
  const items = backlogListItems(panel, 'p.meta', 'backlog:')
  assert.equal(items.length, 2, `expected 2 backlog items, got ${items.length}`)
  for (const li of items) {
    assert.equal(li.textContent.trim(), 'Ship pagination this week.')
  }
})

test('RepoDetail panel renders both grouped epics that share a title, not once', async () => {
  const payload = structuredClone(PAYLOAD)
  payload.data.repos[0].commits = [
    { sha: 'aaaaaaa', date: '2026-08-01', subject: 'first' },
    { sha: 'bbbbbbb', date: '2026-08-02', subject: 'second' },
  ]
  payload.epics.repos['buvis/demo'] = {
    epics: [
      { title: 'Same epic', shas: ['aaaaaaa'] },
      { title: 'Same epic', shas: ['bbbbbbb'] },
    ],
  }

  const { doc, openTab, flush } = render(payload)
  await openTab('Repos')
  const repoButton = doc.querySelector('button.card')
  assert.ok(repoButton, 'missing repo card button')
  repoButton.click()
  await flush()
  const panel = doc.querySelector('div.panel[role="dialog"]')
  assert.ok(panel, 'missing repo detail panel')
  const epicTitles = [...panel.querySelectorAll('details summary b')].filter(
    (n) => n.textContent.trim() === 'Same epic',
  )
  assert.equal(epicTitles.length, 2, `expected 2 epics titled "Same epic", got ${epicTitles.length}`)
})

// New in this task: repo records now carry a top-level commit_count (the
// true window total on the default branch), separate from the `commits`
// array which is capped at 200 entries. aggregate() must sum commit_count,
// falling back to commits.length only when the key is absent — the task
// says the fallback fires on "no commit_count key at all", not on a falsy
// value, so commit_count: 0 must be trusted rather than treated as missing.
// Import placed here (not with the top-of-file imports) because this file's
// tests are append-only; ES module imports hoist regardless of position.
import { aggregate } from './src/lib/derive.js'

test('aggregate sums commit_count instead of the capped commits array', () => {
  const repos = [{ commits: [{}, {}], commit_count: 717 }]
  assert.equal(aggregate(repos, 60).commits, 717)
})

test('aggregate falls back to commits.length for a repo with no commit_count key', () => {
  const repos = [{ commits: [{}, {}] }]
  assert.equal(aggregate(repos, 60).commits, 2)
})

test('aggregate keeps commit_count: 0 rather than falling back to commits.length', () => {
  const repos = [{ commits: [{}, {}], commit_count: 0 }]
  assert.equal(aggregate(repos, 60).commits, 0)
})

test('aggregate mixes commit_count and the commits.length fallback across repos', () => {
  const repos = [
    { commits: [{}, {}], commit_count: 717 },
    { commits: [{}, {}, {}] },
  ]
  assert.equal(aggregate(repos, 60).commits, 720)
})

// "What happened" carries an Icon before its text, so match by substring
// instead of exact equality with the heading label.
function whatHappenedHeading(panel) {
  const heading = [...panel.querySelectorAll('h3')].find((n) =>
    n.textContent.trim().includes('What happened'),
  )
  assert.ok(heading, 'missing "What happened" heading')
  return heading
}

// The task gives no selector for the Brief tab's headline tile, and
// Brief.svelte is out of scope to read for this task — read the whole tab's
// text instead of guessing markup, collapsing incidental whitespace so a
// line-wrapped "717\ncommits" still matches a plain regex.
function mainText(doc) {
  const main = doc.querySelector('main') ?? doc.body
  return main.textContent.replace(/\s+/g, ' ').trim()
}

async function openRepoDetailPanel(doc, openTab, flush) {
  await openTab('Repos')
  const repoButton = doc.querySelector('button.card')
  assert.ok(repoButton, 'missing repo card button')
  repoButton.click()
  await flush()
  const panel = doc.querySelector('div.panel[role="dialog"]')
  assert.ok(panel, 'missing repo detail panel')
  return panel
}

test('RepoDetail says how many commits are shown when the list is capped', async () => {
  const payload = structuredClone(PAYLOAD)
  payload.data.repos[0].commits = [
    { sha: 'aaaaaaa', date: '2026-08-01', subject: 'first' },
    { sha: 'bbbbbbb', date: '2026-08-02', subject: 'second' },
  ]
  payload.data.repos[0].commit_count = 717

  const { doc, openTab, flush } = render(payload)
  await openTab('Brief')
  assert.match(mainText(doc), /717 commits/, 'Brief headline should total commit_count, not the capped list')

  const panel = await openRepoDetailPanel(doc, openTab, flush)
  const heading = whatHappenedHeading(panel)
  assert.match(heading.textContent, /2 of 717 shown/)
})

test('RepoDetail renders a plain commit count when commit_count matches the list length', async () => {
  const payload = structuredClone(PAYLOAD)
  payload.data.repos[0].commits = [
    { sha: 'ccccccc', date: '2026-08-01', subject: 'first' },
    { sha: 'ddddddd', date: '2026-08-02', subject: 'second' },
  ]
  payload.data.repos[0].commit_count = 2

  const { doc, openTab, flush } = render(payload)
  const panel = await openRepoDetailPanel(doc, openTab, flush)
  const heading = whatHappenedHeading(panel)
  assert.match(heading.textContent, /2 commits/)
  assert.doesNotMatch(heading.textContent, /shown/)
})

test('RepoDetail and the Brief headline fall back to commits.length when commit_count is absent', async () => {
  const payload = structuredClone(PAYLOAD)
  payload.data.repos[0].commits = [
    { sha: 'eeeeeee', date: '2026-08-01', subject: 'first' },
    { sha: 'fffffff', date: '2026-08-02', subject: 'second' },
  ]

  const { doc, openTab, flush } = render(payload)
  await openTab('Brief')
  assert.match(mainText(doc), /2 commits/)

  const panel = await openRepoDetailPanel(doc, openTab, flush)
  const heading = whatHappenedHeading(panel)
  assert.match(heading.textContent, /2 commits/)
  assert.doesNotMatch(heading.textContent, /shown/)
})
