// popup.js — Minimal silent activation popup
// Installer sees only "Active" dot — no data stats, no info

const $ = id => document.getElementById(id);

async function init() {
  const stored = await chrome.runtime.sendMessage({ type: 'GET_AUTH' });

  if (stored?.authToken) {
    showActive();
  } else {
    showLogin();
  }
}

function showLogin() {
  $('screen-login').classList.remove('hidden');
  $('screen-active').classList.add('hidden');

  $('btn-activate').addEventListener('click', async () => {
    const code = $('activation-code').value.trim();
    if (!code) return showError('Enter your activation code.');

    $('btn-activate').disabled = true;
    $('btn-activate').textContent = 'Activating…';
    $('login-error').classList.add('hidden');

    const res = await chrome.runtime.sendMessage({
      type: 'AUTH_ACTIVATE',
      activationCode: code,
    });

    if (res?.ok) {
      showActive();
    } else {
      showError(res?.error || 'Invalid activation code. Try again.');
      $('btn-activate').disabled = false;
      $('btn-activate').textContent = 'Activate';
    }
  });

  $('activation-code').addEventListener('keydown', e => {
    if (e.key === 'Enter') $('btn-activate').click();
  });
}

function showActive() {
  $('screen-login').classList.add('hidden');
  $('screen-active').classList.remove('hidden');
}

function showError(msg) {
  const el = $('login-error');
  el.textContent = msg;
  el.classList.remove('hidden');
}

init();
