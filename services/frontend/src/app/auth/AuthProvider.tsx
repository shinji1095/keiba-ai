import React from "react";

import { api } from "@/api/endpoints";
import { getApiBaseUrl } from "@/api/http";
import { TokenResponse } from "@/api/generated";

type AuthContextValue = {
  userToken: string | null;
  serviceToken: string | null;
  useServiceToken: boolean;
  activeToken: string | null;

  setServiceToken: (token: string | null) => void;
  setUseServiceToken: (v: boolean) => void;

  login: (username: string, password: string) => Promise<void>;
  register: (username: string, password: string) => Promise<void>;
  refresh: () => Promise<string | null>;
  logout: () => Promise<void>;
};

const AuthContext = React.createContext<AuthContextValue | null>(null);

type Stored = {
  userToken: string | null;
  issuedAt: string | null;
  expiresIn: number | null;
  serviceToken: string | null;
  useServiceToken: boolean;
};

const STORAGE_KEY = "keiba_dashboard_auth_v1";

function nowMs(): number {
  return Date.now();
}

function loadStored(): Stored {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return { userToken: null, issuedAt: null, expiresIn: null, serviceToken: null, useServiceToken: false };
    }
    const v = JSON.parse(raw) as Partial<Stored>;
    return {
      userToken: typeof v.userToken === "string" ? v.userToken : null,
      issuedAt: typeof v.issuedAt === "string" ? v.issuedAt : null,
      expiresIn: typeof v.expiresIn === "number" ? v.expiresIn : null,
      serviceToken: typeof v.serviceToken === "string" ? v.serviceToken : null,
      useServiceToken: typeof v.useServiceToken === "boolean" ? v.useServiceToken : false,
    };
  } catch {
    return { userToken: null, issuedAt: null, expiresIn: null, serviceToken: null, useServiceToken: false };
  }
}

function saveStored(st: Stored): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(st));
}

export function AuthProvider({ children }: { children: React.ReactNode }): React.JSX.Element {
  const [stored, setStored] = React.useState<Stored>(() => loadStored());
  const baseUrl = getApiBaseUrl();

  const activeToken = stored.useServiceToken ? stored.serviceToken : stored.userToken;

  const updateStored = React.useCallback((updater: (prev: Stored) => Stored) => {
    setStored((prev) => {
      const next = updater(prev);
      saveStored(next);
      return next;
    });
  }, []);

  const updateFromTokenResponse = React.useCallback(
    (tr: TokenResponse) => {
      const issuedAt = tr.issued_at ?? new Date().toISOString();
      updateStored((prev) => ({
        ...prev,
        userToken: tr.access_token,
        issuedAt,
        expiresIn: tr.expires_in,
      }));
    },
    [updateStored],
  );

  const setServiceToken = React.useCallback(
    (token: string | null) => {
      updateStored((prev) => ({ ...prev, serviceToken: token }));
    },
    [updateStored],
  );

  const setUseServiceToken = React.useCallback(
    (v: boolean) => {
      updateStored((prev) => ({ ...prev, useServiceToken: v }));
    },
    [updateStored],
  );

  const login = React.useCallback(
    async (username: string, password: string) => {
      const tr = await api.login({ baseUrl }, { username, password });
      updateFromTokenResponse(tr);
    },
    [baseUrl, updateFromTokenResponse],
  );

  const register = React.useCallback(
    async (username: string, password: string) => {
      const tr = await api.register({ baseUrl }, { username, password });
      updateFromTokenResponse(tr);
    },
    [baseUrl, updateFromTokenResponse],
  );

  const refreshInFlight = React.useRef<Promise<string | null> | null>(null);

  const refresh = React.useCallback(async (): Promise<string | null> => {
    if (refreshInFlight.current) return refreshInFlight.current;

    refreshInFlight.current = (async () => {
      try {
        const tr = await api.refresh({ baseUrl });
        updateFromTokenResponse(tr);
        return tr.access_token;
      } catch {
        updateStored((prev) => ({ ...prev, userToken: null, issuedAt: null, expiresIn: null, useServiceToken: false }));
        return null;
      } finally {
        refreshInFlight.current = null;
      }
    })();

    return refreshInFlight.current;
  }, [baseUrl, updateStored, updateFromTokenResponse]);

  const logout = React.useCallback(async () => {
    try {
      await api.logout({ baseUrl });
    } finally {
      updateStored((prev) => ({ ...prev, userToken: null, issuedAt: null, expiresIn: null, useServiceToken: false }));
    }
  }, [baseUrl, updateStored]);

  // Best-effort proactive refresh (only for user token).
  React.useEffect(() => {
    if (!stored.userToken || !stored.issuedAt || !stored.expiresIn) return;

    const issuedMs = Date.parse(stored.issuedAt);
    if (Number.isNaN(issuedMs)) return;

    const expMs = issuedMs + stored.expiresIn * 1000;
    const msLeft = expMs - nowMs();
    const refreshBeforeMs = 60_000;
    if (msLeft <= refreshBeforeMs) {
      void refresh();
      return;
    }

    const id = window.setTimeout(() => {
      void refresh();
    }, msLeft - refreshBeforeMs);

    return () => window.clearTimeout(id);
  }, [stored.userToken, stored.issuedAt, stored.expiresIn, refresh]);

  const value: AuthContextValue = {
    userToken: stored.userToken,
    serviceToken: stored.serviceToken,
    useServiceToken: stored.useServiceToken,
    activeToken,

    setServiceToken,
    setUseServiceToken,

    login,
    register,
    refresh,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuthContext(): AuthContextValue {
  const v = React.useContext(AuthContext);
  if (!v) throw new Error("AuthProvider is missing");
  return v;
}
