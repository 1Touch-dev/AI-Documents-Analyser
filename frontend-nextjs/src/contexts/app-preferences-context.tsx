"use client";

import { createContext, useContext, useMemo, useState } from "react";

// All currencies accepted by the backend API.
export const SUPPORTED_CURRENCY_CODES = [
  "BRL","USD","CAD","MXN","ARS","CLP","COP","PEN",
  "EUR","GBP","CHF","NOK","SEK","DKK","PLN","CZK","HUF","RON","TRY","RUB","UAH",
  "JPY","CNY","INR","KRW","SGD","HKD","TWD","THB","IDR","MYR","PHP","VND",
  "AUD","NZD",
  "AED","SAR","QAR","ILS","EGP","ZAR","NGN","KES","PKR","BDT",
] as const;

export type CurrencyCode = (typeof SUPPORTED_CURRENCY_CODES)[number];

type AppPreferences = {
  selectedProvider: string;   // "openai" | "bedrock"
  selectedModel: string;
  bedrockCustomModel: string; // free-text override for any Bedrock model ID
  selectedCategory: string;
  selectedPromptTemplate: string;
  openaiApiKey: string;
  anthropicApiKey: string;
  geminiApiKey: string;
  translateToEnglish: boolean;
  targetCurrency: string;
};

type AppPreferencesContextValue = AppPreferences & {
  setSelectedProvider: (value: string) => void;
  setSelectedModel: (value: string) => void;
  setBedrockCustomModel: (value: string) => void;
  setSelectedCategory: (value: string) => void;
  setSelectedPromptTemplate: (value: string) => void;
  setOpenaiApiKey: (value: string) => void;
  setAnthropicApiKey: (value: string) => void;
  setGeminiApiKey: (value: string) => void;
  setTranslateToEnglish: (value: boolean) => void;
  setTargetCurrency: (value: string) => void;
  // Atomic multi-field update — avoids stale-closure overwrite when several
  // fields must change together (e.g. switching provider resets model too).
  updatePrefs: (patch: Partial<AppPreferences>) => void;
};

const STORAGE_KEY = "akp_preferences";

const AppPreferencesContext = createContext<AppPreferencesContextValue | null>(null);

function isValidCurrency(code: unknown): code is string {
  return typeof code === "string" && (SUPPORTED_CURRENCY_CODES as readonly string[]).includes(code);
}

function loadInitial(): AppPreferences {
  const defaults: AppPreferences = {
    selectedProvider: "openai",
    selectedModel: "auto",
    bedrockCustomModel: "",
    selectedCategory: "general",
    selectedPromptTemplate: "",
    openaiApiKey: "",
    anthropicApiKey: "",
    geminiApiKey: "",
    translateToEnglish: false,
    targetCurrency: "BRL",
  };

  if (typeof window === "undefined") return defaults;

  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return defaults;
    const parsed = JSON.parse(raw) as Partial<AppPreferences>;
    return {
      selectedProvider: parsed.selectedProvider || "openai",
      selectedModel: parsed.selectedModel || "auto",
      bedrockCustomModel: parsed.bedrockCustomModel || "",
      selectedCategory: parsed.selectedCategory || "general",
      selectedPromptTemplate: parsed.selectedPromptTemplate || "",
      openaiApiKey: parsed.openaiApiKey || "",
      anthropicApiKey: parsed.anthropicApiKey || "",
      geminiApiKey: parsed.geminiApiKey || "",
      translateToEnglish: Boolean(parsed.translateToEnglish),
      targetCurrency: isValidCurrency(parsed.targetCurrency)
        ? parsed.targetCurrency
        : "BRL",
    };
  } catch {
    return defaults;
  }
}

export function AppPreferencesProvider({ children }: { children: React.ReactNode }) {
  const [prefs, setPrefs] = useState<AppPreferences>(loadInitial);

  const persist = (next: AppPreferences) => {
    setPrefs(next);
    if (typeof window !== "undefined") {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    }
  };

  const value = useMemo<AppPreferencesContextValue>(
    () => ({
      ...prefs,
      updatePrefs: (patch: Partial<AppPreferences>) => persist({ ...prefs, ...patch }),
      setSelectedProvider: (selectedProvider) => persist({ ...prefs, selectedProvider }),
      setSelectedModel: (selectedModel) => persist({ ...prefs, selectedModel }),
      setBedrockCustomModel: (bedrockCustomModel) => persist({ ...prefs, bedrockCustomModel }),
      setSelectedCategory: (selectedCategory) => persist({ ...prefs, selectedCategory }),
      setSelectedPromptTemplate: (selectedPromptTemplate) =>
        persist({ ...prefs, selectedPromptTemplate }),
      setOpenaiApiKey: (openaiApiKey) => persist({ ...prefs, openaiApiKey }),
      setAnthropicApiKey: (anthropicApiKey) => persist({ ...prefs, anthropicApiKey }),
      setGeminiApiKey: (geminiApiKey) => persist({ ...prefs, geminiApiKey }),
      setTranslateToEnglish: (translateToEnglish) => persist({ ...prefs, translateToEnglish }),
      setTargetCurrency: (targetCurrency) => persist({ ...prefs, targetCurrency }),
    }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [prefs]
  );

  return (
    <AppPreferencesContext.Provider value={value}>{children}</AppPreferencesContext.Provider>
  );
}

export function useAppPreferences() {
  const context = useContext(AppPreferencesContext);
  if (!context) {
    throw new Error("useAppPreferences must be used inside AppPreferencesProvider");
  }
  return context;
}
