import type {} from './runtime.js'

export interface FileSystem {
  readText(path: string): string
}

declare module './runtime.js' {
  interface Context {
    fs: FileSystem
  }
}
