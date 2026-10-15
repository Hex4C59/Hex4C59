import assert from 'node:assert/strict'

const deferred = () => {
  let resolve
  let reject
  const promise = new Promise((yes, no) => { resolve = yes; reject = no })
  return { promise, resolve, reject }
}

export async function verifyLifecycle({ Context, FiberState }, { createScope, scopeOf, scopeParentOf, scopeTarget }) {
  const results = []
  const check = async (name, body) => {
    const ctx = new Context()
    try {
      results.push({ name, observation: await body(ctx) })
      console.log(`PASS ${name}`)
    } finally {
      // The root fiber's dispose is a restart; this drains this test's owned work.
      await ctx.fiber.dispose()
    }
  }

  await check('effect executes now and public disposer is single-shot', async ctx => {
    const trace = []
    const stop = ctx.effect(() => { trace.push('setup'); return () => { trace.push('cleanup') } }, 'lab/one')
    assert.deepEqual(trace, ['setup'])
    assert.equal(typeof stop, 'function')
    await stop()
    assert.equal(stop(), undefined)
    assert.deepEqual(trace, ['setup', 'cleanup'])
    assert.equal(ctx.fiber.getEffects().some(x => x.label === 'lab/one'), false)
    return trace
  })

  await check('one generator effect waits in reverse yield order', async ctx => {
    const trace = []
    const gate = deferred()
    const began = deferred()
    const stop = ctx.effect(function* () {
      yield () => { trace.push('A') }
      yield async () => { trace.push('B:start'); began.resolve(); await gate.promise; trace.push('B:end') }
    }, 'lab/composite')
    const draining = Promise.resolve(stop())
    await began.promise
    assert.deepEqual(trace, ['B:start'])
    gate.resolve()
    await draining
    assert.deepEqual(trace, ['B:start', 'B:end', 'A'])
    return trace
  })

  await check('fiber siblings start in reverse order but overlap', async ctx => {
    const trace = []
    const a = deferred(), b = deferred(), startedA = deferred(), startedB = deferred(), endedA = deferred()
    const fiber = await ctx.plugin(inner => {
      inner.effect(() => async () => { trace.push('A:start'); startedA.resolve(); await a.promise; trace.push('A:end'); endedA.resolve() })
      inner.effect(() => async () => { trace.push('B:start'); startedB.resolve(); await b.promise; trace.push('B:end') })
    })
    let complete = false
    const draining = fiber.dispose().then(() => { complete = true })
    await Promise.all([startedA.promise, startedB.promise])
    assert.deepEqual(trace, ['B:start', 'A:start'])
    a.resolve()
    await endedA.promise
    assert.equal(complete, false)
    b.resolve()
    await draining
    assert.deepEqual(trace, ['B:start', 'A:start', 'A:end', 'B:end'])
    return trace
  })

  await check('yielding exact scope disposer adopts its cleanup order', async ctx => {
    const trace = []
    const gate = deferred(), began = deferred()
    const owner = await ctx.plugin(inner => {
      inner.effect(function* () {
        yield () => { trace.push('tail') }
        const scope = createScope(inner, {})
        scope.ctx.effect(() => async () => { trace.push('scope:start'); began.resolve(); await gate.promise; trace.push('scope:end') })
        yield scope.rawDispose
        yield () => { trace.push('B') }
      }, 'lab/exact')
    })
    const draining = owner.dispose()
    await began.promise
    assert.deepEqual(trace, ['B', 'scope:start'])
    gate.resolve()
    await draining
    assert.deepEqual(trace, ['B', 'scope:start', 'scope:end', 'tail'])
    return trace
  })

  await check('wrapping the scope disposer leaves it a concurrent sibling', async ctx => {
    const trace = []
    const gateB = deferred(), gateScope = deferred(), beganB = deferred(), beganScope = deferred(), tail = deferred()
    const owner = await ctx.plugin(inner => {
      inner.effect(function* () {
        yield () => { trace.push('tail'); tail.resolve() }
        const scope = createScope(inner, {})
        scope.ctx.effect(() => async () => { trace.push('scope:start'); beganScope.resolve(); await gateScope.promise; trace.push('scope:end') })
        yield () => scope.rawDispose()
        yield async () => { trace.push('B:start'); beganB.resolve(); await gateB.promise; trace.push('B:end') }
      }, 'lab/wrapped')
    })
    let complete = false
    const draining = owner.dispose().then(() => { complete = true })
    await Promise.all([beganB.promise, beganScope.promise])
    assert.deepEqual(trace, ['B:start', 'scope:start'])
    gateB.resolve()
    await tail.promise
    assert.equal(complete, false)
    assert.deepEqual(trace, ['B:start', 'scope:start', 'B:end', 'tail'])
    gateScope.resolve()
    await draining
    assert.deepEqual(trace, ['B:start', 'scope:start', 'B:end', 'tail', 'scope:end'])
    return trace
  })

  await check('awaiting an effect waits for setup and yields a disposer', async ctx => {
    const trace = []
    const gate = deferred()
    const stop = ctx.effect(async () => {
      trace.push('setup')
      await gate.promise
      trace.push('ready')
      return () => { trace.push('cleanup') }
    })
    gate.resolve()
    const readyStop = await stop
    assert.equal(typeof readyStop, 'function')
    assert.deepEqual(trace, ['setup', 'ready'])
    await readyStop()
    assert.deepEqual(trace, ['setup', 'ready', 'cleanup'])
    const pluginGate = deferred(), pluginBegan = deferred()
    const fiber = ctx.plugin(async inner => {
      const pending = inner.effect(async () => { pluginBegan.resolve(); await pluginGate.promise; return () => {} })
      await pending
    })
    await pluginBegan.promise
    assert.equal(fiber.state, FiberState.LOADING)
    pluginGate.resolve()
    await fiber.await()
    assert.equal(fiber.state, FiberState.ACTIVE)
    await fiber.dispose()
    return trace
  })

  await check('unload waits for late async acquisition and then cleans it', async ctx => {
    const trace = []
    const gate = deferred()
    const fiber = await ctx.plugin(inner => {
      inner.effect(async () => { await gate.promise; trace.push('acquired'); return () => { trace.push('cleanup') } })
    })
    assert.equal(fiber.state, FiberState.ACTIVE, 'unawaited nested setup does not hold plugin loading open')
    let complete = false
    const draining = fiber.dispose().then(() => { complete = true })
    assert.equal(fiber.uid, null)
    assert.equal(complete, false)
    gate.resolve()
    await draining
    assert.deepEqual(trace, ['acquired', 'cleanup'])
    assert.equal(fiber.state, FiberState.DISPOSED)
    return trace
  })

  await check('reentrant unload sees the effect before setup returns', async ctx => {
    const trace = []
    let inner, draining
    const owner = await ctx.plugin(value => { inner = value })
    inner.effect(() => {
      trace.push('setup')
      draining = owner.dispose()
      trace.push('setup:return')
      return () => { trace.push('cleanup') }
    })
    await draining
    assert.deepEqual(trace, ['setup', 'setup:return', 'cleanup'])
    assert.throws(() => inner.effect(() => () => {}), e => e.code === 'INACTIVE_EFFECT')
    return trace
  })

  await check('sync setup failure rolls back and remains owner-visible while pending', async ctx => {
    const trace = []
    const gate = deferred(), began = deferred()
    let inner
    const owner = await ctx.plugin(value => { inner = value })
    const failure = new Error('setup failed')
    assert.throws(() => inner.effect(function* () {
      yield async () => { trace.push('rollback:start'); began.resolve(); await gate.promise; trace.push('rollback:end') }
      throw failure
    }, 'lab/failed-setup'), e => e === failure)
    await began.promise
    assert.equal(inner.fiber.getEffects().some(x => x.label === 'lab/failed-setup'), true)
    const draining = owner.dispose()
    gate.resolve()
    await draining
    assert.deepEqual(trace, ['rollback:start', 'rollback:end'])
    return trace
  })

  await check('async setup rejection releases previously yielded resources', async ctx => {
    const trace = []
    const setup = deferred(), cleanup = deferred(), began = deferred()
    let inner
    const owner = await ctx.plugin(value => { inner = value })
    const stop = inner.effect(async function* () {
      yield async () => { trace.push('rollback:start'); began.resolve(); await cleanup.promise; trace.push('rollback:end') }
      await setup.promise
      throw new Error('async setup failed')
    })
    const setupResult = assert.rejects(Promise.resolve(stop), /async setup failed/)
    setup.resolve()
    await setupResult
    await began.promise
    const draining = owner.dispose()
    cleanup.resolve()
    await draining
    assert.deepEqual(trace, ['rollback:start', 'rollback:end'])
    return trace
  })

  await check('invalid setup result is rejected', ctx => {
    assert.throws(() => ctx.effect(() => 42), /Invalid effect/)
    return 'TypeError: Invalid effect'
  })

  await check('one composite failure stops older members while fiber drains siblings', async ctx => {
    const trace = []
    const failure = new Error('cleanup failed')
    const owner = await ctx.plugin(inner => {
      inner.effect(() => () => { trace.push('sibling') })
      inner.effect(function* () {
        yield () => { trace.push('older') }
        yield () => { trace.push('failed'); throw failure }
      })
    })
    await owner.dispose()
    assert.deepEqual(trace, ['failed', 'sibling'])
    assert.equal(ctx.logger.buffer.some(x => x.args.includes(failure)), true)
    return { trace, errorLogged: true, disposeResolved: true }
  })

  await check('public repeat call does not join but structural owners join in-flight cleanup', async ctx => {
    const gate = deferred(), began = deferred()
    let stop, outer, calls = 0, tailRan = false, inner
    const owner = await ctx.plugin(value => {
      inner = value
      stop = value.effect(() => async () => { calls++; began.resolve(); await gate.promise }, 'lab/in-flight')
      outer = value.effect(function* () {
        yield () => { tailRan = true }
        yield stop
      }, 'lab/outer')
    })
    const first = stop()
    await began.promise
    assert.equal(stop(), undefined)
    const meta = inner.fiber.getEffects().find(x => x.label === 'lab/outer')
    assert.equal(meta.children.some(x => x.label === 'lab/in-flight'), true)
    const ordered = outer()
    assert.equal(tailRan, false, 'the older outer cleanup must wait for the already-started child')
    const draining = owner.dispose()
    gate.resolve()
    await Promise.all([first, ordered, draining])
    assert.equal(tailRan, true)
    assert.equal(calls, 1)
    return { publicRepeat: 'undefined', tailWaited: true, calls }
  })

  await check('pending plugin can own pre-activation effects that still unload', async ctx => {
    let started = false, cleaned = 0
    const plugin = { inject: ['lab_missing'], apply() { started = true } }
    ctx.on('internal/plugin', fiber => {
      if (fiber.runtime?.callback === plugin.apply && fiber.uid !== null) {
        fiber.ctx.effect(() => () => { cleaned++ })
      }
    })
    const fiber = await ctx.plugin(plugin)
    assert.equal(fiber.state, FiberState.PENDING)
    assert.equal(started, false)
    await fiber.dispose()
    assert.equal(cleaned, 1)
    assert.equal(fiber.state, FiberState.DISPOSED)
    return { started, cleaned }
  })

  await check('dispose during loading prevents a stale plugin callback', async ctx => {
    let runs = 0
    const fiber = ctx.plugin(() => { runs++ })
    await fiber.dispose()
    assert.equal(runs, 0)
    assert.equal(fiber.state, FiberState.DISPOSED)
    return { runs, state: 'DISPOSED' }
  })

  await check('dependency loss unloads without disposing and replacement reloads', async ctx => {
    let runs = 0, cleanups = 0
    const provider = inner => { inner.provide('lab_service', {}) }
    const first = await ctx.plugin(provider)
    const consumer = await ctx.plugin({ inject: ['lab_service'], apply() { runs++; return () => { cleanups++ } } })
    const uid = consumer.uid
    await first.dispose()
    await consumer.await()
    assert.equal(consumer.state, FiberState.PENDING)
    assert.equal(consumer.uid, uid)
    const second = await ctx.plugin(provider)
    await consumer.await()
    assert.equal(consumer.state, FiberState.ACTIVE)
    assert.equal(runs, 2)
    assert.equal(cleanups, 1)
    await consumer.dispose()
    await second.dispose()
    return { uidPreserved: true, runs, cleanups }
  })

  await check('parent waits for child cleanup while its own cleanup overlaps', async ctx => {
    const trace = []
    const a = deferred(), b = deferred(), beganA = deferred(), beganB = deferred()
    let childFiber
    const parent = await ctx.plugin(inner => {
      inner.effect(() => async () => { trace.push('parent:start'); beganA.resolve(); await a.promise; trace.push('parent:end') })
      childFiber = inner.plugin(child => {
        child.effect(() => async () => { trace.push('child:start'); beganB.resolve(); await b.promise; trace.push('child:end') })
      })
    })
    await childFiber.await()
    let complete = false
    const draining = parent.dispose().then(() => { complete = true })
    await Promise.all([beganA.promise, beganB.promise])
    a.resolve()
    b.resolve()
    await draining
    assert.equal(complete, true)
    assert.ok(trace.indexOf('parent:start') < trace.indexOf('child:end'))
    return trace
  })

  await check('scope routing ancestry does not reparent sibling fibers', async ctx => {
    const trace = []
    const owner = await ctx.plugin(() => {})
    const keyA = {}, keyB = {}
    const a = createScope(owner.ctx, keyA)
    const b = createScope(owner.ctx, keyB, { parent: keyA })
    await Promise.all([a.ctx.fiber.await(), b.ctx.fiber.await()])
    assert.equal(scopeOf(b.ctx.extend({})), keyB)
    assert.equal(scopeParentOf(keyB), keyA)
    a.ctx.on('lab/scoped', () => { trace.push('A') })
    b.ctx.on('lab/scoped', () => { trace.push('B') })
    await a.dispose()
    assert.equal(b.ctx.fiber.state, FiberState.ACTIVE)
    ctx.emit(scopeTarget({}, keyB), 'lab/scoped')
    assert.deepEqual(trace, ['B'])
    await owner.dispose()
    assert.equal(b.ctx.fiber.state, FiberState.DISPOSED)
    return { trace, bSurvivedA: true, bDisposedWithOwner: true }
  })

  await check('scope public disposal shares quiescence after raw disposal starts', async ctx => {
    const gate = deferred(), began = deferred()
    const owner = await ctx.plugin(() => {})
    const scope = createScope(owner.ctx, {})
    await scope.ctx.fiber.await()
    let finished = false
    scope.ctx.effect(() => async () => { began.resolve(); await gate.promise; finished = true })
    const raw = Promise.resolve(scope.rawDispose())
    await began.promise
    const first = scope.dispose(), second = scope.dispose()
    assert.equal(first, second)
    assert.equal(finished, false)
    gate.resolve()
    await Promise.all([raw, first, second])
    assert.equal(finished, true)
    return { sharedPromise: true, rawStartedFirst: true, finished }
  })

  await check('extend shares the existing fiber rather than minting an owner', async ctx => {
    let cleaned = 0
    const owner = await ctx.plugin(() => {})
    const derived = owner.ctx.extend({ purpose: 'derived' })
    assert.equal(derived.fiber, owner.ctx.fiber)
    derived.effect(() => () => { cleaned++ })
    await owner.dispose()
    assert.equal(cleaned, 1)
    return { sameFiber: true, cleaned }
  })

  await check('restart preserves uid while dispose is terminal except for root', async ctx => {
    let runs = 0, cleanups = 0
    const fiber = await ctx.plugin(() => { runs++; return () => { cleanups++ } })
    const uid = fiber.uid
    await fiber.restart()
    assert.equal(fiber.uid, uid)
    assert.equal(runs, 2)
    assert.equal(cleanups, 1)
    await fiber.dispose()
    assert.equal(fiber.uid, null)
    await assert.rejects(fiber.restart(), e => e.code === 'INACTIVE_EFFECT')
    assert.equal(cleanups, 2)
    await ctx.fiber.dispose()
    assert.equal(ctx.fiber.uid, 0)
    assert.equal(ctx.fiber.state, FiberState.ACTIVE)
    return { runs, cleanups, rootUid: 0, rootState: 'ACTIVE' }
  })

  await check('registry delete starts cleanup but is not a completion barrier', async ctx => {
    const gate = deferred(), began = deferred()
    let finished = false
    const plugin = () => async () => { began.resolve(); await gate.promise; finished = true }
    const fiber = await ctx.plugin(plugin)
    const removed = ctx.registry.delete(plugin)
    assert.ok(removed && typeof removed === 'object')
    assert.equal(ctx.registry.has(plugin), false)
    await began.promise
    assert.equal(finished, false)
    const draining = fiber.await()
    gate.resolve()
    await draining
    assert.equal(finished, true)
    return { returnedRuntime: true, finishedBeforeRelease: false, finished }
  })
  return results
}
