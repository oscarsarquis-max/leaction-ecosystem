package br.com.actionfinance.domain;

import br.com.actionfinance.application.finance.FinanceExceptions.ValidationException;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class DocumentNumbersTest {

    @Test
    void acceptsOfficialAlphanumericCnpjAndNumericCpf() {
        var cnpj = DocumentNumbers.parse("BR", "CNPJ", "12.ABC.345/01DE-35", PersonKind.LEGAL);
        assertThat(cnpj.normalized()).isEqualTo("12ABC34501DE35");
        assertThat(DocumentNumbers.cnpjDigitsValid("12ABC34501DE35")).isTrue();

        var numeric = DocumentNumbers.parse("br", "CNPJ", "11.222.333/0001-81", PersonKind.UNSPECIFIED);
        assertThat(numeric.normalized()).isEqualTo("11222333000181");

        var cpf = DocumentNumbers.parse("BR", "CPF", "529.982.247-25", PersonKind.NATURAL);
        assertThat(cpf.normalized()).isEqualTo("52998224725");
    }

    @Test
    void rejectsMalformedInputWithoutSilentCorrection() {
        assertThatThrownBy(() -> DocumentNumbers.parse("BR", "CNPJ", "12*ABC*345*01DE*35", PersonKind.LEGAL))
                .isInstanceOf(ValidationException.class);
        assertThatThrownBy(() -> DocumentNumbers.parse("BR", "CNPJ", "12.ABC.345/01DE-3A", PersonKind.LEGAL))
                .isInstanceOf(ValidationException.class);
        assertThatThrownBy(() -> DocumentNumbers.parse("BR", "CNPJ", "12.ABC.345/0001-95", PersonKind.LEGAL))
                .isInstanceOf(ValidationException.class);
        assertThatThrownBy(() -> DocumentNumbers.parse("BR", "CPF", "111.111.111-11", PersonKind.NATURAL))
                .isInstanceOf(ValidationException.class);
        assertThatThrownBy(() -> DocumentNumbers.parse("BR", "CNPJ", "11.222.333/0001-81", PersonKind.NATURAL))
                .isInstanceOf(ValidationException.class);
        assertThatThrownBy(() -> DocumentNumbers.parse("BR", "CPF", "529.982.247-25", PersonKind.LEGAL))
                .isInstanceOf(ValidationException.class);
        assertThat(DocumentNumbers.normalizeToken("12*ABC")).isNull();
    }

    @Test
    void emptyDocumentRemainsIncomplete() {
        assertThat(DocumentNumbers.parse("", "", "", PersonKind.UNSPECIFIED)).isNull();
        assertThat(DocumentNumbers.mask("12ABC34501DE35", false)).isEqualTo("••••35");
    }
}
