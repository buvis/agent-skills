// Renders the built single-file page in jsdom. Catches the runtime breakage a
// successful `vite build` cannot: a missing field, a bad lookup, a dead tab.
//
// Regression: {#each} blocks keyed by a list item's own value (instead of a
// stable id or index) throw `each_key_duplicate` when two items share that
// value. On the default tab this blanks the whole page at mount; on other
// tabs, or nested panels, it silently breaks the tab/panel switch. Either
// way, duplicate-valued items should render twice, not crash.
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { PAYLOAD, render } from './smoke.harness.js'

async function waitFor(predicate, { flush, timeout = 3000, interval = 25 } = {}) {
  const deadline = Date.now() + timeout
  const tick = flush ?? (() => new Promise((resolve) => setTimeout(resolve, 0)))
  await tick()
  while (true) {
    if (Date.now() >= deadline) {
      throw new Error(`waitFor: predicate did not become true within ${timeout}ms`)
    }
    if (predicate()) {
      return
    }
    await new Promise((resolve) => setTimeout(resolve, Math.min(interval, deadline - Date.now())))
    await tick()
  }
}

test('waitFor resolves once the predicate turns true', async () => {
  let ready = false
  setTimeout(() => { ready = true }, 20)
  await waitFor(() => ready, { timeout: 200, interval: 5 })
  assert.equal(ready, true)
})

test('waitFor awaits the supplied flush between predicate checks', async () => {
  let value = false
  let pending = false
  let observedWhilePending = false
  let flushCalls = 0
  const flush = () => {
    flushCalls += 1
    const call = flushCalls
    pending = true
    return new Promise((resolve) => {
      setTimeout(() => {
        if (call === 2) {
          value = true
        }
        pending = false
        resolve()
      }, 0)
    })
  }
  await waitFor(() => {
    if (pending) {
      observedWhilePending = true
    }
    return value
  }, { flush, interval: 5, timeout: 200 })
  assert.equal(observedWhilePending, false, 'predicate ran while a flush was still pending, meaning waitFor did not await it')
  assert.equal(flushCalls, 2, 'predicate turned true without waitFor awaiting flush between checks')
})

test('waitFor throws an Error naming the timeout once the deadline passes', async () => {
  await assert.rejects(
    () => waitFor(() => false, { timeout: 50, interval: 10 }),
    (err) => err instanceof Error && err.message.includes('50'),
  )

  // The predicate turns true only after the deadline, mid-way through an
  // oversized interval; waitFor must still reject rather than accept it.
  let value = false
  setTimeout(() => { value = true }, 80)
  const flush = () => new Promise((resolve) => setTimeout(resolve, 40))
  await assert.rejects(() => waitFor(() => value, { flush, timeout: 60, interval: 10000 }))
})

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

// Stubs both clipboard write paths jsdom doesn't implement, and records
// every write attempt so "nothing was copied" is assertable. Both stubs are
// needed: the page falls back to execCommand when
// navigator.clipboard.writeText rejects, and a declined copy must touch
// NEITHER.
function stubClipboard(doc) {
  const writes = []
  doc.defaultView.navigator.clipboard = {
    writeText: (text) => { writes.push(text); return Promise.resolve() },
  }
  doc.execCommand = (cmd) => { writes.push(cmd); return true }
  return writes
}

test('mounts with zero errors on the default Brief tab', () => {
  const { doc } = render()
  assert.equal(doc.querySelector('h1').textContent.trim(), 'Portfolio Brief')
})

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

test('Brief tab names repos it could not collect this run', () => {
  const payload = structuredClone(PAYLOAD)
  payload.data.skipped = [
    { owner: 'acme', name: 'gadget', org: 'acme', path: '/tmp/acme/gadget', skipped: 'clone failed' },
  ]

  // Brief is the default tab — no openTab call needed.
  const { doc } = render(payload)
  const mainText = doc.querySelector('main').textContent
  assert.match(mainText, /not collected/)
  assert.match(mainText, /acme\/gadget/)

  const strongEls = [...doc.querySelectorAll('main strong.sev-warning')]
  assert.ok(
    strongEls.some((el) => el.textContent.trim() === '1'),
    'skipped-repo count is not rendered inside <strong class="sev-warning">',
  )
})

