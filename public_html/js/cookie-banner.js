/* === COOKIE CONSENT BANNER === */
(function () {
  var STORAGE_KEY = 'zd_cookie_consent';

  function init() {
    // Skip if user already made a choice
    if (localStorage.getItem(STORAGE_KEY)) return;

    // Inject CSS once
    if (!document.getElementById('zd-cookie-banner-css')) {
      var style = document.createElement('style');
      style.id = 'zd-cookie-banner-css';
      style.textContent = '' +
        '.zd-cookie-banner{position:fixed;left:24px;right:24px;bottom:24px;max-width:520px;margin:0 auto;background:#fff;border:1px solid rgba(0,0,0,0.08);border-radius:20px;box-shadow:0 16px 48px rgba(0,0,0,0.18);padding:24px;z-index:150;font-family:DM Sans,sans-serif;color:#1a103c;transform:translateY(40px);opacity:0;transition:transform 0.4s cubic-bezier(0.16,1,0.3,1),opacity 0.4s;}' +
        '.zd-cookie-banner.show{transform:translateY(0);opacity:1;}' +
        '.zd-cookie-banner-icon{width:48px;height:48px;border-radius:14px;background:rgba(124,77,255,0.1);display:flex;align-items:center;justify-content:center;margin-bottom:14px;}' +
        '.zd-cookie-banner-icon svg{width:24px;height:24px;color:#7c4dff;}' +
        '.zd-cookie-banner h3{font-family:DM Serif Display,serif;font-size:20px;margin-bottom:8px;}' +
        '.zd-cookie-banner p{font-size:13px;line-height:1.6;color:#8b80b0;margin-bottom:16px;}' +
        '.zd-cookie-banner p a{color:#7c4dff;text-decoration:none;font-weight:600;}' +
        '.zd-cookie-banner-actions{display:flex;gap:8px;flex-wrap:wrap;}' +
        '.zd-cookie-banner-actions button{flex:1;min-width:120px;padding:12px 16px;border:none;border-radius:12px;font-family:DM Sans,sans-serif;font-size:13px;font-weight:600;cursor:pointer;transition:transform 0.2s,filter 0.2s;}' +
        '.zd-cookie-banner-actions button:active{transform:scale(0.97);}' +
        '.zd-cookie-banner-btn-primary{background:#7c4dff;color:#fff;box-shadow:0 4px 14px rgba(124,77,255,0.25);}' +
        '.zd-cookie-banner-btn-primary:hover{filter:brightness(1.08);}' +
        '.zd-cookie-banner-btn-secondary{background:#f3f0ff;color:#5a2ecf;}' +
        '.zd-cookie-banner-btn-tertiary{background:transparent;color:#8b80b0;border:1px solid #ece8f3 !important;}' +
        '.zd-cookie-banner-customize{display:none;border-top:1px solid #ece8f3;margin-top:16px;padding-top:16px;}' +
        '.zd-cookie-banner.expanded .zd-cookie-banner-customize{display:block;}' +
        '.zd-cookie-banner-cat{display:flex;align-items:center;justify-content:space-between;padding:10px 0;border-bottom:1px solid rgba(0,0,0,0.04);}' +
        '.zd-cookie-banner-cat:last-child{border-bottom:none;}' +
        '.zd-cookie-banner-cat-name{font-size:13px;font-weight:600;}' +
        '.zd-cookie-banner-cat-desc{font-size:11px;color:#8b80b0;margin-top:2px;}' +
        '.zd-cookie-banner-toggle{position:relative;width:38px;height:22px;background:#e2e4ea;border-radius:11px;cursor:pointer;transition:background 0.2s;flex-shrink:0;margin-left:12px;}' +
        '.zd-cookie-banner-toggle::after{content:"";position:absolute;top:3px;left:3px;width:16px;height:16px;background:#fff;border-radius:50%;transition:transform 0.2s;box-shadow:0 1px 3px rgba(0,0,0,0.15);}' +
        '.zd-cookie-banner-toggle.active{background:#7c4dff;}' +
        '.zd-cookie-banner-toggle.active::after{transform:translateX(16px);}' +
        '.zd-cookie-banner-toggle.locked{background:#2e994d;cursor:not-allowed;opacity:0.7;}' +
        '.zd-cookie-banner-toggle.locked::after{transform:translateX(16px);}' +
        '@media(max-width:520px){.zd-cookie-banner{left:12px;right:12px;bottom:12px;padding:18px;}}';
      document.head.appendChild(style);
    }

    // Build banner HTML
    var banner = document.createElement('div');
    banner.className = 'zd-cookie-banner';
    banner.innerHTML =
      '<div class="zd-cookie-banner-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2a10 10 0 1 0 10 10 4 4 0 0 1-5-5 4 4 0 0 1-5-5"/><path d="M8.5 8.5v.01"/><path d="M16 15.5v.01"/><path d="M12 12v.01"/><path d="M11 17v.01"/><path d="M7 14v.01"/></svg></div>' +
      '<h3>Бисквитки 🍪</h3>' +
      '<p>Използваме бисквитки, за да помним устройството ви, да подобрим платформата и да ви предложим по-добро изживяване. <a href="cookies.html">Научи повече</a></p>' +
      '<div class="zd-cookie-banner-actions">' +
      '  <button class="zd-cookie-banner-btn-primary" data-action="accept-all">Приеми всички</button>' +
      '  <button class="zd-cookie-banner-btn-secondary" data-action="reject-all">Само необходимите</button>' +
      '  <button class="zd-cookie-banner-btn-tertiary" data-action="customize">Настройки</button>' +
      '</div>' +
      '<div class="zd-cookie-banner-customize">' +
      '  <div class="zd-cookie-banner-cat"><div><div class="zd-cookie-banner-cat-name">Необходими</div><div class="zd-cookie-banner-cat-desc">Винаги активни</div></div><div class="zd-cookie-banner-toggle locked"></div></div>' +
      '  <div class="zd-cookie-banner-cat"><div><div class="zd-cookie-banner-cat-name">Помни устройството</div><div class="zd-cookie-banner-cat-desc">Не се налага login всеки път</div></div><div class="zd-cookie-banner-toggle" data-cat="device"></div></div>' +
      '  <div class="zd-cookie-banner-cat"><div><div class="zd-cookie-banner-cat-name">Предпочитания</div><div class="zd-cookie-banner-cat-desc">Тема, език</div></div><div class="zd-cookie-banner-toggle" data-cat="prefs"></div></div>' +
      '  <div class="zd-cookie-banner-cat"><div><div class="zd-cookie-banner-cat-name">Функционални</div><div class="zd-cookie-banner-cat-desc">Запазени, скрити, "Близо до мен"</div></div><div class="zd-cookie-banner-toggle" data-cat="functional"></div></div>' +
      '  <div class="zd-cookie-banner-cat"><div><div class="zd-cookie-banner-cat-name">Анализи</div><div class="zd-cookie-banner-cat-desc">Анонимна статистика</div></div><div class="zd-cookie-banner-toggle" data-cat="analytics"></div></div>' +
      '  <div class="zd-cookie-banner-cat"><div><div class="zd-cookie-banner-cat-name">Маркетинг</div><div class="zd-cookie-banner-cat-desc">Релевантни реклами</div></div><div class="zd-cookie-banner-toggle" data-cat="marketing"></div></div>' +
      '  <button class="zd-cookie-banner-btn-primary" style="width:100%;margin-top:14px;" data-action="save-custom">Запази избора</button>' +
      '</div>';

    document.body.appendChild(banner);
    setTimeout(function () { banner.classList.add('show'); }, 100);

    // Action handlers
    banner.addEventListener('click', function (e) {
      var action = e.target.dataset.action;
      var toggle = e.target.closest('.zd-cookie-banner-toggle');

      if (toggle && !toggle.classList.contains('locked')) {
        toggle.classList.toggle('active');
        return;
      }

      if (action === 'accept-all') saveConsent({ device: true, prefs: true, functional: true, analytics: true, marketing: true, ab: true });
      else if (action === 'reject-all') saveConsent({ device: false, prefs: false, functional: false, analytics: false, marketing: false, ab: false });
      else if (action === 'customize') banner.classList.toggle('expanded');
      else if (action === 'save-custom') {
        var consent = {};
        banner.querySelectorAll('.zd-cookie-banner-toggle[data-cat]').forEach(function (t) {
          consent[t.dataset.cat] = t.classList.contains('active');
        });
        saveConsent(consent);
      }
    });
  }

  // Known cookies per consent category — used to delete on revoke
  var COOKIE_MAP = {
    analytics: ['_cs_c', '_cs_id', '_cs_s', '_cs_mk', '_cs_ex'],
    marketing: ['_fbp', '_gcl_au', '_gcl_aw'],
    ab: ['zd_ab_bucket']
  };
  function _deleteCookiesFor(category) {
    var names = COOKIE_MAP[category];
    if (!names) return;
    var domains = [location.hostname, '.' + location.hostname];
    names.forEach(function (n) {
      domains.forEach(function (dom) {
        document.cookie = n + '=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/; domain=' + dom;
      });
      document.cookie = n + '=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/;';
    });
  }

  function saveConsent(prefs) {
    prefs.essential = true;
    prefs.version = 1;
    prefs.timestamp = new Date().toISOString();
    // Delete cookies for revoked categories
    Object.keys(COOKIE_MAP).forEach(function (cat) {
      if (!prefs[cat]) _deleteCookiesFor(cat);
    });
    localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs));
    var banner = document.querySelector('.zd-cookie-banner');
    if (banner) {
      banner.classList.remove('show');
      setTimeout(function () { banner.remove(); }, 400);
    }
    // Notify any listeners (e.g. analytics-loader.js) so they can
    // load/unload third-party scripts immediately without a page reload.
    try {
      window.dispatchEvent(new CustomEvent('zd-consent-change', { detail: prefs }));
    } catch (e) { /* IE fallback not needed — site doesn't support IE */ }
  }

  // Expose a small read-only API so other scripts can check current consent
  // without re-parsing localStorage themselves.
  window.ZdConsent = {
    get: function () {
      try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || 'null'); }
      catch (e) { return null; }
    },
    has: function (category) {
      var c = this.get();
      return !!(c && c[category]);
    }
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
