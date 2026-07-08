-- Extensão para gerar IDs únicos (UUID)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. TABELA DE UTILIZADORES CENTRALIZADA
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email TEXT UNIQUE NOT NULL,
    full_name TEXT NOT NULL,
    document_id TEXT,
    phone TEXT,
    company TEXT,
    address TEXT,
    city TEXT,
    state TEXT,
    moodle_user_id INTEGER, -- ID do aluno no Moodle (preenchido após a primeira matrícula)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. TABELA DE PRODUTOS (Cursos vs Assessments)
CREATE TABLE products (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    sku TEXT UNIQUE NOT NULL, -- Código identificador (ex: CURSO_GESTAO_01)
    name TEXT NOT NULL,
    type TEXT NOT NULL, -- 'MOODLE_COURSE' ou 'PANELDX_ASSESSMENT'
    external_resource_id TEXT NOT NULL -- ID do Curso no Moodle ou ID do Modelo no PanelDX
);

-- 3. TABELA DE VENDAS / TRANSAÇÕES
CREATE TABLE orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id),
    product_id UUID REFERENCES products(id),
    gateway_reference TEXT UNIQUE, -- ID da transação no Asaas/Stripe
    gateway_ref TEXT UNIQUE, -- Referência interna hub:client:order
    payment_url TEXT, -- Callback webhook do originador (PanelDX)
    external_resource_id TEXT, -- id_matu PanelDX ou recurso externo do pedido
    status TEXT DEFAULT 'PENDING', -- 'PENDING', 'PAID', 'REFUNDED'
    payment_status TEXT,
    paid_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. ASSINATURAS RECORRENTES (Mercado Pago preapproval)
CREATE TABLE subscriptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    order_id UUID REFERENCES orders(id) ON DELETE SET NULL,
    mp_preapproval_id TEXT UNIQUE,
    status TEXT NOT NULL DEFAULT 'pending',
    amount NUMERIC(10, 2) NOT NULL DEFAULT 99.00,
    currency_id TEXT NOT NULL DEFAULT 'BRL',
    frequency INTEGER NOT NULL DEFAULT 1,
    frequency_type TEXT NOT NULL DEFAULT 'months',
    reason TEXT,
    payer_email TEXT NOT NULL,
    raw_response JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Inserindo um Curso da Academy (Moodle)
INSERT INTO products (sku, name, type, external_resource_id) 
VALUES ('CURSO_LIDERANCA', 'Liderança Eficaz Academy', 'MOODLE_COURSE', '2');

-- Inserindo um Assessment do Sistema (PanelDX)
INSERT INTO products (sku, name, type, external_resource_id) 
VALUES ('PANEL_MATURIDADE', 'Diagnóstico de Maturidade DX', 'PANELDX_ASSESSMENT', 'DX_MOD_101');