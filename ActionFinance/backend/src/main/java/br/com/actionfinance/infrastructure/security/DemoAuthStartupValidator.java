package br.com.actionfinance.infrastructure.security;

import br.com.actionfinance.configuration.ActionFinanceProperties;
import org.springframework.context.annotation.Profile;
import org.springframework.core.env.Environment;
import org.springframework.stereotype.Component;

import java.net.InetAddress;
import java.net.UnknownHostException;
import java.util.HashSet;
import java.util.Set;

@Component
@Profile("local-demo")
public class DemoAuthStartupValidator {

    public DemoAuthStartupValidator(ActionFinanceProperties properties, Environment environment) {
        if (!properties.getDemoAuth().isEnabled()) {
            return;
        }
        String operator = requireToken(properties.getDemoAuth().getOperatorAToken(), "operatorA");
        String viewerA = requireToken(properties.getDemoAuth().getViewerAToken(), "viewerA");
        String viewerB = requireToken(properties.getDemoAuth().getViewerBToken(), "viewerB");
        Set<String> unique = new HashSet<>();
        if (!unique.add(operator) || !unique.add(viewerA) || !unique.add(viewerB)) {
            throw new IllegalStateException("Demo tokens must be unique.");
        }
        rejectNonLoopback(
                firstNonBlank(
                        environment.getProperty("server.address"),
                        environment.getProperty("SERVER_ADDRESS")),
                "server.address");
        String managementAddress = firstNonBlank(
                environment.getProperty("management.server.address"),
                environment.getProperty("MANAGEMENT_SERVER_ADDRESS"));
        if (managementAddress != null && !managementAddress.isBlank()) {
            rejectNonLoopback(managementAddress, "management.server.address");
        }
    }

    static void rejectNonLoopback(String address, String source) {
        if (address == null || address.isBlank()) {
            throw new IllegalStateException("Demo mode requires an explicit loopback " + source + ".");
        }
        try {
            InetAddress inet = InetAddress.getByName(address.trim());
            if (inet.isAnyLocalAddress() || !inet.isLoopbackAddress()) {
                throw new IllegalStateException("Demo mode forbids public bind on " + source + ".");
            }
        } catch (UnknownHostException ex) {
            throw new IllegalStateException("Demo mode received an unresolvable " + source + ".", ex);
        }
    }

    private static String firstNonBlank(String left, String right) {
        if (left != null && !left.isBlank()) {
            return left;
        }
        return right;
    }

    private static String requireToken(String value, String name) {
        if (value == null || value.isBlank()) {
            throw new IllegalStateException("Demo token " + name + " is missing.");
        }
        if (value.length() < 32) {
            throw new IllegalStateException("Demo token " + name + " is too short.");
        }
        return value;
    }
}
