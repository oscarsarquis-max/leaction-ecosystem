package br.com.banco.spider.web;

import org.springframework.core.io.ClassPathResource;
import org.springframework.core.io.Resource;
import org.springframework.http.CacheControl;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;
import reactor.core.publisher.Mono;

@RestController
public class FaviconController {

  @GetMapping("/favicon.ico")
  public Mono<ResponseEntity<Resource>> favicon() {
    Resource resource = new ClassPathResource("static/favicon.svg");
    if (!resource.exists()) {
      return Mono.just(ResponseEntity.notFound().build());
    }
    return Mono.just(
        ResponseEntity.ok()
            .contentType(MediaType.parseMediaType("image/svg+xml"))
            .cacheControl(CacheControl.maxAge(java.time.Duration.ofDays(7)))
            .body(resource));
  }
}
