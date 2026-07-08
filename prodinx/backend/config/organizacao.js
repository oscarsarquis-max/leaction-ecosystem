const ORGANIZACAO_PADRAO = {
  nome: process.env.ORGANIZACAO_NOME || "AGRO LEO",
};

function getOrganizacaoNome() {
  return ORGANIZACAO_PADRAO.nome;
}

module.exports = {
  getOrganizacaoNome,
  ORGANIZACAO_PADRAO,
};
