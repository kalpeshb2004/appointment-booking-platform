const dateInput = document.getElementById("date");
const filterSelect = document.getElementById("filter");
const statsEl = document.getElementById("stats");
const listEl = document.getElementById("appt-list");
const statusEl = document.getElementById("status");
const msgEl = document.getElementById("msg");

const STATUS_LABEL = {
  booked: "Booked",
  completed: "Completed",
  cancelled: "Cancelled",
  no_show: "No show",
};
const GENDER_LABEL = { M: "Male", F: "Female", O: "Other" };

let requestCounter = 0; // ignores stale responses when filters change quickly

function setStatus(text, isError = false) {
  statusEl.textContent = text;
  statusEl.className = isError ? "status error" : "status";
}

/* ---------- Load the list ---------- */
async function loadAppointments() {
  const myRequest = ++requestCounter;
  setStatus("Loading appointments...");

  // Build the query string from the filters. An empty date means all dates.
  const params = new URLSearchParams();
  if (dateInput.value) params.set("date", dateInput.value);
  if (filterSelect.value) params.set("status", filterSelect.value);
  const query = params.toString();

  const res = await apiFetch("/doctor/appointments" + (query ? `?${query}` : ""));
  if (myRequest !== requestCounter) return; // a newer filter was chosen, drop this

  if (!res.ok) {
    listEl.replaceChildren();
    statsEl.replaceChildren();
    setStatus(errorText(res.data), true);
    return;
  }

  const list = res.data.appointments;
  renderStats(list);
  listEl.replaceChildren();
  if (list.length === 0) {
    setStatus("No appointments found for these filters.");
    return;
  }
  setStatus("");
  list.forEach((a) => listEl.appendChild(appointmentCard(a)));
}

/* ---------- Summary counts (calculated from the loaded list) ---------- */
function renderStats(list) {
  const count = (s) => list.filter((a) => a.status === s).length;
  const items = [
    ["Total", list.length],
    ["Booked", count("booked")],
    ["Completed", count("completed")],
    ["No show", count("no_show")],
  ];
  statsEl.replaceChildren(
    ...items.map(([label, value]) => {
      const box = makeEl("div", "stat");
      box.appendChild(makeEl("strong", "", String(value)));
      box.appendChild(makeEl("span", "", label));
      return box;
    })
  );
}

/* ---------- One appointment card ----------
   Built with DOM methods (not innerHTML) so server data is never parsed as HTML. */
function appointmentCard(a) {
  const card = makeEl("div", "appt-card");

  const head = makeEl("div", "appt-head");
  head.appendChild(makeEl("h3", "", a.patient_name));
  head.appendChild(makeEl("span", `badge ${a.status}`, STATUS_LABEL[a.status] || a.status));
  card.appendChild(head);

  card.appendChild(
    makeEl("p", "appt-when", `${prettyDate(a.date)} · ${a.start_time.slice(0, 5)} - ${a.end_time.slice(0, 5)}`)
  );

  // Only the details the doctor needs: gender and phone (no email or date of birth)
  const info = [GENDER_LABEL[a.patient_gender], a.patient_phone].filter(Boolean).join(" · ");
  if (info) card.appendChild(makeEl("p", "doc-detail", info));
  if (a.reason) card.appendChild(makeEl("p", "doc-detail", `Reason: ${a.reason}`));

  // Actions are shown only for booked appointments
  if (a.status === "booked") {
    const actions = makeEl("div", "appt-actions");

    // The backend rejects marking a future appointment (400 too_early).
    // The UI mirrors that rule so the doctor does not see buttons that cannot work.
    // "2026-11-23T10:00:00" without a timezone is read as local time.
    const started = new Date(`${a.date}T${a.start_time}`) <= new Date();

    if (started) {
      actions.appendChild(actionButton("Mark completed", "btn-ok", a, "completed"));
      actions.appendChild(actionButton("No show", "btn-danger", a, "no_show"));
    } else {
      actions.appendChild(makeEl("span", "hint", "Can be marked once the appointment time starts."));
    }
    card.appendChild(actions);
  }
  return card;
}

function actionButton(text, className, a, newStatus) {
  const btn = makeEl("button", className, text);
  btn.type = "button";
  btn.addEventListener("click", () => updateStatus(a, newStatus, btn, text));
  return btn;
}

/* ---------- Mark completed / no show ---------- */
async function updateStatus(a, newStatus, btn, originalText) {
  // Status changes are final (completed and no_show cannot be undone), so ask first
  const label = newStatus === "completed" ? "completed" : "a no show";
  if (!confirm(`Mark ${a.patient_name}'s appointment at ${a.start_time.slice(0, 5)} as ${label}?`)) return;

  btn.disabled = true; // prevents a double click from sending two requests
  btn.textContent = "Saving...";

  const res = await apiFetch(`/doctor/appointments/${a.id}/status`, {
    method: "PATCH",
    body: { status: newStatus },
  });

  if (res.ok) {
    showMessage(msgEl, res.data.message, "success");
    loadAppointments(); // reload so counts and badges reflect the server state
  } else {
    showMessage(msgEl, errorText(res.data));
    btn.disabled = false;
    btn.textContent = originalText;
    // 409 means the patient cancelled (or it changed elsewhere), so show the real state
    if (res.status === 409) loadAppointments();
  }
}

/* ---------- Start ---------- */
if (requireLogin(["doctor"])) {
  renderNavbar();
  dateInput.value = toDateString(new Date()); // default view: today
  [dateInput, filterSelect].forEach((el) =>
    el.addEventListener("change", () => {
      msgEl.textContent = ""; // clear the old message when the view changes
      loadAppointments();
    })
  );
  loadAppointments();
}