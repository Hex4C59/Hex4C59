import type { Context } from './runtime.js'
import type { FileSystem } from './fs-contract.js'

export let mounts = 0

// Deliberate plain-object assignment for the language experiment, not ctx.provide().
export function mountFs(ctx: Context): void {
  const fs: FileSystem = { readText: path => `read:${path}` }
  Object.assign(ctx, { fs })
  mounts += 1
}
