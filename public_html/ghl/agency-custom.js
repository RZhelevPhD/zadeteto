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
  const SESSION_CACHE_TTL_MS = 60000; // 1 minute

  // Translation map: GHL English → Bulgarian
  // Keyed by `meta` attribute (more stable than ID or text)
  const TRANSLATIONS = {
    'dashboard':           'Начало',
    'conversations':       'Разговори',
    'contacts':            'Контакти',
    'calendars':           'Календари',
    'opportunities':       'Възможности',
    'payments':            'Плащания',
    'AI Agents':           'AI Агенти',
    'email-marketing':     'Онлайн маркетинг',
    'automation':          'Автоматизации',
    'sites':               'Уебсайтове',
    'memberships':         'Членства',
    'reputation':          'Отзиви',
    'reporting':           'Отчети',
    'settings':            'Настройки'
  };

  // In-page text translations (page headers, sub-tabs, filter chips,
  // common labels). Matched on exact trimmed textContent of text nodes.
  // Add new entries here as English strings are surfaced in the UI.
  const IN_PAGE_TRANSLATIONS = {
    // Top-level page headers (when shown as page titles inside content area)
    'Dashboard':           'Начало',
    'Conversations':       'Разговори',
    'Contacts':            'Контакти',
    'Calendars':           'Календари',
    'Opportunities':       'Възможности',
    'Payments':            'Плащания',
    'Reputation':          'Отзиви',
    'Reporting':           'Отчети',
    'Sites':               'Уебсайтове',
    'Memberships':         'Членства',
    'Email Marketing':     'Онлайн маркетинг',
    'Automation':          'Автоматизации',
    'Settings':            'Настройки',

    // Conversations sub-tabs
    'Manual Actions':      'Ръчни действия',
    'Snippets':            'Шаблони',
    'Trigger Links':       'Тригер линкове',
    'Analytics':           'Анализи',

    // Inbox filter chips
    'Team Inbox':          'Екипна поща',
    'Unread':              'Непрочетени',
    'All':                 'Всички',
    'Recents':             'Последни',
    'Starred':             'Със звезда',

    // Conversations empty states
    'All Caught Up!':                                              'Готово!',
    "You don't have any unread Team Inbox conversations right now.": 'В момента нямаш непрочетени разговори в екипната поща.',
    'View All Team Inbox Conversations':                           'Виж всички разговори в екипната поща',
    'No conversation selected':                                    'Няма избран разговор',
    'Select a conversation from the list to view contact details.': 'Избери разговор от списъка, за да видиш данните за контакта.',

    // Payments page (Плащания) — page header + sub-tabs
    'Invoices':                                                    'Фактури',
    'Invoices & Estimates':                                        'Фактури и оферти',
    'Documents & Contracts':                                       'Документи и договори',
    'Orders':                                                      'Поръчки',
    'Subscriptions':                                               'Абонаменти',
    'Payment Links':                                               'Линкове за плащане',
    'Transactions':                                                'Транзакции',
    'Products':                                                    'Продукти',
    'Create and manage all invoices generated for your business':  'Създавай и управлявай всички фактури на бизнеса',
    'Connect at least one payment gateway to start receiving payments': 'Свържи поне един метод за плащане, за да започнеш да приемаш плащания',
    'Integrate Payment Gateway':                                   'Свържи метод за плащане',
    'No invoices to show yet':                                     'Все още няма фактури',

    // "Get started with payments" sidebar popup
    'Get started with payments':                                   'Започни с плащанията',
    'Connect your payment provider':                               'Свържи метод за плащане',
    'Connect your accounting':                                     'Свържи счетоводство',
    'Connect Quickbooks':                                          'Свържи Quickbooks',
    'Control who can see your payments':                           'Контролирай кой вижда плащанията ти',
    'Set permissions for your team members':                       'Задай разрешения на членовете на екипа',

    // Common form / table labels
    'Start Date':          'От дата',
    'End Date':            'До дата',
    'Search':              'Търсене',
    'Filters':             'Филтри',
    'Invoice Name':        'Име на фактура',
    'Invoice Number':      'Номер на фактура',
    'Customer':            'Клиент',
    'Issue Date':          'Дата на издаване',
    'Amount':              'Сума',
    'Status':              'Статус',
    'Sort':                'Сортиране',
    'Tasks':               'Задачи',
    'More':                'Още',
    'Delete':              'Изтрий',
    'Import':              'Импорт',
    'Export':              'Експорт',
    'New':                 'Нов',
    'Add':                 'Добави',
    'Send':                'Изпрати',
    'Invite':              'Покани',
    'Invited':             'Поканен',
    'Generate':            'Генерирай',
    'Actions':             'Действия',
    'Branding':            'Брандиране',
    'Overview':            'Преглед',
    'Sections':            'Раздели',
    'Sources':             'Източници',
    'Listings':            'Списъци',
    'Requests':            'Заявки',
    'Widgets':             'Виджети',
    'Beta':                'Бета',
    'Page Size':           'Размер на страница',
    'Page 1 of 1':         'Страница 1 от 1',
    'Prev':                'Предишна',
    'Next':                'Следваща',
    'First':               'Първа',
    'Last':                'Последна',
    'Go':                  'Напред',
    'Get Started':         'Започни',

    // Common header / chrome (appears across all GHL pages)
    'Ask AI':                                                'Питай AI',
    'Notifications':                                         'Известия',
    'Quick Actions':                                         'Бързи действия',
    'Loading fresh data...':                                 'Зарежда се ново съдържание...',
    'Initializing...':                                       'Зарежда се...',
    'View Changelog':                                        'Виж промените',
    'Signout':                                               'Изход',
    'Support':                                               'Поддръжка',
    'Login As':                                              'Влез като',
    'Help me decide':                                        'Помогни ми да избера',
    "What's new":                                            'Какво е ново',
    'Contact updates':                                       'Промени по контакти',
    'SELECTED':                                              'ИЗБРАНО',
    'User not assigned':                                     'Няма зачислен потребител',
    'Schedule appointment':                                  'Запиши среща',
    'You need to add calendar to start scheduling appointments.':
      'Трябва да добавиш календар, за да започнеш да записваш срещи.',

    // Phone / call widget (appears across pages)
    'Keypad':                                                'Клавиатура',
    'Queue':                                                 'Опашка',
    'Voicemail':                                             'Гласова поща',
    'Connect a phone number':                                'Свържи телефонен номер',
    'Buy phone number':                                      'Купи телефонен номер',
    'Search Numbers':                                        'Търси номера',
    'No numbers found':                                      'Няма намерени номера',
    'Use your existing phone number':                        'Използвай съществуващ телефонен номер',
    "You'll need a phone number to get started.":            'За да започнеш, ще ти трябва телефонен номер.',
    'Outbound and inbound calls':                            'Изходящи и входящи разговори',
    'Outbound calls only. Test call in 60 seconds':          'Само изходящи разговори. Тестов разговор за 60 секунди',
    'Call, record, transcribe, automate follow-ups and more - all in one place.':
      'Звъни, записвай, транскрибирай, автоматизирай follow-up и още, всичко на едно място.',

    // Calendars page
    'Appointment List View':                                 'Списък със срещи',
    'Calendar Settings':                                     'Настройки на календара',
    'Calendar Updates':                                      'Промени по календара',
    'Calendar View':                                         'Изглед календар',
    'Go to Calendar Settings':                               'Към настройки на календара',
    'No Calendar Found!':                                    'Няма календар!',
    'Please create a new one or ask the admin to assign you to an existing calendar':
      'Създай нов или поискай админ да те зачисли към съществуващ календар',

    // Contacts page
    '0 Contacts':                                            '0 контакта',
    '0 Contacts Selected':                                   '0 избрани контакта',
    'Add Contact':                                           'Добави контакт',
    'Add smart list':                                        'Добави smart списък',
    'Add tags':                                              'Добави етикети',
    'Advanced filters':                                      'Разширени филтри',
    'Bulk Actions':                                          'Масови действия',
    'Business name':                                         'Име на бизнес',
    'Companies':                                             'Компании',
    'Contact name':                                          'Име на контакт',
    'Created (EEST)':                                        'Създаден (EEST)',
    'Last activity (EEST)':                                  'Последна активност (EEST)',
    'Email':                                                 'Имейл',
    'Phone':                                                 'Телефон',
    'Tags':                                                  'Етикети',
    'Smart Lists':                                           'Smart списъци',
    'Manage fields':                                         'Управление на полета',
    'Send email':                                            'Прати имейл',
    'Trigger automation':                                    'Стартирай автоматизация',
    "It's so lonely in here!":                               'Самотничко е тук!',
    'No Contacts in sight! Ready to create a fresh one?':    'Няма контакти! Готов ли си да създадеш един?',
    'Select all 0':                                          'Маркирай всички 0',

    // Opportunities page
    'Pipelines':                                             'Pipeline-и',

    // Payments page (extras beyond what's already in dictionary)
    '0 Invoice(s) Overdue':                                  '0 просрочени фактури',
    '0 Invoice(s) in Draft':                                 '0 фактури в чернова',
    '0 Invoice(s) in Due':                                   '0 фактури за плащане',
    '0 Invoice(s) received':                                 '0 получени фактури',
    'Abandoned Checkouts':                                   'Изоставени поръчки',
    'All Documents & Contracts':                             'Всички документи и договори',
    'All Invoices':                                          'Всички фактури',
    'Collections':                                           'Колекции',
    'Coupons':                                               'Купони',
    'Estimates':                                             'Оферти',
    'Gift Cards':                                            'Подаръчни карти',
    'Integrations':                                          'Интеграции',
    'Inventory':                                             'Наличност',
    'Recurring Invoices':                                    'Повтарящи се фактури',

    // AI Agents page — UI only, marketing copy is intentionally skipped
    'AI Agent':                                              'AI агент',
    'AI Agent · Auto-reply':                                 'AI агент · Авто-отговор',
    'AI Reputation Manager':                                 'AI мениджър отзиви',
    'Agent Logs':                                            'Логове на агенти',
    'Agent Templates':                                       'Шаблони за агенти',
    'Appointment Scheduler':                                 'Запис на срещи',
    'Appointments Booked':                                   'Записани срещи',
    'Availability':                                          'Достъпност',
    'Avg answer':                                            'Средно време за отговор',
    'Booked':                                                'Записан',
    'Booking confirmed':                                     'Срещата е потвърдена',
    'Calls':                                                 'Разговори',
    'Calls handled':                                         'Обработени разговори',
    'Carrier':                                               'Оператор',
    'Customers Every Day':                                   'Клиенти всеки ден',
    'Deploy now →':                                          'Стартирай сега →',
    'End':                                                   'Край',
    'Estimate':                                              'Оферта',
    'Get Started →':                                         'Започни →',
    'Employee Availability':                                 'Достъпност на служители',
    'Find the right agents for your business':               'Намери правилните агенти за бизнеса',

    // Marketing (Онлайн маркетинг) page
    'Ad Manager':                                            'Реклама мениджър',
    'Affiliate':                                             'Партньорска програма',
    'Affiliate Manager':                                     'Партньорски мениджър',
    'Attach file':                                           'Прикачи файл',
    'Brand Boards':                                          'Брандови табла',
    'Bulk Scheduling with CSV':                              'Масово планиране с CSV',
    'Campaign':                                              'Кампания',
    'Community':                                             'Общност',
    'Countdown Timers':                                      'Таймери за обратно броене',
    'Create Evergreen Post':                                 'Създай Evergreen пост',
    'Create RSS Post':                                       'Създай RSS пост',
    'Create Recurring Post':                                 'Създай Повтарящ пост',
    'Emails':                                                'Имейли',
    'Evergreen Queue Post':                                  'Evergreen опашка пост',
    'Feedback':                                              'Обратна връзка',
    'From':                                                  'От',
    'Generate Feed from RSS Post':                           'Генерирай feed от RSS пост',
    'Grow faster with a smarter social media calendar':      'Расти по-бързо с умен календар за социални медии',
    'Have any ideas, troubles or questions?':                'Имаш идея, проблем или въпрос?',
    'Keep your social channels active by scheduling posts!': 'Поддържай социалните канали активни с планиране на постове!',
    'Keep your social presence active by publishing posts across multiple social media networks at once!':
      'Поддържай социалното си присъствие активно с публикуване в множество мрежи наведнъж!',
    'Marketing':                                             'Маркетинг',
    'Media':                                                 'Медии',
    'Payout':                                                'Изплащане',
    'Prospecting':                                           'Привличане',
    'Recurring Post':                                        'Повтарящ пост',
    'Save time by scheduling posts':                         'Спести време с планиране на постове',
    'Schedule Now':                                          'Планирай сега',
    'Select the social accounts you want to connect:':       'Избери социалните мрежи за свързване:',
    'Send Message':                                          'Изпрати съобщение',
    'Set up posts that automatically repeat on a schedule to maintain consistent engagement':
      'Настрой постове, които се повтарят по график за постоянна ангажираност',
    'Social Planner':                                        'Социален планер',
    'Subject':                                               'Тема',
    'Talk to us!':                                           'Свържи се с нас!',
    'Upload A CSV':                                          'Качи CSV',
    'Automatically create and share posts from your favorite RSS feeds to stay current':
      'Автоматично създавай и публикувай постове от любимите си RSS feed-и',
    'Import and schedule multiple posts at once using CSV files for efficient content management':
      'Импортирай и планирай множество постове наведнъж с CSV файлове',
    'Create a library of timeless content that automatically recycles to keep your feed fresh':
      'Създай библиотека с вечнозелено съдържание, което автоматично се рециклира',

    // Automation page
    'Automation Updates':                                    'Промени по автоматизациите',
    'Global Workflow Settings':                              'Глобални настройки на workflow',
    'Workflows':                                             'Workflow-и',

    // Sites (Сайтове и страници) page
    'All your funnels and folders will live here. Start by creating your first Funnel':
      'Всички твои фунии и папки ще са тук. Започни с първата си фуния',
    'Analyze':                                               'Анализ',
    'Blogs':                                                 'Блогове',
    'Branded Mobile App':                                    'Брандирано мобилно приложение',
    'Build funnels to generate leads, appointments and receive payment':
      'Изгради фунии за лийдове, срещи и плащания',
    'Build with AI':                                         'Изгради с AI',
    'Builder':                                               'Билдер',
    'Chat Widget':                                           'Чат виджет',
    'Client Portal':                                         'Клиентски портал',
    'Create Folder':                                         'Създай папка',
    'Forms':                                                 'Формуляри',
    'Funnels':                                               'Фунии',
    'Home':                                                  'Начало',
    'Last Updated':                                          'Последна промяна',
    'Name':                                                  'Име',
    'New Funnel':                                            'Нова фуния',
    'QR Codes':                                              'QR кодове',
    'Quizzes':                                               'Тестове',
    'Search for Funnels':                                    'Търси фунии',
    'Start by creating a funnel':                            'Започни със създаване на фуния',
    'Stores':                                                'Магазини',
    'Submissions':                                           'Заявки',
    'Surveys':                                               'Анкети',
    'Webinars':                                              'Уебинари',
    'Websites':                                              'Уебсайтове',

    // Memberships page
    'Client Portal App':                                     'Клиентско портал приложение',
    'Client portal URL':                                     'URL на клиентски портал',
    'Communities':                                           'Общности',
    'Course Builder':                                        'Курс билдер',
    'Courses':                                               'Курсове',
    'Creating a protected online gateway for client interactions':
      'Създаване на защитен онлайн портал за работа с клиенти',
    'Credentials':                                           'Данни за вход',
    'Domain setup':                                          'Настройка на домейн',
    'Email notifications':                                   'Имейл известия',
    'Generate magic link':                                   'Генерирай магически линк',
    'Groups':                                                'Групи',
    'Invite to client portal':                               'Покани в клиентския портал',
    'Launch your white-label app with courses and communities':
      'Стартирай white-label приложение с курсове и общности',
    'Manage your client portal activities':                  'Управление на дейностите в клиентския портал',
    'Offers':                                                'Оферти',
    'Send login email':                                      'Прати имейл за вход',
    'Users':                                                 'Потребители',
    'What is a client portal?':                              'Какво е клиентски портал?',
    'Your Brand. Your App.':                                 'Твоят бранд. Твоето приложение.',
    'Your clients can log in anytime to access courses and manage affiliate payouts.':
      'Клиентите ти могат да влизат по всяко време и да управляват плащания.',

    // Reputation (Отзиви) page
    'Begin sending review requests.':                        'Започни да изпращаш заявки за отзиви.',
    'Competitor Analysis':                                   'Анализ на конкуренти',
    'Configure Reviews AI':                                  'Настрой AI за отзиви',
    'Connect Google Business Profile':                       'Свържи Google Business Profile',
    'Connect more platforms':                                'Свържи още платформи',
    'Create Widget':                                         'Създай виджет',
    'Create a Collector':                                    'Създай колектор',
    'Create a Review Widget':                                'Създай виджет за отзиви',
    'Create one now! You can easily gather responses and send out review requests.':
      'Създай го сега! Лесно ще събираш отговори и ще изпращаш заявки за отзиви.',
    'DD / MM / YYYY':                                        'ДД / ММ / ГГГГ',
    'Embed the widget on your site to display authentic customer testimonials.':
      'Постави виджета на сайта си, за да показваш реални отзиви от клиенти.',
    'Finish all these Steps to Set up Your Reputation Dashboard':
      'Завърши тези стъпки, за да настроиш таблото си за отзиви',
    'GBP Optimization':                                      'GBP оптимизация',
    'Gather more customer feedback to enhance your online reputation.':
      'Събери повече обратна връзка от клиенти, за да подобриш онлайн репутацията си.',
    'Hi Rusi':                                               'Здравей, Руси',
    'Measure on-site review visibility, impressions, and submissions through widgets.':
      'Измервай видимостта, импресиите и подаванията на отзиви през виджети.',
    'Monitor how your ratings change over time. Start collecting feedback to gain insights.':
      'Следи как се променят оценките ти. Започни да събираш обратна връзка за прозрения.',
    'Monitor review request volume and conversion across Email, SMS, and WhatsApp.':
      'Следи обема и конверсията на заявки за отзиви в Имейл, SMS и WhatsApp.',
    'My Stats':                                              'Моите статистики',
    'No responses yet.':                                     'Все още няма отговори.',
    'No video reviews yet.':                                 'Все още няма видео отзиви.',
    'No widget activity detected.':                          'Не е засечена активност на виджет.',
    'Once reviews start coming in, you can manage and respond here to foster trust.':
      'Когато отзивите започнат да идват, ще можеш да отговаряш тук и да градиш доверие.',
    'QR code scans':                                         'Сканирания на QR код',
    'Reviews':                                               'Отзиви',
    'Review request':                                        'Заявка за отзив',
    'Review response':                                       'Отговор на отзив',
    'Review widget':                                         'Виджет за отзив',
    'Reviews and ratings trend':                             'Тренд на отзиви и оценки',
    'Send First Review Request':                             'Изпрати първа заявка за отзив',
    'Send Review Request':                                   'Изпрати заявка за отзив',
    'Send your 1st Review Request':                          'Изпрати първата си заявка за отзив',
    'Setup Review Link':                                     'Настрой линк за отзив',
    'Skip Onboarding':                                       'Пропусни въведението',
    'Start Collecting Reviews':                              'Започни да събираш отзиви',
    'Track customer QR scans from physical touchpoints leading to reviews.':
      'Следи сканиранията на QR код, които водят до отзиви.',
    'Track how customers record, submit, and engage with your video testimonials.':
      'Следи как клиентите записват, изпращат и взаимодействат с видео отзиви.',
    'Track how your ratings and review volume change over time.':
      'Следи как се променят оценките и обемът отзиви.',
    'Track your review performance.':                        'Следи представянето на отзивите си.',
    'Video Testimonials':                                    'Видео отзиви',
    'Video testimonials':                                    'Видео отзиви',
    'View response coverage, response time, and how reviews are handled across platforms.':
      'Виж покритието и времето за отговор по платформи.',

    // Reports page
    'Add Reports Insights':                                  'Добави статистики',
    'Appointment Report':                                    'Доклад срещи',
    'Attribution Report':                                    'Доклад атрибуция',
    'Call Report':                                           'Доклад разговори',
    'Create Multi-Page Reports':                             'Създай многостранични доклади',
    'Custom Reports':                                        'Персонализирани доклади',
    'Facebook Ads Report':                                   'Доклад Facebook реклами',
    'Local Marketing Audit':                                 'Локален маркетинг одит',
    'Looking to Track Key Client Metrics at a glance?':      'Искаш ли да следиш ключови клиентски метрики наведнъж?',
    'New Report':                                            'Нов доклад',
    'Reports Overview':                                      'Преглед на доклади',
    'Schedule the Report to your Team Members and Stakeholders':
      'Планирай доклада за членовете на екипа и инвесторите',
    'Try Dashboards':                                        'Опитай таблата',

    // Common UI
    'Select all':          'Маркирай всички'
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
    // Guard: do nothing if we're not on an active ZaDeteto subaccount.
    // The MutationObserver fires on every DOM change including SPA navigation
    // to agency view, where this function would otherwise misapply
    // data-zd-locked to agency sidebar items.
    if (document.documentElement.dataset.zdActive !== 'true') return;

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

    // 5. Walk in-page text nodes and translate known strings (headers,
    //    sub-tabs, filter chips, common labels). Scoped to skip inputs,
    //    contenteditable, scripts, styles, and our own injected text.
    translatePageText();

    // 6. Replace the whitelabel agency logo (123marketing.app) with the
    //    ZaDeteto wordmark. Re-runs on every SPA navigation via the
    //    MutationObserver so newly-mounted logo elements get rewritten too.
    replaceAgencyLogo();
  }

  function replaceAgencyLogo() {
    const logos = document.querySelectorAll('img');
    logos.forEach(img => {
      if (img.dataset.zdLogoReplaced) return;
      const src = img.getAttribute('src') || '';
      // Strict targeting — earlier version matched any msgsndr / GHL CDN
      // URL and accidentally replaced every menu / icon image with the
      // wordmark. Now we require BOTH a CDN host match AND an explicit
      // 'logo' indicator in the URL, OR the image being inside a
      // container whose class clearly says it's a logo slot.
      const looksLikeLogoSrc = /(\/logo[\.\-_/]|_logo\.|whitelabel_logo|companylogo|agency-logo)/i.test(src);
      const inLogoContainer = !!img.closest('[class*="agency-logo"], [class*="sidebar-logo"], [class*="brand-logo"], [class*="header-logo"], [class*="company-logo"], [id*="agency-logo"], [id*="company-logo"]');
      if (looksLikeLogoSrc || inLogoContainer) {
        img.src = 'https://zadeteto.com/brand_assets/zadeteto-ghl-wordmark.svg';
        img.alt = 'Национален Регистър За Детето';
        img.dataset.zdLogoReplaced = 'true';
        // Wordmark is wider than the square original logo — adjust
        // styling so it fits the agency sidebar header without distortion.
        img.style.maxHeight = '48px';
        img.style.width = 'auto';
        img.style.objectFit = 'contain';
      }
    });
  }

  function translatePageText() {
    const walker = document.createTreeWalker(
      document.body,
      NodeFilter.SHOW_TEXT,
      {
        acceptNode(node) {
          const parent = node.parentElement;
          if (!parent) return NodeFilter.FILTER_REJECT;
          const tag = parent.tagName;
          if (tag === 'SCRIPT' || tag === 'STYLE' ||
              tag === 'INPUT' || tag === 'TEXTAREA' ||
              tag === 'NOSCRIPT') {
            return NodeFilter.FILTER_REJECT;
          }
          // Skip user-editable content and our own injected text
          if (parent.closest('[contenteditable="true"]')) {
            return NodeFilter.FILTER_REJECT;
          }
          if (parent.classList && (
              parent.classList.contains('zd-nav-subtext') ||
              parent.classList.contains('zd-premium-divider-label'))) {
            return NodeFilter.FILTER_REJECT;
          }
          const trimmed = node.textContent.trim();
          if (!trimmed) return NodeFilter.FILTER_REJECT;
          if (!IN_PAGE_TRANSLATIONS[trimmed]) return NodeFilter.FILTER_REJECT;
          return NodeFilter.FILTER_ACCEPT;
        }
      }
    );

    let node;
    while ((node = walker.nextNode())) {
      const original = node.textContent.trim();
      const translated = IN_PAGE_TRANSLATIONS[original];
      if (translated && original !== translated) {
        node.textContent = node.textContent.replace(original, translated);
      }
    }
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

    // Re-apply on URL change (SPA route change).
    // Also handle deactivation: if user navigates from a whitelisted
    // subaccount to agency view (or to a different subaccount that is
    // NOT this partner), strip data-zd-active so our CSS stops applying
    // and the user sees default GHL — not a half-broken Bulgarian agency
    // view with misapplied padlocks.
    let lastPath = window.location.pathname;
    const originalLocationId = locationId;
    setInterval(() => {
      if (window.location.pathname === lastPath) return;
      lastPath = window.location.pathname;
      const currentLocationId = getLocationId();
      if (currentLocationId === originalLocationId) {
        // Still on the same partner subaccount (or returning to it).
        // Re-set the activation gate in case it was previously removed,
        // then re-apply translations and locks.
        document.documentElement.setAttribute('data-zd-active', 'true');
        document.documentElement.setAttribute('lang', 'bg');
        scheduleApply(partner, unlockedMetas, activeAddons);
      } else {
        // Navigated to agency view or a different subaccount — deactivate.
        // A full page reload on the new context will re-bootstrap us
        // properly if it's also a whitelisted partner.
        document.documentElement.removeAttribute('data-zd-active');
        document.documentElement.removeAttribute('lang');
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
