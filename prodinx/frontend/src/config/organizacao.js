const ORGANIZACAO_PADRAO = {
  nome: "AGRO LEO",
};

/**
 * Nome da organização exibido na interface.
 * Futuro: derivar do login/sessão do usuário.
 */
export function getOrganizacaoNome() {
  return ORGANIZACAO_PADRAO.nome;
}

export function getOrganizacao() {
  return { ...ORGANIZACAO_PADRAO };
}
