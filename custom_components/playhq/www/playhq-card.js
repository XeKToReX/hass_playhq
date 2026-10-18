/* PlayHQ Lovelace card - vanilla web components, no build step, no external deps. */

const ALL_SECTIONS = [
  { key: "live", label: "Live match" },
  { key: "next", label: "Next match" },
  { key: "last_result", label: "Last result" },
  { key: "career", label: "Career stats (player)" },
  { key: "season", label: "Current season stats (player)" },
];
const SECTION_KEYS = ALL_SECTIONS.map((s) => s.key);

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str == null ? "" : String(str);
  return div.innerHTML;
}

function statsText(stats) {
  if (!stats) return null;
  return Object.entries(stats)
    .filter(([, v]) => v != null)
    .map(([k, v]) => `${k.replace(/_/g, " ").toLowerCase()}: ${v}`)
    .join(", ");
}

/* ------------------------------------------------------------------ */
/* Card                                                                 */
/* ------------------------------------------------------------------ */
class PlayHQCard extends HTMLElement {
  setConfig(config) {
    if (!config.entity) {
      throw new Error("playhq-card: 'entity' is required (a PlayHQ sensor).");
    }
    this._config = {
      show_logos: true,
      show_quarters: true,
      section_order: SECTION_KEYS.slice(),
      disabled_sections: [],
      ...config,
    };
    this._built = false;
  }

  set hass(hass) {
    this._hass = hass;
    const stateObj = hass.states[this._config.entity];
    if (!stateObj) {
      this._renderError(`Entity not found: ${this._config.entity}`);
      return;
    }
    if (!this._built) {
      this._buildShell();
      this._built = true;
    }
    this._renderContent(stateObj);
  }

  getCardSize() {
    return 4;
  }

  static getStubConfig(hass) {
    const entity = Object.keys(hass.states).find((e) => e.startsWith("sensor.") && (e.includes("_status") || e.includes("games_played")));
    return {
      entity: entity || "sensor.your_playhq_entity",
      show_logos: true,
      show_quarters: true,
      section_order: SECTION_KEYS.slice(),
      disabled_sections: [],
    };
  }

  static getConfigElement() {
    return document.createElement("playhq-card-editor");
  }

  _renderError(message) {
    this.innerHTML = `<ha-card><div class="phq-error">${message}</div></ha-card>`;
  }

  _buildShell() {
    const style = document.createElement("style");
    style.textContent = `
      ha-card { padding: 16px; }
      .phq-error { color: var(--error-color, #f44); padding: 8px 0; }
      .phq-header { display:flex; align-items:center; justify-content:space-between; margin-bottom: 12px; }
      .phq-title { font-size: 18px; font-weight: 500; }
      .phq-sub { font-size: 12px; color: var(--secondary-text-color); }
      .phq-section { margin-bottom: 16px; }
      .phq-section:last-child { margin-bottom: 0; }
      .phq-section-label { font-size: 11px; letter-spacing: 1px; text-transform: uppercase; color: var(--secondary-text-color); margin-bottom: 6px; }
      .phq-live-badge { display:inline-block; font-size:11px; letter-spacing:1px; text-transform:uppercase; color:#fff; background:#e53935; border-radius:4px; padding:2px 8px; margin-bottom:6px; }
      .phq-clock { font-size: 22px; font-weight: 700; font-variant-numeric: tabular-nums; margin-bottom: 10px; }
      .phq-matchup { display:flex; align-items:center; justify-content:space-between; gap: 12px; }
      .phq-team { display:flex; flex-direction:column; align-items:center; flex:1; min-width:0; }
      .phq-team img { width: 40px; height: 40px; object-fit: contain; border-radius: 6px; background: var(--secondary-background-color); margin-bottom: 4px; }
      .phq-team-name { font-size: 13px; text-align:center; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; max-width: 100%; }
      .phq-score { font-size: 28px; font-weight: 700; }
      .phq-breakdown { font-size: 12px; color: var(--secondary-text-color); }
      .phq-vs { font-size: 14px; color: var(--secondary-text-color); }
      .phq-meta { font-size: 12px; color: var(--secondary-text-color); margin-top: 8px; }
      table.phq-quarters { width: 100%; border-collapse: collapse; font-size: 12px; margin-top: 10px; }
      table.phq-quarters th, table.phq-quarters td { padding: 4px 6px; text-align: center; }
      table.phq-quarters th { color: var(--secondary-text-color); font-weight: 500; border-bottom: 1px solid var(--divider-color); }
      table.phq-quarters td.phq-q-team { text-align: left; }
      .phq-empty { color: var(--secondary-text-color); font-size: 13px; }
      .phq-row { display:flex; align-items:center; justify-content:space-between; font-size: 13px; }
      .phq-row .phq-row-teams { display:flex; align-items:center; gap:6px; }
      .phq-row img { width: 20px; height: 20px; object-fit: contain; border-radius: 4px; background: var(--secondary-background-color); }
      .phq-stat-line { display:flex; justify-content:space-between; font-size:13px; padding:3px 0; border-bottom:1px solid var(--divider-color); }
      .phq-stat-line:last-child { border-bottom: none; }
      .phq-sub-heading { font-size: 12px; font-weight: 600; margin: 8px 0 4px; }
    `;
    const card = document.createElement("ha-card");
    const content = document.createElement("div");
    content.className = "phq-content";
    card.appendChild(content);
    this.innerHTML = "";
    this.appendChild(style);
    this.appendChild(card);
    this._card = card;
    this._content = content;
  }

