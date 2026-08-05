package br.com.banco.spider.web.controller;

import br.com.banco.spider.web.filter.TraceContextWebFilter;
import java.net.URI;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.bind.support.WebExchangeBindException;
import org.springframework.web.reactive.function.client.WebClientRequestException;
import org.springframework.web.reactive.function.client.WebClientResponseException;
import reactor.core.publisher.Mono;

@RestControllerAdvice
public class GlobalExceptionHandler {

  @ExceptionHandler(WebExchangeBindException.class)
  public Mono<ProblemDetail> handleValidation(WebExchangeBindException ex) {
    ProblemDetail pd = ProblemDetail.forStatus(HttpStatus.BAD_REQUEST);
    pd.setType(URI.create("https://spider.leaction.local/problems/validation"));
    pd.setTitle("Invalid product orchestration request");
    pd.setDetail(ex.getAllErrors().isEmpty() ? ex.getMessage() : ex.getAllErrors().getFirst().toString());
    return withTrace(pd);
  }

  @ExceptionHandler({WebClientRequestException.class, WebClientResponseException.class})
  public Mono<ProblemDetail> handleWebClient(Exception ex) {
    ProblemDetail pd = ProblemDetail.forStatus(HttpStatus.BAD_GATEWAY);
    pd.setType(URI.create("https://spider.leaction.local/problems/legacy-unavailable"));
    pd.setTitle("Legacy financial service unavailable");
    pd.setDetail(ex.getMessage());
    return withTrace(pd);
  }

  @ExceptionHandler(IllegalStateException.class)
  public Mono<ProblemDetail> handleIllegalState(IllegalStateException ex) {
    ProblemDetail pd = ProblemDetail.forStatus(HttpStatus.NOT_FOUND);
    pd.setType(URI.create("https://spider.leaction.local/problems/route-not-found"));
    pd.setTitle("Product route not found");
    pd.setDetail(ex.getMessage());
    return withTrace(pd);
  }

  @ExceptionHandler(Exception.class)
  public Mono<ProblemDetail> handleGeneric(Exception ex) {
    ProblemDetail pd = ProblemDetail.forStatus(HttpStatus.INTERNAL_SERVER_ERROR);
    pd.setType(URI.create("https://spider.leaction.local/problems/internal"));
    pd.setTitle("Unexpected orchestration error");
    pd.setDetail(ex.getMessage());
    return withTrace(pd);
  }

  private Mono<ProblemDetail> withTrace(ProblemDetail pd) {
    return Mono.deferContextual(
        ctx -> {
          ctx.getOrEmpty(TraceContextWebFilter.CONTEXT_KEY)
              .ifPresent(tp -> pd.setProperty("traceparent", tp));
          return Mono.just(pd);
        });
  }
}
