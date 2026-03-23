"use client";

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
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

const AuthContext = createContext<AuthContextValue | null>(null);

function setBrowserToken(token: string) {
  localStorage.setItem(TOKEN_STORAGE_KEY, token);
  document.cookie = `${TOKEN_COOKIE_KEY}=${encodeURIComponent(
    token
  )}; Path=/; SameSite=Strict; Max-Age=86400`;
}

function clearBrowserToken() {
  localStorage.removeItem(TOKEN_STORAGE_KEY);
  document.cookie = `${TOKEN_COOKIE_KEY}=; Path=/; Max-Age=0; SameSite=Strict`;
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(() => {
    if (typeof window === "undefined") {
      return null;
    }
    return localStorage.getItem(TOKEN_STORAGE_KEY);
  });
  const isLoading = false;

  const loginUser = useCallback(async (username: string, password: string) => {
    const response = await api.login(username, password);
    setBrowserToken(response.access_token);
    setToken(response.access_token);
  }, []);

  const registerUser = useCallback(async (username: string, password: string) => {
    const response = await api.register(username, password);
    setBrowserToken(response.access_token);
    setToken(response.access_token);
  }, []);

  const logout = useCallback(() => {
    clearBrowserToken();
    setToken(null);
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

