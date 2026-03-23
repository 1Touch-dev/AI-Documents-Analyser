"use client";

import { createContext, useContext, useMemo, useState } from "react";

type AppPreferences = {
  selectedModel: string;
  selectedCategory: string;
  selectedPromptTemplate: string;
  openaiApiKey: string;
  anthropicApiKey: string;
  geminiApiKey: string;
};

type AppPreferencesContextValue = AppPreferences & {
  setSelectedModel: (value: string) => void;
  setSelectedCategory: (value: string) => void;
  setSelectedPromptTemplate: (value: string) => void;
  setOpenaiApiKey: (value: string) => void;
  setAnthropicApiKey: (value: string) => void;
  setGeminiApiKey: (value: string) => void;
};

const STORAGE_KEY = "akp_preferences";

const AppPreferencesContext = createContext<AppPreferencesContextValue | null>(null);

function loadInitial(): AppPreferences {
  if (typeof window === "undefined") {
    return {
      selectedModel: "auto",
      selectedCategory: "general",
      selectedPromptTemplate: "",
      openaiApiKey: "",
      anthropicApiKey: "",
      geminiApiKey: "",
    };
  }

  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) throw new Error("no local data");
    const parsed = JSON.parse(raw) as Partial<AppPreferences>;
    return {
      selectedModel: parsed.selectedModel || "auto",
      selectedCategory: parsed.selectedCategory || "general",
      selectedPromptTemplate: parsed.selectedPromptTemplate || "",
      openaiApiKey: parsed.openaiApiKey || "",
      anthropicApiKey: parsed.anthropicApiKey || "",
      geminiApiKey: parsed.geminiApiKey || "",
    };
  } catch {
    return {
      selectedModel: "auto",
      selectedCategory: "general",
      selectedPromptTemplate: "",
      openaiApiKey: "",
      anthropicApiKey: "",
      geminiApiKey: "",
    };
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
      setSelectedModel: (selectedModel) => persist({ ...prefs, selectedModel }),
      setSelectedCategory: (selectedCategory) => persist({ ...prefs, selectedCategory }),
      setSelectedPromptTemplate: (selectedPromptTemplate) =>
        persist({ ...prefs, selectedPromptTemplate }),
      setOpenaiApiKey: (openaiApiKey) => persist({ ...prefs, openaiApiKey }),
      setAnthropicApiKey: (anthropicApiKey) => persist({ ...prefs, anthropicApiKey }),
      setGeminiApiKey: (geminiApiKey) => persist({ ...prefs, geminiApiKey }),
    }),
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

