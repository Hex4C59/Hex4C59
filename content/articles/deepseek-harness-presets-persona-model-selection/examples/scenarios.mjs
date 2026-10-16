import assert from 'node:assert/strict'
import { pathToFileURL } from 'node:url'
import { join } from 'node:path'

export async function verifyPresets(m, work) {
  const { Context } = m.cordis
  const { SessionId } = m['dsh-session']
  const { createScope } = m['dsh-scope']
  const { assembleContextFor, agentEvents, installModelSelection } = m['dsh-agent']
  const { renderPrompt } = m['dsh-system-prompt']
  const { ApiSessionAgentController } = m['dsh-api-session-controller/agent']
  const { installModelSelectionProjection } = m['dsh-api-session-controller/model-selection-projection']
  const checks = []
  async function harness() {
    const ctx = new Context()
    ctx.baseUrl = pathToFileURL(join(work, 'package.json')).href
    for (const name of ['cordis-plugin-loader', 'dsh-llm', 'dsh-session', 'dsh-session-projection', 'dsh-tools', 'dsh-typert-registry']) await ctx.plugin(m[name].default)
    await ctx.plugin(m['dsh-system-prompt'].default, { personaPrefix: 'Deployment prefix.', personaSuffix: 'Deployment suffix.' })
    await ctx.plugin(m['dsh-agent'].default)
    await ctx.plugin(m['dsh-agent-loop'].default, { agents: [] })
    const builtins = ctx.loader.builtins
    builtins.group = m['cordis-plugin-group'].default
    builtins.preset = m['dsh-agent-preset'].default
    builtins.persona = m['dsh-persona']
    builtins.registry = m['dsh-agent-preset-registry'].default
    builtins.model = m['dsh-agent-default-model'].default
    builtins.contribute = { inject: ['tools', 'systemPrompt'], apply(child, config) {
      child.effect(() => child.tools.register({ name: config.tool, description: 'Synthetic test tool.', parameters: { type: 'object', properties: {} }, output: { schema: { type: 'string' }, render: (_args, value) => [{ type: 'text', text: String(value) }] }, execute: async () => config.tool }))
      child.effect(() => child.systemPrompt.section({ name: 'example:' + config.tool, order: 100, text: 'Guidance ' + config.tool }))
    } }
    builtins.globalService = { apply(child, config) { child.effect(() => child.provide('examplePresetService', { label: config.label })) } }
    builtins.needsService = { inject: ['exampleLateService'], apply() {} }
    builtins.throws = { apply() { throw new Error('synthetic row failure') } }
    async function live(name, config) {
      const id = await ctx.loader.create({ id: name, name: 'cordis:' + name, config })
      const entry = ctx.loader.resolve(id)
      await entry.fiber.await()
      return { entry, replace: async next => { await entry.update({ config: next }); await entry.fiber.await() } }
    }
    const registry = await live('registry', { default: 'standard' })
    const model = await live('model', { provider: 'route-a', model: 'model-a' })
    installModelSelectionProjection(ctx)
    const controller = new ApiSessionAgentController(ctx)
    async function declare(id, tool = id, extras = {}) {
      return ctx.plugin(m['dsh-agent-preset'].default, { id, plugins: [{ name: 'cordis:contribute', config: { tool } }], ...extras })
    }
    async function create(id, preset = 'standard') {
      const composition = await controller.composeAgent(preset)
      return ctx.agents.create({ sessionId: SessionId(id), meta: { agentPreset: composition.agentPreset }, setup: composition.setup })
    }
    return { ctx, registry, model, controller, declare, create }
  }
  async function check(name, action) {
    const h = await harness()
    try { const observation = await action(h); checks.push({ name, observation: observation ?? true }); console.log('PASS ' + name) }
    finally { await h.ctx.fiber.dispose() }
  }
  const tools = (ctx, agent) => ctx.tools.schemas(agent).map(row => row.name)
  const text = async (ctx, scope) => renderPrompt(await ctx.systemPrompt.assemble(scope === undefined ? {} : { scope }))
  const scopeKey = agent => assembleContextFor(agent).scope
  const header = (agent, config, adapterDefaults) => agent.session.append('request/header', { header: { config, ...(adapterDefaults === undefined ? {} : { adapterDefaults }) }, reason: 'initial' })

  await check('default preset, selected default and explicit identity are separate inputs', async ({ ctx, registry, declare }) => {
    await declare('standard'); await declare('minimal')
    assert.equal((await ctx.agentPresets.resolve()).id, 'standard')
    await registry.replace({ default: 'standard', selectedDefault: 'minimal' })
    assert.equal((await ctx.agentPresets.resolve()).id, 'minimal')
    assert.equal((await ctx.agentPresets.resolve('standard')).id, 'standard')
    assert.equal((await ctx.agentPresets.remoteExportList()).presets.find(p => p.id === 'minimal').isDefault, true)
    await assert.rejects(ctx.agentPresets.resolve(''), /Unknown agent preset/)
    return { deployment: 'standard', selected: 'minimal', explicit: 'standard' }
  })
  await check('one eagerly mounted revision serves multiple real Agents without leaking global tools', async ({ ctx, declare, create }) => {
    await declare('standard'); await declare('minimal')
    const a = await create('a'), b = await create('b'), c = await create('c', 'minimal')
    assert.deepEqual(tools(ctx, a.agent), ['standard']); assert.deepEqual(tools(ctx, b.agent), ['standard']); assert.deepEqual(tools(ctx, c.agent), ['minimal']); assert.deepEqual(ctx.tools.schemas(), [])
    assert.equal(ctx.agentPresets.inspectCompositions().length, 2)
    return { a: tools(ctx, a.agent), b: tools(ctx, b.agent), c: tools(ctx, c.agent), global: [] }
  })
  await check('declaration rejects duplicate and blank ids without replacing the healthy definition', async ({ ctx, declare }) => {
    await declare('standard')
    await assert.rejects(declare('standard'), /Duplicate agent preset/)
    await assert.rejects(declare('   '), /must not be empty/)
    assert.equal((await ctx.agentPresets.resolve()).id, 'standard')
    assert.match(m['dsh-agent-preset-registry'].entryListProblem([{ name: 'cordis:group', group: true, config: [{}] }]), /names no plugin/)
  })
  await check('broken rows remain in the roster and mount fails while another preset is usable', async ({ ctx, declare, create }) => {
    await declare('broken', 'unused', { plugins: [{ name: 'cordis:throws' }] }); await declare('standard')
    assert.match((await ctx.agentPresets.resolve('broken')).broken, /synthetic row failure/)
    await assert.rejects(create('bad', 'broken'), /synthetic row failure/)
    assert.equal(ctx.agents.get(SessionId('bad')), undefined)
    assert.deepEqual(tools(ctx, (await create('good')).agent), ['standard'])
  })
  await check('pending dependency is re-audited after a host provider appears', async ({ ctx, declare }) => {
    await declare('standard', 'unused', { plugins: [{ name: 'cordis:needsService' }] })
    assert.match((await ctx.agentPresets.resolve()).broken, /waiting for exampleLateService/)
    const release = ctx.provide('exampleLateService', {})
    assert.equal((await ctx.agentPresets.resolve()).broken, undefined)
    release()
  })
  await check('root service leak is rejected and an isolated group supplies a scoped service', async ({ ctx, declare, create }) => {
    await declare('leak', 'unused', { plugins: [{ name: 'cordis:globalService', config: { label: 'leak' } }] })
    assert.match((await ctx.agentPresets.resolve('leak')).broken, /isolate realms/)
    await declare('standard', 'unused', { plugins: [{ name: 'cordis:group', group: true, isolate: { examplePresetService: true }, config: [{ name: 'cordis:globalService', config: { label: 'isolated' } }] }] })
    const h = await create('isolated')
    assert.equal(ctx.get('examplePresetService'), undefined)
    assert.equal(ctx.agentPresets.serviceFor(h.agent, 'examplePresetService').label, 'isolated')
  })
  await check('disabled broken rows are intentional exclusions', async ({ ctx, declare, create }) => {
    await declare('standard', 'unused', { plugins: [{ name: 'cordis:missing', disabled: true }, { name: 'cordis:contribute', config: { tool: 'enabled' } }] })
    assert.equal((await ctx.agentPresets.resolve()).broken, undefined)
    assert.deepEqual(tools(ctx, (await create('disabled')).agent), ['enabled'])
  })
  await check('existing Agents and inherited children retain an old revision until the last user leaves', async ({ ctx, declare, create }) => {
    const old = await declare('standard', 'old-tool')
    const first = await create('old-agent')
    await old.dispose(); await declare('standard', 'new-tool')
    const fresh = await create('fresh-agent')
    const child = createScope(ctx, {})
    assert.equal(ctx.agentPresets.composeFrom(child.ctx, first.agent.ctx), 'standard')
    assert.deepEqual(ctx.tools.schemas(m['dsh-scope'].scopeOf(child.ctx)).map(t => t.name), ['old-tool'])
    assert.deepEqual(tools(ctx, first.agent), ['old-tool']); assert.deepEqual(tools(ctx, fresh.agent), ['new-tool'])
    assert.equal(ctx.agentPresets.inspectCompositions().length, 2)
    await first.dispose(); assert.equal(ctx.agentPresets.inspectCompositions().length, 2)
    await child.dispose(); assert.equal(ctx.agentPresets.inspectCompositions().length, 1)
    return { retained: 'old-tool', fresh: 'new-tool', afterLastUser: 1 }
  })
  await check('unregistering a definition removes future resolution without revoking its live Agent', async ({ ctx, declare, create }) => {
    const declaration = await declare('standard'); const h = await create('retained')
    await declaration.dispose()
    await assert.rejects(ctx.agentPresets.resolve(), /Unknown agent preset/)
    assert.deepEqual(tools(ctx, h.agent), ['standard'])
    await h.dispose(); assert.equal(ctx.agentPresets.inspectCompositions().length, 0)
  })
  await check('read lease retains a retired revision and repeated disposal releases once', async ({ ctx, declare }) => {
    const declaration = await declare('standard')
    const lease = await ctx.agentPresets.acquireScope()
    await declaration.dispose(); assert.equal(ctx.agentPresets.inspectCompositions().length, 1)
    await lease[Symbol.asyncDispose](); await lease[Symbol.asyncDispose]()
    assert.equal(ctx.agentPresets.inspectCompositions().length, 0)
  })
  await check('blank-session selection records its new preset without rewriting the creation header', async ({ ctx, declare, create }) => {
    await declare('standard'); await declare('minimal'); const h = await create('blank')
    const seen = []; ctx.on('agent-preset/selected', (id, preset) => seen.push([id, preset]))
    await ctx.agentPresets.select(h.agent, 'minimal')
    assert.equal(h.agent.session.header.agentPreset, 'standard')
    assert.equal(ctx.sessionProjections.stateOf(h.agent.session, 'agentPreset'), 'minimal')
    assert.deepEqual(tools(ctx, h.agent), ['minimal']); assert.deepEqual(seen, [['blank', 'minimal']])
    return { header: 'standard', projection: 'minimal', tools: ['minimal'] }
  })
  await check('started turn locks preset changes', async ({ ctx, declare, create }) => {
    await declare('standard'); await declare('minimal'); const h = await create('started')
    h.agent.session.append('turn/start', { turn: 1 })
    await assert.rejects(ctx.agentPresets.select(h.agent, 'minimal'), /already started/)
    assert.deepEqual(tools(ctx, h.agent), ['standard'])
  })
  await check('failed preset selection does not poison a subsequent queued selection', async ({ ctx, declare, create }) => {
    await declare('standard'); await declare('minimal'); const h = await create('queue')
    const failed = assert.rejects(ctx.agentPresets.select(h.agent, 'missing'), /Unknown agent preset/)
    const next = ctx.agentPresets.select(h.agent, 'minimal')
    await failed; assert.equal(await next, 'minimal')
  })
  await check('low-level recompose does not enforce blank-session policy or append selection events', async ({ ctx, declare, create }) => {
    await declare('standard'); await declare('minimal'); const h = await create('low-level')
    h.agent.session.append('turn/start', { turn: 1 })
    await ctx.agentPresets.recompose(h.agent.ctx, 'minimal')
    assert.deepEqual(tools(ctx, h.agent), ['minimal'])
    assert.equal(ctx.sessionProjections.stateOf(h.agent.session, 'agentPreset'), 'standard')
  })
  await check('Persona shadows only its Agent scope and leaves the deployment unchanged', async ({ ctx, declare, create }) => {
    await declare('standard', 'unused', { plugins: [{ name: 'cordis:persona', config: { prefix: 'Preset prefix.', suffix: 'Preset suffix.' } }] })
    const h = await create('persona')
    assert.match(await text(ctx, scopeKey(h.agent)), /Preset prefix/)
    assert.doesNotMatch(await text(ctx, scopeKey(h.agent)), /Deployment prefix/)
    assert.match(await text(ctx), /Deployment prefix/)
  })
  await check('empty Persona slots remove deployment prose and unloading restores it', async ({ ctx }) => {
    const scope = createScope(ctx, {})
    const persona = await scope.ctx.plugin(m['dsh-persona'], { prefix: '' })
    const empty = await text(ctx, m['dsh-scope'].scopeOf(scope.ctx))
    assert.doesNotMatch(empty, /Deployment prefix|Deployment suffix/)
    await persona.dispose()
    assert.match(await text(ctx, m['dsh-scope'].scopeOf(scope.ctx)), /Deployment prefix/)
    await scope.dispose()
  })
  await check('Persona cannot replace the global registration', async ({ ctx }) => {
    await assert.rejects(async () => await ctx.plugin(m['dsh-persona'], { prefix: 'wrong realm' }), /already registered/)
  })
  await check('Persona interpolation is strict about unknown and malformed names', async ({ ctx }) => {
    const a = createScope(ctx, {}), b = createScope(ctx, {}), c = createScope(ctx, {})
    await a.ctx.plugin(m['dsh-persona'], { prefix: '{{missing}}' })
    await b.ctx.plugin(m['dsh-persona'], { prefix: '{{bad.name}}' })
    ctx.systemPrompt.variable('empty_value', () => undefined)
    await c.ctx.plugin(m['dsh-persona'], { prefix: '{{empty_value}}' })
    await assert.rejects(text(ctx, m['dsh-scope'].scopeOf(a.ctx)), /unknown prompt variable/)
    await assert.rejects(text(ctx, m['dsh-scope'].scopeOf(b.ctx)), /malformed prompt variable/)
    await assert.rejects(text(ctx, m['dsh-scope'].scopeOf(c.ctx)), /has no value/)
    await Promise.all([a.dispose(), b.dispose(), c.dispose()])
  })
  await check('complete Persona replaces sections while keeping tools and required context', async ({ ctx, declare, create }) => {
    ctx.systemPrompt.context({ name: 'required', order: 0, text: 'Required runtime.', required: true })
    ctx.systemPrompt.context({ name: 'optional', order: 1, text: 'Optional runtime.' })
    await declare('standard', 'unused', { plugins: [{ name: 'cordis:contribute', config: { tool: 'still-available' } }, { name: 'cordis:persona', config: { prefix: 'Complete identity.', suffix: 'Suppressed suffix.', complete: true, includeRuntimeContext: false } }] })
    const h = await create('complete'), a = await ctx.systemPrompt.assemble(assembleContextFor(h.agent))
    assert.equal(renderPrompt(a), 'Complete identity.')
    assert.deepEqual(a.tools.map(t => t.name), ['still-available'])
    assert.deepEqual(a.contexts.map(t => t.name), ['required'])
    return { sections: a.sections.map(s => s.name), tools: a.tools.map(t => t.name), context: a.contexts.map(c => c.name) }
  })
  await check('model defaults remain live and currentSelection returns a detached object', async ({ ctx, model }) => {
    const before = ctx.agentDefaultModel.currentSelection(); before.model = 'mutated'
    assert.equal(ctx.agentDefaultModel.currentSelection().model, 'model-a')
    await model.replace({ provider: 'route-b', model: 'model-b', reasoningEffort: 'high' })
    assert.deepEqual(ctx.agentDefaultModel.currentSelection(), { provider: 'route-b', model: 'model-b', reasoningEffort: 'high' })
    await model.replace({ provider: 'route-c', model: 'model-c' })
    assert.equal(ctx.agentDefaultModel.currentSelection().reasoningEffort, undefined)
  })
  await check('saving without a config editor does not mutate the defaults', async ({ ctx }) => {
    await ctx.agentDefaultModel.saveSelection({ provider: 'ignored', model: 'ignored' })
    assert.deepEqual(ctx.agentDefaultModel.currentSelection(), { provider: 'route-a', model: 'model-a' })
  })
  await check('default saves capture full values, serialize writes and continue after rejection', async ({ ctx }) => {
    const entered = Promise.withResolvers(), release = Promise.withResolvers(); const calls = []
    ctx.provide('configEditor', { async edit(_entry, change) { const value = change(); calls.push(value); if (calls.length === 1) { entered.resolve(); await release.promise; throw new Error('synthetic write failure') } } })
    const failed = assert.rejects(ctx.agentDefaultModel.saveSelection({ provider: 'first', model: 'first' }), /synthetic write failure/)
    const last = { provider: 'last', model: 'captured' }; const saved = ctx.agentDefaultModel.saveSelection(last); last.model = 'mutated'
    await entered.promise; assert.equal(calls.length, 1); release.resolve(); await failed; await saved
    assert.deepEqual(calls, [{ provider: 'first', model: 'first' }, { provider: 'last', model: 'captured' }])
  })
  await check('unstarted API Agent follows current defaults while a logged request keeps its route', async ({ ctx, model, controller, declare, create }) => {
    await declare('standard'); const a = await create('unstarted'), b = await create('with-history')
    const sa = controller.selectionFor(a.agent), sb = controller.selectionFor(b.agent)
    header(b.agent, { provider: 'old-route', model: 'old-model' })
    await model.replace({ provider: 'new-default', model: 'new-model' })
    assert.equal(sa.current.model, 'new-model'); assert.equal(sb.current.model, 'old-model')
    return { unstarted: sa.current, withRequestHeader: sb.current }
  })
  await check('pending model choice wins over request history and is stored in the Session projection', async ({ ctx, controller, declare, create }) => {
    await declare('standard'); const h = await create('pending')
    header(h.agent, { provider: 'old-route', model: 'old-model' })
    controller.selectForNextRequest(h.agent, { provider: 'picked', model: 'picked-model' })
    assert.equal(controller.selectionFor(h.agent).current.model, 'picked-model')
    assert.equal(ctx.sessionProjections.stateOf(h.agent.session, 'modelSelection').pending.model, 'picked-model')
    // Read the real projection maintained from committed Session events.
    const state = ctx.sessionProjections.stateOf(h.agent.session, 'modelSelection')
    assert.equal(state.lastUsed.model, 'old-model'); assert.equal(state.pending.model, 'picked-model')
  })
  await check('pending model is retired only by a matching request and matching consumption', async ({ ctx, controller, declare, create }) => {
    await declare('standard'); const h = await create('consume'), pick = { provider: 'p', model: 'm' }
    controller.selectForNextRequest(h.agent, pick)
    header(h.agent, { provider: 'different', model: 'm' })
    assert.notEqual(ctx.sessionProjections.stateOf(h.agent.session, 'modelSelection').pending, null)
    assert.equal(controller.consumeSelection(h.agent, 'different', 'm', undefined), false)
    header(h.agent, pick); assert.equal(ctx.sessionProjections.stateOf(h.agent.session, 'modelSelection').pending, null)
    assert.equal(controller.consumeSelection(h.agent, 'p', 'm', undefined), true)
    assert.deepEqual(controller.selectionFor(h.agent).current, pick)
  })
  await check('an adapter-defaulted effort is not restored as an explicit conversation choice', async ({ controller, declare, create }) => {
    await declare('standard'); const h = await create('adapter-default')
    header(h.agent, { provider: 'p', model: 'm', reasoningEffort: 'high' }, { reasoningEffort: true })
    assert.deepEqual(controller.selectionFor(h.agent).current, { provider: 'p', model: 'm' })
  })
  await check('prompt assembly snapshots routing so a concurrent switch waits for the next assembly', async ({ ctx, controller, declare, create }) => {
    await declare('standard'); const h = await create('snapshot'), selected = controller.selectionFor(h.agent)
    selected.current = { provider: 'p-a', model: 'm-a', reasoningEffort: 'high' }
    const assembly = await ctx.systemPrompt.assemble(assembleContextFor(h.agent))
    selected.current = { provider: 'p-b', model: 'm-b' }
    const config = await agentEvents(h.agent.ctx, h.agent).waterfall('agent/request', { turn: 1, step: 1, signal: new AbortController().signal }, async () => ({ provider: 'base', model: 'base', reasoningEffort: 'low', temperature: .2 }))
    assert.equal(assembly.variables.model, 'm-a'); assert.equal(config.model, 'm-a'); assert.equal(config.reasoningEffort, 'high')
    const next = await ctx.systemPrompt.assemble(assembleContextFor(h.agent)); assert.equal(next.variables.model, 'm-b')
    const nextConfig = await agentEvents(h.agent.ctx, h.agent).waterfall('agent/request', { turn: 1, step: 2, signal: new AbortController().signal }, async () => ({ reasoningEffort: 'inherited', temperature: .2 }))
    assert.equal(nextConfig.model, 'm-b'); assert.equal(nextConfig.reasoningEffort, undefined); assert.equal(nextConfig.temperature, .2)
    return { assembly: assembly.variables.model, request: config.model, nextAssembly: next.variables.model }
  })
  await check('route changes add one model notice while effort-only changes do not', async ({ ctx, controller, declare, create }) => {
    await declare('standard'); const h = await create('notice'), selected = controller.selectionFor(h.agent)
    header(h.agent, { provider: 'p', model: 'old' }); selected.current = { provider: 'p', model: 'new' }
    const input = m['dsh-llm'].createUserMessage({ content: [{ type: 'text', text: 'hello' }] })
    const pre = async () => agentEvents(h.agent.ctx, h.agent).waterfall('agent/pre-step', { turn: 1, step: 1, messages: [input], signal: new AbortController().signal }, async () => ({ kind: 'enter', messages: [input] }))
    await ctx.systemPrompt.assemble(assembleContextFor(h.agent))
    const changed = await pre(); assert.equal(changed.messages.length, 2); assert.equal(changed.messages[1].source.kind, 'model-selection')
    header(h.agent, { provider: 'p', model: 'new' }); selected.current = { provider: 'p', model: 'new', reasoningEffort: 'high' }
    await ctx.systemPrompt.assemble(assembleContextFor(h.agent)); assert.equal((await pre()).messages.length, 1)
  })
  await check('changing preset does not replace the Session model selection', async ({ ctx, controller, declare, create }) => {
    await declare('standard'); await declare('minimal'); const h = await create('independent')
    controller.selectForNextRequest(h.agent, { provider: 'explicit', model: 'kept' })
    await ctx.agentPresets.select(h.agent, 'minimal')
    assert.equal(controller.selectionFor(h.agent).current.model, 'kept'); assert.deepEqual(tools(ctx, h.agent), ['minimal'])
  })
  await check('bare AgentRegistry creation does not automatically compose a preset', async ({ ctx, declare }) => {
    await declare('standard')
    const h = await ctx.agents.create({ sessionId: SessionId('bare'), agentOptions: { provider: 'direct', model: 'direct-model' } })
    assert.equal(ctx.agentPresets.composedPreset(h.agent.ctx), undefined)
    assert.deepEqual(tools(ctx, h.agent), [])
    assert.equal(h.agent.options.model, 'direct-model')
  })
  return checks
}
