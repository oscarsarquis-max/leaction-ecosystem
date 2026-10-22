package br.com.actionfinance.application.finance;

import br.com.actionfinance.domain.AccountType;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.UUID;
import java.util.regex.Pattern;

public record AccountProfile(
        String institutionName,
        String bankCode,
        String modality,
        String branchNumber,
        String branchDigit,
        String accountNumber,
        String accountDigit,
        String countryCode,
        String institutionEmail,
        String institutionPhone,
        List<AccountContact> contacts) {

    public AccountProfile {
        contacts = contacts == null ? List.of() : List.copyOf(contacts);
    }

    public static AccountProfile empty() {
        return new AccountProfile(null, null, null, null, null, null, null, null, null, null, List.of());
    }

    public AccountProfile withContacts(List<AccountContact> next) {
        return new AccountProfile(
                institutionName, bankCode, modality, branchNumber, branchDigit, accountNumber, accountDigit,
                countryCode, institutionEmail, institutionPhone, next);
    }

    public record AccountContact(
            UUID id,
            String personName,
            String role,
            String email,
            String phone,
            boolean primaryContact,
            String association) {}
}

final class AccountProfileRules {

    private static final Pattern ACCOUNT_NUMBER = Pattern.compile("^[0-9A-Za-z][0-9A-Za-z.\\-/]{0,31}$");
    private static final Pattern DIGITS = Pattern.compile("^\\d{1,12}$");
    private static final Pattern SHORT_DIGITS = Pattern.compile("^\\d{1,8}$");
    private static final Pattern DIGIT = Pattern.compile("^[0-9A-Za-z]{1,4}$");
    private static final Pattern EMAIL = Pattern.compile("^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$");
    private static final Pattern PHONE = Pattern.compile("^[0-9+()\\-\\s]{3,40}$");
    private static final Pattern COUNTRY = Pattern.compile("^[A-Z]{2}$");

    private AccountProfileRules() {}

    static AccountProfile normalize(AccountType type, AccountProfileInput input, Map<String, String> errors, boolean creating) {
        AccountProfileInput source = input == null
                ? new AccountProfileInput(null, null, null, null, null, null, null, null, null, null, List.of())
                : input;
        String institution = limited(source.institutionName(), 120, "institutionName", "O banco ou a instituição deve ter até 120 caracteres.", errors);
        String bankCode = limited(source.bankCode(), 8, "bankCode", "O código do banco usa até 8 dígitos.", errors);
        String modality = upper(source.modality());
        String branch = limited(source.branchNumber(), 12, "branchNumber", "A agência usa até 12 dígitos.", errors);
        String branchDigit = limited(source.branchDigit(), 4, "branchDigit", "O dígito da agência é inválido.", errors);
        String number = limited(source.accountNumber(), 32, "accountNumber", "O número da conta deve ter até 32 caracteres.", errors);
        String accountDigit = limited(source.accountDigit(), 4, "accountDigit", "O dígito da conta é inválido.", errors);
        String country = upper(limited(source.countryCode(), 2, "countryCode", "Informe o país com duas letras, como BR.", errors));
        String email = limited(source.institutionEmail(), 160, "institutionEmail", "O e-mail institucional deve ter até 160 caracteres.", errors);
        String phone = limited(source.institutionPhone(), 40, "institutionPhone", "O telefone de atendimento deve ter até 40 caracteres.", errors);
        boolean bankIdentity = !institution.isEmpty() || !number.isEmpty() || !modality.isEmpty();

        if (type == AccountType.CASH && (bankIdentity || !bankCode.isEmpty() || !branch.isEmpty() || !branchDigit.isEmpty() || !accountDigit.isEmpty())) {
            errors.put("type", "Caixa físico é identificado pelo nome e não usa dados bancários.");
        }
        if (type == AccountType.OTHER && (!number.isEmpty() || !modality.isEmpty() || !bankCode.isEmpty() || !branch.isEmpty() || !accountDigit.isEmpty() || !branchDigit.isEmpty())) {
            errors.put("type", "Outra conta não usa número, agência nem modalidade bancária.");
        }
        if (type == AccountType.BANK && (creating || bankIdentity)) {
            if (institution.isEmpty()) {
                errors.put("institutionName", "Informe o banco ou a instituição.");
            }
            if (number.isEmpty()) {
                errors.put("accountNumber", "Informe o número da conta.");
            }
            if (!modality.isEmpty() && !List.of("CHECKING", "SAVINGS", "INVESTMENT", "PAYMENT").contains(modality)) {
                errors.put("modality", "Escolha conta corrente, poupança, investimento ou conta de pagamento.");
            } else if (modality.isEmpty()) {
                errors.put("modality", "Escolha a modalidade.");
            }
        } else if (type == AccountType.BANK && !modality.isEmpty() && !List.of("CHECKING", "SAVINGS", "INVESTMENT", "PAYMENT").contains(modality)) {
            errors.put("modality", "Escolha conta corrente, poupança, investimento ou conta de pagamento.");
        }
        if (!number.isEmpty() && !ACCOUNT_NUMBER.matcher(number).matches()) {
            errors.put("accountNumber", "Use letras, números e os sinais . - /. O número não é a chave interna.");
        }
        if (!bankCode.isEmpty() && !SHORT_DIGITS.matcher(bankCode).matches()) {
            errors.put("bankCode", "O código do banco usa até 8 dígitos.");
        }
        if (!branch.isEmpty() && !DIGITS.matcher(branch).matches()) {
            errors.put("branchNumber", "A agência usa até 12 dígitos.");
        }
        if (!branchDigit.isEmpty() && !DIGIT.matcher(branchDigit).matches()) {
            errors.put("branchDigit", "O dígito da agência é inválido.");
        }
        if (!accountDigit.isEmpty() && !DIGIT.matcher(accountDigit).matches()) {
            errors.put("accountDigit", "O dígito da conta é inválido.");
        }
        if (!country.isEmpty() && !COUNTRY.matcher(country).matches()) {
            errors.put("countryCode", "Informe o país com duas letras, como BR.");
        }
        if (!email.isEmpty() && !EMAIL.matcher(email).matches()) {
            errors.put("institutionEmail", "Informe um e-mail institucional válido ou deixe em branco.");
        }
        if (!phone.isEmpty() && !PHONE.matcher(phone).matches()) {
            errors.put("institutionPhone", "Informe um telefone de atendimento válido ou deixe em branco.");
        }

        List<AccountProfile.AccountContact> contacts = contacts(source.contacts(), errors);
        return new AccountProfile(
                blank(institution),
                blank(bankCode),
                blank(modality),
                blank(branch),
                blank(branchDigit),
                blank(number),
                blank(accountDigit),
                blank(country),
                blank(email),
                blank(phone),
                contacts);
    }

