--
-- PostgreSQL database dump
--


-- Dumped from database version 18.4 (Debian 18.4-1.pgdg13+1)
-- Dumped by pg_dump version 18.4

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Data for Name: crm_sessoes; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.crm_sessoes VALUES ('73d3d3ba-e34d-4387-87ef-866c864fea06', 'paneldx', NULL, '4519f79c589ed12b53599421ed0b3eda978e58b3f18bcc0619503077599cf2d2', 'axios/1.12.2', '2026-07-15 11:23:57.32215+00');
INSERT INTO public.crm_sessoes VALUES ('feb4354a-fb05-4896-951e-c2215feda444', 'paneldx', NULL, '9c03328ee486fa6db0e1fda19da8d157ada6f5d0d3bef6f497f6672f11019a60', 'smoke-test', '2026-07-15 11:24:22.669393+00');
INSERT INTO public.crm_sessoes VALUES ('c4c34f56-5c8d-4427-a24e-2527e45e2064', 'paneldx', NULL, 'aed1e7e8cbf37b772edafc343980f150bd51e31dc236439b306f66c493a84e0a', 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)', '2026-07-15 11:39:37.419597+00');


--
-- Data for Name: crm_eventos; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.crm_eventos VALUES (1, '73d3d3ba-e34d-4387-87ef-866c864fea06', 'pageview', '/', 0, '2026-07-15 11:23:57.32215+00');
INSERT INTO public.crm_eventos VALUES (2, 'feb4354a-fb05-4896-951e-c2215feda444', 'pageview', '/', 0, '2026-07-15 11:24:22.669393+00');
INSERT INTO public.crm_eventos VALUES (3, 'feb4354a-fb05-4896-951e-c2215feda444', 'click_cta_mesa_inovador', '/mesa-do-inovador', 0, '2026-07-15 11:24:22.723203+00');
INSERT INTO public.crm_eventos VALUES (4, 'feb4354a-fb05-4896-951e-c2215feda444', 'pageview', '/mesa-do-inovador', 0, '2026-07-15 11:24:22.741493+00');
INSERT INTO public.crm_eventos VALUES (5, 'c4c34f56-5c8d-4427-a24e-2527e45e2064', 'pageview', '/mesa-do-inovador', 125, '2026-07-15 11:39:37.419597+00');
INSERT INTO public.crm_eventos VALUES (6, '73d3d3ba-e34d-4387-87ef-866c864fea06', 'pageview', '/', 0, '2026-07-15 11:45:23.684904+00');
INSERT INTO public.crm_eventos VALUES (7, '73d3d3ba-e34d-4387-87ef-866c864fea06', 'click_cta_mesa_inovador', 'http://localhost:3000/cadastro', 0, '2026-07-15 12:25:24.996276+00');
INSERT INTO public.crm_eventos VALUES (8, '73d3d3ba-e34d-4387-87ef-866c864fea06', 'pageview', '/cadastro', 0, '2026-07-15 12:25:25.072386+00');


--
-- Data for Name: marketplace_curation; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.marketplace_curation VALUES ('global', '[]', '[]', '["gamer", "jogo", "ps5", "xbox", "nintendo", "tv", "televisÃ£o", "televisao", "smart tv", "brinquedo", "pelÃºcia", "pelucia", "infantil"]', '2026-07-15 12:02:04.161922+00');
INSERT INTO public.marketplace_curation VALUES ('formacao', '["livro lideranÃ§a", "livro transformaÃ§Ã£o digital", "livro gestÃ£o de ti", "livro governanÃ§a corporativa", "livro inovaÃ§Ã£o estratÃ©gia"]', '["livro", "ebook", "curso", "apostila", "guia", "handbook", "gestao", "gestÃ£o", "lideranca", "lideranÃ§a", "governanca", "governanÃ§a", "inovacao", "inovaÃ§Ã£o", "management"]', '[]', '2026-07-15 12:02:04.161926+00');
INSERT INTO public.marketplace_curation VALUES ('equipamentos', '["roteador corporativo cisco", "switch rede ubiquiti", "servidor rack dell", "access point corporativo", "firewall hardware"]', '["roteador", "router", "switch", "servidor", "server", "access point", "firewall", "rack", "cisco", "ubiquiti", "dell", "tp-link", "unifi"]', '[]', '2026-07-15 12:02:04.161927+00');
INSERT INTO public.marketplace_curation VALUES ('software', '["licenÃ§a microsoft 365", "antivirus corporativo endpoint", "windows server licenÃ§a", "kaspersky endpoint"]', '["licenca", "licenÃ§a", "software", "microsoft", "365", "office", "windows server", "antivirus", "endpoint", "kaspersky"]', '[]', '2026-07-15 12:02:04.161928+00');


