/* Vision-to-Cart — frontend logic (no build step). */

const API = ""; // same origin; set to "http://localhost:8000" if served elsewhere

const $ = (id) => document.getElementById(id);

const el = {
  drop: $("drop"), file: $("file"), dropIdle: $("dropIdle"), dropPreview: $("dropPreview"),
  previewImg: $("previewImg"), clearBtn: $("clearBtn"), lang: $("lang"), speak: $("speak"),
  scanBtn: $("scanBtn"), voiceBtn: $("voiceBtn"), voiceHint: $("voiceHint"),
  results: $("results"), empty: $("empty"), cards: $("cards"),
  objQuery: $("objQuery"), objProvider: $("objProvider"), objLabels: $("objLabels"),
  objNote: $("objNote"), statusDot: $("statusDot"), statusText: $("statusText"),
};

let selectedFile = null;
let currentAudio = null;
let mediaRecorder = null;
let audioSources = [];   // data URIs for the current result set

/* ---------------- boot ---------------- */
(async function init() {
  await Promise.all([loadLanguages(), loadHealth()]);
})();

async function loadLanguages() {
  try {
    const res = await fetch(`${API}/api/v1/languages`);
    const { languages } = await res.json();
    el.lang.innerHTML = languages
      .map((l) => `<option value="${l.code}">${labelFor(l.code)}</option>`)
      .join("");
    el.lang.value = "hi"; // sensible default for the Indian market
  } catch {
    el.lang.innerHTML = `<option value="en">English</option>`;
  }
}

const NAMES = {
  en: "English", hi: "हिन्दी (Hindi)", bn: "বাংলা (Bengali)", gu: "ગુજરાતી (Gujarati)",
  kn: "ಕನ್ನಡ (Kannada)", ml: "മലയാളം (Malayalam)", mr: "मराठी (Marathi)", od: "ଓଡ଼ିଆ (Odia)",
  pa: "ਪੰਜਾਬੀ (Punjabi)", ta: "தமிழ் (Tamil)", te: "తెలుగు (Telugu)",
};
const labelFor = (code) => NAMES[code] || code;

async function loadHealth() {
  try {
    const res = await fetch(`${API}/api/v1/health`);
    const h = await res.json();
    const demo = h.lens_provider === "mock";
    el.statusDot.className = "status__dot " + (demo ? "status__dot--demo" : "status__dot--ok");
    const bits = [`lens: ${h.lens_provider}`];
    bits.push(h.sarvam ? "sarvam: on" : "sarvam: off");
    if (h.marketplaces?.length) bits.push(`+${h.marketplaces.join(",")}`);
    el.statusText.textContent = bits.join(" · ");
  } catch {
    el.statusDot.className = "status__dot";
    el.statusText.textContent = "offline";
  }
}

/* ---------------- file selection ---------------- */
el.drop.addEventListener("click", (e) => {
  if (e.target === el.clearBtn) return;
  el.file.click();
});
el.drop.addEventListener("keydown", (e) => {
  if (e.key === "Enter" || e.key === " ") { e.preventDefault(); el.file.click(); }
});
el.file.addEventListener("change", () => setFile(el.file.files?.[0]));

["dragenter", "dragover"].forEach((evt) =>
  el.drop.addEventListener(evt, (e) => { e.preventDefault(); el.drop.classList.add("is-over"); })
);
["dragleave", "drop"].forEach((evt) =>
  el.drop.addEventListener(evt, (e) => { e.preventDefault(); el.drop.classList.remove("is-over"); })
);
el.drop.addEventListener("drop", (e) => {
  const f = e.dataTransfer?.files?.[0];
  if (f) setFile(f);
});

function setFile(file) {
  if (!file || !file.type.startsWith("image/")) return;
  selectedFile = file;
  el.previewImg.src = URL.createObjectURL(file);
  el.dropIdle.hidden = true;
  el.dropPreview.hidden = false;
  el.scanBtn.disabled = false;
}

el.clearBtn.addEventListener("click", (e) => {
  e.stopPropagation();
  selectedFile = null;
  el.file.value = "";
  el.dropPreview.hidden = true;
  el.dropIdle.hidden = false;
  el.scanBtn.disabled = true;
});

/* ---------------- scan ---------------- */
el.scanBtn.addEventListener("click", async () => {
  if (!selectedFile) return;
  setBusy(true, "Identifying…");
  try {
    const form = new FormData();
    form.append("image", selectedFile);
    form.append("lang", el.lang.value);
    form.append("speak", String(el.speak.checked));

    const res = await fetch(`${API}/api/v1/scan`, { method: "POST", body: form });
    if (!res.ok) throw new Error(await readError(res));
    render(await res.json());
  } catch (err) {
    showError(err.message);
  } finally {
    setBusy(false);
  }
});

