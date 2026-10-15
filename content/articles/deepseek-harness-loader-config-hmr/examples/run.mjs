import assert from 'node:assert/strict'
import { execFileSync } from 'node:child_process'
import { createRequire } from 'node:module'
import { mkdtemp, readdir, readFile, writeFile, mkdir, rm, cp } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { dirname, join, resolve } from 'node:path'
import { pathToFileURL } from 'node:url'
import { verifyLoader } from './scenarios.mjs'

const require = createRequire(import.meta.url)
const ts = require(process.env.DSH_LOADER_TYPESCRIPT ?? 'typescript')
assert.equal(ts.version, '6.0.3')
assert.ok(process.env.DSH_SOURCE, 'Set DSH_SOURCE to the pinned deepseek-harness checkout')
const source = resolve(process.env.DSH_SOURCE)
const commit = execFileSync('git', ['rev-parse', 'HEAD'], { cwd: source, encoding: 'utf8' }).trim()
assert.equal(commit, 'd743267388641bc76f17c45ce8b4c231aed1d32c')
const packages = ['cosmokit', 'cordis', 'schemastery', 'loader', 'include']
const modified = execFileSync('git', ['status', '--porcelain', '--', ...packages.map(p => `vendor/${p}`)], { cwd: source, encoding: 'utf8' }).trim()
assert.equal(modified, '', 'The five vendored source trees must match the pinned commit')
const yamlManifest = process.env.DSH_LOADER_YAML_PACKAGE ?? require.resolve('js-yaml/package.json')
const yamlPackage = JSON.parse(await readFile(yamlManifest, 'utf8'))
assert.equal(yamlPackage.version, '4.1.1')
const yamlRequire = createRequire(yamlManifest)
const work = await mkdtemp(join(tmpdir(), 'dsh-loader-lab-'))
try {
  // Copy only fixed, installed runtime dependencies; never install into the source checkout.
  for (const [name, manifest] of [['js-yaml', yamlManifest], ['argparse', yamlRequire.resolve('argparse/package.json')]]) {
    await cp(dirname(manifest), join(work, 'node_modules', name), { recursive: true })
  }
  async function transpile(input, output) {
    await mkdir(output, { recursive: true })
    for (const entry of await readdir(input, { withFileTypes: true })) {
      if (entry.isDirectory()) { await transpile(join(input, entry.name), join(output, entry.name)); continue }
      if (!entry.name.endsWith('.ts') || entry.name.endsWith('.d.ts')) continue
      const result = ts.transpileModule(await readFile(join(input, entry.name), 'utf8'), {
        fileName: join(input, entry.name), reportDiagnostics: true,
        compilerOptions: { target: ts.ScriptTarget.ES2024, module: ts.ModuleKind.ESNext, rewriteRelativeImportExtensions: true, verbatimModuleSyntax: false },
      })
      const errors = (result.diagnostics ?? []).filter(d => d.category === ts.DiagnosticCategory.Error)
      assert.equal(errors.length, 0, ts.formatDiagnosticsWithColorAndContext(errors, {
        getCanonicalFileName: x => x, getCurrentDirectory: () => source, getNewLine: () => '\n',
      }))
      await writeFile(join(output, entry.name.replace(/\.ts$/, '.js')), result.outputText)
    }
  }
  for (const name of packages) {
    const published = ['loader', 'include'].includes(name) ? `cordis-plugin-${name}` : name
    const output = join(work, 'node_modules', '@deepseek-ai', published)
    await transpile(join(source, 'vendor', name, 'src'), output)
    await writeFile(join(output, 'package.json'), JSON.stringify({ type: 'module', exports: './index.js' }))
  }
  const load = name => import(pathToFileURL(join(work, 'node_modules/@deepseek-ai', name, 'index.js')).href)
  const [cordis, loader, schema, include] = await Promise.all([load('cordis'), load('cordis-plugin-loader'), load('schemastery'), load('cordis-plugin-include')])
  const checks = await verifyLoader(cordis, loader, schema.default, include, work)
  console.log(JSON.stringify({ commit, node: process.version, typescript: ts.version, yaml: yamlPackage.version, checks }, null, 2))
} finally {
  await rm(work, { recursive: true, force: true })
}
