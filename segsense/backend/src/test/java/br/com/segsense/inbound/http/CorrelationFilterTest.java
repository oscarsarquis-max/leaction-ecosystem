package br.com.segsense.inbound.http;

import static org.assertj.core.api.Assertions.assertThat;

import br.com.segsense.application.correlation.CorrelationContext;
import jakarta.servlet.FilterChain;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.slf4j.MDC;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;

class CorrelationFilterTest {

  private final CorrelationFilter filter = new CorrelationFilter();

  @AfterEach
  void clearThreadState() {
    MDC.clear();
    CorrelationContext.clear();
  }

  @Test
  void preservesValidUuid() throws Exception {
    String incoming = "11111111-1111-1111-1111-111111111111";
    MockHttpServletRequest request = apiRequest();
    request.addHeader(CorrelationContext.HTTP_HEADER, incoming);
    MockHttpServletResponse response = new MockHttpServletResponse();

    filter.doFilter(request, response, capturingChain());

    assertThat(response.getHeader(CorrelationContext.HTTP_HEADER)).isEqualTo(incoming);
    assertThat(MDC.get(CorrelationContext.MDC_KEY)).isNull();
    assertThat(CorrelationContext.current()).isNull();
  }

  @Test
  void generatesUuidWhenHeaderIsAbsent() throws Exception {
    MockHttpServletRequest request = apiRequest();
    MockHttpServletResponse response = new MockHttpServletResponse();

    filter.doFilter(request, response, capturingChain());

    assertThat(response.getHeader(CorrelationContext.HTTP_HEADER))
        .matches(
            "[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}");
    assertThat(MDC.get(CorrelationContext.MDC_KEY)).isNull();
  }

  @Test
  void generatesNewUuidWhenHeaderIsInvalid() throws Exception {
    MockHttpServletRequest request = apiRequest();
    request.addHeader(CorrelationContext.HTTP_HEADER, "not-a-uuid");
    MockHttpServletResponse response = new MockHttpServletResponse();

    filter.doFilter(request, response, capturingChain());

    assertThat(response.getHeader(CorrelationContext.HTTP_HEADER)).isNotEqualTo("not-a-uuid");
    assertThat(response.getHeader(CorrelationContext.HTTP_HEADER))
        .matches(
            "[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}");
  }

  @Test
  void removesMdcAfterRequestEvenWhenChainFails() throws Exception {
    MockHttpServletRequest request = apiRequest();
    MockHttpServletResponse response = new MockHttpServletResponse();
    FilterChain chain =
        (req, res) -> {
          assertThat(MDC.get(CorrelationContext.MDC_KEY)).isNotBlank();
          throw new IllegalStateException("forced");
        };

    try {
      filter.doFilter(request, response, chain);
    } catch (IllegalStateException ignored) {
      // expected from the chain
    }

    assertThat(MDC.get(CorrelationContext.MDC_KEY)).isNull();
    assertThat(CorrelationContext.current()).isNull();
  }

  private static MockHttpServletRequest apiRequest() {
    return new MockHttpServletRequest("GET", "/api/v1/system/info");
  }

  private static FilterChain capturingChain() {
    return (req, res) -> {
      assertThat(MDC.get(CorrelationContext.MDC_KEY)).isEqualTo(CorrelationContext.current().toString());
    };
  }
}
