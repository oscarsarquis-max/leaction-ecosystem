package br.com.segsense.inbound.http.demo;

import br.com.segsense.application.urlcapture.CapturePublicUrlUseCase;
import br.com.segsense.application.urlcapture.ConfirmUrlCaptureUseCase;
import br.com.segsense.application.urlcapture.UrlCaptureConfirmationRecord;
import br.com.segsense.application.urlcapture.UrlCapturePublicMessages;
import br.com.segsense.application.urlcapture.UrlCaptureRecord;
import br.com.segsense.inbound.http.link.NonStoreHeaders;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.UUID;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Profile;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@Profile({"local", "test"})
@ConditionalOnProperty(name = "segsense.demo.protection-journey.enabled", havingValue = "true")
@RequestMapping("/api/v1/public/demo/url-captures")
public class PublicDemoUrlCaptureController {

  private final CapturePublicUrlUseCase capture;
  private final ConfirmUrlCaptureUseCase confirm;

  public PublicDemoUrlCaptureController(
      CapturePublicUrlUseCase capture, ConfirmUrlCaptureUseCase confirm) {
    this.capture = capture;
    this.confirm = confirm;
  }

  @PostMapping
  public ResponseEntity<Map<String, Object>> capture(@RequestBody(required = false) Map<String, String> body) {
    String url = body == null ? null : body.get("url");
    UrlCaptureRecord record = capture.execute(url);
    return ResponseEntity.ok().headers(NonStoreHeaders.of()).body(UrlCapturePublicMessages.publicProjection(record));
  }

  @GetMapping("/{id}")
  public ResponseEntity<Map<String, Object>> get(@PathVariable UUID id) {
    return ResponseEntity.ok()
        .headers(NonStoreHeaders.of())
        .body(UrlCapturePublicMessages.publicProjection(capture.require(id)));
  }

  @PostMapping("/{id}/confirmations")
  public ResponseEntity<Map<String, Object>> confirm(
      @PathVariable UUID id, @RequestBody(required = false) Map<String, Object> body) {
    UrlCaptureConfirmationRecord confirmation = confirm.execute(id, body);
    Map<String, Object> payload = new LinkedHashMap<>();
    payload.put("confirmationId", confirmation.id().toString());
    payload.put("captureId", confirmation.captureId().toString());
    payload.put("publicStatus", "CONTEXT_CONFIRMED");
    payload.put("message", "Este contexto foi confirmado para esta tentativa.");
    payload.put("nextStep", "Informe a intenção e veja as possibilidades para este contexto.");
    payload.put("confirmedAt", confirmation.confirmedAt().toString());
    payload.put("confirmedElementsJson", confirmation.confirmedElementsJson());
    payload.put("correctionsJson", confirmation.correctionsJson());
    Map<String, Object> technical = new LinkedHashMap<>();
    technical.put("confirmationId", confirmation.id().toString());
    technical.put("captureId", confirmation.captureId().toString());
    technical.put("correlationId", confirmation.correlationId());
    payload.put("technical", technical);
    return ResponseEntity.ok().headers(NonStoreHeaders.of()).body(payload);
  }
}
