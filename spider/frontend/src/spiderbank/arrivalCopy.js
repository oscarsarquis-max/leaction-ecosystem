export function directArrivalNarrative() {
  return {
    banner: "Você chegou diretamente ao SpiderBank.",
    lead: "Você chegou diretamente ao SpiderBank. Conte-nos o que precisa resolver.",
    status: "entrada direta",
    content: "sem origem de parceiro",
    human: "Você chegou diretamente ao SpiderBank.",
    captured: false,
    partnerName: null,
    direct: true,
  };
}

export function arrivalNarrative(page = {}, partnerName = "CampoAberto") {
  const captured = page.acquisitionStatus === "CAPTURED";
  const title = page.sourceTitle || "";
  if (!captured) {
    return {
      banner: "Você chegou a partir de um contexto.",
      lead: "Ainda não identificamos a página de origem. O momento mínimo foi criado após o clique, sem inventar a reportagem.",
      status: "origem não identificada",
      content: "não adquirida — o SpiderBank não inventa a página",
      human: "Ainda não identificamos de onde você veio.",
      captured: false,
      partnerName,
    };
  }
  const cropFailure = /quebra de safra|continuidade da produção|safra/i.test(title);
  return {
    banner: "Você chegou a partir de um contexto.",
    lead: cropFailure
      ? "Você chegou a partir de um conteúdo sobre os impactos da quebra de safra na continuidade da produção."
      : `Você chegou a partir de: ${title}`,
    status: "Já sabemos de onde você veio.",
    content: title,
    human: "Já sabemos de onde você veio.",
    captured: true,
    partnerName,
  };
}
