package br.com.banco.spider.config;

import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Profile;

/** Demo properties remain available for the deprecated endpoint. Beans live in SatelliteContractConfig. */
@Configuration
@Profile("local-demo")
@EnableConfigurationProperties(SegSenseDemoProperties.class)
public class SegSenseDemoConfig {}
