import { test } from 'node:test'
import assert from 'node:assert/strict'
import { waitFor } from './smoke.harness.js'

test('waitFor resolves once the predicate turns true', async () => {
  let ready = false
  setTimeout(() => { ready = true }, 20)
  await waitFor(() => ready, { timeout: 200, interval: 5 })
  assert.equal(ready, true)
})

test('waitFor awaits the supplied flush between predicate checks', async () => {
  let value = false
  let pending = false
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
    assert.equal(pending, false, 'predicate ran while a flush was still pending, meaning waitFor did not await it')
    return value
  }, { flush, interval: 5, timeout: 200 })
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
