package br.com.segsense.inbound.http.consent;

public record ConsentNoticeRequest(
    Long expectedVersion,
    String purposeTitle,
    String purposeDescription,
    String transparencyText,
    String noExternalSharingText,
    String justification) {}
