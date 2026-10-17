import { Service } from '@deepseek-ai/cordis'
import type { Context } from '@deepseek-ai/cordis'

// This teaching capability is not dsh's FileSystem or LocalFileSystem.
export abstract class BlogFiles extends Service<{ prefix: string }> {
  constructor(ctx: Context) { super(ctx, 'blogFiles') }
  abstract readText(path: string): string
}

export class MemoryFiles extends BlogFiles {
  constructor(ctx: Context, private options: { prefix: string }) { super(ctx) }
  readText(path: string) { return `${this.options.prefix}:${path}` }
}

declare module '@deepseek-ai/cordis' {
  interface Context {
    blogFiles: BlogFiles
    // A plain interface, deliberately without Service's config symbol.
    plainFiles: { readText(path: string): string }
  }
}
