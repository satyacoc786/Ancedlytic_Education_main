(() => {
  'use strict';

  const $ = (sel, root = document) => root.querySelector(sel);
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const clamp = (n) => Math.max(0, Math.min(100, n));
  const avg = (arr) => arr.reduce((a, b) => a + b, 0) / (arr.length || 1);

  /* =====================================================
     1. LOGIN GUARD: no session means back to the login page
     ===================================================== */
  const SESSION_KEY = 'sp_session';
  const getSession = () => {
    try { return JSON.parse(localStorage.getItem(SESSION_KEY) || sessionStorage.getItem(SESSION_KEY) || 'null'); }
    catch (e) { return null; }
  };
  const session = getSession();
  if (!session) { window.location.replace('index.html'); return; }

  $('#who-name').textContent = session.id;
  $('#avatar').textContent = String(session.id).charAt(0).toUpperCase();
  if (session.role === 'teacher') $('#role-note').hidden = false;

  $('#logout').addEventListener('click', () => {
    localStorage.removeItem(SESSION_KEY);
    sessionStorage.removeItem(SESSION_KEY);
    window.location.replace('index.html');
  });

  /* =====================================================
     2. DATA INTEGRATION: load the signed-in student's records
     ===================================================== */
  async function loadStudentView(id) {
    const token = localStorage.getItem('acadivance_token') || sessionStorage.getItem('acadivance_token');
    const response = await fetch(`/api/students/${encodeURIComponent(id)}/portal`, {
      headers: { Authorization: `Bearer ${token || ''}` }
    });
    if (response.status === 401) {
      window.location.replace('index.html');
      throw new Error('Your session has expired. Please sign in again.');
    }
    if (!response.ok) throw new Error('Unable to load your student records.');

    const record = await response.json();
    const academic = record.academic || {};
    const attendance = record.attendance || {};
    const lms = record.lms || {};
    const engagement = record.engagement || {};
    const placement = record.placement || {};
    return {
      id: record.id,
      name: record.name,
      semester: record.semester || 1,
      academic: {
        ...academic,
        available: Boolean(record.academic),
        cgpa: academic.cgpa ?? 0,
        semester: academic.semester ?? record.semester ?? 1,
        backlogs: academic.backlogs ?? 0,
        subjects: academic.subjects || []
      },
      attendance: { ...attendance, available: Boolean(record.attendance), percent: attendance.percentage ?? 0 },
      lms: {
        ...lms,
        available: Boolean(record.lms),
        courses: lms.courses_enrolled || 0,
        completion: lms.completion_rate || 0,
        assignmentsSubmitted: lms.assignments_submitted || 0,
        assignmentsTotal: lms.assignments_total || 0,
        quizAvg: lms.quiz_avg || 0,
        lastLogin: lms.last_activity || 'No recent activity'
      },
      engagement: {
        ...engagement,
        available: Boolean(record.engagement),
        score: engagement.score ?? 0,
        clubs: engagement.clubs_count || 0,
        events: engagement.events_attended || 0,
        mentorMeetings: engagement.mentor_meetings || 0,
        forumPosts: lms.forum_posts || 0
      },
      placement: {
        ...placement,
        available: Boolean(record.placement),
        readiness: placement.readiness_score || 0,
        mockInterviews: placement.mock_interviews || 0,
        resumeScore: placement.resume_score || 0
      },
      skills: { list: placement.skills || [], certifications: placement.certifications_count || 0 },
      interventions: record.interventions || [],
      scoreAnalysis: record.score_analysis
    };
  }

  /* =====================================================
     3. STUDENT SUCCESS SCORE (weighted, total = 100)
     ===================================================== */
  const LABELS = {
    academic: 'Academics',
    attendance: 'Attendance',
    lms: 'LMS activity',
    placement: 'Placement readiness',
    engagement: 'Campus engagement'
  };

  function renderScore(view) {
    const analysis = view.scoreAnalysis;
    const hasScores = analysis.data_completeness_percent > 0;
    const s = hasScores ? Math.round(analysis.overall_score) : null;
    const band = !hasScores ? ['Records pending', 'warn']
      : analysis.band === 'On Track' ? ['On track', 'good']
      : analysis.band === 'Needs Attention' ? ['Needs attention', 'warn']
      : ['At risk', 'bad'];
    $('#score-num').textContent = s === null ? '—' : s;
    $('#score-bar').style.width = (s || 0) + '%';
    const badge = $('#score-badge');
    badge.textContent = band[0];
    badge.className = 'badge ' + band[1];
    $('#score-how').innerHTML = Object.entries(analysis.components)
      .map(([key, component]) => `<li><span>${LABELS[key]} (${Math.round(component.weight * 100)}%)</span><b>${component.is_missing ? 'Missing' : `${component.normalized_score}/100`}</b></li>`).join('');
  }

  /* =====================================================
     4. ATTENDANCE CIRCLE
        below 50  -> red number,    "SHAME ON YOU"
        50 to 74  -> yellow number, "TRY MORE"
        75 and up -> green number,  "GOOD JOB"
     ===================================================== */
  function captionFor(p) {
    if (p < 50) return { text: 'SHAME ON YOU', cls: 'bad' };
    if (p < 75) return { text: 'TRY MORE', cls: 'warn' };
    return { text: 'GOOD JOB', cls: 'good' };
  }

  const CIRC = 2 * Math.PI * 100; // circle length (r = 100)
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  let countFrame = null;

  function renderAttendance(p, animate = true, available = true) {
    const ring = $('#ring');
    const el = $('#att-percent');
    cancelAnimationFrame(countFrame);
    if (!available) {
      ring.className = 'ring';
      ring.setAttribute('aria-label', 'Attendance data not available');
      $('#ring-bar').style.strokeDashoffset = CIRC;
      $('#att-caption').textContent = 'No data';
      el.textContent = '—';
      return;
    }
    const { text, cls } = captionFor(p);
    ring.className = 'ring ' + cls;
    ring.setAttribute('aria-label', `Attendance ${p} percent. ${text}`);
    $('#ring-bar').style.strokeDashoffset = CIRC * (1 - p / 100);
    $('#att-caption').textContent = text;

    // number counts up from 0 to the real value
    if (!animate || reduceMotion) { el.textContent = p + '%'; return; }
    const start = performance.now(), dur = 1200;
    const tick = (now) => {
      const t = Math.min(1, (now - start) / dur);
      el.textContent = Math.round(p * (1 - Math.pow(1 - t, 3))) + '%';
      if (t < 1) countFrame = requestAnimationFrame(tick);
    };
    countFrame = requestAnimationFrame(tick);
  }

  /* =====================================================
     5. BOXES (rendered in sequence, same order as the sketch)
     ===================================================== */
  const ICONS = {
    academics: '<path d="M4 5a2 2 0 0 1 2-2h13v16H6a2 2 0 0 0-2 2z"/><path d="M4 21V5"/>',
    lms: '<rect x="3" y="4" width="18" height="12" rx="2"/><path d="M8 20h8M12 16v4"/>',
    engagement: '<circle cx="9" cy="8" r="3"/><path d="M3 20c0-3 3-5 6-5s6 2 6 5"/><circle cx="17" cy="9" r="2.5"/><path d="M16 15c3 0 5 1.5 5 4"/>',
    placement: '<rect x="3" y="7" width="18" height="13" rx="2"/><path d="M9 7V5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2M3 13h18"/>',
    skills: '<path d="M13 2 4 14h7l-1 8 9-12h-7z"/>',
    feedback: '<path d="M21 12a8 8 0 0 1-11.5 7.2L4 20l1-4.5A8 8 0 1 1 21 12z"/>',
    interventions: '<path d="M8 6h13M8 12h13M8 18h13"/><path d="M3 6h.01M3 12h.01M3 18h.01"/>',
  };

  const kv = (pairs) => `<dl class="kv">${pairs.map(([k, v]) => `<div><dt>${esc(k)}</dt><dd>${esc(v)}</dd></div>`).join('')}</dl>`;
  const bar = (name, pct) => `<div><b><span>${esc(name)}</span><span>${Math.round(pct)}%</span></b><div class="mini"><span style="width:${clamp(pct)}%"></span></div></div>`;

  const TILES = [
    { id: 'academics', title: 'Academics',
      metric: (v) => v.academic.available ? `${v.academic.cgpa} CGPA` : 'No record',
      sub: (v) => v.academic.available ? `Semester ${v.academic.semester} · ${v.academic.backlogs} backlogs` : `Semester ${v.semester} · Awaiting records`,
      pct: (v) => v.academic.available ? v.academic.cgpa * 10 : 0,
      detail: (v) => v.academic.available
        ? kv([['CGPA', v.academic.cgpa], ['Semester', v.academic.semester], ['Backlogs', v.academic.backlogs]]) +
          `<div class="bars">${v.academic.subjects.map((s) => bar(s.name, s.marks)).join('')}</div>`
        : '<p>Academic records have not been added yet.</p>' },
    { id: 'lms', title: 'LMS',
      metric: (v) => v.lms.available ? `${v.lms.completion}%` : 'No record',
      sub: (v) => v.lms.available ? 'Course completion' : 'Awaiting synced data', pct: (v) => v.lms.available ? v.lms.completion : 0,
      detail: (v) => v.lms.available
        ? kv([['Courses enrolled', v.lms.courses], ['Course completion', v.lms.completion + '%'],
          ['Assignments', `${v.lms.assignmentsSubmitted}/${v.lms.assignmentsTotal}`], ['Quiz average', v.lms.quizAvg + '%'], ['Last login', v.lms.lastLogin]])
        : '<p>LMS activity has not been synced yet.</p>' },
    { id: 'engagement', title: 'Engagement',
      metric: (v) => v.engagement.available ? `${v.engagement.score}/100` : 'No record',
      sub: (v) => v.engagement.available ? `${v.engagement.events} events · ${v.engagement.clubs} clubs` : 'Awaiting campus data',
      pct: (v) => v.engagement.available ? v.engagement.score : 0,
      detail: (v) => v.engagement.available
        ? kv([['Engagement score', v.engagement.score + '/100'], ['Clubs joined', v.engagement.clubs], ['Events attended', v.engagement.events],
          ['Forum posts', v.engagement.forumPosts], ['Mentor meetings', v.engagement.mentorMeetings]])
        : '<p>Campus engagement data has not been added yet.</p>' },
    { id: 'placement', title: 'Placement',
      metric: (v) => v.placement.available ? `${v.placement.readiness}%` : 'No record',
      sub: (v) => v.placement.available ? 'Placement readiness' : 'Awaiting placement data',
      pct: (v) => v.placement.available ? v.placement.readiness : 0,
      detail: (v) => v.placement.available
        ? kv([['Readiness', v.placement.readiness + '%'], ['Resume score', v.placement.resumeScore + '/100'], ['Mock interviews', v.placement.mockInterviews]])
        : '<p>Placement records have not been added yet.</p>' },
    { id: 'skills', title: 'Skills',
      metric: (v) => v.skills.list.length ? `${Math.round(avg(v.skills.list.map((s) => s.level)))}%` : 'No record',
      sub: (v) => `${v.skills.certifications} certifications`, pct: (v) => avg(v.skills.list.map((s) => s.level)),
      detail: (v) => v.skills.list.length
        ? `<div class="bars">${v.skills.list.map((s) => bar(s.name, s.level)).join('')}</div>` + kv([['Certifications', v.skills.certifications]])
        : '<p>Skills have not been assessed yet.</p>' },
    { id: 'interventions', title: 'Support plans',
      metric: (v) => String(v.interventions.length), sub: (v) => `${v.interventions.filter((i) => !['Completed', 'Cancelled'].includes(i.status)).length} active`,
      pct: (v) => v.interventions.length ? (v.interventions.filter((i) => i.status === 'Completed').length / v.interventions.length) * 100 : 0,
      detail: (v) => v.interventions.length
        ? v.interventions.map((i) => `<p class="quote">${esc(i.title)}<small>${esc(i.status)} · ${esc(i.assigned_to || 'Staff')}</small></p>`).join('')
        : '<p>No support plans are currently recorded.</p>' },
  ];

  function renderTiles(view) {
    $('#tiles').innerHTML = TILES.map((t, i) => `
      <button class="tile" style="--i:${i}" data-tile="${t.id}" aria-haspopup="dialog">
        <span class="tile__icon"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICONS[t.id]}</svg></span>
        <span><span class="tile__title">${t.title}</span><span class="tile__sub">${esc(t.sub(view))}</span></span>
        <span class="tile__metric">${esc(t.metric(view))}</span>
        <span class="mini"><span style="width:${clamp(t.pct(view))}%"></span></span>
      </button>`).join('');
  }

  $('#tiles').addEventListener('click', (e) => {
    const btn = e.target.closest('[data-tile]');
    if (!btn) return;
    const t = TILES.find((x) => x.id === btn.dataset.tile);
    $('#detail-title').textContent = t.title;
    $('#detail-body').innerHTML = t.detail(view);
    $('#detail').showModal();
  });

  /* =====================================================
     6. AI COACH
     ===================================================== */
  async function askAiCoach(question) {
    const token = localStorage.getItem('acadivance_token') || sessionStorage.getItem('acadivance_token');
    const response = await fetch(`/api/students/${encodeURIComponent(session.id)}/coach`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token || ''}`
      },
      body: JSON.stringify({ question })
    });

    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail || 'The AI coach could not answer your request.');
    return data.answer || 'I could not generate a response from your data.';
  }

  const aiButton = $('#ask-ai-btn');
  const aiQuestion = $('#ai-question');
  const aiAnswer = $('#ai-answer');

  aiButton.addEventListener('click', async () => {
    const question = aiQuestion.value.trim();
    if (!question) {
      aiAnswer.textContent = 'Type a question about your progress to get advice from the AI coach.';
      aiQuestion.focus();
      return;
    }

    aiButton.disabled = true;
    aiButton.textContent = 'Thinking...';
    aiAnswer.textContent = 'Analyzing your progress and preparing a personalized answer...';

    try {
      const answer = await askAiCoach(question);
      aiAnswer.textContent = answer;
    } catch (error) {
      aiAnswer.textContent = error.message || 'The AI coach is unavailable right now.';
    } finally {
      aiButton.disabled = false;
      aiButton.textContent = 'Ask AI';
    }
  });

  aiQuestion.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' && (event.metaKey || event.ctrlKey)) {
      aiButton.click();
    }
  });

  /* =====================================================
     7. START (runs right after login)
     ===================================================== */
  let view = null;

  (async function init() {
    try {
      view = await loadStudentView(session.id);
      $('#who-name').textContent = view.name || session.id;
      renderScore(view);
      renderTiles(view);
      await sleep(300);
      renderAttendance(view.attendance.percent, true, view.attendance.available);
    } catch (error) {
      $('#tiles').textContent = error.message || 'Could not load student records.';
      $('#att-caption').textContent = 'Unavailable';
    }
  })();
})();