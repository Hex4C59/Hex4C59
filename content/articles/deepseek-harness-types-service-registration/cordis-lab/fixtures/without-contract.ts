import type { Context } from '@deepseek-ai/cordis'
import { readThroughContext } from '@dsh-blog/reader'
export function inspect(ctx: Context) {
  readThroughContext(ctx)
  return ctx.blogFiles
}
