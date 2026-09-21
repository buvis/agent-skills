// The duplicate-rendering test below relies on the each_key_duplicate regression note atop smoke.repos.test.js.
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { PAYLOAD, render } from './smoke.harness.js'

test('mounts with zero errors on the default Brief tab', () => {
  const { doc } = render()
  assert.equal(doc.querySelector('h1').textContent.trim(), 'Portfolio Brief')
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
