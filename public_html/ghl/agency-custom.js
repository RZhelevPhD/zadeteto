/* ================================================================
   ZaDeteto — Agency-level Custom JavaScript for GoHighLevel
   ================================================================
   
   Paste this into: Settings → Company → Custom JavaScript (Agency)
   
   WHAT THIS FILE DOES:
   1. On every GHL page load, extracts the current Location ID from URL
   2. Fetches https://zadeteto.com/ghl-locations.json
   3. If Location ID matches an entry → activates the ZaDeteto layer:
      - Sets <html data-zd-active="true"> (CSS hook)
      - Translates sidebar text to Bulgarian
      - Marks tier-locked items with data-zd-locked="true"
      - Marks AI Agents with data-zd-locked-addon="true" (unless activated)
      - Injects subtext under locked items
      - Injects "Премиум" divider
      - Binds click handlers that show upgrade/contact modals
   4. If Location ID does NOT match → exits silently
   
   ARCHITECTURE NOTES:
   - GHL is a SPA. The sidebar re-renders when switching between locations
     or sometimes during navigation. We use MutationObserver to re-apply
     translations whenever the DOM changes.
   - We cache the JSON in sessionStorage for the session to avoid
     re-fetching on every page navigation.
   - All text replacement is non-destructive — we don't remove GHL's
     original spans, we just rewrite textContent.
   ================================================================ */

