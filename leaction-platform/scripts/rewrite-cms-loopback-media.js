/**
 * Reescreve image_url/image_path de localhost → S3 no JSON do Micro-CMS.
 *
 *   node scripts/rewrite-cms-loopback-media.js --file=./.deploy-secrets/cms-inove4us.json
 */
'use strict';

const fs = require('fs');
const path = require('path');

require('dotenv').config({ path: path.join(__dirname, '..', '.env'), override: false });

const { rewriteLandingMedia } = require('../services/gateway-api/lib/cms-media-url');

function argValue(name) {
  const hit = process.argv.find((a) => a.startsWith(`--${name}=`));
  return hit ? hit.slice(name.length + 3).trim() : null;
}

const file = argValue('file');
if (!file) {
  console.error('Uso: node scripts/rewrite-cms-loopback-media.js --file=path.json');
  process.exit(1);
}
const abs = path.resolve(file);
const payload = JSON.parse(fs.readFileSync(abs, 'utf8'));
payload.landing_page_data = rewriteLandingMedia(payload.landing_page_data || {});
fs.writeFileSync(abs, `${JSON.stringify(payload, null, 2)}\n`, 'utf8');
console.log(`OK reescrito ${abs}`);
