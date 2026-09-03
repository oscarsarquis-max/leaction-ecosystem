package br.com.banco.spider.config;

import br.com.banco.spider.application.canonical.SubmitCanonicalExecutionUseCase;
import br.com.banco.spider.context.application.ContextDecisionStore;
import br.com.banco.spider.context.application.ContextIntelligenceService;
import br.com.banco.spider.context.application.ContextInputRedactor;
import br.com.banco.spider.context.application.ContextInterpretationService;
import br.com.banco.spider.context.application.ContextInterpreterPrompt;
import br.com.banco.spider.context.application.InMemoryContextDecisionStore;
import br.com.banco.spider.context.application.port.ContextInterpretationProvider;
import br.com.banco.spider.context.capability.BusinessCapabilityCatalog;
import br.com.banco.spider.context.capability.CapabilityResolver;
import br.com.banco.spider.context.capability.DeterministicCapabilityResolver;
import br.com.banco.spider.context.capability.StaticBusinessCapabilityCatalog;
import br.com.banco.spider.context.domain.BusinessIntentCatalog;
import br.com.banco.spider.context.domain.ContextConfidencePolicy;
import br.com.banco.spider.context.domain.ContextPolicyGuard;
import br.com.banco.spider.context.domain.DeterministicIntentRouter;
import br.com.banco.spider.context.domain.StaticBusinessIntentCatalog;
import br.com.banco.spider.context.planning.DeterministicExecutionPlanResolver;
import br.com.banco.spider.context.planning.ExecutionPlanCatalog;
import br.com.banco.spider.context.planning.ExecutionPlanResolver;
import br.com.banco.spider.context.planning.StaticExecutionPlanCatalog;
import br.com.banco.spider.execution.support.IdentifierGenerator;
import br.com.banco.spider.execution.support.SpiderClock;
import br.com.banco.spider.integration.outbound.ai.BedrockContextInterpretationProvider;
import br.com.banco.spider.integration.outbound.ai.ScriptedContextInterpretationProvider;
import br.com.banco.spider.operational.events.OperationalEventPublisher;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.core.io.ClassPathResource;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Conditional;
import org.springframework.context.annotation.Condition;
import org.springframework.context.annotation.ConditionContext;
import org.springframework.context.annotation.Profile;
import org.springframework.core.type.AnnotatedTypeMetadata;
import software.amazon.awssdk.core.client.config.ClientOverrideConfiguration;
import software.amazon.awssdk.core.retry.RetryPolicy;
import software.amazon.awssdk.regions.Region;
import software.amazon.awssdk.services.bedrockruntime.BedrockRuntimeAsyncClient;

@Configuration
@EnableConfigurationProperties(ContextIntelligenceProperties.class)
@ConditionalOnProperty(name = "spider.context.enabled", havingValue = "true")
public class ContextIntelligenceConfig {

  @Bean
  BusinessIntentCatalog businessIntentCatalog() {
    return new StaticBusinessIntentCatalog();
  }

  @Bean
  ContextPolicyGuard contextPolicyGuard(
      BusinessIntentCatalog catalog, ContextIntelligenceProperties properties) {
    return new ContextPolicyGuard(
        catalog, new ContextConfidencePolicy(properties.getAi().getMinimumConfidence()));
  }

  @Bean
  BusinessCapabilityCatalog businessCapabilityCatalog() {
    return new StaticBusinessCapabilityCatalog();
  }

  @Bean
  ExecutionPlanCatalog executionPlanCatalog() {
    return new StaticExecutionPlanCatalog();
  }

  @Bean
  ExecutionPlanResolver executionPlanResolver(
      ExecutionPlanCatalog planCatalog, BusinessCapabilityCatalog capabilityCatalog) {
    return new DeterministicExecutionPlanResolver(planCatalog, capabilityCatalog);
  }

  @Bean
  CapabilityResolver capabilityResolver(BusinessCapabilityCatalog catalog) {
    return new DeterministicCapabilityResolver(catalog);
  }

  @Bean
  DeterministicIntentRouter deterministicIntentRouter() {
    return new DeterministicIntentRouter();
  }

  @Bean
  ContextDecisionStore contextDecisionStore() {
    return new InMemoryContextDecisionStore();
  }

