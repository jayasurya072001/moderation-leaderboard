// ===== CONFIG =====
const DATA_PATH = "http://localhost:5000/data";         
const MAX_LIMIT = 5000;             

// ===== UTIL =====
const fmt = (n) => (n == null || Number.isNaN(n)) ? "—" : (Math.round(n * 100) / 100).toFixed(2);
const esc = (s="") => String(s).replace(/[&<>"'`=]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;','`':'&#96;','=':'&#61;'}[c]));

// ===== RENDER =====
function render(rows){
  const tbody = document.getElementById("tbody");
  tbody.innerHTML = "";

  if (!rows.length){
    tbody.insertAdjacentHTML("beforeend",
      `<tr><td class="muted" colspan="10" style="text-align:center">No records found</td></tr>`);
    document.getElementById("last-updated").textContent = nowStr();
    return;
  }

  for (const r of rows){
    const badge =
      r.rank === 1 ? `<span class="medal gold" title="1st">★</span>` :
      r.rank === 2 ? `<span class="medal silver" title="2nd">★</span>` :
      r.rank === 3 ? `<span class="medal bronze" title="3rd">★</span>` :
      `<span class="plain" title="${r.rank}">*</span>`;

    const html = `
      <tr class="pulse">
        <td class="rank">${badge}<span>${r.rank}</span></td>
       <td class="name-cell">${esc(r.name)}</td>
      <td><span class="stat">${r.batches}</span></td>
      <td><span class="stat">${fmt(r.avg)}</span></td>
      <td><span class="stat">${r.realRetries}</span></td>
      <td><span class="stat">${fmt(r.batchesScore)}</span></td>
      <td><span class="stat">${fmt(r.avgScore)}</span></td>
      <td><span class="stat">${fmt(r.retryScore)}</span></td>
      <td><span class="stat">${fmt(r.points)}</span></td>
      </tr>`;
    tbody.insertAdjacentHTML("beforeend", html);
  }

  document.getElementById("last-updated").textContent = nowStr();
}

// ===== FETCH ONCE with UI dates =====
async function fetchWithUIRange(){
  showError("");
  const startVal = document.getElementById("start-input").value;
  const endVal   = document.getElementById("end-input").value;

  const startISO = localToISOZ(startVal);
  const endISO   = localToISOZ(endVal);

  if (!startISO || !endISO){
    showError("Please select both Start and End date/time.");
    render([]);
    return;
  }
  if (new Date(startISO) > new Date(endISO)){
    showError("Start must be earlier than End.");
    render([]);
    return;
  }

  // Build endpoint with params
  const url = `${DATA_PATH}?start=${encodeURIComponent(startISO)}&end=${encodeURIComponent(endISO)}&limit=${MAX_LIMIT}`;
  print (url)
  try{
    const res = await fetch(url, { cache: "no-store" });
    if(!res.ok) throw new Error(`HTTP ${res.status}`);
    const docs = await res.json();
    render(docs);
  } catch (e){
    console.error(e);
    showError("Failed to load data. See console for details.");
    render([]);
  }
}

// ===== Quick range chips =====
function setRangeFromNow(rangeKey){
  const end = new Date(); // now
  let start = new Date(end);

  if (rangeKey === "1h")  start.setHours(end.getHours() - 1);
  if (rangeKey === "24h") start.setHours(end.getHours() - 24);
  if (rangeKey === "7d")  start.setDate(end.getDate() - 7);

  // Fill inputs with local datetime strings suitable for datetime-local
  const pad = (n) => String(n).padStart(2, "0");
  const toLocalInput = (d) => {
    const y = d.getFullYear();
    const m = pad(d.getMonth()+1);
    const day = pad(d.getDate());
    const h = pad(d.getHours());
    const min = pad(d.getMinutes());
    const s = pad(d.getSeconds());
    return `${y}-${m}-${day}T${h}:${min}:${s}`;
  };

  document.getElementById("start-input").value = toLocalInput(start);
  document.getElementById("end-input").value   = toLocalInput(end);
}

document.getElementById("load-btn").addEventListener("click", fetchWithUIRange);

document.querySelectorAll(".chip").forEach(btn=>{
  btn.addEventListener("click", ()=>{
    setRangeFromNow(btn.dataset.range);
    fetchWithUIRange(); 
  });
});

setRangeFromNow("24h");
fetchWithUIRange();
