// Small helper: create an element and set its text safely
function makeEl(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text; // textContent, never innerHTML
  return node;
}

function makeLink(text, href) {
  const a = makeEl("a", "", text);
  a.href = href;
  return a;
}

// Builds the navbar inside <header id="navbar">.
// The links change with the login state and the user's role.
function renderNavbar() {
  const nav = document.getElementById("navbar");
  if (!nav) return;

  const user = getUser();
  nav.className = "navbar";

  const inner = makeEl("div", "navbar-inner");

  const brand = makeLink("MediBook", "index.html");
  brand.className = "brand";
  inner.appendChild(brand);

  // Left side links
  const links = makeEl("nav", "nav-links");
  links.appendChild(makeLink("Doctors", "index.html"));
  if (user && user.role === "patient") {
    links.appendChild(makeLink("My Appointments", "my-appointments.html"));
  } else if (user) {
    // Doctors and admins get a link to their own dashboard
    links.appendChild(makeLink("Dashboard", ROLE_HOME[user.role]));
  }
  inner.appendChild(links);

  // Right side: user info + logout, or login/register links
  const right = makeEl("div", "nav-user");
  if (user) {
    right.appendChild(makeEl("span", "", `Hi, ${user.first_name || user.username}`));
    const logoutBtn = makeEl("button", "link-btn", "Logout");
    logoutBtn.type = "button";
    logoutBtn.addEventListener("click", logout);
    right.appendChild(logoutBtn);
  } else {
    right.appendChild(makeLink("Login", "login.html"));
    right.appendChild(makeLink("Register", "register.html"));
  }
  inner.appendChild(right);

  nav.replaceChildren(inner);
}