test('Todos tab shows a failed-copy state when neither clipboard.writeText nor execCommand works', async () => {
  // jsdom provides neither navigator.clipboard nor a working execCommand('copy')
  // by default — the same failure mode as clicking "copy open as markdown"
  // from a file:// page.
  // Duplicate backlog/wip entries (as in the shared PAYLOAD) trip the
  // unrelated each_key_duplicate crash on this tab, so use unique data here.
  const payload = structuredClone(PAYLOAD)
  payload.data.repos[0].prds = { backlog: [], wip: [], done_count: 0 }

  const { doc, openTab, flush } = render(payload)
  await openTab('Todo')
  const button = [...doc.querySelectorAll('main button.chip')].find(
    (b) => b.textContent.trim() === 'copy open as markdown',
  )
  assert.ok(button, 'missing "copy open as markdown" button')
  button.click()
  await flush()
  assert.equal(button.textContent.trim(), '✗ copy failed')
})

test('Failed copy leaves no leftover <textarea> in the document', async () => {
  // Same failure path as the "✗ copy failed" test above: jsdom provides
  // neither navigator.clipboard nor a working execCommand('copy'), so the
  // fallback textarea's select()/execCommand() throw before box.remove()
  // runs, leaking a hidden textarea into the document on every failed copy.
  const payload = structuredClone(PAYLOAD)
  payload.data.repos[0].prds = { backlog: [], wip: [], done_count: 0 }

  const { doc, openTab, flush } = render(payload)
  await openTab('Todo')
  const button = [...doc.querySelectorAll('main button.chip')].find(
    (b) => b.textContent.trim() === 'copy open as markdown',
  )
  assert.ok(button, 'missing "copy open as markdown" button')
  button.click()
  await flush()
  assert.equal(doc.querySelector('textarea'), null, 'a failed copy left a <textarea> in the document')
})

test('Failed copy is announced in an aria-live region, not just the button label', async () => {
  // Same failure path as the two tests above: jsdom provides neither
  // navigator.clipboard nor a working execCommand('copy'). A label that only
  // mutates in place tells a screen-reader user nothing — the outcome must
  // also reach an aria-live="polite" region.
  const payload = structuredClone(PAYLOAD)
  payload.data.repos[0].prds = { backlog: [], wip: [], done_count: 0 }

  const { doc, openTab, flush } = render(payload)
  await openTab('Todo')
  const button = [...doc.querySelectorAll('main button.chip')].find(
    (b) => b.textContent.trim() === 'copy open as markdown',
  )
  assert.ok(button, 'missing "copy open as markdown" button')
  button.click()
  await flush()
  const liveRegions = [...doc.querySelectorAll('[aria-live="polite"]')]
  const announced = liveRegions.find((el) => /copy failed/i.test(el.textContent.trim()))
  assert.ok(
    announced,
    'no aria-live="polite" element announces the copy failure (the button label alone changed)',
  )
})

test('Todos tab reports success and copies the open todos when the execCommand fallback works', async () => {
  // navigator.clipboard.writeText rejects (as it would on a file:// page with
  // no secure-context clipboard access), so copy() falls through to
  // fallbackCopy(). Stubbing execCommand to return true simulates a browser
  // where the fallback actually works, unlike the failed-copy tests above
  // where jsdom's own execCommand never succeeds.
  const payload = structuredClone(PAYLOAD)
  payload.data.repos[0].prds = { backlog: [], wip: [], done_count: 0 }
  payload.data.repos[0].local = { dirty: 2, dirty_since_days: 1, ahead: 3 }

  const { doc, openTab, flush } = render(payload)
  await openTab('Todo')

  const button = [...doc.querySelectorAll('main button.chip')].find(
    (b) => b.textContent.trim() === 'copy open as markdown',
  )
  assert.ok(button, 'missing "copy open as markdown" button')

  // Derive the expected clipboard payload from what the page itself rendered
  // for the open todos, rather than hardcoding a markdown string.
  const expected = [...doc.querySelectorAll('main .todo')]
    .map((el) => {
      const action = el.querySelector('.action').textContent.trim()
      const repo = el.querySelector('.repobtn').textContent.trim()
      return `- [ ] ${repo}: ${action}`
    })
    .join('\n')
  assert.ok(expected.length > 0, 'test setup produced no open todos to copy')

  doc.defaultView.navigator.clipboard = { writeText: () => Promise.reject(new Error('denied')) }
  let recorded = null
  doc.execCommand = () => {
    // The fallback textarea is still in the document at this point — the
    // stub can't read a real selection, so it captures the value directly.
    const box = doc.querySelector('textarea')
    recorded = box ? box.value : null
    return true
  }

  button.click()
  await flush()

  assert.equal(button.textContent.trim(), '✓ copied')
  assert.equal(doc.querySelector('textarea'), null, 'a successful fallback copy left a <textarea> in the document')
  assert.equal(recorded, expected)

  const liveRegions = [...doc.querySelectorAll('[aria-live="polite"]')]
  const announced = liveRegions.find((el) => /copied/i.test(el.textContent.trim()))
  assert.ok(
    announced,
    'no aria-live="polite" element announces the successful copy (the button label alone changed)',
  )
})

