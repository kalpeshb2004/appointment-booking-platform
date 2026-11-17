const statusEl = document.getElementById("status");
const doctorBox = document.getElementById("doctor-info");

let doctor = null; // filled by loadDoctor, F3.3 will use it

function setStatus(text, isError = false) {
  statusEl.textContent = text;
  statusEl.className = isError ? "status error" : "status";
}

// ?doctor=5 -> "5". Anything that is not digits is rejected.
function getDoctorId() {
  const id = new URLSearchParams(window.location.search).get("doctor");
  return /^\d+$/.test(id || "") ? id : null;
}

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
}

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