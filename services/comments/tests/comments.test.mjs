import test from 'node:test';
import assert from 'node:assert/strict';
import { createHandler, ArticleComments } from '../worker.mjs';
import { makeAnchor, validAnchor, resolveAnchor, encodeAnchor, decodeAnchor, quoteBody } from '../../../assets/js/annotations-model.mjs';

const origin = 'https://blog.example';
const settings = { SITE_URL: origin + '/', REPO: 'owner/blog', REPO_ID: 'repo', CATEGORY: 'Comments', CATEGORY_ID: 'category', OWNER: 'owner' };
const response = (data, status = 200) => new Response(JSON.stringify(data), { status, headers: { 'Content-Type': 'application/json' } });
function fixture(options = {}) {
  const saved = new Map();
  const calls = [], mutations = [];
  let creates = 0, exists = options.exists !== false;
  const discussion = { id: 'discussion', url: 'https://github.com/owner/blog/discussions/7', locked: false,
    repository: { nameWithOwner: options.repo || settings.REPO }, totalCommentCount: 0, comments: [],
    pageInfo: { startCursor: 'cursor', hasPreviousPage: true } };
  const fetcher = async (address, init = {}) => {
    const url = new URL(address); calls.push({ url, init });
    if (options.unavailable) throw Error('network');
    if (url.pathname === '/api/oauth/token') {
      if (options.expired) return response({ error: 'State has expired.' }, 400);
      return response({ token: 'test-token-not-for-client' });
    }
    if (url.pathname === '/api/discussions') {
      if (init.method === 'POST') { creates++; await Promise.resolve(); exists = true; return response({ id: 'discussion' }); }
      return exists ? response({ discussion, viewer: { login: 'giscus-bot' } }) : response({ error: 'Discussion not found' }, 404);
    }
    assert.equal(url.href, 'https://api.github.com/graphql');
    const body = JSON.parse(init.body);
    if (body.query.includes('query { viewer')) return response({ data: { viewer: { login: options.login || 'reader', url: 'https://github.com/reader' } } });
    if (body.query.includes('... on DiscussionComment')) return response({ data: { node: {
      id: body.variables.id, replyTo: options.isReply ? { id: 'parent' } : null,
      isMinimized: options.minimized || false, discussion: { id: options.foreign ? 'other' : 'discussion', locked: options.locked || false, repository: { nameWithOwner: options.foreignRepo || settings.REPO } },
    } } });
    if (body.query.includes('... on Discussion{')) return response({ data: { node: { id: 'discussion', number: 7, repository: { nameWithOwner: settings.REPO } } } });
    mutations.push(body);
    if (body.query.includes('addDiscussionComment')) return response({ data: { addDiscussionComment: { comment: { id: 'comment-' + mutations.length, bodyHTML: '<p>Stored comment</p>', author: { login: options.login || 'reader' }, createdAt: '2026-10-15T00:00:00Z' } } } });
    return response({ data: {} });
  };
  const actor = new ArticleComments({ storage: { get: key => saved.get(key), put: (key, value) => saved.set(key, value) } }, settings, fetcher);
  const env = { ...settings, ARTICLES: { idFromName: name => name, get: () => actor }, ...options.env };
  const handler = createHandler(fetcher);
  const request = async (route, { method = 'GET', body, headers = {}, query = '' } = {}) => {
    const result = await handler(new Request('https://api.example/' + route + query, {
      method, headers: { Origin: origin, ...(method === 'POST' ? { Authorization: 'Giscus abcdefgh+/==' } : {}), ...headers },
      ...(body !== undefined ? { body: typeof body === 'string' ? body : JSON.stringify(body) } : {}),
    }), env);
    return { status: result.status, headers: result.headers, data: result.status === 204 ? null : await result.json() };
  };
  return { request, calls, mutations, saved, discussion, creates: () => creates };
}

test('Unicode anchors survive a portable URL round trip', () => {
  const text = '前言：一段中文与 emoji 🌿，也可以带 `代码`。';
  const anchor = makeAnchor(text, 1, 3, text.length);
  assert.deepEqual(decodeAnchor(encodeAnchor(anchor)), anchor);
  const body = quoteBody('讨论内容', anchor, origin + '/article/?tracking=1');
  assert.ok(body.includes('[查看划线原文](https://blog.example/article/#annotation='));
  assert.ok(!body.includes('tracking'));
  assert.ok(body.endsWith('\n\n讨论内容'));
});
test('invalid and oversized anchor payloads are rejected', () => {
  assert.equal(decodeAnchor('%%%'), null);
  assert.equal(decodeAnchor('a'.repeat(9000)), null);
  assert.equal(validAnchor({ ...makeAnchor('quote', 0, 0, 5), quote: 'a'.repeat(1001) }), false);
  assert.equal(validAnchor({ ...makeAnchor('quote', 0, 0, 5), v: 2 }), false);
});
test('a moved paragraph resolves using its original text', () => {
  const anchor = makeAnchor('hello quoted text after', 0, 6, 17);
  assert.deepEqual(resolveAnchor(anchor, ['new paragraph', 'hello quoted text after']), { index: 1, start: 6, end: 17, score: 22 });
});
test('surrounding context disambiguates repeated quotations', () => {
  const original = 'first quoted last';
  const anchor = makeAnchor(original, 0, 6, 12);
  const found = resolveAnchor(anchor, ['different quoted context', 'prefix ' + original]);
  assert.equal(found.index, 1);
});
test('ambiguous duplicate paragraphs remain detached', () => {
  const anchor = makeAnchor('same quote', 0, 5, 10);
  assert.equal(resolveAnchor(anchor, ['same quote', 'same quote']), null);
});
test('deleted or rewritten quotations do not attach to nearby text', () => {
  const anchor = makeAnchor('original quoted sentence', 0, 9, 15);
  assert.equal(resolveAnchor(anchor, ['original rewritten sentence']), null);
});
test('overlapping quotations resolve independently', () => {
  const text = 'one two three four';
  const first = makeAnchor(text, 0, 4, 13), second = makeAnchor(text, 0, 8, 18);
  assert.equal(resolveAnchor(first, [text]).start, 4);
  assert.equal(resolveAnchor(second, [text]).start, 8);
});

