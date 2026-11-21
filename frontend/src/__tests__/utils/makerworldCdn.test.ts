import { describe, expect, it } from 'vitest';
import { proxyCdn, proxyCdnUrlsInHtml } from '../../utils/makerworldCdn';

describe('proxyCdn', () => {
  it('returns empty string for empty input', () => {
    expect(proxyCdn('')).toBe('');
  });

  it('leaves non-MakerWorld URLs alone', () => {
    expect(proxyCdn('/api/v1/archives/1/project-image/foo.png')).toBe(
      '/api/v1/archives/1/project-image/foo.png',
    );
    expect(proxyCdn('https://example.com/pic.jpg')).toBe('https://example.com/pic.jpg');
  });

  it('routes MakerWorld CDN hosts through the thumbnail proxy', () => {
    const url = 'https://makerworld.bblmw.com/model_images/cover.webp';
    expect(proxyCdn(url)).toBe(
      `/api/v1/makerworld/thumbnail?url=${encodeURIComponent(url)}`,
    );
  });

  it('routes public-cdn.bblmw.com through the thumbnail proxy', () => {
    const url = 'https://public-cdn.bblmw.com/gallery/1.jpg';
    expect(proxyCdn(url)).toBe(
      `/api/v1/makerworld/thumbnail?url=${encodeURIComponent(url)}`,
    );
  });
});

describe('proxyCdnUrlsInHtml', () => {
  it('rewrites MakerWorld CDN src attributes inside HTML', () => {
    const html =
      '<p>Hi</p><img src="https://makerworld.bblmw.com/a.png"><img src="https://public-cdn.bblmw.com/b.jpg">';
    const out = proxyCdnUrlsInHtml(html);
    expect(out).toContain(
      `src="/api/v1/makerworld/thumbnail?url=${encodeURIComponent('https://makerworld.bblmw.com/a.png')}"`,
    );
    expect(out).toContain(
      `src="/api/v1/makerworld/thumbnail?url=${encodeURIComponent('https://public-cdn.bblmw.com/b.jpg')}"`,
    );
    expect(out).not.toContain('src="https://makerworld.bblmw.com/');
  });

  it('leaves non-CDN markup unchanged', () => {
    const html = '<p>No images</p><a href="https://makerworld.com/models/1">link</a>';
    expect(proxyCdnUrlsInHtml(html)).toBe(html);
  });
});
