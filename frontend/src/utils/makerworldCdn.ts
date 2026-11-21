/**
 * MakerWorld CDN images can't be hotlinked — Printbuddy's img-src CSP only
 * allows ``'self' data: blob:``. Route them through the backend thumbnail
 * proxy so description HTML and explicit <img> tags actually render.
 */

const MAKERWORLD_CDN_HOST_RE = /^https?:\/\/(?:makerworld|public-cdn)\.bblmw\.com\//i;
const MAKERWORLD_CDN_URL_IN_HTML_RE =
  /(https?:\/\/(?:makerworld|public-cdn)\.bblmw\.com\/[^\s"']+)/gi;

/** Rewrite MakerWorld CDN URLs inside HTML (design summary, 3MF description). */
export function proxyCdnUrlsInHtml(html: string): string {
  return html.replace(
    MAKERWORLD_CDN_URL_IN_HTML_RE,
    (match) => `/api/v1/makerworld/thumbnail?url=${encodeURIComponent(match)}`,
  );
}

/**
 * Rewrite a single MakerWorld CDN URL for an explicit <img src>.
 * Empty string in → empty string out so ``{coverUrl && ...}`` short-circuits.
 */
export function proxyCdn(url: string): string {
  if (!url) return '';
  if (!MAKERWORLD_CDN_HOST_RE.test(url)) return url;
  return `/api/v1/makerworld/thumbnail?url=${encodeURIComponent(url)}`;
}
