package br.com.segsense.application.demo;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

import br.com.segsense.domain.demo.DemoProtectionException;
import org.junit.jupiter.api.Test;

class DemoPersonalDataGuardTest {

  @Test
  void rejectsEmail() {
    DemoProtectionException error =
        assertThrows(
            DemoProtectionException.class,
            () -> DemoPersonalDataGuard.rejectObviousPersonalData("meu email e teste@example.com"));
    assertEquals("PERSONAL_DATA_NOT_ALLOWED", error.code());
  }

  @Test
  void allowsSyntheticFamilyText() {
    DemoPersonalDataGuard.rejectObviousPersonalData("continuidade familiar com dependentes");
  }
}
