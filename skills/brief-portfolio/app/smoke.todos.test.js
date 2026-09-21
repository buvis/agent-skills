import { test } from 'node:test'
import assert from 'node:assert/strict'
import { PAYLOAD, render, waitFor } from './smoke.harness.js'

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
