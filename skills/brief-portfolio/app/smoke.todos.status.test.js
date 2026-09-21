import { test } from 'node:test'
import assert from 'node:assert/strict'
import { PAYLOAD, render } from './smoke.harness.js'

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
