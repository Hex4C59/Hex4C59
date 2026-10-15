// Stored in a normal GitHub comment link, so annotations remain portable.
export const ANCHOR_PREFIX = '#annotation=';
export const MAX_QUOTE = 1000;

export function validAnchor(value) {
  return !!value && value.v === 1 && typeof value.id === 'string' && /^[\w-]{8,64}$/.test(value.id)
    && typeof value.quote === 'string' && value.quote.trim().length > 0 && value.quote.length <= MAX_QUOTE
    && ['prefix', 'suffix'].every(key => typeof value[key] === 'string' && value[key].length <= 64)
    && Number.isInteger(value.block) && value.block >= 0 && value.block < 100000
    && Number.isInteger(value.start) && value.start >= 0 && value.start < 1000000
    && typeof value.blockKey === 'string' && value.blockKey.length <= 32;
}

export function encodeAnchor(anchor) {
  if (!validAnchor(anchor)) throw new Error('无效的划线位置');
  return btoa(String.fromCharCode(...new TextEncoder().encode(JSON.stringify(anchor))))
    .replaceAll('+', '-').replaceAll('/', '_').replace(/=+$/, '');
}

export function decodeAnchor(encoded) {
  if (typeof encoded !== 'string' || encoded.length > 8000 || !/^[\w-]+$/.test(encoded)) return null;
  try {
    const bytes = Uint8Array.from(atob(encoded.replaceAll('-', '+').replaceAll('_', '/')), char => char.charCodeAt(0));
    const anchor = JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(bytes));
    return validAnchor(anchor) ? anchor : null;
  } catch { return null; }
}

export function textKey(text) {
  let hash = 2166136261;
  for (const char of text) hash = Math.imul(hash ^ char.codePointAt(0), 16777619);
  return (hash >>> 0).toString(36);
}

export function makeAnchor(text, block, start, end, id = crypto.randomUUID()) {
  return { v: 1, id, quote: text.slice(start, end), prefix: text.slice(Math.max(0, start - 48), start),
    suffix: text.slice(end, end + 48), block, start, blockKey: textKey(text) };
}

// Resolve against exact text and surrounding context. Ambiguous matches stay detached.
export function resolveAnchor(anchor, blocks) {
  if (!validAnchor(anchor)) return null;
  const candidates = [];
  blocks.forEach((block, index) => {
    const text = typeof block === 'string' ? block : block.text;
    let from = 0;
    while (from <= text.length) {
      const start = text.indexOf(anchor.quote, from);
      if (start < 0) break;
      const end = start + anchor.quote.length;
      const prefix = anchor.prefix && text.slice(Math.max(0, start - anchor.prefix.length), start) === anchor.prefix;
      const suffix = anchor.suffix && text.slice(end, end + anchor.suffix.length) === anchor.suffix;
      const sameBlock = textKey(text) === anchor.blockKey;
      const score = (prefix ? 8 : 0) + (suffix ? 8 : 0) + (sameBlock ? 4 : 0)
        + (sameBlock && anchor.start === start ? 2 : 0);
      candidates.push({ index, start, end, score });
      from = start + Math.max(1, anchor.quote.length);
    }
  });
  candidates.sort((a, b) => b.score - a.score);
  if (!candidates.length || (candidates.length > 1 && candidates[0].score === candidates[1].score)) return null;
  if (candidates.length > 1 && !candidates[0].score) return null;
  return candidates[0];
}

export function quoteBody(message, anchor, pageURL) {
  if (!anchor) return message;
  if (!validAnchor(anchor)) throw new Error('无效的划线位置');
  const url = new URL(pageURL);
  url.search = '';
  url.hash = ANCHOR_PREFIX + encodeAnchor(anchor);
  return `${anchor.quote.split(/\r?\n/).map(line => '> ' + line.replace(/([\\`*_[\]{}()#+.!<>~|])/g, '\\$1')).join('\n')}\n\n[查看划线原文](${url.href})\n\n${message}`;
}
