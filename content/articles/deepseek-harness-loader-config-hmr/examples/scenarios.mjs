import assert from 'node:assert/strict'
import { readFile, writeFile } from 'node:fs/promises'
import { join } from 'node:path'
import { pathToFileURL } from 'node:url'

const deferred = () => Promise.withResolvers()
const expr = source => ({ __jsExpr: source })

export async function verifyLoader({ Context, FiberState }, { default: Loader, Group }, z, { default: Include, applyEntryPatches }, work) {
  const results = []
  let serial = 0
  async function check(name, body) {
    const ctx = new Context()
    ctx.baseUrl = pathToFileURL(work).href + '/'
    try {
      await ctx.plugin(Loader)
      ctx.loader.builtins.group = Group
      ctx.loader.builtins.include = Include
      results.push({ name, observation: await body(ctx) })
      console.log(`PASS ${name}`)
    } finally { await ctx.fiber.dispose() }
  }
  async function mount(ctx, plugin, config = {}, extra = {}) {
    const key = `lab${++serial}`
    ctx.loader.builtins[key] = plugin
    const id = await ctx.loader.create({ id: key, name: `cordis:${key}`, config, ...extra })
    await ctx.loader.await()
    return ctx.loader.resolve(id)
  }
  async function update(entry, config) { await entry.update({ config }); await entry.fiber?.await() }
  function ordinary(trace, Config) {
    return { Config, apply(owner, config) {
      trace.push(['apply', config.value])
      owner.effect(() => () => { trace.push(['dispose', config.value]) })
    } }
  }
  const liveSchema = () => z.object({ fixed: z.string().default('A'), live: z.string().default('one').volatile(), count: z.natural().default(1).volatile() })

  await check('raw expressions survive while plugin receives evaluated values', async ctx => {
    ctx.provide('labInput', 3)
    const raw = { value: expr('ctx.get("labInput") * 2'), list: [expr('1 + 2')], literal: '${1 + 2}' }
    let parsed
    const entry = await mount(ctx, (_, config) => { parsed = config }, raw)
    assert.equal(entry.options.config, raw)
    assert.deepEqual(parsed, { value: 6, list: [3], literal: '${1 + 2}' })
    return { raw: raw.value, parsed: parsed.value, literal: parsed.literal }
  })

  await check('group carries expressions until the child dependency is available', async ctx => {
    let calls = 0, value
    ctx.provide('labRead', () => { calls++; return 'child' })
    ctx.loader.builtins.leaf = { inject: ['labGate'], apply(_, config) { value = config.value } }
    const group = await mount(ctx, Group, [{ id: 'leaf', name: 'cordis:leaf', config: { value: expr('ctx.get("labRead")()') } }], { group: true })
    const child = ctx.loader.resolve('leaf')
    assert.equal(calls, 0)
    assert.equal(child.fiber.state, FiberState.PENDING)
    ctx.provide('labGate', {})
    await child.fiber.await()
    assert.equal(calls, 1)
    assert.equal(value, 'child')
    assert.equal(group.options.config[0].config.value.__jsExpr, 'ctx.get("labRead")()')
    return { beforeDependency: 0, afterDependency: calls, value }
  })

  await check('unchanged entry options skip ordinary restart', async ctx => {
    const trace = [], entry = await mount(ctx, ordinary(trace), { value: 'A' })
    const fiber = entry.fiber
    await update(entry, { value: 'A' })
    assert.equal(entry.fiber, fiber)
    assert.deepEqual(trace, [['apply', 'A']])
    return trace
  })

  await check('ordinary config change restarts the same fiber after cleanup', async ctx => {
    const trace = [], entry = await mount(ctx, ordinary(trace), { value: 'A' })
    const fiber = entry.fiber, uid = fiber.uid
    await update(entry, { value: 'B' })
    assert.equal(entry.fiber, fiber)
    assert.equal(fiber.uid, uid)
    assert.deepEqual(trace, [['apply', 'A'], ['dispose', 'A'], ['apply', 'B']])
    return trace
  })

  await check('internal update can consume the change without next', async ctx => {
    let mounts = 0, accepted
    const entry = await mount(ctx, { apply(owner) {
      mounts++
      owner.on('internal/update', config => { accepted = config.value })
    } }, { value: 'A' })
    const parsed = entry.fiber.config
    await update(entry, { value: 'B' })
    assert.equal(mounts, 1)
    assert.equal(accepted, 'B')
    assert.equal(entry.fiber.config, parsed)
    assert.equal(entry.options.config.value, 'B')
    return { mounts, accepted, parsedStill: parsed.value }
  })

  await check('fiber update is not an asynchronous completion barrier', async ctx => {
    const began = deferred(), release = deferred(), trace = []
    const entry = await mount(ctx, { apply(owner, config) {
      trace.push(config.value)
      owner.effect(() => async () => { began.resolve(); await release.promise })
    } }, { value: 'A' })
    const result = entry.fiber.update({ value: 'B' }, true)
    assert.equal(result, undefined)
    await began.promise
    assert.deepEqual(trace, ['A'])
    release.resolve()
    await entry.fiber.await()
    assert.deepEqual(trace, ['A', 'B'])
    return { returned: 'undefined', afterAwait: trace }
  })

  await check('volatile fields keep references and commit before the owner event', async ctx => {
    let mounts = 0, stops = 0, config
    const events = []
    const plugin = { Config: liveSchema(), apply(owner, value) {
      mounts++; config ??= value
      owner.effect(() => () => { stops++ })
      owner.on('loader/volatile-update', paths => events.push({ paths, live: value.live.get(), count: value.count.get() }))
    } }
    const entry = await mount(ctx, plugin)
    const sibling = await mount(ctx, plugin)
    const reference = config.live
    await update(entry, { live: 'two', count: 2 })
    assert.equal(entry.fiber.config, config)
    assert.equal(config.live, reference)
    assert.equal(mounts, 2)
    assert.equal(stops, 0)
    assert.equal(sibling.fiber.config.live.get(), 'one')
    assert.deepEqual(events, [{ paths: [['live'], ['count']], live: 'two', count: 2 }])
    return { mounts, stops, events }
  })

  await check('invalid volatile candidate retains raw input and last running value', async ctx => {
    const entry = await mount(ctx, { Config: liveSchema(), apply() {} })
    const old = entry.fiber.config
    await update(entry, { live: 42 })
    assert.equal(entry.options.config.live, 42)
    assert.equal(entry.fiber._config.live, 42)
    assert.equal(entry.fiber.config, old)
    assert.equal(old.live.get(), 'one')
    assert.equal(entry.fiber.state, FiberState.ACTIVE)
    return { raw: 42, running: old.live.get(), active: true }
  })

  await check('mixed config takes ordinary restart and replaces parsed references', async ctx => {
    let mounts = 0, stops = 0
    const entry = await mount(ctx, { Config: liveSchema(), apply(owner) { mounts++; owner.effect(() => () => { stops++ }) } })
    const old = entry.fiber.config
    await update(entry, { fixed: 'B', live: 'two' })
    assert.equal(mounts, 2); assert.equal(stops, 1)
    assert.notEqual(entry.fiber.config, old)
    assert.equal(old.live.get(), 'one')
    assert.equal(entry.fiber.config.live.get(), 'two')
    return { mounts, stops, old: old.live.get(), current: entry.fiber.config.live.get() }
  })

  await check('ordinary effective expression change defeats the volatile fast path', async ctx => {
    let mounts = 0
    const release = ctx.provide('labFixed', 'A')
    const fixed = expr('ctx.get("labFixed")')
    const entry = await mount(ctx, { Config: liveSchema(), apply() { mounts++ } }, { fixed, live: 'one' })
    release(); ctx.provide('labFixed', 'B')
    await update(entry, { fixed, live: 'two' })
    assert.equal(mounts, 2)
    assert.equal(entry.fiber.config.fixed, 'B')
    return { mounts, effectiveFixed: 'B' }
  })

  await check('equivalent ordinary object defaults do not force a remount', async ctx => {
    let mounts = 0
    const Config = z.object({ fixed: z.object({ title: z.string().default('A') }).default({ title: 'A' }), live: z.string().volatile() })
    const entry = await mount(ctx, { Config, apply() { mounts++ } }, { live: 'one' })
    await update(entry, { fixed: { title: 'A' }, live: 'two' })
    assert.equal(mounts, 1)
    assert.equal(entry.fiber.config.live.get(), 'two')
    return { mounts }
  })

  await check('pending entries defer validation and use the latest raw config', async ctx => {
    let mounts = 0, value
    const entry = await mount(ctx, { inject: ['labGate'], Config: liveSchema(), apply(_, config) { mounts++; value = config.live.get() } })
    assert.equal(entry.fiber.state, FiberState.PENDING)
    await update(entry, { live: 'two' })
    assert.equal(mounts, 0)
    ctx.provide('labGate', {})
    await entry.fiber.await()
    assert.equal(mounts, 1); assert.equal(value, 'two')
    return { mounts, value }
  })

  await check('disabled expression stops an entry and enabling imports it again', async ctx => {
    const trace = [], entry = await mount(ctx, ordinary(trace), { value: 'A' })
    const old = entry.fiber
    await entry.update({ disabled: expr('true') }); await old.await()
    assert.equal(old.uid, null)
    assert.equal(entry.options.disabled.__jsExpr, 'true')
    await entry.update({ disabled: false }); await ctx.loader.await()
    assert.notEqual(entry.fiber, old)
    assert.deepEqual(trace, [['apply', 'A'], ['dispose', 'A'], ['apply', 'A']])
    return trace
  })

  await check('disabled group stays active while its descendants stop', async ctx => {
    let mounts = 0
    ctx.loader.builtins.leaf = () => { mounts++ }
    const group = await mount(ctx, Group, [{ id: 'leaf', name: 'cordis:leaf' }], { group: true, disabled: true })
    assert.equal(group.disabled, false)
    assert.equal(group.fiber.state, FiberState.ACTIVE)
    assert.equal(ctx.loader.resolve('leaf').disabled, true)
    assert.equal(ctx.loader.resolve('leaf').fiber, undefined)
    assert.equal(mounts, 0)
    return { group: 'ACTIVE', child: 'disabled', mounts }
  })

  await check('same-label service domains connect provider and consumer', async ctx => {
    const provider = await mount(ctx, owner => { owner.provide('labService', { id: 'blue' }) }, {}, { isolate: { labService: 'blue' } })
    let seen
    const consumer = await mount(ctx, { inject: ['labService'], apply(owner) { seen = owner.labService.id } }, {}, { isolate: { labService: 'blue' } })
    assert.equal(seen, 'blue')
    assert.equal(consumer.ctx[Context.isolate].labService, provider.ctx[Context.isolate].labService)
    assert.equal(ctx.get('labService'), undefined)
    return { seen, rootSeesService: false }
  })

  await check('true isolation creates distinct entry-local service symbols', async ctx => {
    const a = await mount(ctx, owner => { owner.provide('labService', { id: 'A' }) }, {}, { isolate: { labService: true } })
    const b = await mount(ctx, owner => { owner.provide('labService', { id: 'B' }) }, {}, { isolate: { labService: true } })
    assert.notEqual(a.ctx[Context.isolate].labService, b.ctx[Context.isolate].labService)
    assert.equal(a.ctx.get('labService').id, 'A'); assert.equal(b.ctx.get('labService').id, 'B')
    return { first: 'A', second: 'B', separateSymbols: true }
  })

  await check('moving an entry changes context and resumes a previously pending consumer', async ctx => {
    ctx.loader.builtins.provider = owner => { owner.provide('labService', { id: 'group-blue' }) }
    const group = await mount(ctx, Group, [{ id: 'provider', name: 'cordis:provider' }], { group: true, isolate: { labService: 'blue' } })
    let seen
    const consumer = await mount(ctx, { inject: ['labService'], apply(owner) { seen = owner.labService.id } })
    assert.equal(consumer.fiber.state, FiberState.PENDING)
    await ctx.loader.update(consumer.id, {}, group.id)
    await ctx.loader.await()
    assert.equal(seen, 'group-blue')
    assert.equal(Object.getPrototypeOf(consumer.ctx), group.subgroup.ctx)
    return { before: 'PENDING', after: seen }
  })

  await check('intercept options live on the entry context map', async ctx => {
    const entry = await mount(ctx, () => {}, {}, { intercept: { labService: { mode: 'strict' } } })
    assert.deepEqual(entry.ctx[Context.intercept].labService, { mode: 'strict' })
    await entry.update({ intercept: { labService: { mode: 'soft' } } })
    assert.deepEqual(entry.ctx[Context.intercept].labService, { mode: 'soft' })
    return { mode: 'soft' }
  })

  await check('remove leaves the store before asynchronous cleanup is complete', async ctx => {
    const began = deferred(), release = deferred(), done = deferred()
    const entry = await mount(ctx, owner => { owner.effect(() => async () => { began.resolve(); await release.promise; done.resolve() }) })
    const fiber = entry.fiber
    ctx.loader.remove(entry.id)
    await began.promise
    assert.throws(() => ctx.loader.resolve(entry.id), /cannot resolve/)
    let completed = false
    done.promise.then(() => { completed = true })
    await ctx.loader.await()
    assert.equal(completed, false)
    release.resolve(); await fiber.await()
    assert.equal(completed, true)
    return { afterLoaderAwait: false, afterSavedFiberAwait: true }
  })

  await check('changing an active entry name alone does not import a replacement', async ctx => {
    const trace = [], entry = await mount(ctx, () => { trace.push('old') })
    ctx.loader.builtins.replacement = () => { trace.push('new') }
    const fiber = entry.fiber
    await entry.update({ name: 'cordis:replacement' }); await ctx.loader.await()
    assert.equal(entry.fiber, fiber)
    assert.deepEqual(trace, ['old'])
    return { rawName: entry.options.name, trace }
  })

  await check('include parses expressions in the child fiber and exposes subtree ids', async ctx => {
    const filename = join(work, `config-${++serial}.yml`)
    let value
    ctx.loader.builtins.leaf = (_, config) => { value = config.value }
    await writeFile(filename, '- id: leaf\n  name: cordis:leaf\n  config:\n    value: !!js "1 + 2"\n')
    const entry = await mount(ctx, Include, { path: filename })
    const child = ctx.loader.resolve(`${entry.id}:leaf`)
    assert.equal(value, 3)
    assert.equal(child.options.config.value.__jsExpr, '1 + 2')
    assert.equal(child.id, `${entry.id}:leaf`)
    return { value, nestedId: child.id }
  })

  await check('invalid include refresh keeps the last good tree and can recover', async ctx => {
    const filename = join(work, `config-${++serial}.json`), trace = []
    ctx.loader.builtins.leaf = ordinary(trace)
    const raw = value => JSON.stringify([{ id: 'leaf', name: 'cordis:leaf', config: { value } }])
    await writeFile(filename, raw('A'))
    const entry = await mount(ctx, Include, { path: filename })
    const include = entry.subtree, child = ctx.loader.resolve(`${entry.id}:leaf`), old = child.fiber
    await writeFile(filename, '{}'); await include.refresh()
    assert.equal(child.fiber, old); assert.deepEqual(trace, [['apply', 'A']])
    await writeFile(filename, raw('A')); await include.refresh()
    assert.deepEqual(trace, [['apply', 'A']])
    await writeFile(filename, raw('B')); await include.refresh(); await ctx.loader.await()
    assert.deepEqual(trace, [['apply', 'A'], ['dispose', 'A'], ['apply', 'B']])
    return trace
  })

  await check('include patches update children without remounting the include fiber', async ctx => {
    const filename = join(work, `config-${++serial}.json`), trace = []
    ctx.loader.builtins.leaf = ordinary(trace)
    await writeFile(filename, JSON.stringify([{ id: 'leaf', name: 'cordis:leaf', config: { value: 'A' } }]))
    const entry = await mount(ctx, Include, { path: filename })
    const fiber = entry.fiber, tree = entry.subtree
    await update(entry, { path: filename, patches: [{ id: 'leaf', config: { value: 'B' } }] })
    await ctx.loader.await()
    assert.equal(entry.fiber, fiber); assert.equal(entry.subtree, tree)
    assert.deepEqual(trace, [['apply', 'A'], ['dispose', 'A'], ['apply', 'B']])
    return trace
  })

  await check('patch input stays detached and later patches can target inserted rows', async () => {
    const input = [{ id: 'leaf', name: 'cordis:leaf', config: { value: 'A' } }]
    const before = JSON.stringify(input), warnings = []
    const output = applyEntryPatches(input, [
      { insert: [{ id: 'added', name: 'cordis:leaf', config: { value: 'B' } }] },
      { id: 'added', config: { value: 'C' } },
    ], message => warnings.push(message))
    assert.equal(JSON.stringify(input), before)
    assert.equal(output.find(row => row.id === 'added').config.value, 'C')
    assert.deepEqual(warnings, [])
    return { original: input[0].config.value, inserted: 'C', warnings: 0 }
  })

  await check('entry update retains expression nodes for YAML write-back', async ctx => {
    const filename = join(work, `config-${++serial}.yml`)
    ctx.loader.builtins.leaf = () => {}
    await writeFile(filename, '- id: leaf\n  name: cordis:leaf\n  config:\n    value: !!js "1 + 2"\n')
    const entry = await mount(ctx, Include, { path: filename })
    const child = ctx.loader.resolve(`${entry.id}:leaf`)
    await ctx.loader.update(child.id, { config: { value: expr('2 + 3') } })
    await child.fiber.await()
    // Include's own teardown flushes the scheduled file write before stopping children.
    await entry.fiber.dispose()
    const saved = await readFile(filename, 'utf8')
    assert.match(saved, /!!js/); assert.match(saved, /2 \+ 3/)
    return { expressionTagPreserved: true }
  })
  await check('programmatic fiber update saves its resolved config rather than the raw expression', async ctx => {
    const filename = join(work, `config-${++serial}.yml`)
    ctx.loader.builtins.leaf = () => {}
    await writeFile(filename, '- id: leaf\n  name: cordis:leaf\n  config:\n    value: !!js "1 + 2"\n')
    const entry = await mount(ctx, Include, { path: filename })
    const child = ctx.loader.resolve(`${entry.id}:leaf`)
    child.fiber.update({ value: expr('2 + 3') })
    await child.fiber.await()
    await entry.fiber.dispose()
    const saved = await readFile(filename, 'utf8')
    assert.doesNotMatch(saved, /!!js/)
    assert.match(saved, /value: 5/)
    return { savedResolvedValue: 5 }
  })
  await check('self-dispose disables the owning entry while retaining its declaration', async ctx => {
    const entry = await mount(ctx, () => {})
    await entry.fiber.dispose()
    assert.equal(entry.options.disabled, true)
    assert.equal(ctx.loader.resolve(entry.id), entry)
    return { disabled: true, entryRetained: true }
  })

  await check('loader await intercept delays a dependent until entry loading finishes', async ctx => {
    const began = deferred(), release = deferred()
    ctx.loader.builtins.slow = async () => { began.resolve(); await release.promise }
    await ctx.loader.create({ id: 'slow', name: 'cordis:slow' })
    await began.promise
    let activated = false
    const consumer = ctx.intercept('loader', { await: true }).plugin({ inject: ['loader'], apply() { activated = true } })
    try {
      await consumer.await()
      assert.equal(consumer.state, FiberState.PENDING)
      assert.equal(activated, false)
    } finally { release.resolve() }
    await ctx.loader.await()
    await consumer.await()
    assert.equal(activated, true)
    assert.equal(consumer.state, FiberState.ACTIVE)
    return { before: 'PENDING', after: 'ACTIVE' }
  })
  return results
}
