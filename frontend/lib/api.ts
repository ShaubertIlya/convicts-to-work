const API_ROOT = "/backend";

function cookie(name: string) {
  if (typeof document === "undefined") return "";
  const row = document.cookie.split("; ").find((item) => item.startsWith(`${name}=`));
  return row ? decodeURIComponent(row.split("=")[1]) : "";
}

export async function ensureCsrf() {
  await fetch(`${API_ROOT}/csrf/`, { credentials: "include" });
}

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const method = (options.method ?? "GET").toUpperCase();
  if (!["GET", "HEAD", "OPTIONS"].includes(method) && !cookie("csrftoken")) {
    await ensureCsrf();
  }
  const headers = new Headers(options.headers);
  if (options.body && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  const csrf = cookie("csrftoken");
  if (csrf) headers.set("X-CSRFToken", csrf);
  const response = await fetch(`${API_ROOT}${path}`, {
    ...options,
    headers,
    credentials: "include",
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: "Ошибка запроса" }));
    const detail = body.detail ?? body.non_field_errors?.[0];
    if (detail) throw new Error(detail);
    const fields = Object.entries(body)
      .flatMap(([field, messages]) => {
        const value = Array.isArray(messages) ? messages.join(" ") : String(messages);
        return value ? [`${field}: ${value}`] : [];
      })
      .join(" ");
    throw new Error(fields || "Ошибка запроса");
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}
