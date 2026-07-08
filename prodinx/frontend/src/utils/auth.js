const AUTH_STORAGE_KEY = "isAuthenticated";

function readStoredAuth() {
  if (typeof window === "undefined") {
    return false;
  }

  // Limpa flag legada que mantinha sessão entre reinícios do browser.
  localStorage.removeItem(AUTH_STORAGE_KEY);

  return sessionStorage.getItem(AUTH_STORAGE_KEY) === "true";
}

export function isAuthenticated() {
  return readStoredAuth();
}

export function setAuthenticated(value) {
  if (typeof window === "undefined") {
    return;
  }

  if (value) {
    sessionStorage.setItem(AUTH_STORAGE_KEY, "true");
  } else {
    sessionStorage.removeItem(AUTH_STORAGE_KEY);
  }
}

export function clearAuthentication() {
  setAuthenticated(false);
}
