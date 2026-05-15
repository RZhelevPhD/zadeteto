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
    // Note: no 'dashboard' entry — the native Dashboard sidebar item is
    // hidden by CSS Zone 3. The "Начало" custom menu link (created
    // manually in GHL Settings > Custom Menu Links) replaces it.
    'conversations':       'Разговори',
    'contacts':            'Контакти',
    'calendars':           'Календари',
    'opportunities':       'Потенциални клиенти',
    'payments':            'Плащания',
    'AI Agents':           'AI Служители',
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
    // Native Dashboard widgets + metrics (in case partner deep-links
    // directly to /dashboard URL even though sidebar item is hidden)
    '(Last 12 months)':       '(Последните 12 месеца)',
    '(Last 30 Days)':         '(Последните 30 дни)',
    'Last 30 Days':           'Последните 30 дни',
    '0s':                     '0с',
    'All Pipelines':          'Всички pipeline-и',
    'Average Sales Duration': 'Средна продължителност на продажба',
    'Bookings':               'Записвания',
    'Campaign Selection':     'Избор на кампания',
    'Conversion Rate':        'Степен на конверсия',
    'Due Date (ASC)':         'Краен срок (възх.)',
    'Edit Dashboard':         'Редактирай таблото',
    'Email Health Report':    'Доклад имейл здраве',
    'Error while loading data': 'Грешка при зареждане',
    'Funnel':                 'Фуния',
    'Go to Manual Actions':   'Към ръчните действия',
    'Google Ads Report':      'Доклад Google Ads',
    'Google Analytics Report':'Доклад Google Analytics',
    'Lead Source Report':     'Доклад източник на лийдове',
    'Maps (Desktop & Mobile)':'Карти (Desktop & Mobile)',
    'No Data Found':          'Няма данни',
    'No pipeline available':  'Няма наличен pipeline',
    'Opportunity Status':     'Статус на възможност',
    'Opportunity Value':      'Стойност на възможност',
    'Pending':                'Чакащи',
    'Please Select':          'Моля, изберете',
    'Previous':               'Предишен',
    'Quick Filters':          'Бързи филтри',
    'Sales Efficiency':       'Ефективност на продажби',
    'Sales Velocity':         'Скорост на продажби',
    'Search (Desktop & Mobile)': 'Търсене (Desktop & Mobile)',
    'Stage Distribution':     'Разпределение по етапи',
    'Total Pending':          'Общо чакащи',
    'Total Sale Value':       'Обща стойност продажби',
    'Total views':            'Общо прегледи',
    'User Selection':         'Избор на потребител',
    'Website visits':         'Посещения на сайт',
    'Won revenue':            'Спечелени приходи',
    'Workflow':               'Workflow',
    'Workflow Selection':     'Избор на workflow',
    'You must send at least 500 emails within the last 30 days. Start sending now to track your performance!':
      'За да следиш ефективността, трябва да изпратиш поне 500 имейла през последните 30 дни. Започни сега!',

    'Conversations':       'Разговори',
    'Contacts':            'Контакти',
    'Calendars':           'Календари',
    'Opportunities':       'Потенциални клиенти',
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
    'AI Agent':                                              'AI служител',
    'AI Agents':                                             'AI Служители',
    'AI Agent · Auto-reply':                                 'AI служител · Авто-отговор',
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
  // NOTE: 'payments' was removed from premium tier in May 2026 — it is now
  // an add-on (configured manually by a ZaDeteto employee on request).
  const TIER_UNLOCKS = {
    'verified':  ['conversations', 'contacts', 'settings'],
    'trusted':   ['conversations', 'contacts', 'calendars', 'opportunities', 'settings'],
    'premium':   ['conversations', 'contacts', 'calendars', 'opportunities',
                  'email-marketing', 'automation', 'sites', 'memberships',
                  'reputation', 'reporting', 'settings']
  };

  // Which `meta` values are add-ons — always visible in the sidebar but
  // gated separately from the tier. Activated by listing the matching
  // key in the partner's `addons` array in ghl-locations.json. All four
  // are services that a ZaDeteto employee configures manually on request.
  const ADDON_METAS = ['AI Agents', 'payments'];
  // Map addon meta → internal addon key (for whitelist matching).
  // Custom Menu Links (СМС карти, Касови бележки) are handled separately
  // via CUSTOM_LINK_ADDONS at the bottom of this file.
  const ADDON_KEYS = {
    'AI Agents': 'ai_agents',
    'payments':  'payments'
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
    // Payments is now an add-on (May 2026 restructure) — needs to be
    // requested separately because integration with the payment gateway
    // is configured manually by a ZaDeteto employee.
    'payments': {
      icon: '💳',
      headline: 'Приемай плащания директно от профила',
      body: 'Родителите плащат онлайн. Парите идват директно при теб, без посредници и без забавяне.',
      benefits: [
        'Карти, Apple Pay, Google Pay',
        'Автоматични фактури',
        'Месечни абонаменти за курсове'
      ],
      isAddon: true,
      addonName: 'Плащания'
    },
    // Add-on — different copy, different CTA
    'AI Agents': {
      icon: '🤖',
      headline: 'AI служител, който отговаря вместо теб',
      body: 'Отговаряй на родители 24/7 — за разписания, цени и записване. Когато спиш, AI работи за теб.',
      benefits: [
        'Отговори на български в твоя стил',
        'Записва часове директно в календара',
        'Прехвърля сложни случаи към теб'
      ],
      isAddon: true,
      addonName: 'AI Служители'
    },
    // SMS cards add-on — prepaid SMS credits for reminders + campaigns.
    // Targeted via Custom Menu Link with title "СМС карти" (no native
    // sb_* item exists for it). See markCustomLinkAddons() below.
    'sms_cards': {
      icon: '💬',
      headline: 'СМС карти — напомняния и кампании в SMS',
      body: 'Купи пакет SMS-и наведнъж и ги изразходвай постепенно. Стига до родителите за секунди, без приложение.',
      benefits: [
        'Напомняния за час 24 часа предварително',
        'Потвърждения на записани занимания',
        'Сезонни кампании до цялата база родители'
      ],
      isAddon: true,
      addonName: 'СМС карти'
    },
    // Cash receipts add-on — fiscal receipt integration for cash payments.
    // Targeted via Custom Menu Link with title "Касови бележки".
    'cash_receipts': {
      icon: '🧾',
      headline: 'Касови бележки за плащания в брой',
      body: 'Регистрирай всяко плащане в брой като фискална касова бележка, директно от профила. Без отделен касов апарат.',
      benefits: [
        'Издаване и съхранение на касови бележки',
        'Свързване с НАП и фискална памет',
        'Месечен отчет за приходи в брой'
      ],
      isAddon: true,
      addonName: 'Касови бележки'
    },
    // Documents add-on — contracts, invoices, signed forms with parents.
    // Targeted via Custom Menu Link with title "Документи".
    'documents': {
      icon: '📄',
      headline: 'Документи — договори, оферти, фактури',
      body: 'Създавай, изпращай и подписвай документи с родителите без излизане от профила. Готови шаблони и автоматични напомняния.',
      benefits: [
        'Електронен подпис на договори',
        'PDF фактури и оферти',
        'Архив на всички документи'
      ],
      isAddon: true,
      addonName: 'Документи'
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
        } else {
          // Activated add-on — still want it marked so the addons divider
          // header appears above the addons group regardless of activation.
          item.setAttribute('data-zd-addon-activated', 'true');
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

    // 4. Inject "Premium upgrade" divider before the first Premium-tier
    //    locked item.
    injectPremiumDivider(partner, unlockedMetas);

    // 4b. Inject "По заявка" divider before the first add-on item
    //     (Payments, AI Служители, plus any Custom Menu Link addons).
    //     Runs AFTER markCustomLinkAddons (called in step 7) by way of
    //     the MutationObserver re-firing apply() once those links get
    //     their data-zd-locked-addon attributes.
    injectAddonsDivider();

    // 5. Walk in-page text nodes and translate known strings (headers,
    //    sub-tabs, filter chips, common labels). Scoped to skip inputs,
    //    contenteditable, scripts, styles, and our own injected text.
    translatePageText();

    // 6. Hide any sidebar item whose title is "Tutorials" or "Уроци" —
    //    catches user-created Custom Menu Links that the #sb_tutorials
    //    CSS selector misses (custom links get unpredictable sb_* IDs).
    hideCustomTutorialsLink();

    // 6b. Translate icon alt attributes so any image-load failure shows
    //     Bulgarian fallback text instead of "Calendars icon" / similar.
    translateIconAlts();

    // 7. Mark Custom Menu Links that act as add-on entry points (e.g.
    //    "СМС карти" added in GHL UI → flagged as locked-addon so the
    //    purple sparkle CSS + click-to-modal handler kick in).
    markCustomLinkAddons(partner, activeAddons);

    // 8. Reorder addon items (Plaщания, AI Служители, СМС карти, Касови
    //    бележки) + their divider to the BOTTOM of the sidebar, right
    //    above Settings. Keeps tier-locked items + their gold divider
    //    in their original GHL positions; only the per-service addons
    //    get pulled out into a separate bottom section.
    reorderAddonsToBottom();

    // 8b. Position the static custom links — "Начало" anchors at the
    //     top of the sidebar, "Помощ и активиране" anchors at the very
    //     bottom (below Settings). GHL groups all Custom Menu Links
    //     together by default, so without this they cluster in the
    //     middle of the sidebar regardless of drag order.
    repositionStaticCustomLinks();

    // 9. Replace the whitelabel agency logo (123marketing.app) with the
    //    ZaDeteto wordmark. Re-runs on every SPA navigation via the
    //    MutationObserver so newly-mounted logo elements get rewritten too.
    replaceAgencyLogo();
  }

  function reorderAddonsToBottom() {
    // Find Settings as the anchor — addons go directly above it.
    const settings = document.querySelector('[id^="sb_"][meta="settings"]');
    if (!settings) return;
    const parent = settings.parentElement;
    if (!parent) return;

    // Gather addon items document-wide (not just direct children of one
    // parent) — Custom Menu Links may live in a different wrapper than
    // native sb_* items. We'll move them into Settings' parent.
    const divider = document.querySelector('.zd-addons-divider');
    const addons = [...document.querySelectorAll(
      '[data-zd-locked-addon="true"], [data-zd-addon-activated="true"]'
    )];
    if (!divider || !addons.length) return;

    // Sort addons by ADDON_ORDER (partner-specified display order).
    // Items whose data-zd-feature is not in ADDON_ORDER end up last.
    addons.sort((a, b) => {
      const af = a.getAttribute('data-zd-feature') || '';
      const bf = b.getAttribute('data-zd-feature') || '';
      const ai = ADDON_ORDER.indexOf(af);
      const bi = ADDON_ORDER.indexOf(bf);
      return (ai === -1 ? 999 : ai) - (bi === -1 ? 999 : bi);
    });

    const desired = [divider, ...addons];

    // Idempotency check — if the elements directly preceding Settings
    // (in Settings' parent) already match `desired`, skip the reorder.
    const tail = [];
    let cursor = settings.previousElementSibling;
    for (let i = 0; i < desired.length && cursor; i++) {
      tail.unshift(cursor);
      cursor = cursor.previousElementSibling;
    }
    const correctOrder = desired.length === tail.length &&
                         desired.every((el, i) => el === tail[i]);
    if (correctOrder) return;

    // Reorder: each insertBefore relocates the element into Settings'
    // parent (if it was elsewhere) and positions it directly before
    // Settings. Looping in order produces the final sequence:
    // [..., divider, ...addons (in DOM-discovery order), settings].
    desired.forEach(el => parent.insertBefore(el, settings));
  }

  // Map of sidebar item title (case-insensitive trimmed) to addon meta key.
  // Used by markCustomLinkAddons to convert user-created Custom Menu Links
  // into addon-styled sidebar entries with sparkle + click-to-modal.
  const CUSTOM_LINK_ADDONS = {
    'неограничени смс':  { meta: 'sms_cards',     addonKey: 'sms_cards' },
    'неограничени sms':  { meta: 'sms_cards',     addonKey: 'sms_cards' },
    'смс карти':         { meta: 'sms_cards',     addonKey: 'sms_cards' },
    'sms карти':         { meta: 'sms_cards',     addonKey: 'sms_cards' },
    'касови бележки':    { meta: 'cash_receipts', addonKey: 'cash_receipts' },
    'документи':         { meta: 'documents',     addonKey: 'documents' }
  };

  // Explicit display order for the add-ons group. Without this we'd
  // get whatever DOM-discovery order produces, which depends on GHL
  // sidebar ordering + user drag order in Custom Menu Links. Indexes
  // in this array win over data-zd-feature alphabetical fallback.
  const ADDON_ORDER = [
    'payments',       // Плащания (native)
    'documents',      // Документи (custom)
    'cash_receipts',  // Касови бележки (custom)
    'AI Agents',      // AI Служители (native)
    'sms_cards'       // Неограничени СМС / СМС карти (custom)
  ];

  function markCustomLinkAddons(partner, activeAddons) {
    // Custom Menu Links sometimes lack the [id^="sb_"] convention used
    // by native sidebar items, so cast a wider net — anything that looks
    // like a sidebar nav element and whose visible text matches a known
    // addon title.
    const items = document.querySelectorAll(
      '[id^="sb_"], aside a, nav a, [class*="sidebar"] a'
    );
    items.forEach(item => {
      if (item.dataset.zdCustomAddonMarked === 'true') return;
      const titleEl = item.querySelector('.nav-title');
      const candidates = [
        titleEl && titleEl.textContent,
        item.getAttribute('aria-label'),
        item.getAttribute('title'),
        item.textContent
      ].filter(Boolean).map(s => s.trim().toLowerCase());
      let matchedCfg = null;
      for (const t of candidates) {
        if (CUSTOM_LINK_ADDONS[t]) {
          matchedCfg = CUSTOM_LINK_ADDONS[t];
          break;
        }
      }
      if (!matchedCfg) return;
      // Clear any prior tier-locked flag — these are addons, not tier items.
      item.removeAttribute('data-zd-locked');
      const activated = activeAddons.has(matchedCfg.addonKey);
      if (activated) {
        item.removeAttribute('data-zd-locked-addon');
        item.setAttribute('data-zd-addon-activated', 'true');
      } else {
        item.setAttribute('data-zd-locked-addon', 'true');
      }
      item.setAttribute('data-zd-feature', matchedCfg.meta);
      item.dataset.zdCustomAddonMarked = 'true';
    });
  }

  // Custom Menu Links that should anchor at the TOP or BOTTOM of the
  // sidebar regardless of where GHL places them by default. Matched
  // by visible title (case-insensitive).
  const STATIC_LINK_POSITIONS = {
    'начало':              'top',
    'помощ и активиране':  'bottom'
  };

  function repositionStaticCustomLinks() {
    // Find Settings as anchor for "bottom" group reasoning.
    const settings = document.querySelector('[id^="sb_"][meta="settings"]');
    if (!settings) return;
    const parent = settings.parentElement;
    if (!parent) return;

    Object.entries(STATIC_LINK_POSITIONS).forEach(([title, position]) => {
      const link = findElementByTitle(title);
      if (!link) return;
      if (link.dataset.zdStaticPositionApplied === position) return;
      // Move into Settings' parent if it's elsewhere.
      if (position === 'top') {
        const firstChild = parent.firstElementChild;
        if (firstChild !== link) {
          parent.insertBefore(link, firstChild);
        }
      } else if (position === 'bottom') {
        if (parent.lastElementChild !== link) {
          parent.appendChild(link);
        }
      }
      link.dataset.zdStaticPositionApplied = position;
    });
  }

  function findElementByTitle(targetTitle) {
    const norm = targetTitle.trim().toLowerCase();
    const candidates = document.querySelectorAll(
      '[id^="sb_"], aside a, nav a, [class*="sidebar"] a'
    );
    let nativeMatch = null;
    let customMatch = null;
    for (const el of candidates) {
      const titleEl = el.querySelector('.nav-title');
      const candidatesText = [
        titleEl && titleEl.textContent,
        el.getAttribute('aria-label'),
        el.getAttribute('title'),
        el.textContent
      ].filter(Boolean).map(s => s.trim().toLowerCase());
      if (!candidatesText.some(t => t === norm)) continue;
      // Skip hidden elements (e.g. CSS-hidden #sb_dashboard).
      const cs = window.getComputedStyle(el);
      if (cs.display === 'none' || cs.visibility === 'hidden') continue;
      if (el.id && el.id.startsWith('sb_')) {
        if (!nativeMatch) nativeMatch = el;
      } else {
        if (!customMatch) customMatch = el;
      }
    }
    // Prefer custom links over native items — when both exist (e.g. user
    // created a "Начало" custom link AND we display-none the native
    // sb_dashboard whose nav-title also got translated to "Начало").
    return customMatch || nativeMatch;
  }

  function hideCustomTutorialsLink() {
    // Match against multiple text sources because Custom Menu Links
    // sometimes lack a .nav-title child and put text directly in the
    // anchor, or use an aria-label / title attribute instead.
    const items = document.querySelectorAll(
      '[id^="sb_"], aside a[href*="custom"], aside a[href*="tutorials" i]'
    );
    items.forEach(item => {
      if (item.dataset.zdTutorialsHidden) return;
      const titleEl = item.querySelector('.nav-title');
      const candidates = [
        titleEl && titleEl.textContent,
        item.getAttribute('aria-label'),
        item.getAttribute('title'),
        item.textContent
      ].filter(Boolean).map(s => s.trim().toLowerCase());
      const isTutorials = candidates.some(t =>
        t === 'tutorials' || t === 'уроци' ||
        t.startsWith('tutorials ') || t.startsWith('уроци ') ||
        t.startsWith('tutorials\n') || t.startsWith('уроци\n')
      );
      if (isTutorials) {
        item.style.display = 'none';
        item.dataset.zdTutorialsHidden = 'true';
      }
    });
  }

  // Translate the alt-text on GHL sidebar icons so that if the icon
  // fails to load (CDN flake, ad blocker, slow connection), the fallback
  // text the browser renders is Bulgarian, not English. Also helps with
  // screen-reader localisation.
  const ICON_ALT_TRANSLATIONS = {
    'Dashboard icon':       'Начало',
    'Conversations icon':   'Разговори',
    'Calendars icon':       'Календари',
    'Contacts icon':        'Контакти',
    'Opportunities icon':   'Потенциални клиенти',
    'Payments icon':        'Плащания',
    'AI Agents icon':       'AI Служители',
    'Marketing icon':       'Онлайн маркетинг',
    'Automation icon':      'Автоматизации',
    'Sites icon':           'Уебсайтове',
    'Memberships icon':     'Членства',
    'Media Storage icon':   'Хранилище',
    'Reputation icon':      'Отзиви',
    'Reporting icon':       'Отчети',
    'Settings icon':        'Настройки',
    'Launchpad icon':       'Старт',
    'Mobile App icon':      'Мобилно приложение',
    'Tutorials icon':       'Уроци',
    'Quick actions icon':   'Бързи действия'
  };

  function translateIconAlts() {
    const imgs = document.querySelectorAll('[id^="sb_"] img[alt]');
    imgs.forEach(img => {
      if (img.dataset.zdAltTranslated) return;
      const alt = img.getAttribute('alt');
      if (ICON_ALT_TRANSLATIONS[alt]) {
        img.alt = ICON_ALT_TRANSLATIONS[alt];
        img.dataset.zdAltTranslated = 'true';
      }
    });
  }

  function replaceAgencyLogo() {
    const logos = document.querySelectorAll('img');
    logos.forEach(img => {
      if (img.dataset.zdLogoReplaced) return;
      const alt = (img.getAttribute('alt') || '').trim().toLowerCase();
      const src = img.getAttribute('src') || '';
      // GHL tags the whitelabel agency logo uniquely with alt="agency logo".
      // Sidebar menu icons use alt="X icon" (Dashboard icon, Conversations
      // icon, etc.) so they will never match. As a belt-and-braces fallback
      // we also accept src patterns that point at company-uploaded photos
      // or paths with explicit 'logo' markers.
      const isAgencyLogo =
        alt === 'agency logo' ||
        alt === 'company logo' ||
        /companyPhotos|companyphotos|whitelabel_logo|companylogo/i.test(src);
      if (!isAgencyLogo) return;
      img.src = 'https://zadeteto.com/brand_assets/zadeteto-ghl-wordmark.svg';
      img.alt = 'Национален Регистър За Детето';
      img.dataset.zdLogoReplaced = 'true';
      // Wordmark is 3:1 — constrain by height and let width follow.
      // max-width:100% keeps it inside narrow sidebars on smaller screens.
      img.style.maxHeight = '64px';
      img.style.maxWidth = '100%';
      img.style.width = 'auto';
      img.style.height = 'auto';
      img.style.objectFit = 'contain';
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
    // unlocks at premium tier). 'payments' is no longer in this list —
    // it became an add-on in the May 2026 restructure.
    const premiumOnlyMetas = ['email-marketing', 'automation', 'sites',
                              'memberships', 'reputation', 'reporting'];

    for (const meta of premiumOnlyMetas) {
      const item = document.querySelector(`[meta="${meta}"]`);
      if (item && item.hasAttribute('data-zd-locked')) {
        // Build the divider
        const divider = document.createElement('div');
        divider.className = 'zd-premium-divider';
        divider.innerHTML =
          '<span class="zd-premium-divider-icon">🔒</span>' +
          '<span class="zd-premium-divider-label">Premium upgrade</span>';
        item.parentNode.insertBefore(divider, item);
        break;
      }
    }
  }

  function injectAddonsDivider() {
    // Already injected? Skip.
    if (document.querySelector('.zd-addons-divider')) return;

    // Find the first item that is an add-on (whether currently locked or
    // already activated — we still want the section header to appear so
    // the partner can scan 'these are paid services configured manually').
    // Order matters because DOM order on GHL native sidebar is fixed.
    const addonCandidates = document.querySelectorAll(
      '[id^="sb_"][data-zd-locked-addon="true"], [id^="sb_"][data-zd-addon-activated="true"]'
    );
    if (!addonCandidates.length) return;

    // Pick the topmost one in document order.
    let first = addonCandidates[0];
    addonCandidates.forEach(el => {
      if (el.compareDocumentPosition(first) & Node.DOCUMENT_POSITION_PRECEDING) {
        first = el;
      }
    });

    const divider = document.createElement('div');
    divider.className = 'zd-addons-divider';
    divider.innerHTML =
      '<span class="zd-addons-divider-icon">✦</span>' +
      '<span class="zd-addons-divider-label">По заявка</span>';
    first.parentNode.insertBefore(divider, first);
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
        const addonLabel = content.addonName || 'Надстройка';
        const subject = encodeURIComponent(`${addonLabel} за ${partner.name}`);
        const body = encodeURIComponent(
          `Здравейте,\n\nИнтересувам се от активиране на ${addonLabel} за моя профил (${partner.name}).\n\nLocation ID: ${locationId}\n\nПоздрави,`
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
