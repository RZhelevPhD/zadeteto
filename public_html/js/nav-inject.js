/* === HEADER SEARCH ICON + FOOTER REPORT BUTTON + LEGAL LINKS + GLOBAL A11Y ===
 *
 * Despite the name, this script is the de-facto "shared CSS injection" point
 * for the site. Every page loads it. So we use it to land site-wide
 * accessibility styles (focus-visible rings + prefers-reduced-motion guards)
 * in ONE file instead of editing 12 page <head>s.
 */
(function () {
  /* ---- GLOBAL ACCESSIBILITY CSS — injected into <head> as early as possible ----
     Runs synchronously when this script is parsed, before init() / DOMContentLoaded.
     This ensures focus rings render correctly on first interaction and reduced-motion
     takes effect before any animation has a chance to start. */
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
      /* Shared nav button styles — injected globally so all pages are consistent */
      '.nav-btn-partner{display:inline-flex;align-items:center;padding:9px 20px;background:#7c4dff;color:#fff!important;border-radius:10px;font-weight:600;text-decoration:none;font-size:13px;box-shadow:0 4px 14px rgba(124,77,255,0.2);transition:transform 0.2s,box-shadow 0.2s;}' +
      '.nav-btn-partner:hover{transform:translateY(-1px);box-shadow:0 6px 20px rgba(124,77,255,0.3);}' +
      '.nav-btn-partner:active{transform:scale(0.97);}' +
      '.nav-btn-login{display:inline-flex;align-items:center;padding:8px 18px;background:transparent;color:#1a103c!important;border:1.5px solid #ece8f3;border-radius:10px;font-weight:600;text-decoration:none;font-size:13px;transition:border-color 0.2s,background 0.2s;}' +
      '.nav-btn-login:hover{border-color:#7c4dff;background:rgba(124,77,255,0.04);}' +
      /* Skip-to-content link — hidden until focused via Tab */
      '.zd-skip-link{position:absolute;top:-50px;left:0;background:#7c4dff;color:#fff;padding:10px 18px;z-index:10000;font-size:14px;font-weight:600;border-radius:0 0 10px 0;text-decoration:none;transition:top 0.2s;}' +
      '.zd-skip-link:focus{top:0;}' +
      /* ---- HAMBURGER MENU (mobile ≤768px) ---- */
      '.zd-hamburger{display:none;background:none;border:none;cursor:pointer;padding:8px;z-index:101;-webkit-tap-highlight-color:transparent;}' +
      '.zd-hamburger svg{width:28px;height:28px;stroke:currentColor;stroke-width:2;stroke-linecap:round;}' +
      '.zd-hamburger .bar1,.zd-hamburger .bar2,.zd-hamburger .bar3{transition:transform 0.3s cubic-bezier(0.16,1,0.3,1),opacity 0.2s;}' +
      '@media(max-width:768px){' +
        '.zd-hamburger{display:flex;align-items:center;justify-content:center;color:#fff;}' +
        'nav.scrolled .zd-hamburger{color:#1a103c;}' +
        '.nav-links{position:fixed;top:0;right:-100%;width:280px;height:100vh;height:100dvh;background:#fff;flex-direction:column;align-items:stretch;padding:80px 24px 32px;gap:8px!important;z-index:100;box-shadow:-4px 0 24px rgba(0,0,0,0.1);transition:right 0.35s cubic-bezier(0.16,1,0.3,1);}' +
        '.nav-links.zd-open{right:0;}' +
        '.nav-links a.nav-link{display:block!important;color:#1a103c!important;text-shadow:none!important;font-size:16px;padding:12px 0;border-bottom:1px solid #ece8f3;}' +
        '.nav-links .nav-btn-partner,.nav-links .nav-btn-login{width:100%;justify-content:center;margin-top:8px;min-height:44px;font-size:14px;}' +
        '.zd-nav-backdrop{display:none;position:fixed;inset:0;background:rgba(0,0,0,0.3);z-index:99;-webkit-tap-highlight-color:transparent;}' +
        '.zd-nav-backdrop.zd-open{display:block;}' +
      '}' +
      /* Hamburger X animation when open */
      '.zd-hamburger.zd-open .bar1{transform:translateY(7px) rotate(45deg);}' +
      '.zd-hamburger.zd-open .bar2{opacity:0;}' +
      '.zd-hamburger.zd-open .bar3{transform:translateY(-7px) rotate(-45deg);}';
    // Insert as early as possible — at the top of <head> if it exists, else <html>
    var head = document.head || document.getElementsByTagName('head')[0] || document.documentElement;
    head.insertBefore(a11yStyle, head.firstChild);
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
      document.body.appendChild(backdrop);

      function toggleMenu() {
        var isOpen = navLinks.classList.toggle('zd-open');
        burger.classList.toggle('zd-open', isOpen);
        backdrop.classList.toggle('zd-open', isOpen);
        burger.setAttribute('aria-expanded', String(isOpen));
        document.body.style.overflow = isOpen ? 'hidden' : '';
      }
      function closeMenu() {
        navLinks.classList.remove('zd-open');
        burger.classList.remove('zd-open');
        backdrop.classList.remove('zd-open');
        burger.setAttribute('aria-expanded', 'false');
        document.body.style.overflow = '';
      }
      burger.addEventListener('click', toggleMenu);
      backdrop.addEventListener('click', closeMenu);
      // Close on nav link click
      navLinks.querySelectorAll('a').forEach(function(a) {
        a.addEventListener('click', closeMenu);
      });
      // Close on Escape
      document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') closeMenu();
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
          '.zd-footer-report-btn svg{width:18px;height:18px;}';
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
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
