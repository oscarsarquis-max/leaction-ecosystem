package br.com.segsense.inbound.http;

import br.com.segsense.application.system.SystemInfoService;
import br.com.segsense.domain.system.SystemInfo;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/system")
public class SystemInfoController {

  private final SystemInfoService systemInfoService;

  public SystemInfoController(SystemInfoService systemInfoService) {
    this.systemInfoService = systemInfoService;
  }

  @GetMapping("/info")
  public SystemInfo info() {
    return systemInfoService.current();
  }
}
