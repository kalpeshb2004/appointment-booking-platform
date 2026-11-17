// Which page each role lands on after login
const ROLE_HOME = {
  patient: "index.html",
  doctor: "doctor-dashboard.html", // will be built later
  admin: "admin-dashboard.html",
};

function getUser() {
  try {
    return JSON.parse(localStorage.getItem("user"));
  } catch {
    return null;
  }
}

function logout() {
  clearSession();
  window.location.href = "login.html";
}

// Call at the top of a protected page. Not logged in: go to login.
// Wrong role: go to that role's own home page.
// NOTE: this is only UX. Real security is enforced by backend permissions (403).
function requireLogin(allowedRoles = null) {
  const user = getUser();
    if (!user || !getTokens().access) {
    // Remember the page so login can send the user back here
    const here = window.location.pathname.split("/").pop() + window.location.search;
    window.location.href = "login.html?next=" + encodeURIComponent(here);
    return null;
  }
  if (allowedRoles && !allowedRoles.includes(user.role)) {
    window.location.href = ROLE_HOME[user.role];
    return null;
  }
  return user;

  // Safe redirect target after login. Only a same-folder .html page is allowed,
// so ?next=https://evil.com can never send the user to another site (open redirect).
function safeNext() {
  const next = new URLSearchParams(window.location.search).get("next");
  return next && /^[\w-]+\.html(\?[\w=&%.-]*)?$/.test(next) ? next : null;
}
}

/* ---------- Login page ---------- */
const loginForm = document.getElementById("login-form");
if (loginForm) {
  // Already logged in: skip the form
  const existing = getUser();
  if (existing && getTokens().access) {
    window.location.href = ROLE_HOME[existing.role];
  }

  loginForm.addEventListener("submit", async (e) => {
    e.preventDefault(); // stop the page from reloading
    const msg = document.getElementById("msg");
    const btn = loginForm.querySelector("button");

    btn.disabled = true; // prevents duplicate requests on double click
    btn.textContent = "Logging in...";

    const res = await apiFetch("/auth/login", {
      method: "POST",
      auth: false, // no token needed to log in
      body: {
        username: document.getElementById("username").value.trim(),
        password: document.getElementById("password").value,
      },
    });

    if (res.ok) {
      saveSession(res.data);
      window.location.href = safeNext() || ROLE_HOME[res.data.user.role];
    } else {
      showMessage(msg, errorText(res.data));
      btn.disabled = false;
      btn.textContent = "Login";
    }
  });
}

/* ---------- Register page ---------- */
const registerForm = document.getElementById("register-form");
if (registerForm) {
  registerForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const msg = document.getElementById("msg");
    const btn = registerForm.querySelector("button");
    const val = (id) => document.getElementById(id).value.trim();

    btn.disabled = true;
    btn.textContent = "Creating account...";

    // Empty optional fields are not sent, so the backend uses its defaults
    const body = {
      username: val("username"),
      email: val("email"),
      password: document.getElementById("password").value,
      first_name: val("first_name"),
    };
    if (val("phone")) body.phone = val("phone");
    if (val("gender")) body.gender = val("gender");

    const res = await apiFetch("/auth/register", { method: "POST", auth: false, body });

    if (res.ok) {
      showMessage(msg, "Account created. Redirecting to login...", "success");
      setTimeout(() => (window.location.href = "login.html"), 1200);
    } else {
      showMessage(msg, errorText(res.data));
      btn.disabled = false;
      btn.textContent = "Register";
    }
  });
}