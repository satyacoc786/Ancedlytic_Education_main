(() => {
  'use strict';

  /* =========================================================
     1. AUTHENTICATION & STATE MANAGEMENT
     ========================================================= */
  const token = localStorage.getItem('acadivance_token') || sessionStorage.getItem('acadivance_token');
  const userJson = localStorage.getItem('acadivance_user') || sessionStorage.getItem('acadivance_user');

  let currentUser = null;
  try { currentUser = JSON.parse(userJson); } catch (e) { currentUser = null; }

  // If unauthenticated, redirect back to login
  if (!token && !currentUser) {
    window.location.replace('index.html');
    return;
  }

  // Populate user profile in topbar
  if (currentUser) {
    const nameEl = document.getElementById('user-name');
    const roleEl = document.getElementById('user-role');
    const avatarEl = document.getElementById('user-avatar');
    const greetingEl = document.getElementById('greeting-title');

    if (nameEl) nameEl.textContent = currentUser.name || currentUser.username || 'Staff User';
    if (roleEl) roleEl.textContent = (currentUser.role || 'Administrator').toUpperCase();
    if (avatarEl) avatarEl.textContent = (currentUser.name || currentUser.username || 'ST').substring(0, 2).toUpperCase();
    if (greetingEl) greetingEl.textContent = `Welcome back, ${currentUser.name || 'Staff User'}!`;
  }

  const dashboardDate = document.getElementById('dashboard-date');
  if (dashboardDate) {
    dashboardDate.textContent = new Intl.DateTimeFormat(undefined, {
      weekday: 'long',
      day: 'numeric',
      month: 'long',
      year: 'numeric'
    }).format(new Date());
  }

  // API Request Helper with Bearer Authorization
  async function apiFetch(endpoint, options = {}) {
    const headers = options.headers || {};
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    options.headers = headers;
    try {
      const res = await fetch(endpoint, options);
      if (res.status === 401) {
        // Token expired
        localStorage.removeItem('acadivance_token');
        window.location.replace('index.html');
        return null;
      }
      return res;
    } catch (err) {
      console.error('API Fetch Error:', err);
      showToast('Network error: unable to reach server', 'error');
      return null;
    }
  }

  // Toast Notification System
  function showToast(msg, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.innerHTML = `<span>${type === 'error' ? '⚠️' : '✓'}</span><span>${msg}</span>`;
    container.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = '0';
      setTimeout(() => toast.remove(), 300);
    }, 3200);
  }

  /* =========================================================
     2. NAVIGATION & ROUTING
     ========================================================= */
  const navItems = document.querySelectorAll('.nav__item[data-view]');
  const viewPanels = document.querySelectorAll('.view-panel');

  function switchView(viewName) {
    navItems.forEach((btn) => {
      btn.classList.toggle('is-active', btn.dataset.view === viewName);
    });

    viewPanels.forEach((panel) => {
      const isActive = panel.id === `view-${viewName}`;
      panel.classList.toggle('is-active', isActive);
    });

    window.location.hash = viewName;

    // Load data for newly active view
    if (viewName === 'dashboard') loadDashboard();
    else if (viewName === 'students') loadStudentsExplorer();
    else if (viewName === 'risks') loadRisks();
    else if (viewName === 'placements') loadPlacementAnalytics();
    else if (viewName === 'interventions') loadInterventions();
    else if (viewName === 'settings') loadSettings();
  }

  navItems.forEach((btn) => {
    btn.addEventListener('click', () => switchView(btn.dataset.view));
  });

  // Handle in-page jumps
  document.querySelectorAll('[data-jump]').forEach((el) => {
    el.addEventListener('click', (e) => {
      e.preventDefault();
      const target = el.dataset.jump;
      if (el.dataset.filter && target === 'students') {
        const riskSelect = document.getElementById('explorer-risk');
        if (riskSelect) riskSelect.value = el.dataset.filter;
      }
      switchView(target);
    });
  });

  // Logout button
  document.getElementById('logout-btn')?.addEventListener('click', () => {
    localStorage.removeItem('acadivance_token');
    localStorage.removeItem('acadivance_user');
    localStorage.removeItem('sp_session');
    sessionStorage.clear();
    window.location.replace('index.html');
  });

  // Theme toggle
  const themeToggle = document.getElementById('theme-toggle');
  const savedTheme = localStorage.getItem('acadivance_theme') || 'light';
  document.documentElement.setAttribute('data-theme', savedTheme);

  themeToggle?.addEventListener('click', () => {
    const current = document.documentElement.getAttribute('data-theme');
    const next = current === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('acadivance_theme', next);
  });

  // Global search input
  const globalSearch = document.getElementById('global-search');
  globalSearch?.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      const q = globalSearch.value.trim();
      const explorerSearch = document.getElementById('explorer-search');
      if (explorerSearch) explorerSearch.value = q;
      switchView('students');
      loadStudentsExplorer();
    }
  });

    /* =========================================================
      3. DASHBOARD METRICS
      ========================================================= */
  let riskChartInstance = null;

  async function loadDashboard() {
    const res = await apiFetch('/api/dashboard/summary');
    if (!res || !res.ok) return;
    const data = await res.json();

    // 1. KPI Cards
    const kpiTotal = document.getElementById('kpi-total-students');
    const kpiAvg = document.getElementById('kpi-avg-score');
    const kpiRisk = document.getElementById('kpi-at-risk');
    const kpiRiskSub = document.getElementById('kpi-at-risk-sub');
    const kpiPlc = document.getElementById('kpi-placement-ready');
    const kpiPlcSub = document.getElementById('kpi-placement-ready-sub');

    if (kpiTotal) kpiTotal.textContent = data.total_students;
    if (kpiAvg) kpiAvg.textContent = data.avg_success_score;
    if (kpiRisk) kpiRisk.textContent = data.at_risk_count;
    if (kpiRiskSub) kpiRiskSub.textContent = `${data.at_risk_percent}% of total students`;
    if (kpiPlc) kpiPlc.textContent = data.placement_ready_count;
    if (kpiPlcSub) kpiPlcSub.textContent = `${data.placement_ready_percent}% of total students`;

    // 2. Risk Donut Chart
    renderRiskChart(data.risk_distribution);

    // 3. Students by Department
    renderDepartmentBars(data.dept_counts);

    // 4. Students Needing Support Table
    renderNeedingReviewTable(data.needing_review);

    // 5. Recent Support Plans Table
    renderRecentInterventionsTable(data.recent_interventions);
  }

  const teacherAiForm = document.getElementById('teacher-ai-form');
  const teacherAiQuestion = document.getElementById('teacher-ai-question');
  const teacherAiAnswer = document.getElementById('teacher-ai-answer');
  const teacherAiSubmit = document.getElementById('teacher-ai-submit');

  async function askTeacherAi(question) {
    if (!question || !teacherAiAnswer || !teacherAiSubmit) return;
    teacherAiSubmit.disabled = true;
    teacherAiAnswer.textContent = 'Reviewing current cohort data...';

    try {
      const res = await apiFetch('/api/dashboard/coach', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question })
      });
      if (!res) return;
      const data = await res.json();
      if (!res.ok) {
        teacherAiAnswer.textContent = data.detail || 'The assistant could not answer right now.';
        return;
      }
      teacherAiAnswer.textContent = data.answer;
    } catch (error) {
      teacherAiAnswer.textContent = 'Unable to get cohort guidance right now. Please try again.';
    } finally {
      teacherAiSubmit.disabled = false;
    }
  }

  teacherAiForm?.addEventListener('submit', (event) => {
    event.preventDefault();
    askTeacherAi(teacherAiQuestion?.value.trim());
  });

  document.querySelectorAll('[data-ai-prompt]').forEach((button) => {
    button.addEventListener('click', () => {
      if (!teacherAiQuestion) return;
      teacherAiQuestion.value = button.dataset.aiPrompt || '';
      teacherAiQuestion.focus();
    });
  });

  function renderRiskChart(riskDist) {
    const ctx = document.getElementById('riskChart')?.getContext('2d');
    if (!ctx) return;
    if (riskChartInstance) riskChartInstance.destroy();

    const centerNum = document.getElementById('donut-center-num');
    if (centerNum) centerNum.textContent = riskDist.total_at_risk;

    const acadVal = document.getElementById('legend-acad-val');
    const plcVal = document.getElementById('legend-plc-val');
    const bothVal = document.getElementById('legend-both-val');

    if (acadVal) acadVal.textContent = `${riskDist.academic} (${riskDist.academic_percent}%)`;
    if (plcVal) plcVal.textContent = `${riskDist.placement} (${riskDist.placement_percent}%)`;
    if (bothVal) bothVal.textContent = `${riskDist.both} (${riskDist.both_percent}%)`;

    riskChartInstance = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: ['Academic Risk', 'Placement Risk', 'Both Risks'],
        datasets: [{
          data: [riskDist.academic, riskDist.placement, riskDist.both],
          backgroundColor: ['#ef4444', '#f97316', '#8b5cf6'],
          borderWidth: 2,
          borderColor: '#ffffff',
          hoverOffset: 4
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '72%',
        plugins: {
          legend: { display: false }
        }
      }
    });
  }

  function renderDepartmentBars(deptCounts) {
    const container = document.getElementById('dept-bars-container');
    if (!container) return;

    const colors = {
      'Computer Science': '#0d9488',
      'Electronics': '#3b82f6',
      'Mechanical': '#8b5cf6',
      'Civil': '#f97316',
      'Business': '#eab308',
      'Biotech': '#ec4899',
      'Others': '#64748b'
    };

    const maxCount = Math.max(...Object.values(deptCounts), 1);

    container.innerHTML = Object.entries(deptCounts).map(([dept, count]) => {
      const pct = Math.round((count / maxCount) * 100);
      const color = colors[dept] || '#0d9488';
      return `
        <div class="dept-bar-row">
          <span class="dept-name" title="${dept}">${dept}</span>
          <div class="dept-track">
            <div class="dept-fill" style="width: ${pct}%; background-color: ${color};"></div>
          </div>
          <span class="dept-count">${count}</span>
        </div>
      `;
    }).join('');
  }

  function renderNeedingReviewTable(students) {
    const tbody = document.getElementById('needing-review-tbody');
    if (!tbody) return;

    if (!students || students.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--text-muted); padding: 24px;">No students requiring immediate review.</td></tr>`;
      return;
    }

    tbody.innerHTML = students.slice(0, 5).map((s) => {
      const scoreClass = s.success_score >= 75 ? 'score-pill--good' : s.success_score >= 50 ? 'score-pill--warn' : 'score-pill--bad';
      const flagsHtml = s.risk_flags.map((f) => {
        const cls = f === 'Academic' ? 'badge--red' : 'badge--orange';
        const label = f === 'Academic' ? 'Academic support' : 'Career preparation';
        return `<span class="badge ${cls}">${label}</span>`;
      }).join(' ');

      return `
        <tr>
          <td><b>${s.name}</b></td>
          <td style="color: var(--text-muted); font-family: monospace;">${s.id}</td>
          <td>${s.department}</td>
          <td><span class="score-pill ${scoreClass}">${s.success_score}</span></td>
          <td>${flagsHtml}</td>
          <td style="color: var(--text-muted); font-size: 0.8rem;">${s.last_activity}</td>
          <td><button class="btn-sm" onclick="window.viewStudentProfile('${s.id}')">View</button></td>
        </tr>
      `;
    }).join('');
  }

  function renderRecentInterventionsTable(items) {
    const tbody = document.getElementById('recent-interventions-tbody');
    if (!tbody) return;

    if (!items || items.length === 0) {
      tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: var(--text-muted); padding: 18px;">No recent interventions recorded.</td></tr>`;
      return;
    }

    tbody.innerHTML = items.map((i) => {
      const statusCls = i.status === 'Completed' ? 'badge--green' :
                        i.status === 'In Progress' ? 'badge--blue' :
                        i.status === 'Scheduled' ? 'badge--purple' : 'badge--orange';
      return `
        <tr>
          <td><b>${i.student_name || i.student_id}</b></td>
          <td style="font-size: 0.82rem;">${i.issue}</td>
          <td style="color: var(--text-muted); font-size: 0.8rem;">${i.assigned_to}</td>
          <td><span class="badge ${statusCls}">${i.status}</span></td>
          <td style="color: var(--text-muted); font-size: 0.8rem;">${i.due_date}</td>
        </tr>
      `;
    }).join('');
  }

  /* =========================================================
     4. STUDENT EXPLORER VIEW & PAGINATION
     ========================================================= */
  let explorerCurrentPage = 1;

  async function loadStudentsExplorer() {
    const searchVal = document.getElementById('explorer-search')?.value || '';
    const deptVal = document.getElementById('explorer-dept')?.value || 'All';
    const riskVal = document.getElementById('explorer-risk')?.value || 'all';
    const sortVal = document.getElementById('explorer-sort')?.value || 'score';

    const params = new URLSearchParams({
      page: explorerCurrentPage,
      page_size: 15,
      sort_by: sortVal,
      sort_order: sortVal === 'name' ? 'asc' : 'desc'
    });
    if (searchVal) params.append('q', searchVal);
    if (deptVal !== 'All') params.append('department', deptVal);
    if (riskVal !== 'all') params.append('risk_type', riskVal);

    const res = await apiFetch(`/api/students?${params.toString()}`);
    if (!res || !res.ok) return;
    const data = await res.json();

    const tbody = document.getElementById('explorer-table-body');
    if (!tbody) return;

    if (data.items.length === 0) {
      tbody.innerHTML = `<tr><td colspan="9" style="text-align: center; color: var(--text-muted); padding: 32px;">No students match the selected filters.</td></tr>`;
      return;
    }

    tbody.innerHTML = data.items.map((s) => {
      const scoreClass = s.success_score >= 75 ? 'score-pill--good' : s.success_score >= 50 ? 'score-pill--warn' : 'score-pill--bad';
      const flagsHtml = s.risk_flags.length > 0 ? s.risk_flags.map((f) => {
        const cls = f === 'Academic' ? 'badge--red' : 'badge--orange';
        return `<span class="badge ${cls}">${f}</span>`;
      }).join(' ') : `<span class="badge badge--green">On Track</span>`;

      return `
        <tr>
          <td style="font-family: monospace; font-weight: 600;">${s.id}</td>
          <td><b>${s.name}</b></td>
          <td>${s.department}</td>
          <td>Sem ${s.semester}</td>
          <td>${s.cgpa.toFixed(2)}</td>
          <td>${s.attendance_pct.toFixed(1)}%</td>
          <td><span class="score-pill ${scoreClass}">${s.success_score}</span></td>
          <td>${flagsHtml}</td>
          <td><button class="btn-sm" onclick="window.viewStudentProfile('${s.id}')">View Profile</button></td>
        </tr>
      `;
    }).join('');

    // Pagination label & button state
    const info = document.getElementById('pagination-info');
    if (info) {
      const start = (data.page - 1) * data.page_size + 1;
      const end = Math.min(data.page * data.page_size, data.total);
      info.textContent = `Showing ${start} to ${end} of ${data.total} students`;
    }

    const prevBtn = document.getElementById('prev-page-btn');
    const nextBtn = document.getElementById('next-page-btn');
    if (prevBtn) prevBtn.disabled = data.page <= 1;
    if (nextBtn) nextBtn.disabled = data.page >= data.total_pages;
  }

  document.getElementById('explorer-search')?.addEventListener('input', () => {
    explorerCurrentPage = 1;
    loadStudentsExplorer();
  });
  document.getElementById('explorer-dept')?.addEventListener('change', () => {
    explorerCurrentPage = 1;
    loadStudentsExplorer();
  });
  document.getElementById('explorer-risk')?.addEventListener('change', () => {
    explorerCurrentPage = 1;
    loadStudentsExplorer();
  });
  document.getElementById('explorer-sort')?.addEventListener('change', () => {
    explorerCurrentPage = 1;
    loadStudentsExplorer();
  });

  document.getElementById('prev-page-btn')?.addEventListener('click', () => {
    if (explorerCurrentPage > 1) {
      explorerCurrentPage--;
      loadStudentsExplorer();
    }
  });

  document.getElementById('next-page-btn')?.addEventListener('click', () => {
    explorerCurrentPage++;
    loadStudentsExplorer();
  });

  document.getElementById('explorer-export-btn')?.addEventListener('click', () => {
    const dept = document.getElementById('explorer-dept')?.value || 'All';
    const risk = document.getElementById('explorer-risk')?.value || 'all';
    window.location.href = `/api/reports/export.csv?department=${encodeURIComponent(dept)}&risk_filter=${encodeURIComponent(risk)}`;
  });

  /* =========================================================
     5. STUDENT DETAILED PROFILE MODAL & EXPLAINABILITY
     ========================================================= */
  window.viewStudentProfile = async function (studentId) {
    const res = await apiFetch(`/api/students/${studentId}`);
    if (!res || !res.ok) return;
    const s = await res.json();

    const modal = document.getElementById('student-modal');
    const title = document.getElementById('m-student-name');
    const sub = document.getElementById('m-student-sub');
    const body = document.getElementById('m-student-body');

    if (title) title.textContent = s.name;
    if (sub) sub.textContent = `ID: ${s.id} · ${s.department} · Semester ${s.semester} (${s.academic_year})`;

    const sc = s.score_analysis;
    const rk = s.risk_analysis;

    // Build Component Cards & Factor Contributions
    const componentsHtml = Object.entries(sc.components).map(([k, c]) => `
      <div style="background: var(--surface-bg); padding: 12px 14px; border-radius: var(--radius-md); border: 1px solid var(--border-color);">
        <div style="display: flex; justify-content: space-between; font-size: 0.8rem; font-weight: 600; margin-bottom: 4px;">
          <span>${k.toUpperCase()} (Weight ${Math.round(c.weight * 100)}%)</span>
          <b>${c.normalized_score} / 100</b>
        </div>
        <div style="height: 6px; background: var(--navy-100); border-radius: 999px; overflow: hidden; margin-bottom: 6px;">
          <div style="width: ${c.normalized_score}%; height: 100%; background: var(--teal-600); border-radius: 999px;"></div>
        </div>
        <p style="font-size: 0.74rem; color: var(--text-muted);">${c.description}</p>
        <p style="font-size: 0.72rem; color: var(--teal-700); font-weight: 600; margin-top: 2px;">Contribution: +${c.weighted_contribution} pts</p>
      </div>
    `).join('');

    // Positive & Negative Factors
    const posFactorsHtml = sc.positive_factors.map((f) => `<li style="color: var(--accent-green); font-size: 0.8rem;">✓ ${f}</li>`).join('');
    const negFactorsHtml = sc.negative_factors.map((f) => `<li style="color: var(--accent-red); font-size: 0.8rem;">⚠️ ${f}</li>`).join('');
    const actionsHtml = sc.recommended_actions.map((a) => `<li style="color: var(--teal-800); font-size: 0.8rem;">→ ${a}</li>`).join('');

    // Risk Indicators
    const allIndicators = [...rk.academic_indicators, ...rk.placement_indicators];
    const riskIndicatorsHtml = allIndicators.length > 0 ? allIndicators.map((ind) => `
      <div style="padding: 10px 14px; background: #fff5f5; border-left: 4px solid #ef4444; border-radius: 4px; margin-bottom: 8px;">
        <div style="display: flex; justify-content: space-between; align-items: baseline;">
          <b style="font-size: 0.84rem; color: #991b1b;">${ind.rule_name}</b>
          <span class="badge ${ind.severity === 'High' ? 'badge--red' : 'badge--orange'}">${ind.severity} Severity</span>
        </div>
        <p style="font-size: 0.78rem; color: #4b5563; margin-top: 2px;">${ind.reason}</p>
        <p style="font-size: 0.75rem; color: #1e3a8a; margin-top: 4px;"><b>Action:</b> ${ind.recommended_action}</p>
      </div>
    `).join('') : `<p style="font-size: 0.82rem; color: var(--accent-green);">No active risk flags triggered for this student.</p>`;

    // Active Interventions
    const intHtml = s.interventions.length > 0 ? s.interventions.map((i) => `
      <div style="padding: 10px 14px; background: var(--surface-bg); border-radius: var(--radius-md); border: 1px solid var(--border-color); margin-bottom: 8px;">
        <div style="display: flex; justify-content: space-between;">
          <b style="font-size: 0.85rem;">${i.title}</b>
          <span class="badge badge--blue">${i.status}</span>
        </div>
        <p style="font-size: 0.78rem; color: var(--text-muted); margin-top: 2px;">Assigned to: ${i.assigned_to} · Due: ${i.due_date}</p>
        <p style="font-size: 0.8rem; margin-top: 4px;">${i.action_plan}</p>
      </div>
    `).join('') : `<p style="font-size: 0.82rem; color: var(--text-muted);">No existing interventions for this student.</p>`;

    body.innerHTML = `
      <!-- Score Overview Header -->
      <div style="display: flex; gap: 20px; align-items: center; padding: 16px; background: var(--teal-50); border-radius: var(--radius-lg); margin-bottom: 20px; border: 1px solid var(--teal-100);">
        <div style="text-align: center; min-width: 100px;">
          <span style="font-size: 2.2rem; font-weight: 800; color: var(--teal-900);">${sc.overall_score}</span>
          <span style="font-size: 0.8rem; color: var(--text-muted);">/ 100</span>
          <div style="margin-top: 4px;"><span class="badge ${sc.band === 'On Track' ? 'badge--green' : sc.band === 'Needs Attention' ? 'badge--orange' : 'badge--red'}">${sc.band}</span></div>
        </div>
        <div style="flex: 1;">
          <h4 style="font-size: 0.92rem; font-weight: 700; color: var(--teal-950);">Explainable Success Score (Deterministic Formula)</h4>
          <p style="font-size: 0.78rem; color: var(--teal-800); margin-top: 2px;">Data completeness: <b>${sc.data_completeness_percent}%</b>. Missing components are re-weighted without artificial penalties.</p>
          <div style="display: flex; gap: 14px; margin-top: 8px; font-size: 0.8rem;">
            <span>CGPA: <b>${s.academic ? s.academic.cgpa : 'N/A'}</b></span>
            <span>Attendance: <b>${s.attendance ? s.attendance.percentage + '%' : 'N/A'}</b></span>
            <span>Placement Readiness: <b>${s.placement ? s.placement.readiness_score + '%' : 'N/A'}</b></span>
          </div>
        </div>
      </div>

      <!-- Component Weights Breakdown -->
      <h4 style="font-size: 0.9rem; font-weight: 700; margin-bottom: 10px;">Factor Contributions & Components</h4>
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 20px;">
        ${componentsHtml}
      </div>

      <!-- Explainability Insights -->
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 20px;">
        <div style="padding: 14px; background: var(--surface-bg); border-radius: var(--radius-md); border: 1px solid var(--border-color);">
          <h5 style="font-size: 0.82rem; font-weight: 700; margin-bottom: 6px;">Positive Factors</h5>
          <ul style="list-style: none; display: flex; flex-direction: column; gap: 4px;">${posFactorsHtml}</ul>
        </div>
        <div style="padding: 14px; background: var(--surface-bg); border-radius: var(--radius-md); border: 1px solid var(--border-color);">
          <h5 style="font-size: 0.82rem; font-weight: 700; margin-bottom: 6px;">Negative Risk Drivers</h5>
          <ul style="list-style: none; display: flex; flex-direction: column; gap: 4px;">${negFactorsHtml}</ul>
        </div>
      </div>

      <!-- Risk Analysis Rule Triggers -->
      <h4 style="font-size: 0.9rem; font-weight: 700; margin-bottom: 10px;">Rule-based Risk Triggers & Institutional Flags</h4>
      <div style="margin-bottom: 20px;">${riskIndicatorsHtml}</div>

      <!-- Active Interventions -->
      <h4 style="font-size: 0.9rem; font-weight: 700; margin-bottom: 10px;">Assigned Interventions & Remediation</h4>
      <div>${intHtml}</div>
    `;

    // Hook Create Intervention Button
    const createBtn = document.getElementById('btn-modal-create-intervention');
    if (createBtn) {
      createBtn.onclick = () => {
        modal.classList.remove('is-open');
        window.openInterventionModal({
          student_id: s.id,
          title: `Support Plan for ${s.name}`,
          issue: rk.risk_summary_badge !== 'None' ? rk.risk_summary_badge : 'Academic Mentoring',
          category: rk.academic_risk ? 'academic' : 'placement'
        });
      };
    }

    modal.classList.add('is-open');
  };

  document.getElementById('close-student-modal')?.addEventListener('click', () => {
    document.getElementById('student-modal')?.classList.remove('is-open');
  });
  document.getElementById('btn-modal-close-student')?.addEventListener('click', () => {
    document.getElementById('student-modal')?.classList.remove('is-open');
  });

  /* =========================================================
     6. AT-RISK VIEW
     ========================================================= */
  let currentRiskCategory = 'all';

  async function loadRisks() {
    const res = await apiFetch(`/api/risks?risk_category=${currentRiskCategory}`);
    if (!res || !res.ok) return;
    const data = await res.json();

    const label = document.getElementById('risk-count-badge');
    if (label) label.textContent = `${data.total_at_risk} student(s) identified with active risk flags`;

    const tbody = document.getElementById('risk-table-body');
    if (!tbody) return;

    if (data.items.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--text-muted); padding: 32px;">No at-risk students found for the current selection.</td></tr>`;
      return;
    }

    tbody.innerHTML = data.items.map((s) => {
      const catBadge = s.academic_risk && s.placement_risk ? 'badge--purple' :
                       s.academic_risk ? 'badge--red' : 'badge--orange';
      const sevBadge = s.academic_severity === 'High' || s.placement_severity === 'High' ? 'badge--red' : 'badge--orange';
      const maxSev = s.academic_severity === 'High' || s.placement_severity === 'High' ? 'High' : 'Moderate';

      const indicatorsSummary = s.indicators.map((ind) => `• <b>${ind.rule_name}</b>: ${ind.actual_value} (threshold ${ind.threshold})`).join('<br>');
      const recAction = s.indicators[0] ? s.indicators[0].recommended_action : 'Schedule faculty advisory session';

      return `
        <tr>
          <td><b>${s.name}</b><br><small style="color: var(--text-muted); font-family: monospace;">${s.id}</small></td>
          <td>${s.department}</td>
          <td><span class="badge ${catBadge}">${s.summary_badge}</span></td>
          <td><span class="badge ${sevBadge}">${maxSev}</span></td>
          <td style="font-size: 0.78rem; max-width: 300px;">${indicatorsSummary}</td>
          <td style="font-size: 0.78rem; color: var(--teal-800);">${recAction}</td>
          <td>
            <button class="btn-sm" onclick="window.openInterventionModal({ student_id: '${s.id}', title: 'Remediation for ${s.name}', issue: '${s.summary_badge}', category: '${s.academic_risk ? 'academic' : 'placement'}' })">+ Intervention</button>
          </td>
        </tr>
      `;
    }).join('');
  }

  // Risk tabs
  ['all', 'academic', 'placement', 'both'].forEach((cat) => {
    const btn = document.getElementById(`risk-tab-${cat}`);
    btn?.addEventListener('click', () => {
      ['all', 'academic', 'placement', 'both'].forEach((c) => {
        const b = document.getElementById(`risk-tab-${c}`);
        if (b) {
          b.className = c === cat ? 'btn btn--primary btn-sm' : 'btn btn--ghost btn-sm';
        }
      });
      currentRiskCategory = cat;
      loadRisks();
    });
  });

  /* =========================================================
     7. PLACEMENT INSIGHTS VIEW
     ========================================================= */
  async function loadPlacementAnalytics() {
    const res = await apiFetch('/api/placements/analytics');
    if (!res || !res.ok) return;
    const data = await res.json();

    document.getElementById('plc-kpi-ready').textContent = data.ready_count;
    document.getElementById('plc-kpi-pct').textContent = `${data.ready_percent}% of total students`;
    document.getElementById('plc-kpi-coding').textContent = data.avg_coding;
    document.getElementById('plc-kpi-apt').textContent = data.avg_aptitude;
    document.getElementById('plc-kpi-mocks').textContent = data.mock_interviews_completed;

    // Skill gaps
    const gapsContainer = document.getElementById('plc-skill-gaps-container');
    if (gapsContainer) {
      gapsContainer.innerHTML = data.skill_gaps.map((g) => `
        <div>
          <div style="display: flex; justify-content: space-between; font-size: 0.82rem; font-weight: 600; margin-bottom: 4px;">
            <span>${g.skill}</span>
            <span>Current: <b>${g.current}</b> / Target: ${g.benchmark} (Gap: <span style="color: ${g.gap > 0 ? '#ef4444' : '#10b981'};">${g.gap > 0 ? '-' + g.gap : 'None'}</span>)</span>
          </div>
          <div style="height: 8px; background: var(--navy-100); border-radius: 999px; overflow: hidden;">
            <div style="width: ${Math.min(100, g.current)}%; height: 100%; background: ${g.current >= g.benchmark ? '#10b981' : '#f97316'}; border-radius: 999px;"></div>
          </div>
        </div>
      `).join('');
    }

    // Department Readiness
    const deptContainer = document.getElementById('plc-dept-readiness-container');
    if (deptContainer) {
      deptContainer.innerHTML = Object.entries(data.dept_readiness).map(([dept, score]) => `
        <div style="display: flex; align-items: center; gap: 12px; font-size: 0.82rem;">
          <span style="width: 120px; font-weight: 600;">${dept}</span>
          <div style="flex: 1; height: 8px; background: var(--navy-100); border-radius: 999px; overflow: hidden;">
            <div style="width: ${score}%; height: 100%; background: var(--teal-600); border-radius: 999px;"></div>
          </div>
          <b style="width: 40px; text-align: right;">${score}%</b>
        </div>
      `).join('');
    }

    // Students needing support
    const tbody = document.getElementById('plc-support-tbody');
    if (tbody) {
      tbody.innerHTML = data.students_needing_support.map((s) => `
        <tr>
          <td style="font-family: monospace;">${s.id}</td>
          <td><b>${s.name}</b></td>
          <td>${s.department}</td>
          <td><span class="score-pill score-pill--warn">${s.readiness_score}%</span></td>
          <td>${s.coding_score}</td>
          <td>${s.aptitude_score}</td>
          <td>Resume ${s.resume_score}%, Mocks: ${s.mock_interviews}</td>
          <td><span class="badge badge--orange">${s.primary_gap}</span></td>
          <td>
            <button class="btn-sm" onclick="window.openInterventionModal({ student_id: '${s.id}', title: 'Placement Coaching for ${s.name}', issue: '${s.primary_gap} Deficiency', category: 'placement' })">+ Support</button>
          </td>
        </tr>
      `).join('');
    }
  }

  /* =========================================================
     8. INTERVENTION CENTER CRUD & STATUS UPDATES
     ========================================================= */
  async function loadInterventions() {
    const statusVal = document.getElementById('int-status-filter')?.value || 'All';
    const prioVal = document.getElementById('int-priority-filter')?.value || 'All';
    const catVal = document.getElementById('int-cat-filter')?.value || 'All';

    const params = new URLSearchParams();
    if (statusVal !== 'All') params.append('status', statusVal);
    if (prioVal !== 'All') params.append('priority', prioVal);
    if (catVal !== 'All') params.append('category', catVal);

    const res = await apiFetch(`/api/interventions?${params.toString()}`);
    if (!res || !res.ok) return;
    const items = await res.json();

    const countLabel = document.getElementById('int-count-label');
    if (countLabel) countLabel.textContent = `${items.length} active intervention record(s)`;

    const tbody = document.getElementById('interventions-tbody');
    if (!tbody) return;

    if (items.length === 0) {
      tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; color: var(--text-muted); padding: 32px;">No interventions found matching criteria.</td></tr>`;
      return;
    }

    tbody.innerHTML = items.map((i) => {
      const prioCls = i.priority === 'High' || i.priority === 'Urgent' ? 'badge--red' :
                      i.priority === 'Medium' ? 'badge--orange' : 'badge--gray';

      return `
        <tr>
          <td><b>${i.student_name || i.student_id}</b><br><small style="color: var(--text-muted); font-family: monospace;">${i.student_id}</small></td>
          <td><b>${i.title}</b><br><small style="color: var(--text-muted);">${i.issue}</small></td>
          <td><span class="badge badge--blue">${i.category}</span></td>
          <td style="font-size: 0.82rem;">${i.assigned_to_name}</td>
          <td><span class="badge ${prioCls}">${i.priority}</span></td>
          <td>
            <select class="form-control" style="padding: 4px 8px; font-size: 0.78rem; width: 110px;" onchange="window.updateInterventionStatus(${i.id}, this.value)">
              <option value="Open" ${i.status === 'Open' ? 'selected' : ''}>Open</option>
              <option value="In Progress" ${i.status === 'In Progress' ? 'selected' : ''}>In Progress</option>
              <option value="Scheduled" ${i.status === 'Scheduled' ? 'selected' : ''}>Scheduled</option>
              <option value="Completed" ${i.status === 'Completed' ? 'selected' : ''}>Completed</option>
              <option value="Cancelled" ${i.status === 'Cancelled' ? 'selected' : ''}>Cancelled</option>
            </select>
          </td>
          <td style="font-size: 0.8rem; color: var(--text-muted);">${i.due_date}</td>
          <td>
            <button class="btn-sm" onclick="window.viewStudentProfile('${i.student_id}')">Profile</button>
          </td>
        </tr>
      `;
    }).join('');
  }

  document.getElementById('int-status-filter')?.addEventListener('change', loadInterventions);
  document.getElementById('int-priority-filter')?.addEventListener('change', loadInterventions);
  document.getElementById('int-cat-filter')?.addEventListener('change', loadInterventions);

  window.updateInterventionStatus = async function (id, newStatus) {
    const res = await apiFetch(`/api/interventions/${id}/status`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: newStatus, notes: `Status set to ${newStatus}` })
    });
    if (res && res.ok) {
      showToast(`Intervention #${id} status updated to ${newStatus}!`, 'info');
      loadInterventions();
      loadDashboard(); // Refresh KPI counts
    }
  };

  // Intervention Modal Open / Submit
  window.openInterventionModal = function (prefill = {}) {
    const modal = document.getElementById('intervention-modal');
    if (!modal) return;
    document.getElementById('form-int-id').value = prefill.id || '';
    document.getElementById('form-int-student').value = prefill.student_id || '';
    document.getElementById('form-int-title-inp').value = prefill.title || '';
    document.getElementById('form-int-category').value = prefill.category || 'academic';
    document.getElementById('form-int-priority').value = prefill.priority || 'Medium';
    document.getElementById('form-int-issue').value = prefill.issue || '';
    document.getElementById('form-int-plan').value = prefill.action_plan || '';
    modal.classList.add('is-open');
  };

  document.getElementById('open-new-intervention-btn')?.addEventListener('click', () => {
    window.openInterventionModal();
  });
  document.getElementById('quick-create-intervention')?.addEventListener('click', () => {
    window.openInterventionModal();
  });
  document.getElementById('close-int-modal')?.addEventListener('click', () => {
    document.getElementById('intervention-modal')?.classList.remove('is-open');
  });
  document.getElementById('cancel-int-btn')?.addEventListener('click', () => {
    document.getElementById('intervention-modal')?.classList.remove('is-open');
  });

  document.getElementById('intervention-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const payload = {
      student_id: document.getElementById('form-int-student').value.trim(),
      title: document.getElementById('form-int-title-inp').value.trim(),
      category: document.getElementById('form-int-category').value,
      priority: document.getElementById('form-int-priority').value,
      issue: document.getElementById('form-int-issue').value.trim(),
      action_plan: document.getElementById('form-int-plan').value.trim(),
      assigned_to_name: document.getElementById('form-int-assignee').value.trim(),
      due_date: document.getElementById('form-int-due').value.trim()
    };

    const res = await apiFetch('/api/interventions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (res && res.ok) {
      document.getElementById('intervention-modal')?.classList.remove('is-open');
      showToast('Intervention created successfully and logged in database!', 'info');
      loadInterventions();
      loadDashboard();
    } else {
      showToast('Failed to create intervention. Check Student ID.', 'error');
    }
  });

  /* =========================================================
     9. CSV IMPORT & DATA INTEGRATION
     ========================================================= */
  async function handleCsvImport(commit = false) {
    const typeSelect = document.getElementById('import-type-select');
    const fileInput = document.getElementById('csv-file-input');

    if (!fileInput || !fileInput.files || fileInput.files.length === 0) {
      showToast('Please select a CSV file first.', 'error');
      return;
    }

    const formData = new FormData();
    formData.append('import_type', typeSelect.value);
    formData.append('commit', commit ? 'true' : 'false');
    formData.append('file', fileInput.files[0]);

    const res = await apiFetch('/api/integration/import', {
      method: 'POST',
      body: formData
    });

    if (!res || !res.ok) {
      showToast('Failed to process CSV file.', 'error');
      return;
    }

    const data = await res.json();
    const resultsBox = document.getElementById('import-results-box');
    const summaryText = document.getElementById('import-summary-text');
    const previewTable = document.getElementById('import-preview-table');

    if (resultsBox) resultsBox.style.display = 'block';

    const errHtml = data.errors.length > 0 ? `
      <div style="background: #fee2e2; color: #991b1b; padding: 10px; border-radius: var(--radius-md); margin-top: 8px;">
        <b>Validation Errors (${data.error_rows}):</b><br>
        <ul style="margin-left: 18px; font-size: 0.8rem;">
          ${data.errors.slice(0, 5).map((e) => `<li>${e}</li>`).join('')}
        </ul>
      </div>
    ` : '';

    if (summaryText) {
      summaryText.innerHTML = `
        <div style="display: flex; gap: 20px; font-weight: 600;">
          <span>Total Rows: ${data.total_rows}</span>
          <span style="color: #10b981;">Valid Rows: ${data.valid_rows}</span>
          <span style="color: #ef4444;">Error Rows: ${data.error_rows}</span>
          <span>Status: <b>${commit ? 'COMMITTED TO DATABASE' : 'PREVIEW ONLY'}</b></span>
        </div>
        ${errHtml}
      `;
    }

    if (previewTable && data.preview_data.length > 0) {
      const headers = Object.keys(data.preview_data[0]);
      previewTable.innerHTML = `
        <thead>
          <tr>${headers.map((h) => `<th>${h}</th>`).join('')}</tr>
        </thead>
        <tbody>
          ${data.preview_data.map((r) => `<tr>${headers.map((h) => `<td>${r[h]}</td>`).join('')}</tr>`).join('')}
        </tbody>
      `;
    }

    if (commit && data.valid_rows > 0) {
      showToast(`Successfully committed ${data.valid_rows} rows to database!`, 'info');
      loadDashboard();
    }
  }

  document.getElementById('preview-csv-btn')?.addEventListener('click', () => handleCsvImport(false));
  document.getElementById('csv-upload-form')?.addEventListener('submit', (e) => {
    e.preventDefault();
    handleCsvImport(true);
  });

  /* =========================================================
     10. REPORTS EXPORT
     ========================================================= */
  document.getElementById('quick-download-report')?.addEventListener('click', () => {
    window.location.href = '/api/reports/export.csv';
  });
  document.getElementById('export-report-btn')?.addEventListener('click', () => {
    const dept = document.getElementById('report-dept-select')?.value || 'All';
    const risk = document.getElementById('report-risk-select')?.value || 'all';
    window.location.href = `/api/reports/export.csv?department=${encodeURIComponent(dept)}&risk_filter=${encodeURIComponent(risk)}`;
  });

  /* =========================================================
     11. SETTINGS & WEIGHTS CONFIGURATION
     ========================================================= */
  async function loadSettings() {
    const res = await apiFetch('/api/settings/weights');
    if (!res || !res.ok) return;
    const weights = await res.json();

    const wA = document.getElementById('inp-w-acad');
    const wT = document.getElementById('inp-w-att');
    const wL = document.getElementById('inp-w-lms');
    const wP = document.getElementById('inp-w-plc');
    const wE = document.getElementById('inp-w-eng');

    if (wA) wA.value = weights.weight_academic;
    if (wT) wT.value = weights.weight_attendance;
    if (wL) wL.value = weights.weight_lms;
    if (wP) wP.value = weights.weight_placement;
    if (wE) wE.value = weights.weight_engagement;

    document.getElementById('lbl-w-acad').textContent = weights.weight_academic;
    document.getElementById('lbl-w-att').textContent = weights.weight_attendance;
    document.getElementById('lbl-w-lms').textContent = weights.weight_lms;
    document.getElementById('lbl-w-plc').textContent = weights.weight_placement;
    document.getElementById('lbl-w-eng').textContent = weights.weight_engagement;

    document.getElementById('inp-th-cgpa').value = weights.academic_risk_cgpa;
    document.getElementById('inp-th-att').value = weights.academic_risk_attendance;
    document.getElementById('inp-th-lms').value = weights.academic_risk_lms;
    document.getElementById('inp-th-plc').value = weights.placement_risk_readiness;

    // Load audit logs
    const auditRes = await apiFetch('/api/settings/audit-logs');
    if (auditRes && auditRes.ok) {
      const logs = await auditRes.json();
      const tbody = document.getElementById('audit-trail-tbody');
      if (tbody) {
        tbody.innerHTML = logs.map((l) => `
          <tr>
            <td style="font-family: monospace; font-size: 0.78rem;">${l.timestamp}</td>
            <td><b>${l.user_name}</b></td>
            <td><span class="badge badge--blue">${l.action}</span></td>
            <td style="font-size: 0.8rem; color: var(--text-muted);">${l.details || ''}</td>
          </tr>
        `).join('');
      }
    }
  }

  // Hook range inputs to live labels
  ['acad', 'att', 'lms', 'plc', 'eng'].forEach((k) => {
    const inp = document.getElementById(`inp-w-${k}`);
    const lbl = document.getElementById(`lbl-w-${k}`);
    inp?.addEventListener('input', () => {
      if (lbl) lbl.textContent = parseFloat(inp.value).toFixed(2);
    });
  });

  document.getElementById('weights-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const payload = {
      weight_academic: parseFloat(document.getElementById('inp-w-acad').value),
      weight_attendance: parseFloat(document.getElementById('inp-w-att').value),
      weight_lms: parseFloat(document.getElementById('inp-w-lms').value),
      weight_placement: parseFloat(document.getElementById('inp-w-plc').value),
      weight_engagement: parseFloat(document.getElementById('inp-w-eng').value),
      academic_risk_cgpa: parseFloat(document.getElementById('inp-th-cgpa').value),
      academic_risk_attendance: parseFloat(document.getElementById('inp-th-att').value),
      academic_risk_lms: parseFloat(document.getElementById('inp-th-lms').value),
      placement_risk_readiness: parseFloat(document.getElementById('inp-th-plc').value),
      placement_risk_skill: 55.0
    };

    const res = await apiFetch('/api/settings/weights', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (res && res.ok) {
      showToast('Settings & formula weights updated successfully!', 'info');
      loadDashboard();
      loadSettings();
    } else {
      showToast('Failed to update settings. Sum of weights must equal 1.0', 'error');
    }
  });

  /* =========================================================
     12. INITIALIZATION
     ========================================================= */
  const initialHash = window.location.hash.replace('#', '') || 'dashboard';
  switchView(initialHash);

})();

