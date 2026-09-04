<script>
  import { getContext } from 'svelte'
  import { slug, allTodos } from '../lib/derive.js'
  import { loadDone, saveDone } from '../lib/done.js'
  import Icon from './Icon.svelte'

  const KIND_ICON = { local: 'wip', external: 'pr' } // other kinds share the icon name

  let { repos, epics, external, onselect } = $props()
  const slots = getContext('slots')

  let done = $state(loadDone())
  let hideDone = $state(false)
  // The single latest copy outcome, so a later announcement always replaces
  // an earlier one instead of racing three independent timers.
  let outcome = $state(null) // { kind: 'copied' | 'failed' | 'nothing', label } | null
  let outcomeTimer

  const byslug = $derived(new Map(repos.map((r) => [slug(r), r])))
  const todos = $derived(allTodos(repos, epics, external))
  const groups = $derived(
    ['now', 'soon', 'later'].map((u) => ({
      u,
      all: todos.filter((t) => t.urgency === u),
      shown: todos.filter((t) => t.urgency === u && !(hideDone && done.has(t.id))),
    }))
  )
  const openCount = $derived(todos.filter((t) => !done.has(t.id)).length)
  const status = $derived(
    outcome?.kind === 'copied' ? '✓ copied' : outcome?.kind === 'failed' ? '✗ copy failed' : outcome?.kind === 'nothing' ? 'nothing to copy' : ''
  )

  function toggle(id) {
    const s = new Set(done)
    if (s.has(id)) s.delete(id)
    else s.add(id)
    done = s
    saveDone(s)
  }
  function fallbackCopy(value) {
    const box = document.createElement('textarea')
    box.value = value
    box.style.position = 'fixed'
    box.style.opacity = '0'
    document.body.append(box)
    try {
      box.select()
      const ok = document.execCommand('copy')
      if (!ok) throw new Error('execCommand copy returned false')
    } finally {
      box.remove()
    }
  }

  function announce(kind, label) {
    clearTimeout(outcomeTimer)
    outcome = { kind, label }
    outcomeTimer = setTimeout(() => (outcome = null), 1500)
  }

  async function copy(items, label) {
    const open = items.filter((t) => !done.has(t.id))
    if (open.length === 0) {
      announce('nothing', label)
      return
    }
    const md = open.map((t) => `- [ ] ${t.repo}: ${t.action}`).join('\n')
    try {
      await navigator.clipboard.writeText(md)
    } catch {
      try {
        fallbackCopy(md)
      } catch {
        announce('failed', label)
        return
      }
    }
    announce('copied', label)
  }
</script>

<div class="bar">
  <span class="count"><b>{openCount}</b> open follow-ups · checked state survives regeneration</span>
  <button class="chip" class:active={hideDone} aria-pressed={hideDone} onclick={() => (hideDone = !hideDone)}>hide done</button>
  <button class="chip" disabled={openCount === 0} onclick={() => copy(todos, 'all')}>
    {outcome?.label === 'all' && outcome.kind === 'copied' ? '✓ copied' : outcome?.label === 'all' && outcome.kind === 'failed' ? '✗ copy failed' : 'copy open as markdown'}
  </button>
</div>

{#each groups as { u, all, shown } (u)}
  {#if all.length}
    <section class="sec">
      <h2 class="u-{u}">
        {u} · {all.filter((t) => !done.has(t.id)).length} open
        <button class="chip mini" disabled={openCount === 0} onclick={() => copy(all, u)}>{outcome?.label === u && outcome.kind === 'copied' ? '✓' : outcome?.label === u && outcome.kind === 'failed' ? '✗' : outcome?.label === u && outcome.kind === 'nothing' ? 'nothing' : 'copy'}</button>
      </h2>
      {#each shown as t (t.id)}
        <div class="todo" class:isdone={done.has(t.id)}>
          <input type="checkbox" id={t.id} checked={done.has(t.id)} onchange={() => toggle(t.id)} />
          <label for={t.id}>
            <span class="action">
              {#if t.url}<a href={t.url} target="_blank" rel="noreferrer">{t.action}</a>{:else}{t.action}{/if}
            </span>
            {#if t.why}<span class="why">{t.why}</span>{/if}
          </label>
          {#if t.agent}<span class="lbl agent">→ {t.agent}</span>{/if}
          <span class="lbl"><Icon name={KIND_ICON[t.kind] ?? t.kind} size={11} /> {t.kind}{t.manual ? ' ✦' : ''}</span>
          {#if byslug.has(t.repo)}
            <button class="repobtn" onclick={() => onselect(byslug.get(t.repo))}>
              <span class="dot" style="background: var(--cat{slots.get(byslug.get(t.repo).org)})"></span>
              {t.repo}
            </button>
          {:else}
            <span class="lbl">{t.repo}</span>
          {/if}
        </div>
      {/each}
    </section>
  {/if}
{/each}
{#if todos.length === 0}
  <p class="empty">Nothing to do. Enjoy it.</p>
{/if}
<span class="visually-hidden" aria-live="polite">{status}</span>

<style>
  .bar { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
  .count { color: var(--ink-2); }
  .u-now { color: var(--critical); }
  .u-soon { color: var(--serious); }
  .u-later { color: var(--muted); }
  .sec > h2 { display: flex; align-items: center; gap: 10px; }
  .mini { padding: 1px 8px; font-size: 11px; }
  .todo {
    display: flex;
    align-items: baseline;
    gap: 10px;
    padding: 7px 10px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 7px;
    margin-bottom: 5px;
  }
  .todo:nth-of-type(even) { background: color-mix(in srgb, var(--plane) 45%, var(--surface)); }
  .todo input { margin: 0; accent-color: var(--accent); }
  .todo label { flex: 1; cursor: pointer; }
  .isdone .action { text-decoration: line-through; color: var(--muted); }
  .isdone .action a { text-decoration: line-through; color: var(--muted); }
  .why { color: var(--muted); font-size: 12px; margin-left: 8px; }
  .agent { color: var(--accent); border-color: var(--accent); }
  .todo .repobtn { white-space: nowrap; font-size: 12.5px; }
  .empty { color: var(--muted); margin-top: 20px; }
  .visually-hidden {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    white-space: nowrap;
    border: 0;
  }
</style>
