import type { Context } from './runtime.js'
import type {} from './fs-contract.js'

export function readThroughContext(ctx: Context): string {
  return ctx.fs.readText('hello.txt')
}