  _logoImg(logoUrl, alt) {
    if (!this._config.show_logos || !logoUrl) return "";
    return `<img src="${logoUrl}" alt="${escapeHtml(alt || "")}">`;
  }

  _quarterTable(homeName, awayName, homePeriods, awayPeriods) {
    if (!this._config.show_quarters) return "";
    const order = ["FIRST_QTR", "SECOND_QTR", "THIRD_QTR", "FOURTH_QTR"];
    const labels = { FIRST_QTR: "Q1", SECOND_QTR: "Q2", THIRD_QTR: "Q3", FOURTH_QTR: "Q4" };
    const keys = [...order];
    Object.keys(homePeriods || {}).forEach((k) => { if (!keys.includes(k)) keys.push(k); });
    Object.keys(awayPeriods || {}).forEach((k) => { if (!keys.includes(k)) keys.push(k); });

    const rows = keys
      .filter((q) => (homePeriods && homePeriods[q]) || (awayPeriods && awayPeriods[q]))
      .map((q) => {
        const label = labels[q] || q;
        const h = this._statsText(homePeriods && homePeriods[q]);
        const a = this._statsText(awayPeriods && awayPeriods[q]);
        return `<tr><td class="phq-q-team">${label}</td><td>${h}</td><td>${a}</td></tr>`;
      });

    if (!rows.length) return "";
    return `<table class="phq-quarters">
      <tr><th></th><th>${escapeHtml(homeName)}</th><th>${escapeHtml(awayName)}</th></tr>
      ${rows.join("")}
    </table>`;
  }

  _statsText(stats) {
    if (!stats) return "-";
    const find = (key) => {
      const s = stats.find((x) => x.type && x.type.value === key);
      return s ? s.count : "-";
    };
    return `${find("TOTAL_GOALS")}.${find("TOTAL_BEHINDS")} (${find("TOTAL_SCORE")})`;
  }

  _scoreBreakdown(scoreText, score) {
    if (!scoreText) return "";
    if (scoreText === String(score ?? "")) return "";
    return `<div class="phq-breakdown">${escapeHtml(scoreText)}</div>`;
  }

