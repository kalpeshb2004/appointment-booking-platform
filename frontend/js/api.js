// Backend base URL. Change only this line when deploying.
const API_BASE = "http://127.0.0.1:8000/api";

/* ---------- Token storage ---------- */
// localStorage keeps the user logged in even after the tab is closed.
function getTokens() {
  return {
    access: localStorage.getItem("access"),
    refresh: localStorage.getItem("refresh"),
  };
}

// Save the login response (access, refresh, user)
function saveSession(data) {
  localStorage.setItem("access", data.access);
  localStorage.setItem("refresh", data.refresh);
  localStorage.setItem("user", JSON.stringify(data.user));
}

// Remove only our own keys (localStorage.clear() would wipe other data too)
function clearSession() {
  ["access", "refresh", "user"].forEach((k) => localStorage.removeItem(k));
}

/* ---------- Get a new access token using the refresh token ---------- */
async function refreshAccessToken() {
  const { refresh } = getTokens();
  if (!refresh) return false;
  try {
    const res = await fetch(`${API_BASE}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh }),
    });
    if (!res.ok) return false; // the refresh token has expired too
    const data = await res.json();
    localStorage.setItem("access", data.access);
    return true;
  } catch {
    return false;
  }
}

/* ---------- Central fetch wrapper ----------
   Every API call goes through here: auth header, JSON and error handling
   live in one place. Always returns { ok, status, data } and never throws. */
async function apiFetch(path, { method = "GET", body = null, auth = true } = {}, retry = true) {
  const headers = { "Content-Type": "application/json" };
  const { access } = getTokens();
  if (auth && access) headers["Authorization"] = `Bearer ${access}`;

  let res;
  try {
    res = await fetch(API_BASE + path, {
      method,
      headers,
      body: body ? JSON.stringify(body) : null,
    });
  } catch {
    // Network error: server is down or the request was blocked by CORS
    return {
      ok: false,
      status: 0,
      data: { detail: "Could not connect to the server. Is the backend running?" },
    };
  }

  // 401 means the access token expired. Refresh once and retry the request.
  // retry=false prevents an infinite loop if the retry also returns 401.
  if (res.status === 401 && auth && retry) {
    if (await refreshAccessToken()) {
      return apiFetch(path, { method, body, auth }, false);
    }
    logout(); // refresh failed too: send the user to the login page
  }

  let data = null;
  try {
    data = await res.json(); // 204 responses have no body, hence the try/catch
  } catch {}
  return { ok: res.ok, status: res.status, data };
}

/* ---------- Turn DRF error shapes into readable text ----------
   DRF returns either {"detail": "..."} or {"field": ["..."], ...} */
function errorText(data) {
  if (!data) return "Something went wrong.";
  if (typeof data === "string") return data;
  if (data.detail) return data.detail;
  return Object.entries(data)
    .map(([field, msgs]) => `${field}: ${Array.isArray(msgs) ? msgs.join(" ") : msgs}`)
    .join("\n");
}

// Show a message in a box. textContent (not innerHTML) is used so server text
// is never parsed as HTML, which protects against XSS.
function showMessage(el, text, type = "error") {
  el.textContent = text;
  el.className = `msg ${type}`;
}

// "2026-11-23" -> "Mon, 23 Nov 2026". Parsed manually to avoid the UTC shift.
function prettyDate(str) {
  const [y, m, d] = str.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString("en-IN", {
    weekday: "short", day: "numeric", month: "short", year: "numeric",
  });
}

// Local YYYY-MM-DD string. toISOString() converts to UTC and can shift the
// date by one day, so the string is built from local date parts instead.
function toDateString(d) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}