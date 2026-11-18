// Must match MAX_ADVANCE_DAYS on the backend (services.py)
const MAX_ADVANCE_DAYS = 30;

const dateInput = document.getElementById("date");
const slotsEl = document.getElementById("slots");
const slotStatusEl = document.getElementById("slot-status");
const reasonInput = document.getElementById("reason");
const summaryEl = document.getElementById("summary");
const confirmBtn = document.getElementById("confirm");
const msgEl = document.getElementById("msg");

let doctorId = null;
let selectedSlot = null; // e.g. "10:15"
let requestCounter = 0;  // ignores stale slot responses (same idea as doctors.js)

/* ---------- Date helpers ----------
   Date.toISOString() converts to UTC and can shift the date by one day
   (an IST morning would become "yesterday"). So the string is built from
   local date parts instead. */
function toDateString(d) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

// "2026-11-23" -> "Mon, 23 Nov 2026". Parsed manually to avoid the UTC shift.
function prettyDate(str) {
  const [y, m, d] = str.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString("en-IN", {
    weekday: "short", day: "numeric", month: "short", year: "numeric",
  });
}

/* ---------- Page state ---------- */
function showFatal(text) {
  document.getElementById("booking-page").hidden = true;
  document.getElementById("page-error").textContent = text;
}

function setSlotStatus(text, isError = false) {
  slotStatusEl.textContent = text;
  slotStatusEl.className = isError ? "status error" : "status";
}

// The confirm button is enabled only when a date and a slot are both chosen
function updateSummary() {
  if (selectedSlot && dateInput.value) {
    summaryEl.textContent = `Selected: ${prettyDate(dateInput.value)} at ${selectedSlot}`;
    confirmBtn.disabled = false;
  } else {
    summaryEl.textContent = "";
    confirmBtn.disabled = true;
  }
}

/* ---------- Doctor info ---------- */
async function loadDoctor() {
  // Public endpoint, so auth: false
  const res = await apiFetch(`/doctors/${doctorId}`, { auth: false });
  if (!res.ok) {
    showFatal(res.status === 404 ? "Doctor not found." : errorText(res.data));
    return false;
  }

  const d = res.data;
  const box = document.getElementById("doctor-info");
  box.replaceChildren(
    makeEl("h1", "", d.name),
    makeEl("p", "doc-meta", `${d.department} · ${d.hospital}`),
    makeEl("p", "doc-detail", `${d.qualification} · ${d.experience_years} years experience`),
    makeEl("p", "doc-fee", `Fee: ₹${Number(d.consultation_fee).toLocaleString("en-IN")}`)
  );

  // Weekly schedule so the patient knows which days the doctor works
  if (d.schedule.length > 0) {
    box.appendChild(makeEl("p", "doc-detail", "Weekly schedule:"));
    const list = makeEl("ul", "schedule-list");
    d.schedule.forEach((s) => {
      // times arrive as "10:00:00", show only "10:00"
      list.appendChild(
        makeEl("li", "", `${s.day}: ${s.start_time.slice(0, 5)} - ${s.end_time.slice(0, 5)}`)
      );
    });
    box.appendChild(list);
  }
  return true;
}

/* ---------- Slots ---------- */
async function loadSlots() {
  selectedSlot = null;
  updateSummary();
  slotsEl.replaceChildren();

  const day = dateInput.value;
  if (!day) {
    setSlotStatus("Pick a date to see available slots.");
    return;
  }

  const myRequest = ++requestCounter;
  setSlotStatus("Loading slots...");

  // This endpoint needs login, so the token is sent (auth defaults to true)
  const res = await apiFetch(`/doctors/${doctorId}/slots?date=${day}`);
  if (myRequest !== requestCounter) return; // a newer date was picked, drop this

  if (!res.ok) {
    setSlotStatus(errorText(res.data), true);
    return;
  }
  if (res.data.slots.length === 0) {
    setSlotStatus("No slots available on this date. The doctor may be on leave or not working that day.");
    return;
  }

  setSlotStatus(`${res.data.total} slots available · ${res.data.slot_minutes} minutes each`);
  res.data.slots.forEach((time) => {
    const btn = makeEl("button", "slot-btn", time);
    btn.type = "button";
    btn.addEventListener("click", () => selectSlot(time, btn));
    slotsEl.appendChild(btn);
  });
}

function selectSlot(time, btn) {
  // Only one slot can be selected at a time
  slotsEl.querySelectorAll(".slot-btn").forEach((b) => b.classList.remove("selected"));
  btn.classList.add("selected");
  selectedSlot = time;
  msgEl.textContent = ""; // clear any old message
  updateSummary();
}

/* ---------- Booking ---------- */
async function confirmBooking() {
  if (!selectedSlot || !dateInput.value) return;

  confirmBtn.disabled = true; // prevents a double click from sending two requests
  confirmBtn.textContent = "Booking...";

  const res = await apiFetch("/appointments", {
    method: "POST",
    body: {
      doctor_id: Number(doctorId),
      date: dateInput.value,
      start_time: selectedSlot,
      reason: reasonInput.value.trim(),
    },
  });

  confirmBtn.textContent = "Confirm booking";

  if (res.ok) {
    showMessage(
      msgEl,
      `Appointment booked for ${prettyDate(res.data.date)} at ${res.data.start_time.slice(0, 5)}. Redirecting...`,
      "success"
    );
    // Button stays disabled so the same booking is not sent again
    setTimeout(() => (window.location.href = "my-appointments.html"), 1500);
    return;
  }

  showMessage(msgEl, errorText(res.data));
  // 409 = someone else took the slot a moment ago. Reload the slots so the
  // patient sees the fresh list and can pick another one.
  if (res.status === 409 || res.status === 400) {
    loadSlots();
  } else {
    updateSummary(); // other errors: let the user try again
  }
}

/* ---------- Start ---------- */
async function init() {
  // Only patients can book. Others are redirected (the backend enforces it too).
  const currentUser = requireLogin(["patient"]);
  if (!currentUser) return;

  renderNavbar();

  // The doctor id comes from the URL: book.html?doctor=1
  doctorId = new URLSearchParams(window.location.search).get("doctor");
  if (!doctorId || !/^\d+$/.test(doctorId)) {
    showFatal("No doctor selected. Please choose a doctor from the list.");
    return;
  }

  if (!(await loadDoctor())) return;
  document.getElementById("booking-page").hidden = false;

  // Date picker limits: today up to MAX_ADVANCE_DAYS ahead.
  // This is only UX; the backend validates the range as well.
  const today = new Date();
  const last = new Date();
  last.setDate(today.getDate() + MAX_ADVANCE_DAYS);
  dateInput.min = toDateString(today);
  dateInput.max = toDateString(last);

  dateInput.addEventListener("change", () => {
    msgEl.textContent = "";
    loadSlots();
  });
  confirmBtn.addEventListener("click", confirmBooking);

  setSlotStatus("Pick a date to see available slots.");
}

init();