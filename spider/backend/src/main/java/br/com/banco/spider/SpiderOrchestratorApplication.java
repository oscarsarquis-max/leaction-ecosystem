package br.com.banco.spider;

import br.com.banco.spider.config.CanonicalHttpProperties;
import br.com.banco.spider.config.CanonicalSignalHttpProperties;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.properties.EnableConfigurationProperties;

@SpringBootApplication
@EnableConfigurationProperties({CanonicalHttpProperties.class, CanonicalSignalHttpProperties.class})
public class SpiderOrchestratorApplication {

  public static void main(String[] args) {
    SpringApplication.run(SpiderOrchestratorApplication.class, args);
  }
}
