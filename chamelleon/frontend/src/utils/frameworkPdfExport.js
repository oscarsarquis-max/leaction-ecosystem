/**
 * PDF com a definição completa do framework exibida no Estúdio de Criação.
 * Inclui manifesto, dimensões, níveis, 5ª dimensão, building blocks e matriz leaf PanelDX.
 */

function escapeHtml(text) {
  return String(text ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function slugify(value) {
  return String(value || 'framework')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '') || 'framework';
}

function getBlockQuestions(block) {
  if (!block) return [];
  if (block.assessment_questions) {
    const items = [];
    if (block.assessment_questions.present) {
      items.push({ temporal: 'Presente', ...block.assessment_questions.present });
    }
    if (block.assessment_questions.future) {
      items.push({ temporal: 'Futuro', ...block.assessment_questions.future });
    }
    return items.filter((q) => q.question_text);
  }
  if (block.assessment_question?.question_text) {
    return [{ temporal: 'Presente', ...block.assessment_question }];
  }
  return [];
}

function renderDeliverables(deliverables) {
  if (!Array.isArray(deliverables) || deliverables.length === 0) {
    return '';
  }
  return `
    <div style="margin-top:8px;">
      <p style="margin:0 0 6px 0;font-size:10px;font-weight:700;text-transform:uppercase;color:#0d9488;">Entregáveis / KPIs (leaf_derv)</p>
      ${deliverables
        .map(
          (derv) => `
        <div style="margin-bottom:8px;padding:8px 10px;background:#fff;border-left:3px solid #14b8a6;">
          <p style="margin:0;font-size:12px;font-weight:600;color:#0f766e;">${escapeHtml(derv.name_derv)}</p>
          ${derv.desc_derv ? `<p style="margin:4px 0 0 0;font-size:11px;color:#475569;">${escapeHtml(derv.desc_derv)}</p>` : ''}
          ${derv.derv_defi ? `<p style="margin:4px 0 0 0;font-size:10px;color:#64748b;"><strong>Definição:</strong> ${escapeHtml(derv.derv_defi)}</p>` : ''}
          ${derv.derv_comp ? `<p style="margin:4px 0 0 0;font-size:10px;color:#64748b;"><strong>Composição:</strong> ${escapeHtml(derv.derv_comp)}</p>` : ''}
          ${derv.derv_metr ? `<p style="margin:4px 0 0 0;font-size:10px;color:#0d9488;"><strong>KPI:</strong> ${escapeHtml(derv.derv_metr)}</p>` : ''}
        </div>`,
        )
        .join('')}
    </div>`;
}

function renderMethodologyBlocks(blocks) {
  if (!blocks?.length) return '';
  return blocks
    .map(
      (bloc) => `
      <article style="margin:8px 0;padding:10px;border:1px solid #e2e8f0;background:#f8fafc;">
        <p style="margin:0;font-size:12px;font-weight:600;color:#0f172a;">${escapeHtml(bloc.name_bloc)}</p>
        ${bloc.desc_bloc ? `<p style="margin:6px 0 0 0;font-size:11px;color:#475569;line-height:1.45;">${escapeHtml(bloc.desc_bloc)}</p>` : ''}
        ${bloc.level_bloc != null ? `<p style="margin:4px 0 0 0;font-size:10px;color:#64748b;">Nível do bloco: ${escapeHtml(bloc.level_bloc)}</p>` : ''}
        ${bloc.quali_bloc ? `<p style="margin:4px 0 0 0;font-size:10px;color:#64748b;">Qualificação: ${escapeHtml(bloc.quali_bloc)}</p>` : ''}
        ${renderDeliverables(bloc.deliverables)}
      </article>`,
    )
    .join('');
}

function renderMethodologyDomains(domains) {
  if (!domains?.length) return '';
  return domains
    .map(
      (dom) => `
      <div style="margin-bottom:14px;">
        <h4 style="margin:0 0 6px 0;font-size:12px;color:#0f766e;">
          ${escapeHtml(dom.domain_key || '')} — ${escapeHtml(dom.name_doma)}
        </h4>
        ${dom.desc_doma ? `<p style="margin:0 0 6px 0;font-size:11px;color:#64748b;">${escapeHtml(dom.desc_doma)}</p>` : ''}
        ${renderMethodologyBlocks(dom.blocks)}
      </div>`,
    )
    .join('');
}

function renderMethodologyDimension(dim, title) {
  if (!dim) return '';
  return `
    <section style="margin-bottom:24px;">
      <h2 style="margin:0 0 10px 0;font-size:15px;color:#0f766e;border-bottom:2px solid #99f6e4;padding-bottom:4px;">
        ${escapeHtml(title)}: ${escapeHtml(dim.name_dime || dim.dimension_key || '')}
      </h2>
      ${dim.desc_dime ? `<p style="margin:0 0 8px 0;font-size:12px;color:#334155;">${escapeHtml(dim.desc_dime)}</p>` : ''}
      ${dim.long_description ? `<p style="margin:0 0 10px 0;font-size:11px;color:#475569;line-height:1.5;">${escapeHtml(dim.long_description)}</p>` : ''}
      ${renderMethodologyDomains(dim.domains)}
    </section>`;
}

/** Seções espelhando exatamente o formulário em tela. */
function renderScreenProposal(proposal) {
  const op = proposal.operational_dimension || {};
  const manifest = proposal.manifest || {};
  const blocks = op.building_blocks || [];

  const universalList = (proposal.universal_dimensions || [])
    .map(
      (dim) =>
        `<li style="margin-bottom:4px;"><strong>${escapeHtml(dim.name)}</strong> <span style="color:#64748b;">(${escapeHtml(dim.key?.toUpperCase())}) — ${escapeHtml(dim.label)}</span></li>`,
    )
    .join('');

  const maturity = (proposal.maturity_levels || [])
    .map(
      (level) => `
      <div style="margin-bottom:10px;padding:10px;border:1px solid #e2e8f0;background:#f8fafc;">
        <p style="margin:0 0 4px 0;font-size:11px;font-weight:700;color:#0d9488;">Nível ${escapeHtml(level.level)}</p>
        <p style="margin:0 0 4px 0;font-size:13px;font-weight:600;">${escapeHtml(level.name)}</p>
        <p style="margin:0;font-size:11px;color:#475569;line-height:1.45;">${escapeHtml(level.description)}</p>
      </div>`,
    )
    .join('');

  const buildingBlocks = blocks
    .map((block) => {
      const questions = getBlockQuestions(block);
      const questionsHtml = questions.length
        ? questions
            .map(
              (q) => `
            <p style="margin:8px 0 0 0;font-size:10px;font-weight:700;color:#64748b;text-transform:uppercase;">${escapeHtml(q.temporal)}</p>
            <p style="margin:2px 0 0 0;font-size:11px;color:#334155;">${escapeHtml(q.question_text)}</p>`,
            )
            .join('')
        : '';

      return `
      <article style="margin-bottom:12px;padding:12px;border:1px solid #cbd5e1;background:#f8fafc;">
        <p style="margin:0 0 8px 0;font-size:11px;font-weight:700;text-transform:uppercase;color:#0f766e;">
          ${escapeHtml(block.domain_key)} — ${escapeHtml(block.domain_name)}
        </p>
        <p style="margin:0 0 4px 0;font-size:10px;color:#64748b;">Nome do bloco (leaf_bloc)</p>
        <p style="margin:0 0 8px 0;font-size:13px;font-weight:600;color:#0f172a;">${escapeHtml(block.block_name || '—')}</p>
        ${
          block.block_description
            ? `<p style="margin:0 0 4px 0;font-size:10px;color:#64748b;">Descrição do bloco</p>
               <p style="margin:0 0 8px 0;font-size:11px;color:#475569;line-height:1.45;">${escapeHtml(block.block_description)}</p>`
            : ''
        }
        ${questionsHtml}
      </article>`;
    })
    .join('');

  const snippets = (proposal.research_snippets || [])
    .map(
      (s) =>
        `<li style="margin-bottom:6px;font-size:11px;"><strong>${escapeHtml(s.title || 'Referência')}</strong><br/>
         <span style="color:#0d9488;word-break:break-all;">${escapeHtml(s.url || '')}</span>
         ${s.snippet ? `<br/><span style="color:#64748b;">${escapeHtml(s.snippet)}</span>` : ''}
        </li>`,
    )
    .join('');

  const sourceUrls = (proposal.sources || []).map(
    (url) => `<li style="word-break:break-all;font-size:11px;">${escapeHtml(url)}</li>`,
  );

  return `
    <section style="margin-bottom:22px;">
      <h2 style="margin:0 0 10px 0;font-size:15px;color:#0f766e;">Fontes pesquisadas</h2>
      ${snippets ? `<ul style="margin:0;padding-left:18px;">${snippets}</ul>` : ''}
      ${sourceUrls.length ? `<ul style="margin:8px 0 0 0;padding-left:18px;">${sourceUrls.join('')}</ul>` : ''}
      ${!snippets && !sourceUrls.length ? '<p style="font-size:11px;color:#94a3b8;">Sem fontes registradas.</p>' : ''}
    </section>

    <section style="margin-bottom:22px;">
      <h2 style="margin:0 0 10px 0;font-size:15px;color:#0f766e;">Dimensões universais (imutáveis)</h2>
      <ul style="margin:0;padding-left:18px;">${universalList || '<li>—</li>'}</ul>
    </section>

    <section style="margin-bottom:22px;">
      <h2 style="margin:0 0 10px 0;font-size:15px;color:#0f766e;">5ª dimensão — core operacional</h2>
      <table style="width:100%;border-collapse:collapse;font-size:12px;">
        <tr><td style="padding:4px 8px 4px 0;color:#64748b;width:120px;">Nome</td><td style="padding:4px 0;font-weight:600;">${escapeHtml(op.name)}</td></tr>
        <tr><td style="padding:4px 8px 4px 0;color:#64748b;">Sigla</td><td style="padding:4px 0;">${escapeHtml(op.acronym)}</td></tr>
        <tr><td style="padding:4px 8px 4px 0;color:#64748b;">Rótulo completo</td><td style="padding:4px 0;">${escapeHtml(op.full_label)}</td></tr>
        <tr><td style="padding:4px 8px 4px 0;color:#64748b;vertical-align:top;">Descrição</td><td style="padding:4px 0;line-height:1.45;">${escapeHtml(op.description)}</td></tr>
      </table>
    </section>

    <section style="margin-bottom:22px;">
      <h2 style="margin:0 0 10px 0;font-size:15px;color:#0f766e;">Manifesto do framework</h2>
      <p style="margin:0 0 6px 0;font-size:13px;font-weight:600;">${escapeHtml(manifest.name)}</p>
      <p style="margin:0;font-size:12px;line-height:1.5;color:#334155;">${escapeHtml(manifest.descricao)}</p>
    </section>

    <section style="margin-bottom:22px;">
      <h2 style="margin:0 0 10px 0;font-size:15px;color:#0f766e;">Níveis de maturidade</h2>
      ${maturity || '<p style="color:#94a3b8;">—</p>'}
    </section>

    <section style="margin-bottom:22px;">
      <h2 style="margin:0 0 10px 0;font-size:15px;color:#0f766e;">Building blocks — 9 domínios operacionais</h2>
      ${buildingBlocks || '<p style="color:#94a3b8;">Nenhum bloco definido.</p>'}
    </section>`;
}

function buildFrameworkPdfHtml(proposal, { sector = '' } = {}) {
  const manifest = proposal?.manifest || {};
  const structure = proposal?.methodology_structure;
  const sectorLabel = proposal?.sector || sector || '—';
  const frameworkId = proposal?.framework_id_preview || proposal?.framework_id || '—';
  const generatedAt = new Date().toLocaleString('pt-BR');

  const universalMethodology = (structure?.universal_dimensions || [])
    .map((dim) => renderMethodologyDimension(dim, 'Matriz PanelDX — dimensão universal'))
    .join('');

  const sectorMethodology = structure?.sector_dimension
    ? renderMethodologyDimension(
        structure.sector_dimension,
        `5ª dimensão setorial (substitui ${structure.replaces_dimension_key || 'LA'} no modelo PanelDX)`,
      )
    : '';

  return `
    <div id="framework-pdf-root" style="font-family:Segoe UI,Helvetica,Arial,sans-serif;color:#0f172a;padding:28px 32px;width:750px;background:#ffffff;">
      <header style="margin-bottom:22px;padding-bottom:12px;border-bottom:3px solid #14b8a6;">
        <p style="margin:0;font-size:10px;letter-spacing:0.14em;text-transform:uppercase;color:#0d9488;">Chamelleon — Definição do Framework</p>
        <h1 style="margin:8px 0 4px 0;font-size:20px;color:#0f766e;">${escapeHtml(manifest.name || 'Framework setorial')}</h1>
        <p style="margin:0;font-size:12px;color:#475569;">Setor: <strong>${escapeHtml(sectorLabel)}</strong></p>
        <p style="margin:4px 0 0 0;font-size:12px;color:#475569;">ID: <strong>${escapeHtml(frameworkId)}</strong></p>
        <p style="margin:6px 0 0 0;font-size:10px;color:#94a3b8;">Exportado em ${escapeHtml(generatedAt)}</p>
      </header>

      ${renderScreenProposal(proposal)}

      ${
        universalMethodology
          ? `<section style="margin-top:28px;padding-top:16px;border-top:2px dashed #cbd5e1;">
               <h2 style="margin:0 0 12px 0;font-size:16px;color:#0f766e;">Anexo — estrutura metodológica PanelDX (leaf_bloc / leaf_derv)</h2>
               <p style="margin:0 0 16px 0;font-size:11px;color:#64748b;">Blocos metodológicos e entregáveis (leaf_bloc / leaf_derv) das dimensões canônicas SV, HC, FS e DA. A dimensão LA do modelo PanelDX é substituída pela 5ª dimensão setorial abaixo.</p>
               ${universalMethodology}
             </section>`
          : ''
      }

      ${sectorMethodology ? `<div style="margin-top:16px;">${sectorMethodology}</div>` : ''}

      <footer style="margin-top:32px;padding-top:10px;border-top:1px solid #e2e8f0;font-size:9px;color:#94a3b8;text-align:center;">
        Documento gerado a partir da definição exibida no Estúdio de Criação · Chamelleon
      </footer>
    </div>`;
}

function openPrintablePdf(html, filename) {
  const printWindow = window.open('', '_blank', 'noopener,noreferrer');
  if (!printWindow) {
    throw new Error('Permita pop-ups do navegador para exportar o PDF.');
  }
  printWindow.document.open();
  printWindow.document.write(`<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8" />
  <title>${escapeHtml(filename)}</title>
  <style>
    @page { margin: 12mm; }
    body { margin: 0; background: #fff; }
    @media print { body { -webkit-print-color-adjust: exact; print-color-adjust: exact; } }
  </style>
</head>
<body>${html}</body>
</html>`);
  printWindow.document.close();
  printWindow.focus();
  setTimeout(() => {
    printWindow.print();
  }, 400);
}

/**
 * @param {object} proposal
 * @param {{ sector?: string }} options
 */
export async function exportFrameworkDefinitionPdf(proposal, { sector = '' } = {}) {
  if (!proposal) {
    throw new Error('Nenhuma proposta de framework para exportar.');
  }

  const html = buildFrameworkPdfHtml(proposal, { sector });
  const sectorSlug = slugify(proposal.sector || sector);
  const dateSlug = new Date().toISOString().slice(0, 10);
  const filename = `chamelleon-framework-${sectorSlug}-${dateSlug}.pdf`;

  const mount = document.createElement('div');
  mount.id = 'framework-pdf-mount';
  mount.style.cssText =
    'position:fixed;left:0;top:0;width:794px;max-height:100vh;overflow:visible;z-index:2147483646;background:#fff;pointer-events:none;opacity:0.01;';
  mount.innerHTML = html;
  document.body.appendChild(mount);

  const root = mount.querySelector('#framework-pdf-root');
  if (!root) {
    document.body.removeChild(mount);
    openPrintablePdf(html, filename);
    return `${filename} (via impressão)`;
  }

  await new Promise((resolve) => {
    requestAnimationFrame(() => requestAnimationFrame(resolve));
  });

  try {
    const html2pdf = (await import('html2pdf.js')).default;
    await html2pdf()
      .set({
        margin: [8, 8, 8, 8],
        filename,
        image: { type: 'jpeg', quality: 0.98 },
        html2canvas: {
          scale: 2,
          useCORS: true,
          logging: false,
          scrollX: 0,
          scrollY: 0,
          windowWidth: 794,
        },
        jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' },
        pagebreak: { mode: ['css', 'legacy'] },
      })
      .from(root)
      .save();
  } catch {
    openPrintablePdf(html, filename);
    return `${filename} (via impressão)`;
  } finally {
    if (mount.parentNode) {
      document.body.removeChild(mount);
    }
  }

  return filename;
}