  _renderLive(attrs) {
    const live = attrs.live;
    if (!live) return "";
    const clockLine = live.period
      ? `${escapeHtml(live.period)}${live.clock_time ? " &middot; " + escapeHtml(live.clock_time) : ""}${live.clock_paused ? " (paused)" : ""}`
      : "";
    return `
      <div class="phq-section">
        <span class="phq-live-badge">Live</span>
        ${clockLine ? `<div class="phq-clock">${clockLine}</div>` : ""}
        <div class="phq-matchup">
          <div class="phq-team">
            ${this._logoImg(live.home.logo, live.home.name)}
            <div class="phq-team-name">${escapeHtml(live.home.name)}</div>
            <div class="phq-score">${live.home_score ?? "-"}</div>
            ${this._scoreBreakdown(live.home_score_text, live.home_score)}
          </div>
          <div class="phq-vs">vs</div>
          <div class="phq-team">
            ${this._logoImg(live.away.logo, live.away.name)}
            <div class="phq-team-name">${escapeHtml(live.away.name)}</div>
            <div class="phq-score">${live.away_score ?? "-"}</div>
            ${this._scoreBreakdown(live.away_score_text, live.away_score)}
          </div>
        </div>
        ${this._quarterTable(live.home.name, live.away.name, live.home_periods, live.away_periods)}
        ${live.venue ? `<div class="phq-meta">${escapeHtml(live.venue)}</div>` : ""}
      </div>
    `;
  }

  _renderNext(attrs) {
    const next = attrs.next_match;
    if (!next) return "";
    const date = (next.dates && next.dates[0]) || "";
    const when = [date, next.time].filter(Boolean).join(" ");
    return `
      <div class="phq-section">
        <div class="phq-section-label">Next match</div>
        <div class="phq-row">
          <span class="phq-row-teams">
            ${this._logoImg(next.home.logo, next.home.name)}
            ${escapeHtml(next.home.name)}
            <span>vs</span>
            ${escapeHtml(next.away.name)}
            ${this._logoImg(next.away.logo, next.away.name)}
          </span>
        </div>
        <div class="phq-meta">${escapeHtml([when, next.venue].filter(Boolean).join(" · "))}</div>
      </div>
    `;
  }

  _renderLastResult(attrs) {
    const last = attrs.last_result;
    if (!last) return "";
    const date = (last.dates && last.dates[0]) || "";
    return `
      <div class="phq-section">
        <div class="phq-section-label">Last result</div>
        <div class="phq-row">
          <span class="phq-row-teams">
            ${this._logoImg(last.home.logo, last.home.name)}
            ${escapeHtml(last.home.name)}
          </span>
          <span>${escapeHtml(last.home_score_text ?? String(last.home_score ?? "-"))} - ${escapeHtml(last.away_score_text ?? String(last.away_score ?? "-"))}</span>
          <span class="phq-row-teams">
            ${escapeHtml(last.away.name)}
            ${this._logoImg(last.away.logo, last.away.name)}
          </span>
        </div>
        <div class="phq-meta">${escapeHtml(date)}</div>
      </div>
    `;
  }

  _renderCareer(attrs) {
    const career = attrs.career;
    if (!career) return "";
    const totals = career.totals || {};
    const lines = Object.entries(totals)
      .filter(([, v]) => v != null)
      .map(([k, v]) => `<div class="phq-stat-line"><span>${escapeHtml(k.replace(/_/g, " "))}</span><span>${v}</span></div>`)
      .join("");
    const clubs = (career.clubs || [])
      .map((c) => {
        const t = statsText(c.statistics);
        return `<div class="phq-stat-line"><span>${escapeHtml(c.club_name || "Unknown club")}</span><span>${escapeHtml(t || "")}</span></div>`;
      })
      .join("");
    if (!lines && !clubs) return "";
    return `
      <div class="phq-section">
        <div class="phq-section-label">Career stats</div>
        ${lines}
        ${clubs ? `<div class="phq-sub-heading">By club</div>${clubs}` : ""}
      </div>
    `;
  }

  _renderSeason(attrs) {
    const season = attrs.current_season;
    if (!season) return "";
    const regs = (season.registrations || [])
      .map((r) => {
        const t = statsText(r.statistics);
        return `<div class="phq-stat-line"><span>${escapeHtml(r.club_name || r.role || "")}</span><span>${escapeHtml(t || "")}</span></div>`;
      })
      .join("");
    if (!regs) return "";
    return `
      <div class="phq-section">
        <div class="phq-section-label">${escapeHtml(season.season_name || "Current season")}</div>
        ${regs}
      </div>
    `;
  }

