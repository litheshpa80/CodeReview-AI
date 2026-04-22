const state = {
    bugChart: null,
    severityChart: null,
    prs: [],
    refreshHandle: null
};

const chartPalette = {
    text: "#44576d",
    grid: "rgba(130, 149, 176, 0.2)",
    accent: "#1d5eff",
    accentSoft: "rgba(29, 94, 255, 0.12)",
    low: "#1f8f5f",
    medium: "#b7791f",
    critical: "#c94a4a"
};

document.addEventListener("DOMContentLoaded", () => {
    setupNavigation();
    setupModal();
    setupBulkScan();
    setupJumpLinks();
    updateClock();
    refreshDashboard();

    window.setInterval(updateClock, 1000);
    state.refreshHandle = window.setInterval(refreshDashboard, 30000);
});

async function refreshDashboard() {
    try {
        const [metrics, stats, prs] = await Promise.all([
            fetchJSON("/api/metrics"),
            fetchJSON("/api/stats"),
            fetchJSON("/api/prs")
        ]);

        state.prs = prs;

        updateStats(stats);
        updateHero(stats);
        renderBugTrend(metrics);
        renderSeverity(stats);
        renderPRTable(prs);
        renderWatchlist(prs);
    } catch (error) {
        console.error("Dashboard refresh failed:", error);
    }
}

async function fetchJSON(url) {
    const response = await fetch(url);
    if (!response.ok) {
        throw new Error(`Request failed for ${url}: ${response.status}`);
    }
    return response.json();
}

function updateStats(stats) {
    const severity = stats.severity_dist || {};
    const totalFindings = Object.values(severity).reduce((sum, value) => sum + value, 0);

    setText("total-prs", stats.total_prs || 0);
    setText("total-reviews", stats.total_reviews || 0);
    setText("critical-findings", severity.CRITICAL || 0);
    setText("total-findings", totalFindings);
    setText("pr-count-pill", `${state.prs.length} PRs`);
}

function updateHero(stats) {
    const critical = (stats.severity_dist && stats.severity_dist.CRITICAL) || 0;
    const coverage = stats.total_prs ? Math.round((stats.total_reviews / stats.total_prs) * 100) : 0;

    setText("hero-critical", critical);
    setText("hero-coverage", `${coverage}%`);
    setText("hero-coverage-secondary", `${coverage}%`);
}

function renderBugTrend(metrics) {
    const ctx = document.getElementById("bugTrendChart").getContext("2d");
    const gradient = ctx.createLinearGradient(0, 0, 0, 320);
    gradient.addColorStop(0, "rgba(29, 94, 255, 0.22)");
    gradient.addColorStop(1, "rgba(29, 94, 255, 0.02)");

    const chartData = {
        labels: metrics.labels || [],
        datasets: [
            {
                label: "Bugs Found",
                data: metrics.bugs || [],
                borderColor: chartPalette.accent,
                backgroundColor: gradient,
                fill: true,
                tension: 0.38,
                pointRadius: 3,
                pointHoverRadius: 5,
                borderWidth: 3
            },
            {
                label: "Critical Issues",
                data: metrics.critical || [],
                borderColor: chartPalette.critical,
                backgroundColor: "rgba(201, 74, 74, 0.08)",
                fill: false,
                tension: 0.28,
                pointRadius: 3,
                pointHoverRadius: 5,
                borderWidth: 2
            }
        ]
    };

    if (state.bugChart) {
        state.bugChart.data = chartData;
        state.bugChart.update();
        return;
    }

    state.bugChart = new Chart(ctx, {
        type: "line",
        data: chartData,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    labels: {
                        color: chartPalette.text,
                        boxWidth: 12,
                        boxHeight: 12,
                        padding: 18
                    }
                },
                tooltip: {
                    backgroundColor: "rgba(24, 36, 51, 0.96)",
                    titleColor: "#ffffff",
                    bodyColor: "#dbe5f2",
                    borderColor: "rgba(255, 255, 255, 0.08)",
                    borderWidth: 1,
                    padding: 12,
                    displayColors: true
                }
            },
            interaction: {
                mode: "index",
                intersect: false
            },
            scales: {
                x: {
                    ticks: {
                        color: chartPalette.text,
                        maxRotation: 0,
                        autoSkip: true
                    },
                    grid: {
                        display: false,
                        drawBorder: false
                    }
                },
                y: {
                    beginAtZero: true,
                    ticks: {
                        color: chartPalette.text,
                        padding: 10
                    },
                    grid: {
                        color: chartPalette.grid,
                        drawBorder: false
                    }
                }
            }
        }
    });
}

