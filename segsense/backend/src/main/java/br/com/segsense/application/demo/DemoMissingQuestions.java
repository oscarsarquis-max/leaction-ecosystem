package br.com.segsense.application.demo;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public final class DemoMissingQuestions {

  private DemoMissingQuestions() {}

  public static List<Map<String, String>> fromCodes(List<String> codes) {
    List<Map<String, String>> questions = new ArrayList<>();
    if (codes == null) {
      return questions;
    }
    for (String code : codes) {
      String prompt = prompt(code);
      if (prompt == null) {
        continue;
      }
      Map<String, String> row = new LinkedHashMap<>();
      row.put("code", code);
      row.put("prompt", prompt);
      questions.add(row);
    }
    return questions;
  }

  public static String prompt(String code) {
    if ("dwelling_type".equals(code)) {
      return "Qual é o tipo de imóvel nesta simulação? Apartamento ou casa — use um valor hipotético.";
    }
    if ("insured_amount".equals(code)) {
      return "Qual valor de proteção deseja nesta simulação, em reais?";
    }
    if ("cover_period".equals(code)) {
      return "Qual período deseja? Nesta fatia a simulação cobre 12 meses.";
    }
    if ("home_intention".equals(code)) {
      return "Deseja avaliar uma proteção residencial em simulação?";
    }
    if ("theme".equals(code)) {
      return "Descreva um contexto sintético (por exemplo, incêndios nas proximidades) ou use um link governado.";
    }
    if ("intention".equals(code)) {
      return "O que você deseja fazer? Diga, por exemplo, que quer avaliar uma proteção residencial.";
    }
    return null;
  }
}
