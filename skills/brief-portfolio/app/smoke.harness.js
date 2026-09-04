import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { JSDOM, VirtualConsole } from 'jsdom'

export const TEMPLATE = new URL('../assets/template.html', import.meta.url)

export const PAYLOAD = {
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

export function render(payload = PAYLOAD, options = {}) {
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
