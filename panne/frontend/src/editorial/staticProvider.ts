import leftImage from "../../images/aprovados/horizontal-claro.png";
import rightImage from "../../images/aprovados/compacto-escuro.png";
import type { LoginEditorialContentProvider } from "./provider";
import { sanitizePayload } from "./sanitize";
import type { LoginEditorialPayload } from "./schema";
import { EDITORIAL_SCHEMA_VERSION } from "./schema";

const STATIC: LoginEditorialPayload = {
  schema_version: EDITORIAL_SCHEMA_VERSION,
  source: "static",
  columns: [
    {
      schema_version: EDITORIAL_SCHEMA_VERSION,
      placement: "left",
      locale: "pt-BR",
      eyebrow: "Oficina",
      title: "O turno cabe no quadro",
      summary: "A Panne organiza produção, componentes e conformidade no mesmo recorte da padaria.",
      sections: [
        "Contexto do turno antes dos filtros.",
        "Próxima ação por estado e permissão.",
        "Custos ficam fora do chão de fábrica.",
      ],
      image: { url: leftImage, alt: "Marca Panne em fundo claro, usada como imagem editorial de teste." },
      priority: 10,
      hash: "editorial-left-v1",
    },
    {
      schema_version: EDITORIAL_SCHEMA_VERSION,
      placement: "right",
      locale: "pt-BR",
      eyebrow: "Atelier",
      title: "Ficha antes do palpite",
      summary: "Ingrediente, receita e rótulo candidato passam por versão e revisão humana.",
      sections: [
        "Ausência não é zero.",
        "Assistente orienta, não executa.",
        "Estoque não inventa valor contábil.",
      ],
      image: { url: rightImage, alt: "Símbolo compacto da Panne em grafite." },
      priority: 9,
      hash: "editorial-right-v1",
    },
  ],
};

export class StaticLoginEditorialProvider implements LoginEditorialContentProvider {
  constructor(private readonly mode: "ok" | "invalid" | "unavailable" = "ok") {}

  async load(): Promise<LoginEditorialPayload | null> {
    if (this.mode === "unavailable") return null;
    if (this.mode === "invalid") return sanitizePayload({ schema_version: 1, columns: [{ title: "" }] });
    return sanitizePayload(STATIC);
  }
}