  _renderContent(stateObj) {
    const attrs = stateObj.attributes || {};
    const title = this._config.title || attrs.team_name || attrs.player_name || "PlayHQ";
    const sub = [attrs.grade_name, attrs.org_name].filter(Boolean).join(" · ");

    const renderers = {
      live: () => this._renderLive(attrs),
      next: () => this._renderNext(attrs),
      last_result: () => this._renderLastResult(attrs),
      career: () => this._renderCareer(attrs),
      season: () => this._renderSeason(attrs),
    };

    const order = (this._config.section_order || SECTION_KEYS).filter((k) => renderers[k]);
    const disabled = new Set(this._config.disabled_sections || []);

    let body = "";
    for (const key of order) {
      if (disabled.has(key)) continue;
      body += renderers[key]();
    }

    if (!body) {
      body = `<div class="phq-empty">No data available yet.</div>`;
    }

    this._content.innerHTML = `
      <div class="phq-header">
        <div>
          <div class="phq-title">${escapeHtml(title)}</div>
          ${sub ? `<div class="phq-sub">${sub}</div>` : ""}
        </div>
      </div>
      ${body}
    `;
  }
}

customElements.define("playhq-card", PlayHQCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "playhq-card",
  name: "PlayHQ",
  description: "Live scores, next match, last result, and player stats for PlayHQ (AFL, basketball, cricket).",
});

/* ------------------------------------------------------------------ */
/* Visual editor                                                        */
/* ------------------------------------------------------------------ */
class PlayHQCardEditor extends HTMLElement {
  setConfig(config) {
    this._config = {
      show_logos: true,
      show_quarters: true,
      section_order: SECTION_KEYS.slice(),
      disabled_sections: [],
      ...config,
    };
    // make sure any section keys missing from an older config are appended
    for (const key of SECTION_KEYS) {
      if (!this._config.section_order.includes(key)) this._config.section_order.push(key);
    }
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    if (this._built) this._populateEntities();
  }

  connectedCallback() {
    if (!this._built) this._render();
  }

  _emitChange() {
    this.dispatchEvent(new CustomEvent("config-changed", { detail: { config: this._config }, bubbles: true, composed: true }));
  }

  _playhqEntityIds() {
    if (this._hass && this._hass.entities) {
      const ids = Object.values(this._hass.entities)
        .filter((e) => e.platform === "playhq")
        .map((e) => e.entity_id);
      if (ids.length) return ids;
    }
    if (this._hass && this._hass.states) {
      return Object.keys(this._hass.states).filter((id) => id.startsWith("sensor.") && (id.includes("_status") || id.includes("games_played")));
    }
    return [];
  }

  _populateEntities() {
    const select = this.querySelector("#phq-entity");
    if (!select) return;
    const ids = this._playhqEntityIds();
    const current = this._config.entity;
    select.innerHTML = ids
      .map((id) => `<option value="${id}" ${id === current ? "selected" : ""}>${id}</option>`)
      .join("") || `<option value="${current || ""}">${current || "(no PlayHQ entities found)"}</option>`;
  }

