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
import { readFileSync } from 'node:fs'
import { JSDOM, VirtualConsole } from 'jsdom'

const TEMPLATE = new URL('../assets/template.html', import.meta.url)

const PAYLOAD = {
  data: {
    repos: [{
      owner: 'buvis', name: 'demo', org: 'buvis',
      prds: {
        backlog: ['Ship pagination this week.', 'Ship pagination this week.'],
        wip: [{ title: 'Same title', idle_days: 3 }, { title: 'Same title', idle_days: 9 }],
        done_count: 0,
      },
    }],
    generated_at: new Date(0).toISOString(), since_days: 60, external: null, skill_adherence: null,
  },
  epics: { summary: '', repos: {} }, prev: null, history: [],
}

function render(payload = PAYLOAD, options = {}) {
  const defaults = { url: 'https://example.org/' }
  const { url } = { ...defaults, ...options }
  const page = readFileSync(TEMPLATE, 'utf8').replace(
    '__PORTFOLIO_PAYLOAD__',
    JSON.stringify(payload).replace(/<\//g, '<\\/'),
  )
  // jsdom does not run type="module", and running the bundle inline would fire
  // before #app exists. Lift it out and eval it once the document is built —
  // same code, same order a deferred module script would give it.
  const [tag, bundle] = page.match(/<script type="module"[^>]*>([\s\S]*?)<\/script>/)
  const errors = []
  const dom = new JSDOM(page.replace(tag, ''), {
    runScripts: 'dangerously',
    pretendToBeVisual: true,
    // jsdom treats the default about:blank as an opaque origin, where
    // localStorage throws instead of working — give it a real origin so the
    // app's own localStorage use behaves as it would in a browser. Passing
    // { url: null } omits this option so a caller can exercise that default.
    ...(url == null ? {} : { url }),
    virtualConsole: new VirtualConsole().on('jsdomError', (e) => errors.push(e)),
  })
  // jsdom has no ResizeObserver; stub it so components that size themselves
  // off it (e.g. the sparkline) don't throw a ReferenceError at mount.
  dom.window.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
  dom.window.eval(bundle)
  assert.deepEqual(errors.map((e) => e.message), [], 'the page threw while mounting')
  const doc = dom.window.document
  // Svelte 5 applies updates in a microtask, so every click needs a flush
  const flush = () => new Promise((resolve) => dom.window.setTimeout(resolve, 0))
  const openTab = async (label) => {
    const button = [...doc.querySelectorAll('header nav button')].find((b) =>
      b.textContent.trim().startsWith(label),
    )
    assert.ok(button, `missing tab ${label}`)
    button.click()
    await flush()
    return button
  }
  return { doc, flush, openTab }
}

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

test('nav element has an accessible label', () => {
  const { doc } = render()
  const nav = doc.querySelector('header nav')
  assert.ok(nav, 'missing <nav> inside <header>')
  assert.equal(nav.getAttribute('aria-label'), 'Sections')
})

test('exactly one tab button carries aria-current="page" on the default Brief tab, and no others', () => {
  const { doc } = render()
  const buttons = [...doc.querySelectorAll('header nav button')]
  assert.ok(buttons.length > 1, 'expected multiple tab buttons')
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

  // Wait past the component's 1.5s reset (real time, not a stubbed clock),
  // then flush so the resulting DOM update lands.
  await new Promise((resolve) => setTimeout(resolve, 1600))
  await flush()
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

test('Work tab filter chips expose their on/off state via aria-pressed on mount', async () => {
  const { doc, openTab } = render()
  await openTab('Work')
  const chips = [...doc.querySelectorAll('main .filters button.chip')]
  assert.equal(chips.length, 2, `expected 2 filter chips on the Work tab, got ${chips.length}`)
  assert.equal(
    chips[0].getAttribute('aria-pressed'),
    'false',
    'deps-bot PRs chip should read aria-pressed="false" by default (showDeps starts false)',
  )
  assert.equal(
    chips[1].getAttribute('aria-pressed'),
    'true',
    'drafts chip should read aria-pressed="true" by default (showDrafts starts true)',
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
