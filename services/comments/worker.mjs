import { validAnchor, quoteBody } from '../../assets/js/annotations-model.mjs';

const GISCUS = 'https://giscus.app';
const GRAPHQL = 'https://api.github.com/graphql';
const MAX_BODY_BYTES = 20000;
const COMMENT_FIELDS = `id url bodyHTML createdAt isMinimized authorAssociation
  author { login avatarUrl url }`;
class APIError extends Error {
  constructor(status, message) { super(message); this.status = status; }
}
const json = (data, status = 200) => new Response(JSON.stringify(data), {
  status, headers: { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store' },
});

function siteURL(env) {
  const url = new URL(env.SITE_URL);
  if (url.protocol !== 'https:' && url.hostname !== '127.0.0.1' && url.hostname !== 'localhost') throw new APIError(503, '评论服务配置有误');
  return url;
}
function pagePath(value, env) {
  if (typeof value !== 'string' || !value.startsWith('/') || value.startsWith('//') || value.length > 255
      || /[?#\\\x00-\x20]/.test(value)) throw new APIError(400, '无效的文章地址');
  const site = siteURL(env);
  const url = new URL(value, site);
  if (url.origin !== site.origin || url.pathname !== value || !url.pathname.startsWith(site.pathname)) throw new APIError(400, '无效的文章地址');
  return url.pathname;
}
function termFor(path) { return path.length < 2 ? 'index' : path.slice(1).replace(/\.\w+$/, ''); }
async function upstream(url, options, fetcher) {
  let response;
  try { response = await fetcher(url, { ...options, signal: AbortSignal.timeout(12000) }); }
  catch { throw new APIError(502, '评论服务连接失败，请稍后重试'); }
  if (response.status === 429) throw new APIError(429, '请求较多，请稍后重试');
  return response;
}
async function readJSON(response) {
  try { return await response.json(); } catch { throw new APIError(502, '评论服务暂时不可用'); }
}
async function graphql(token, query, variables, fetcher) {
  const response = await upstream(GRAPHQL, { method: 'POST', headers: {
    Authorization: `Bearer ${token}`, 'Content-Type': 'application/json', 'User-Agent': 'Hex4C59-blog-comments',
  }, body: JSON.stringify({ query, variables }) }, fetcher);
  if (response.status === 401) throw new APIError(401, '登录已失效，请重新登录');
  const result = await readJSON(response);
  if (!response.ok || result.errors?.length) throw new APIError(403, '操作未完成，请确认评论权限或稍后重试');
  return result.data;
}
async function authenticate(request, fetcher) {
  const session = request.headers.get('Authorization')?.match(/^Giscus ([A-Za-z0-9+\/=_-]{8,16000})$/)?.[1];
  if (!session) throw new APIError(401, '请先使用 GitHub 登录');
  // Only the existing encrypted giscus session crosses the browser boundary.
  // The decrypted GitHub token stays in this request and is never returned or logged.
  const response = await upstream(`${GISCUS}/api/oauth/token`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ session }),
  }, fetcher);
  const payload = await readJSON(response);
  if (!response.ok || typeof payload.token !== 'string') throw new APIError(401, '登录已失效，请重新登录');
  const { viewer } = await graphql(payload.token, 'query { viewer { login avatarUrl url } }', {}, fetcher);
  if (!viewer?.login) throw new APIError(401, '请重新登录');
  return { token: payload.token, viewer };
}
async function limitedJSON(request) {
  const length = Number(request.headers.get('Content-Length'));
  if (length > MAX_BODY_BYTES) throw new APIError(413, '评论内容过长');
  const reader = request.body?.getReader();
  if (!reader) throw new APIError(400, '缺少评论内容');
  let size = 0; const chunks = [];
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    size += value.byteLength;
    if (size > MAX_BODY_BYTES) { await reader.cancel(); throw new APIError(413, '评论内容过长'); }
    chunks.push(value);
  }
  const joined = new Uint8Array(size); let offset = 0;
  for (const chunk of chunks) { joined.set(chunk, offset); offset += chunk.length; }
  try { return JSON.parse(new TextDecoder().decode(joined)); }
  catch { throw new APIError(400, '无效的请求内容'); }
}