  _render() {
    this._built = true;
    this.innerHTML = `
      <style>
        .phq-ed-row { margin-bottom: 12px; }
        .phq-ed-label { display:block; font-size: 12px; font-weight: 500; margin-bottom: 4px; color: var(--secondary-text-color); }
        .phq-ed-row select, .phq-ed-row input[type=text] { width: 100%; padding: 8px; border-radius: 6px; border: 1px solid var(--divider-color); background: var(--card-background-color); color: var(--primary-text-color); box-sizing: border-box; }
        .phq-ed-check { display:flex; align-items:center; gap:8px; margin-bottom: 6px; font-size: 13px; }
        .phq-section-row { display:flex; align-items:center; gap:8px; padding:6px 0; border-bottom: 1px solid var(--divider-color); font-size: 13px; }
        .phq-section-row:last-child { border-bottom: none; }
        .phq-section-row span.name { flex: 1; }
        .phq-section-row button { border:none; background: var(--secondary-background-color); border-radius:4px; width:28px; height:28px; cursor:pointer; font-size: 14px; }
        .phq-section-row button:disabled { opacity: 0.3; cursor: default; }
        h4 { margin: 0 0 6px; font-size: 13px; color: var(--secondary-text-color); }
      </style>
      <div class="phq-ed-row">
        <label class="phq-ed-label">Entity</label>
        <select id="phq-entity"></select>
      </div>
      <div class="phq-ed-row">
        <label class="phq-ed-label">Title (optional override)</label>
        <input id="phq-title" type="text" value="${escapeHtml(this._config.title || "")}" placeholder="Uses the team/player name if blank">
      </div>
      <div class="phq-ed-row">
        <label class="phq-ed-check"><input id="phq-logos" type="checkbox" ${this._config.show_logos ? "checked" : ""}> Show team logos</label>
        <label class="phq-ed-check"><input id="phq-quarters" type="checkbox" ${this._config.show_quarters ? "checked" : ""}> Show quarter-by-quarter breakdown</label>
      </div>
      <div class="phq-ed-row">
        <h4>Sections (check to show, arrows to reorder)</h4>
        <div id="phq-sections"></div>
      </div>
    `;

    this._populateEntities();
    this._renderSections();

    this.querySelector("#phq-entity").addEventListener("change", (e) => {
      this._config.entity = e.target.value;
      this._emitChange();
    });
    this.querySelector("#phq-title").addEventListener("input", (e) => {
      this._config.title = e.target.value;
      this._emitChange();
    });
    this.querySelector("#phq-logos").addEventListener("change", (e) => {
      this._config.show_logos = e.target.checked;
      this._emitChange();
    });
    this.querySelector("#phq-quarters").addEventListener("change", (e) => {
      this._config.show_quarters = e.target.checked;
      this._emitChange();
    });
  }

  _renderSections() {
    const container = this.querySelector("#phq-sections");
    if (!container) return;
    const order = this._config.section_order;
    const disabled = new Set(this._config.disabled_sections || []);
    const labelFor = (key) => (ALL_SECTIONS.find((s) => s.key === key) || {}).label || key;

    container.innerHTML = order
      .map(
        (key, i) => `
        <div class="phq-section-row" data-key="${key}">
          <input type="checkbox" class="phq-sec-toggle" ${disabled.has(key) ? "" : "checked"}>
          <span class="name">${escapeHtml(labelFor(key))}</span>
          <button class="phq-sec-up" ${i === 0 ? "disabled" : ""} title="Move up">&uarr;</button>
          <button class="phq-sec-down" ${i === order.length - 1 ? "disabled" : ""} title="Move down">&darr;</button>
        </div>`
      )
      .join("");

    container.querySelectorAll(".phq-sec-toggle").forEach((el) => {
      el.addEventListener("change", (e) => {
        const key = e.target.closest(".phq-section-row").dataset.key;
        const set = new Set(this._config.disabled_sections || []);
        if (e.target.checked) set.delete(key);
        else set.add(key);
        this._config.disabled_sections = [...set];
        this._emitChange();
      });
    });
    container.querySelectorAll(".phq-sec-up").forEach((el) => {
      el.addEventListener("click", (e) => {
        const key = e.target.closest(".phq-section-row").dataset.key;
        const idx = this._config.section_order.indexOf(key);
        if (idx > 0) {
          const arr = this._config.section_order;
          [arr[idx - 1], arr[idx]] = [arr[idx], arr[idx - 1]];
          this._renderSections();
          this._emitChange();
        }
      });
    });
    container.querySelectorAll(".phq-sec-down").forEach((el) => {
      el.addEventListener("click", (e) => {
        const key = e.target.closest(".phq-section-row").dataset.key;
        const arr = this._config.section_order;
        const idx = arr.indexOf(key);
        if (idx >= 0 && idx < arr.length - 1) {
          [arr[idx + 1], arr[idx]] = [arr[idx], arr[idx + 1]];
          this._renderSections();
          this._emitChange();
        }
      });
    });
  }
}

customElements.define("playhq-card-editor", PlayHQCardEditor);
