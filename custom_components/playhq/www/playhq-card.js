/* PlayHQ Lovelace card - vanilla web component, no build step, no external deps. */

class PlayHQCard extends HTMLElement {
  setConfig(config) {
    if (!config.entity) {
      throw new Error("playhq-card: 'entity' is required (the PlayHQ sensor).");
    }
    this._config = {
      show_live: true,
      show_next: true,
      show_last_result: true,
      show_logos: true,
      show_quarters: true,
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
    const entity = Object.keys(hass.states).find((e) => e.startsWith("sensor.") && e.includes("_status"));
    return {
      entity: entity || "sensor.your_team_status",
      show_live: true,
      show_next: true,
      show_last_result: true,
      show_logos: true,
      show_quarters: true,
    };
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
    return `<img src="${logoUrl}" alt="${this._escape(alt || "")}">`;
  }

  _escape(str) {
    const div = document.createElement("div");
    div.textContent = str == null ? "" : String(str);
    return div.innerHTML;
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
      <tr><th></th><th>${this._escape(homeName)}</th><th>${this._escape(awayName)}</th></tr>
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

  _renderLive(live) {
    if (!this._config.show_live || !live) return "";
    const clockLine = live.period
      ? `${this._escape(live.period)}${live.clock_time ? " &middot; " + this._escape(live.clock_time) : ""}${live.clock_paused ? " (paused)" : ""}`
      : "";
    return `
      <div class="phq-section">
        <span class="phq-live-badge">Live</span>
        ${clockLine ? `<div class="phq-clock">${clockLine}</div>` : ""}
        <div class="phq-matchup">
          <div class="phq-team">
            ${this._logoImg(live.home.logo, live.home.name)}
            <div class="phq-team-name">${this._escape(live.home.name)}</div>
            <div class="phq-score">${live.home_score ?? "-"}</div>
            <div class="phq-breakdown">${live.home_goals ?? "-"}.${live.home_behinds ?? "-"}</div>
          </div>
          <div class="phq-vs">vs</div>
          <div class="phq-team">
            ${this._logoImg(live.away.logo, live.away.name)}
            <div class="phq-team-name">${this._escape(live.away.name)}</div>
            <div class="phq-score">${live.away_score ?? "-"}</div>
            <div class="phq-breakdown">${live.away_goals ?? "-"}.${live.away_behinds ?? "-"}</div>
          </div>
        </div>
        ${this._quarterTable(live.home.name, live.away.name, live.home_periods, live.away_periods)}
        ${live.venue ? `<div class="phq-meta">${this._escape(live.venue)}</div>` : ""}
      </div>
    `;
  }

  _renderNext(next) {
    if (!this._config.show_next || !next) return "";
    const date = (next.dates && next.dates[0]) || "";
    const when = [date, next.time].filter(Boolean).join(" ");
    return `
      <div class="phq-section">
        <div class="phq-section-label">Next match</div>
        <div class="phq-row">
          <span class="phq-row-teams">
            ${this._logoImg(next.home.logo, next.home.name)}
            ${this._escape(next.home.name)}
            <span>vs</span>
            ${this._escape(next.away.name)}
            ${this._logoImg(next.away.logo, next.away.name)}
          </span>
        </div>
        <div class="phq-meta">${this._escape([when, next.venue].filter(Boolean).join(" &middot; "))}</div>
      </div>
    `;
  }

  _renderLastResult(last) {
    if (!this._config.show_last_result || !last) return "";
    const date = (last.dates && last.dates[0]) || "";
    return `
      <div class="phq-section">
        <div class="phq-section-label">Last result</div>
        <div class="phq-row">
          <span class="phq-row-teams">
            ${this._logoImg(last.home.logo, last.home.name)}
            ${this._escape(last.home.name)}
          </span>
          <span>${last.home_score ?? "-"} - ${last.away_score ?? "-"}</span>
          <span class="phq-row-teams">
            ${this._escape(last.away.name)}
            ${this._logoImg(last.away.logo, last.away.name)}
          </span>
        </div>
        <div class="phq-meta">${this._escape(date)}</div>
      </div>
    `;
  }

  _renderContent(stateObj) {
    const attrs = stateObj.attributes || {};
    const title = this._config.title || attrs.team_name || "PlayHQ";
    const sub = [attrs.grade_name, attrs.org_name].filter(Boolean).join(" &middot; ");

    let body = "";
    body += this._renderLive(attrs.live);
    body += this._renderNext(attrs.next_match);
    body += this._renderLastResult(attrs.last_result);

    if (!body) {
      body = `<div class="phq-empty">No fixture data available yet.</div>`;
    }

    this._content.innerHTML = `
      <div class="phq-header">
        <div>
          <div class="phq-title">${this._escape(title)}</div>
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
  description: "Live scores, next match and last result for a PlayHQ team.",
});
