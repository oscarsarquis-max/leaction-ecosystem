package br.com.banco.spider.application.console;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import br.com.banco.spider.config.OperationalConsoleProperties;
import br.com.banco.spider.operational.events.OperationalEventCategory;
import br.com.banco.spider.operational.events.OperationalEventOutcome;
import br.com.banco.spider.operational.events.OperationalEventType;
import br.com.banco.spider.operational.readmodel.OperationalEventView;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import org.junit.jupiter.api.Test;

class MonitorCompanyAccessTest {

  private static final String COMPANY = "9c2e0a10-4f11-4b8a-9c2e-0a104f11000c";
  private static final String OTHER = "624023a4-57e3-415c-b7d0-925ca1acd3b7";

  @Test
  void denyByDefaultWhenScopeEnabledAndBindingMissing() {
    MonitorCompanyAccess access = scoped("");
    OperationalConsoleSecurityContext ctx = new OperationalConsoleSecurityContext("owner:sandbox", "SANDBOX", true);
    assertTrue(access.allowedCompanies(ctx).isEmpty());
    assertFalse(access.maySee(ctx, Optional.of(COMPANY)));
    assertFalse(access.maySee(ctx, Optional.empty()));
  }

  @Test
  void missingCompanyNeverGrantsAccess() {
    MonitorCompanyAccess access = scoped(COMPANY);
    OperationalConsoleSecurityContext ctx = new OperationalConsoleSecurityContext("owner:sandbox", "SANDBOX", true);
    assertFalse(access.maySee(ctx, Optional.empty()));
    assertFalse(access.maySee(ctx, Optional.of(" ")));
    OperationalEventView bare =
        new OperationalEventView(
            "ev-1",
            1,
            OperationalEventType.SATELLITE_REQUEST_RECEIVED,
            OperationalEventCategory.INTERACTION,
            Instant.parse("2026-10-01T12:00:00Z"),
            "afm-other",
            null,
            "corr",
            "satellite-contract",
            OperationalEventOutcome.SUCCESS,
            null,
            Map.of());
    assertTrue(access.companyOfViews(List.of(bare)).isEmpty());
    assertFalse(access.maySee(ctx, access.companyOfViews(List.of(bare))));
  }

  @Test
  void allowsBoundCompanyAndRejectsSwap() {
    MonitorCompanyAccess access = scoped(COMPANY);
    OperationalConsoleSecurityContext ctx = new OperationalConsoleSecurityContext("owner:sandbox", "SANDBOX", true);
    OperationalEventView owned =
        new OperationalEventView(
            "ev-ok",
            1,
            OperationalEventType.SATELLITE_COMPANY_AUTHORIZED,
            OperationalEventCategory.SECURITY,
            Instant.parse("2026-10-01T12:00:00Z"),
            "afm-ok",
            null,
            "corr-ok",
            "satellite-contract",
            OperationalEventOutcome.SUCCESS,
            null,
            Map.of("companyId", COMPANY, "reasonCode", COMPANY));
    OperationalEventView foreign =
        new OperationalEventView(
            "ev-no",
            1,
            OperationalEventType.SATELLITE_COMPANY_AUTHORIZED,
            OperationalEventCategory.SECURITY,
            Instant.parse("2026-10-01T12:00:01Z"),
            "afm-no",
            null,
            "corr-no",
            "satellite-contract",
            OperationalEventOutcome.SUCCESS,
            null,
            Map.of("companyId", OTHER, "reasonCode", OTHER));
    assertTrue(access.maySee(ctx, access.companyOfViews(List.of(owned))));
    assertFalse(access.maySee(ctx, access.companyOfViews(List.of(foreign))));
    assertEquals(COMPANY, access.companyOfViews(List.of(owned)).orElseThrow());
  }

  @Test
  void disabledScopeKeepsPreviousLocalDemoBehaviour() {
    OperationalConsoleProperties props = new OperationalConsoleProperties();
    MonitorCompanyAccess access = new MonitorCompanyAccess(props);
    OperationalConsoleSecurityContext ctx = new OperationalConsoleSecurityContext("local-demo-console", "LOCAL", true);
    assertFalse(access.enabled());
    assertTrue(access.maySee(ctx, Optional.empty()));
    assertTrue(access.maySee(ctx, Optional.of(OTHER)));
  }

  private static MonitorCompanyAccess scoped(String companies) {
    OperationalConsoleProperties props = new OperationalConsoleProperties();
    props.getCompanyScope().setEnabled(true);
    props.getCompanyScope().getBindings().put("owner:sandbox", companies);
    return new MonitorCompanyAccess(props);
  }
}
