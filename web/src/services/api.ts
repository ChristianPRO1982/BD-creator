const API_BASE = import.meta.env.VITE_API_BASE_URL || "";
const LOGIN_URL = API_BASE ? `${API_BASE}/login` : "/login";

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    credentials: "include",
    headers: {
      ...(init?.headers || {}),
    },
    ...init,
  });
  if (res.status === 401) {
    window.location.href = LOGIN_URL;
    throw new Error("unauthorized");
  }
  if (!res.ok) {
    const payload = await res.json().catch(() => ({}));
    throw new Error(payload.detail || "API error");
  }
  return res.json();
}

export const api = {
  get: <T>(path: string) => call<T>(path),
  post: <T>(path: string, body?: unknown) =>
    call<T>(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: body ? JSON.stringify(body) : undefined,
    }),
  patch: <T>(path: string, body: unknown) =>
    call<T>(path, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  del: <T>(path: string) => call<T>(path, { method: "DELETE" }),
};

export async function postForm<T>(path: string, form: FormData): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    credentials: "include",
    body: form,
  });
  if (res.status === 401) {
    window.location.href = LOGIN_URL;
    throw new Error("unauthorized");
  }
  if (!res.ok) {
    const payload = await res.json().catch(() => ({}));
    throw new Error(payload.detail || "API error");
  }
  return res.json();
}

export async function uploadComicAsset(comicId: string, file: File, name?: string) {
  const form = new FormData();
  form.append("file", file);
  if (name) form.append("name", name);
  const res = await fetch(`${API_BASE}/api/comics/${comicId}/assets/upload`, {
    method: "POST",
    credentials: "include",
    body: form,
  });
  if (!res.ok) {
    throw new Error("upload failed");
  }
  return res.json();
}
