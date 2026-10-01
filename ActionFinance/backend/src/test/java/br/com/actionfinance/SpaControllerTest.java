package br.com.actionfinance;

import br.com.actionfinance.interfaces.http.SpaController;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.test.context.TestPropertySource;
import org.springframework.test.web.servlet.MockMvc;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.forwardedUrl;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest(controllers = SpaController.class)
@AutoConfigureMockMvc(addFilters = false)
@TestPropertySource(properties = "actionfinance.oidc.enabled=true")
class SpaControllerTest {

    @Autowired
    private MockMvc mvc;

    @Test
    void payReceiptsShellForwardsToIndex() throws Exception {
        mvc.perform(get("/pay-receipts")).andExpect(status().isOk()).andExpect(forwardedUrl("/index.html"));
        mvc.perform(get("/pay-receipts/")).andExpect(status().isOk()).andExpect(forwardedUrl("/index.html"));
        mvc.perform(get("/pay-receipts/abc")).andExpect(status().isOk()).andExpect(forwardedUrl("/index.html"));
    }
}