test('Todos tab reports failure when the execCommand fallback returns false', async () => {
  // navigator.clipboard.writeText rejects (as in the fallback-succeeds test
  // above), but execCommand runs without throwing and returns false — a
  // silently no-op copy rather than a working one. fallbackCopy must treat
  // that as a failure, not report success.
  const payload = structuredClone(PAYLOAD)
  payload.data.repos[0].prds = { backlog: [], wip: [], done_count: 0 }
  payload.data.repos[0].local = { dirty: 2, dirty_since_days: 1, ahead: 3 }

  const { doc, openTab, flush } = render(payload)
  await openTab('Todo')

  const button = [...doc.querySelectorAll('main button.chip')].find(
    (b) => b.textContent.trim() === 'copy open as markdown',
  )
  assert.ok(button, 'missing "copy open as markdown" button')

  doc.defaultView.navigator.clipboard = { writeText: () => Promise.reject(new Error('denied')) }
  doc.execCommand = () => false

  button.click()
  await flush()

  assert.equal(button.textContent.trim(), '✗ copy failed')
  assert.equal(doc.querySelector('textarea'), null, 'a failed fallback copy left a <textarea> in the document')
})

test('Brief tab trend sparkline plots only complete history runs, not incomplete ones', () => {
  const payload = structuredClone(PAYLOAD)
  payload.prev = { repos: [], generated_at: new Date(0).toISOString() }
  payload.history = [
    { at: new Date(0).toISOString(), repos: {} },
    { at: new Date(0).toISOString(), repos: {}, skipped: 0 },
    { at: new Date(0).toISOString(), repos: {} },
    { at: new Date(0).toISOString(), repos: {}, skipped: 1 },
  ]

  // Brief is the default tab — no openTab call needed.
  const { doc } = render(payload)
  const mainText = doc.querySelector('main').textContent
  assert.match(
    mainText,
    /open items across 3 briefs/,
    'trend label should report 3 complete runs, not all 4 history entries',
  )
})

test('Brief tab trend sparkline skips a run where a repo failed to collect', () => {
  const payload = structuredClone(PAYLOAD)
  payload.prev = { repos: [], generated_at: new Date(0).toISOString() }
  payload.history = [
    { at: new Date(0).toISOString(), repos: {} },
    { at: new Date(0).toISOString(), repos: {}, skipped: 0 },
    { at: new Date(0).toISOString(), repos: {} },
    { at: new Date(0).toISOString(), repos: {}, skipped: 1 },
    { at: new Date(0).toISOString(), repos: { 'o/r': { i: 0, e: 1 } } },
  ]

  // Brief is the default tab — no openTab call needed.
  const { doc } = render(payload)
  const mainText = doc.querySelector('main').textContent
  assert.match(
    mainText,
    /open items across 3 briefs/,
    'trend label should still report 3 complete runs, dropping the run where a repo failed to collect',
  )
})

