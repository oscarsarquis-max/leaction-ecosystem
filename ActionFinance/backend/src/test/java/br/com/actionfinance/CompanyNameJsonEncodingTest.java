package br.com.actionfinance;

import br.com.actionfinance.application.AccessQueryService;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;

import java.nio.charset.StandardCharsets;
import java.util.HexFormat;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;

class CompanyNameJsonEncodingTest {

    @Test
    void accessContextJsonKeepsLatinSmallLetterAWithTilde() throws Exception {
        var mapper = new ObjectMapper();
        var view =
                new AccessQueryService.CompanyContext(
                        UUID.fromString("624023a4-57e3-415c-b7d0-925ca1acd3b7"),
                        UUID.fromString("4f150085-f5f0-4138-80c3-fcf06db15c3c"),
                        "Loja de P\u00e3es",
                        true,
                        false,
                        "America/Sao_Paulo",
                        "Loja de P\u00e3es");
        byte[] json = mapper.writeValueAsBytes(view);
        String hex = HexFormat.of().formatHex(json);
        assertThat(new String(json, StandardCharsets.UTF_8)).contains("Loja de P\u00e3es");
        assertThat(hex).contains("c3a3");
        assertThat(hex).doesNotContain("c383c2a3");
    }
}