export function createHandler(fetcher = fetch) {
  return async (request, env) => {
    const origin = request.headers.get('Origin');
    let allowed;
    try { allowed = siteURL(env).origin; } catch { return json({ error: '评论服务配置有误' }, 503); }
    if ((origin && origin !== allowed) || (request.method === 'POST' && origin !== allowed)) return json({ error: '请求来源不受支持' }, 403);
    const respond = response => {
      const headers = new Headers(response.headers);
      headers.set('Access-Control-Allow-Origin', allowed);
      headers.set('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
      headers.set('Access-Control-Allow-Headers', 'Content-Type, Authorization');
      headers.set('Vary', 'Origin'); headers.set('X-Content-Type-Options', 'nosniff');
      return new Response(response.body, { status: response.status, headers });
    };
    if (request.method === 'OPTIONS') return respond(new Response(null, { status: 204 }));
    try {
      const url = new URL(request.url);
      const route = url.pathname.replace(/\/$/, '').split('/').pop();
      if (route === 'viewer' && request.method === 'GET') {
        const { viewer } = await authenticate(request, fetcher);
        return respond(json({ viewer }));
      }
      if (route !== 'discussion' && route !== 'comment' && route !== 'moderate') throw new APIError(404, '接口不存在');
      let input;
      if (request.method === 'GET' && route === 'discussion') {
        input = { path: pagePath(url.searchParams.get('path'), env), before: url.searchParams.get('before') || '' };
        if (input.before.length > 256) throw new APIError(400, '无效的分页位置');
      } else if (request.method === 'POST' && (route === 'comment' || route === 'moderate')) {
        input = await limitedJSON(request);
        if (!input || typeof input !== 'object' || Array.isArray(input)) throw new APIError(400, '无效的请求内容');
        input.path = pagePath(input.path, env);
        const { token, viewer } = await authenticate(request, fetcher);
        if (env.WRITE_LIMITER && !(await env.WRITE_LIMITER.limit({ key: viewer.login })).success) throw new APIError(429, '发送较频繁，请稍后重试');
        input.token = token; input.viewer = viewer;
        if (route === 'moderate' && viewer.login.toLowerCase() !== env.OWNER.toLowerCase()) throw new APIError(403, '仅作者可以管理讨论');
      } else throw new APIError(405, '请求方式不受支持');
      const stub = env.ARTICLES.get(env.ARTICLES.idFromName(input.path));
      const response = await stub.fetch(new Request('https://article.internal/' + route, {
        method: 'POST', body: JSON.stringify(input), headers: { 'Content-Type': 'application/json' },
      }));
      return respond(response);
    } catch (error) { return respond(json({ error: error instanceof APIError ? error.message : '评论服务暂时不可用，请稍后重试' }, error.status || 502)); }
  };
}
export default { fetch: createHandler() };

// A per-article coordinator serializes first-comment creation. Only the GitHub
// discussion ID/number is persisted; comment text remains in Discussions.
export class ArticleComments {
  constructor(state, env, fetcher = fetch) { this.state = state; this.env = env; this.fetcher = fetcher; this.queue = Promise.resolve(); this.pages = new Map(); }
  fetch(request) {
    const result = this.queue.then(() => this.handle(request));
    this.queue = result.catch(() => {});
    return result;
  }
  async readDiscussion(path, before = '', known = null) {
    const params = new URLSearchParams({ repo: this.env.REPO, category: this.env.CATEGORY,
      term: termFor(path), last: '50', strict: 'true' });
    if (known?.number) params.set('number', String(known.number));
    if (before) params.set('before', before);
    const response = await upstream(`${GISCUS}/api/discussions?${params}`, {}, this.fetcher);
    if (response.status === 404) return null;
    if (!response.ok) throw new APIError(502, '暂时无法读取评论，请稍后重试');
    const { discussion } = await readJSON(response);
    if (!discussion || discussion.repository?.nameWithOwner.toLowerCase() !== this.env.REPO.toLowerCase()) throw new APIError(502, '评论数据不匹配');
    return discussion;
  }
  async discussionFor(path, token) {
    let known = await this.state.storage.get('discussion');
    if (known) return known;
    const discussion = await this.readDiscussion(path);
    if (discussion) {
      known = { id: discussion.id, number: Number(new URL(discussion.url).pathname.split('/').pop()) };
    } else if (token) {
      const response = await upstream(`${GISCUS}/api/discussions`, { method: 'POST', headers: {
        Authorization: `Bearer ${token}`, 'Content-Type': 'application/json',
      }, body: JSON.stringify({ repo: this.env.REPO, input: {
        repositoryId: this.env.REPO_ID, categoryId: this.env.CATEGORY_ID,
        title: termFor(path), body: `文章讨论：${new URL(path, this.env.SITE_URL).href}`,
      } }) }, this.fetcher);
      const result = await readJSON(response);
      if (!response.ok || !result.id) throw new APIError(502, '暂时无法建立讨论，请稍后重试');
      const data = await graphql(token, 'query($id:ID!){node(id:$id){... on Discussion{id number repository{nameWithOwner}}}}', { id: result.id }, this.fetcher);
      if (data.node?.repository?.nameWithOwner.toLowerCase() !== this.env.REPO.toLowerCase()) throw new APIError(502, '评论数据不匹配');
      known = { id: data.node.id, number: data.node.number };
    }
    if (known) await this.state.storage.put('discussion', known);
    return known;
  }
  async checkComment(id, discussion, token) {
    if (typeof id !== 'string' || id.length > 160) throw new APIError(400, '无效的讨论');
    const { node } = await graphql(token, `query($id:ID!){node(id:$id){... on DiscussionComment {
      id isMinimized replyTo{id} discussion{id locked repository{nameWithOwner}} }}}`, { id }, this.fetcher);
    if (!node || node.discussion?.id !== discussion.id || node.discussion.repository?.nameWithOwner.toLowerCase() !== this.env.REPO.toLowerCase() || node.replyTo) throw new APIError(400, '讨论不属于这篇文章');
    if (node.discussion.locked) throw new APIError(403, '这篇文章的讨论已关闭');
    return node;
  }
  async handle(request) {
    try {
      const input = await request.json();
      const route = new URL(request.url).pathname.slice(1);
      if (route === 'discussion') {
        const cached = this.pages.get(input.before || 'latest');
        if (cached && cached.expires > Date.now()) return json(cached.data);
        const known = await this.state.storage.get('discussion');
        const discussion = await this.readDiscussion(input.path, input.before, known);
        if (!known && discussion) await this.state.storage.put('discussion', { id: discussion.id, number: Number(new URL(discussion.url).pathname.split('/').pop()) });
        const data = { discussion };
        this.pages.set(input.before || 'latest', { data, expires: Date.now() + 15000 });
        if (this.pages.size > 16) this.pages.delete(this.pages.keys().next().value);
        return json(data);
      }
      if (route !== 'comment' && route !== 'moderate') throw new APIError(404, '接口不存在');
      if (route === 'comment') {
        if (typeof input.message !== 'string' || !input.message.trim() || input.message.length > 4000) throw new APIError(400, '请输入 1–4000 字的评论');
        if (input.anchor && !validAnchor(input.anchor)) throw new APIError(400, '划线位置无效，请重新选择');
      }
      const known = await this.discussionFor(input.path, route === 'comment' && !input.replyToId ? input.token : undefined);
      if (!known) throw new APIError(404, '讨论不存在');
      let body, replyToId = input.replyToId || null;
      if (route === 'moderate') {
        if (input.viewer.login.toLowerCase() !== this.env.OWNER.toLowerCase()) throw new APIError(403, '仅作者可以管理讨论');
        await this.checkComment(input.commentId, known, input.token);
        if (input.action === 'feature' || input.action === 'unfeature') {
          replyToId = input.commentId;
          const url = new URL(this.env.SITE_URL); url.hash = `annotation-${input.action}`;
          body = `[${input.action === 'feature' ? '作者精选' : '取消精选'}](${url.href})`;
        } else if (input.action === 'minimize' || input.action === 'restore') {
          const action = input.action === 'minimize' ? 'minimizeComment' : 'unminimizeComment';
          const type = input.action === 'minimize' ? 'MinimizeCommentInput' : 'UnminimizeCommentInput';
          await graphql(input.token, `mutation($input:${type}!){${action}(input:$input){clientMutationId}}`, {
            input: { subjectId: input.commentId, ...(input.action === 'minimize' ? { classifier: 'OFF_TOPIC' } : {}) },
          }, this.fetcher);
          this.pages.clear();
          return json({ ok: true });
        } else throw new APIError(400, '无效的管理操作');
      } else {
        if (replyToId) {
          const comment = await this.checkComment(replyToId, known, input.token);
          if (comment.isMinimized) throw new APIError(403, '这条讨论已折叠');
        }
        body = quoteBody(input.message.trim(), replyToId ? null : input.anchor, new URL(input.path, this.env.SITE_URL).href);
      }
      const data = await graphql(input.token, `mutation($input:AddDiscussionCommentInput!){addDiscussionComment(input:$input){comment{${COMMENT_FIELDS}}}}`, {
        input: { discussionId: known.id, body, ...(replyToId ? { replyToId } : {}) },
      }, this.fetcher);
      if (!data.addDiscussionComment?.comment) throw new APIError(502, '发送结果暂时无法确认，请先刷新讨论再重试');
      this.pages.clear();
      return json({ comment: data.addDiscussionComment.comment, discussion: known }, 201);
    } catch (error) { return json({ error: error instanceof APIError ? error.message : '评论服务暂时不可用，请稍后重试' }, error.status || 502); }
  }
}
