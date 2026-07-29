# Pedido inicial — LEACTIONA.COM.BR

Pipeline Phanton: `leactiona-lms-migration` · perfil `software_saas` · `single_tenant`.

## Em uma frase

Substituir o Moodle por LMS multimídia próprio (leve, responsivo, SCORM/xAPI, H5P-like, gamificação), sem billing e sem migração Moodle na v1.

## Escopo v1 (sim)

- Cursos / módulos / lições + RBAC (aluno, professor/admin)
- SCORM 2004 4ª ed. + xAPI (LRS próprio vs Learning Locker — decidir na pesquisa)
- Player interno YouTube/Vimeo + overlays interativos
- Mídia: MP4, YouTube, MP3, PDF, HTML5/SCORM/H5P
- Avaliações, certificados PDF download, gamificação
- Conteúdo gratuito vs pago via **flag de matrícula** (sem gateway)
- LGPD como requisito de 1ª classe
- Escala ~100–1.000 alunos; AWS barata; CDN/mídia conscientes

## Fora de escopo v1

- Import/ETL Moodle
- Billing / checkout / assinatura
- App nativo
- Fórum / comunidade / comentários
- Webinar / aula ao vivo
- Verificação pública de certificado (QR)
- Multi-tenant

## Destino do código

`C:\Projetos\leaction-ecosystem\leactiona` (monorepo; não `C:\Projetos\leactiona` isolado).

## Artefatos esperados do Phanton (ainda não colados aqui)

1. PRD.md  
2. SDD.md  
3. security_guidelines (se houver)  
4. Fila `module_prompts` — executar um a um nesta pasta  

Spec JSON completo: `docs/00-spec-inicial.json`.
