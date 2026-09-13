package br.com.segsense.architecture;

import static com.tngtech.archunit.lang.syntax.ArchRuleDefinition.classes;
import static com.tngtech.archunit.lang.syntax.ArchRuleDefinition.noClasses;

import com.tngtech.archunit.core.importer.ImportOption;
import com.tngtech.archunit.junit.AnalyzeClasses;
import com.tngtech.archunit.junit.ArchTest;
import com.tngtech.archunit.lang.ArchRule;
import org.springframework.web.bind.annotation.RestController;

@AnalyzeClasses(packages = "br.com.segsense", importOptions = ImportOption.DoNotIncludeTests.class)
class ArchitectureConstraintsTest {

  @ArchTest
  static final ArchRule domain_is_independent_of_spring_jpa_and_http =
      noClasses()
          .that()
          .resideInAPackage("br.com.segsense.domain..")
          .should()
          .dependOnClassesThat()
          .resideInAnyPackage(
              "org.springframework..",
              "org.springframework.security..",
              "org.springframework.security.oauth2..",
              "io.jsonwebtoken..",
              "com.nimbusds..",
              "jakarta.persistence..",
              "jakarta.servlet..",
              "jakarta.ws.rs..",
              "org.hibernate..",
              "org.springframework.web..");

  @ArchTest
  static final ArchRule application_is_independent_of_inbound =
      noClasses()
          .that()
          .resideInAPackage("br.com.segsense.application..")
          .should()
          .dependOnClassesThat()
          .resideInAPackage("br.com.segsense.inbound..");

  @ArchTest
  static final ArchRule application_is_independent_of_infrastructure =
      noClasses()
          .that()
          .resideInAPackage("br.com.segsense.application..")
          .should()
          .dependOnClassesThat()
          .resideInAPackage("br.com.segsense.infrastructure..");

  @ArchTest
  static final ArchRule no_spider_or_icatu_operational_clients =
      noClasses()
          .should()
          .dependOnClassesThat()
          .resideInAnyPackage("br.com.spider..", "com.icatu..");

  @ArchTest
  static final ArchRule no_spider_internal_orchestration_types =
      noClasses()
          .that()
          .resideInAPackage("br.com.segsense..")
          .should()
          .haveNameMatching(
              ".*(IntentRouter|ContextGuard|ExecutionPlan|CapabilityResolver|RouteResolver)");

  @ArchTest
  static final ArchRule application_is_independent_of_security_implementations =
      noClasses()
          .that()
          .resideInAPackage("br.com.segsense.application..")
          .should()
          .dependOnClassesThat()
          .resideInAnyPackage(
              "org.springframework.security..",
              "br.com.segsense.inbound.http.security..",
              "br.com.segsense.infrastructure.security..");

  @ArchTest
  static final ArchRule no_invented_satellite_contract_types =
      noClasses()
          .should()
          .haveNameMatching(
              ".*(SatelliteContract|SatelliteContractMapper|SpiderClient|IcatuClient|IcatuProduct|IcatuAdapter)");
}
