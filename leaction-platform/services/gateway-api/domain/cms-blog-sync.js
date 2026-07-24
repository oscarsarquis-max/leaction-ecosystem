'use strict';

/**
 * Destaques fixos do Micro-CMS — sempre os N posts mais recentes de
 * https://leaction.com.br/blog (não editáveis no admin).
 */

const axios = require('axios');

const LEACTION_BLOG_URL = 'https://leaction.com.br/blog';
const LEACTION_BLOG_BASE = 'https://leaction.com.br';
const BLOG_SLOT_COUNT = 3;
const BLOG_CACHE_TTL_SEC = Number(process.env.LEACTION_BLOG_CACHE_TTL || 1800);

const blogCache = { posts: null, fetchedAt: 0 };

function emptyBlogSlot() {
  return {
    image_url: '',
    title: '',
    description: '',
    link_url: '',
    link_text: 'Leia mais →',
    source: 'blog',
  };
}

function stripHtml(html) {
  return String(html || '')
    .replace(/<[^>]+>/g, '')
    .replace(/\s+/g, ' ')
    .trim();
}

const NAMED_ENTITIES = {
  amp: '&',
  lt: '<',
  gt: '>',
  quot: '"',
  apos: "'",
  nbsp: ' ',
  ndash: '–',
  mdash: '—',
  aacute: 'á',
  eacute: 'é',
  iacute: 'í',
  oacute: 'ó',
  uacute: 'ú',
  Aacute: 'Á',
  Eacute: 'É',
  Iacute: 'Í',
  Oacute: 'Ó',
  Uacute: 'Ú',
  atilde: 'ã',
  otilde: 'õ',
  Atilde: 'Ã',
  Otilde: 'Õ',
  ccedil: 'ç',
  Ccedil: 'Ç',
  agrave: 'à',
  Agrave: 'À',
  circ: '^',
};

function decodeEntities(text) {
  return String(text || '')
    .replace(/&#x([0-9a-fA-F]+);/g, (_, hex) => {
      const code = parseInt(hex, 16);
      return Number.isFinite(code) ? String.fromCodePoint(code) : _;
    })
    .replace(/&#(\d+);/g, (_, num) => {
      const code = Number(num);
      return Number.isFinite(code) ? String.fromCodePoint(code) : _;
    })
    .replace(/&([a-zA-Z]+);/g, (match, name) => NAMED_ENTITIES[name] || match);
}

function parseLeactionBlogPosts(html, limit = BLOG_SLOT_COUNT) {
  const posts = [];
  const pattern =
    /data-blog-post-alias="([^"]+)"[\s\S]*?background-image:\s*url\('([^']+)'\)[\s\S]*?postTitle[\s\S]*?<h3>\s*<a[^>]+>([\s\S]*?)<\/a>[\s\S]*?postDescription">([\s\S]*?)<\/div>/gi;
  const seen = new Set();
  let match;
  while ((match = pattern.exec(html)) !== null) {
    const alias = String(match[1] || '').trim();
    if (!alias || seen.has(alias)) continue;
    seen.add(alias);

    let description = decodeEntities(stripHtml(match[4]));
    if (description.length > 340) {
      description = `${description.slice(0, 337).replace(/\s+\S*$/, '')}...`;
    }

    posts.push({
      image_url: String(match[2] || '').trim(),
      title: decodeEntities(stripHtml(match[3])),
      description,
      link_url: `${LEACTION_BLOG_BASE}/${alias}`,
      link_text: 'Leia mais →',
      source: 'blog',
    });
    if (posts.length >= limit) break;
  }
  return posts;
}

async function fetchLeactionBlogPosts(limit = BLOG_SLOT_COUNT) {
  const now = Date.now() / 1000;
  const cached = Array.isArray(blogCache.posts) ? blogCache.posts : [];
  if (cached.length && now - blogCache.fetchedAt < BLOG_CACHE_TTL_SEC) {
    return cached.slice(0, limit);
  }

  try {
    const response = await axios.get(LEACTION_BLOG_URL, {
      timeout: 15000,
      headers: {
        'User-Agent': 'ActionHub-CMS/1.0 (+https://actionhub.com.br)',
        Accept: 'text/html',
      },
      // Mesmo comportamento configurável do PanelDX
      httpsAgent:
        String(process.env.CMS_BLOG_SSL_VERIFY || 'true').toLowerCase() === 'false'
          ? new (require('https').Agent)({ rejectUnauthorized: false })
          : undefined,
      validateStatus: (s) => s >= 200 && s < 400,
    });
    const posts = parseLeactionBlogPosts(String(response.data || ''), limit);
    if (posts.length) {
      blogCache.posts = posts;
      blogCache.fetchedAt = now;
      return posts;
    }
  } catch (err) {
    console.warn('[cms-blog] Falha ao sincronizar blog LeAction:', err.message);
  }

  if (cached.length) return cached.slice(0, limit);
  return [];
}

function blogPostToColumn(post) {
  return {
    image_url: post.image_url || '',
    title: post.title || '',
    description: post.description || '',
    link_url: post.link_url || '',
    link_text: post.link_text || 'Leia mais →',
    source: 'blog',
  };
}

/**
 * Injeta os 3 posts mais recentes em columns[2..4].
 * Slots 0–1 (Mesa + YouTube) permanecem editáveis.
 */
async function applyBlogPostsToLanding(landing) {
  if (!landing || typeof landing !== 'object') return landing;
  const posts = await fetchLeactionBlogPosts(BLOG_SLOT_COUNT);
  const columns = Array.isArray(landing.columns) ? [...landing.columns] : [];
  while (columns.length < 2 + BLOG_SLOT_COUNT) {
    columns.push(emptyBlogSlot());
  }

  if (posts.length) {
    for (let i = 0; i < BLOG_SLOT_COUNT; i += 1) {
      const colIdx = 2 + i;
      columns[colIdx] = posts[i] ? blogPostToColumn(posts[i]) : emptyBlogSlot();
    }
  }

  return {
    ...landing,
    columns,
    blog_sync: {
      source_url: LEACTION_BLOG_URL,
      synced_at: new Date().toISOString(),
      posts_count: posts.length,
      slot_count: BLOG_SLOT_COUNT,
    },
  };
}

/** Não persiste slots dinâmicos do blog nem metadados de sync. */
function stripBlogColumnsFromLanding(landing) {
  if (!landing || typeof landing !== 'object') return landing;
  const cleaned = { ...landing };
  delete cleaned.blog_sync;
  if (Array.isArray(cleaned.columns)) {
    cleaned.columns = cleaned.columns.slice(0, 2);
  }
  return cleaned;
}

module.exports = {
  BLOG_SLOT_COUNT,
  LEACTION_BLOG_URL,
  applyBlogPostsToLanding,
  stripBlogColumnsFromLanding,
  fetchLeactionBlogPosts,
};