test('preflight allows only configured site and explicit headers', async () => {
  const f = fixture(); const r = await f.request('comment', { method: 'OPTIONS' });
  assert.equal(r.status, 204); assert.equal(r.headers.get('Access-Control-Allow-Origin'), origin);
  assert.equal(r.headers.get('Access-Control-Allow-Headers'), 'Content-Type, Authorization');
  assert.equal(f.calls.length, 0);
});
test('foreign origins cannot read or post through the API', async () => {
  const f = fixture(); const r = await f.request('discussion', { headers: { Origin: 'https://other.example' }, query: '?path=/article/' });
  assert.equal(r.status, 403); assert.equal(f.calls.length, 0);
});
test('writes without an Origin are rejected', async () => {
  const f = fixture(); const r = await f.request('comment', { method: 'POST', headers: { Origin: '' }, body: { path: '/article/', message: 'test' } });
  assert.equal(r.status, 403); assert.equal(f.calls.length, 0);
});
for (const path of ['https://evil.example/', '//evil.example/', '/a/../b/', '/%2e%2e/x/', '/article/?x=1', '/article/#target', '/back\\slash/']) {
  test('invalid path is rejected: ' + path, async () => {
    const f = fixture(); const r = await f.request('discussion', { query: '?path=' + encodeURIComponent(path) });
    assert.equal(r.status, 400); assert.equal(f.calls.length, 0);
  });
}
test('malformed JSON is a client error', async () => {
  const f = fixture(); assert.equal((await f.request('comment', { method: 'POST', body: '{' })).status, 400);
});
test('oversized request is rejected before authentication', async () => {
  const f = fixture(); const r = await f.request('comment', { method: 'POST', body: 'a'.repeat(20001) });
  assert.equal(r.status, 413); assert.equal(f.calls.length, 0);
});
test('missing session does not reach upstream authentication', async () => {
  const f = fixture(); const r = await f.request('comment', { method: 'POST', headers: { Authorization: '' }, body: { path: '/article/', message: 'test' } });
  assert.equal(r.status, 401); assert.equal(f.calls.length, 0);
});
test('expired sessions require login without leaking upstream details', async () => {
  const f = fixture({ expired: true }); const r = await f.request('viewer', { headers: { Authorization: 'Giscus abcdefgh+/==' } });
  assert.equal(r.status, 401); assert.ok(!JSON.stringify(r.data).includes('token'));
});
test('viewer returns public identity and never the decrypted token', async () => {
  const f = fixture(); const r = await f.request('viewer', { headers: { Authorization: 'Giscus abcdefgh+/==' } });
  assert.equal(r.status, 200); assert.equal(r.data.viewer.login, 'reader'); assert.ok(!JSON.stringify(r.data).includes('test-token-not-for-client'));
});
test('anonymous pagination reads newest comments and preserves the older cursor', async () => {
  const f = fixture(); const r = await f.request('discussion', { query: '?path=/article/&before=old-cursor' });
  assert.equal(r.status, 200); const call = f.calls.find(call => call.url.pathname === '/api/discussions');
  assert.equal(call.url.searchParams.get('last'), '50'); assert.equal(call.url.searchParams.get('strict'), 'true'); assert.equal(call.url.searchParams.get('before'), 'old-cursor');
  assert.equal(r.data.discussion.id, 'discussion'); assert.equal(r.data.viewer, undefined);
});
test('discussion number is persisted and used after search indexing', async () => {
  const f = fixture(); await f.request('discussion', { query: '?path=/article/' }); await f.request('discussion', { query: '?path=/article/&before=older' });
  assert.equal(f.saved.get('discussion').number, 7);
  assert.equal(f.calls.filter(call => call.url.pathname === '/api/discussions')[1].url.searchParams.get('number'), '7');
});
test('a missing discussion is an empty state rather than an error', async () => {
  const f = fixture({ exists: false }); const r = await f.request('discussion', { query: '?path=/article/' });
  assert.equal(r.status, 200); assert.equal(r.data.discussion, null);
});
test('upstream data from a different repository is rejected', async () => {
  const f = fixture({ repo: 'other/repo' }); assert.equal((await f.request('discussion', { query: '?path=/article/' })).status, 502);
});
test('concurrent first comments create only one article discussion', async () => {
  const f = fixture({ exists: false });
  const results = await Promise.all(['one', 'two'].map(message => f.request('comment', { method: 'POST', body: { path: '/article/', message } })));
  assert.deepEqual(results.map(r => r.status), [201, 201]); assert.equal(f.creates(), 1); assert.equal(f.mutations.length, 2);
});
test('a quote becomes a normal portable GitHub comment', async () => {
  const f = fixture(); const anchor = makeAnchor('a quoted sentence', 0, 2, 8);
  const r = await f.request('comment', { method: 'POST', body: { path: '/article/', message: 'My question', anchor } });
  assert.equal(r.status, 201); const body = f.mutations[0].variables.input.body;
  assert.ok(body.includes('查看划线原文')); assert.ok(body.includes('My question')); assert.ok(!JSON.stringify(r.data).includes('test-token-not-for-client'));
});
test('rate-limited writes do not create a discussion or comment', async () => {
  const f = fixture({ env: { WRITE_LIMITER: { limit: async () => ({ success: false }) } } });
  const r = await f.request('comment', { method: 'POST', body: { path: '/article/', message: 'hello' } });
  assert.equal(r.status, 429); assert.equal(f.mutations.length, 0); assert.equal(f.creates(), 0);
});
for (const option of ['foreign', 'foreignRepo', 'isReply', 'locked', 'minimized']) {
  test('reply validation prevents invalid writes: ' + option, async () => {
    const f = fixture({ [option]: option === 'foreignRepo' ? 'other/repo' : true });
    const r = await f.request('comment', { method: 'POST', body: { path: '/article/', message: 'reply', replyToId: 'root' } });
    assert.ok([400, 403].includes(r.status)); assert.equal(f.mutations.length, 0);
  });
}
test('reply mutations are scoped to the configured article and root', async () => {
  const f = fixture(); const r = await f.request('comment', { method: 'POST', body: { path: '/article/', message: '@reader reply', replyToId: 'root' } });
  assert.equal(r.status, 201); assert.deepEqual(f.mutations[0].variables.input, { discussionId: 'discussion', replyToId: 'root', body: '@reader reply' });
});
test('readers cannot impersonate author moderation', async () => {
  const f = fixture(); const r = await f.request('moderate', { method: 'POST', body: { path: '/article/', commentId: 'root', action: 'feature' } });
  assert.equal(r.status, 403); assert.equal(f.mutations.length, 0);
});
test('author selections are recorded as an author reply, not visitor metadata', async () => {
  const f = fixture({ login: 'owner' }); const r = await f.request('moderate', { method: 'POST', body: { path: '/article/', commentId: 'root', action: 'feature' } });
  assert.equal(r.status, 201); assert.equal(f.mutations[0].variables.input.replyToId, 'root');
  assert.equal(f.mutations[0].variables.input.body, '[作者精选](https://blog.example/#annotation-feature)');
});
test('author can fold a root comment through GitHub moderation', async () => {
  const f = fixture({ login: 'owner' }); const r = await f.request('moderate', { method: 'POST', body: { path: '/article/', commentId: 'root', action: 'minimize' } });
  assert.equal(r.status, 200); assert.equal(f.mutations[0].variables.input.classifier, 'OFF_TOPIC');
});
test('a moderation request never creates an empty discussion', async () => {
  const f = fixture({ login: 'owner', exists: false });
  const r = await f.request('moderate', { method: 'POST', body: { path: '/article/', commentId: 'root', action: 'feature' } });
  assert.equal(r.status, 404); assert.equal(f.creates(), 0);
});
test('network failures produce a retryable error without private data', async () => {
  const f = fixture({ unavailable: true }); const r = await f.request('discussion', { query: '?path=/article/' });
  assert.equal(r.status, 502); assert.equal(r.headers.get('Cache-Control'), 'no-store');
});

test('repeated anonymous reads share a short per-article cache', async () => {
  const f = fixture();
  await Promise.all(Array.from({ length: 5 }, () => f.request('discussion', { query: '?path=/article/' })));
  assert.equal(f.calls.filter(call => call.url.pathname === '/api/discussions').length, 1);
});

for (const body of ['null', '[]', '42']) {
  test('non-object payload is a client error: ' + body, async () => {
    const f = fixture();
    const r = await f.request('comment', { method: 'POST', body });
    assert.equal(r.status, 400);
    assert.equal(f.calls.length, 0);
  });
}

test('stored quotation keeps Markdown punctuation as literal text', () => {
  const quote = '`literal` *text* [label](value)';
  const anchor = makeAnchor(quote, 0, 0, quote.length);
  const body = quoteBody('question', anchor, origin + '/article/');
  assert.ok(body.startsWith('> ' + String.raw`\`literal\` \*text\* \[label\]\(value\)`));
});
