package br.com.segsense.infrastructure.link;

import java.security.SecureRandom;
import java.util.Base64;
import br.com.segsense.application.link.OpaqueTokenGenerator;
import br.com.segsense.domain.link.OpaqueToken;
import org.springframework.stereotype.Component;

@Component
public class SecureOpaqueTokenGenerator implements OpaqueTokenGenerator {

  private final SecureRandom random = new SecureRandom();

  @Override
  public String generate() {
    byte[] bytes = new byte[OpaqueToken.RAW_BYTE_LENGTH];
    random.nextBytes(bytes);
    return Base64.getUrlEncoder().withoutPadding().encodeToString(bytes);
  }
}
