package br.com.segsense.domain.identity;

/**
 * Identity of the satellite application. {@code applicationId=SEGSENSE} does not authenticate a
 * user.
 */
public record ApplicationIdentity(String applicationId) {

  public ApplicationIdentity {
    applicationId = IdentityValues.requireNormalized(applicationId, "applicationId");
  }

  public static ApplicationIdentity of(String applicationId) {
    return new ApplicationIdentity(applicationId);
  }
}
