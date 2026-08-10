'use strict';

/**
 * Envio de e-mail via Amazon SES (alertas de status do Hub).
 * Env: AWS_REGION / CMS_S3_REGION, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY,
 *      STATUS_ALERT_FROM, STATUS_ALERT_TO
 */

const { SESClient, SendEmailCommand } = require('@aws-sdk/client-ses');

let sesClient = null;

function getRegion() {
  return (
    process.env.STATUS_ALERT_AWS_REGION ||
    process.env.CMS_S3_REGION ||
    process.env.AWS_REGION ||
    process.env.AWS_DEFAULT_REGION ||
    'us-east-2'
  );
}

function getSesClient() {
  if (!sesClient) {
    sesClient = new SESClient({ region: getRegion() });
  }
  return sesClient;
}

function alertFrom() {
  return String(process.env.STATUS_ALERT_FROM || '').trim();
}

function alertTo() {
  const raw = String(process.env.STATUS_ALERT_TO || 'suporte@leaction.com.br').trim();
  return raw
    .split(',')
    .map((e) => e.trim())
    .filter(Boolean);
}

function isSesMailConfigured() {
  return Boolean(alertFrom() && alertTo().length);
}

/**
 * @param {{ subject: string, text: string, html?: string }} opts
 */
async function sendStatusAlertEmail(opts) {
  const from = alertFrom();
  const to = alertTo();
  if (!from || !to.length) {
    throw new Error('STATUS_ALERT_FROM / STATUS_ALERT_TO não configurados');
  }

  const subject = String(opts.subject || '').trim();
  const text = String(opts.text || '').trim();
  const html = opts.html ? String(opts.html) : undefined;
  if (!subject || !text) {
    throw new Error('subject e text são obrigatórios');
  }

  const cmd = new SendEmailCommand({
    Source: from,
    Destination: { ToAddresses: to },
    Message: {
      Subject: { Data: subject, Charset: 'UTF-8' },
      Body: {
        Text: { Data: text, Charset: 'UTF-8' },
        ...(html ? { Html: { Data: html, Charset: 'UTF-8' } } : {}),
      },
    },
  });

  const result = await getSesClient().send(cmd);
  return { messageId: result.MessageId || null, to, from };
}

module.exports = {
  isSesMailConfigured,
  sendStatusAlertEmail,
  alertFrom,
  alertTo,
  getRegion,
};