/* ---------------- voice ---------------- */
el.voiceBtn.addEventListener("click", async () => {
  if (mediaRecorder && mediaRecorder.state === "recording") {
    mediaRecorder.stop();
    return;
  }
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const chunks = [];
    mediaRecorder = new MediaRecorder(stream);
    mediaRecorder.ondataavailable = (e) => chunks.push(e.data);
    mediaRecorder.onstop = async () => {
      stream.getTracks().forEach((t) => t.stop());
      el.voiceBtn.textContent = "🎙 Speak a name";
      el.voiceHint.textContent = "Transcribing…";
      try {
        const form = new FormData();
        form.append("audio", new Blob(chunks, { type: "audio/webm" }), "clip.webm");
        form.append("lang", el.lang.value);
        form.append("speak", String(el.speak.checked));
        const res = await fetch(`${API}/api/v1/scan/voice`, { method: "POST", body: form });
        if (!res.ok) throw new Error(await readError(res));
        render(await res.json());
        el.voiceHint.textContent = "";
      } catch (err) {
        el.voiceHint.textContent = err.message;
      }
    };
    mediaRecorder.start();
    el.voiceBtn.textContent = "■ Stop";
    el.voiceHint.textContent = "Recording… speak the product name.";
  } catch {
    el.voiceHint.textContent = "Microphone unavailable (needs HTTPS or localhost).";
  }
});

/* ---------------- rendering ---------------- */
function render(data) {
  audioSources = (data.products || []).map((p) =>
    p.audio_b64 ? `data:audio/wav;base64,${p.audio_b64}` : null);

  el.empty.hidden = true;
  el.results.hidden = false;

  el.objQuery.textContent = data.query || "—";
  el.objProvider.textContent = `via ${data.provider}` + (data.translated ? " · translated" : "");
  el.objLabels.innerHTML = (data.labels || []).map((l) => `<span>${esc(l)}</span>`).join("");
  if (data.note) { el.objNote.hidden = false; el.objNote.textContent = data.note; }
  else { el.objNote.hidden = true; }

  if (!data.products?.length) {
    el.cards.innerHTML = `<div class="empty">No products found for “${esc(data.query)}”.</div>`;
    return;
  }

  el.cards.innerHTML = data.products
    .map((p, i) => card(p, i))
    .join("");

  el.cards.querySelectorAll("[data-play]").forEach((btn) => {
    btn.addEventListener("click", () => playAudio(btn.dataset.play));
  });
}

function card(p, i) {
  const img = p.image_url
    ? `<img src="${esc(p.image_url)}" alt="" loading="lazy" referrerpolicy="no-referrer"
            onerror="this.replaceWith(Object.assign(document.createElement('span'),{className:'ph',textContent:'no image'}))">`
    : `<span class="ph">no image</span>`;

  const price = p.price_inr != null
    ? inr.format(p.price_inr)
    : p.price_text
      ? esc(p.price_text)
      : `<span class="na">price n/a</span>`;

  const stock = p.in_stock
    ? `<span class="card__stock card__stock--in">In stock</span>`
    : `<span class="card__stock card__stock--out">Out of stock</span>`;

  const rating = p.rating ? ` · ★ ${p.rating}` : "";
  const listen = p.audio_b64
    ? `<button data-play="${i}" type="button">▶ Listen</button>`
    : `<button type="button" disabled title="No audio — enable Sarvam TTS">▶ Listen</button>`;
  const view = p.url
    ? `<a href="${esc(p.url)}" target="_blank" rel="noreferrer">View ↗</a>`
    : "";

  return `
    <article class="card" style="animation-delay:${i * 45}ms">
      <div class="card__img">${img}</div>
      <div class="card__body">
        <div class="card__src">
          <span class="card__origin">${esc(p.source || "web")}${rating}</span>
          <span>${esc(p.origin || "")}</span>
        </div>
        <p class="card__title">${esc(p.title)}</p>
        <div class="card__price">${price}</div>
        ${stock}
        <div class="card__actions">${listen}${view}</div>
      </div>
    </article>`;
}

/* ---------------- helpers ---------------- */
function playAudio(index) {
  const src = audioSources[index];
  if (!src) return;
  if (currentAudio) currentAudio.pause();
  currentAudio = new Audio(src);
  currentAudio.play();
}

function setBusy(busy, label) {
  el.scanBtn.disabled = busy || !selectedFile;
  el.scanBtn.classList.toggle("is-busy", busy);
  el.scanBtn.innerHTML = busy
    ? `<span class="spinner"></span>${label}`
    : "Identify &amp; shop";
}

function showError(msg) {
  el.empty.hidden = false;
  el.empty.innerHTML = `<p style="color:var(--rose)">${esc(msg)}</p>`;
}

async function readError(res) {
  try { return (await res.json()).detail || `HTTP ${res.status}`; }
  catch { return `HTTP ${res.status}`; }
}

const inr = new Intl.NumberFormat("en-IN", {
  style: "currency", currency: "INR", maximumFractionDigits: 0,
});

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