(function() {
  'use strict';

  // ----------------------------------------------------------------
  // CONFIG
  // ----------------------------------------------------------------
  const WHITELIST_URL = 'https://zadeteto.com/ghl-locations.json';
  const SESSION_CACHE_KEY = 'zd_ghl_whitelist_v1';
  const SESSION_CACHE_TTL_MS = 60_000; // 1 minute

  // Translation map: GHL English → Bulgarian
  // Keyed by `meta` attribute (more stable than ID or text)
  const TRANSLATIONS = {
    'conversations':       'Разговори',
    'contacts':            'Контакти',
    'calendars':           'Календари',
    'opportunities':       'Възможности',
    'payments':            'Плащания',
    'AI Agents':           'AI Агенти',
    'email-marketing':     'Имейл маркетинг',
    'automation':          'Автоматизации',
    'sites':               'Сайтове',
    'memberships':         'Членства',
    'reputation':          'Репутация',
    'reporting':           'Отчети',
    'settings':            'Настройки'
  };

  // Subtext shown under locked items (one-line tagline)
  const SUBTEXTS = {
    'opportunities':       'Pipeline за всяко запитване',
    'AI Agents':           'Отговаря на запитвания 24/7',
    'email-marketing':     'Кампании с готови шаблони',
    'automation':          'Напомняния, имейли, SMS',
    'sites':               'Landing страници и фунии',
    'memberships':         'Курсове и онлайн уроци',
    'reputation':          'Отзиви и Google отговори',
    'reporting':           'Записвания, удържане, приходи',
    'payments':            'Онлайн такси и абонаменти'
  };

  // Which `meta` values are unlocked by each tier
  // (Used as fallback if whitelist defaults are missing)
  const TIER_UNLOCKS = {
    'verified':  ['conversations', 'contacts', 'settings'],
    'trusted':   ['conversations', 'contacts', 'calendars', 'opportunities', 'settings'],
    'premium':   ['conversations', 'contacts', 'calendars', 'opportunities',
                  'email-marketing', 'automation', 'sites', 'memberships',
                  'reputation', 'reporting', 'payments', 'settings']
  };

  // Which `meta` values are add-ons (always visible, separately gated)
  const ADDON_METAS = ['AI Agents'];
  // Map addon meta → internal addon key (for whitelist matching)
  const ADDON_KEYS = {
    'AI Agents': 'ai_agents'
  };

  // Modal copy per feature
  const MODAL_CONTENT = {
    'opportunities': {
      icon: '🎯',
      headline: 'Не губи нито един потенциален клиент',
      body: 'Виж всяко запитване от родител в pipeline. Знай кой чака отговор и кой е готов да запази час.',
      benefits: [
        'Pipeline за всеки етап на запитването',
        'Напомняния за follow-up',
        'Виж кои деца чакат среща'
      ],
      tier: 'trusted'
    },
    'email-marketing': {
      icon: '📧',
      headline: 'Достигни всички родители с един клик',
      body: 'Изпращай бюлетини, обяви за нови курсове и сезонни кампании — без да отваряш Gmail.',
      benefits: [
        'Готови шаблони на български',
        'Сегментиране по възраст и курс',
        'Отчети за отворени и кликове'
      ],
      tier: 'premium'
    },
    'automation': {
      icon: '⚡',
      headline: 'Автоматизирай повторящите се задачи',
      body: 'Изпращай напомняния, благодарствени съобщения и follow-up автоматично. Спестяваш часове всяка седмица.',
      benefits: [
        'Автоматични напомняния за час',
        'Welcome поредица за нови родители',
        'Reactivation на спящи контакти'
      ],
      tier: 'premium'
    },
    'sites': {
      icon: '🌐',
      headline: 'Превърни посетители в записани часове',
      body: 'Конструирай страница за записване за минути — с форми, разписания и плащане. Без програмист.',
      benefits: [
        'Готови шаблони за студия и школи',
        'Онлайн запис и плащане',
        'Свързано с твоя календар и контакти'
      ],
      tier: 'premium'
    },
    'memberships': {
      icon: '🎓',
      headline: 'Превърни курсовете си в членска програма',
      body: 'Продавай абонаменти, онлайн уроци и материали в защитена зона за родители.',
      benefits: [
        'Месечни и годишни абонаменти',
        'Заключено съдържание и видеа',
        'Автоматично подновяване и фактури'
      ],
      tier: 'premium'
    },
    'reputation': {
      icon: '⭐',
      headline: 'Превърни доволните родители в нови клиенти',
      body: 'Автоматично искай отзиви в Google и Facebook след всеки курс. Повече звезди — повече записвания.',
      benefits: [
        'Покани за отзив след заниманието',
        'Следене на оценки от всички платформи',
        'Бърз отговор на негативни коментари'
      ],
      tier: 'premium'
    },
    'reporting': {
      icon: '📊',
      headline: 'Виж кое работи и кое не — на едно място',
      body: 'Приходи, посещения, конверсии и задържане на родители. Реални числа, без таблици и догадки.',
      benefits: [
        'Табла за приходи и записвания',
        'Източници на нови контакти',
        'Сравнение по месеци и курсове'
      ],
      tier: 'premium'
    },
    'payments': {
      icon: '💳',
      headline: 'Приемай плащания директно от профила',
      body: 'Родителите плащат онлайн. Парите идват директно при теб, без посредници и без забавяне.',
      benefits: [
        'Карти, Apple Pay, Google Pay',
        'Автоматични фактури',
        'Месечни абонаменти за курсове'
      ],
      tier: 'premium'
    },
    // Add-on — different copy, different CTA
    'AI Agents': {
      icon: '🤖',
      headline: 'AI асистент, който отговаря вместо теб',
      body: 'Отговаряй на родители 24/7 — за разписания, цени и записване. Когато спиш, AI работи за теб.',
      benefits: [
        'Отговори на български в твоя стил',
        'Записва часове директно в календара',
        'Прехвърля сложни случаи към теб'
      ],
      isAddon: true
    }
  };

  // Tier display names (for modal CTA text)
  const TIER_NAMES = {
    'trusted':  'Доверен',
    'premium':  'Премиум'
  };

  // ----------------------------------------------------------------
  // UTILITIES
  // ----------------------------------------------------------------

  // Extract Location ID from URL pattern /v2/location/{ID}/...
  function getLocationId() {
    const match = window.location.pathname.match(/\/v2\/location\/([^\/]+)/);
    return match ? match[1] : null;
  }

  // Fetch whitelist with sessionStorage caching
  async function getWhitelist() {
    // Check cache
    try {
      const cached = sessionStorage.getItem(SESSION_CACHE_KEY);
      if (cached) {
        const parsed = JSON.parse(cached);
        if (Date.now() - parsed.fetchedAt < SESSION_CACHE_TTL_MS) {
          return parsed.data;
        }
      }
    } catch (e) { /* ignore */ }

    // Fetch fresh
    try {
      const response = await fetch(WHITELIST_URL, { cache: 'no-cache' });
      if (!response.ok) throw new Error('Whitelist fetch failed: ' + response.status);
      const data = await response.json();
      try {
        sessionStorage.setItem(SESSION_CACHE_KEY, JSON.stringify({
          data: data,
          fetchedAt: Date.now()
        }));
      } catch (e) { /* ignore */ }
      return data;
    } catch (err) {
      console.warn('[ZaDeteto] Whitelist fetch error — falling back to default GHL:', err);
      return null;
    }
  }

  // Get effective tier and addons for a Location ID
  function resolvePartner(whitelist, locationId) {
    if (!whitelist || !whitelist.locations || !whitelist.locations[locationId]) {
      return null;
    }
    const loc = whitelist.locations[locationId];
    const defaults = whitelist.defaults || {};
    return {
      name: loc.name || 'Партньор',
      tier: loc.tier || defaults.tier || 'verified',
      addons: loc.addons || defaults.addons || []
    };
  }

  // Build the set of meta values that should be UNLOCKED for this partner
  function buildUnlockedSet(whitelist, partner) {
    const tierTable = (whitelist && whitelist.defaults && whitelist.defaults.unlocked_by_tier)
      || TIER_UNLOCKS;
    const tierUnlocked = tierTable[partner.tier] || [];
    return new Set(tierUnlocked);
  }

  // Build the set of activated add-ons for this partner
  function buildAddonSet(partner) {
    return new Set(partner.addons || []);
  }

  // ----------------------------------------------------------------
  // APPLICATION
  // ----------------------------------------------------------------

  function applyTranslationsAndLocks(partner, unlockedMetas, activeAddons) {
    const items = document.querySelectorAll('[id^="sb_"]');

    items.forEach(item => {
      const meta = item.getAttribute('meta');
      if (!meta) return;

      // 1. Translate the title text
      const titleEl = item.querySelector('.nav-title');
      if (titleEl && TRANSLATIONS[meta]) {
        // Only rewrite if not already in Bulgarian (avoid loop with observer)
        if (titleEl.textContent.trim() !== TRANSLATIONS[meta]) {
          titleEl.textContent = TRANSLATIONS[meta];
        }
      }

      // 2. Decide lock state
      const isAddon = ADDON_METAS.indexOf(meta) !== -1;
      const addonKey = ADDON_KEYS[meta];
      const addonActivated = addonKey && activeAddons.has(addonKey);
      const isTierUnlocked = unlockedMetas.has(meta);

      // Clear any existing lock flags first
      item.removeAttribute('data-zd-locked');
      item.removeAttribute('data-zd-locked-addon');

      if (isAddon) {
        // Add-on logic — separate from tier
        if (!addonActivated) {
          item.setAttribute('data-zd-locked-addon', 'true');
          item.setAttribute('data-zd-feature', meta);
        }
      } else {
        // Tier logic
        if (!isTierUnlocked) {
          item.setAttribute('data-zd-locked', 'true');
          item.setAttribute('data-zd-feature', meta);
        }
      }

      // 3. Inject subtext under title for locked items
      const isLocked = item.hasAttribute('data-zd-locked') ||
                       item.hasAttribute('data-zd-locked-addon');
      if (isLocked && SUBTEXTS[meta] && titleEl && !item.querySelector('.zd-nav-subtext')) {
        // Wrap title + subtext in a flex column container
        const wrap = document.createElement('div');
        wrap.className = 'zd-nav-textblock';
        const subtext = document.createElement('div');
        subtext.className = 'zd-nav-subtext';
        subtext.textContent = SUBTEXTS[meta];
        titleEl.parentNode.insertBefore(wrap, titleEl);
        wrap.appendChild(titleEl);
        wrap.appendChild(subtext);
      }
    });

    // 4. Inject "Премиум" divider before the first Premium-tier locked item
    injectPremiumDivider(partner, unlockedMetas);
  }

  function injectPremiumDivider(partner, unlockedMetas) {
    // Already injected? Skip.
    if (document.querySelector('.zd-premium-divider')) return;

    // Find the first item that is premium-locked (i.e., locked AND only
    // unlocks at premium tier)
    const premiumOnlyMetas = ['email-marketing', 'automation', 'sites',
                              'memberships', 'reputation', 'reporting', 'payments'];

    for (const meta of premiumOnlyMetas) {
      const item = document.querySelector(`[meta="${meta}"]`);
      if (item && item.hasAttribute('data-zd-locked')) {
        // Build the divider
        const divider = document.createElement('div');
        divider.className = 'zd-premium-divider';
        divider.innerHTML =
          '<span class="zd-premium-divider-icon">🔒</span>' +
          '<span class="zd-premium-divider-label">Премиум</span>';
        item.parentNode.insertBefore(divider, item);
        break;
      }
    }
  }

  // ----------------------------------------------------------------
  // MODAL
  // ----------------------------------------------------------------

  function buildModal() {
    if (document.getElementById('zd-modal-overlay')) return;

    const overlay = document.createElement('div');
    overlay.id = 'zd-modal-overlay';
    overlay.innerHTML = `
      <div id="zd-modal" role="dialog" aria-modal="true">
        <button class="zd-modal-close" aria-label="Затвори">✕</button>
        <div class="zd-modal-icon-wrap">
          <div class="zd-modal-icon-tile">
            <span id="zd-modal-icon">🔒</span>
            <div class="zd-modal-icon-badge" id="zd-modal-icon-badge">🔒</div>
          </div>
        </div>
        <h2 id="zd-modal-headline">…</h2>
        <p id="zd-modal-body">…</p>
        <ul id="zd-modal-benefits"></ul>
        <div class="zd-modal-actions">
          <button id="zd-modal-cta-primary">…</button>
          <button id="zd-modal-cta-secondary">По-късно</button>
        </div>
        <p class="zd-modal-footer">
          Имаш въпрос? Пиши ни на
          <a href="mailto:partner@zadeteto.com">partner@zadeteto.com</a>
        </p>
      </div>
    `;
    document.body.appendChild(overlay);

    // Close handlers
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) closeModal();
    });
    overlay.querySelector('.zd-modal-close').addEventListener('click', closeModal);
    overlay.querySelector('#zd-modal-cta-secondary').addEventListener('click', closeModal);

    // ESC key
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && overlay.classList.contains('zd-open')) {
        closeModal();
      }
    });
  }

  function openModal(meta, partner, locationId) {
    buildModal();
    const content = MODAL_CONTENT[meta];
    if (!content) return;

    const overlay = document.getElementById('zd-modal-overlay');
    const isAddon = !!content.isAddon;

    // Populate content
    document.getElementById('zd-modal-icon').textContent = content.icon;
    document.getElementById('zd-modal-headline').textContent = content.headline;
    document.getElementById('zd-modal-body').textContent = content.body;

    const badge = document.getElementById('zd-modal-icon-badge');
    badge.classList.toggle('zd-addon-badge', isAddon);
    badge.textContent = isAddon ? '✦' : '🔒';

    const benefitsList = document.getElementById('zd-modal-benefits');
    benefitsList.innerHTML = '';
    content.benefits.forEach(text => {
      const li = document.createElement('li');
      li.innerHTML = `<span class="zd-benefit-check">✓</span><span>${text}</span>`;
      benefitsList.appendChild(li);
    });

    // Primary CTA — different for tier vs addon
    const cta = document.getElementById('zd-modal-cta-primary');
    if (isAddon) {
      cta.textContent = 'Свържи се за оферта →';
      cta.onclick = () => {
        const subject = encodeURIComponent(`AI Агенти за ${partner.name}`);
        const body = encodeURIComponent(
          `Здравейте,\n\nИнтересувам се от активиране на AI Агенти за моя профил (${partner.name}).\n\nLocation ID: ${locationId}\n\nПоздрави,`
        );
        window.open(`mailto:partner@zadeteto.com?subject=${subject}&body=${body}`, '_blank');
      };
    } else {
      const tierName = TIER_NAMES[content.tier] || 'по-висок план';
      cta.textContent = `Обнови до ${tierName} →`;
      cta.onclick = () => {
        const url = `https://zadeteto.com/crm-upgrade?feature=${encodeURIComponent(meta)}&from_tier=${encodeURIComponent(partner.tier)}&location=${encodeURIComponent(locationId)}`;
        // Use top-level navigation so it works inside GHL iframe context
        try {
          window.top.location.href = url;
        } catch (e) {
          window.open(url, '_blank', 'noopener');
        }
      };
    }

    overlay.classList.add('zd-open');
  }

  function closeModal() {
    const overlay = document.getElementById('zd-modal-overlay');
    if (overlay) overlay.classList.remove('zd-open');
    // Remove any active shake state
    document.querySelectorAll('[data-zd-shake]').forEach(el => {
      el.removeAttribute('data-zd-shake');
    });
  }

  // ----------------------------------------------------------------
  // CLICK HANDLER — intercept clicks on locked items
  // ----------------------------------------------------------------

  function bindClickHandlers(partner, locationId) {
    if (document.body.hasAttribute('data-zd-clicks-bound')) return;
    document.body.setAttribute('data-zd-clicks-bound', 'true');

    document.body.addEventListener('click', (e) => {
      // Find ancestor sb_* item
      const item = e.target.closest('[id^="sb_"]');
      if (!item) return;

      const isLocked = item.hasAttribute('data-zd-locked') ||
                       item.hasAttribute('data-zd-locked-addon');
      if (!isLocked) return;

      // Block navigation
      e.preventDefault();
      e.stopPropagation();

      // Trigger shake
      item.setAttribute('data-zd-shake', 'true');
      setTimeout(() => item.removeAttribute('data-zd-shake'), 500);

      // Open modal for this feature
      const meta = item.getAttribute('data-zd-feature') || item.getAttribute('meta');
      openModal(meta, partner, locationId);
    }, true); // capture phase — beat GHL's own handlers
  }

  // ----------------------------------------------------------------
  // OBSERVER — re-apply on DOM changes (SPA navigation)
  // ----------------------------------------------------------------

  let applyTimer = null;
  function scheduleApply(partner, unlockedMetas, activeAddons) {
    clearTimeout(applyTimer);
    applyTimer = setTimeout(() => {
      applyTranslationsAndLocks(partner, unlockedMetas, activeAddons);
    }, 80);
  }

  function startObserver(partner, unlockedMetas, activeAddons) {
    const observer = new MutationObserver(() => {
      scheduleApply(partner, unlockedMetas, activeAddons);
    });
    observer.observe(document.body, {
      childList: true,
      subtree: true,
      characterData: false
    });
  }

  // ----------------------------------------------------------------
  // MAIN
  // ----------------------------------------------------------------

  async function main() {
    const locationId = getLocationId();
    if (!locationId) {
      // Not on a sub-account page (probably agency-level) — do nothing
      return;
    }

    const whitelist = await getWhitelist();
    if (!whitelist) return; // fetch failed — fall back gracefully

    const partner = resolvePartner(whitelist, locationId);
    if (!partner) {
      // This Location is not a ZaDeteto partner — do nothing
      return;
    }

    // Activate
    document.documentElement.setAttribute('data-zd-active', 'true');
    document.documentElement.setAttribute('lang', 'bg');

    const unlockedMetas = buildUnlockedSet(whitelist, partner);
    const activeAddons = buildAddonSet(partner);

    // Initial application (may run before sidebar is mounted)
    applyTranslationsAndLocks(partner, unlockedMetas, activeAddons);

    // Bind clicks and start observer for ongoing SPA navigation
    bindClickHandlers(partner, locationId);
    startObserver(partner, unlockedMetas, activeAddons);

    // Re-apply on URL change (SPA route change)
    let lastPath = window.location.pathname;
    setInterval(() => {
      if (window.location.pathname !== lastPath) {
        lastPath = window.location.pathname;
        scheduleApply(partner, unlockedMetas, activeAddons);
      }
    }, 500);

    console.info('[ZaDeteto] Activated for', partner.name, '— tier:', partner.tier);
  }

  // Run as soon as possible
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', main);
  } else {
    main();
  }

})();
