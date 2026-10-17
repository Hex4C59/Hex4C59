import { Inject } from '@deepseek-ai/cordis'
import type { Plugin } from '@deepseek-ai/cordis'
import type {} from '@dsh-blog/files'

// Ordinary metadata is open; these two mistakes still type-check.
export const wrongName: Plugin.Object<void> = { inject: ['blogFiels'], apply() {} }
export const wrongConfig: Plugin.Object<void> = {
  inject: { blogFiles: { prefix: 123 } }, apply() {},
}

// The decorator function checks both the known key and config type.
@Inject('blogFiles', { prefix: 'ok' })
export class TypedConsumer {}
