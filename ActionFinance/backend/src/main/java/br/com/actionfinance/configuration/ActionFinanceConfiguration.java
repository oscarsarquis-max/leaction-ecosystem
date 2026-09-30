package br.com.actionfinance.configuration;

import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.time.Clock;
import java.time.Instant;
import java.time.ZoneId;

@Configuration
@EnableConfigurationProperties(ActionFinanceProperties.class)
public class ActionFinanceConfiguration {

    @Bean
    Clock businessClock(ActionFinanceProperties properties) {
        ZoneId zone = ZoneId.of(properties.getClock().getZone());
        String fixed = properties.getClock().getFixedInstant();
        if (fixed != null && !fixed.isBlank()) {
            return Clock.fixed(Instant.parse(fixed.trim()), zone);
        }
        return Clock.system(zone);
    }
}
