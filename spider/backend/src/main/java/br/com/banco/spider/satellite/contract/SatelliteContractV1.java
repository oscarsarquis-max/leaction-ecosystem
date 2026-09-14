package br.com.banco.spider.satellite.contract;

public final class SatelliteContractV1 {
  public static final String VERSION = "1.0";
  public static final String VERSION_1_1 = "1.1";
  public static final String WATERMARK =
      "DEMONSTRAÇÃO — SEM VALOR COMERCIAL — NÃO É COTAÇÃO/PROPOSTA DE CONTRATAÇÃO";
  public static final String ILLUSTRATIVE_CAPABILITY = "BUILD_ILLUSTRATIVE_PROTECTION_SCENARIO";
  public static final String HOME_QUOTE_CAPABILITY = "GENERATE_SYNTHETIC_HOME_QUOTE";
  public static final String WATERMARK_QUOTE =
      "SIMULAÇÃO DEMONSTRATIVA — SEM VALIDADE COMERCIAL — NÃO É OFERTA ICATU NEM CONTRATAÇÃO";
  public static final String PURPOSE_INSURANCE = "INSURANCE_PROTECTION_ASSESSMENT";
  public static final String PATH_V1 = "SATELLITE_CONTRACT_V1_THEN_CAPABILITY_RESOLUTION";
  public static final String PATH_V1_1 = "SATELLITE_CONTRACT_V1_1_THEN_CAPABILITY_RESOLUTION";

  private SatelliteContractV1() {}

  public static boolean supports(String contractVersion) {
    return VERSION.equals(contractVersion) || VERSION_1_1.equals(contractVersion);
  }

  public static boolean is11(String contractVersion) {
    return VERSION_1_1.equals(contractVersion);
  }
}
