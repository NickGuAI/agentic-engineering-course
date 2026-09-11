"use strict";

const feedEl = document.getElementById("feed");
const statusEl = document.getElementById("status-bar");
const weightsPanel = document.getElementById("weights-panel");
const weightsChips = document.getElementById("weights-chips");
const refreshBtn = document.getElementById("refresh-btn");
const resetBtn = document.getElementById("reset-btn");
const cardTemplate = document.getElementById("card-template");

// debounce timers for note auto-save, keyed by article id
const noteTimers = new Map();

async function api(path, options) {
  const res = await fetch(path, options);
  if (!res.ok) throw new Error(`${path} -> HTTP ${res.status}`);
  return res.json();
}

function badgeClass(source) {
  return source.toLowerCase().startsWith("openai") ? "openai" : "anthropic";
}

function render(payload) {
  renderStatus(payload);
  renderWeights(payload.weights || {});
  renderFeed(payload.articles || []);
}

function renderStatus(payload) {
  statusEl.innerHTML = "";
  const entries = Object.entries(payload.status || {});
  for (const [source, state] of entries) {
    const pill = document.createElement("span");
    const ok = state === "ok" || state.startsWith("served");
    pill.className = "status-pill " + (ok ? "ok" : "warn");
    pill.textContent = `${source}: ${state}`;
    statusEl.appendChild(pill);
  }
  const count = document.createElement("span");
  count.className = "status-pill";
  count.textContent = `${payload.count || 0} updates`;
  statusEl.appendChild(count);
}

function renderWeights(weights) {
  const entries = Object.entries(weights);
  weightsPanel.hidden = false;
  weightsChips.innerHTML = "";
  if (entries.length === 0) {
    weightsChips.innerHTML =
      '<span class="chips-empty">No signal yet — rate a few blocks below to train the ranker.</span>';
    return;
  }
  for (const [tag, w] of entries) {
    const chip = document.createElement("span");
    chip.className = "chip " + (w >= 0 ? "pos" : "neg");
    chip.innerHTML = `${tag}<span class="w">${w > 0 ? "+" : ""}${w.toFixed(1)}</span>`;
    weightsChips.appendChild(chip);
  }
}

function renderFeed(articles) {
  feedEl.innerHTML = "";
  if (articles.length === 0) {
    feedEl.innerHTML = '<div class="error">No updates could be loaded.</div>';
    return;
  }
  articles.forEach((art, i) => feedEl.appendChild(buildCard(art, i + 1)));
}

function buildCard(art, position) {
  const node = cardTemplate.content.cloneNode(true);
  const card = node.querySelector(".card");
  card.dataset.id = art.id;
  if (art.rating === 1) card.classList.add("rated-up");
  if (art.rating === -1) card.classList.add("rated-down");

  node.querySelector(".rank").textContent = "#" + position;
  const badge = node.querySelector(".source-badge");
  badge.textContent = art.source;
  badge.classList.add(badgeClass(art.source));
  node.querySelector(".category").textContent = art.category || "";
  node.querySelector(".date").textContent = art.date || "";
  node.querySelector(".score").textContent = "score " + art.score;

  const link = node.querySelector(".card-title a");
  link.textContent = art.title;
  link.href = art.url;

  const summary = node.querySelector(".card-summary");
  summary.textContent = art.summary || "";
  if (!art.summary) summary.hidden = true;

  const tagsEl = node.querySelector(".tags");
  (art.tags || []).forEach((t) => {
    const el = document.createElement("span");
    el.className = "tag";
    el.textContent = "#" + t;
    tagsEl.appendChild(el);
  });

  node.querySelector(".score-breakdown").innerHTML =
    `agent-relevance <b>${art.relevance}</b> · recency <b>${art.recency}</b> · learned <b>${
      art.learned > 0 ? "+" : ""
    }${art.learned}</b>`;

  wireRating(node, art);
  return node;
}

function wireRating(node, art) {
  const up = node.querySelector(".vote-up");
  const down = node.querySelector(".vote-down");
  const noteInput = node.querySelector(".note-input");
  const saveBtn = node.querySelector(".save-btn");
  const savedFlag = node.querySelector(".saved-flag");

  if (art.rating === 1) up.classList.add("active");
  if (art.rating === -1) down.classList.add("active");
  noteInput.value = art.note || "";

  const currentRating = () =>
    up.classList.contains("active") ? 1 : down.classList.contains("active") ? -1 : 0;

  const flashSaved = () => {
    savedFlag.hidden = false;
    setTimeout(() => (savedFlag.hidden = true), 1500);
  };

  // Voting re-ranks immediately (full re-render).
  up.addEventListener("click", () => {
    down.classList.remove("active");
    up.classList.toggle("active");
    submitRating(art, currentRating(), noteInput.value, { rerender: true });
  });
  down.addEventListener("click", () => {
    up.classList.remove("active");
    down.classList.toggle("active");
    submitRating(art, currentRating(), noteInput.value, { rerender: true });
  });

  // Notes save quietly (debounced) so the input keeps focus while typing.
  saveBtn.addEventListener("click", () => {
    submitRating(art, currentRating(), noteInput.value, { rerender: false }).then(flashSaved);
  });
  noteInput.addEventListener("input", () => {
    saveBtn.hidden = false;
    clearTimeout(noteTimers.get(art.id));
    noteTimers.set(
      art.id,
      setTimeout(() => {
        submitRating(art, currentRating(), noteInput.value, { rerender: false }).then(flashSaved);
      }, 900)
    );
  });
}

async function submitRating(art, rating, note, { rerender }) {
  try {
    const payload = await api("/api/rate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id: art.id, rating, note, tags: art.tags, title: art.title }),
    });
    // Keep the learned-weights panel live on every save.
    renderWeights(payload.weights || {});
    if (rerender) {
      renderStatus(payload);
      renderFeed(payload.articles || []);
    }
    return payload;
  } catch (err) {
    statusEl.insertAdjacentHTML(
      "beforeend",
      `<span class="status-pill warn">save failed: ${err.message}</span>`
    );
  }
}

async function load(refresh) {
  feedEl.innerHTML = '<div class="loading">Loading updates…</div>';
  refreshBtn.disabled = true;
  refreshBtn.textContent = refresh ? "Fetching…" : "↻ Refresh sources";
  try {
    const payload = await api(refresh ? "/api/refresh" : "/api/articles", {
      method: refresh ? "POST" : "GET",
    });
    render(payload);
  } catch (err) {
    feedEl.innerHTML = `<div class="error">Failed to load: ${err.message}</div>`;
  } finally {
    refreshBtn.disabled = false;
    refreshBtn.textContent = "↻ Refresh sources";
  }
}

refreshBtn.addEventListener("click", () => load(true));
resetBtn.addEventListener("click", async () => {
  if (!confirm("Clear all your ratings and notes?")) return;
  const current = await api("/api/articles");
  await Promise.all(
    (current.articles || [])
      .filter((a) => a.rating !== 0 || a.note)
      .map((a) =>
        api("/api/rate", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ id: a.id, rating: 0, note: "", tags: a.tags, title: a.title }),
        })
      )
  );
  load(false);
});

load(false);
