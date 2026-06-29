import { createContext, useContext, useEffect, useState, ReactNode, useCallback } from "react";
import { api, setTokens, clearToken, getToken, getRefresh } from "@/lib/api";
import { applyBranding } from "@/lib/branding";
import type { Me } from "@/types";

interface AuthCtx {
  user: Me | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  can: (code: string) => boolean;
}

const Ctx = createContext<AuthCtx>(null as unknown as AuthCtx);
export const useAuth = () => useContext(Ctx);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<Me | null>(null);
  const [loading, setLoading] = useState(true);

  const loadMe = useCallback(async () => {
    if (!getToken()) { setLoading(false); return; }
    try {
      const me = await api.get("/auth/me");
      setUser(me);
      api.get("/settings/branding").then(applyBranding).catch(() => {});
    } catch {
      clearToken();
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadMe(); }, [loadMe]);

  const login = async (email: string, password: string) => {
    const res = await api.login(email, password);
    setTokens(res.access_token, res.refresh_token);
    const me = await api.get("/auth/me");
    setUser(me);
    api.get("/settings/branding").then(applyBranding).catch(() => {});
  };

  const logout = () => {
    const refresh = getRefresh();
    if (refresh) api.post("/auth/logout", { refresh_token: refresh }).catch(() => {});
    clearToken();
    setUser(null);
  };

  // Owner has all permissions (backend also enforces). UI convenience:
  const can = (code: string) =>
    !!user && (user.role_name === "Owner" || user.permissions.includes(code));

  return (
    <Ctx.Provider value={{ user, loading, login, logout, can }}>
      {children}
    </Ctx.Provider>
  );
}
