import assert from 'node:assert/strict'
import { execFileSync } from 'node:child_process'
import { createRequire } from 'node:module'
import { cp, mkdir, mkdtemp, readFile, readdir, rm, writeFile } from 'node:fs/promises'
import { dirname, join, relative, resolve } from 'node:path'
import { tmpdir } from 'node:os'
import { pathToFileURL } from 'node:url'
import { verifyOwnership } from './scenarios.mjs'

const require = createRequire(import.meta.url)
const ts = require(process.env.DSH_AGENT_TYPESCRIPT ?? 'typescript')
assert.equal(ts.version, '6.0.3')
assert.ok(process.env.DSH_SOURCE, 'Set DSH_SOURCE to the fixed deepseek-harness checkout')
const source = resolve(process.env.DSH_SOURCE)
const commit = execFileSync('git', ['rev-parse', 'HEAD'], { cwd: source, encoding: 'utf8' }).trim()
assert.equal(commit, 'd743267388641bc76f17c45ce8b4c231aed1d32c')
const zodManifest = process.env.DSH_AGENT_ZOD_PACKAGE ?? require.resolve('zod/package.json')
assert.equal(JSON.parse(await readFile(zodManifest, 'utf8')).version, '4.4.3')
const work = await mkdtemp(join(tmpdir(), 'dsh-agent-ownership-'))
try {
  const packages = new Map()
  async function register(directory) {
    try {
      const manifest = JSON.parse(await readFile(join(directory, 'package.json'), 'utf8'))
      if (manifest.name) packages.set(manifest.name, { directory, exports: {} })
    } catch (error) { if (error.code !== 'ENOENT') throw error }
  }
  for (const child of await readdir(join(source, 'vendor'), { withFileTypes: true })) {
    if (child.isDirectory()) await register(join(source, 'vendor', child.name))
  }
  for (const group of await readdir(join(source, 'packages'), { withFileTypes: true })) {
    if (!group.isDirectory()) continue
    for (const child of await readdir(join(source, 'packages', group.name), { withFileTypes: true })) {
      if (child.isDirectory()) await register(join(source, 'packages', group.name, child.name))
    }
  }
  const used = new Map(), files = new Map()
  async function locate(specifier, from) {
    if (specifier.startsWith('node:')) return
    if (specifier.startsWith('.')) return { file: resolve(dirname(from), specifier).replace(/\.js$/, '.ts') }
    const parts = specifier.split('/')
    const name = specifier.startsWith('@') ? parts.slice(0, 2).join('/') : parts[0]
    if (name === 'zod') return
    const pkg = packages.get(name)
    assert.ok(pkg, `Unsupported external dependency: ${specifier}`)
    used.set(name, pkg)
    const sub = specifier.slice(name.length)
    let file = join(pkg.directory, 'src', sub ? sub.slice(1).replace(/\.js$/, '.ts') : 'index.ts')
    if (!/\.(ts|json)$/.test(file)) file += '.ts'
    pkg.exports[sub ? '.' + sub : '.'] = './' + relative(pkg.directory, file).replace(/\.ts$/, '.js')
    return { file, pkg: name }
  }
  async function visit(file, pkgName) {
    if (files.has(file)) return
    files.set(file, { pkgName, result: undefined })
    const raw = await readFile(file, 'utf8')
    if (file.endsWith('.json')) { files.set(file, { pkgName, result: raw }); return }
    const transformed = ts.transpileModule(raw, {
      fileName: file, reportDiagnostics: true,
      compilerOptions: { target: ts.ScriptTarget.ES2024, module: ts.ModuleKind.ESNext, rewriteRelativeImportExtensions: true, verbatimModuleSyntax: false },
    })
    const errors = (transformed.diagnostics ?? []).filter(d => d.category === ts.DiagnosticCategory.Error)
    assert.equal(errors.length, 0, ts.formatDiagnosticsWithColorAndContext(errors, {
      getCanonicalFileName: x => x, getCurrentDirectory: () => source, getNewLine: () => '\n',
    }))
    files.set(file, { pkgName, result: transformed.outputText })
    const ast = ts.createSourceFile(file, transformed.outputText, ts.ScriptTarget.ESNext, true, ts.ScriptKind.JS)
    for (const node of ast.statements) {
      if ((!ts.isImportDeclaration(node) && !ts.isExportDeclaration(node)) || !node.moduleSpecifier) continue
      const next = await locate(node.moduleSpecifier.text, file)
      if (next) await visit(next.file, next.pkg ?? pkgName)
    }
  }
  const entryNames = ['dsh-agent-loop', 'dsh-session-projection']
  for (const name of entryNames) {
    const entry = await locate('@deepseek-ai/' + name, join(source, '_entry.ts'))
    await visit(entry.file, entry.pkg)
  }
  const modified = execFileSync('git', ['status', '--porcelain', '--', ...[...used.values()].map(p => relative(source, p.directory))], { cwd: source, encoding: 'utf8' }).trim()
  assert.equal(modified, '', 'The reachable workspace packages must match the fixed source commit')
  await cp(dirname(zodManifest), join(work, 'node_modules/zod'), { recursive: true })
  for (const [file, record] of files) {
    const pkg = used.get(record.pkgName)
    const output = join(work, 'node_modules', record.pkgName, relative(pkg.directory, file).replace(/\.ts$/, '.js'))
    await mkdir(dirname(output), { recursive: true })
    await writeFile(output, record.result)
  }
  for (const [name, pkg] of used) {
    await writeFile(join(work, 'node_modules', name, 'package.json'), JSON.stringify({ name, type: 'module', exports: pkg.exports }))
  }
  const load = async name => {
    const pkg = used.get('@deepseek-ai/' + name)
    return import(pathToFileURL(join(work, 'node_modules/@deepseek-ai', name, pkg.exports['.'])).href)
  }
  const names = ['cordis', 'dsh-agent', 'dsh-agent-loop', 'dsh-session', 'dsh-session-projection', 'dsh-llm', 'dsh-tools', 'dsh-system-prompt', 'dsh-scope']
  const modules = Object.fromEntries(await Promise.all(names.map(async name => [name, await load(name)])))
  const checks = await verifyOwnership(modules)
  console.log(JSON.stringify({ commit, node: process.version, typescript: ts.version, zod: '4.4.3', packages: used.size, modules: files.size, checks }, null, 2))
} finally {
  await rm(work, { recursive: true, force: true })
}
