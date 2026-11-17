const statusEl = document.getElementById("status");
const doctorBox = document.getElementById("doctor-info");
const panel = document.getElementById("booking-panel");
const dateInput = document.getElementById("date");
const slotStatus = document.getElementById("slot-status");
const slotGrid = document.getElementById("slot-grid");
const confirmBtn = document.getElementById("confirm-btn");

const MAX_ADVANCE_DAYS = 30; // must match MAX_ADVANCE_DAYS in services.py

let doctor = null;       // set by loadDoctor
let selectedSlot = null; // "10:00" or null. F3.4 will read this
let slotRequest = 0;     // counter to drop stale slot responses

function setStatus(text, isError = false) {
  statusEl.textContent = text;
  statusEl.className = isError ? "status error" : "status";
}

function setSlotStatus(text, isError = false) {
  slotStatus.textContent = text;
  slotStatus.className = isError ? "status error" : "status";
}

// ?doctor=5 -> "5". Anything that is not digits is rejected.
function getDoctorId() {
  const id = new URLSearchParams(window.location.search).get("doctor");
  return /^\d+$/.test(id || "") ? id : null;
}

/* ---------- Doctor info ---------- */
function renderDoctor(d) {
  doctorBox.replaceChildren(makeEl("h2", "", d.name));
  doctorBox.appendChild(makeEl("p", "doc-meta", `${d.department} · ${d.hospital}`));
  doctorBox.appendChild(makeEl("p", "doc-detail", d.qualification));
  doctorBox.appendChild(makeEl("p", "doc-detail", `${d.experience_years} years experience`));
  doctorBox.appendChild(makeEl("p", "doc-detail", `Slot length: ${d.slot_minutes} min`));
  doctorBox.appendChild(
    makeEl("p", "doc-fee", `Fee: ₹${Number(d.consultation_fee).toLocaleString("en-IN")}`)
  );

  doctorBox.appendChild(makeEl("p", "schedule-title", "Weekly schedule"));
  const list = makeEl("ul", "schedule-list");
  if (d.schedule.length === 0) {
    list.appendChild(makeEl("li", "", "No schedule set yet"));
  } else {
    // API order is not guaranteed, so sort by day, then start time
    [...d.schedule]
      .sort((a, b) => a.day_of_week - b.day_of_week || a.start_time.localeCompare(b.start_time))
      .forEach((s) => {
        const text = `${s.day}: ${s.start_time.slice(0, 5)} - ${s.end_time.slice(0, 5)}`;
        list.appendChild(makeEl("li", "", text));
      });
  }
  doctorBox.appendChild(list);
}

async function loadDoctor(id) {
  setStatus("Loading doctor...");
  // Public endpoint, so auth: false
  const res = await apiFetch(`/doctors/${id}`, { auth: false });

  if (res.status === 404) {
    doctorBox.replaceChildren();
    setStatus("Doctor not found. Go back to the doctors list.", true);
    return;
  }
  if (!res.ok) {
    doctorBox.replaceChildren();
    setStatus(errorText(res.data), true);
    return;
  }

  doctor = res.data;
  setStatus("");
  renderDoctor(doctor);

  // Doctor is ready, so the booking panel can open
  setupDateLimits();
  setSlotStatus("Pick a date to see slots.");
  panel.hidden = false;
}

/* ---------- Date picker ---------- */
// Local YYYY-MM-DD. toISOString() is avoided: it uses UTC and can show
// yesterday's date late at night in India.
function toYMD(d) {
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  return `${d.getFullYear()}-${mm}-${dd}`;
}

function setupDateLimits() {
  const today = new Date();
  const last = new Date();
  last.setDate(today.getDate() + MAX_ADVANCE_DAYS);
  dateInput.min = toYMD(today);
  dateInput.max = toYMD(last);
}

/* ---------- Slots ---------- */
function clearSelection() {
  selectedSlot = null;
  confirmBtn.disabled = true;
}

function selectSlot(button, time) {
  slotGrid.querySelectorAll(".slot-btn").forEach((b) => b.classList.remove("selected"));
  button.classList.add("selected");
  selectedSlot = time;
  confirmBtn.disabled = false;
}

function renderSlots(slots) {
  slotGrid.replaceChildren();
  if (slots.length === 0) {
    setSlotStatus("No slots on this day. The doctor may be off, fully booked, or the time has passed.");
    return;
  }
  setSlotStatus(`${slots.length} slot${slots.length > 1 ? "s" : ""} available. Pick one.`);
  slots.forEach((time) => {
    const btn = makeEl("button", "slot-btn", time);
    btn.type = "button";
    btn.addEventListener("click", () => selectSlot(btn, time));
    slotGrid.appendChild(btn);
  });
}

async function loadSlots() {
  // Same idea as loadDoctors in doctors.js: an old slow response must not
  // overwrite the grid of the newer date.
  const myRequest = ++slotRequest;

  clearSelection(); // a new date means the old choice is gone
  slotGrid.replaceChildren();

  const date = dateInput.value;
  if (!date) {
    setSlotStatus("Pick a date to see slots.");
    return;
  }

  setSlotStatus("Loading slots...");
  // Login required on this endpoint, so auth stays on (default)
  const res = await apiFetch(`/doctors/${doctor.id}/slots?date=${date}`);

  if (myRequest !== slotRequest) return; // stale response, drop it

  if (!res.ok) {
    // Typed dates can ignore min/max, so the backend 400 message is shown
    setSlotStatus(errorText(res.data), true);
    return;
  }
  renderSlots(res.data.slots);
}

dateInput.addEventListener("change", loadSlots);

/* ---------- Start ---------- */
// Only patients can book. Guest goes to login (with ?next), others to their home.
const user = requireLogin(["patient"]);
if (user) {
  renderNavbar();
  const doctorId = getDoctorId();
  if (doctorId) {
    loadDoctor(doctorId);
  } else {
    doctorBox.replaceChildren();
    setStatus("No doctor selected. Go back to the doctors list.", true);
  }
}