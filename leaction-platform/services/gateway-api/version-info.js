'use strict';

/**
 * Versão de release do Action Hub — lida de VERSION na raiz do leaction-platform.
 */

const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '../..');
const VERSION_FILE = path.join(ROOT, 'VERSION');
const SHA_FILE = path.join(ROOT, 'GIT_SHA');

function getVersion() {
  const fromEnv = String(
    process.env.APP_VERSION || process.env.ACTIONHUB_VERSION || ''
  ).trim();
  if (fromEnv) return fromEnv;
  try {
    return fs.readFileSync(VERSION_FILE, 'utf8').trim() || '0.0.0';
  } catch {
    return '0.0.0';
  }
}

function getGitSha() {
  for (const key of ['GIT_SHA', 'SOURCE_COMMIT', 'GITHUB_SHA', 'COMMIT_SHA']) {
    const val = String(process.env[key] || '').trim();
    if (val) return val.slice(0, 12);
  }
  try {
    return fs.readFileSync(SHA_FILE, 'utf8').trim().slice(0, 12) || 'unknown';
  } catch {
    return 'unknown';
  }
}

function versionPayload(extra = {}) {
  return {
    app: 'actionhub',
    version: getVersion(),
    git_sha: getGitSha(),
    ...extra,
  };
}

module.exports = {
  getVersion,
  getGitSha,
  versionPayload,
};
