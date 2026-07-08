async function buscarAnaliseArmazenada(pool, idColaborador) {
  const { rows } = await pool.query(
    `
    SELECT id_colaborador, hash_contexto, resultado, modelo, provider, gerado_em, atualizado_em
    FROM analises_inteligentes
    WHERE id_colaborador = $1::integer
    LIMIT 1
    `,
    [idColaborador]
  );

  return rows[0] ?? null;
}

async function salvarAnaliseArmazenada(pool, idColaborador, hashContexto, analise) {
  const { rows } = await pool.query(
    `
    INSERT INTO analises_inteligentes (
      id_colaborador,
      hash_contexto,
      resultado,
      modelo,
      provider,
      gerado_em,
      atualizado_em
    )
    VALUES ($1::integer, $2::text, $3::jsonb, $4::text, $5::text, NOW(), NOW())
    ON CONFLICT (id_colaborador)
    DO UPDATE SET
      hash_contexto = EXCLUDED.hash_contexto,
      resultado = EXCLUDED.resultado,
      modelo = EXCLUDED.modelo,
      provider = EXCLUDED.provider,
      atualizado_em = NOW()
    RETURNING gerado_em, atualizado_em
    `,
    [
      idColaborador,
      hashContexto,
      JSON.stringify(analise),
      analise.modelo ?? null,
      analise.provider ?? null,
    ]
  );

  return rows[0] ?? null;
}

module.exports = {
  buscarAnaliseArmazenada,
  salvarAnaliseArmazenada,
};