test('aria-live region clears once the failed-copy button label has reverted', async () => {
  // Same failure path as the tests above. The button's own copied/failed
  // state resets to '' after 1.5s via setTimeout, but the aria-live status
  // never resets. Svelte's $state skips the DOM write when a value repeats,
  // so once the label looks normal again, the live region must not still be
  // holding the stale "✗ copy failed" text from the click that just cleared.
  const payload = structuredClone(PAYLOAD)
  payload.data.repos[0].prds = { backlog: [], wip: [], done_count: 0 }

  const { doc, openTab, flush } = render(payload)
  await openTab('Todo')
  const button = [...doc.querySelectorAll('main button.chip')].find(
    (b) => b.textContent.trim() === 'copy open as markdown',
  )
  assert.ok(button, 'missing "copy open as markdown" button')
  button.click()
  await flush()
  assert.equal(button.textContent.trim(), '✗ copy failed')

  // Wait past the component's 1.5s reset (real time, not a stubbed clock);
  // waitFor already flushes before the predicate check that resolves it.
  await waitFor(() => button.textContent.trim() === 'copy open as markdown', { flush })
  assert.equal(button.textContent.trim(), 'copy open as markdown', 'label did not revert after 1.5s')

  const liveRegion = doc.querySelector('[aria-live="polite"]')
  assert.ok(liveRegion, 'missing aria-live="polite" element')
  assert.equal(
    liveRegion.textContent.trim(),
    '',
    'aria-live region still holds stale "✗ copy failed" text after the button label reverted',
  )
})

test('Todos tab shows a "nothing" status on a per-group copy when the group\'s only open item is checked done', async () => {
  // This payload derives exactly two open todos: one 'soon' (brush_last_run
  // is left unset) and one 'later' (a non-empty backlog). purge_last_run is
  // set to now so the repo-scoped purge-devlocal maintenance nag (also
  // 'soon' whenever it's unset) doesn't add a second item to the soon group.
  // Checking off the sole 'soon' item leaves that group with nothing open,
  // so clicking its own per-group copy button should decline instead of
  // touching the clipboard.
  const payload = structuredClone(PAYLOAD)
  payload.data.repos[0].prds = { backlog: ['Ship it.'], wip: [], done_count: 0 }
  payload.data.repos[0].purge_last_run = new Date().toISOString()

  const { doc, openTab, flush } = render(payload)
  await openTab('Todo')

  const writes = stubClipboard(doc)

  const sectionsWithTodos = [...doc.querySelectorAll('main section.sec')].filter(
    (sec) => sec.querySelector('.todo'),
  )
  assert.equal(
    sectionsWithTodos.length,
    2,
    `expected 2 urgency sections holding a todo (soon, later), got ${sectionsWithTodos.length}`,
  )
  // Select the soon group directly by its heading class, rather than relying
  // on the sections' urgency order.
  const soonSection = doc.querySelector('h2.u-soon').closest('section.sec')

  const checkbox = soonSection.querySelector('.todo input[type="checkbox"]')
  assert.ok(checkbox, 'missing checkbox on the soon-group todo')
  checkbox.click()
  await flush()

  const miniButton = soonSection.querySelector('button.chip.mini')
  assert.ok(miniButton, 'missing per-group button.chip.mini in the soon section')
  miniButton.click()
  await flush()

  assert.equal(writes.length, 0, 'a declined copy should not touch the clipboard')
  assert.equal(miniButton.textContent.trim(), 'nothing')

  const liveRegion = doc.querySelector('[aria-live="polite"]')
  assert.ok(liveRegion, 'missing aria-live="polite" element')
  assert.equal(liveRegion.textContent.trim(), 'nothing to copy')
})

test('done.js survives a blocked localStorage: loadDone returns empty, saveDone no-ops, isStorageBlocked flips true', async () => {
  // Simulates a file:// page or a browser with storage access disabled, where
  // both getItem and setItem throw (e.g. a SecurityError) instead of working.
  const hadLocalStorage = Object.prototype.hasOwnProperty.call(globalThis, 'localStorage')
  const previousLocalStorage = globalThis.localStorage
  globalThis.localStorage = {
    getItem() { throw new Error('SecurityError') },
    setItem() { throw new Error('SecurityError') },
  }
  try {
    const { loadDone, saveDone, isStorageBlocked } = await import('./src/lib/done.js')
    assert.equal(loadDone().size, 0, 'loadDone should return an empty Set when localStorage.getItem throws')
    assert.doesNotThrow(
      () => saveDone(new Set(['x'])),
      'saveDone should not throw when localStorage.setItem throws',
    )
    assert.equal(isStorageBlocked(), true, 'isStorageBlocked should be true once a helper has caught an error')
  } finally {
    if (hadLocalStorage) {
      globalThis.localStorage = previousLocalStorage
    } else {
      delete globalThis.localStorage
    }
  }
})

