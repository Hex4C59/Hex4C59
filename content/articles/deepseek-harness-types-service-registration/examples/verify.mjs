import assert from 'node:assert/strict'
import { spawnSync } from 'node:child_process'
import { mkdtemp, readFile, rm, writeFile } from 'node:fs/promises'
import { createRequire } from 'node:module'
import { tmpdir } from 'node:os'
import { dirname, join } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

const root = dirname(fileURLToPath(import.meta.url))
const require = createRequire(import.meta.url)
const compiler = process.env.DSH_TYPES_TSC ?? require.resolve('typescript/bin/tsc')
const workspace = await mkdtemp(join(tmpdir(), 'dsh-types-registration-'))
const run = args => {
  const result = spawnSync(process.execPath, [compiler, ...args], { cwd: root, encoding: 'utf8' })
  if (result.error) throw result.error
  return { status: result.status, text: result.stdout + result.stderr }
}
const passes = []
const pass = label => { passes.push(label); console.log(`PASS ${label}`) }
try {
  const version = run(['--version'])
  assert.equal(version.text.trim(), 'Version 6.0.3')
  const positive = run(['-p', 'tsconfig.main.json', '--outDir', workspace])
  assert.equal(positive.status, 0, positive.text)
  pass('augmentation included: compile succeeds')
  const missing = run(['-p', 'tsconfig.missing.json', '--noEmit'])
  assert.notEqual(missing.status, 0)
  assert.match(missing.text, /TS2339/)
  pass('augmentation absent: TS2339')
  const conflict = run(['-p', 'tsconfig.conflict.json', '--noEmit'])
  assert.notEqual(conflict.status, 0)
  assert.match(conflict.text, /TS2717/)
  pass('incompatible merge: TS2717')
  const overloads = run(['-p', 'tsconfig.overloads.json', '--noEmit'])
  assert.equal(overloads.status, 0, overloads.text)
  pass('known get is optional; fallback permits any and mismatched provide')
  const consumerJs = await readFile(join(workspace, 'with-contract.js'), 'utf8')
  const contractDts = await readFile(join(workspace, 'fs-contract.d.ts'), 'utf8')
  const consumerDts = await readFile(join(workspace, 'with-contract.d.ts'), 'utf8')
  assert.doesNotMatch(consumerJs, /fs-contract/)
  assert.match(contractDts, /declare module ['"]\.\/runtime\.js['"]/)
  assert.doesNotMatch(consumerDts, /fs-contract/)
  pass('type import erased; augmentation remains in its own declaration')
  await writeFile(join(workspace, 'package.json'), '{"type":"module"}\n')
  const externalSource = "import type { Context } from './runtime.js';\nimport { readThroughContext } from './with-contract.js';\nexport function probe(ctx: Context) { readThroughContext(ctx); return ctx.fs; }\n"
  for (const includeContract of [false, true]) {
    const stem = includeContract ? 'external-with-contract' : 'external-without-contract'
    const source = (includeContract ? "import type {} from './fs-contract.js';\n" : '') + externalSource
    await writeFile(join(workspace, `${stem}.ts`), source)
    const config = {
      compilerOptions: { target: 'ES2024', module: 'NodeNext', moduleResolution: 'NodeNext', strict: true, types: [], lib: ['ES2024'], noEmit: true },
      files: [`${stem}.ts`], include: [],
    }
    const project = join(workspace, `${stem}.json`)
    await writeFile(project, JSON.stringify(config))
    const result = run(['-p', project])
    if (includeContract) assert.equal(result.status, 0, result.text)
    else { assert.notEqual(result.status, 0); assert.match(result.text, /TS2339/) }
  }
  pass('external declaration consumer needs its own augmentation path')
  const { Context } = await import(pathToFileURL(join(workspace, 'runtime.js')).href)
  const { readThroughContext } = await import(pathToFileURL(join(workspace, 'with-contract.js')).href)
  const provider = await import(pathToFileURL(join(workspace, 'provider.js')).href)
  const a = new Context()
  const b = new Context()
  assert.equal(provider.mounts, 0)
  assert.equal(typeof a.fs, 'undefined')
  assert.throws(() => readThroughContext(a), TypeError)
  pass('importing provider module does not call mountFs')
  provider.mountFs(a)
  assert.equal(provider.mounts, 1)
  assert.equal(readThroughContext(a), 'read:hello.txt')
  assert.equal(typeof b.fs, 'undefined')
  assert.throws(() => readThroughContext(b), TypeError)
  pass('mounting A does not add the property to B')
  console.log(`${passes.length} checks passed · Node ${process.version} · TypeScript 6.0.3`)
} finally {
  await rm(workspace, { recursive: true, force: true })
}
