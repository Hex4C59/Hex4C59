import type { Context } from './runtime.js'
import type { FileSystem } from './fs-contract.js'

// A reduced copy of the overload shapes; no Cordis runtime is loaded.
interface Facade {
  get<K extends string & keyof Context>(name: K): undefined | Context[K]
  get(name: string): any
  provide<K extends string & keyof Context>(name: K, value: undefined | Context[K]): () => void
  provide(name: string, value?: any): () => void
}

export function inspectFacade(facade: Facade) {
  const known = facade.get('fs')
  const unknown = facade.get('misspelled-service')
  // This passes through the permissive fallback overload, despite the wrong value.
  facade.provide('fs', { unrelated: true })
  return { known, unknown }
}

type Equal<A, B> = (<T>() => T extends A ? 1 : 2) extends
  (<T>() => T extends B ? 1 : 2) ? true : false
type Assert<T extends true> = T
type IsAny<T> = 0 extends (1 & T) ? true : false
type Inferred = ReturnType<typeof inspectFacade>
export type KnownIsOptionalFs = Assert<Equal<Inferred['known'], FileSystem | undefined>>
export type UnknownFallsBackToAny = Assert<IsAny<Inferred['unknown']>>
