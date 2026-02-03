(function () {
  const selectEl = document.getElementById("team-select");
  const btnEl = document.getElementById("btn-go");
  const resultsEl = document.getElementById("results");
  const loadingMsgEl = document.getElementById("loading-msg");
  const resultsContentEl = document.getElementById("results-content");
  const teamHeadingEl = document.getElementById("team-heading");
  const summaryEl = document.getElementById("summary");
  const gamesEl = document.getElementById("games");

  var LOGO_BASE = "https://a.espncdn.com/i/teamlogos/nba/500";
  var LOGO_SLUG = { uta: "utah", brk: "bkn", gsw: "gs", nop: "no", sas: "sa", nyk: "ny", njk: "nj" };
  function getLogoUrl(abbr) {
    var key = (abbr || "nba").toLowerCase();
    return LOGO_BASE + "/" + (LOGO_SLUG[key] || key) + ".png";
  }

  function showMsg(msg, isError) {
    var textEl = loadingMsgEl.querySelector && loadingMsgEl.querySelector(".loading-text");
    if (textEl) textEl.textContent = msg;
    else loadingMsgEl.textContent = msg;
    loadingMsgEl.className = isError ? "error" : "loading loading-with-spinner";
    loadingMsgEl.classList.remove("hidden");
    if (resultsContentEl) resultsContentEl.style.display = "none";
  }

  function hideMsgAndShowContent() {
    loadingMsgEl.classList.add("hidden");
    loadingMsgEl.classList.remove("loading-with-spinner");
    if (resultsContentEl) resultsContentEl.style.display = "";
  }

  var heroEl = document.getElementById("hero");
  var leagueOverviewEl = document.getElementById("league-overview");
  var leagueOverviewUndersEl = document.getElementById("league-overview-unders");
  var heatmapWrapEl = document.getElementById("full-heatmap-wrap");
  var btnBackEl = document.getElementById("btn-back");

  function backToLeagueView() {
    resultsEl.classList.add("hidden");
    if (heroEl) heroEl.classList.remove("hidden");
    if (leagueOverviewEl) leagueOverviewEl.classList.remove("hidden");
    if (leagueOverviewUndersEl) leagueOverviewUndersEl.classList.remove("hidden");
    if (heatmapWrapEl) heatmapWrapEl.classList.remove("hidden");
  }

  async function loadTeams() {
    try {
      const r = await fetch("/api/teams");
      const teams = await r.json();
      selectEl.innerHTML = '<option value="">Select a team</option>';
      teams.forEach(function (t) {
        const opt = document.createElement("option");
        opt.value = t.id;
        opt.textContent = t.full_name;
        selectEl.appendChild(opt);
      });
    } catch (e) {
      showMsg("Could not load teams.", true);
      resultsEl.classList.remove("hidden");
    }
  }

  function formatVariance(pct) {
    if (pct == null) return "—";
    return (pct >= 0 ? "+" : "") + pct + "%";
  }

  function varianceClass(pct) {
    if (pct == null) return "neutral";
    if (pct > 0) return "positive";
    if (pct < 0) return "negative";
    return "neutral";
  }

  function vsLeagueVarianceClass(pct) {
    if (pct == null) return "neutral";
    if (pct > 0) return "worse";  // allowing more than league = bad = red
    if (pct < 0) return "better"; // allowing less than league = good = green
    return "neutral";
  }

  function arrow(pct) {
    if (pct == null) return "";
    if (pct > 0) return " ↑";
    if (pct < 0) return " ↓";
    return "";
  }

  function summaryVarianceText(pct) {
    if (pct == null) return "—";
    var rounded = Math.round(Math.abs(pct));
    if (rounded === 0) return "Same as league avg";
    if (pct > 0) return rounded + "% WORSE vs League avg";
    return rounded + "% BETTER vs League avg";
  }

  function renderSummary(data) {
    const s = data.summary;
    var ppgText = summaryVarianceText(s.ppg_vs_league_pct);
    var rpgText = summaryVarianceText(s.rpg_vs_league_pct);
    var apgText = summaryVarianceText(s.apg_vs_league_pct);
    var ppgClass = vsLeagueVarianceClass(s.ppg_vs_league_pct);
    var rpgClass = vsLeagueVarianceClass(s.rpg_vs_league_pct);
    var apgClass = vsLeagueVarianceClass(s.apg_vs_league_pct);
    var leagueNote = s.league_avg_ppg != null ? '<p class="summary-league-note">League avg: ' + s.league_avg_ppg + ' PPG, ' + (s.league_avg_rpg || "—") + ' RPG, ' + (s.league_avg_apg || "—") + ' APG</p>' : '';
    summaryEl.innerHTML =
      '<div class="summary-card"><div class="value">' + s.ppg_allowed + '</div><div class="label">PPG allowed</div><div class="summary-variance ' + ppgClass + '">' + ppgText + '</div></div>' +
      '<div class="summary-card"><div class="value">' + s.rpg_allowed + '</div><div class="label">RPG allowed</div><div class="summary-variance ' + rpgClass + '">' + rpgText + '</div></div>' +
      '<div class="summary-card"><div class="value">' + s.apg_allowed + '</div><div class="label">APG allowed</div><div class="summary-variance ' + apgClass + '">' + apgText + '</div></div>' +
      leagueNote;
  }

  function escapeHtml(s) {
    if (!s) return "";
    const div = document.createElement("div");
    div.textContent = s;
    return div.innerHTML;
  }

  function renderGame(game) {
    const top3 = game.top3_scorers || [];
    const rows = top3.map(function (p) {
      const avg = p.season_avg_ppg != null ? p.season_avg_ppg + " ppg" : "—";
      const vClass = varianceClass(p.variance_pct);
      const vStr = formatVariance(p.variance_pct);
      return '<div class="scorer-row">' +
        '<span class="scorer-name">' + escapeHtml(p.player_name) + '</span>' +
        '<span class="scorer-pts">' + p.points + '</span>' +
        '<span class="scorer-avg">' + avg + '</span>' +
        '<span class="variance ' + vClass + '">' + vStr + arrow(p.variance_pct) + '</span></div>';
    }).join("");

    let scoreStr = "";
    if (game.our_pts != null && game.opp_pts != null) {
      scoreStr = "Final: " + game.our_pts + " – " + game.opp_pts;
      if (game.opp_reb != null) scoreStr += " · Opponent: " + game.opp_pts + " pts, " + game.opp_reb + " reb, " + game.opp_ast + " ast";
    } else if (game.opp_pts != null) {
      scoreStr = "Opponent: " + game.opp_pts + " pts" + (game.opp_reb != null ? ", " + game.opp_reb + " reb, " + game.opp_ast + " ast" : "");
    }

    return '<div class="game-card">' +
      '<div class="game-header">' +
      '<div><div class="game-date">' + escapeHtml(game.date) + '</div><div class="game-matchup">' + escapeHtml(game.matchup) + '</div></div>' +
      (scoreStr ? '<div class="game-score">' + scoreStr + '</div>' : '') +
      '</div>' +
      '<div class="scorers"><div class="scorers-title">Top 3 opponent scorers in this game</div>' +
      '<div class="scorer-header"><span class="scorer-name">Player</span><span>Pts (game)</span><span>Season avg</span><span>Vs avg</span></div>' +
      (rows || '<div class="scorer-row">No data</div>') + '</div></div>';
  }

  function renderLeagueCharts(data) {
    var teams = data.teams || [];
    var loadingEl = document.getElementById("league-loading");
    var loadingUndersEl = document.getElementById("league-loading-unders");
    var chartPpg = document.getElementById("chart-ppg");
    var chartRpg = document.getElementById("chart-rpg");
    var chartApg = document.getElementById("chart-apg");
    var chartPpgUnder = document.getElementById("chart-ppg-under");
    var chartRpgUnder = document.getElementById("chart-rpg-under");
    var chartApgUnder = document.getElementById("chart-apg-under");
    if (!chartPpg || !chartRpg || !chartApg) return;

    var MAX_BAR_PCT = 25;
    function barWidth(pct) {
      if (pct == null) return 0;
      var abs = Math.abs(pct);
      return Math.min(100, (abs / MAX_BAR_PCT) * 100);
    }
    function barHtml(teamsSorted, statKey) {
      return teamsSorted.slice(0, 3).map(function (t) {
        var pct = t[statKey];
        var vClass = pct == null ? "neutral" : pct > 0 ? "worse" : pct < 0 ? "better" : "neutral";
        var label = pct == null ? "—" : (pct > 0 ? "+" : "") + Math.round(pct) + "%";
        var width = barWidth(pct);
        var logoUrl = getLogoUrl(t.team_abbreviation);
        return '<div class="league-chart-bar-row">' +
          '<span class="league-chart-bar-label" title="' + escapeHtml(t.team_name) + '">' +
          '<img src="' + logoUrl + '" alt="' + escapeHtml(t.team_abbreviation) + '" class="team-logo-chart" onerror="this.style.display=\'none\';this.nextElementSibling.style.display=\'inline\'" />' +
          '<span class="team-logo-fallback" style="display:none">' + escapeHtml(t.team_abbreviation) + '</span>' +
          '</span>' +
          '<div class="league-chart-bar-track">' +
          '<div class="league-chart-bar-fill ' + vClass + '" style="width:' + width + '%"></div>' +
          '</div>' +
          '<span class="league-chart-bar-value ' + vClass + '">' + label + '</span>' +
          '</div>';
      }).join("");
    }

    // OVERS: worst defense first (highest variance)
    var byPpg = teams.slice().sort(function (a, b) {
      var ap = a.ppg_vs_league_pct != null ? a.ppg_vs_league_pct : -999;
      var bp = b.ppg_vs_league_pct != null ? b.ppg_vs_league_pct : -999;
      return bp - ap;
    });
    var byRpg = teams.slice().sort(function (a, b) {
      var ap = a.rpg_vs_league_pct != null ? a.rpg_vs_league_pct : -999;
      var bp = b.rpg_vs_league_pct != null ? b.rpg_vs_league_pct : -999;
      return bp - ap;
    });
    var byApg = teams.slice().sort(function (a, b) {
      var ap = a.apg_vs_league_pct != null ? a.apg_vs_league_pct : -999;
      var bp = b.apg_vs_league_pct != null ? b.apg_vs_league_pct : -999;
      return bp - ap;
    });

    chartPpg.innerHTML = barHtml(byPpg.slice(0, 3), "ppg_vs_league_pct");
    chartRpg.innerHTML = barHtml(byRpg.slice(0, 3), "rpg_vs_league_pct");
    chartApg.innerHTML = barHtml(byApg.slice(0, 3), "apg_vs_league_pct");
    if (loadingEl) loadingEl.style.display = "none";

    // UNDERS: only teams giving up LESS than league avg (exclude 0% — use rounded value so we exclude e.g. -0.4% that displays as 0%)
    function isStrictlyNegative(pct) { var v = Number(pct); return !isNaN(v) && Math.round(v) < 0; }
    var ppgNegative = teams.filter(function (t) { return isStrictlyNegative(t.ppg_vs_league_pct); });
    var rpgNegative = teams.filter(function (t) { return isStrictlyNegative(t.rpg_vs_league_pct); });
    var apgNegative = teams.filter(function (t) { return isStrictlyNegative(t.apg_vs_league_pct); });
    var byPpgUnder = ppgNegative.slice().sort(function (a, b) { return a.ppg_vs_league_pct - b.ppg_vs_league_pct; }).slice(0, 3);
    var byRpgUnder = rpgNegative.slice().sort(function (a, b) { return a.rpg_vs_league_pct - b.rpg_vs_league_pct; }).slice(0, 3);
    var byApgUnder = apgNegative.slice().sort(function (a, b) { return a.apg_vs_league_pct - b.apg_vs_league_pct; }).slice(0, 3);

    if (chartPpgUnder) chartPpgUnder.innerHTML = barHtml(byPpgUnder, "ppg_vs_league_pct");
    if (chartRpgUnder) chartRpgUnder.innerHTML = barHtml(byRpgUnder, "rpg_vs_league_pct");
    if (chartApgUnder) chartApgUnder.innerHTML = barHtml(byApgUnder, "apg_vs_league_pct");
    if (loadingUndersEl) loadingUndersEl.style.display = "none";

    renderTableSummary(data, true);
    renderTableSummary(data, false);
    renderFullHeatmap(data);
    var heatmapWrap = document.getElementById("full-heatmap-wrap");
    if (heatmapWrap) heatmapWrap.classList.remove("hidden");
  }

  function renderTableSummary(data, isOvers) {
    var teams = data.teams || [];
    var abbrToTeam = {};
    teams.forEach(function (t) { abbrToTeam[(t.team_abbreviation || "").toUpperCase()] = t; });

    var top3Ppg, top3Rpg, top3Apg;
    if (isOvers) {
      top3Ppg = teams.slice().sort(function (a, b) { return (b.ppg_vs_league_pct || -999) - (a.ppg_vs_league_pct || -999); }).slice(0, 3);
      top3Rpg = teams.slice().sort(function (a, b) { return (b.rpg_vs_league_pct || -999) - (a.rpg_vs_league_pct || -999); }).slice(0, 3);
      top3Apg = teams.slice().sort(function (a, b) { return (b.apg_vs_league_pct || -999) - (a.apg_vs_league_pct || -999); }).slice(0, 3);
    } else {
      top3Ppg = teams.filter(function (t) { return Number(t.ppg_vs_league_pct) < 0; }).sort(function (a, b) { return a.ppg_vs_league_pct - b.ppg_vs_league_pct; }).slice(0, 3);
      top3Rpg = teams.filter(function (t) { return Number(t.rpg_vs_league_pct) < 0; }).sort(function (a, b) { return a.rpg_vs_league_pct - b.rpg_vs_league_pct; }).slice(0, 3);
      top3Apg = teams.filter(function (t) { return Number(t.apg_vs_league_pct) < 0; }).sort(function (a, b) { return a.apg_vs_league_pct - b.apg_vs_league_pct; }).slice(0, 3);
    }

    function initialLastName(fullName) {
      if (!fullName || !fullName.trim()) return "—";
      var parts = fullName.trim().split(/\s+/);
      if (parts.length === 1) return escapeHtml(parts[0]);
      return escapeHtml(parts[0].charAt(0) + ". " + parts[parts.length - 1]);
    }
    function miniTableHtml(sectionTitle, top3Teams, statKey, col3Header, apiStat) {
      var valKey = statKey === "top_3_scorers" ? "ppg" : statKey === "top_3_rebounders" ? "rpg" : "apg";
      var rows = top3Teams.map(function (t) {
        var logoUrl = getLogoUrl(t.team_abbreviation);
        var targetCell = '<img src="' + logoUrl + '" alt="' + escapeHtml(t.team_abbreviation) + '" title="' + escapeHtml(t.team_name) + '" class="summary-table-logo" onerror="this.style.display=\'none\'">';
        var oppAbbr = (t.next_opponent_abbr || "").toUpperCase();
        var oppTeam = oppAbbr ? abbrToTeam[oppAbbr] : null;
        var oppLogo = "—";
        if (t.next_opponent_abbr) {
          oppLogo = '<img src="' + getLogoUrl(t.next_opponent_abbr) + '" alt="' + escapeHtml(t.next_opponent_abbr) + '" title="' + escapeHtml(t.next_opponent_name || "") + '" class="summary-table-logo" onerror="this.style.display=\'none\'">';
        }
        var list = (oppTeam && oppTeam[statKey]) ? oppTeam[statKey].slice(0, 2) : [];
        if (list.length === 0) {
          return "<tr><td>" + targetCell + "</td><td>" + oppLogo + "</td><td>—</td><td>—</td></tr>";
        }
        var first = list[0];
        var pid1 = first.player_id != null ? first.player_id : "";
        var row1 = "<tr><td rowspan=\"" + list.length + "\">" + targetCell + "</td><td rowspan=\"" + list.length + "\">" + oppLogo + "</td>" +
          "<td>" + initialLastName(first.player_name) + " <span class=\"stat-num\">(" + first[valKey] + ")</span></td>" +
          "<td class=\"last-10-cell\" data-player-id=\"" + pid1 + "\">—</td></tr>";
        var rest = list.slice(1).map(function (p) {
          var pid = p.player_id != null ? p.player_id : "";
          return "<tr><td>" + initialLastName(p.player_name) + " <span class=\"stat-num\">(" + p[valKey] + ")</span></td>" +
            "<td class=\"last-10-cell\" data-player-id=\"" + pid + "\">—</td></tr>";
        }).join("");
        return row1 + rest;
      }).join("");
      return '<div class="summary-subtable-wrap summary-subtable-' + apiStat + '" data-stat="' + apiStat + '"><h4 class="summary-subtable-title">' + escapeHtml(sectionTitle) + "</h4>" +
        '<table class="summary-table"><thead><tr><th>Target</th><th>Next opp</th><th>Player (Season AVG)</th><th>Last 10 Games</th></tr></thead><tbody>' + rows + '</tbody></table></div>';
    }

    var lead = isOvers
      ? "If you're betting OVERS, consider going against these teams"
      : "If you're betting UNDERS, consider going against these teams";
    var html = '<p class="summary-lead">' + escapeHtml(lead) + "</p>" +
      '<div class="summary-content">' +
      miniTableHtml("Points", top3Ppg, "top_3_scorers", "Player (avg)", "pts") +
      miniTableHtml("Rebounds", top3Rpg, "top_3_rebounders", "Player (avg)", "reb") +
      miniTableHtml("Assists", top3Apg, "top_3_assisters", "Player (avg)", "ast") +
      "</div>";

    var el = document.getElementById(isOvers ? "overs-summary" : "unders-summary");
    if (el) {
      el.innerHTML = html;
      el.classList.remove("hidden");
      fillSummaryLast10(el);
    }
  }

  function fillSummaryLast10(container) {
    if (!container) return;
    var subtables = [].slice.call(container.querySelectorAll(".summary-subtable-wrap[data-stat]"));
    function fetchOne(index) {
      if (index >= subtables.length) return Promise.resolve();
      var wrap = subtables[index];
      var stat = wrap.getAttribute("data-stat");
      var cells = wrap.querySelectorAll(".last-10-cell[data-player-id]");
      var ids = [];
      var idToCell = {};
      cells.forEach(function (cell) {
        var id = (cell.getAttribute("data-player-id") || "").trim();
        if (id) { ids.push(id); idToCell[id] = cell; }
      });
      if (ids.length === 0) return fetchOne(index + 1);
      return fetch("/api/players-last-10?ids=" + encodeURIComponent(ids.join(",")) + "&stat=" + encodeURIComponent(stat))
        .then(function (r) { return r.json(); })
        .then(function (data) {
          if (data && typeof data === "object" && !data.error) {
            ids.forEach(function (id) {
              var cell = idToCell[id];
              if (!cell || !data[id]) return;
              cell.textContent = Array.isArray(data[id]) ? data[id].join(", ") : String(data[id]);
            });
          }
        })
        .catch(function () { })
        .then(function () { return fetchOne(index + 1); });
    }
    fetchOne(0);
  }

  var _heatmapData = null;
  var _heatmapSortCol = 1;
  var _heatmapSortDir = -1;

  function getHeatmapSortKey(t, col) {
    if (col === 0) return (t.team_abbreviation || "").toLowerCase();
    if (col === 1) return t.ppg_allowed != null ? t.ppg_allowed : -9999;
    if (col === 2) return t.ppg_vs_league_pct != null ? t.ppg_vs_league_pct : -9999;
    if (col === 3) return t.rpg_allowed != null ? t.rpg_allowed : -9999;
    if (col === 4) return t.rpg_vs_league_pct != null ? t.rpg_vs_league_pct : -9999;
    if (col === 5) return t.apg_allowed != null ? t.apg_allowed : -9999;
    if (col === 6) return t.apg_vs_league_pct != null ? t.apg_vs_league_pct : -9999;
    return 0;
  }

  function renderFullHeatmap(data, sortCol, sortDir) {
    if (data && data.teams) _heatmapData = data.teams;
    var teams = _heatmapData || [];
    if (!teams.length) return;
    if (sortCol != null) _heatmapSortCol = sortCol;
    if (sortDir != null) _heatmapSortDir = sortDir;
    var col = _heatmapSortCol;
    var dir = _heatmapSortDir;

    var wrap = document.getElementById("full-heatmap-table");
    if (!wrap) return;

    var sorted = teams.slice().sort(function (a, b) {
      var ak = getHeatmapSortKey(a, col);
      var bk = getHeatmapSortKey(b, col);
      if (typeof ak === "string") return dir * (ak < bk ? -1 : ak > bk ? 1 : 0);
      return dir * (ak - bk);
    });

    var ppgVals = teams.map(function (t) { return t.ppg_vs_league_pct; }).filter(function (v) { return v != null; });
    var rpgVals = teams.map(function (t) { return t.rpg_vs_league_pct; }).filter(function (v) { return v != null; });
    var apgVals = teams.map(function (t) { return t.apg_vs_league_pct; }).filter(function (v) { return v != null; });
    function minMax(arr) {
      if (!arr.length) return { min: 0, max: 0 };
      return { min: Math.min.apply(null, arr), max: Math.max.apply(null, arr) };
    }
    var ppgMm = minMax(ppgVals);
    var rpgMm = minMax(rpgVals);
    var apgMm = minMax(apgVals);
    function heatStyle(pct, mm) {
      if (pct == null || mm.max === mm.min) return "";
      var pctNorm = (pct - mm.min) / (mm.max - mm.min);
      if (pctNorm >= 0.5) {
        var g = 0.12 + (pctNorm - 0.5) * 0.6;
        return "background:rgba(34,197,94," + Math.min(0.45, g) + ");";
      }
      var r = 0.12 + (0.5 - pctNorm) * 0.6;
      return "background:rgba(239,68,68," + Math.min(0.45, r) + ");";
    }

    function oneDec(val) { return val != null ? Number(val).toFixed(1) : "—"; }
    function pctOneDec(pct) { return pct != null ? (pct > 0 ? "+" : "") + Number(pct).toFixed(1) + "%" : "—"; }
    var rows = sorted.map(function (t) {
      var logoUrl = getLogoUrl(t.team_abbreviation);
      var ppgPct = pctOneDec(t.ppg_vs_league_pct);
      var rpgPct = pctOneDec(t.rpg_vs_league_pct);
      var apgPct = pctOneDec(t.apg_vs_league_pct);
      return "<tr>" +
        "<td><img src=\"" + logoUrl + "\" alt=\"\" class=\"team-logo-mini\" onerror=\"this.style.display='none'\">" + escapeHtml(t.team_abbreviation) + "</td>" +
        "<td>" + oneDec(t.ppg_allowed) + "</td>" +
        "<td class=\"heat-cell\" style=\"" + heatStyle(t.ppg_vs_league_pct, ppgMm) + "\">" + ppgPct + "</td>" +
        "<td>" + oneDec(t.rpg_allowed) + "</td>" +
        "<td class=\"heat-cell\" style=\"" + heatStyle(t.rpg_vs_league_pct, rpgMm) + "\">" + rpgPct + "</td>" +
        "<td>" + oneDec(t.apg_allowed) + "</td>" +
        "<td class=\"heat-cell\" style=\"" + heatStyle(t.apg_vs_league_pct, apgMm) + "\">" + apgPct + "</td></tr>";
    }).join("");

    function thClass(i) {
      if (i !== col) return "";
      return dir === 1 ? "sort-asc" : "sort-desc";
    }
    var headers = [
      "<th data-sort-col=\"0\" class=\"" + thClass(0) + "\">Team</th>",
      "<th data-sort-col=\"1\" class=\"" + thClass(1) + "\">PPG</th>",
      "<th data-sort-col=\"2\" class=\"" + thClass(2) + "\">vs Lg</th>",
      "<th data-sort-col=\"3\" class=\"" + thClass(3) + "\">REB</th>",
      "<th data-sort-col=\"4\" class=\"" + thClass(4) + "\">vs Lg</th>",
      "<th data-sort-col=\"5\" class=\"" + thClass(5) + "\">AST</th>",
      "<th data-sort-col=\"6\" class=\"" + thClass(6) + "\">vs Lg</th>"
    ].join("");

    wrap.innerHTML = "<table><thead><tr>" + headers + "</tr></thead><tbody>" + rows + "</tbody></table>";

    wrap.querySelectorAll("thead th").forEach(function (th) {
      th.addEventListener("click", function () {
        var c = parseInt(th.getAttribute("data-sort-col"), 10);
        var newDir = (c === _heatmapSortCol && _heatmapSortDir === -1) ? 1 : -1;
        renderFullHeatmap(null, c, newDir);
      });
    });
  }

  async function loadLeagueOverview() {
    try {
      var r = await fetch("/api/league-defense-last-10");
      var data = await r.json();
      if (data.teams && data.teams.length > 0) {
        renderLeagueCharts(data);
      } else {
        var loadingEl = document.getElementById("league-loading");
        if (loadingEl) loadingEl.textContent = "No league data available.";
      }
    } catch (e) {
      var loadingEl = document.getElementById("league-loading");
      if (loadingEl) loadingEl.textContent = "Could not load league data.";
    }
  }

  function renderResults(data) {
    if (data.error && !data.games) {
      showMsg(escapeHtml(data.error), true);
      resultsEl.classList.remove("hidden");
      return;
    }
    if (heroEl) heroEl.classList.add("hidden");
    if (leagueOverviewEl) leagueOverviewEl.classList.add("hidden");
    if (leagueOverviewUndersEl) leagueOverviewUndersEl.classList.add("hidden");
    if (heatmapWrapEl) heatmapWrapEl.classList.add("hidden");
    hideMsgAndShowContent();
    var logoUrl = getLogoUrl(data.team_abbreviation);
    if (teamHeadingEl) {
      teamHeadingEl.innerHTML = "<img src=\"" + logoUrl.replace(/"/g, "&quot;") + "\" alt=\"\" class=\"team-heading-logo\" onerror=\"this.style.display='none'\">" +
        "<span>" + escapeHtml(data.team_name) + " — Last 10 games</span>";
    }
    renderSummary(data);
    var games = data.games || [];
    if (games.length === 0) {
      gamesEl.innerHTML = '<p class="error" style="margin:0;">No games found for this season. The NBA API may be slow or blocking — check the terminal where the server is running for errors, then try again.</p>';
    } else {
      gamesEl.innerHTML = games.map(renderGame).join("");
    }
    resultsEl.classList.remove("hidden");
  }

  async function fetchDefense() {
    const teamId = selectEl.value;
    if (!teamId) return;
    btnEl.disabled = true;
    resultsEl.classList.remove("hidden");
    showMsg("This may take 1–2 minutes. Fetching box scores — please keep this tab open.", false);
    var timeoutId = setTimeout(function() {}, 1);
    try {
      var controller = new AbortController();
      timeoutId = setTimeout(function() { controller.abort(); }, 120000);
      var r = await fetch("/api/team/" + encodeURIComponent(teamId) + "/defense-last-10", { signal: controller.signal });
      clearTimeout(timeoutId);
      var text = await r.text();
      var data;
      try {
        data = JSON.parse(text);
      } catch (parseErr) {
        showMsg("Server returned an error. Check the terminal. " + (text ? "Response: " + escapeHtml(text.slice(0, 300)) : ""), true);
        return;
      }
      if (!r.ok) {
        showMsg(escapeHtml(data.error || "Request failed"), true);
        return;
      }
      renderResults(data);
    } catch (e) {
      clearTimeout(timeoutId);
      if (e.name === "AbortError") {
        showMsg("Request timed out (over 2 minutes). Try again and leave the tab open.", true);
      } else {
        showMsg("Network error. Open the page at http://127.0.0.1:5000 (same as the server). Error: " + (e.message || String(e)), true);
      }
    } finally {
      btnEl.disabled = false;
    }
  }

  if (btnBackEl) btnBackEl.addEventListener("click", backToLeagueView);
  btnEl.addEventListener("click", fetchDefense);
  selectEl.addEventListener("keydown", function (e) { if (e.key === "Enter") fetchDefense(); });
  loadTeams();
  loadLeagueOverview();
})();
