import assert from 'node:assert/strict'
import { execFileSync } from 'node:child_process'
import { createRequire } from 'node:module'
import { mkdtemp, readdir, readFile, writeFile, mkdir, rm } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join, resolve } from 'node:path'
import { pathToFileURL } from 'node:url'
import { verifyEvents } from './scenarios.mjs'
import { verifyFigureCases } from './figure-fixtures.mjs'

const require = createRequire(import.meta.url)
const ts = require(process.env.DSH_EVENTS_TYPESCRIPT ?? 'typescript')
assert.equal(ts.version, '6.0.3')
const source = resolve(process.env.DSH_SOURCE ?? '')
assert.ok(process.env.DSH_SOURCE, 'Set DSH_SOURCE to the pinned deepseek-harness checkout')
const commit = execFileSync('git', ['rev-parse', 'HEAD'], { cwd: source, encoding: 'utf8' }).trim()
assert.equal(commit, 'd743267388641bc76f17c45ce8b4c231aed1d32c')
const modified = execFileSync('git', ['status', '--porcelain', '--', 'vendor/cordis', 'vendor/cosmokit'], { cwd: source, encoding: 'utf8' }).trim()
assert.equal(modified, '', 'The Cordis and cosmokit source trees must match the pinned commit')
const work = await mkdtemp(join(tmpdir(), 'dsh-cordis-events-'))
try {
  for (const name of ['cosmokit', 'cordis']) {
    const input = join(source, 'vendor', name, 'src')
    const output = join(work, 'node_modules', '@deepseek-ai', name)
    await mkdir(output, { recursive: true })
    await writeFile(join(output, 'package.json'), JSON.stringify({ type: 'module', exports: './index.js' }))
    for (const entry of await readdir(input)) {
      if (!entry.endsWith('.ts') || entry.endsWith('.d.ts')) continue
      const result = ts.transpileModule(await readFile(join(input, entry), 'utf8'), {
        fileName: join(input, entry), reportDiagnostics: true,
        compilerOptions: { target: ts.ScriptTarget.ES2024, module: ts.ModuleKind.ESNext, rewriteRelativeImportExtensions: true, verbatimModuleSyntax: false },
      })
      const errors = (result.diagnostics ?? []).filter(d => d.category === ts.DiagnosticCategory.Error)
      assert.equal(errors.length, 0, ts.formatDiagnosticsWithColorAndContext(errors, {
        getCanonicalFileName: x => x, getCurrentDirectory: () => source, getNewLine: () => '\n',
      }))
      await writeFile(join(output, entry.replace(/\.ts$/, '.js')), result.outputText)
    }
  }
  const cordis = await import(pathToFileURL(join(work, 'node_modules/@deepseek-ai/cordis/index.js')).href)
  const report = await verifyEvents(cordis)
  const figures = await verifyFigureCases(cordis)
  console.log(JSON.stringify({ commit, node: process.version, typescript: ts.version, checks: report, figures }, null, 2))
} finally {
  await rm(work, { recursive: true, force: true })
}