test('loadDone() returns an empty Set when the stored value is corrupt JSON', async () => {
  // getItem succeeds but returns a string JSON.parse chokes on; setItem works
  // fine, only the parse should trip the catch.
  const hadLocalStorage = Object.prototype.hasOwnProperty.call(globalThis, 'localStorage')
  const previousLocalStorage = globalThis.localStorage
  globalThis.localStorage = {
    getItem() { return '{not json' },
    setItem() {},
  }
  try {
    const { loadDone } = await import('./src/lib/done.js?case=corrupt')
    assert.equal(loadDone().size, 0, 'loadDone should return an empty Set when the stored value is corrupt JSON')
  } finally {
    if (hadLocalStorage) {
      globalThis.localStorage = previousLocalStorage
    } else {
      delete globalThis.localStorage
    }
  }
})

test('saveDone() alone flips isStorageBlocked when only setItem throws', async () => {
  // getItem works and returns a valid stored value; only setItem throws,
  // proving saveDone sets the flag on its own, without loadDone catching first.
  const hadLocalStorage = Object.prototype.hasOwnProperty.call(globalThis, 'localStorage')
  const previousLocalStorage = globalThis.localStorage
  globalThis.localStorage = {
    getItem() { return '[]' },
    setItem() { throw new Error('SecurityError') },
  }
  try {
    const { saveDone, isStorageBlocked } = await import('./src/lib/done.js?case=savefail')
    assert.doesNotThrow(
      () => saveDone(new Set(['x'])),
      'saveDone should not throw when localStorage.setItem throws',
    )
    assert.equal(isStorageBlocked(), true, 'isStorageBlocked should be true after saveDone alone caught an error')
  } finally {
    if (hadLocalStorage) {
      globalThis.localStorage = previousLocalStorage
    } else {
      delete globalThis.localStorage
    }
  }
})

test('render(payload, { url: null }) omits the jsdom url option, so localStorage throws on the default opaque origin', () => {
  const { doc } = render(PAYLOAD, { url: null })
  assert.throws(() => doc.defaultView.localStorage)
})

test('render(payload) still mounts on a real origin, so localStorage works by default', () => {
  const { doc } = render(PAYLOAD)
  assert.doesNotThrow(() => doc.defaultView.localStorage)
})

test('Brief tab shows no persistence notice when localStorage works', () => {
  const { doc } = render()
  assert.doesNotMatch(doc.body.textContent, /will not persist/)
})

test('Brief tab still renders with a persistence notice when localStorage is blocked', () => {
  const { doc } = render(PAYLOAD, { url: null })
  assert.equal(doc.querySelector('h1').textContent.trim(), 'Portfolio Brief')
  assert.ok(doc.querySelector('main').textContent.trim().length > 0, 'Brief tab is blank')
  assert.ok(
    doc.body.textContent.includes(
      'Checked state will not persist: this browser is blocking local storage.',
    ),
    'exact persistence notice not found',
  )
  assert.ok(
    doc.querySelectorAll('header nav button').length > 0,
    'tab controls missing',
  )
  const activeTab = doc.querySelector('header nav button.active')
  assert.ok(activeTab, 'no active tab button found')
  assert.ok(
    activeTab.textContent.trim().startsWith('Brief'),
    'the active tab is not Brief',
  )
})

test('Todos tab disables the "copy open as markdown" button and touches nothing when there are no open todos', async () => {
  // Zero todos: an empty backlog/wip/done_count alone still leaves two
  // repo-scoped nags standing — a 'soon' brush nag whenever brush_last_run
  // is unset or stale, and a 'soon' maintenance "Run /purge-devlocal" nag
  // whenever purge_last_run is unset or stale (generated unconditionally,
  // it does not depend on the external field) — so both must also be set to
  // now to actually reach openCount === 0.
  const payload = structuredClone(PAYLOAD)
  payload.data.repos[0].prds = { backlog: [], wip: [], done_count: 0 }
  payload.data.repos[0].brush_last_run = new Date().toISOString()
  payload.data.repos[0].purge_last_run = new Date().toISOString()

  const { doc, openTab, flush } = render(payload)
  await openTab('Todo')

  const writes = stubClipboard(doc)

  const button = [...doc.querySelectorAll('main button.chip')].find(
    (b) => b.textContent.trim() === 'copy open as markdown',
  )
  assert.ok(button, 'missing "copy open as markdown" button')
  assert.equal(button.disabled, true, 'the bar button should be disabled when openCount is 0')

  button.click()
  await flush()

  assert.equal(writes.length, 0, 'clicking the disabled button must not touch the clipboard')

  const liveRegion = doc.querySelector('[aria-live="polite"]')
  assert.ok(liveRegion, 'missing aria-live="polite" element')
  assert.equal(liveRegion.textContent.trim(), '', 'no status should be set since no copy was ever attempted')
})