    static String presentationName(String institution, String accountNumber) {
        String masked = mask(accountNumber);
        String label = (institution == null ? "" : institution.trim()) + (masked.isEmpty() ? "" : " " + masked);
        String trimmed = label.trim();
        return trimmed.length() <= 100 ? trimmed : trimmed.substring(0, 100);
    }

    static String mask(String accountNumber) {
        String text = accountNumber == null ? "" : accountNumber.trim();
        if (text.isEmpty()) {
            return "";
        }
        if (text.length() <= 4) {
            return "••••";
        }
        return "••••" + text.substring(text.length() - 4);
    }

    private static List<AccountProfile.AccountContact> contacts(List<AccountContactInput> inputs, Map<String, String> errors) {
        List<AccountProfile.AccountContact> contacts = new ArrayList<>();
        if (inputs == null || inputs.isEmpty()) {
            return List.of();
        }
        if (inputs.size() > 20) {
            errors.put("contacts", "Informe até 20 contatos.");
            return List.of();
        }
        int primary = 0;
        int index = 0;
        for (AccountContactInput input : inputs) {
            String name = limited(input == null ? null : input.personName(), 80, "contacts." + index + ".personName", "O nome do contato deve ter até 80 caracteres.", errors);
            if (name.isEmpty()) {
                index += 1;
                continue;
            }
            String role = upper(input.role());
            String association = upper(input.association());
            String email = limited(input.email(), 160, "contacts." + index + ".email", "O e-mail do contato deve ter até 160 caracteres.", errors);
            String phone = limited(input.phone(), 40, "contacts." + index + ".phone", "O telefone do contato deve ter até 40 caracteres.", errors);
            if (!List.of("ACCOUNT_MANAGER", "BRANCH_MANAGER", "SERVICE", "OTHER").contains(role)) {
                errors.put("contacts." + index + ".role", "Escolha a função do contato.");
            }
            if (!List.of("ACCOUNT", "BRANCH", "INSTITUTION").contains(association)) {
                errors.put("contacts." + index + ".association", "Escolha a associação do contato.");
            }
            if (!email.isEmpty() && !EMAIL.matcher(email).matches()) {
                errors.put("contacts." + index + ".email", "Informe um e-mail profissional válido ou deixe em branco.");
            }
            if (!phone.isEmpty() && !PHONE.matcher(phone).matches()) {
                errors.put("contacts." + index + ".phone", "Informe um telefone ou ramal válido ou deixe em branco.");
            }
            if (input.primaryContact()) {
                primary += 1;
            }
            contacts.add(new AccountProfile.AccountContact(
                    null, name, role, blank(email), blank(phone), input.primaryContact(), association));
            index += 1;
        }
        if (primary > 1) {
            errors.put("contacts", "Marque apenas um contato principal.");
        }
        return List.copyOf(contacts);
    }

    private static String limited(String value, int max, String field, String message, Map<String, String> errors) {
        String trimmed = value == null ? "" : value.trim();
        if (trimmed.length() > max) {
            errors.put(field, message);
        }
        return trimmed;
    }

    private static String upper(String value) {
        String trimmed = value == null ? "" : value.trim();
        if (trimmed.length() > 24) {
            trimmed = trimmed.substring(0, 24);
        }
        return trimmed.isEmpty() ? "" : trimmed.toUpperCase(Locale.ROOT);
    }

    private static String blank(String value) {
        return value == null || value.isEmpty() ? null : value;
    }
}
