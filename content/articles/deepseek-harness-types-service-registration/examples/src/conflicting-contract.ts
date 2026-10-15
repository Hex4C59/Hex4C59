import type {} from './fs-contract.js'

declare module './runtime.js' {
  interface Context {
    fs: string
  }
}