function renderSeverity(stats) {
    const ctx = document.getElementById("severityChart").getContext("2d");
    const labels = ["LOW", "MEDIUM", "CRITICAL"];
    const values = labels.map((label) => (stats.severity_dist && stats.severity_dist[label]) || 0);
    const chartData = {
        labels,
        datasets: [
            {
                data: values,
                backgroundColor: [chartPalette.low, chartPalette.medium, chartPalette.critical],
                borderColor: "#ffffff",
                borderWidth: 5,
                hoverOffset: 6,
                spacing: 2
            }
        ]
    };

    if (state.severityChart) {
        state.severityChart.data = chartData;
        state.severityChart.update();
        return;
    }

    state.severityChart = new Chart(ctx, {
        type: "doughnut",
        data: chartData,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: "66%",
            plugins: {
                legend: {
                    position: "bottom",
                    labels: {
                        color: chartPalette.text,
                        boxWidth: 12,
                        boxHeight: 12,
                        padding: 18
                    }
                },
                tooltip: {
                    backgroundColor: "rgba(24, 36, 51, 0.96)",
                    titleColor: "#ffffff",
                    bodyColor: "#dbe5f2",
                    borderColor: "rgba(255, 255, 255, 0.08)",
                    borderWidth: 1,
                    padding: 12
                }
            }
        }
    });
}

function renderPRTable(prs) {
    const tableBody = document.getElementById("pr-table-body");
    tableBody.innerHTML = "";

    if (!prs.length) {
        const row = document.createElement("tr");
        row.innerHTML = `
            <td colspan="7">
                <p class="empty-state">No pull requests are available yet. Run a bulk scan or wait for the next refresh.</p>
            </td>
        `;
        tableBody.appendChild(row);
        return;
    }

    prs.forEach((pr) => {
        const issues = normalizeFeedback(pr.feedback);
        const dominantSeverity = getDominantSeverity(issues);
        const row = document.createElement("tr");

        row.innerHTML = `
            <td>${pr.id}</td>
            <td>
                <div class="pr-title-cell">
                    <span class="eyebrow">PR #${pr.id}</span>
                    <strong>${escapeHtml(pr.title || "Untitled pull request")}</strong>
                    <div class="pr-meta-row">
                        <span>${escapeHtml(pr.repo || "Unknown repo")}</span>
                    </div>
                </div>
            </td>
            <td>${escapeHtml(pr.author || "Unknown")}</td>
            <td>${escapeHtml(pr.repo || "Unknown repo")}</td>
            <td><span class="status-chip ${statusClass(pr.status)}">${escapeHtml(pr.status || "unknown")}</span></td>
            <td><span class="finding-chip ${findingClass(dominantSeverity)}">${issues.length} findings</span></td>
            <td><button class="view-btn" data-id="${pr.id}" type="button">View feedback</button></td>
        `;

        tableBody.appendChild(row);
    });

    tableBody.querySelectorAll(".view-btn").forEach((button) => {
        button.addEventListener("click", () => {
            const prId = Number(button.getAttribute("data-id"));
            const pr = state.prs.find((item) => item.id === prId);
            showFeedback(pr);
        });
    });
}

function renderWatchlist(prs) {
    const container = document.getElementById("review-watchlist");
    container.innerHTML = "";

    const prioritized = [...prs]
        .sort((a, b) => severityWeight(getDominantSeverity(normalizeFeedback(b.feedback))) - severityWeight(getDominantSeverity(normalizeFeedback(a.feedback))))
        .slice(0, 4);

    if (prioritized.length === 0) {
        container.innerHTML = '<p class="empty-state">No pull requests are available yet. Run a scan or wait for review records to arrive.</p>';
        return;
    }

    prioritized.forEach((pr) => {
        const issues = normalizeFeedback(pr.feedback);
        const dominantSeverity = getDominantSeverity(issues);
        const item = document.createElement("button");
        item.type = "button";
        item.className = "watchlist-item";
        item.innerHTML = `
            <div>
                <span class="watchlist-label">${escapeHtml(pr.repo || "Repository")}</span>
                <strong>${escapeHtml(pr.title || "Untitled pull request")}</strong>
            </div>
            <div class="watchlist-meta">
                <span class="status-chip ${statusClass(pr.status)}">${escapeHtml(pr.status || "unknown")}</span>
                <span class="finding-chip ${findingClass(dominantSeverity)}">${issues.length} findings</span>
            </div>
        `;
        item.addEventListener("click", () => showFeedback(pr));
        container.appendChild(item);
    });
}

function setupNavigation() {
    const navLinks = document.querySelectorAll(".nav-link");
    const tabContents = document.querySelectorAll(".tab-content");

    navLinks.forEach((link) => {
        link.addEventListener("click", () => {
            const target = link.getAttribute("data-target");

            navLinks.forEach((item) => item.classList.remove("active"));
            tabContents.forEach((item) => item.classList.remove("active"));

            link.classList.add("active");
            document.getElementById(target).classList.add("active");
        });
    });
}

function setupJumpLinks() {
    document.querySelectorAll(".jump-link").forEach((button) => {
        button.addEventListener("click", () => {
            const target = button.getAttribute("data-target");
            const navMatch = document.querySelector(`.nav-link[data-target="${target}"]`);
            if (navMatch) {
                navMatch.click();
            }
        });
    });
}

