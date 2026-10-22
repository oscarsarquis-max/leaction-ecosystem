package br.com.actionfinance.application.finance;

import br.com.actionfinance.domain.AccountType;
import org.junit.jupiter.api.Test;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

class AccountProfileRulesTest {

    @Test
    void bankCreateKeepsTheLiteralAccountNumberAndDoesNotRequireANickname() {
        Map<String, String> errors = new LinkedHashMap<>();
        AccountProfile profile = AccountProfileRules.normalize(AccountType.BANK, bank("0012345-6"), errors, true);

        assertTrue(errors.isEmpty());
        assertEquals("0012345-6", profile.accountNumber());
        assertEquals("CHECKING", profile.modality());
        String masked = AccountProfileRules.mask("0012345-6");
        assertEquals("Banco Ensaio " + masked, AccountProfileRules.presentationName("Banco Ensaio", profile.accountNumber()));
        assertTrue(masked.endsWith("45-6"));
        assertTrue(!masked.contains("0012"));
    }

    @Test
    void cashRejectsBankFieldsAndLegacyBankCanStayBlank() {
        Map<String, String> cashErrors = new LinkedHashMap<>();
        AccountProfileRules.normalize(AccountType.CASH, bank("1"), cashErrors, true);
        assertTrue(cashErrors.containsKey("type"));

        Map<String, String> legacy = new LinkedHashMap<>();
        AccountProfile profile = AccountProfileRules.normalize(AccountType.BANK, null, legacy, false);
        assertTrue(legacy.isEmpty());
        assertNull(profile.institutionName());
        assertNull(profile.accountNumber());
    }

    @Test
    void optionalContactIsAcceptedAndASecondPrimaryIsRefused() {
        Map<String, String> errors = new LinkedHashMap<>();
        AccountProfileInput input = new AccountProfileInput(
                "Banco Ensaio", null, "PAYMENT", null, null, "0012345-6", null, null, null, null,
                List.of(
                        new AccountContactInput("Ana Ensaio", "ACCOUNT_MANAGER", "ana@ensaio.example", "1133334444", true, "ACCOUNT"),
                        new AccountContactInput("Bruno Ensaio", "BRANCH_MANAGER", "", "", true, "BRANCH")));
        AccountProfileRules.normalize(AccountType.BANK, input, errors, true);
        assertEquals("Marque apenas um contato principal.", errors.get("contacts"));
    }

    private static AccountProfileInput bank(String number) {
        return new AccountProfileInput(
                "Banco Ensaio", null, "CHECKING", null, null, number, null, null, null, null, List.of());
    }
}