test('Todos tab disables the per-group button too, once the whole-list openCount reaches 0', async () => {
  // Exactly one open todo: a single-item backlog produces one 'later' todo;
  // brush_last_run and purge_last_run (as in the zero-todos test above)
  // suppress the 'soon' brush and maintenance nags, leaving one rendered
  // section. Checking that lone item off drives openCount (the whole-list
  // count of not-done todos) to 0 while the section itself still renders,
  // since a section's visibility depends on the group holding any todo, not
  // on whether that todo is done.
  const payload = structuredClone(PAYLOAD)
  payload.data.repos[0].prds = { backlog: ['Ship it.'], wip: [], done_count: 0 }
  payload.data.repos[0].brush_last_run = new Date().toISOString()
  payload.data.repos[0].purge_last_run = new Date().toISOString()

  const { doc, openTab, flush } = render(payload)
  await openTab('Todo')

  const section = doc.querySelector('main section.sec')
  assert.ok(section, 'missing the single rendered urgency section')
  const checkbox = section.querySelector('.todo input[type="checkbox"]')
  assert.ok(checkbox, 'missing checkbox on the only todo')
  checkbox.click()
  await flush()

  const writes = stubClipboard(doc)

  const miniButton = section.querySelector('button.chip.mini')
  assert.ok(miniButton, 'missing per-group button.chip.mini')
  assert.equal(miniButton.disabled, true, 'the per-group button should be disabled once the whole-list openCount is 0')

  miniButton.click()
  await flush()
  assert.equal(writes.length, 0, 'clicking the disabled per-group button must not touch the clipboard')

  const barButton = [...doc.querySelectorAll('main button.chip')].find(
    (b) => b.textContent.trim() === 'copy open as markdown',
  )
  assert.ok(barButton, 'missing "copy open as markdown" button')
  assert.equal(barButton.disabled, true, 'the bar button shares the same openCount and should also be disabled')
})

test('A declined copy is announced truthfully even right after a successful copy', async () => {
  // Two open todos in different urgency groups: one 'soon' (brush_last_run
  // left unset) and one 'later' (a non-empty backlog) — the same fixture
  // recipe as the "shows a 'nothing' status" test above. purge_last_run is
  // set to now so the repo-scoped purge-devlocal nag doesn't add a second
  // 'soon' item.
  const payload = structuredClone(PAYLOAD)
  payload.data.repos[0].prds = { backlog: ['Ship it.'], wip: [], done_count: 0 }
  payload.data.repos[0].purge_last_run = new Date().toISOString()

  const { doc, openTab, flush } = render(payload)
  await openTab('Todo')

  const writes = stubClipboard(doc)

  const sectionsWithTodos = [...doc.querySelectorAll('main section.sec')].filter(
    (sec) => sec.querySelector('.todo'),
  )
  assert.equal(
    sectionsWithTodos.length,
    2,
    `expected 2 urgency sections holding a todo (soon, later), got ${sectionsWithTodos.length}`,
  )
  const [soonSection] = sectionsWithTodos

  // Check off the soon group's only item so that group has nothing open,
  // while the whole list (the later item) still does — both buttons stay
  // enabled, since `disabled` is driven by the whole-list count only.
  const checkbox = soonSection.querySelector('.todo input[type="checkbox"]')
  assert.ok(checkbox, 'missing checkbox on the soon-group todo')
  checkbox.click()
  await flush()

  const barButton = [...doc.querySelectorAll('.bar button.chip')].find(
    (b) => b.textContent.trim().startsWith('copy open as markdown'),
  )
  assert.ok(barButton, 'missing "copy open as markdown" button')
  const miniButton = soonSection.querySelector('button.chip.mini')
  assert.ok(miniButton, 'missing per-group button.chip.mini in the soon section')
  const liveRegion = doc.querySelector('[aria-live="polite"]')
  assert.ok(liveRegion, 'missing aria-live="polite" element')

  // Both clicks happen back to back, inside a single 1500ms announcement
  // window — no wait between them.
  barButton.click()
  await flush()
  assert.equal(liveRegion.textContent.trim(), '✓ copied', 'test setup: the bar copy did not succeed')
  const writesAfterBarClick = writes.length

  miniButton.click()
  await flush()

  assert.equal(
    liveRegion.textContent.trim(),
    'nothing to copy',
    'a declined copy must announce "nothing to copy", not the stale success from the click right before it',
  )
  assert.notEqual(liveRegion.textContent.trim(), '✓ copied')
  assert.equal(
    writes.length,
    writesAfterBarClick,
    'a declined copy must not touch the clipboard, even right after a successful one',
  )
})

