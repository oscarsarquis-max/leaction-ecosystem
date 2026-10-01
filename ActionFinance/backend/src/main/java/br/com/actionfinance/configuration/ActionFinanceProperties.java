package br.com.actionfinance.configuration;

import org.springframework.boot.context.properties.ConfigurationProperties;

import java.util.ArrayList;
import java.util.List;

@ConfigurationProperties(prefix = "actionfinance")
public class ActionFinanceProperties {

    private String appVersion = "0.1.0";
    private final DemoAuth demoAuth = new DemoAuth();
    private final Cors cors = new Cors();
    private final ClockProperties clock = new ClockProperties();
    private final Oidc oidc = new Oidc();
    private final SessionProperties session = new SessionProperties();
    private final Ingress ingress = new Ingress();
    private final Integration integration = new Integration();
    private String publicOrigin = "";
    private String loginRegistrationId = "actionfinance";

    public String getAppVersion() {
        return appVersion;
    }

    public void setAppVersion(String appVersion) {
        this.appVersion = appVersion;
    }

    public DemoAuth getDemoAuth() {
        return demoAuth;
    }

    public Cors getCors() {
        return cors;
    }

    public ClockProperties getClock() {
        return clock;
    }

    public Oidc getOidc() {
        return oidc;
    }

    public SessionProperties getSession() {
        return session;
    }

    public Ingress getIngress() {
        return ingress;
    }

    public Integration getIntegration() {
        return integration;
    }

    public String getPublicOrigin() {
        return publicOrigin;
    }

    public void setPublicOrigin(String publicOrigin) {
        this.publicOrigin = publicOrigin;
    }

    public String getLoginRegistrationId() {
        return loginRegistrationId;
    }

    public void setLoginRegistrationId(String loginRegistrationId) {
        this.loginRegistrationId = loginRegistrationId;
    }

    public static class DemoAuth {
        private boolean enabled = false;
        private String operatorAToken = "";
        private String viewerAToken = "";
        private String viewerBToken = "";
        private String operatorMultiToken = "";
        private String mixedAbToken = "";

        public boolean isEnabled() {
            return enabled;
        }

        public void setEnabled(boolean enabled) {
            this.enabled = enabled;
        }

        public String getOperatorAToken() {
            return operatorAToken;
        }

        public void setOperatorAToken(String operatorAToken) {
            this.operatorAToken = operatorAToken;
        }

        public String getViewerAToken() {
            return viewerAToken;
        }

        public void setViewerAToken(String viewerAToken) {
            this.viewerAToken = viewerAToken;
        }

        public String getViewerBToken() {
            return viewerBToken;
        }

        public void setViewerBToken(String viewerBToken) {
            this.viewerBToken = viewerBToken;
        }

        public String getOperatorMultiToken() {
            return operatorMultiToken;
        }

        public void setOperatorMultiToken(String operatorMultiToken) {
            this.operatorMultiToken = operatorMultiToken;
        }

        public String getMixedAbToken() {
            return mixedAbToken;
        }

        public void setMixedAbToken(String mixedAbToken) {
            this.mixedAbToken = mixedAbToken;
        }
    }

    public static class ClockProperties {
        private String zone = "America/Sao_Paulo";
        private String fixedInstant = "";

        public String getZone() {
            return zone;
        }

        public void setZone(String zone) {
            this.zone = zone;
        }

        public String getFixedInstant() {
            return fixedInstant;
        }

        public void setFixedInstant(String fixedInstant) {
            this.fixedInstant = fixedInstant;
        }
    }

    public static class Cors {
        private List<String> allowedOrigins = new ArrayList<>();

        public List<String> getAllowedOrigins() {
            return allowedOrigins;
        }

        public void setAllowedOrigins(List<String> allowedOrigins) {
            this.allowedOrigins = allowedOrigins;
        }
    }

    public static class Oidc {
        private boolean enabled = false;
        private String issuer = "";
        private String clientId = "";
        private String clientSecret = "";
        private String redirectUri = "";

        public boolean isEnabled() {
            return enabled;
        }

