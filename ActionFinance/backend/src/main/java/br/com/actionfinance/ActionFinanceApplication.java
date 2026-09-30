package br.com.actionfinance;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.autoconfigure.security.servlet.UserDetailsServiceAutoConfiguration;

@SpringBootApplication(exclude = {UserDetailsServiceAutoConfiguration.class})
public class ActionFinanceApplication {

    public static void main(String[] args) {
        SpringApplication.run(ActionFinanceApplication.class, args);
    }
}
