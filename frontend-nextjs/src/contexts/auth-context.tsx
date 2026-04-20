"use client";

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useSyncExternalStore,
} from "react";
import * as api from "@/lib/api";

type AuthContextValue = {
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  loginUser: (username: string, password: string) => Promise<void>;
  registerUser: (username: string, password: string) => Promise<void>;
  logout: () => void;
};

const TOKEN_STORAGE_KEY = "akp_token";
const TOKEN_COOKIE_KEY = "akp_token";
const AUTH_CHANGE_EVENT = "akp-auth-change";

const AuthContext = createContext<AuthContextValue | null>(null);

function readCookieToken() {
  if (typeof document === "undefined") {
    return null;
  }

  const match = document.cookie.match(/(?:^|; )akp_token=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : null;
}

function readBrowserToken() {
  if (typeof window === "undefined") {
    return null;
  }

  try {
    return localStorage.getItem(TOKEN_STORAGE_KEY) || readCookieToken();
  } catch {
    return readCookieToken();
  }
}

function setBrowserToken(token: string) {
  try {
    localStorage.setItem(TOKEN_STORAGE_KEY, token);
  } catch {
    // Ignore storage issues and rely on cookie fallback.
  }
  document.cookie = `${TOKEN_COOKIE_KEY}=${encodeURIComponent(
    token
  )}; Path=/; SameSite=Strict; Max-Age=86400`;
}

function clearBrowserToken() {
  try {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
  } catch {
    // Ignore storage issues during logout.
  }
  document.cookie = `${TOKEN_COOKIE_KEY}=; Path=/; Max-Age=0; SameSite=Strict`;
}

function emitAuthChange() {
  if (typeof window === "undefined") {
    return;
  }
  window.dispatchEvent(new Event(AUTH_CHANGE_EVENT));
}

function subscribeToAuthChanges(callback: () => void) {
  if (typeof window === "undefined") {
    return () => {};
  }

  const handler = () => callback();
  window.addEventListener("storage", handler);
  window.addEventListener(AUTH_CHANGE_EVENT, handler);

  return () => {
    window.removeEventListener("storage", handler);
    window.removeEventListener(AUTH_CHANGE_EVENT, handler);
  };
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const token = useSyncExternalStore(subscribeToAuthChanges, readBrowserToken, () => null);
  const isHydrated = useSyncExternalStore(
    () => () => {},
    () => true,
    () => false
  );
  const isLoading = !isHydrated;

  const loginUser = useCallback(async (username: string, password: string) => {
    const response = await api.login(username, password);
    setBrowserToken(response.access_token);
    emitAuthChange();
  }, []);

  const registerUser = useCallback(async (username: string, password: string) => {
    const response = await api.register(username, password);
    setBrowserToken(response.access_token);
    emitAuthChange();
  }, []);

  const logout = useCallback(() => {
    clearBrowserToken();
    emitAuthChange();
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      token,
      isAuthenticated: Boolean(token),
      isLoading,
      loginUser,
      registerUser,
      logout,
    }),
    [token, isLoading, loginUser, registerUser, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used inside AuthProvider");
  }
  return context;
}
