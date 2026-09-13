package br.com.segsense;

import java.nio.charset.StandardCharsets;
import java.util.TimeZone;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication(
    excludeName = {
      "org.springframework.boot.autoconfigure.security.servlet.UserDetailsServiceAutoConfiguration",
      "org.springframework.boot.security.autoconfigure.UserDetailsServiceAutoConfiguration"
    })
public class SegSenseApplication {

  public static void main(String[] args) {
    TimeZone.setDefault(TimeZone.getTimeZone("UTC"));
    System.setProperty("file.encoding", StandardCharsets.UTF_8.name());
    SpringApplication.run(SegSenseApplication.class, args);
  }
}
