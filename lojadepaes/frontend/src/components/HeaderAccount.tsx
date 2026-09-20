import { useEffect, useId, useRef, useState, type FormEvent } from "react";
import { accessMessage } from "../admin/accessMessages";
import { adminRequest, clearSession, rememberSession, storedCsrf } from "../admin/api";
import { goToPath, nextFromLocation } from "../admin/safePath";
import type { SessionInfo } from "../admin/types";
import {
  ArrowStrokeIcon,
  BackStrokeIcon,
  EyeOffStrokeIcon,
  EyeStrokeIcon,
  UserStrokeIcon,
} from "./HeaderIcons";

type HeaderAccountProps = {
  afterLogin?: "storefront" | "stay";
  initialSession?: SessionInfo | null;
};

type AccessMode = {
  local_passwordless: boolean;
};

type Step = "user" | "password";

const LOCAL_DEV_NAME = "desenvolvimento";

export function HeaderAccount({ afterLogin = "storefront", initialSession = null }: HeaderAccountProps) {
  const [session, setSession] = useState<SessionInfo | null>(initialSession);
  const [step, setStep] = useState<Step>("user");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [showPassword, setShowPassword] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [localPasswordless, setLocalPasswordless] = useState(false);
  const [accessReady, setAccessReady] = useState(Boolean(initialSession));
  const userId = useId();
  const passwordId = useId();
  const menuId = useId();
  const userRef = useRef<HTMLInputElement>(null);
  const passwordRef = useRef<HTMLInputElement>(null);
  const menuToggleRef = useRef<HTMLButtonElement>(null);
  const localEnterRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (initialSession) {
      setSession(initialSession);
      setAccessReady(true);
      return;
    }
    let cancelled = false;
    const hadSession = Boolean(storedCsrf());
    adminRequest<AccessMode>("/api/v1/admin/access")
      .then((mode) => {
        if (!cancelled) {
          setLocalPasswordless(Boolean(mode.local_passwordless));
          setAccessReady(true);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setLocalPasswordless(false);
          setAccessReady(true);
        }
      });
    adminRequest<SessionInfo>("/api/v1/admin/session")
      .then((info) => {
        if (cancelled) {
          return;
        }
        rememberSession(info.csrf_token, info.bakery_timezone);
        setSession(info);
        setMessage(null);
      })
      .catch(() => {
        if (cancelled) {
          return;
        }
        clearSession();
        setSession(null);
        if (hadSession) {
          setMessage("Sessão expirada. Entre novamente.");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [initialSession]);

  useEffect(() => {
    if (session || window.location.hash !== "#acesso") {
      return;
    }
    if (localPasswordless) {
      localEnterRef.current?.focus();
      return;
    }
    userRef.current?.focus();
  }, [session, localPasswordless]);

  useEffect(() => {
    if (session || step !== "password") {
      return;
    }
    passwordRef.current?.focus();
  }, [session, step]);

  useEffect(() => {
    if (!menuOpen) {
      return;
    }
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setMenuOpen(false);
        menuToggleRef.current?.focus();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [menuOpen]);

  function goToPasswordStep() {
    if (!username.trim()) {
      userRef.current?.focus();
      return;
    }
    setMessage(null);
    setStep("password");
  }

  function goToUserStep() {
    setPassword("");
    setShowPassword(false);
    setMessage(null);
    setStep("user");
    requestAnimationFrame(() => userRef.current?.focus());
  }

  async function enterLocal() {
    if (busy) {
      return;
    }
    setBusy(true);
    setMessage(null);
    try {
      const info = await adminRequest<SessionInfo>("/api/v1/admin/local-login", { method: "POST" });
      rememberSession(info.csrf_token, info.bakery_timezone);
      setSession(info);
      if (afterLogin === "storefront") {
        goToPath(nextFromLocation());
      }
    } catch (error: unknown) {
      setMessage(accessMessage(error));
      requestAnimationFrame(() => localEnterRef.current?.focus());
    } finally {
      setBusy(false);
    }
  }

  async function submitCredentials() {
    if (busy) {
      return;
    }
    if (!password) {
      passwordRef.current?.focus();
      return;
    }
    setBusy(true);
    setMessage(null);
    try {
      const info = await adminRequest<SessionInfo>("/api/v1/admin/login", {
        method: "POST",
        body: JSON.stringify({ username: username.trim(), password }),
      });
      rememberSession(info.csrf_token, info.bakery_timezone);
      setSession(info);
      setUsername("");
      setPassword("");
      setShowPassword(false);
      setStep("user");
      if (afterLogin === "storefront") {
        goToPath(nextFromLocation());
      }
    } catch (error: unknown) {
      setPassword("");
      setShowPassword(false);
      setMessage(accessMessage(error));
      requestAnimationFrame(() => passwordRef.current?.focus());
    } finally {
      setBusy(false);
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (step === "user") {
      goToPasswordStep();
      return;
    }
    void submitCredentials();
  }

  async function handleLogout() {
    try {
      await adminRequest("/api/v1/admin/logout", { method: "POST" });
    } catch {
      // restore the compact field anyway
    }
    clearSession();
    setSession(null);
    setMenuOpen(false);
    setUsername("");
    setPassword("");
    setShowPassword(false);
    setStep("user");
    setMessage(null);
    if (window.location.pathname.startsWith("/admin")) {
      goToPath("/#acesso");
    }
  }

  if (session) {
    const label = session.username?.trim() || "Conta";
    const short = label === LOCAL_DEV_NAME || label.length > 14 ? (label === LOCAL_DEV_NAME ? "Admin" : "Conta") : label;
    return (
      <div className="header-access header-access--session">
        <button
          ref={menuToggleRef}
          type="button"
          className="header-access-account"
          aria-expanded={menuOpen}
          aria-controls={menuId}
          aria-haspopup="menu"
          onClick={() => setMenuOpen((open) => !open)}
        >
          <UserStrokeIcon />
          <span>{short}</span>
        </button>
        <div id={menuId} className={menuOpen ? "header-account-menu is-open" : "header-account-menu"} role="menu">
          <a href="/admin/produtos" role="menuitem" onClick={() => setMenuOpen(false)}>
            Produtos
          </a>
          <a href="/admin/pedidos" role="menuitem" onClick={() => setMenuOpen(false)}>
            Pedidos
          </a>
          <button type="button" role="menuitem" onClick={() => void handleLogout()}>
            Sair
          </button>
        </div>
      </div>
    );
  }

  if (!accessReady) {
    return (
      <div className="header-access" aria-busy="true">
        <span className="header-access-icon" aria-hidden="true">
          <UserStrokeIcon />
        </span>
      </div>
    );
  }

  if (localPasswordless) {
    return (
      <form
        id="acesso"
        className={`header-access header-access--local${busy ? " is-busy" : ""}`}
        method="post"
        action="."
        onSubmit={(event) => {
          event.preventDefault();
          void enterLocal();
        }}
        aria-busy={busy}
      >
        <span className="header-access-icon" aria-hidden="true">
          <UserStrokeIcon />
        </span>
        <button
          ref={localEnterRef}
          className="header-access-local-enter"
          type="submit"
          disabled={busy}
          aria-label="Entrar como administrador"
        >
          Entrar
        </button>
        <span className="header-access-local-hint">local</span>
        {message ? (
          <p className="header-access-message" role="alert">
            {message}
          </p>
        ) : null}
      </form>
    );
  }

  return (
    <form
      id="acesso"
      className={`header-access${busy ? " is-busy" : ""}`}
      method="post"
      action="."
      onSubmit={handleSubmit}
      aria-busy={busy}
    >
      {step === "password" ? (
        <button type="button" className="header-access-icon-btn" aria-label="Editar usuário" onClick={goToUserStep}>
          <BackStrokeIcon />
        </button>
      ) : (
        <span className="header-access-icon" aria-hidden="true">
          <UserStrokeIcon />
        </span>
      )}
      <div className={`header-access-field${step === "password" ? " has-reveal" : ""}`}>
        <label htmlFor={userId} className="visually-hidden">
          Usuário
        </label>
        <input
          ref={userRef}
          id={userId}
          name="username"
          autoComplete="username"
          autoCapitalize="none"
          autoCorrect="off"
          spellCheck={false}
          maxLength={80}
          disabled={busy}
          placeholder="Usuário"
          value={username}
          onChange={(event) => {
            setUsername(event.target.value);
            setMessage(null);
          }}
          className={step === "user" ? "is-active" : "is-idle"}
          tabIndex={step === "user" ? 0 : -1}
          aria-hidden={step !== "user"}
        />
        <label htmlFor={passwordId} className="visually-hidden">
          Senha
        </label>
        <input
          ref={passwordRef}
          id={passwordId}
          name="password"
          type={showPassword ? "text" : "password"}
          autoComplete="current-password"
          maxLength={200}
          disabled={busy}
          placeholder="Senha"
          value={password}
          onChange={(event) => {
            setPassword(event.target.value);
            setMessage(null);
          }}
          className={step === "password" ? "is-active" : "is-idle"}
          tabIndex={step === "password" ? 0 : -1}
          aria-hidden={step !== "password"}
        />
        <button
          type="button"
          className="header-access-icon-btn header-access-eye"
          aria-hidden={step !== "password"}
          tabIndex={step === "password" ? 0 : -1}
          disabled={step !== "password"}
          aria-pressed={showPassword}
          aria-label={showPassword ? "Ocultar senha" : "Mostrar senha"}
          onClick={() => setShowPassword((open) => !open)}
        >
          {showPassword ? <EyeOffStrokeIcon /> : <EyeStrokeIcon />}
        </button>
      </div>
      <button
        className="header-access-icon-btn header-access-go"
        type="submit"
        disabled={busy}
        aria-label={step === "user" ? "Avançar" : busy ? "Entrando" : "Entrar"}
      >
        <ArrowStrokeIcon />
      </button>
      {message ? (
        <p className="header-access-message" role="alert">
          {message}
        </p>
      ) : null}
    </form>
  );
}
