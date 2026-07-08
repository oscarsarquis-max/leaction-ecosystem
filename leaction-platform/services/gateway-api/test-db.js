const { Pool } = require('pg');
require('dotenv').config({ path: '../../.env' }); // IMPORTANTE: Sobe dois níveis para achar o .env na raiz

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
});

async function verificarSistema() {
  try {
    console.log('🔍 Verificando conexão com o Banco LeAction...');
    const res = await pool.query('SELECT NOW()');
    console.log('✅ Node.js acessou o Postgres com sucesso!');

    const produtos = await pool.query('SELECT * FROM products');
    console.log(`📦 Encontrados ${produtos.rowCount} produtos cadastrados.`);
    
    produtos.rows.forEach(p => {
      console.log(`   - [${p.type}] SKU: ${p.sku} -> ID Externo: ${p.external_resource_id}`);
    });

    process.exit(0);
  } catch (err) {
    console.error('❌ ERRO DE CONEXÃO:', err.message);
    console.log('DICA: Verifique se o Docker está rodando e se a porta no .env é 5433.');
    process.exit(1);
  }
}

verificarSistema();