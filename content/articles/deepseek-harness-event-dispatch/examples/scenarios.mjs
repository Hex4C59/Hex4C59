import assert from 'node:assert/strict'

const deferred = () => {
  let resolve
  let reject
  const promise = new Promise((yes, no) => { resolve = yes; reject = no })
  return { promise, resolve, reject }
}

export async function verifyEvents({ Context, isBailed }) {
  const results = []
  const check = async (name, body) => {
    const ctx = new Context()
    try {
      const observation = await body(ctx)
      results.push({ name, observation })
      console.log(`PASS ${name}`)
    } finally {
      await ctx.fiber.dispose()
    }
  }

  await check('bail values include zero and empty string', ctx => {
    assert.deepEqual([undefined, null, false, 0, '', NaN, true, {}].map(isBailed), [false, false, false, true, true, true, true, true])
    const trace = []
    for (const value of [undefined, false, 0, 'late']) ctx.on('lab/value', () => { trace.push(String(value)); return value })
    assert.equal(ctx.bail('lab/value'), 0)
    assert.deepEqual(trace, ['undefined', 'false', '0'])
    return trace
  })

  await check('emit returns before async listener settles', async ctx => {
    const gate = deferred()
    const trace = []
    let pending
    ctx.on('lab/emit', () => { trace.push('A:start'); pending = gate.promise.then(() => trace.push('A:end')); return pending })
    ctx.on('lab/emit', () => trace.push('B'))
    assert.equal(ctx.emit('lab/emit'), undefined)
    assert.deepEqual(trace, ['A:start', 'B'])
    gate.resolve()
    await pending
    assert.deepEqual(trace, ['A:start', 'B', 'A:end'])
    return trace
  })

  await check('emit synchronous throw prevents later listeners', ctx => {
    const trace = []
    const problem = new Error('emit failed')
    ctx.on('lab/throw', () => { trace.push('A'); throw problem })
    ctx.on('lab/throw', () => trace.push('B'))
    assert.throws(() => ctx.emit('lab/throw'), error => error === problem)
    assert.deepEqual(trace, ['A'])
    return trace
  })

  await check('parallel starts all and waits for all before AggregateError', async ctx => {
    const a = deferred()
    const b = deferred()
    const trace = []
    const problemA = new Error('A')
    const problemB = new Error('B')
    ctx.on('lab/all', () => { trace.push('A:start'); return a.promise })
    ctx.on('lab/all', () => { trace.push('B:start'); return b.promise })
    ctx.on('lab/all', () => { trace.push('C:throw'); throw problemB })
    const observed = ctx.parallel('lab/all').then(() => null, error => error)
    assert.deepEqual(trace, ['A:start', 'B:start', 'C:throw'])
    let settled = false
    observed.then(() => { settled = true })
    a.reject(problemA)
    await Promise.resolve()
    await Promise.resolve()
    assert.equal(settled, false)
    b.resolve('ignored')
    const error = await observed
    assert.ok(error instanceof AggregateError)
    assert.deepEqual(error.errors, [problemA, problemB])
    return { trace, errors: error.errors.map(e => e.message) }
  })

  await check('serial awaits and stops on a resolved bail value', async ctx => {
    const gate = deferred()
    const trace = []
    ctx.on('lab/serial', async () => { trace.push('A:start'); await gate.promise; trace.push('A:end'); return false })
    ctx.on('lab/serial', () => { trace.push('B'); return '' })
    ctx.on('lab/serial', () => trace.push('C'))
    const result = ctx.serial('lab/serial')
    assert.deepEqual(trace, ['A:start'])
    gate.resolve()
    assert.equal(await result, '')
    assert.deepEqual(trace, ['A:start', 'A:end', 'B'])
    return trace
  })

  await check('serial rejects and skips remaining listeners', async ctx => {
    const trace = []
    const problem = new Error('serial failed')
    ctx.on('lab/fail', async () => { trace.push('A'); throw problem })
    ctx.on('lab/fail', () => trace.push('B'))
    await assert.rejects(ctx.serial('lab/fail'), error => error === problem)
    assert.deepEqual(trace, ['A'])
    return trace
  })

  await check('bail treats a Promise as an immediate bail value', async ctx => {
    const trace = []
    const pending = Promise.resolve(false)
    ctx.on('lab/promise', () => { trace.push('A'); return pending })
    ctx.on('lab/promise', () => trace.push('B'))
    const result = ctx.bail('lab/promise')
    assert.equal(result, pending)
    assert.equal(await result, false)
    assert.deepEqual(trace, ['A'])
    return trace
  })

  await check('waterfall wraps next in entry and reverse exit order', ctx => {
    const trace = []
    for (const name of ['A', 'B']) ctx.on('lab/wrap', (value, next) => { trace.push(`${name}:before`); const answer = next(); trace.push(`${name}:after`); return answer + name })
    const result = ctx.waterfall('lab/wrap', 'payload', () => { trace.push('inner'); return 'x' })
    assert.equal(result, 'xBA')
    assert.deepEqual(trace, ['A:before', 'B:before', 'inner', 'B:after', 'A:after'])
    return { result, trace }
  })

  await check('waterfall without next stops regardless of undefined result', ctx => {
    const trace = []
    ctx.on('lab/veto', () => { trace.push('A'); return undefined })
    ctx.on('lab/veto', (_value, next) => { trace.push('B'); return next() })
    assert.equal(ctx.waterfall('lab/veto', 'payload', () => trace.push('inner')), undefined)
    assert.deepEqual(trace, ['A'])
    return trace
  })

  await check('waterfall propagates promises when listeners return them', async ctx => {
    const trace = []
    ctx.on('lab/async-wrap', async (_value, next) => { trace.push('A:before'); const value = await next(); trace.push('A:after'); return value + 1 })
    const result = await ctx.waterfall('lab/async-wrap', 'payload', async () => { trace.push('inner'); return 3 })
    assert.equal(result, 4)
    assert.deepEqual(trace, ['A:before', 'inner', 'A:after'])
    return { result, trace }
  })

  await check('waterfall permits repeated next and repeated inner calls', ctx => {
    let count = 0
    ctx.on('lab/repeat', (_value, next) => { next(); return next() })
    assert.equal(ctx.waterfall('lab/repeat', 'payload', () => ++count), 2)
    assert.equal(count, 2)
    return { innerCalls: count }
  })

  await check('prepend changes order; current dispatch uses a snapshot', ctx => {
    const trace = []
    let removeB
    let added = false
    ctx.on('lab/order', () => {
      trace.push('A'); removeB()
      if (!added) { added = true; ctx.on('lab/order', () => trace.push('C')) }
    })
    removeB = ctx.on('lab/order', () => trace.push('B'))
    ctx.on('lab/order', () => trace.push('P'), { prepend: true })
    ctx.emit('lab/order')
    assert.deepEqual(trace, ['P', 'A', 'B'])
    ctx.emit('lab/order')
    assert.deepEqual(trace, ['P', 'A', 'B', 'P', 'A', 'C'])
    return trace
  })

  await check('once removes before a reentrant emit', ctx => {
    let count = 0
    ctx.once('lab/once', () => { count++; ctx.emit('lab/once') })
    ctx.emit('lab/once')
    ctx.emit('lab/once')
    assert.equal(count, 1)
    return { calls: count }
  })

  await check('once can remain in an older dispatch snapshot', ctx => {
    let nested = false
    let calls = 0
    ctx.on('lab/once-snapshot', () => {
      if (!nested) { nested = true; ctx.emit('lab/once-snapshot') }
    })
    ctx.once('lab/once-snapshot', () => { calls++ })
    ctx.emit('lab/once-snapshot')
    assert.equal(calls, 2)
    return { calls }
  })

  await check('empty dispatch defaults and parallel success return', async ctx => {
    assert.equal(ctx.emit('lab/empty'), undefined)
    assert.equal(ctx.bail('lab/empty'), undefined)
    assert.equal(await ctx.serial('lab/empty'), undefined)
    assert.equal(await ctx.parallel('lab/empty'), undefined)
    assert.equal(ctx.waterfall('lab/empty', () => 42), 42)
    ctx.on('lab/success', () => 7)
    assert.equal(await ctx.parallel('lab/success'), undefined)
    return { ordinary: 'undefined', waterfall: 42, parallelSuccess: 'undefined' }
  })

  await check('dispatch receiver controls filter and callback this', ctx => {
    const a = ctx.extend({ labTag: 'A' })
    const b = ctx.extend({ labTag: 'B' })
    const trace = []
    const receiver = { [Context.filter]: owner => owner.labTag === 'A' }
    const receivers = []
    a.on('lab/filter', function () { receivers.push(this); trace.push('A') })
    b.on('lab/filter', () => trace.push('B'))
    b.on('lab/filter', () => trace.push('global'), { global: true })
    ctx.emit(receiver, 'lab/filter')
    assert.deepEqual(trace, ['A', 'global'])
    assert.equal(receivers[0], receiver)
    trace.length = 0
    ctx.emit('lab/filter')
    assert.deepEqual(trace, ['A', 'B', 'global'])
    assert.equal(receivers[1], null)
    return trace
  })

  await check('fiber disposal removes its listener', async ctx => {
    let calls = 0
    const fiber = await ctx.plugin(child => { child.on('lab/owned', () => { calls++ }) })
    ctx.emit('lab/owned')
    assert.equal(calls, 1)
    await fiber.dispose()
    ctx.emit('lab/owned')
    assert.equal(calls, 1)
    return { calls }
  })

  await check('parallel diagnostics are reported as emit in this snapshot', async ctx => {
    const modes = []
    ctx.on('internal/dispatch', (mode, name) => { if (name === 'lab/diagnostic') modes.push(mode) })
    ctx.on('lab/diagnostic', () => {})
    ctx.emit('lab/diagnostic')
    await ctx.parallel('lab/diagnostic')
    await ctx.serial('lab/diagnostic')
    ctx.bail('lab/diagnostic')
    ctx.waterfall('lab/diagnostic', () => {})
    assert.deepEqual(modes, ['emit', 'emit', 'serial', 'bail', 'waterfall'])
    return modes
  })

  return results
}
