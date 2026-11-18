const fromInput = document.getElementById("from");
const toInput = document.getElementById("to");
const resetBtn = document.getElementById("reset");
const statusEl = document.getElementById("status");
const contentEl = document.getElementById("content");

let requestCounter = 0; // ignores stale responses when the dates change quickly

function setStatus(text, isError = false) {
  statusEl.textContent = text;
  statusEl.className = isError ? "status error" : "status";
}

/* ---------- Load stats ---------- */
async function loadStats() {
  // Validate the range here for a quick message. The backend checks it too.
  if (fromInput.value && toInput.value && fromInput.value > toInput.value) {
    setStatus("The 'From' date must be on or before the 'To' date.", true);
    return;
  }

  const myRequest = ++requestCounter;
  setStatus("Loading stats...");

  const params = new URLSearchParams();
  if (fromInput.value) params.set("from", fromInput.value);
  if (toInput.value) params.set("to", toInput.value);
  const query = params.toString();

  const res = await apiFetch("/admin/stats" + (query ? `?${query}` : ""));
  if (myRequest !== requestCounter) return; // a newer range was chosen, drop this

  if (!res.ok) {
    contentEl.hidden = true;
    setStatus(errorText(res.data), true);
    return;
  }

  setStatus("");
  contentEl.hidden = false;
  render(res.data);
}

/* ---------- Rendering ---------- */
// A small card: big number on top, label below
function statBox(label, value, highlight = false) {
  const box = makeEl("div", highlight ? "stat highlight" : "stat");
  box.appendChild(makeEl("strong", "", value));
  box.appendChild(makeEl("span", "", label));
  return box;
}

function render(data) {
  const t = data.totals;
  const n = (v) => v.toLocaleString("en-IN");

  document.getElementById("totals").replaceChildren(
    statBox("Total appointments", n(t.appointments), true),
    statBox("Upcoming (booked)", n(t.upcoming_booked)),
    statBox("Booked", n(t.booked)),
    statBox("Completed", n(t.completed)),
    statBox("Cancelled", n(t.cancelled)),
    statBox("No show", n(t.no_show)),
    statBox("Patients", n(data.counts.patients)),
    statBox("Active doctors", n(data.counts.active_doctors))
  );

  document.getElementById("rates").replaceChildren(
    statBox("Completed", `${data.rates.completed_percent}%`),
    statBox("Cancelled", `${data.rates.cancelled_percent}%`),
    statBox("No show", `${data.rates.no_show_percent}%`)
  );

  renderDoctorTable(data.by_doctor);
  renderDepartmentBars(data.by_department);
}

function renderDoctorTable(rows) {
  const box = document.getElementById("by-doctor");
  if (rows.length === 0) {
    box.replaceChildren(makeEl("p", "empty-note", "No appointments in this range."));
    return;
  }

  const table = makeEl("table", "data-table");
  const head = makeEl("tr");
  ["Doctor", "Department", "Total", "Completed", "Cancelled", "No show", "No-show rate"].forEach(
    (h, i) => head.appendChild(makeEl("th", i >= 2 ? "num" : "", h))
  );
  table.appendChild(makeEl("thead")).appendChild(head);

  const body = makeEl("tbody");
  rows.forEach((r) => {
    const tr = makeEl("tr");
    tr.appendChild(makeEl("td", "", r.name));
    tr.appendChild(makeEl("td", "", r.department));
    [r.total, r.completed, r.cancelled, r.no_show].forEach((v) =>
      tr.appendChild(makeEl("td", "num", String(v)))
    );
    tr.appendChild(makeEl("td", "num", `${r.no_show_rate}%`));
    body.appendChild(tr);
  });
  table.appendChild(body);
  box.replaceChildren(table);
}

// Horizontal bars. Each bar width is relative to the largest department.
function renderDepartmentBars(rows) {
  const box = document.getElementById("by-department");
  if (rows.length === 0) {
    box.replaceChildren(makeEl("p", "empty-note", "No appointments in this range."));
    return;
  }

  const max = Math.max(...rows.map((r) => r.total));
  box.replaceChildren(
    ...rows.map((r) => {
      const row = makeEl("div", "bar-row");
      row.appendChild(makeEl("span", "bar-label", r.department));

      const track = makeEl("div", "bar-track");
      const fill = makeEl("div", "bar-fill");
      fill.style.width = `${(r.total / max) * 100}%`; // a number we computed, not server HTML
      track.appendChild(fill);
      row.appendChild(track);

      row.appendChild(makeEl("span", "bar-value", String(r.total)));
      return row;
    })
  );
}

/* ---------- Start ---------- */
if (requireLogin(["admin"])) {
  renderNavbar();
  [fromInput, toInput].forEach((el) => el.addEventListener("change", loadStats));
  resetBtn.addEventListener("click", () => {
    fromInput.value = "";
    toInput.value = "";
    loadStats();
  });
  loadStats();
}