package br.com.banco.spider.context.application;

/** Prompt versionado e testável; não contém contexto do usuário. */
public record ContextInterpreterPrompt(String version, String text) {
  public static final String VERSION = "CTX-INTERPRETER-1.0";
}
