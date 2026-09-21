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
