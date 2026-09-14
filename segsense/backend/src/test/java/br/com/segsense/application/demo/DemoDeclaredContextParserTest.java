package br.com.segsense.application.demo;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;

import org.junit.jupiter.api.Test;

class DemoDeclaredContextParserTest {

  @Test
  void mapsFamilyAndIncomeWithoutInventingLifeFacts() {
    assertEquals("family_continuity", DemoDeclaredContextParser.themeFromDeclaredText("continuidade familiar"));
    assertEquals("income_interruption", DemoDeclaredContextParser.themeFromDeclaredText("interrupção de renda"));
    assertEquals("nearby_fires", DemoDeclaredContextParser.themeFromDeclaredText("Houve incêndios nas proximidades"));
    assertEquals("conflict", DemoDeclaredContextParser.themeFromDeclaredText("continuidade familiar e houve incêndios"));
    assertNull(DemoDeclaredContextParser.themeFromDeclaredText("asdf"));
  }
}
