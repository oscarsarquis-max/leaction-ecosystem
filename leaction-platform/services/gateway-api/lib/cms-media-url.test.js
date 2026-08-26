'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { canonicalizeCmsMediaUrl, rewriteLandingMedia } = require('./cms-media-url');

test('localhost /images vira URL S3', () => {
  assert.equal(
    canonicalizeCmsMediaUrl('http://localhost:4000/images/1786368621959-schoolplan_prof.png'),
    'https://paneldx-cms-assets-2026.s3.us-east-2.amazonaws.com/cms/1786368621959-schoolplan_prof.png'
  );
});

test('URL S3 existente permanece', () => {
  const url =
    'https://paneldx-cms-assets-2026.s3.us-east-2.amazonaws.com/cms/1786621279074-proj_pedag.png';
  assert.equal(canonicalizeCmsMediaUrl(url), url);
});

test('rewrite percorre columns e coluna1', () => {
  const out = rewriteLandingMedia({
    columns: [{ image_url: 'http://127.0.0.1:4000/images/a.png', image_path: 'http://localhost:4000/images/a.png' }],
    coluna1: { image_url: 'http://localhost:4001/images/b.png' },
  });
  assert.match(out.columns[0].image_url, /s3\.us-east-2\.amazonaws.com\/cms\/a\.png$/);
  assert.match(out.coluna1.image_url, /s3\.us-east-2\.amazonaws.com\/cms\/b\.png$/);
});
