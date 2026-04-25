/* === HEADER SEARCH ICON + FOOTER REPORT BUTTON + LEGAL LINKS + GLOBAL A11Y ===
 *
 * Despite the name, this script is the de-facto "shared CSS injection" point
 * for the site. Every page loads it. So we use it to land site-wide
 * accessibility styles (focus-visible rings + prefers-reduced-motion guards)
 * in ONE file instead of editing 12 page <head>s.
 */
(function () {
  /* ---- GLOBAL CSS injected synchronously during <head> parse ----
     This script tag lives in <head> BEFORE any page <style>. We create
     a <style> element and append it to head — it lands BEFORE the page
     <style> that follows in source, so page rules win via source order
     when specificity is equal. */
  if (!document.getElementById('zd-a11y-css')) {
    var a11yStyle = document.createElement('style');
    a11yStyle.id = 'zd-a11y-css';
    a11yStyle.textContent = '' +
      /* :focus-visible — only show focus ring on keyboard nav, not mouse clicks.
         Site-wide rule: every interactive element gets a 3px purple ring. Pages
         that defined `outline:none` are now safely overridden because we use
         `outline` (not box-shadow) and pair it with `outline-offset` for clarity. */
      'a:focus-visible,' +
      'button:focus-visible,' +
      'input:focus-visible,' +
      'select:focus-visible,' +
      'textarea:focus-visible,' +
      '[role="button"]:focus-visible,' +
      '[tabindex]:not([tabindex="-1"]):focus-visible{' +
        'outline:3px solid #7c4dff!important;' +
        'outline-offset:2px!important;' +
        'border-radius:6px;' +
      '}' +
      /* Inputs/textareas already have border-radius — keep their focus ring tight */
      'input:focus-visible,' +
      'select:focus-visible,' +
      'textarea:focus-visible{' +
        'outline-offset:1px!important;' +
      '}' +
      /* Suppress focus ring on mouse clicks (matches modern UA default) */
      'a:focus:not(:focus-visible),' +
      'button:focus:not(:focus-visible),' +
      '[role="button"]:focus:not(:focus-visible){outline:none;}' +
      /* prefers-reduced-motion — kill animations + transitions + smooth scroll
         for users who have OS-level "reduce motion" enabled. CLAUDE.md hard rule
         + accessibility requirement. GSAP scroll triggers still fire but without
         the animated tweens (this is a CSS-only guard; for full GSAP suppression
         the page-level scripts can check `matchMedia("(prefers-reduced-motion)")`. */
      '@media (prefers-reduced-motion:reduce){' +
        '*,*::before,*::after{' +
          'animation-duration:0.01ms!important;' +
          'animation-iteration-count:1!important;' +
          'transition-duration:0.01ms!important;' +
          'scroll-behavior:auto!important;' +
        '}' +
      '}' +
      /* ═══ GLOBAL NAV LAYOUT — identical on every page ═══ */
      'nav{position:sticky;top:0;z-index:900;display:flex;justify-content:space-between;align-items:center;padding:12px 24px;background:rgba(255,255,255,0.92);backdrop-filter:blur(14px);-webkit-backdrop-filter:blur(14px);border-bottom:1px solid rgba(0,0,0,0.06);min-height:80px;}' +
      'nav .nav-logo{display:flex;align-items:center;text-decoration:none;flex-shrink:0;}' +
      'nav .nav-logo img{height:56px;width:auto;display:block;}' +
      'nav .nav-links{display:flex;align-items:center;gap:22px;}' +
      'nav .nav-links a.nav-link{color:#1a103c;text-decoration:none;font-size:14px;font-weight:600;padding:8px 4px;transition:color 0.2s;}' +
      'nav .nav-links a.nav-link:hover{color:#7c4dff;}' +
      /* Primary CTA — Търсене (search button) with subtle glow */
      'nav .nav-btn-search{display:inline-flex;align-items:center;gap:6px;padding:10px 20px;background:#7c4dff;color:#fff!important;border-radius:10px;font-weight:600;text-decoration:none;font-size:14px;box-shadow:0 4px 14px rgba(124,77,255,0.25),0 0 24px rgba(124,77,255,0.2);transition:transform 0.2s,box-shadow 0.2s;}' +
      'nav .nav-btn-search:hover{transform:translateY(-1px);box-shadow:0 6px 20px rgba(124,77,255,0.35),0 0 32px rgba(124,77,255,0.3);}' +
      'nav .nav-btn-search:active{transform:scale(0.97);}' +
      'nav .nav-btn-search svg{width:16px;height:16px;stroke:currentColor;stroke-width:2;fill:none;stroke-linecap:round;stroke-linejoin:round;}' +
      /* Partner — plain text link (like Контакти) + wobble animation */
      'nav .nav-btn-partner{color:#1a103c!important;text-decoration:none;font-size:14px;font-weight:600;padding:8px 4px;background:none!important;border:none!important;box-shadow:none!important;display:inline-flex;align-items:center;animation:zdNavWobble 3s ease-in-out infinite;transform-origin:center;}' +
      'nav .nav-btn-partner:hover{color:#7c4dff!important;animation-play-state:paused;}' +
      '@keyframes zdNavWobble{0%,88%,100%{transform:rotate(0deg)}90%{transform:rotate(-4deg)}92%{transform:rotate(3deg)}94%{transform:rotate(-3deg)}96%{transform:rotate(2deg)}98%{transform:rotate(-1deg)}}' +
      '@media(prefers-reduced-motion:reduce){nav .nav-btn-partner{animation:none!important}}' +
      /* Login button */
      'nav .nav-btn-login{display:inline-flex;align-items:center;padding:9px 18px;background:transparent;color:#1a103c!important;border:1.5px solid #ece8f3;border-radius:10px;font-weight:600;text-decoration:none;font-size:14px;transition:border-color 0.2s,background 0.2s;}' +
      'nav .nav-btn-login:hover{border-color:#7c4dff;background:rgba(124,77,255,0.04);}' +
      /* Report button — red warning CTA with soft pulsing glow */
      'nav .nav-btn-report{display:inline-flex;align-items:center;gap:7px;padding:9px 16px;background:linear-gradient(180deg,#f05a78,#e23e62)!important;color:#fff!important;border:1px solid rgba(226,62,98,0.6);border-radius:10px;font-weight:700;text-decoration:none;font-size:14px;box-shadow:0 0 0 0 rgba(231,76,111,0.55),0 4px 14px rgba(231,76,111,0.35);transition:transform 0.2s,box-shadow 0.2s,filter 0.2s;animation:zdReportGlow 2.8s ease-in-out infinite;}' +
      'nav .nav-btn-report svg{width:16px;height:16px;stroke:currentColor;stroke-width:2.3;fill:none;stroke-linecap:round;stroke-linejoin:round;flex-shrink:0;}' +
      'nav .nav-btn-report:hover{transform:translateY(-1px);filter:brightness(1.05);box-shadow:0 0 0 6px rgba(231,76,111,0.18),0 8px 22px rgba(231,76,111,0.5);}' +
      'nav .nav-btn-report:active{transform:scale(0.97);}' +
      '@keyframes zdReportGlow{0%,100%{box-shadow:0 0 0 0 rgba(231,76,111,0.45),0 4px 14px rgba(231,76,111,0.3);}50%{box-shadow:0 0 0 5px rgba(231,76,111,0.12),0 6px 18px rgba(231,76,111,0.45);}}' +
      '@media(prefers-reduced-motion:reduce){nav .nav-btn-report{animation:none!important}}' +
      /* Skip-to-content link — hidden until focused via Tab */
      '.zd-skip-link{position:absolute;top:-50px;left:0;background:#7c4dff;color:#fff;padding:10px 18px;z-index:10000;font-size:14px;font-weight:600;border-radius:0 0 10px 0;text-decoration:none;transition:top 0.2s;}' +
      '.zd-skip-link:focus{top:0;}' +
      /* ---- HAMBURGER MENU (mobile ≤768px) ---- */
      '.zd-hamburger{display:none;background:rgba(255,255,255,0.9);border:1.5px solid #ece8f3;cursor:pointer;padding:8px;border-radius:10px;z-index:101;-webkit-tap-highlight-color:transparent;color:#1a103c;}' +
      '.zd-hamburger svg{width:24px;height:24px;stroke:currentColor;stroke-width:2.5;stroke-linecap:round;fill:none;}' +
      '.zd-hamburger .bar1,.zd-hamburger .bar2,.zd-hamburger .bar3{transition:transform 0.3s cubic-bezier(0.16,1,0.3,1),opacity 0.2s;stroke:#1a103c!important;}' +
      '@media(max-width:768px){' +
        '.zd-hamburger{display:flex!important;align-items:center;justify-content:center;color:#1a103c!important;background:rgba(255,255,255,0.9)!important;border:1.5px solid #ece8f3!important;box-shadow:0 2px 8px rgba(0,0,0,0.08);}' +
        '.zd-hamburger svg line{stroke:#1a103c!important;}' +
        '.nav-links{position:fixed!important;top:0!important;right:0!important;left:auto!important;width:300px!important;height:100vh!important;height:100dvh!important;background:#ffffff!important;flex-direction:column!important;align-items:stretch!important;padding:88px 28px 40px!important;gap:4px!important;z-index:10000!important;box-shadow:-8px 0 32px rgba(0,0,0,0.15)!important;transform:translateX(100%)!important;transition:transform 0.35s cubic-bezier(0.16,1,0.3,1)!important;will-change:transform;}' +
        '.nav-links.zd-open{transform:translateX(0)!important;}' +
        '.nav-links a.nav-link{display:block!important;color:#1a103c!important;text-shadow:none!important;font-size:18px!important;font-weight:600!important;padding:16px 0!important;border-bottom:1px solid #ece8f3!important;background:transparent!important;}' +
        '.nav-links a.nav-link:hover{color:#7c4dff!important;}' +
        '.nav-links .nav-btn-partner{display:block!important;width:100%!important;color:#1a103c!important;text-shadow:none!important;text-align:center!important;padding:16px 0!important;margin-top:12px!important;min-height:48px!important;font-size:18px!important;font-weight:700!important;background:transparent!important;animation:zdNavWobble 3s ease-in-out infinite!important;}' +
        '.nav-links .nav-btn-search{display:flex!important;width:100%!important;justify-content:center!important;margin-top:12px!important;min-height:52px!important;font-size:16px!important;padding:14px 20px!important;color:#ffffff!important;background:#7c4dff!important;}' +
        '.nav-links .nav-btn-login{display:flex!important;width:100%!important;justify-content:center!important;margin-top:8px!important;min-height:48px!important;font-size:16px!important;color:#1a103c!important;background:transparent!important;border:1.5px solid #ece8f3!important;}' +
        '.nav-links .nav-btn-report{display:flex!important;width:100%!important;justify-content:center!important;gap:8px!important;margin-top:12px!important;min-height:48px!important;font-size:16px!important;padding:12px 20px!important;color:#ffffff!important;background:linear-gradient(180deg,#f05a78,#e23e62)!important;border:1px solid rgba(226,62,98,0.6)!important;box-shadow:0 6px 18px rgba(231,76,111,0.35)!important;animation:none!important;}' +
        '.nav-links .nav-btn-report svg{width:18px!important;height:18px!important;}' +
        '.zd-nav-backdrop{display:none;position:fixed;inset:0;background:rgba(0,0,0,0.35);z-index:899;-webkit-tap-highlight-color:transparent;}' +
        '.zd-nav-backdrop.zd-open{display:block;}' +
      '}' +
      /* Hamburger X animation when open */
      '.zd-hamburger.zd-open .bar1{transform:translateY(7px) rotate(45deg);}' +
      '.zd-hamburger.zd-open .bar2{opacity:0;}' +
      '.zd-hamburger.zd-open .bar3{transform:translateY(-7px) rotate(-45deg);}' +
      /* ═══ AUTH MENU dropdown (login + profile dropdowns in nav) ═══ */
      '.zd-auth-anchor{position:relative;display:inline-flex;}' +
      '.zd-auth-menu{position:absolute;top:calc(100% + 8px);right:0;min-width:220px;background:#fff;border:1px solid #ece8f3;border-radius:14px;box-shadow:0 14px 40px rgba(26,16,60,0.10),0 4px 12px rgba(26,16,60,0.04);padding:6px;display:none;flex-direction:column;z-index:1100;animation:zdAuthMenuFadeIn 0.16s ease-out;}' +
      '.zd-auth-menu.zd-open{display:flex;}' +
      '.zd-auth-menu .zd-auth-item{display:flex;align-items:center;gap:10px;padding:10px 14px;border-radius:10px;color:#1a103c;text-decoration:none;font-size:14px;font-weight:600;font-family:DM Sans,sans-serif;background:transparent;border:none;cursor:pointer;text-align:left;width:100%;transition:background 0.15s,color 0.15s;}' +
      '.zd-auth-menu .zd-auth-item:hover{background:rgba(124,77,255,0.06);color:#7c4dff;}' +
      '.zd-auth-menu .zd-auth-item:focus-visible{background:rgba(124,77,255,0.08);}' +
      '.zd-auth-menu .zd-auth-item--danger{color:#c23a5d;}' +
      '.zd-auth-menu .zd-auth-item--danger:hover{background:rgba(194,58,93,0.08);color:#c23a5d;}' +
      '.zd-auth-menu .zd-auth-item svg{width:16px;height:16px;stroke:currentColor;stroke-width:2;fill:none;flex-shrink:0;}' +
      '.zd-auth-menu .zd-auth-divider{height:1px;background:#ece8f3;margin:4px 8px;}' +
      '.zd-auth-menu .zd-auth-section-label{font-size:11px;font-weight:700;letter-spacing:0.06em;text-transform:uppercase;color:#8b80b0;padding:8px 14px 4px;}' +
      '@keyframes zdAuthMenuFadeIn{from{opacity:0;transform:translateY(-4px);}to{opacity:1;transform:translateY(0);}}' +
      /* Mobile: dropdown becomes full-width inside hamburger */
      '@media(max-width:980px){' +
        '.zd-auth-menu{position:static;width:100%;min-width:0;box-shadow:none;border:1px solid #ece8f3;margin-top:8px;}' +
      '}';
    // Append to head at parse time. This style lands just after the <script>
    // (which is before the page's own <style>), so the page <style> wins when
    // specificity is equal — per-page rules override these defaults.
    var head = document.head || document.getElementsByTagName('head')[0] || document.documentElement;
    head.appendChild(a11yStyle);
  }

  function init() {
    /* ---- SKIP-TO-CONTENT LINK ---- */
    if (!document.querySelector('.zd-skip-link')) {
      var mainEl = document.querySelector('main') || document.querySelector('[role="main"]');
      var targetId = mainEl ? (mainEl.id || 'zd-main-content') : 'zd-main-content';
      if (mainEl && !mainEl.id) mainEl.id = targetId;
      var skip = document.createElement('a');
      skip.className = 'zd-skip-link';
      skip.href = '#' + targetId;
      skip.textContent = 'Премини към съдържанието';
      document.body.insertBefore(skip, document.body.firstChild);
    }
    /* ---- HEADER: remove stale search icon if present from previous version ---- */
    var oldSearchIcon = document.querySelector('.nav-search-icon');
    if (oldSearchIcon) oldSearchIcon.remove();

    /* ---- REPORT BUTTON INJECTION (top nav, before login) ---- */
    var _nav = document.querySelector('nav');
    var _navLinks = _nav ? _nav.querySelector('.nav-links') : null;
    if (_navLinks && !_navLinks.querySelector('.nav-btn-report')) {
      var reportBtn = document.createElement('a');
      reportBtn.href = 'report.html';
      reportBtn.className = 'nav-btn-report';
      reportBtn.setAttribute('aria-label', 'Подай сигнал за нарушение');
      reportBtn.innerHTML =
        '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">' +
          '<path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>' +
          '<line x1="12" y1="9" x2="12" y2="13"/>' +
          '<line x1="12" y1="17" x2="12.01" y2="17"/>' +
        '</svg><span>Подай сигнал</span>';
      var loginBtn = _navLinks.querySelector('.nav-btn-login');
      if (loginBtn) _navLinks.insertBefore(reportBtn, loginBtn);
      else _navLinks.appendChild(reportBtn);
    }

    /* ---- HAMBURGER MENU INJECTION ---- */
    var nav = document.querySelector('nav');
    var navLinks = nav ? nav.querySelector('.nav-links') : null;
    if (nav && navLinks && !nav.querySelector('.zd-hamburger')) {
      // Create hamburger button
      var burger = document.createElement('button');
      burger.className = 'zd-hamburger';
      burger.setAttribute('aria-label', 'Меню');
      burger.setAttribute('aria-expanded', 'false');
      burger.innerHTML = '<svg viewBox="0 0 24 24" fill="none"><line class="bar1" x1="4" y1="6" x2="20" y2="6"/><line class="bar2" x1="4" y1="12" x2="20" y2="12"/><line class="bar3" x1="4" y1="18" x2="20" y2="18"/></svg>';
      nav.appendChild(burger);

      // Create backdrop
      var backdrop = document.createElement('div');
      backdrop.className = 'zd-nav-backdrop';
      backdrop.setAttribute('aria-hidden', 'true');
      document.body.appendChild(backdrop);

      function handleEscape(e) { if (e.key === 'Escape') closeMenu(); }
      function openMenu() {
        navLinks.classList.add('zd-open');
        burger.classList.add('zd-open');
        backdrop.classList.add('zd-open');
        burger.setAttribute('aria-expanded', 'true');
        document.body.style.overflow = 'hidden';
        document.addEventListener('keydown', handleEscape);
      }
      function closeMenu() {
        navLinks.classList.remove('zd-open');
        burger.classList.remove('zd-open');
        backdrop.classList.remove('zd-open');
        burger.setAttribute('aria-expanded', 'false');
        document.body.style.overflow = '';
        document.removeEventListener('keydown', handleEscape);
      }
      burger.addEventListener('click', function() {
        navLinks.classList.contains('zd-open') ? closeMenu() : openMenu();
      });
      backdrop.addEventListener('click', closeMenu);
      // Close on nav link click (event delegation)
      navLinks.addEventListener('click', function(e) {
        if (e.target.closest('a')) closeMenu();
      });
    }

    /* ---- FOOTER: red report button + legal links ---- */
    var footer = document.querySelector('.zd-footer');
    if (footer && !footer.querySelector('.zd-footer-report-btn')) {
      // Inject CSS once
      if (!document.getElementById('zd-footer-extras-css')) {
        var style = document.createElement('style');
        style.id = 'zd-footer-extras-css';
        style.textContent = '' +
          '.zd-footer-report{display:flex;justify-content:center;padding:0 24px 24px;}' +
          '.zd-footer-report-btn{display:inline-flex;align-items:center;gap:10px;padding:14px 28px;border-radius:14px;background:#e74c6f;color:#fff;font-weight:600;font-size:14px;font-family:DM Sans,sans-serif;text-decoration:none;box-shadow:0 6px 20px rgba(231,76,111,0.25);transition:transform 0.2s,box-shadow 0.2s;}' +
          '.zd-footer-report-btn:hover{transform:translateY(-2px);box-shadow:0 10px 28px rgba(231,76,111,0.35);}' +
          '.zd-footer-report-btn:active{transform:scale(0.97);}' +
          '.zd-footer-report-btn svg{width:18px;height:18px;}' +
          '.zd-footer-socials{display:flex;justify-content:center;gap:12px;margin-bottom:16px;}' +
          '.zd-footer-socials a{width:36px;height:36px;border-radius:10px;display:flex;align-items:center;justify-content:center;background:rgba(124,77,255,0.06);border:1px solid rgba(124,77,255,0.12);transition:transform 0.2s,background 0.2s;}' +
          '.zd-footer-socials a:hover{transform:translateY(-2px);background:rgba(124,77,255,0.12);}' +
          '.zd-footer-socials img{width:18px;height:18px;}';
        document.head.appendChild(style);
      }

      // Build the button container
      var reportContainer = document.createElement('div');
      reportContainer.className = 'zd-footer-report';
      reportContainer.innerHTML = '<a href="report.html" class="zd-footer-report-btn"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>Подай сигнал за нарушение</a>';
      footer.insertBefore(reportContainer, footer.firstChild);

      // Add legal links to .zd-footer-links if not already present
      var footerLinks = footer.querySelector('.zd-footer-links');
      if (footerLinks && !footerLinks.querySelector('a[href="terms.html"]')) {
        // Remove old "Докладвай" link if it exists
        var oldReport = footerLinks.querySelector('a[href="report.html"]');
        if (oldReport) oldReport.remove();

        // Append legal links
        var legalHTML = '<a href="terms.html">Условия за ползване</a><a href="privacy.html">Поверителност</a><a href="cookies.html">Бисквитки</a>';
        footerLinks.insertAdjacentHTML('beforeend', legalHTML);
      }

      // Add social icons row to footer
      if (!footer.querySelector('.zd-footer-socials')) {
        var socialsDiv = document.createElement('div');
        socialsDiv.className = 'zd-footer-socials';
        socialsDiv.innerHTML = '' +
          '<a href="https://www.facebook.com/bgregzadeteto/" target="_blank" rel="noopener" title="Facebook"><img src="https://assets.cdn.filesafe.space/EiVgrua1Bi7nEWRXtm8R/media/69da779aa4e6aa34cbc97684.svg" alt="Facebook"></a>' +
          '<a href="https://www.instagram.com/zade.teto/" target="_blank" rel="noopener" title="Instagram"><img src="https://assets.cdn.filesafe.space/EiVgrua1Bi7nEWRXtm8R/media/69da779a77bcdd31bb6f417b.svg" alt="Instagram"></a>' +
          '<a href="tiktok.html" title="TikTok"><img src="https://assets.cdn.filesafe.space/EiVgrua1Bi7nEWRXtm8R/media/69da779aa4e6aa34cbc976a8.svg" alt="TikTok"></a>' +
          '<a href="https://www.linkedin.com/showcase/zadeteto-com/" target="_blank" rel="noopener" title="LinkedIn"><img src="https://assets.cdn.filesafe.space/EiVgrua1Bi7nEWRXtm8R/media/69da779a019dc508d342f768.svg" alt="LinkedIn"></a>' +
          '<a href="youtube.html" title="YouTube"><img src="https://assets.cdn.filesafe.space/EiVgrua1Bi7nEWRXtm8R/media/69da779b982fd67a3560f3e6.svg" alt="YouTube"></a>';
        // Insert before the copyright line
        var copyEl = footer.querySelector('.zd-footer-copy');
        if (copyEl) footer.insertBefore(socialsDiv, copyEl);
        else footer.appendChild(socialsDiv);
      }
    }

    /* ═══ AUTH MENU dropdowns (login + profile) ═══ */
    initAuthMenu();
  }

  /* Helpers за auth menu */
  function _zdCloseAllAuthMenus(except) {
    document.querySelectorAll('.zd-auth-menu.zd-open').forEach(function (m) {
      if (m !== except) m.classList.remove('zd-open');
    });
  }
  document.addEventListener('click', function (e) {
    if (!e.target.closest('.zd-auth-anchor')) _zdCloseAllAuthMenus();
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') _zdCloseAllAuthMenus();
  });

  function _zdMakeAnchor(btn) {
    // Wrap a button/link in a positioning anchor so the dropdown sits relative to it
    if (btn.parentElement && btn.parentElement.classList.contains('zd-auth-anchor')) {
      return btn.parentElement;
    }
    var anchor = document.createElement('span');
    anchor.className = 'zd-auth-anchor';
    btn.parentNode.insertBefore(anchor, btn);
    anchor.appendChild(btn);
    return anchor;
  }

  function _zdBuildMenu(items) {
    var menu = document.createElement('div');
    menu.className = 'zd-auth-menu';
    menu.setAttribute('role', 'menu');
    items.forEach(function (it) {
      if (it.divider) {
        var d = document.createElement('div');
        d.className = 'zd-auth-divider';
        menu.appendChild(d);
        return;
      }
      if (it.label) {
        var l = document.createElement('div');
        l.className = 'zd-auth-section-label';
        l.textContent = it.label;
        menu.appendChild(l);
        return;
      }
      var el;
      if (it.href) {
        el = document.createElement('a');
        el.href = it.href;
      } else {
        el = document.createElement('button');
        el.type = 'button';
      }
      el.className = 'zd-auth-item' + (it.danger ? ' zd-auth-item--danger' : '');
      el.setAttribute('role', 'menuitem');
      el.innerHTML = (it.icon || '') + '<span>' + it.text + '</span>';
      if (it.onclick) el.addEventListener('click', function (e) { it.onclick(e); _zdCloseAllAuthMenus(); });
      menu.appendChild(el);
    });
    return menu;
  }

  function _zdRoleIcons() {
    return {
      admin:    '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>',
      business: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 21h18M5 21V7l7-4 7 4v14M9 9h.01M9 13h.01M9 17h.01M15 9h.01M15 13h.01M15 17h.01"/></svg>',
      parent:   '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/></svg>',
      logout:   '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>'
    };
  }

  /* ── LOGGED-OUT: replace „Вход" link with role-pick dropdown ── */
  function _zdAttachLoginDropdown(loginBtn) {
    if (loginBtn.dataset.zdAuthMenuAttached === '1') return;
    loginBtn.dataset.zdAuthMenuAttached = '1';
    loginBtn.setAttribute('aria-haspopup', 'menu');
    loginBtn.setAttribute('aria-expanded', 'false');
    // Премахваме inline onclick (search.html го set-ва за openAuthModal)
    loginBtn.onclick = null;
    loginBtn.removeAttribute('onclick');
    var anchor = _zdMakeAnchor(loginBtn);
    var menu = _zdBuildMenu([
      { label: 'Вход като' },
      {
        text: 'Родител',
        href: 'search.html?login=true',
        icon: _zdRoleIcons().parent
      },
      {
        text: 'Партньор',
        href: 'business-login.html',
        icon: _zdRoleIcons().business
      }
    ]);
    anchor.appendChild(menu);

    loginBtn.addEventListener('click', function (e) {
      // Re-clear onclick на всеки клик за случаите когато други скриптове го re-set-ват
      loginBtn.onclick = null;
      e.preventDefault();
      e.stopPropagation();
      e.stopImmediatePropagation();
      var isOpen = menu.classList.contains('zd-open');
      _zdCloseAllAuthMenus();
      if (!isOpen) {
        menu.classList.add('zd-open');
        loginBtn.setAttribute('aria-expanded', 'true');
        var first = menu.querySelector('.zd-auth-item');
        if (first) first.focus();
      } else {
        loginBtn.setAttribute('aria-expanded', 'false');
      }
    }, true); // capture phase
  }

  /* ── LOGGED-IN: replace any .nav-auth-btn with role-aware dropdown ── */
  async function _zdAttachProfileDropdown(profileBtn, session) {
    if (profileBtn.dataset.zdAuthMenuAttached === '1') return;
    profileBtn.dataset.zdAuthMenuAttached = '1';
    profileBtn.setAttribute('aria-haspopup', 'menu');
    profileBtn.setAttribute('aria-expanded', 'false');

    // Detect role
    var role = 'parent';
    var ownerRow = null;
    try {
      var ownerRes = await window.ZdSupabase
        .from('business_owners')
        .select('id, business_id, is_admin, is_superadmin')
        .eq('id', session.user.id)
        .maybeSingle();
      ownerRow = ownerRes.data || null;
      if (ownerRow && (ownerRow.is_admin || ownerRow.is_superadmin)) role = 'admin';
      else if (ownerRow && ownerRow.business_id) role = 'business';
    } catch (e) {
      console.warn('[auth-menu] role lookup failed:', e);
    }

    // Build menu items по role
    var icons = _zdRoleIcons();
    var items = [];
    if (role === 'admin') {
      items.push({ text: 'Админ панел', href: 'business-audit-admin.html', icon: icons.admin });
      items.push({ text: 'Моят бизнес', href: 'business-dashboard.html', icon: icons.business });
    } else if (role === 'business') {
      items.push({ text: 'Бизнес профил', href: 'business-dashboard.html', icon: icons.business });
    } else {
      items.push({ text: 'Запазени бизнеси', href: 'search.html#liked', icon: icons.parent });
    }
    items.push({ divider: true });
    items.push({
      text: 'Изход',
      icon: icons.logout,
      danger: true,
      onclick: async function (e) {
        e.preventDefault();
        try { if (window.ZdSupabase) await window.ZdSupabase.auth.signOut(); } catch (_) {}
        try { localStorage.removeItem('zd_parent_logged_in'); } catch (_) {}
        // Redirect според контекста
        if (/\/(business-dashboard|business-audit-admin|business-audit|business-login|claim|welcome)\.html/i.test(location.pathname)) {
          location.replace('business-login.html');
        } else {
          location.reload();
        }
      }
    });

    var anchor = _zdMakeAnchor(profileBtn);
    var menu = _zdBuildMenu(items);
    anchor.appendChild(menu);

    // Override existing click handler — премахваме any onclick set by inline pages
    profileBtn.onclick = null;
    profileBtn.addEventListener('click', function (e) {
      // search.html / listing.html re-set onclick on всеки auth state change.
      // Изтриваме го наново всеки път и прекъсваме propagation за да не сработи.
      profileBtn.onclick = null;
      e.preventDefault();
      e.stopPropagation();
      e.stopImmediatePropagation();
      var isOpen = menu.classList.contains('zd-open');
      _zdCloseAllAuthMenus();
      if (!isOpen) {
        menu.classList.add('zd-open');
        profileBtn.setAttribute('aria-expanded', 'true');
        var first = menu.querySelector('.zd-auth-item');
        if (first) first.focus();
      } else {
        profileBtn.setAttribute('aria-expanded', 'false');
      }
    }, true); // capture phase, преди inline handler-и
  }

  function initAuthMenu() {
    // Logged-OUT button: винаги attach дропдауна (без значение от Supabase)
    var loginBtn = document.querySelector('.nav-btn-login');
    if (loginBtn) _zdAttachLoginDropdown(loginBtn);

    // Logged-IN button: чакаме Supabase да зареди + има активна session
    var profileBtns = document.querySelectorAll('.nav-auth-btn');
    if (profileBtns.length === 0) return;

    function tryAttach() {
      if (!window.ZdSupabase) return false;
      window.ZdSupabase.auth.getSession().then(function (res) {
        var session = res && res.data ? res.data.session : null;
        if (!session || !session.user) return; // not logged in: leave default behaviour
        profileBtns.forEach(function (btn) { _zdAttachProfileDropdown(btn, session); });
      });
      return true;
    }

    if (!tryAttach()) {
      // Изчаквай supabase-init да dispatch-не „zd-supabase-ready"
      var ready = function () { tryAttach(); };
      window.addEventListener('zd-supabase-ready', ready, { once: true });
      // Fallback: poll до 4 секунди ако event не дойде
      var tries = 0;
      var poll = setInterval(function () {
        tries++;
        if (window.ZdSupabase) {
          clearInterval(poll);
          tryAttach();
        } else if (tries > 40) {
          clearInterval(poll);
        }
      }, 100);
    }

    // React на промени в session (sign-in/sign-out от друг tab)
    function watchAuthChanges() {
      if (!window.ZdSupabase) return;
      window.ZdSupabase.auth.onAuthStateChange(function (event) {
        if (event === 'SIGNED_OUT') {
          // Премахни dropdown-а — пагаждавай след reload
          location.reload();
        }
      });
    }
    if (window.ZdSupabase) watchAuthChanges();
    else window.addEventListener('zd-supabase-ready', watchAuthChanges, { once: true });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
