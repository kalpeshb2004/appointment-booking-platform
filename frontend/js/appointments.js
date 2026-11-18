const filterSelect = document.getElementById("filter");
const listEl = document.getElementById("appt-list");
const statusEl = document.getElementById("status");
const msgEl = document.getElementById("msg");

// Filter name -> query string understood by GET /appointments
const FILTER_QUERY = {
  upcoming: "?upcoming=true",
  all: "",
  booked: "?status=booked",
  completed: "?status=completed",
  cancelled: "?status=cancelled",
  no_show: "?status=no_show",
};

// Backend status value -> text shown in the badge
const STATUS_LABEL = {
  booked: "Booked",
  completed: "Completed",
  cancelled: "Cancelled",
  no_show: "No show",
};

let requestCounter = 0; // ignores stale responses when the filter changes quickly

function setStatus(text, isError = false) {
  statusEl.textContent = text;
  statusEl.className = isError ? "status error" : "status";
}

/* ---------- Load the list ---------- */
async function loadAppointments() {
  const myRequest = ++requestCounter;
  setStatus("Loading appointments...");

  const res = await apiFetch("/appointments" + FILTER_QUERY[filterSelect.value]);
  if (myRequest !== requestCounter) return; // a newer filter was chosen, drop this

  if (!res.ok) {
    listEl.replaceChildren();
    setStatus(errorText(res.data), true);
    return;
  }

  listEl.replaceChildren();
  if (res.data.length === 0) {
    setStatus("No appointments found.");
    return;
  }
  setStatus(`${res.data.length} appointment${res.data.length > 1 ? "s" : ""}`);
  res.data.forEach((a) => listEl.appendChild(appointmentCard(a)));
}

/* ---------- One appointment card ----------
   Built with DOM methods (not innerHTML) so server data is never parsed as HTML. */
function appointmentCard(a) {
  const card = makeEl("div", "appt-card");

  const head = makeEl("div", "appt-head");
  head.appendChild(makeEl("h3", "", a.doctor_name));
  head.appendChild(makeEl("span", `badge ${a.status}`, STATUS_LABEL[a.status] || a.status));
  card.appendChild(head);

  card.appendChild(makeEl("p", "doc-meta", `${a.department} · ${a.hospital}`));
  card.appendChild(
    makeEl("p", "appt-when", `${prettyDate(a.date)} · ${a.start_time.slice(0, 5)} - ${a.end_time.slice(0, 5)}`)
  );
  if (a.reason) card.appendChild(makeEl("p", "doc-detail", `Reason: ${a.reason}`));

  // Only booked appointments can be cancelled. The 2-hour rule is enforced
  // by the backend, and its error message is shown if the request is rejected.
  if (a.status === "booked") {
    const actions = makeEl("div", "appt-actions");
    const cancelBtn = makeEl("button", "btn-danger", "Cancel appointment");
    cancelBtn.type = "button";
    cancelBtn.addEventListener("click", () => cancelAppointment(a, cancelBtn));
    actions.appendChild(cancelBtn);
    card.appendChild(actions);
  }
  return card;
}

/* ---------- Cancel ---------- */
async function cancelAppointment(a, btn) {
  // confirm() blocks accidental clicks. Cancelling frees the slot for others.
  const ok = confirm(
    `Cancel your appointment with ${a.doctor_name} on ${prettyDate(a.date)} at ${a.start_time.slice(0, 5)}?`
  );
  if (!ok) return;

  btn.disabled = true; // prevents a double click from sending two requests
  btn.textContent = "Cancelling...";

  const res = await apiFetch(`/appointments/${a.id}`, { method: "DELETE" });

  if (res.ok) {
    showMessage(msgEl, res.data.message, "success");
    loadAppointments(); // reload so the card moves to the right filter
  } else {
    // Examples: "can only be cancelled at least 2 hours before" or "already cancelled"
    showMessage(msgEl, errorText(res.data));
    btn.disabled = false;
    btn.textContent = "Cancel appointment";
    // 409 means the state changed elsewhere, so refresh to show the real state
    if (res.status === 409) loadAppointments();
  }
}

/* ---------- Start ---------- */
if (requireLogin(["patient"])) {
  renderNavbar();
  filterSelect.addEventListener("change", () => {
    msgEl.textContent = ""; // clear the old message when the view changes
    loadAppointments();
  });
  loadAppointments();
}