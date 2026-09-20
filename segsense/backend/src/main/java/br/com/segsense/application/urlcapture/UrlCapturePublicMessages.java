package br.com.segsense.application.urlcapture;

import java.util.LinkedHashMap;
import java.util.Map;

public final class UrlCapturePublicMessages {

  private UrlCapturePublicMessages() {}

  public static String of(String resultCode) {
    return switch (resultCode == null ? "" : resultCode) {
      case "FETCHED" -> "Conteúdo obtido. Confira o trecho e os elementos antes de continuar.";
      case "INVALID_URL" -> "Este endereço não pode ser usado. Use http ou https público, sem credencial na URL.";
      case "DNS_BLOCKED" -> "Este endereço não é uma página pública utilizável nesta demonstração.";
      case "TIMEOUT" -> "A página não respondeu a tempo. Você pode tentar de novo ou informar outro endereço.";
      case "REDIRECT_BLOCKED" -> "O redirecionamento desta página não é seguro para captura. Informe outro endereço.";
      case "HTTP_ERROR" -> "A página não devolveu conteúdo utilizável. Verifique o endereço.";
      case "UNSUPPORTED_CONTENT" -> "Este tipo de arquivo não é lido nesta demonstração. Use uma página em texto.";
      case "TOO_LARGE" -> "A resposta ultrapassou o limite desta demonstração. Tente uma página menor.";
      case "NO_MEANINGFUL_TEXT" ->
          "Não foi possível isolar o texto principal desta página com confiança suficiente. Cole um trecho no campo de contexto ou informe outro endereço.";
      default -> "A captura não concluiu com conteúdo utilizável.";
    };
  }

  public static Map<String, Object> publicProjection(UrlCaptureRecord record) {
    Map<String, Object> body = new LinkedHashMap<>();
    body.put("captureId", record.id().toString());
    body.put("publicStatus", publicStatus(record.resultCode()));
    body.put("message", of(record.resultCode()));
    body.put("nextStep", nextStep(record.resultCode()));
    body.put("requestedUrl", record.requestedUrl());
    body.put("finalUrl", record.finalUrl());
    body.put("finalHost", record.finalHost());
    body.put("capturedAt", record.capturedAt() == null ? null : record.capturedAt().toString());
    body.put("title", record.title());
    body.put("excerpt", record.excerpt());
    body.put("normalizedText", record.normalizedText());
    body.put("extractedElementsJson", record.extractedElementsJson());
    Map<String, Object> technical = new LinkedHashMap<>();
    technical.put("resultCode", record.resultCode());
    technical.put("httpStatus", record.httpStatus());
    technical.put("contentType", record.contentType());
    technical.put("bytesSha256", record.bytesSha256());
    technical.put("textSha256", record.textSha256());
    technical.put("extractorVersion", record.extractorVersion());
    technical.put("selectionStrategy", UrlExtractedEnvelope.readSelectionStrategy(record.extractedElementsJson()));
    technical.put("detectedLanguage", record.detectedLanguage());
    technical.put("correlationId", record.correlationId());
    body.put("technical", technical);
    return body;
  }

  private static String publicStatus(String resultCode) {
    if ("FETCHED".equals(resultCode)) {
      return "AWAITING_REVIEW";
    }
    return "CAPTURE_FAILED";
  }

  private static String nextStep(String resultCode) {
    if ("FETCHED".equals(resultCode)) {
      return "Revise o trecho extraído e confirme o contexto.";
    }
    if ("NO_MEANINGFUL_TEXT".equals(resultCode)) {
      return "Cole um trecho da página no contexto escrito ou informe outro endereço. Nada foi enviado à Spider.";
    }
    return "Corrija o endereço ou informe outro. Nada foi enviado à Spider.";
  }
}