        public void setEnabled(boolean enabled) {
            this.enabled = enabled;
        }

        public String getIssuer() {
            return issuer;
        }

        public void setIssuer(String issuer) {
            this.issuer = issuer;
        }

        public String getClientId() {
            return clientId;
        }

        public void setClientId(String clientId) {
            this.clientId = clientId;
        }

        public String getClientSecret() {
            return clientSecret;
        }

        public void setClientSecret(String clientSecret) {
            this.clientSecret = clientSecret;
        }

        public String getRedirectUri() {
            return redirectUri;
        }

        public void setRedirectUri(String redirectUri) {
            this.redirectUri = redirectUri;
        }
    }

    public static class SessionProperties {
        private int inactivityMinutes = 30;
        private boolean cookieSecure = true;

        public int getInactivityMinutes() {
            return inactivityMinutes;
        }

        public void setInactivityMinutes(int inactivityMinutes) {
            this.inactivityMinutes = inactivityMinutes;
        }

        public boolean isCookieSecure() {
            return cookieSecure;
        }

        public void setCookieSecure(boolean cookieSecure) {
            this.cookieSecure = cookieSecure;
        }
    }

    public static class Ingress {
        private boolean trustForwardedHeaders = false;

        public boolean isTrustForwardedHeaders() {
            return trustForwardedHeaders;
        }

        public void setTrustForwardedHeaders(boolean trustForwardedHeaders) {
            this.trustForwardedHeaders = trustForwardedHeaders;
        }
    }

    public static class Integration {
        private boolean homolog = false;
        private boolean receiptSyncEnabled = false;
        private String spiderBaseUrl = "";
        private String spiderSecret = "";
        private String satelliteId = "actionfinance";
        private java.time.Duration lookupStaleAfter = java.time.Duration.ofSeconds(30);
        private String spiderMonitorBaseUrl = "http://127.0.0.1:5180";
        private int syncPageLimit = 25;
        private java.time.Duration syncStaleAfter = java.time.Duration.ofSeconds(60);

        public boolean isHomolog() {
            return homolog;
        }

        public void setHomolog(boolean homolog) {
            this.homolog = homolog;
        }

        public boolean isReceiptSyncEnabled() {
            return receiptSyncEnabled;
        }

        public void setReceiptSyncEnabled(boolean receiptSyncEnabled) {
            this.receiptSyncEnabled = receiptSyncEnabled;
        }

        public boolean isReceiptSyncAllowed() {
            return homolog || receiptSyncEnabled;
        }

        public String getSpiderBaseUrl() {
            return spiderBaseUrl;
        }

        public void setSpiderBaseUrl(String spiderBaseUrl) {
            this.spiderBaseUrl = spiderBaseUrl;
        }

        public String getSpiderSecret() {
            return spiderSecret;
        }

        public void setSpiderSecret(String spiderSecret) {
            this.spiderSecret = spiderSecret;
        }

        public String getSatelliteId() {
            return satelliteId;
        }

        public void setSatelliteId(String satelliteId) {
            this.satelliteId = satelliteId;
        }

        public java.time.Duration getLookupStaleAfter() {
            return lookupStaleAfter;
        }

        public void setLookupStaleAfter(java.time.Duration lookupStaleAfter) {
            this.lookupStaleAfter = lookupStaleAfter;
        }

        public String getSpiderMonitorBaseUrl() {
            return spiderMonitorBaseUrl;
        }

        public void setSpiderMonitorBaseUrl(String spiderMonitorBaseUrl) {
            this.spiderMonitorBaseUrl = spiderMonitorBaseUrl;
        }

        public int getSyncPageLimit() {
            return syncPageLimit;
        }

        public void setSyncPageLimit(int syncPageLimit) {
            this.syncPageLimit = syncPageLimit;
        }

        public java.time.Duration getSyncStaleAfter() {
            return syncStaleAfter;
        }

        public void setSyncStaleAfter(java.time.Duration syncStaleAfter) {
            this.syncStaleAfter = syncStaleAfter;
        }
    }
}
