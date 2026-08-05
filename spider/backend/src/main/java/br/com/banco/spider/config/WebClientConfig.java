package br.com.banco.spider.config;

import io.netty.channel.ChannelOption;
import java.time.Duration;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.client.reactive.ReactorClientHttpConnector;
import org.springframework.http.codec.json.Jackson2JsonDecoder;
import org.springframework.http.codec.json.Jackson2JsonEncoder;
import org.springframework.web.reactive.function.client.ExchangeStrategies;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.netty.http.client.HttpClient;

@Configuration
public class WebClientConfig {

  @Bean
  WebClient.Builder webClientBuilder(
      @Value("${spider.http.connect-timeout-ms:2000}") int connectTimeoutMs,
      @Value("${spider.http.response-timeout-ms:3000}") int responseTimeoutMs) {

    HttpClient httpClient =
        HttpClient.create()
            .option(ChannelOption.CONNECT_TIMEOUT_MILLIS, connectTimeoutMs)
            .responseTimeout(Duration.ofMillis(responseTimeoutMs));

    ExchangeStrategies strategies =
        ExchangeStrategies.builder()
            .codecs(
                configurer -> {
                  configurer.defaultCodecs().jackson2JsonEncoder(new Jackson2JsonEncoder());
                  configurer.defaultCodecs().jackson2JsonDecoder(new Jackson2JsonDecoder());
                  configurer.defaultCodecs().maxInMemorySize(1024 * 1024);
                })
            .build();

    return WebClient.builder()
        .clientConnector(new ReactorClientHttpConnector(httpClient))
        .exchangeStrategies(strategies);
  }
}
