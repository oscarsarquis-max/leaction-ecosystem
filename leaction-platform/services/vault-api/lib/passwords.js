'use strict';

const bcrypt = require('bcryptjs');

const ROUNDS = 12;

function hashPassword(password) {
  return bcrypt.hashSync(String(password), ROUNDS);
}

function verifyPassword(password, stored) {
  if (!stored || typeof stored !== 'string') return false;
  try {
    return bcrypt.compareSync(String(password), stored);
  } catch {
    return false;
  }
}

module.exports = { hashPassword, verifyPassword };
