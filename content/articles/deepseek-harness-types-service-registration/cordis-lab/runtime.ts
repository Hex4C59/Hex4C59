import assert from 'node:assert/strict'
import { Context, FiberState } from '@deepseek-ai/cordis'
import { MemoryFiles } from '@dsh-blog/files'
import { readThroughContext } from '@dsh-blog/reader'

export async function lifecycle() {
  const ctx = new Context()
  const trace: string[] = []
  const states: { stage: string, consumer: string, trace?: string[] }[] = []
  const labels: Record<number, string> = {
    [FiberState.PENDING]: 'PENDING', [FiberState.ACTIVE]: 'ACTIVE',
    [FiberState.DISPOSED]: 'DISPOSED',
  }
  const consumer = ctx.plugin({
    name: 'blog-reader', inject: ['blogFiles'],
    apply(ctx) {
      const value = readThroughContext(ctx)
      trace.push(`read:${value}`)
      ctx.effect(() => () => { trace.push(`cleanup:${value}`) })
    },
  })
  const snapshot = (stage: string) => {
    states.push({ stage, consumer: labels[consumer.state], trace: [...trace] })
  }
  try {
    await consumer
    assert.equal(consumer.state, FiberState.PENDING)
    assert.deepEqual(trace, [])
    snapshot('consumer-first')
    const provider = ctx.plugin(MemoryFiles, { prefix: 'v1' })
    await provider
    await consumer
    assert.equal(consumer.state, FiberState.ACTIVE)
    assert.deepEqual(trace, ['read:v1:hello.txt'])
    snapshot('provider-v1')
    await provider.dispose()
    await consumer
    assert.equal(consumer.state, FiberState.PENDING)
    assert.deepEqual(trace, ['read:v1:hello.txt', 'cleanup:v1:hello.txt'])
    snapshot('provider-removed')
    const replacement = ctx.plugin(MemoryFiles, { prefix: 'v2' })
    await replacement
    await consumer
    assert.equal(consumer.state, FiberState.ACTIVE)
    assert.deepEqual(trace, ['read:v1:hello.txt', 'cleanup:v1:hello.txt', 'read:v2:hello.txt'])
    snapshot('provider-v2')
    const isolated = ctx.isolate('blogFiles')
    const isolatedConsumer = isolated.inject(['blogFiles'], () => { throw new Error('wrong domain activated') })
    await isolatedConsumer
    assert.equal(isolatedConsumer.state, FiberState.PENDING)
    assert.equal(isolated.get('blogFiles'), undefined)
    states.push({ stage: 'other-domain', consumer: labels[isolatedConsumer.state] })
  } finally {
    await ctx.fiber.dispose()
  }
  assert.deepEqual(trace, [
    'read:v1:hello.txt', 'cleanup:v1:hello.txt',
    'read:v2:hello.txt', 'cleanup:v2:hello.txt',
  ])
  states.push({ stage: 'root-disposed', consumer: labels[consumer.state], trace: [...trace] })
  return states
}
