import type { Context } from '@deepseek-ai/cordis'
import type {} from '@dsh-blog/files'

export function readThroughContext(ctx: Context): string {
  return ctx.blogFiles.readText('hello.txt')
}
