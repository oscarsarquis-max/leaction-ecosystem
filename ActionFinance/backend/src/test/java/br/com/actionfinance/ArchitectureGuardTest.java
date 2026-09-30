package br.com.actionfinance;

import com.tngtech.archunit.core.importer.ImportOption;
import com.tngtech.archunit.junit.AnalyzeClasses;
import com.tngtech.archunit.junit.ArchTest;
import com.tngtech.archunit.lang.ArchRule;

import static com.tngtech.archunit.lang.syntax.ArchRuleDefinition.noClasses;

@AnalyzeClasses(packages = "br.com.actionfinance", importOptions = ImportOption.DoNotIncludeTests.class)
class ArchitectureGuardTest {

    @ArchTest
    static final ArchRule domainDoesNotDependOnFramework =
            noClasses()
                    .that()
                    .resideInAPackage("br.com.actionfinance.domain..")
                    .should()
                    .dependOnClassesThat()
                    .resideInAnyPackage(
                            "org.springframework..",
                            "jakarta.persistence..",
                            "jakarta.servlet..",
                            "org.hibernate..",
                            "org.flywaydb..");

    @ArchTest
    static final ArchRule domainDoesNotImportNeighbors =
            noClasses()
                    .that()
                    .resideInAPackage("br.com.actionfinance..")
                    .should()
                    .dependOnClassesThat()
                    .resideInAnyPackage(
                            "br.com.banco.spider..",
                            "br.com.segsense..",
                            "br.com.spiderbank..",
                            "br.com.panne..");
}
