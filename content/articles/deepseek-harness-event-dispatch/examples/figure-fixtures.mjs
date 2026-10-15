import assert from 'node:assert/strict'

// The figure compares one controlled input per mode; waterfall needs next wrappers.
export async function verifyFigureCases({ Context }) {
  const expected = {
    'emit/normal': ['A:start', 'B:0', 'C:last', 'caller:undefined', 'A:end'],
    'parallel/normal': ['A:start', 'B:0', 'C:last', 'caller:Promise', 'A:end', 'caller:resolved:undefined'],
    'serial/normal': ['A:start', 'caller:Promise', 'A:end', 'B:0', 'caller:resolved:0'],
    'bail/normal': ['A:start', 'caller:Promise', 'A:end', 'caller:resolved:undefined'],
    'waterfall/normal': ['A:enter', 'B:enter', 'C:enter', 'inner:base', 'C:exit', 'B:exit', 'A:exit', 'caller:baseCBA'],
    'emit/throw': ['A:throw', 'caller:Error:A'],
    'parallel/throw': ['A:throw', 'B:0', 'C:last', 'caller:Promise', 'caller:AggregateError:A'],
    'serial/throw': ['A:throw', 'caller:Promise', 'caller:Error:A'],
    'bail/throw': ['A:throw', 'caller:Error:A'],
    'waterfall/throw': ['A:throw', 'caller:Error:A'],
  }
  const cases = []
  for (const scenario of ['normal', 'throw']) {
    for (const mode of ['emit', 'parallel', 'serial', 'bail', 'waterfall']) {
      const ctx = new Context()
      const trace = []
      let release
      let pending
      const gate = new Promise(resolve => { release = resolve })
      try {
        for (const [index, name] of ['A', 'B', 'C'].entries()) {
          ctx.on('lab/figure', (...args) => {
            if (scenario === 'throw' && name === 'A') {
              trace.push('A:throw')
              throw new Error('A')
            }
            if (mode === 'waterfall') {
              trace.push(`${name}:enter`)
              const result = args.at(-1)()
              trace.push(`${name}:exit`)
              return result + name
            }
            if (index === 0) {
              trace.push('A:start')
              pending = gate.then(() => { trace.push('A:end') })
              return pending
            }
            const value = index === 1 ? 0 : 'last'
            trace.push(`${name}:${value}`)
            return value
          })
        }
        try {
          const result = mode === 'waterfall'
            ? ctx.waterfall('lab/figure', () => { trace.push('inner:base'); return 'base' })
            : ctx[mode]('lab/figure')
          const isPromise = result instanceof Promise
          trace.push(`caller:${isPromise ? 'Promise' : result}`)
          release()
          if (isPromise) trace.push(`caller:resolved:${await result}`)
          else if (pending) await pending
        } catch (error) {
          trace.push(`caller:${error.name}:${error instanceof AggregateError ? error.errors.map(e => e.message).join(',') : error.message}`)
        }
        const key = `${mode}/${scenario}`
        assert.deepEqual(trace, expected[key], key)
        cases.push({ mode, scenario, trace })
      } finally {
        release()
        await ctx.fiber.dispose()
      }
    }
  }
  console.log(`PASS ${cases.length} figure fixtures`)
  return cases
}