test('A newer status announcement survives an older one\'s 1500ms expiry, and still clears once its own window elapses', async () => {
  // Real waiting, not a stubbed clock: the contract only promises "clears
  // itself 1500ms later" — it doesn't say how many timers the page keeps or
  // how it tracks which announcement is newest, and stubbing
  // doc.defaultView.setTimeout here would mean guessing that internal
  // shape. Real time keeps this test bound to the documented behaviour
  // only, at the cost of ~2.2s of wall time (comparable to the existing
  // 1.6s real-wait test above).
  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms))

  // Same two-group fixture as the "declined right after a successful copy"
  // test above: one open 'soon' todo and one open 'later' todo.
  // purge_last_run is set to now so the maintenance nag doesn't add a
  // second 'soon' item.
  const payload = structuredClone(PAYLOAD)
  payload.data.repos[0].prds = { backlog: ['Ship it.'], wip: [], done_count: 0 }
  payload.data.repos[0].purge_last_run = new Date().toISOString()

  const { doc, openTab, flush } = render(payload)
  await openTab('Todo')

  const writes = stubClipboard(doc)

  const sectionsWithTodos = [...doc.querySelectorAll('main section.sec')].filter(
    (sec) => sec.querySelector('.todo'),
  )
  assert.equal(
    sectionsWithTodos.length,
    2,
    `expected 2 urgency sections holding a todo (soon, later), got ${sectionsWithTodos.length}`,
  )
  const [soonSection] = sectionsWithTodos

  // Check off the soon group's only item so that group has nothing open,
  // while the whole list (the later item) still does — both buttons stay
  // enabled.
  const checkbox = soonSection.querySelector('.todo input[type="checkbox"]')
  assert.ok(checkbox, 'missing checkbox on the soon-group todo')
  checkbox.click()
  await flush()

  const barButton = [...doc.querySelectorAll('.bar button.chip')].find(
    (b) => b.textContent.trim().startsWith('copy open as markdown'),
  )
  assert.ok(barButton, 'missing "copy open as markdown" button')
  const miniButton = soonSection.querySelector('button.chip.mini')
  assert.ok(miniButton, 'missing per-group button.chip.mini in the soon section')
  const liveRegion = doc.querySelector('[aria-live="polite"]')
  assert.ok(liveRegion, 'missing aria-live="polite" element')

  // Older announcement: the bar copy succeeds.
  barButton.click()
  await flush()
  assert.equal(liveRegion.textContent.trim(), '✓ copied', 'test setup: the bar copy did not succeed')

  await sleep(500)

  // Newer announcement, 500ms later: the fully-done group's own button is
  // clicked, which declines instead of touching the clipboard.
  const writesBeforeDecline = writes.length
  miniButton.click()
  await flush()
  assert.equal(
    liveRegion.textContent.trim(),
    'nothing to copy',
    'the declined copy did not announce truthfully right after the successful one',
  )
  assert.equal(writes.length, writesBeforeDecline, 'test setup: the declined copy touched the clipboard')

  // ~1700ms after the older click: its own 1500ms window has expired, but
  // the newer click's window (started 500ms later) has not — the newer
  // announcement must still be showing.
  await sleep(1200)
  await flush()
  assert.equal(
    liveRegion.textContent.trim(),
    'nothing to copy',
    "the newer announcement was wiped out by the older announcement's own expiry",
  )

  // ~2200ms after the older click, ~1700ms after the newer one: the newer
  // announcement's own 1500ms window has now elapsed too.
  await sleep(500)
  await flush()
  assert.equal(
    liveRegion.textContent.trim(),
    '',
    'the announcement did not clear once its own 1500ms window elapsed',
  )
})
