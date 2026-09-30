package br.com.actionfinance.admin;

import br.com.actionfinance.application.identity.AccessAdminService;
import br.com.actionfinance.application.identity.MembershipRole;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.context.annotation.Profile;
import org.springframework.stereotype.Component;

import java.util.List;
import java.util.UUID;

@Component
@Profile("access-admin")
public class AccessAdminRunner implements ApplicationRunner {

    private final AccessAdminService admin;

    public AccessAdminRunner(AccessAdminService admin) {
        this.admin = admin;
    }

    @Override
    public void run(ApplicationArguments args) {
        List<String> nonOption = args.getNonOptionArgs();
        if (nonOption.isEmpty()) {
            throw new IllegalArgumentException(
                    "Usage: bootstrap-org|provision|revoke|block|unblock --tenant-code --tenant-name --company-code --company-name --timezone --responsible-name --display-name --issuer --subject --tenant-id --company-id --role --user-id --reason [--dry-run]");
        }
        String command = nonOption.getFirst();
        boolean dryRun = args.containsOption("dry-run");
        String reason = required(args, "reason");
        String executor = first(args, "executor", "access-admin");
        AccessAdminService.Result result =
                switch (command) {
                    case "bootstrap-org" ->
                            admin.bootstrapOrganization(
                                    required(args, "tenant-code"),
                                    required(args, "tenant-name"),
                                    required(args, "company-code"),
                                    required(args, "company-name"),
                                    first(args, "timezone", "America/Sao_Paulo"),
                                    required(args, "responsible-name"),
                                    reason,
                                    executor,
                                    dryRun);
                    case "provision" ->
                            admin.provision(
                                    required(args, "display-name"),
                                    required(args, "issuer"),
                                    required(args, "subject"),
                                    uuid(required(args, "tenant-id")),
                                    uuid(required(args, "company-id")),
                                    MembershipRole.valueOf(required(args, "role").toUpperCase()),
                                    reason,
                                    executor,
                                    first(args, "correlation-id", null),
                                    dryRun);
                    case "revoke" ->
                            admin.revoke(
                                    uuid(required(args, "user-id")),
                                    uuid(required(args, "tenant-id")),
                                    uuid(required(args, "company-id")),
                                    reason,
                                    executor,
                                    dryRun);
                    case "block" -> admin.setBlocked(uuid(required(args, "user-id")), true, reason, executor, dryRun);
                    case "unblock" -> admin.setBlocked(uuid(required(args, "user-id")), false, reason, executor, dryRun);
                    default -> throw new IllegalArgumentException("Unknown command " + command);
                };
        System.out.println(result.summary() + " userId=" + result.userId() + " changed=" + result.changed());
    }

    private static String required(ApplicationArguments args, String name) {
        List<String> values = args.getOptionValues(name);
        if (values == null || values.isEmpty() || values.getFirst() == null || values.getFirst().isBlank()) {
            throw new IllegalArgumentException(name + " is required.");
        }
        return values.getFirst();
    }

    private static String first(ApplicationArguments args, String name, String fallback) {
        List<String> values = args.getOptionValues(name);
        if (values == null || values.isEmpty()) {
            return fallback;
        }
        return values.getFirst();
    }

    private static UUID uuid(String value) {
        return UUID.fromString(value);
    }
}