--
-- Data for Name: marketplace_products; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.marketplace_products VALUES ('catalog-formacao-1', 'LideranÃ§a em Tempos de TransformaÃ§Ã£o Digital', 79.90, 'BRL', 'R$ 79,90', '/marketplace/placeholders/livro.svg', 'https://lista.mercadolivre.com.br/livros-lideranca-transformacao-digital', 'catalog', 'formacao', '{formacao}', true, '2026-07-15 12:02:04.17778+00', '2026-07-15 12:02:04.177783+00');
INSERT INTO public.marketplace_products VALUES ('catalog-formacao-2', 'GestÃ£o EstratÃ©gica e InovaÃ§Ã£o Corporativa', 92.50, 'BRL', 'R$ 92,50', '/marketplace/placeholders/gestao.svg', 'https://lista.mercadolivre.com.br/livros-gestao-estrategica', 'catalog', 'formacao', '{formacao}', true, '2026-07-15 12:02:04.177785+00', '2026-07-15 12:02:04.177786+00');
INSERT INTO public.marketplace_products VALUES ('catalog-formacao-3', 'TransformaÃ§Ã£o Digital para Executivos', 68.00, 'BRL', 'R$ 68,00', '/marketplace/placeholders/digital.svg', 'https://lista.mercadolivre.com.br/livros-transformacao-digital', 'catalog', 'formacao', '{formacao}', true, '2026-07-15 12:02:04.177787+00', '2026-07-15 12:02:04.177787+00');
INSERT INTO public.marketplace_products VALUES ('catalog-formacao-4', 'Curso Online â€” Maturidade Digital Organizacional', 197.00, 'BRL', 'R$ 197,00', '/marketplace/placeholders/digital.svg', 'https://lista.mercadolivre.com.br/curso-maturidade-digital', 'catalog', 'formacao', '{formacao}', true, '2026-07-15 12:02:04.177788+00', '2026-07-15 12:02:04.177788+00');
INSERT INTO public.marketplace_products VALUES ('catalog-equip-1', 'Switch GerenciÃ¡vel Gigabit â€” Infraestrutura de Rede', 489.90, 'BRL', 'R$ 489,90', '/marketplace/placeholders/rede.svg', 'https://lista.mercadolivre.com.br/switch-gerenciavel-gigabit', 'catalog', 'equipamentos', '{equipamentos}', true, '2026-07-15 12:02:04.177789+00', '2026-07-15 12:02:04.177789+00');
INSERT INTO public.marketplace_products VALUES ('catalog-equip-2', 'Roteador Wi-Fi 6 Empresarial', 629.00, 'BRL', 'R$ 629,00', '/marketplace/placeholders/rede.svg', 'https://lista.mercadolivre.com.br/roteador-wifi-6-empresarial', 'catalog', 'equipamentos', '{equipamentos}', true, '2026-07-15 12:02:04.17779+00', '2026-07-15 12:02:04.17779+00');
INSERT INTO public.marketplace_products VALUES ('catalog-equip-3', 'Access Point Corporativo Dual Band', 399.90, 'BRL', 'R$ 399,90', '/marketplace/placeholders/rede.svg', 'https://lista.mercadolivre.com.br/access-point-corporativo', 'catalog', 'equipamentos', '{equipamentos}', true, '2026-07-15 12:02:04.177791+00', '2026-07-15 12:02:04.177792+00');
INSERT INTO public.marketplace_products VALUES ('catalog-equip-4', 'Notebook Profissional â€” Produtividade Digital', 3299.00, 'BRL', 'R$ 3.299,00', '/marketplace/placeholders/equipamento.svg', 'https://lista.mercadolivre.com.br/notebook-profissional', 'catalog', 'equipamentos', '{equipamentos}', true, '2026-07-15 12:02:04.177792+00', '2026-07-15 12:02:04.177793+00');
INSERT INTO public.marketplace_products VALUES ('catalog-sw-1', 'Microsoft 365 Business â€” LicenÃ§a Anual', 899.00, 'BRL', 'R$ 899,00', '/marketplace/placeholders/digital.svg', 'https://lista.mercadolivre.com.br/microsoft-365-business', 'catalog', 'software', '{software}', true, '2026-07-15 12:02:04.177793+00', '2026-07-15 12:02:04.177794+00');
INSERT INTO public.marketplace_products VALUES ('catalog-sw-2', 'AntivÃ­rus Corporativo Endpoint Protection', 249.90, 'BRL', 'R$ 249,90', '/marketplace/placeholders/digital.svg', 'https://lista.mercadolivre.com.br/antivirus-corporativo-endpoint', 'catalog', 'software', '{software}', true, '2026-07-15 12:02:04.177794+00', '2026-07-15 12:02:04.177795+00');
INSERT INTO public.marketplace_products VALUES ('catalog-sw-3', 'Windows Server â€” LicenÃ§a Standard', 1899.00, 'BRL', 'R$ 1.899,00', '/marketplace/placeholders/digital.svg', 'https://lista.mercadolivre.com.br/windows-server-licenca', 'catalog', 'software', '{software}', true, '2026-07-15 12:02:04.177795+00', '2026-07-15 12:02:04.177796+00');
INSERT INTO public.marketplace_products VALUES ('catalog-sw-4', 'Ferramentas de GestÃ£o e Produtividade Digital', 159.00, 'BRL', 'R$ 159,00', '/marketplace/placeholders/digital.svg', 'https://lista.mercadolivre.com.br/software-gestao-corporativa', 'catalog', 'software', '{software}', true, '2026-07-15 12:02:04.177796+00', '2026-07-15 12:02:04.177797+00');


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.users VALUES ('d8a72d5f-f5bc-4736-a8e8-4f927f06cde7', 'sistema@paneldx.com.br', 'Cliente PanelDX', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, '2026-07-09 17:13:25.829377');
INSERT INTO public.users VALUES ('08c6e87f-b7c1-4c3e-ad25-aedd02c1140b', 'sysadmin@inove4us.com.br', 'SysAdmin inove4us', 'scrypt$70fed296661251588e25e6c18edac517$2b897e83ba188660e83b866d3e50f2a6a3e6b5c5a03be45eaa714b5d4b946c23c68d9daaacba94a93813abf4ec0526cbd084d0276f41803107e7725853c31751', NULL, NULL, NULL, NULL, NULL, NULL, NULL, '2026-07-15 15:27:19.579897');


--
-- Name: crm_eventos_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.crm_eventos_id_seq', 8, true);


--
-- PostgreSQL database dump complete
--


