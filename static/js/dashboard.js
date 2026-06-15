/**
 * Dashboard charts.
 *
 * Fetches the aggregated summary from the REST API (GET /api/dashboard) and
 * renders four Chart.js visualizations. Keeping the data in the API (rather
 * than inlining it in the template) means the same numbers power both the UI
 * and any external API consumer.
 */
(function () {
  "use strict";

  const STATUS_LABELS = {
    PENDING: "Pendiente",
    APPROVED: "Aprobado",
    PAID: "Pagado",
    CANCELLED: "Cancelado",
  };
  const STATUS_COLORS = {
    PENDING: "#ffc107",
    APPROVED: "#0dcaf0",
    PAID: "#198754",
    CANCELLED: "#6c757d",
  };

  async function loadDashboard() {
    const res = await fetch("/api/dashboard", { headers: { Accept: "application/json" } });
    if (!res.ok) {
      console.error("No se pudo cargar el dashboard:", res.status);
      return;
    }
    const data = await res.json();
    renderByMonth(data.charts);
    renderStatusDoughnut("chartExpenseStatus", data.charts.expenses_by_status);
    renderStatusBar("chartPaymentStatus", data.charts.payments_by_status);
    renderByAccount(data.charts.consumption_by_account);
  }

  function renderByMonth(charts) {
    const labels = charts.expenses_by_month.map((r) => r[0]);
    new Chart(document.getElementById("chartByMonth"), {
      type: "bar",
      data: {
        labels: labels,
        datasets: [
          {
            label: "Gastos",
            data: charts.expenses_by_month.map((r) => r[1]),
            backgroundColor: "rgba(13,110,253,.6)",
          },
          {
            label: "Pagos",
            data: charts.payments_by_month.map((r) => r[1]),
            backgroundColor: "rgba(25,135,84,.6)",
          },
        ],
      },
      options: { responsive: true, scales: { y: { beginAtZero: true } } },
    });
  }

  function renderStatusDoughnut(canvasId, statusMap) {
    const keys = Object.keys(statusMap);
    new Chart(document.getElementById(canvasId), {
      type: "doughnut",
      data: {
        labels: keys.map((k) => STATUS_LABELS[k] || k),
        datasets: [
          {
            data: keys.map((k) => statusMap[k]),
            backgroundColor: keys.map((k) => STATUS_COLORS[k] || "#adb5bd"),
          },
        ],
      },
      options: { responsive: true, plugins: { legend: { position: "bottom" } } },
    });
  }

  function renderStatusBar(canvasId, statusMap) {
    const keys = Object.keys(statusMap);
    new Chart(document.getElementById(canvasId), {
      type: "bar",
      data: {
        labels: keys.map((k) => STATUS_LABELS[k] || k),
        datasets: [
          {
            label: "Pagos",
            data: keys.map((k) => statusMap[k]),
            backgroundColor: keys.map((k) => STATUS_COLORS[k] || "#adb5bd"),
          },
        ],
      },
      options: {
        responsive: true,
        plugins: { legend: { display: false } },
        scales: { y: { beginAtZero: true, ticks: { precision: 0 } } },
      },
    });
  }

  function renderByAccount(rows) {
    new Chart(document.getElementById("chartByAccount"), {
      type: "bar",
      data: {
        labels: rows.map((r) => r.account_name),
        datasets: [
          {
            label: "Consumo (Pagado)",
            data: rows.map((r) => r.total),
            backgroundColor: "rgba(108,117,125,.7)",
          },
        ],
      },
      options: {
        indexAxis: "y",
        responsive: true,
        plugins: { legend: { display: false } },
        scales: { x: { beginAtZero: true } },
      },
    });
  }

  document.addEventListener("DOMContentLoaded", loadDashboard);
})();