  @Bean
  ContextInterpreterPrompt contextInterpreterPrompt() throws IOException {
    ClassPathResource resource =
        new ClassPathResource("context/context-interpreter-v1.txt");
    String text =
        new String(resource.getInputStream().readAllBytes(), StandardCharsets.UTF_8);
    return new ContextInterpreterPrompt(ContextInterpreterPrompt.VERSION, text);
  }

  @Bean
  ContextInputRedactor contextInputRedactor(ContextIntelligenceProperties properties) {
    return new ContextInputRedactor(properties.getAi().getMaxInputChars());
  }

  @Bean
  ContextIntelligenceService contextIntelligenceService(
      BusinessIntentCatalog catalog,
      ContextPolicyGuard guard,
      ExecutionPlanResolver planResolver,
      CapabilityResolver capabilityResolver,
      DeterministicIntentRouter router,
      ContextDecisionStore store,
      SubmitCanonicalExecutionUseCase canonicalSubmit,
      OperationalEventPublisher events,
      IdentifierGenerator ids,
      SpiderClock clock,
      ObjectMapper mapper) {
    return new ContextIntelligenceService(
        catalog,
        guard,
        planResolver,
        capabilityResolver,
        router,
        store,
        canonicalSubmit,
        events,
        ids,
        clock,
        mapper);
  }

  @Bean
  ContextInterpretationService contextInterpretationService(
      ContextIntelligenceProperties properties,
      ObjectProvider<ContextInterpretationProvider> provider,
      ContextInterpreterPrompt prompt,
      ContextInputRedactor redactor,
      BusinessIntentCatalog catalog,
      ContextIntelligenceService context,
      OperationalEventPublisher events,
      IdentifierGenerator ids,
      SpiderClock clock) {
    return new ContextInterpretationService(
        properties,
        provider.getIfAvailable(),
        prompt,
        redactor,
        catalog,
        context,
        events,
        ids,
        clock);
  }

  @Bean(destroyMethod = "close")
  @Conditional(BedrockAiEnabledCondition.class)
  BedrockRuntimeAsyncClient contextBedrockClient(ContextIntelligenceProperties properties) {
    return BedrockRuntimeAsyncClient.builder()
        .region(Region.of(properties.getAi().getRegion()))
        .overrideConfiguration(
            ClientOverrideConfiguration.builder()
                .apiCallTimeout(properties.getAi().getTimeout())
                .apiCallAttemptTimeout(properties.getAi().getTimeout())
                .retryPolicy(RetryPolicy.none())
                .build())
        .build();
  }

  @Bean
  @Conditional(BedrockAiEnabledCondition.class)
  ContextInterpretationProvider bedrockContextInterpretationProvider(
      BedrockRuntimeAsyncClient client,
      ObjectMapper mapper,
      ContextInterpreterPrompt prompt,
      ContextIntelligenceProperties properties) {
    return new BedrockContextInterpretationProvider(
        client, mapper, prompt, properties.getAi().getModel());
  }

  @Bean
  @Profile("local-demo")
  @Conditional(ScriptedAiEnabledCondition.class)
  ContextInterpretationProvider scriptedContextInterpretationProvider() {
    return new ScriptedContextInterpretationProvider();
  }

  public static final class BedrockAiEnabledCondition implements Condition {
    @Override
    public boolean matches(
        ConditionContext context, AnnotatedTypeMetadata metadata) {
      return enabled(context)
          && "bedrock".equalsIgnoreCase(
              context.getEnvironment().getProperty(
                  "spider.context.ai.provider", "bedrock"));
    }
  }

  public static final class ScriptedAiEnabledCondition implements Condition {
    @Override
    public boolean matches(
        ConditionContext context, AnnotatedTypeMetadata metadata) {
      return enabled(context)
          && context
              .getEnvironment()
              .getProperty(
                  "spider.context.ai.scripted-enabled", Boolean.class, false)
          && "scripted".equalsIgnoreCase(
              context.getEnvironment().getProperty(
                  "spider.context.ai.provider", "bedrock"));
    }
  }

  private static boolean enabled(ConditionContext context) {
    return context
        .getEnvironment()
        .getProperty("spider.context.ai.enabled", Boolean.class, false);
  }
}
