const hospitalSelect = document.getElementById("hospital");
const departmentSelect = document.getElementById("department");
const searchInput = document.getElementById("search");
const listEl = document.getElementById("doctor-list");
const statusEl = document.getElementById("status");

// Used to ignore out-of-date responses (see loadDoctors)
let requestCounter = 0;
let searchTimer = null;

function setStatus(text, isError = false) {
  statusEl.textContent = text;
  statusEl.className = isError ? "status error" : "status";
}

/* ---------- Filters: load dropdown options ---------- */
async function loadHospitals() {
  // Public endpoint, so auth: false (an expired token can't break this page)
  const res = await apiFetch("/hospitals", { auth: false });
  if (!res.ok) return;
  res.data.forEach((h) => {
    hospitalSelect.appendChild(new Option(`${h.name} (${h.city})`, h.id));
  });
}

// Department options depend on the selected hospital
async function loadDepartments(hospitalId) {
  departmentSelect.length = 1; // keep only the "All departments" option
  departmentSelect.disabled = true;
  if (!hospitalId) return;

  const res = await apiFetch(`/hospitals/${hospitalId}/departments`, { auth: false });
  if (!res.ok) return;
  res.data.forEach((d) => departmentSelect.appendChild(new Option(d.name, d.id)));
  departmentSelect.disabled = false;
}

/* ---------- Doctor list ---------- */
async function loadDoctors() {
  // Each call gets a number. If the user changes a filter while a request is
  // still running, the older response arrives late and must be ignored,
  // otherwise it could overwrite the newer results.
  const myRequest = ++requestCounter;

  // URLSearchParams builds the query string and encodes special characters
  const params = new URLSearchParams();
  if (hospitalSelect.value) params.set("hospital", hospitalSelect.value);
  if (departmentSelect.value) params.set("department", departmentSelect.value);
  if (searchInput.value.trim()) params.set("search", searchInput.value.trim());
  const query = params.toString();

  setStatus("Loading doctors...");
  const res = await apiFetch("/doctors" + (query ? `?${query}` : ""), { auth: false });

  if (myRequest !== requestCounter) return; // stale response, drop it

  if (!res.ok) {
    listEl.replaceChildren();
    setStatus(errorText(res.data), true);
    return;
  }
  renderDoctors(res.data);
}

function renderDoctors(doctors) {
  listEl.replaceChildren(); // clear the old cards
  if (doctors.length === 0) {
    setStatus("No doctors found. Try changing the filters.");
    return;
  }
  setStatus(`${doctors.length} doctor${doctors.length > 1 ? "s" : ""} found`);
  doctors.forEach((d) => listEl.appendChild(doctorCard(d)));
}

// Cards are built with DOM methods (not innerHTML) so server data can never
// be interpreted as HTML.
function doctorCard(d) {
  const card = makeEl("div", "doctor-card");
  card.appendChild(makeEl("h3", "", d.name));
  card.appendChild(makeEl("p", "doc-meta", `${d.department} · ${d.hospital}`));
  card.appendChild(makeEl("p", "doc-detail", d.qualification));
  card.appendChild(makeEl("p", "doc-detail", `${d.experience_years} years experience`));
  card.appendChild(
    makeEl("p", "doc-fee", `Fee: ₹${Number(d.consultation_fee).toLocaleString("en-IN")}`)
  );

  // book.html (next step) reads the doctor id from the URL
  const bookLink = makeEl("a", "btn", "Book appointment");
  bookLink.href = `book.html?doctor=${d.id}`;
  card.appendChild(bookLink);
  return card;
}

/* ---------- Events ---------- */
hospitalSelect.addEventListener("change", () => {
  loadDepartments(hospitalSelect.value); // a new hospital means a new department list
  loadDoctors();
});

departmentSelect.addEventListener("change", loadDoctors);

// Debounce: wait 350 ms after the last keystroke before calling the API,
// so typing "sharma" sends 1 request instead of 6.
searchInput.addEventListener("input", () => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(loadDoctors, 350);
});

/* ---------- Start ---------- */
renderNavbar();
loadHospitals();
loadDoctors();