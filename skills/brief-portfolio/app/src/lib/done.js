// Shared checked-state for todos, keyed by stable todo id.
// ponytail: localStorage-on-file:// is one shared bucket; fine for one user
const KEY = 'brief-portfolio-done'

let storageBlocked = false

export const isStorageBlocked = () => storageBlocked

export const loadDone = () => {
  try {
    return new Set(JSON.parse(localStorage.getItem(KEY) ?? '[]'))
  } catch {
    storageBlocked = true
    return new Set()
  }
}

export const saveDone = (s) => {
  try {
    localStorage.setItem(KEY, JSON.stringify([...s]))
  } catch {
    storageBlocked = true
  }
}

// Drop ids that no longer exist in the payload so the set can't grow forever.
export function pruneDone(validIds) {
  const done = loadDone()
  const kept = new Set([...done].filter((id) => validIds.has(id)))
  if (kept.size !== done.size) saveDone(kept)
  return kept
}
