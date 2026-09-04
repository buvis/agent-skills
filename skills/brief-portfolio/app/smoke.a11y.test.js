import { test } from 'node:test'
import assert from 'node:assert/strict'
import { PAYLOAD, render } from './smoke.harness.js'

test('nav element has an accessible label', () => {
  const { doc } = render()
  const nav = doc.querySelector('header nav')
  assert.ok(nav, 'missing <nav> inside <header>')
  assert.equal(nav.getAttribute('aria-label'), 'Sections')
})

test('exactly one tab button carries aria-current="page" on the default Brief tab, and no others', () => {
  const { doc } = render()
  const buttons = [...doc.querySelectorAll('header nav button')]
  assert.equal(buttons.length, 7, `expected 7 tab buttons, got ${buttons.length}`)
  const current = buttons.filter((b) => b.getAttribute('aria-current') === 'page')
  assert.equal(
    current.length,
    1,
    `expected exactly 1 button with aria-current="page", got ${current.length}`,
  )
  assert.ok(
    current[0].textContent.trim().startsWith('Brief'),
    'the button carrying aria-current="page" is not the Brief tab',
  )
  const others = buttons.filter((b) => b !== current[0])
  for (const b of others) {
    assert.equal(
      b.getAttribute('aria-current'),
      null,
      `non-active tab button "${b.textContent.trim()}" should have no aria-current attribute`,
    )
  }
})

test('aria-current moves to the Work tab once it becomes active', async () => {
  const { doc, openTab } = render()
  await openTab('Work')
  const buttons = [...doc.querySelectorAll('header nav button')]
  const current = buttons.filter((b) => b.getAttribute('aria-current') === 'page')
  assert.equal(
    current.length,
    1,
    `expected exactly 1 button with aria-current="page" after opening Work, got ${current.length}`,
  )
  assert.ok(
    current[0].textContent.trim().startsWith('Work'),
    'the button carrying aria-current="page" is not the Work tab',
  )
})

test('Repos tab filter input has an accessible name', async () => {
  const { doc, openTab } = render()
  await openTab('Repos')
  const input = doc.querySelector('main input')
  assert.ok(input, 'missing filter input inside <main> on the Repos tab')
  assert.equal(input.getAttribute('aria-label'), 'Filter repos')
})

test('Repos tab sort select has an accessible name', async () => {
  const { doc, openTab } = render()
  await openTab('Repos')
  const select = doc.querySelector('main select')
  assert.ok(select, 'missing sort select inside <main> on the Repos tab')
  assert.equal(select.getAttribute('aria-label'), 'Sort repos')
})

test('Todo tab "hide done" chip exposes its on/off state via aria-pressed, not just the active class', async () => {
  // Duplicate backlog/wip entries (as in the shared PAYLOAD) trip the
  // unrelated each_key_duplicate crash on this tab, so use unique data here —
  // same fixup as the other Todos-tab tests above.
  const payload = structuredClone(PAYLOAD)
  payload.data.repos[0].prds = { backlog: [], wip: [], done_count: 0 }

  const { doc, openTab, flush } = render(payload)
  await openTab('Todo')
  const button = [...doc.querySelectorAll('main button.chip')].find(
    (b) => b.textContent.trim() === 'hide done',
  )
  assert.ok(button, 'missing "hide done" chip')
  assert.equal(button.getAttribute('aria-pressed'), 'false', 'chip should read aria-pressed="false" before any click')

  button.click()
  await flush()
  assert.equal(button.getAttribute('aria-pressed'), 'true', 'chip should read aria-pressed="true" after one click')
})

test('Work tab filter chips expose their on/off state via aria-pressed, and flip it on click', async () => {
  const { doc, openTab, flush } = render()
  await openTab('Work')
  const chips = [...doc.querySelectorAll('main .filters button.chip')]
  const depsChip = chips.find((b) => b.textContent.trim().startsWith('deps-bot PRs'))
  const draftsChip = chips.find((b) => b.textContent.trim() === 'drafts')
  assert.ok(depsChip, 'missing "deps-bot PRs" filter chip')
  assert.ok(draftsChip, 'missing "drafts" filter chip')

  assert.equal(
    depsChip.getAttribute('aria-pressed'),
    'false',
    'deps-bot PRs chip should read aria-pressed="false" by default (showDeps starts false)',
  )
  assert.equal(
    draftsChip.getAttribute('aria-pressed'),
    'true',
    'drafts chip should read aria-pressed="true" by default (showDrafts starts true)',
  )

  depsChip.click()
  draftsChip.click()
  await flush()

  assert.equal(
    depsChip.getAttribute('aria-pressed'),
    'true',
    'deps-bot PRs chip should read aria-pressed="true" after a click',
  )
  assert.equal(
    draftsChip.getAttribute('aria-pressed'),
    'false',
    'drafts chip should read aria-pressed="false" after a click',
  )
})

test('Header org filter chip exposes its on/off state via aria-pressed, on mount and once an org is picked', async () => {
  // Brief is the default tab, and the header is rendered regardless of the
  // active tab — no openTab call needed.
  const { doc, flush } = render()
  const toggle = doc.querySelector('header .filter button.chip')
  assert.ok(toggle, 'missing header org filter chip')
  assert.equal(toggle.getAttribute('aria-pressed'), 'false', 'chip should read aria-pressed="false" while org is "all"')

  toggle.click()
  await flush()
  const buvisOption = [...doc.querySelectorAll('header .pop button')].find(
    (b) => b.textContent.trim() === 'buvis',
  )
  assert.ok(buvisOption, 'missing "buvis" org option in the filter panel')
  buvisOption.click()
  await flush()

  assert.equal(
    toggle.getAttribute('aria-pressed'),
    'true',
    'chip should read aria-pressed="true" once an org other than "all" is selected',
  )
})
