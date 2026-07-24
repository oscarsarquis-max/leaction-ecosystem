'use strict';

const fs = require('fs');
const path = require('path');
const multer = require('multer');
const cmsS3 = require('../lib/cms-s3-storage');
const { createRequireAdminAuth } = require('../admin/auth');

const CMS_IMAGES_DIR = path.join(__dirname, '..', 'cms-uploads', 'images');
fs.mkdirSync(CMS_IMAGES_DIR, { recursive: true });

const cmsImageStorage = cmsS3.isCmsS3Enabled()
  ? multer.memoryStorage()
  : multer.diskStorage({
      destination: (_req, _file, cb) => cb(null, CMS_IMAGES_DIR),
      filename: (_req, file, cb) => {
        cb(null, cmsS3.buildCmsFilename(file.originalname));
      },
    });

const cmsImageUpload = multer({
  storage: cmsImageStorage,
  limits: { fileSize: 5 * 1024 * 1024 },
  fileFilter: (_req, file, cb) => {
    if (file.mimetype && file.mimetype.startsWith('image/')) {
      cb(null, true);
      return;
    }
    cb(new Error('Apenas arquivos de imagem são permitidos.'));
  },
});

/**
 * Upload de imagens do CMS (posts + Micro-CMS).
 * Mesmo contrato do PanelDX: field `imagem` → { success, url, public_url, storage }
 *
 * @param {import('express').Express} app
 * @param {{ jwtSecret?: string }} [options]
 */
function registerCmsUploadRoutes(app, options = {}) {
  const requireAdmin = createRequireAdminAuth(options.jwtSecret || process.env.JWT_SECRET);

  // Serve local fallback (dev sem S3)
  app.get('/images/:filename', async (req, res, next) => {
    const filename = path.basename(String(req.params.filename || ''));
    if (!filename || filename.includes('..')) {
      return res.status(400).json({ error: 'Arquivo inválido' });
    }
    const localPath = path.join(CMS_IMAGES_DIR, filename);
    if (fs.existsSync(localPath)) {
      return res.sendFile(localPath);
    }
    if (cmsS3.isCmsS3Enabled()) {
      try {
        const exists = await cmsS3.cmsObjectExists(filename);
        if (exists) {
          return res.redirect(302, cmsS3.getPublicUrlForFilename(filename));
        }
      } catch (err) {
        console.warn('[cms-upload] HeadObject:', err.message);
      }
    }
    return next();
  });

  function handleCmsImageUpload(req, res) {
    cmsImageUpload.single('imagem')(req, res, async (err) => {
      if (err) {
        const message =
          err.code === 'LIMIT_FILE_SIZE'
            ? 'Imagem muito grande. Limite: 5 MB.'
            : err.message || 'Falha no upload.';
        return res.status(400).json({ success: false, error: message });
      }
      if (!req.file) {
        return res.status(400).json({ success: false, error: 'Nenhum arquivo enviado.' });
      }

      try {
        if (cmsS3.isCmsS3Enabled()) {
          const uploaded = await cmsS3.uploadCmsImage(
            req.file.buffer,
            req.file.mimetype,
            req.file.originalname
          );
          console.log(`📤 [CMS Upload S3] ${req.file.originalname} -> ${uploaded.publicUrl}`);
          return res.json({
            success: true,
            // Posts do Hub preferem URL absoluta (satélites); Micro-CMS usa url relativa.
            url: uploaded.persistedUrl,
            public_url: uploaded.publicUrl,
            storage: 's3',
          });
        }

        const url = cmsS3.getCmsPersistedUrl(req.file.filename);
        const publicBase = (
          process.env.ACTION_HUB_PUBLIC_URL ||
          process.env.HUB_PUBLIC_URL ||
          `http://127.0.0.1:${process.env.GATEWAY_PORT || 4001}`
        ).replace(/\/$/, '');
        console.log(`📤 [CMS Upload local] ${req.file.originalname} -> ${url}`);
        return res.json({
          success: true,
          url,
          public_url: `${publicBase}${url}`,
          storage: 'local',
        });
      } catch (uploadErr) {
        console.error('[CMS Upload] Erro:', uploadErr.message);
        return res.status(500).json({
          success: false,
          error: 'Falha ao persistir imagem do CMS.',
        });
      }
    });
  }

  // Aliases alinhados ao PanelDX + path Hub
  app.post('/api/admin/cms/upload', requireAdmin, handleCmsImageUpload);
  app.post('/admin/cms/upload', requireAdmin, handleCmsImageUpload);
  app.post('/api/admin/upload', requireAdmin, handleCmsImageUpload);
}

module.exports = { registerCmsUploadRoutes };
