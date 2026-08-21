package br.com.banco.spider.application.console;

import static org.junit.jupiter.api.Assertions.assertFalse;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.context.ApplicationContext;
import org.springframework.test.context.TestPropertySource;

@SpringBootTest
@TestPropertySource(
    properties = {
      "spider.console.enabled=false",
      "spider.console.http.enabled=false",
      "spider.canonical.persistence.mode=memory",
      "spring.datasource.url=jdbc:h2:mem:spider_console_deny;MODE=PostgreSQL;DB_CLOSE_DELAY=-1",
      "spring.datasource.driver-class-name=org.h2.Driver",
      "spring.datasource.username=sa",
      "spring.datasource.password=",
      "spring.jpa.hibernate.ddl-auto=create-drop",
      "spring.jpa.database-platform=org.hibernate.dialect.H2Dialect"
    })
class DenyAllConsoleAuthBeansPresentTest {

  @Autowired ApplicationContext ctx;

  @Test
  void noPermissiveLocalDemoBeansOutsideProfile() {
    assertFalse(ctx.containsBean("localDemoConsoleAuthentication"));
    assertFalse(ctx.containsBean("localDemoConsoleAuthorization"));
  }

  @Test
  void denyAllBeansPresent() {
    OperationalConsoleAuthenticationPort auth =
        ctx.getBean(OperationalConsoleAuthenticationPort.class);
    OperationalConsoleAuthorizationPort authz =
        ctx.getBean(OperationalConsoleAuthorizationPort.class);
    assertFalse(Boolean.TRUE.equals(auth.authenticate("x").block().authenticated()));
    assertFalse(
        Boolean.TRUE.equals(
            authz
                .authorize(
                    OperationalConsoleSecurityContext.anonymous(),
                    OperationalConsoleAction.LIST_EXECUTIONS)
                .block()));
  }
}
