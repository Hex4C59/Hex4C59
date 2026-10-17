import assert from 'node:assert/strict'
import { spawnSync, execFileSync } from 'node:child_process'
import { cp, mkdir, mkdtemp, readFile, readdir, rm, symlink, writeFile } from 'node:fs/promises'
import { createRequire } from 'node:module'
import { tmpdir } from 'node:os'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'
import { build } from 'tsdown'

const root = dirname(fileURLToPath(import.meta.url))
const source = process.env.DSH_SOURCE
assert.ok(source, 'Set DSH_SOURCE to a DeepSeek Harness 0.2.1-alpha.2 checkout')
const baseline = 'd743267388641bc76f17c45ce8b4c231aed1d32c'
assert.equal(execFileSync('git', ['rev-parse', 'HEAD'], { cwd: source, encoding: 'utf8' }).trim(), baseline)
assert.equal(execFileSync('git', ['status', '--porcelain', '--', 'vendor/cordis', 'vendor/cosmokit', 'tsconfig.base.json'], { cwd: source, encoding: 'utf8' }).trim(), '')
assert.equal(JSON.parse(await readFile(join(source, 'package.json'), 'utf8')).version, '0.2.1-alpha.2')
const require = createRequire(import.meta.url)
const compiler = require.resolve('typescript/bin/tsc')
const dependencies = join(root, 'node_modules')
const work = await mkdtemp(join(tmpdir(), 'dsh-types-cordis-'))
const reports = resolve(root, process.argv.includes('--report-dir') ? process.argv[process.argv.indexOf('--report-dir') + 1] : 'reports')
const keepWorkspace = process.argv.includes('--keep-workspace')
const checks = [], logs = {}, details = {}
const clean = text => text.replaceAll(work, '<work>').replaceAll(resolve(source), '<source>').replaceAll(root, '<lab>')
function command(bin, args, cwd = work, expected = 0) {
  const result = spawnSync(bin, args, { cwd, encoding: 'utf8', maxBuffer: 16 * 1024 * 1024,
    env: { ...process.env, npm_config_update_notifier: 'false' } })
  if (result.error) throw result.error
  const text = result.stdout + result.stderr
  if (expected === 0) assert.equal(result.status, 0, clean(text))
  else assert.notEqual(result.status, 0, clean(text))
  return text
}
function tsc(args, cwd = work, expected = 0) { return command(process.execPath, [compiler, ...args], cwd, expected) }
function npm(args, cwd = work) { return command(process.platform === 'win32' ? 'npm.cmd' : 'npm', args, cwd) }
function pass(label) { checks.push(label); console.log(`PASS ${label}`) }
async function json(path, object) { await writeFile(path, JSON.stringify(object, null, 2) + '\n') }
async function link(from, to) { await mkdir(dirname(to), { recursive: true }); await symlink(from, to, 'dir') }
async function pack(directory) {
  const result = JSON.parse(npm(['pack', directory, '--ignore-scripts', '--json', '--pack-destination', join(work, 'tarballs')]))[0]
  details.packages ??= []
  details.packages.push({ name: result.name, version: result.version, files: result.files.map(file => file.path) })
  return join(work, 'tarballs', result.filename)
}
try {
  assert.equal(tsc(['--version']).trim(), 'Version 6.0.3')
  for (const [name, version] of Object.entries({ tsdown: '0.22.2', '@types/node': '22.20.1', '@standard-schema/spec': '1.1.0' })) {
    assert.equal(JSON.parse(await readFile(join(dependencies, name, 'package.json'), 'utf8')).version, version)
  }
  await mkdir(join(work, 'tarballs'))
  const workspace = join(work, 'workspace')
  await mkdir(workspace)
  await cp(join(source, 'tsconfig.base.json'), join(workspace, 'tsconfig.base.json'))
  const vendorVersions = new Map()
  for (const directory of await readdir(join(source, 'vendor'), { withFileTypes: true })) {
    if (!directory.isDirectory()) continue
    try {
      const manifest = JSON.parse(await readFile(join(source, 'vendor', directory.name, 'package.json'), 'utf8'))
      vendorVersions.set(manifest.name, manifest.version)
    } catch (error) { if (error.code !== 'ENOENT') throw error }
  }
  for (const name of ['cordis', 'cosmokit']) {
    const target = join(workspace, 'vendor', name)
    await cp(join(source, 'vendor', name), target, { recursive: true, filter: path => !['node_modules', 'lib'].includes(path.split('/').at(-1)) })
    const manifest = JSON.parse(await readFile(join(target, 'package.json'), 'utf8'))
    for (const field of ['dependencies', 'peerDependencies']) {
      for (const [key, value] of Object.entries(manifest[field] ?? {})) {
        if (!value.startsWith('workspace:')) continue
        assert.ok(vendorVersions.has(key), `Unknown workspace dependency ${key}`)
        manifest[field][key] = vendorVersions.get(key)
      }
    }
    await json(join(target, 'package.json'), manifest)
    await cp(join(source, 'LICENSE'), join(target, 'LICENSE'))
    await link(target, join(workspace, 'node_modules', '@deepseek-ai', name))
  }
  for (const name of ['@types', '@standard-schema', 'undici-types']) {
    await link(join(dependencies, name), join(workspace, 'node_modules', name))
  }
  logs['vendor-build.log'] = tsc(['-b', 'vendor/cordis/tsconfig.json', '--pretty', 'false'], workspace)
  pass('real Cordis and Cosmokit project-reference build')
  for (const name of ['cosmokit', 'cordis']) {
    const directory = join(workspace, 'vendor', name)
    await build({ config: false, cwd: directory, entry: ['lib/types/index.js'], outDir: 'lib',
      format: ['esm'], platform: 'node', target: 'es2024', fixedExtension: false,
      dts: false, clean: false, sourcemap: false, deps: { neverBundle: ['@deepseek-ai/cosmokit'] } })
  }
  pass('bundle emitted JavaScript with tsdown; retain tsc declarations')
  const packageConfig = { compilerOptions: { target: 'ES2024', module: 'NodeNext', moduleResolution: 'NodeNext',
    rootDir: 'src', outDir: 'lib', declaration: true, strict: true, skipLibCheck: false, types: [] }, include: ['src'] }
  for (const name of ['files', 'reader']) {
    const target = join(workspace, 'packages', name)
    await cp(join(root, 'packages', name), target, { recursive: true })
    await json(join(target, 'tsconfig.json'), packageConfig)
    await link(target, join(workspace, 'node_modules', '@dsh-blog', name))
    logs[`${name}-build.log`] = tsc(['-p', 'tsconfig.json', '--pretty', 'false'], target)
  }
  const readerDts = await readFile(join(workspace, 'packages/reader/lib/index.d.ts'), 'utf8')
  assert.doesNotMatch(readerDts, /@dsh-blog\/files/)
  logs['reader-output.d.ts'] = readerDts
  pass('real Cordis consumer declaration omits its empty type import')
  const archives = []
  for (const directory of [join(workspace, 'vendor/cosmokit'), join(workspace, 'vendor/cordis'),
    join(dependencies, '@standard-schema/spec'), join(workspace, 'packages/files'), join(workspace, 'packages/reader')]) {
    archives.push(await pack(directory))
  }
  for (const name of ['@deepseek-ai/cordis', '@deepseek-ai/cosmokit']) {
    const packed = details.packages.find(pkg => pkg.name === name)
    assert.ok(packed.files.includes('lib/index.js'))
    assert.ok(packed.files.includes('lib/types/index.d.ts'))
  }
  pass('pack five local tarballs with runtime and type entries')
  const consumer = join(work, 'consumer')
  await mkdir(consumer)
  await json(join(consumer, 'package.json'), { name: 'isolated-cordis-consumer', private: true, type: 'module' })
  logs['consumer-install.log'] = npm(['install', '--offline', '--ignore-scripts', '--legacy-peer-deps',
    '--package-lock=false', '--no-audit', '--no-fund', ...archives], consumer)
  await cp(join(root, 'fixtures'), join(consumer, 'fixtures'), { recursive: true })
  await cp(join(root, 'runtime.ts'), join(consumer, 'runtime.ts'))
  pass('install only packed dependencies into independent consumer')
  async function checkFixture(name, mode = 'NodeNext', expected = 0, diagnostic) {
    const config = join(consumer, `${name}-${mode}.json`)
    await json(config, { compilerOptions: { target: 'ES2024', module: mode === 'NodeNext' ? 'NodeNext' : 'ESNext',
      moduleResolution: mode, strict: true, skipLibCheck: false, types: [], noEmit: true },
      files: [`fixtures/${name}.ts`], include: [] })
    const output = tsc(['-p', config, '--pretty', 'false'], consumer, expected)
    if (diagnostic) assert.match(output, new RegExp(diagnostic))
    logs[`${name}-${mode}.log`] = output
    return config
  }
  let positive, negative
  for (const mode of ['NodeNext', 'Bundler']) {
    positive = await checkFixture('with-contract', mode)
    negative = await checkFixture('without-contract', mode, 1, 'TS2339')
    pass(`${mode}: explicit augmentation passes; reader alone gives TS2339`)
  }
  await checkFixture('inject-positive')
  pass('ordinary inject metadata accepts misspelled name and wrong config')
  for (const [fixture, diagnostic] of [['inject-wrong-name', 'TS2345'], ['inject-wrong-config', 'TS2322'], ['inject-plain-interface', 'TS2345']]) {
    await checkFixture(fixture, 'NodeNext', 1, diagnostic)
    pass(`${fixture}: ${diagnostic}`)
  }
  await json(join(consumer, 'runtime.json'), { compilerOptions: {
    target: 'ES2024', module: 'NodeNext', moduleResolution: 'NodeNext', strict: true,
    skipLibCheck: false, types: ['node'], typeRoots: [join(dependencies, '@types')],
  }, files: ['runtime.ts'], include: [] })
  logs['runtime-build.log'] = tsc(['-p', 'runtime.json', '--pretty', 'false'], consumer)
  const runtime = await import(pathToFileURL(join(consumer, 'runtime.js')).href)
  details.lifecycle = await runtime.lifecycle()
  pass('real provide/inject lifecycle, cleanup, restoration and isolation')
  logs['explain-with-contract.log'] = tsc(['-p', positive, '--explainFiles', '--pretty', 'false'], consumer)
  logs['explain-without-contract.log'] = tsc(['-p', negative, '--explainFiles', '--pretty', 'false'], consumer, 1)
  assert.match(logs['explain-with-contract.log'], /node_modules\/@dsh-blog\/files\/lib\/index.d.ts/)
  assert.doesNotMatch(logs['explain-without-contract.log'], /node_modules\/@dsh-blog\/files\/lib\/index.d.ts/)
  logs['trace-resolution.log'] = tsc(['-p', positive, '--traceResolution', '--pretty', 'false'], consumer)
  assert.match(logs['trace-resolution.log'], /Matched 'exports' condition 'types'/)
  assert.match(logs['trace-resolution.log'], /@dsh-blog\/files\/lib\/index.d.ts/)
  pass('explainFiles and traceResolution expose augmentation entry')
  await mkdir(reports, { recursive: true })
  for (const [name, text] of Object.entries(logs)) await writeFile(join(reports, name), clean(text))
  await json(join(reports, 'report.json'), { version: '0.2.1-alpha.2', cordis: '4.0.5-alpha.1', baseline,
    node: process.version, typescript: '6.0.3', tsdown: '0.22.2', checks, ...details })
  if (keepWorkspace) console.log(`Consumer retained for inspection: ${consumer}`)
  console.log(JSON.stringify(details.lifecycle, null, 2))
  console.log(`${checks.length} checks passed · Node ${process.version} · TypeScript 6.0.3`)
} finally {
  if (!keepWorkspace) await rm(work, { recursive: true, force: true })
}
