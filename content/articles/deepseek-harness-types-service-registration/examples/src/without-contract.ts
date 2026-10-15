import type { Context } from './runtime.js'

export function readWithoutContract(ctx: Context) {
  return ctx.fs
}