function setupModal() {
    const modal = document.getElementById("feedback-modal");
    const closeButton = document.querySelector(".close-modal");

    closeButton.addEventListener("click", hideFeedback);
    modal.addEventListener("click", (event) => {
        if (event.target.dataset.closeModal === "true") {
            hideFeedback();
        }
    });

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") {
            hideFeedback();
        }
    });
}

function showFeedback(pr) {
    const modal = document.getElementById("feedback-modal");
    const body = document.getElementById("modal-feedback-body");
    const meta = document.getElementById("modal-pr-meta");
    const issues = normalizeFeedback(pr && pr.feedback);

    body.innerHTML = "";
    meta.textContent = pr
        ? `${pr.repo || "Repository"} | ${pr.author || "Unknown author"} | ${issues.length} findings`
        : "No pull request selected";

    if (!pr || issues.length === 0) {
        body.innerHTML = `
            <div class="feedback-item empty">
                <p class="feedback-comment">No feedback is available for this pull request yet.</p>
            </div>
        `;
    } else {
        issues.forEach((issue) => {
            const severity = normalizeSeverity(issue.severity);
            const item = document.createElement("article");
            item.className = `feedback-item ${severity.toLowerCase()}`;
            item.innerHTML = `
                <div class="feedback-meta">
                    <span class="feedback-severity ${findingClass(severity)}">${severity}</span>
                    <span class="feedback-line">Line ${issue.line || "N/A"}</span>
                </div>
                <p class="feedback-comment">${escapeHtml(issue.comment || "No comment provided.")}</p>
                <p class="feedback-fix">Suggested fix: <code>${escapeHtml(issue.fix_suggestion || "No fix suggestion provided.")}</code></p>
            `;
            body.appendChild(item);
        });
    }

    modal.classList.add("is-open");
    modal.setAttribute("aria-hidden", "false");
}

function hideFeedback() {
    const modal = document.getElementById("feedback-modal");
    modal.classList.remove("is-open");
    modal.setAttribute("aria-hidden", "true");
}

function setupBulkScan() {
    const startScanButton = document.getElementById("start-bulk-scan-btn");
    const scanStatus = document.getElementById("scan-status");
    const githubTokenInput = document.getElementById("github-token");
    const scanFeedback = document.getElementById("scan-feedback");

    startScanButton.addEventListener("click", async () => {
        const token = githubTokenInput.value.trim();
        if (!token) {
            setScanFeedback("Please enter a GitHub token before starting the scan.", "error");
            return;
        }

        setScanFeedback("", "");
        startScanButton.disabled = true;
        scanStatus.classList.remove("hidden");

        try {
            const response = await fetch("http://localhost:8000/api/bulk-scan", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ token })
            });

            const result = await response.json();
            if (!response.ok) {
                throw new Error(result.detail || "Bulk scan request failed.");
            }

            setScanFeedback("Bulk scan started in the background. New review results will appear in the archive as they arrive.", "success");
            githubTokenInput.value = "";
            refreshDashboard();
        } catch (error) {
            console.error("Bulk scan failed:", error);
            setScanFeedback(error.message || "Failed to connect to backend.", "error");
        } finally {
            startScanButton.disabled = false;
            scanStatus.classList.add("hidden");
        }
    });

    function setScanFeedback(message, type) {
        if (!message) {
            scanFeedback.textContent = "";
            scanFeedback.className = "scan-feedback hidden";
            return;
        }

        scanFeedback.textContent = message;
        scanFeedback.className = `scan-feedback ${type === "error" ? "is-error" : "is-success"}`;
    }
}

function updateClock() {
    const formatter = new Intl.DateTimeFormat([], {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit"
    });
    setText("current-time", formatter.format(new Date()));
}

function normalizeFeedback(feedback) {
    if (Array.isArray(feedback)) {
        return feedback;
    }
    if (feedback && Array.isArray(feedback.issues)) {
        return feedback.issues;
    }
    return [];
}

function normalizeSeverity(severity) {
    const value = (severity || "LOW").toString().toUpperCase();
    if (["LOW", "MEDIUM", "CRITICAL"].includes(value)) {
        return value;
    }
    return "LOW";
}

function getDominantSeverity(issues) {
    if (!issues.length) {
        return "LOW";
    }

    return issues
        .map((issue) => normalizeSeverity(issue.severity))
        .sort((a, b) => severityWeight(b) - severityWeight(a))[0];
}

function severityWeight(severity) {
    switch (normalizeSeverity(severity)) {
        case "CRITICAL":
            return 3;
        case "MEDIUM":
            return 2;
        default:
            return 1;
    }
}

function statusClass(status) {
    const normalized = (status || "").toString().toLowerCase();
    if (normalized === "open") {
        return "status-open";
    }
    if (normalized === "closed" || normalized === "merged") {
        return "status-closed";
    }
    return "status-default";
}

function findingClass(severity) {
    switch (normalizeSeverity(severity)) {
        case "CRITICAL":
            return "finding-critical";
        case "MEDIUM":
            return "finding-medium";
        default:
            return "finding-low";
    }
}

function setText(id, value) {
    const node = document.getElementById(id);
    if (node) {
        node.textContent = value;
    }
}

function escapeHtml(value) {
    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
}
