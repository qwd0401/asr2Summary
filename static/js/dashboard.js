/**
 * MeetAssistant — Dashboard
 * Renders KPI cards, charts (Chart.js loaded separately), and table
 */
(function () {
  'use strict';

  const fmtNumber = (n) => new Intl.NumberFormat('zh-CN').format(n ?? 0);
  const fmtPct = (n) => (n == null ? '—' : `${n.toFixed(1)}%`);
  const fmtDuration = (sec) => {
    if (!sec) return '—';
    if (sec < 60) return `${sec.toFixed(1)}s`;
    const m = Math.floor(sec / 60);
    const s = Math.round(sec % 60);
    return `${m}m ${s}s`;
  };

  async function fetchJSON(url) {
    try {
      const r = await fetch(url);
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      return await r.json();
    } catch (e) {
      console.error('Fetch failed:', url, e);
      return null;
    }
  }

  function setKPI(id, value, label) {
    const el = document.querySelector(id);
    if (!el) return;
    el.textContent = value;
    if (label) el.setAttribute('aria-label', label);
  }

  function removeSkeleton(containerId) {
    const skeleton = document.getElementById(containerId);
    if (skeleton) {
      skeleton.style.opacity = '0';
      setTimeout(() => skeleton.remove(), 300);
    }
  }

  async function loadOverview() {
    const data = await fetchJSON('/api/stats/overview');
    if (!data || !data.data) return;
    const d = data.data;
    setKPI('#kpi-total', fmtNumber(d.total_requests), `总请求数 ${fmtNumber(d.total_requests)}`);
    setKPI('#kpi-success-rate', fmtPct(d.success_rate), `成功率 ${fmtPct(d.success_rate)}`);
    setKPI(
      '#kpi-avg-time',
      fmtDuration(d.avg_processing_time),
      `平均耗时 ${fmtDuration(d.avg_processing_time)}`
    );
    setKPI(
      '#kpi-total-size',
      fmtSize(d.total_file_size),
      `总处理大小 ${fmtSize(d.total_file_size)}`
    );
  }

  function fmtSize(bytes) {
    if (!bytes) return '0 B';
    const units = ['B', 'KB', 'MB', 'GB'];
    let i = 0;
    let n = bytes;
    while (n >= 1024 && i < units.length - 1) {
      n /= 1024;
      i++;
    }
    return `${n.toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
  }

  async function loadUsageChart() {
    const data = await fetchJSON('/api/stats/usage');
    if (!data || !data.data) return;
    const days = data.data;
    const labels = days.map((d) => d.date.slice(5)).reverse();
    const totals = days.map((d) => d.total_requests || d.requests || 0).reverse();
    const success = days.map((d) => d.successful_requests || d.success || 0).reverse();

    // 移除骨架屏
    removeSkeleton('usageChartSkeleton');

    const el = document.getElementById('usageChart');
    if (!el || typeof Chart === 'undefined') return;

    // 检查是否有数据
    const hasData = totals.some(t => t > 0);
    if (!hasData) {
      el.parentElement.innerHTML = '<div style="display:flex;align-items:center;justify-content:center;height:100%;color:var(--color-text-muted);"><span data-lucide="bar-chart-3" style="margin-right:8px;"></span>暂无数据</div>';
      if (window.appIcons) window.appIcons.render();
      return;
    }

    new Chart(el, {
      type: 'line',
      data: {
        labels,
        datasets: [
          {
            label: '总请求',
            data: totals,
            borderColor: '#0D9488',
            backgroundColor: 'rgba(13, 148, 136, 0.12)',
            fill: true,
            tension: 0.35,
            pointRadius: 3,
            pointHoverRadius: 6,
            borderWidth: 2,
          },
          {
            label: '成功',
            data: success,
            borderColor: '#10B981',
            backgroundColor: 'transparent',
            borderDash: [4, 4],
            tension: 0.35,
            pointRadius: 2,
            borderWidth: 2,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: 'bottom', labels: { boxWidth: 12, padding: 12 } },
          tooltip: { intersect: false, mode: 'index' },
        },
        scales: {
          y: {
            beginAtZero: true,
            grid: { color: 'rgba(148, 163, 184, 0.15)' },
            ticks: { precision: 0 },
          },
          x: { grid: { display: false } },
        },
      },
    });
  }

  async function loadEndpointChart() {
    const data = await fetchJSON('/stats');
    if (!data || !data.endpoint_statistics) return;
    const list = (data.endpoint_statistics || []).slice(0, 6);
    const labels = list.map((e) => e.endpoint);
    const counts = list.map((e) => e.total_requests);

    // 移除骨架屏
    removeSkeleton('endpointChartSkeleton');

    const el = document.getElementById('endpointChart');
    if (!el || typeof Chart === 'undefined') return;

    // 检查是否有数据
    const hasData = counts.some(c => c > 0);
    if (!hasData) {
      el.parentElement.innerHTML = '<div style="display:flex;align-items:center;justify-content:center;height:100%;color:var(--color-text-muted);"><span data-lucide="pie-chart" style="margin-right:8px;"></span>暂无数据</div>';
      if (window.appIcons) window.appIcons.render();
      return;
    }

    new Chart(el, {
      type: 'doughnut',
      data: {
        labels,
        datasets: [
          {
            data: counts,
            backgroundColor: ['#0D9488', '#14B8A6', '#3B82F6', '#F59E0B', '#EA580C', '#8B5CF6'],
            borderWidth: 0,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '60%',
        plugins: {
          legend: { position: 'bottom', labels: { boxWidth: 12, padding: 10, font: { size: 11 } } },
          tooltip: {
            callbacks: {
              label: (ctx) => {
                const total = counts.reduce((a, b) => a + b, 0);
                const pct = total ? ((ctx.parsed / total) * 100).toFixed(1) : 0;
                return `${ctx.label}: ${ctx.parsed} (${pct}%)`;
              },
            },
          },
        },
      },
    });
  }

  const pagination = {
    page: 1,
    pageSize: 10,
    total: 0,
    totalPages: 0,
    loading: false,
  };

  async function loadUsageTable(opts = {}) {
    const tbody = document.querySelector('#usageTable tbody');
    if (!tbody) return;
    if (opts.page) pagination.page = opts.page;
    if (opts.pageSize) pagination.pageSize = opts.pageSize;

    const params = new URLSearchParams({
      page: pagination.page,
      page_size: pagination.pageSize,
    });
    const successFilter = document.getElementById('filter-success');
    if (successFilter && successFilter.value !== 'all') {
      params.set('success', successFilter.value);
    }

    pagination.loading = true;
    tbody.innerHTML = `<tr><td colspan="5" style="text-align:center;color:var(--color-text-muted);padding:var(--space-6);"><span class="spinner" aria-hidden="true"></span><span class="sr-only">加载中</span></td></tr>`;

    try {
      const r = await fetch(`/api/stats/usage-table?${params.toString()}`);
      const data = await r.json();
      if (!data.success) throw new Error('API returned failure');
      pagination.total = data.pagination?.total ?? 0;
      pagination.totalPages = data.pagination?.total_pages ?? 0;

      if (!data.data || data.data.length === 0) {
        tbody.innerHTML = `<tr><td colspan="5" style="text-align:center;color:var(--color-text-muted);padding:var(--space-8);">暂无活动记录</td></tr>`;
        renderPagination();
        return;
      }

      tbody.innerHTML = data.data
        .map(
          (row) => `
        <tr>
          <td><code class="text-xs">${row.request_id || '—'}</code></td>
          <td><span class="badge">${row.endpoint || '—'}</span></td>
          <td>${row.file_type ? `<span class="badge">.${row.file_type}</span>` : '—'}</td>
          <td class="num">${row.success ? '<span class="badge badge-success">成功</span>' : '<span class="badge badge-error">失败</span>'}</td>
          <td class="num">${(row.processing_time ?? 0).toFixed(2)}s</td>
        </tr>`
        )
        .join('');
      renderPagination();
    } catch (e) {
      tbody.innerHTML = `<tr><td colspan="5"><div class="alert alert-error" style="margin:var(--space-4);">加载失败：${e.message}</div></td></tr>`;
    } finally {
      pagination.loading = false;
    }
  }

  function renderPagination() {
    const wrap = document.getElementById('tablePagination');
    if (!wrap) return;
    const start = pagination.total === 0 ? 0 : (pagination.page - 1) * pagination.pageSize + 1;
    const end = Math.min(pagination.page * pagination.pageSize, pagination.total);
    wrap.innerHTML = `
      <div class="cluster" style="justify-content:space-between;flex-wrap:wrap;gap:var(--space-3);">
        <span class="text-xs text-muted">
          第 ${start}–${end} 条 / 共 ${pagination.total} 条
        </span>
        <div class="cluster" style="gap:var(--space-2);">
          <button type="button" class="btn btn-ghost" data-page="prev" ${pagination.page <= 1 ? 'disabled' : ''}>
            <span data-lucide="arrow-right" data-size="16" style="transform:rotate(180deg);" class="icon"></span>
            上一页
          </button>
          <span class="text-sm" style="padding: 0 var(--space-2);">
            ${pagination.page} / ${Math.max(pagination.totalPages, 1)}
          </span>
          <button type="button" class="btn btn-ghost" data-page="next" ${pagination.page >= pagination.totalPages ? 'disabled' : ''}>
            下一页
            <span data-lucide="arrow-right" data-size="16" class="icon"></span>
          </button>
        </div>
      </div>
    `;
    if (window.appIcons) window.appIcons.render(wrap);
  }

  document.addEventListener('DOMContentLoaded', () => {
    loadOverview();
    loadUsageChart();
    loadEndpointChart();
    loadUsageTable();

    // Pagination click delegation
    const paginationEl = document.getElementById('tablePagination');
    if (paginationEl) {
      paginationEl.addEventListener('click', (e) => {
        const btn = e.target.closest('[data-page]');
        if (!btn || btn.disabled) return;
        const dir = btn.dataset.page;
        if (dir === 'prev' && pagination.page > 1) {
          loadUsageTable({ page: pagination.page - 1 });
        } else if (dir === 'next' && pagination.page < pagination.totalPages) {
          loadUsageTable({ page: pagination.page + 1 });
        }
      });
    }

    // Filter change
    const filter = document.getElementById('filter-success');
    if (filter) {
      filter.addEventListener('change', () => loadUsageTable({ page: 1 }));
    }
  });
})();
