import "@testing-library/jest-dom/vitest";
import { afterEach } from "vitest";
import { cleanup } from "@testing-library/react";
import { resetQmindClient } from "@/api/qmindApi";
import { resetConfigCache } from "@/config/env";
import { abortAllInFlight } from "@/api/abortRegistry";
import { resetTenantContext } from "@/api/tenantContext";

// React 19 + Testing Library act support
(globalThis as unknown as { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT =
  true;

afterEach(() => {
  cleanup();
  abortAllInFlight("test_cleanup");
  resetQmindClient();
  resetTenantContext();
  resetConfigCache();
  sessionStorage.clear();
  localStorage.clear();
});
