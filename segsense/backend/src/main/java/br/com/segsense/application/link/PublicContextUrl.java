package br.com.segsense.application.link;

public interface PublicContextUrl {

  String publicUrl(String opaqueToken);

  String configuredBaseUrl();
}
