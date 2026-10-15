import assert from 'node:assert/strict'

export async function verifyOwnership(modules) {
  const { Context } = modules.cordis
  const { default: Registry } = modules['dsh-agent']
  const Loop = modules['dsh-agent-loop'].default
  const { SessionId, SessionLogOffset } = modules['dsh-session']
  const results = []
  let sequence = 0
  async function check(name, body, withLoop = true) {
    const ctx = new Context(), gates = []
    const gate = () => { const d = Promise.withResolvers(); gates.push(d); return d }
    let loop
    try {
      if (withLoop) {
        for (const plugin of [modules['dsh-llm'].default, modules['dsh-session'].default, modules['dsh-session-projection'].default]) await ctx.plugin(plugin)
        await ctx.plugin(modules['dsh-system-prompt'].default, { personaPrefix: 'Local ownership experiment.' })
        await ctx.plugin(modules['dsh-tools'].default)
      }
      await ctx.plugin(Registry)
      if (withLoop) loop = await ctx.plugin(Loop, { agents: [] })
      const value = await body({ ctx, loop, gate })
      results.push({ name, observation: value })
      console.log(`PASS ${name}`)
    } finally {
      for (const d of gates) d.resolve()
      await ctx.fiber.dispose()
    }
  }
  const id = label => SessionId(`lab-${label}-${++sequence}`)
  const observed = promise => { void promise.catch(() => {}); return promise }
  async function owner(ctx) {
    let current
    const plugin = Object.assign(inner => { current = inner }, { inject: ['agents'] })
    const fiber = await ctx.plugin(plugin)
    return { ctx: current, fiber }
  }
  function synthetic(ctx, key) {
    // Only registry identity/announcement tests use a minimal synthetic Agent.
    return { id: key, session: { id: key }, ctx, status: 'idle' }
  }
  function memoryPersistence(ctx, overrides = {}) {
    const state = { appended: [], closes: 0, headers: [] }
    ctx.provide('sessionPersistence', {
      async create(header, options) {
        state.headers.push(header)
        return {
          header, inheritedEventCount: options.inheritedEventCount,
          async append(events) { state.appended.push(...events) },
          async close() { state.closes++; await overrides.close?.() },
          ...overrides.handle,
        }
      },
      ...overrides.provider,
    })
    return state
  }

  await check('registry create rejects without a factory', async ({ ctx }) => {
    await assert.rejects(ctx.agents.create({ sessionId: id('no-factory') }), /no agent factory/)
    assert.deepEqual(ctx.agents.list(), [])
    return { noFactory: true }
  }, false)

  await check('real creation shares identity and returns a separate disposal capability', async ({ ctx }) => {
    const key = id('created'), handle = await ctx.agents.create({ sessionId: key })
    assert.equal(handle.agent.id, handle.agent.session.id)
    assert.equal(ctx.agents.get(key), handle.agent)
    assert.equal(ctx.sessions.get(key), handle.agent.session)
    assert.equal(typeof handle.dispose, 'function')
    assert.equal(handle.agent.dispose, undefined)
    assert.deepEqual(ctx.agents.roots(), [handle.agent])
    await handle.dispose()
    assert.equal(ctx.agents.get(key), undefined); assert.equal(ctx.sessions.get(key), undefined)
    return { sameIdentity: true, separateHandle: true }
  })

  await check('setup and commit remain unpublished before ordered announcements finish', async ({ ctx, gate }) => {
    const entered = gate(), release = gate(), key = id('publish'), trace = []
    let prepared, returned = false
    ctx.on('session/created', () => { trace.push('session/created') })
    ctx.on('agent/created', async () => { trace.push('agent:first:start'); entered.resolve(); await release.promise; trace.push('agent:first:end') })
    ctx.on('agent/created', () => { trace.push('agent:second') })
    const creating = observed(ctx.agents.create({ sessionId: key, setup(agentCtx, agent) {
      prepared = agent
      assert.equal(agentCtx, agent.ctx)
      assert.equal(ctx.agents.get(key), undefined); assert.equal(ctx.sessions.get(key), undefined)
      trace.push('setup')
      return { commit() { assert.equal(ctx.agents.get(key), undefined); trace.push('commit') } }
    } }).then(handle => { returned = true; trace.push('returned'); return handle }))
    await entered.promise
    assert.equal(returned, false); assert.equal(ctx.agents.get(key), prepared)
    assert.deepEqual(trace, ['setup', 'commit', 'session/created', 'agent:first:start'])
    release.resolve(); const handle = await creating
    assert.deepEqual(trace, ['setup', 'commit', 'session/created', 'agent:first:start', 'agent:first:end', 'agent:second', 'returned'])
    await handle.dispose()
    return trace
  })

  await check('rejected setup unwinds its scope without announcing either registry', async ({ ctx }) => {
    const key = id('setup-failure'), trace = []
    ctx.on('session/created', () => { trace.push('session/created') })
    ctx.on('agent/created', () => { trace.push('agent/created') })
    await assert.rejects(ctx.agents.create({ sessionId: key, setup(agentCtx) {
      agentCtx.effect(() => () => { trace.push('scope cleanup') })
      throw new Error('setup rejected')
    } }), /setup rejected/)
    assert.deepEqual(trace, ['scope cleanup'])
    assert.equal(ctx.agents.get(key), undefined); assert.equal(ctx.sessions.get(key), undefined)
    const retry = await ctx.agents.create({ sessionId: key }); await retry.dispose()
    return { unpublished: true, identityReusable: true }
  })

  await check('publication commit failure is rolled back before announcement', async ({ ctx }) => {
    const key = id('commit-failure'), trace = []
    ctx.on('agent/created', () => { trace.push('created') })
    await assert.rejects(ctx.agents.create({ sessionId: key, setup(agentCtx) {
      agentCtx.effect(() => () => { trace.push('scope cleanup') })
      return { commit() { throw new Error('commit rejected') } }
    } }), /commit rejected/)
    assert.deepEqual(trace, ['scope cleanup'])
    assert.equal(ctx.sessions.get(key), undefined)
    return trace
  })

  await check('owner unload aborts an unfinished setup wait and rejects late registrations', async ({ ctx, gate }) => {
    const caller = await owner(ctx), began = gate(), release = gate(), key = id('setup-abort')
    let scoped
    const creating = observed(caller.ctx.agents.create({ sessionId: key, setup(agentCtx) { scoped = agentCtx; began.resolve(); return release.promise } }))
    await began.promise
    await caller.fiber.dispose()
    await assert.rejects(creating, /disposed|aborted/)
    assert.equal(ctx.agents.get(key), undefined); assert.equal(ctx.sessions.get(key), undefined)
    assert.throws(() => scoped.effect(() => () => {}), /disposed|active|inactive/)
    release.resolve()
    return { unpublished: true, lateRegistrationRejected: true }
  })

  await check('pre-aborted creation never becomes live', async ({ ctx }) => {
    const controller = new AbortController(), key = id('pre-abort')
    controller.abort(new Error('cancel before create'))
    await assert.rejects(ctx.agents.create({ sessionId: key, signal: controller.signal }), /cancel before create/)
    assert.equal(ctx.agents.get(key), undefined); assert.equal(ctx.sessions.get(key), undefined)
    return { neverLive: true }
  })

  await check('creation listener failure skips later listeners and pairs visible announcements', async ({ ctx }) => {
    const trace = [], key = id('listener-fail')
    ctx.on('session/created', () => { trace.push('session/created') })
    ctx.on('agent/created', () => { trace.push('agent/created:first'); throw new Error('created rejected') })
    ctx.on('agent/created', () => { trace.push('unreached') })
    ctx.on('agent/disposed', () => { trace.push('agent/disposed') })
    ctx.on('session/disposed', () => { trace.push('session/disposed') })
    await assert.rejects(ctx.agents.create({ sessionId: key }), /created rejected/)
    assert.deepEqual(trace, ['session/created', 'agent/created:first', 'agent/disposed', 'session/disposed'])
    assert.equal(ctx.agents.get(key), undefined); assert.equal(ctx.sessions.get(key), undefined)
    return trace
  })

  await check('owner unload retains entries and scope until creation listeners settle', async ({ ctx, gate }) => {
    const caller = await owner(ctx), began = gate(), release = gate(), key = id('announce-drain')
    let subject, cleaned = false, disposed = false
    ctx.on('agent/created', async ({ agent }) => { subject = agent; began.resolve(); await release.promise; assert.equal(ctx.agents.get(key), agent) })
    const creating = observed(caller.ctx.agents.create({ sessionId: key, setup(scoped) { scoped.effect(() => () => { cleaned = true }) } }))
    await began.promise
    const disposal = observed(caller.fiber.dispose().then(() => { disposed = true }))
    await Promise.resolve()
    assert.equal(disposed, false); assert.equal(cleaned, false)
    assert.equal(ctx.agents.get(key), subject); assert.equal(ctx.sessions.get(key), subject.session)
    release.resolve(); await disposal; await assert.rejects(creating, /disposed|aborted/)
    assert.equal(cleaned, true); assert.equal(ctx.agents.get(key), undefined)
    return { retainedThroughListener: true, cleanupAfterListener: true }
  })

  await check('unannounced registry insertion detaches without inventing a disposal event', async ({ ctx }) => {
    const trace = [], agent = synthetic(ctx, id('advanced'))
    ctx.on('agent/disposed', () => { trace.push('disposed') })
    const detach = ctx.agents.enter(agent, undefined)
    assert.equal(ctx.agents.get(agent.id), agent)
    detach(); detach()
    assert.deepEqual(trace, []); assert.equal(ctx.agents.get(agent.id), undefined)
    return { disposalEvents: 0 }
  }, false)

  await check('same-id registry collisions and stale detach capabilities preserve the exact entry', async ({ ctx }) => {
    const key = id('collision'), first = synthetic(ctx, key), second = synthetic(ctx, key)
    const detach = ctx.agents.enter(first, undefined)
    assert.throws(() => ctx.agents.enter(second, undefined), /already registered/)
    detach()
    const detachSecond = ctx.agents.enter(second, undefined)
    detach(); assert.equal(ctx.agents.get(key), second)
    detachSecond()
    return { collisionRejected: true, staleDetachSafe: true }
  }, false)

  await check('agent and session id mismatch is rejected at registry entry', async ({ ctx }) => {
    const agent = synthetic(ctx, id('identity')); agent.session.id = id('different')
    assert.throws(() => ctx.agents.enter(agent, undefined), /does not match/)
    assert.deepEqual(ctx.agents.list(), [])
    return { rejected: true }
  }, false)

  await check('detach inside creation dispatch waits until every serial listener settles', async ({ ctx }) => {
    const agent = synthetic(ctx, id('deferred-detach')), trace = []
    const detach = ctx.agents.enter(agent, undefined)
    ctx.on('agent/created', () => { trace.push('first'); detach(); assert.equal(ctx.agents.get(agent.id), agent) })
    ctx.on('agent/created', () => { trace.push('second'); assert.equal(ctx.agents.get(agent.id), agent) })
    ctx.on('agent/disposed', () => { trace.push('disposed') })
    await ctx.agents.announce(agent, 'startup')
    assert.deepEqual(trace, ['first', 'second', 'disposed'])
    assert.equal(ctx.agents.get(agent.id), undefined)
    return trace
  }, false)

  await check('announcement rejects both repeated and reentrant attempts', async ({ ctx }) => {
    const agent = synthetic(ctx, id('announce-once')), detach = ctx.agents.enter(agent, undefined)
    let reentrant
    ctx.on('agent/created', () => { reentrant = assert.rejects(ctx.agents.announce(agent, 'startup'), /already announced/) })
    await ctx.agents.announce(agent, 'startup'); await reentrant
    await assert.rejects(ctx.agents.announce(agent, 'startup'), /already announced/)
    detach()
    return { onlyOneAnnouncement: true }
  }, false)

  await check('register returns a single-shot Cordis disposer and records a runtime root', async ({ ctx }) => {
    const agent = synthetic(ctx, id('register'))
    const dispose = await ctx.agents.register(agent)
    assert.deepEqual(ctx.agents.roots(), [agent])
    await dispose(); assert.equal(dispose(), undefined)
    assert.equal(ctx.agents.get(agent.id), undefined)
    return { secondCall: 'undefined' }
  }, false)

  await check('disposal listener exceptions do not prevent later notifications', async ({ ctx }) => {
    const agent = synthetic(ctx, id('disposal-hooks')), trace = []
    ctx.on('agent/disposed', () => { throw new Error('observer failed') })
    ctx.on('agent/disposed', () => { trace.push('later observer') })
    const dispose = await ctx.agents.register(agent)
    await dispose()
    assert.deepEqual(trace, ['later observer'])
    return trace
  }, false)

  await check('concurrent handle disposals share one cleanup completion', async ({ ctx, gate }) => {
    const began = gate(), release = gate(); let starts = 0, finished = 0
    const handle = await ctx.agents.create({ sessionId: id('shared-dispose'), setup(scoped) {
      scoped.effect(() => async () => { starts++; began.resolve(); await release.promise; finished++ })
    } })
    const first = observed(handle.dispose()), second = observed(handle.dispose())
    await began.promise
    assert.equal(starts, 1); assert.equal(finished, 0)
    release.resolve(); await Promise.all([first, second]); await handle.dispose()
    assert.equal(starts, 1); assert.equal(finished, 1)
    return { cleanupStarts: starts, cleanupFinishes: finished }
  })

  await check('idle status can still hide maintenance that disposal must drain', async ({ ctx, gate }) => {
    const handle = await ctx.agents.create({ sessionId: id('maintenance') }), began = gate(), aborted = gate(), release = gate(), trace = []
    handle.agent.ctx.effect(() => () => { trace.push('scope cleanup') })
    ctx.on('agent/disposed', () => { trace.push('agent/disposed') })
    ctx.on('session/disposed', () => { trace.push('session/disposed') })
    const work = observed(handle.agent.runMaintenance(async signal => {
      signal.addEventListener('abort', () => { aborted.resolve() }, { once: true })
      began.resolve(); await release.promise; trace.push('work exit')
    }))
    await began.promise
    assert.equal(handle.agent.status, 'idle')
    const disposal = observed(handle.dispose())
    await aborted.promise
    assert.equal(ctx.agents.get(handle.agent.id), handle.agent)
    assert.deepEqual(trace, [])
    release.resolve(); await work; await disposal
    assert.deepEqual(trace, ['work exit', 'scope cleanup', 'agent/disposed', 'session/disposed'])
    return trace
  })

  await check('scope-effect failure is logged while factory teardown still detaches both registries', async ({ ctx }) => {
    const failure = new Error('scope release failed')
    const handle = await ctx.agents.create({ sessionId: id('failed-cleanup'), setup(scoped) { scoped.effect(() => () => { throw failure }) } })
    // Cordis itself logs a failing scope effect; factory-level close failures are tested separately below.
    await handle.dispose()
    assert.equal(ctx.logger.buffer.some(message => message.args.includes(failure)), true)
    assert.equal(ctx.agents.get(handle.agent.id), undefined); assert.equal(ctx.sessions.get(handle.agent.id), undefined)
    return { scopeFailureLogged: true, registriesDetached: true }
  })

  await check('caller fiber teardown only stops the agents it owns', async ({ ctx }) => {
    const a = await owner(ctx), b = await owner(ctx)
    const first = await a.ctx.agents.create({ sessionId: id('owner-a') }), second = await b.ctx.agents.create({ sessionId: id('owner-b') })
    await a.fiber.dispose()
    assert.equal(ctx.agents.get(first.agent.id), undefined)
    assert.equal(ctx.agents.get(second.agent.id), second.agent)
    await second.dispose()
    return { firstStopped: true, secondRetained: true }
  })

  await check('factory provider teardown stops agents across different caller fibers', async ({ ctx, loop }) => {
    const a = await owner(ctx), b = await owner(ctx)
    const first = await a.ctx.agents.create({ sessionId: id('provider-a') }), second = await b.ctx.agents.create({ sessionId: id('provider-b') })
    await loop.dispose()
    assert.equal(ctx.agents.get(first.agent.id), undefined); assert.equal(ctx.agents.get(second.agent.id), undefined)
    await assert.rejects(ctx.agents.create({ sessionId: id('after-provider') }), /factory|active|disposed/)
    await Promise.all([first.dispose(), second.dispose()])
    return { bothStopped: true, factorySlotCleared: true }
  })

  await check('retained caller context cannot create after its fiber is disposed', async ({ ctx }) => {
    const caller = await owner(ctx); await caller.fiber.dispose()
    await assert.rejects(async () => caller.ctx.agents.create({ sessionId: id('stale-owner') }), /active|disposed|inactive/)
    return { staleCallerRejected: true }
  })

  await check('runtime owner and durable session lineage are independent', async ({ ctx }) => {
    const parent = await ctx.agents.create({ sessionId: id('parent') })
    const fork = await ctx.agents.create({ sessionId: id('fork-root'), meta: { parentSession: parent.agent.id } })
    const child = await parent.agent.ctx.agents.create({ sessionId: id('child'), parentAgent: parent.agent })
    assert.equal(ctx.agents.isOwnedBy(fork.agent.id, parent.agent), false)
    assert.equal(ctx.agents.roots().includes(fork.agent), true)
    assert.equal(ctx.agents.isOwnedBy(child.agent.id, parent.agent), true)
    assert.equal(ctx.agents.roots().includes(child.agent), false)
    await parent.dispose()
    assert.equal(ctx.agents.get(child.agent.id), undefined)
    assert.equal(ctx.agents.get(fork.agent.id), fork.agent)
    await fork.dispose()
    return { forkIsRuntimeRoot: true, childFollowsCallerScope: true }
  })

  await check('parentAgent alone does not transfer the caller fiber cleanup obligation', async ({ ctx }) => {
    const parent = await ctx.agents.create({ sessionId: id('label-parent') })
    const labeled = await ctx.agents.create({ sessionId: id('root-owned'), parentAgent: parent.agent })
    assert.equal(ctx.agents.isOwnedBy(labeled.agent.id, parent.agent), true)
    await parent.dispose()
    assert.equal(ctx.agents.get(labeled.agent.id), labeled.agent)
    await labeled.dispose()
    return { registryParentSet: true, resourceOwnerStillRootCaller: true }
  })

  await check('caller scope alone does not invent a registry parentAgent relation', async ({ ctx }) => {
    const parent = await ctx.agents.create({ sessionId: id('scope-parent') })
    const child = await parent.agent.ctx.agents.create({ sessionId: id('scope-owned-root') })
    assert.equal(ctx.agents.roots().includes(child.agent), true)
    assert.equal(ctx.agents.isOwnedBy(child.agent.id, parent.agent), false)
    await parent.dispose()
    assert.equal(ctx.agents.get(child.agent.id), undefined)
    return { registryRoot: true, resourceFollowsCallerScope: true }
  })

  await check('owner comparison uses the exact Agent object rather than its id', async ({ ctx }) => {
    const parent = await ctx.agents.create({ sessionId: id('exact-parent') })
    const child = await parent.agent.ctx.agents.create({ sessionId: id('exact-child'), parentAgent: parent.agent })
    const sameIdOtherObject = { ...parent.agent }
    assert.equal(ctx.agents.isOwnedBy(child.agent.id, sameIdOtherObject), false)
    assert.equal(ctx.agents.isOwnedBy(child.agent.id, parent.agent), true)
    await parent.dispose()
    return { exactObjectRequired: true }
  })

  await check('initiator attribution and the Agent passed to setup describe different subjects', async ({ ctx }) => {
    const parent = await ctx.agents.create({ sessionId: id('initiator') })
    let observedParent = false, observedChild = false
    const child = await ctx.agents.withInitiator(parent.agent, () => parent.agent.ctx.agents.create({ sessionId: id('subject'), parentAgent: parent.agent, setup(_, subject) {
      observedParent = ctx.agents.currentInitiator() === parent.agent
      observedChild = subject !== parent.agent
    } }))
    assert.equal(observedParent, true); assert.equal(observedChild, true)
    assert.equal(ctx.agents.currentInitiator(), undefined)
    await child.dispose(); await parent.dispose()
    return { initiatorIsParent: observedParent, setupArgumentIsChild: observedChild }
  })

  await check('setup failure closes a supplied persistence handle before any append', async ({ ctx }) => {
    const state = memoryPersistence(ctx)
    await assert.rejects(ctx.agents.create({ sessionId: id('stored-failure'), setup() { throw new Error('stored setup failed') } }), /stored setup failed/)
    assert.equal(state.closes, 1); assert.equal(state.appended.length, 0)
    return { closes: state.closes, appended: state.appended.length }
  })

  await check('live registry entries remain until an asynchronous persistence close finishes', async ({ ctx, gate }) => {
    const began = gate(), release = gate(), state = memoryPersistence(ctx, { close: async () => { began.resolve(); await release.promise } })
    const handle = await ctx.agents.create({ sessionId: id('stored-close') })
    const disposal = observed(handle.dispose())
    await began.promise
    assert.equal(ctx.agents.get(handle.agent.id), handle.agent); assert.equal(ctx.sessions.get(handle.agent.id), handle.agent.session)
    release.resolve(); await disposal
    assert.equal(state.closes, 1); assert.equal(ctx.agents.get(handle.agent.id), undefined)
    return { registryRetainedUntilClose: true }
  })

  await check('persistence close rejection is shared and does not prevent detachment', async ({ ctx }) => {
    const failure = new Error('final close rejected'), state = memoryPersistence(ctx, { close: async () => { throw failure } })
    const handle = await ctx.agents.create({ sessionId: id('stored-close-failure') })
    const first = observed(handle.dispose()), second = observed(handle.dispose())
    await assert.rejects(first, error => error === failure)
    await assert.rejects(second, error => error === failure)
    assert.equal(state.closes, 1)
    assert.equal(ctx.agents.get(handle.agent.id), undefined); assert.equal(ctx.sessions.get(handle.agent.id), undefined)
    return { oneClose: true, sameFailure: true, detached: true }
  })

  await check('cancelled backend creation releases a handle that arrives late', async ({ ctx, gate }) => {
    const began = gate(), release = gate(), closed = gate(), controller = new AbortController()
    memoryPersistence(ctx, { provider: { async create(header, options) {
      began.resolve(); await release.promise
      return { header, inheritedEventCount: options.inheritedEventCount, async append() {}, async close() { closed.resolve() } }
    } } })
    const key = id('late-handle'), creating = observed(ctx.agents.create({ sessionId: key, signal: controller.signal }))
    await began.promise; controller.abort(new Error('backend creation cancelled'))
    await assert.rejects(creating, /backend creation cancelled/)
    assert.equal(ctx.sessions.get(key), undefined)
    release.resolve(); await closed.promise
    return { lateHandleClosed: true }
  })

  await check('concurrent same-id preparations cannot delete the winning lifecycle', async ({ ctx, gate }) => {
    const began = gate(), release = gate(), key = id('concurrent')
    const first = observed(ctx.agents.create({ sessionId: key, setup() { began.resolve(); return release.promise } }))
    await began.promise
    const winner = await ctx.agents.create({ sessionId: key })
    release.resolve(); await assert.rejects(first, /already exists|already registered/)
    assert.equal(ctx.agents.get(key), winner.agent); assert.equal(ctx.sessions.get(key), winner.agent.session)
    await winner.dispose()
    return { oneWinner: true, failedPreparationCannotDetachWinner: true }
  })

  await check('resume requires persistence and does not reuse the fresh-session path', async ({ ctx }) => {
    await assert.rejects(ctx.agents.resume({ resumeSessionId: id('resume-no-backend') }), /persistence is not configured/)
    return { backendRequired: true }
  })

  await check('session announcement failure only pairs the announcement that began', async ({ ctx }) => {
    const key = id('session-announce-fail'), trace = []
    ctx.on('session/created', () => { trace.push('session/created'); throw new Error('session observer failed') })
    ctx.on('agent/created', () => { trace.push('agent/created') })
    ctx.on('agent/disposed', () => { trace.push('agent/disposed') })
    ctx.on('session/disposed', () => { trace.push('session/disposed') })
    await assert.rejects(ctx.agents.create({ sessionId: key }), /session observer failed/)
    assert.deepEqual(trace, ['session/created', 'session/disposed'])
    assert.equal(ctx.agents.get(key), undefined); assert.equal(ctx.sessions.get(key), undefined)
    return trace
  })

  await check('real resume opens for write before read and preserves durable lineage without a live owner', async ({ ctx }) => {
    const key = id('resume-real'), historicalParent = id('historical-parent')
    const first = await ctx.agents.create({ sessionId: key, meta: { parentSession: historicalParent } })
    const header = structuredClone(first.agent.session.header)
    const events = structuredClone(first.agent.session.snapshotEvents(SessionLogOffset(0)))
    const inheritedEventCount = first.agent.session.inheritedEventCount
    await first.dispose()
    const trace = []
    ctx.provide('sessionPersistence', {
      async open(requested, mode) {
        assert.equal(requested, key); assert.equal(mode, 'write'); trace.push('open:write')
        return { header, inheritedEventCount,
          async read(start) { assert.equal(start, 0); trace.push('read'); return { events, eventState: 'detached' } },
          async append() { trace.push('append repair') },
          async close() { trace.push('close') },
        }
      },
    })
    ctx.on('agent/created', ({ source }) => { trace.push(source) })
    const resumed = await ctx.agents.resume({ resumeSessionId: key })
    assert.equal(resumed.agent.session.header.parentSession, historicalParent)
    assert.equal(ctx.agents.roots().includes(resumed.agent), true)
    assert.deepEqual(trace.slice(0, 2), ['open:write', 'read'])
    assert.equal(trace.includes('resume'), true)
    await resumed.dispose()
    assert.equal(trace.at(-1), 'close')
    return { trace, durableLineageRetained: true, runtimeRoot: true }
  })

  await check('owner disposal aborts a pending resume and closes its late write handle', async ({ ctx, gate }) => {
    const caller = await owner(ctx), began = gate(), release = gate(), closed = gate(), key = id('late-resume')
    let reads = 0
    ctx.provide('sessionPersistence', { async open() {
      began.resolve(); await release.promise
      return { async read() { reads++; throw new Error('abandoned read must not run') }, async close() { closed.resolve() } }
    } })
    const resuming = observed(caller.ctx.agents.resume({ resumeSessionId: key }))
    await began.promise
    await caller.fiber.dispose()
    await assert.rejects(resuming, /disposed|aborted/)
    release.resolve(); await closed.promise
    assert.equal(reads, 0); assert.equal(ctx.sessions.get(key), undefined)
    return { reads, lateWriteHandleClosed: true }
  })

  return results
}
