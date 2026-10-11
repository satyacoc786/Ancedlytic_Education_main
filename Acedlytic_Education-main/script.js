(() => {
  'use strict';

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

  /* =====================================================
     API LAYER  (replace these with real backend calls)
     ===================================================== */
  const api = {
    async login({ role, id, password }) {
      try {
        const response = await fetch('/api/auth/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ username_or_id: id, password: password })
        });
        if (!response.ok) return { ok: false };
        const data = await response.json();
        const allowedRoles = role === 'student'
          ? ['student']
          : ['admin', 'faculty', 'placement_officer', 'teacher'];
        if (!allowedRoles.includes(String(data.user.role).toLowerCase())) return { ok: false };
        return {
          ok: true,
          role: data.user.role,
          user: data.user.name || data.user.username,
          userId: data.user.role === 'student' ? data.user.username : data.user.id,
          token: data.access_token,
          userObj: data.user
        };
      } catch (err) {
        console.warn('Backend login failed:', err);
        return { ok: false };
      }
    },
    async registerStudent(payload) {
      try {
        const response = await fetch('/api/auth/register-student', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        const data = await response.json().catch(() => ({}));
        const detail = data.detail;
        return {
          ok: response.ok,
          data,
          error: typeof detail === 'string' ? detail : 'Check your details and try again.'
        };
      } catch (err) {
        console.warn('Student registration failed:', err);
        return { ok: false, error: 'Unable to reach the server. Try again shortly.' };
      }
    },
    async registerTeacher(payload) {
      try {
        const response = await fetch('/api/auth/register-teacher', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        const data = await response.json().catch(() => ({}));
        const detail = data.detail;
        return {
          ok: response.ok,
          data,
          error: typeof detail === 'string' ? detail : 'Check your details and try again.'
        };
      } catch (err) {
        console.warn('Teacher registration failed:', err);
        return { ok: false, error: 'Unable to reach the server. Try again shortly.' };
      }
    },
  };

  /* =====================================================
     Validation helpers
     ===================================================== */
  const ID_RE = /^[A-Za-z0-9/-]{3,30}$/;
  const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

  function setError(input, message) {
    const err = $('#' + input.getAttribute('aria-describedby'));
    input.setAttribute('aria-invalid', message ? 'true' : 'false');
    if (err) err.textContent = message || '';
  }

  function showAlert(form, type, message) {
    const box = $('.alert', form);
    box.hidden = !message;
    box.className = 'alert' + (type ? ' alert--' + type : '');
    box.textContent = message || '';
  }

  function setLoading(btn, on) {
    btn.disabled = on;
    btn.classList.toggle('is-loading', on);
  }

  /* =====================================================
     Show / hide password
     ===================================================== */
  $$('[data-toggle]').forEach((btn) => {
    btn.addEventListener('click', () => {
      const input = document.getElementById(btn.dataset.toggle);
      const show = input.type === 'password';
      input.type = show ? 'text' : 'password';
      btn.textContent = show ? 'Hide' : 'Show';
      btn.setAttribute('aria-label', show ? 'Hide password' : 'Show password');
    });
  });

  /* =====================================================
     Generic form handler (student + teacher)
     ===================================================== */
  function bindLoginForm({ form, role, idInput, validateId }) {
    const idEl = $(idInput, form);
    const passEl = $('input[type="password"], input[name="password"]', form);
    const submitBtn = $('button[type="submit"]', form);

    [idEl, passEl].forEach((el) => el.addEventListener('input', () => setError(el, '')));

    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      showAlert(form, null, '');

      const idMsg = validateId(idEl.value.trim());
      const passMsg = passEl.value.length < 6 ? 'Password must be at least 6 characters.' : '';
      setError(idEl, idMsg);
      setError(passEl, passMsg);
      if (idMsg || passMsg) {
        (idMsg ? idEl : passEl).focus();
        return;
      }

      setLoading(submitBtn, true);
      try {
        const res = await api.login({
          role,
          id: idEl.value.trim(),
          password: passEl.value,
          remember: form.elements.remember.checked,
        });
        if (!res.ok) throw new Error('Invalid credentials');

        // Store tokens & sessions
        const storage = (form.elements.remember && form.elements.remember.checked) ? localStorage : sessionStorage;
        storage.setItem('acadivance_token', res.token || '');
        storage.setItem('acadivance_user', JSON.stringify(res.userObj || { id: res.userId, role: res.role }));
        storage.setItem('sp_session', JSON.stringify({ id: res.userId || res.user, role: res.role }));

        showAlert(form, 'success', `Signed in successfully. Redirecting to dashboard…`);
        await sleep(700);

        const isStaff = ['admin', 'faculty', 'placement_officer', 'teacher'].includes(res.role.toLowerCase());
        window.location.href = isStaff ? 'staff-dashboard.html' : 'student-dashboard.html';
      } catch (err) {
        showAlert(form, 'error', 'Login failed. Check your details and try again.');
      } finally {
        setLoading(submitBtn, false);
      }
    });
  }

  bindLoginForm({
    form: $('#student-form'),
    role: 'student',
    idInput: '#student-id',
    validateId: (v) => (!v ? 'Enter your Student ID.' : !ID_RE.test(v) ? 'Student ID must be 4–20 letters or numbers.' : ''),
  });

  bindLoginForm({
    form: $('#teacher-form'),
    role: 'teacher',
    idInput: '#teacher-id',
    validateId: (v) => (!v ? 'Enter your Teacher ID or email.' : !(ID_RE.test(v) || EMAIL_RE.test(v)) ? 'Enter a valid Teacher ID or email address.' : ''),
  });

  const registrationForm = $('#student-register-form');
  const registrationInputs = {
    studentId: $('#new-student-id'),
    fullName: $('#new-student-name'),
    email: $('#new-student-email'),
    department: $('#new-student-department'),
    password: $('#new-student-password'),
    confirmPassword: $('#new-student-confirm'),
  };

  Object.values(registrationInputs).forEach((input) => {
    input.addEventListener('input', () => setError(input, ''));
    input.addEventListener('change', () => setError(input, ''));
  });

  registrationForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    showAlert(registrationForm, null, '');

    const formValues = Object.fromEntries(
      Object.entries(registrationInputs).map(([key, input]) => [key, input.value.trim()])
    );
    const errors = {
      studentId: !formValues.studentId || !ID_RE.test(formValues.studentId)
        ? 'Enter the student ID assigned by your college.' : '',
      fullName: formValues.fullName.length < 2 ? 'Enter your full name.' : '',
      email: !EMAIL_RE.test(formValues.email) ? 'Enter a valid email address.' : '',
      department: !formValues.department ? 'Select your department.' : '',
      password: formValues.password.length < 8 ? 'Password must be at least 8 characters.' : '',
      confirmPassword: formValues.confirmPassword !== formValues.password ? 'Passwords do not match.' : '',
    };
    Object.entries(errors).forEach(([key, message]) => setError(registrationInputs[key], message));
    const firstInvalid = Object.keys(errors).find((key) => errors[key]);
    if (firstInvalid) {
      registrationInputs[firstInvalid].focus();
      return;
    }

    const submitButton = $('button[type="submit"]', registrationForm);
    setLoading(submitButton, true);
    try {
      const result = await api.registerStudent({
        student_id: formValues.studentId,
        full_name: formValues.fullName,
        email: formValues.email,
        department: formValues.department,
        password: formValues.password,
      });
      if (!result.ok) throw new Error(result.error);

      const { data } = result;
      const storage = registrationForm.elements.remember.checked ? localStorage : sessionStorage;
      storage.setItem('acadivance_token', data.access_token);
      storage.setItem('acadivance_user', JSON.stringify(data.user));
      storage.setItem('sp_session', JSON.stringify({ id: data.user.username, role: 'student' }));
      showAlert(registrationForm, 'success', 'Account created. Opening your student dashboard…');
      await sleep(500);
      window.location.href = 'student-dashboard.html';
    } catch (error) {
      showAlert(registrationForm, 'error', error.message || 'Could not create the student account.');
    } finally {
      setLoading(submitButton, false);
    }
  });

  const teacherRegistrationForm = $('#teacher-register-form');
  const teacherRegistrationInputs = {
    teacherId: $('#new-teacher-id'),
    fullName: $('#new-teacher-name'),
    email: $('#new-teacher-email'),
    password: $('#new-teacher-password'),
    confirmPassword: $('#new-teacher-confirm'),
  };

  Object.values(teacherRegistrationInputs).forEach((input) => {
    input.addEventListener('input', () => setError(input, ''));
    input.addEventListener('change', () => setError(input, ''));
  });

  teacherRegistrationForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    showAlert(teacherRegistrationForm, null, '');

    const formValues = Object.fromEntries(
      Object.entries(teacherRegistrationInputs).map(([key, input]) => [key, input.value.trim()])
    );
    const errors = {
      teacherId: !formValues.teacherId || !ID_RE.test(formValues.teacherId) ? 'Enter your college-issued teacher ID.' : '',
      fullName: formValues.fullName.length < 2 ? 'Enter your full name.' : '',
      email: !EMAIL_RE.test(formValues.email) ? 'Enter a valid college email address.' : '',
      password: formValues.password.length < 8 ? 'Password must be at least 8 characters.' : '',
      confirmPassword: formValues.confirmPassword !== formValues.password ? 'Passwords do not match.' : '',
    };
    Object.entries(errors).forEach(([key, message]) => setError(teacherRegistrationInputs[key], message));
    const firstInvalid = Object.keys(errors).find((key) => errors[key]);
    if (firstInvalid) {
      teacherRegistrationInputs[firstInvalid].focus();
      return;
    }

    const submitButton = $('button[type="submit"]', teacherRegistrationForm);
    setLoading(submitButton, true);
    try {
      const result = await api.registerTeacher({
        teacher_id: formValues.teacherId,
        full_name: formValues.fullName,
        email: formValues.email,
        password: formValues.password,
      });
      if (!result.ok) throw new Error(result.error);

      const { data } = result;
      const storage = teacherRegistrationForm.elements.remember.checked ? localStorage : sessionStorage;
      storage.setItem('acadivance_token', data.access_token);
      storage.setItem('acadivance_user', JSON.stringify(data.user));
      storage.setItem('sp_session', JSON.stringify({ id: data.user.id, role: data.user.role }));
      showAlert(teacherRegistrationForm, 'success', 'Account created. Opening the staff dashboard…');
      await sleep(500);
      window.location.href = 'staff-dashboard.html';
    } catch (error) {
      showAlert(teacherRegistrationForm, 'error', error.message || 'Could not create the teacher account.');
    } finally {
      setLoading(submitButton, false);
    }
  });

  /* =====================================================
     Student login method tabs (ID / FRS)
     ===================================================== */
  const tabs = $$('.student-tabs .tab');
  const panes = {
    'tab-id': $('#pane-id'),
    'tab-register': $('#pane-register'),
    'tab-frs': $('#pane-frs'),
  };

  function selectTab(tab, focus = false) {
    tabs.forEach((t) => {
      const active = t === tab;
      t.classList.toggle('is-active', active);
      t.setAttribute('aria-selected', String(active));
      t.tabIndex = active ? 0 : -1;
      panes[t.id].hidden = !active;
    });
    if (focus) tab.focus();
  }

  tabs.forEach((tab, i) => {
    tab.addEventListener('click', () => selectTab(tab));
    tab.addEventListener('keydown', (e) => {
      if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') {
        const next = tabs[(i + (e.key === 'ArrowRight' ? 1 : tabs.length - 1)) % tabs.length];
        selectTab(next, true);
      }
    });
  });

  const teacherTabs = $$('.teacher-tabs .tab');
  const teacherPanes = {
    'teacher-tab-login': $('#teacher-pane-login'),
    'teacher-tab-register': $('#teacher-pane-register'),
  };

  function selectTeacherTab(tab, focus = false) {
    teacherTabs.forEach((teacherTab) => {
      const active = teacherTab === tab;
      teacherTab.classList.toggle('is-active', active);
      teacherTab.setAttribute('aria-selected', String(active));
      teacherTab.tabIndex = active ? 0 : -1;
      teacherPanes[teacherTab.id].hidden = !active;
    });
    if (focus) tab.focus();
  }

  teacherTabs.forEach((tab, index) => {
    tab.addEventListener('click', () => selectTeacherTab(tab));
    tab.addEventListener('keydown', (event) => {
      if (event.key === 'ArrowRight' || event.key === 'ArrowLeft') {
        const nextIndex = (index + (event.key === 'ArrowRight' ? 1 : teacherTabs.length - 1)) % teacherTabs.length;
        selectTeacherTab(teacherTabs[nextIndex], true);
      }
    });
  });

  $('#frs-fallback').addEventListener('click', () => selectTab($('#tab-id'), true));

  const faceStatus = $('#face-status');
  const faceLoginButton = $('#face-login');
  const faceEnrollButton = $('#face-enroll');

  function base64UrlToBytes(value) {
    const padded = value.replace(/-/g, '+').replace(/_/g, '/') + '='.repeat((4 - value.length % 4) % 4);
    return Uint8Array.from(atob(padded), (character) => character.charCodeAt(0));
  }

  function bytesToBase64Url(value) {
    return btoa(String.fromCharCode(...new Uint8Array(value)))
      .replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/g, '');
  }

  function serializeCredential(credential) {
    const response = credential.response;
    const serialized = {
      id: credential.id,
      rawId: bytesToBase64Url(credential.rawId),
      type: credential.type,
      authenticatorAttachment: credential.authenticatorAttachment,
      response: {
        clientDataJSON: bytesToBase64Url(response.clientDataJSON),
      },
    };
    if (response.attestationObject) {
      serialized.response.attestationObject = bytesToBase64Url(response.attestationObject);
      serialized.response.transports = response.getTransports ? response.getTransports() : [];
    } else {
      serialized.response.authenticatorData = bytesToBase64Url(response.authenticatorData);
      serialized.response.signature = bytesToBase64Url(response.signature);
      serialized.response.userHandle = response.userHandle ? bytesToBase64Url(response.userHandle) : null;
    }
    return serialized;
  }

  async function faceRequest(path, payload) {
    const response = await fetch(path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: payload ? JSON.stringify(payload) : undefined,
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail || 'Face sign-in could not be completed.');
    return data;
  }

  async function requirePlatformAuthenticator() {
    if (!window.PublicKeyCredential || !navigator.credentials) {
      throw new Error('This browser does not support Face ID or passkeys. Use Student ID sign-in instead.');
    }
    if (PublicKeyCredential.isUserVerifyingPlatformAuthenticatorAvailable) {
      const available = await PublicKeyCredential.isUserVerifyingPlatformAuthenticatorAvailable();
      if (!available) {
        throw new Error('No device authenticator is available. On Windows, set up Windows Hello in Settings > Accounts > Sign-in options, then reload this page in Edge or Chrome. On Apple devices, use Face ID or a passkey-enabled browser.');
      }
    }
  }

  function serializePublicKeyOptions(options) {
    return {
      ...options,
      challenge: base64UrlToBytes(options.challenge),
      ...(options.user ? { user: { ...options.user, id: base64UrlToBytes(options.user.id) } } : {}),
      ...(options.excludeCredentials ? {
        excludeCredentials: options.excludeCredentials.map((credential) => ({
          ...credential,
          id: base64UrlToBytes(credential.id),
        })),
      } : {}),
      ...(options.allowCredentials ? {
        allowCredentials: options.allowCredentials.map((credential) => ({
          ...credential,
          id: base64UrlToBytes(credential.id),
        })),
      } : {}),
    };
  }

  faceEnrollButton.addEventListener('click', async () => {
    const username = $('#face-student-id').value.trim();
    const password = $('#face-student-password').value;
    if (!username || !password) {
      faceStatus.textContent = 'Enter your student ID and password to verify your account.';
      return;
    }

    faceEnrollButton.disabled = true;
    faceStatus.textContent = 'Verifying your student account…';
    try {
      await requirePlatformAuthenticator();
      const options = await faceRequest('/api/auth/face/register/options', {
        username_or_id: username,
        password,
      });
      const credential = await navigator.credentials.create({ publicKey: serializePublicKeyOptions(options) });
      if (!credential) throw new Error('Device registration was cancelled.');
      await faceRequest('/api/auth/face/register/verify', {
        challenge: options.challenge,
        credential: serializeCredential(credential),
      });
      faceStatus.textContent = 'Face ID is ready on this device. You can now sign in with it.';
      $('#face-student-password').value = '';
    } catch (error) {
      faceStatus.textContent = error.message || 'Could not set up Face ID on this device.';
    } finally {
      faceEnrollButton.disabled = false;
    }
  });

  faceLoginButton.addEventListener('click', async () => {
    const username = $('#face-login-id').value.trim();
    if (!username) {
      faceStatus.textContent = 'Enter your student ID to continue.';
      return;
    }
    faceLoginButton.disabled = true;
    faceStatus.textContent = 'Waiting for your device to verify you…';
    try {
      await requirePlatformAuthenticator();
      const options = await faceRequest('/api/auth/face/login/options', { username_or_id: username });
      const credential = await navigator.credentials.get({ publicKey: serializePublicKeyOptions(options) });
      if (!credential) throw new Error('Face sign-in was cancelled.');
      const data = await faceRequest('/api/auth/face/login/verify', {
        challenge: options.challenge,
        credential: serializeCredential(credential),
      });
      sessionStorage.setItem('acadivance_token', data.access_token);
      sessionStorage.setItem('acadivance_user', JSON.stringify(data.user));
      sessionStorage.setItem('sp_session', JSON.stringify({ id: data.user.username, role: data.user.role }));
      faceStatus.textContent = 'Verified. Opening your dashboard…';
      await sleep(350);
      window.location.href = 'student-dashboard.html';
    } catch (error) {
      faceStatus.textContent = error.message || 'Face verification failed. Try again or use Student ID sign-in.';
    } finally {
      faceLoginButton.disabled = false;
    }
  });
})();