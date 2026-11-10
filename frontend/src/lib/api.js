export const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
const API_KEY = import.meta.env.VITE_API_KEY || "";

export async function getJson(path, signal) {
  const res = await fetch(`${API_URL}${path}`, { signal });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

/** POST to a mutating endpoint; sends the API key when one is configured. */
export async function post(path) {
  const res = await fetch(`${API_URL}${path}`, {
    method: "POST",
    headers: API_KEY ? { "X-API-Key": API_KEY } : {},
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(body.detail || `${res.status} ${res.statusText}`);
  return body;
}

export const injectFault = (service, fault) => post(`/api/services/${service}/fault/${fault}`);
