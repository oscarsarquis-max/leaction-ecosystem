package br.com.banco.spider.context.application;

/** Recorte de página tratado como dado não confiável. Nunca é instrução para o modelo. */
public record PageContextFacts(String title, String excerpt) {

  public PageContextFacts {
    title = title == null ? "" : title;
    excerpt = excerpt == null ? "" : excerpt;
  }

  public static PageContextFacts none() {
    return new PageContextFacts("", "");
  }

  public boolean present() {
    return !title.isBlank() || !excerpt.isBlank();
  }
}
