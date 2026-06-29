const BASE = import.meta.env.VITE_API_BASE || "/api";
const TOKEN_KEY = "sainext_token";
const REFRESH_KEY = "sainext_refresh";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}
export function getRefresh(): string | null {
  return localStorage.getItem(REFRESH_KEY);
}
export function setTokens(access: string, refresh?: string | null) {
  localStorage.setItem(TOKEN_KEY, access);
  if (refresh) localStorage.setItem(REFRESH_KEY, refresh);
}
// kept for backward compatibility
export function setToken(t: string) {
  localStorage.setItem(TOKEN_KEY, t);
}
export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_KEY);
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

function authHeaders(extra: Record<string, string> = {}) {
  const t = getToken();
  return t ? { ...extra, Authorization: `Bearer ${t}` } : extra;
}

async function parse(res: Response) {
  if (res.status === 204) return null;
  const text = await res.text();
  const data = text ? JSON.parse(text) : null;
  if (!res.ok) {
    const msg = data?.detail
      ? Array.isArray(data.detail)
        ? data.detail.map((d: any) => d.msg).join(", ")
        : data.detail
      : `Request failed (${res.status})`;
    throw new ApiError(res.status, msg);
  }
  return data;
}

// single-flight refresh so concurrent 401s share one refresh call
let refreshing: Promise<boolean> | null = null;

async function tryRefresh(): Promise<boolean> {
  const refresh = getRefresh();
  if (!refresh) return false;
  if (!refreshing) {
    refreshing = (async () => {
      try {
        const res = await fetch(`${BASE}/auth/refresh`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh_token: refresh }),
        });
        if (!res.ok) return false;
        const data = await res.json();
        setTokens(data.access_token, data.refresh_token);
        return true;
      } catch {
        return false;
      } finally {
        // reset after microtask so awaiting callers read the result first
        setTimeout(() => (refreshing = null), 0);
      }
    })();
  }
  return refreshing;
}

interface ReqOpts {
  method?: string;
  body?: unknown;
  raw?: boolean; // return Response instead of parsed JSON (for downloads)
  _retried?: boolean;
}

async function request(path: string, opts: ReqOpts = {}): Promise<any> {
  const { method = "GET", body, raw } = opts;
  const init: RequestInit = { method, headers: authHeaders() };
  if (body !== undefined) {
    init.headers = authHeaders({ "Content-Type": "application/json" });
    init.body = JSON.stringify(body);
  }
  const res = await fetch(`${BASE}${path}`, init);

  // transparently refresh once on 401, then retry the original request
  if (res.status === 401 && !opts._retried && getRefresh() && !path.startsWith("/auth/")) {
    if (await tryRefresh()) {
      return request(path, { ...opts, _retried: true });
    }
    clearToken();
  }
  if (res.status === 401 && path !== "/auth/login") clearToken();
  return raw ? res : parse(res);
}

export const api = {
  async login(email: string, password: string) {
    const body = new URLSearchParams({ username: email, password });
    const res = await fetch(`${BASE}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body,
    });
    return parse(res);
  },
  get(path: string) {
    return request(path);
  },
  post(path: string, body?: unknown) {
    return request(path, { method: "POST", body: body ?? {} });
  },
  put(path: string, body?: unknown) {
    return request(path, { method: "PUT", body: body ?? {} });
  },
  del(path: string) {
    return request(path, { method: "DELETE" });
  },
  async download(path: string, fallbackName = "download") {
    const res: Response = await request(path, { raw: true });
    if (!res.ok) throw new ApiError(res.status, `Download failed (${res.status})`);
    const blob = await res.blob();
    const cd = res.headers.get("Content-Disposition") || "";
    const m = cd.match(/filename=([^;]+)/);
    const name = m ? m[1].trim() : fallbackName;
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = name;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  },
};
