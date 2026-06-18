import { createContext, useContext, useMemo, useState } from "react";

type AuthContextValue = {
  token: string | null;
  isLoggedIn: boolean;
  login: (token: string) => void;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(() => {
    if (typeof window === "undefined") return null;
    return localStorage.getItem("auth_token");
  });

  const value = useMemo<AuthContextValue>(
    () => ({
      token,
      isLoggedIn: Boolean(token),
      login: (newToken) => {
        localStorage.setItem("auth_token", newToken);
        setToken(newToken);
      },
      logout: () => {
        localStorage.removeItem("auth_token");
        setToken(null);
      },
    }),
    [token]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return ctx;
}
