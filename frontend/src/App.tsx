import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  Bell,
  Home,
  MessageCircle,
  Calendar,
  Package,
  Settings,
  CheckSquare,
  ChevronRight,
  Plus,
  Inbox,
  Search,
  ChevronDown,
  ChevronLeft,
  MapPin,
  Mic,
  Send,
  MoreVertical,
  UserCircle2,
  SlidersHorizontal,
  BookOpen,
  Lightbulb,
  ShoppingCart,
  Box,
  Mail,
  Cog,
  Check,
  CalendarDays,
  Volume2,
  Loader2,
} from 'lucide-react';

type TabId = 'home' | 'chat' | 'calendar' | 'inbox' | 'settings';

type ChatMessage = {
  id: string;
  role: 'user' | 'assistant' | 'system';
  text: string;
};

const copy = {
  version: 'Wersja 9.7.5',
  beta: 'BETA',
  welcome: 'Witaj Mateusz!',
  wave: '👋',
  todayLine1: 'Masz dziś ',
  tasks10: '10 zadań',
  todayLine2: ' i ',
  meeting1: '1 spotkanie',
  todayLine3: ' o ',
  todayLine4: '11:00',
  cardToday: 'Dzisiaj',
  cardTodo: 'Do zrobienia',
  cardWeek: 'Ten tydzień',
  cardProjects: 'Projekty',
  tasksLabel: 'zadań',
  upcoming: 'Nadchodzące',
  seeAll: 'Zobacz wszystko',
  event1: 'Umówione spotkanie z zespołem',
  event2: 'Przegląd zadań tygodniowych',
  meetingTag: 'Spotkanie',
  taskTag: 'Zadanie',
  navHome: 'Home',
  navChat: 'Czat',
  navCalendar: 'Kalendarz',
  navInbox: 'Projekty',
  navSettings: 'Ustawienia',
};

const OLLAMA_MODEL = 'llama3.2';

function Header({
  title,
  icon,
  showProfile = true,
  showBell = true,
  subtitle = copy.version,
  beta = false,
  extraLeft,
  extraRight,
}: {
  title: string;
  icon?: React.ReactNode;
  showProfile?: boolean;
  showBell?: boolean;
  subtitle?: string;
  beta?: boolean;
  extraLeft?: React.ReactNode;
  extraRight?: React.ReactNode;
}) {
  return (
    <header className="mb-3 flex items-start justify-between gap-4">
      <div className="min-w-0 flex items-start gap-3">
        {extraLeft}
        {icon ? <div className="pt-1">{icon}</div> : null}
        <div className="min-w-0">
          <h1 className="text-[34px] font-semibold leading-none tracking-[-0.05em] text-slate-800">
            {title}
          </h1>
          <div className="mt-3 flex flex-wrap items-center gap-3">
            <span className="text-[17px] text-slate-500">{subtitle}</span>
            {beta ? (
              <span className="rounded-full bg-indigo-100 px-3 py-1 text-sm font-medium text-indigo-400">
                BETA
              </span>
            ) : null}
          </div>
        </div>
      </div>

      <div className="flex shrink-0 items-center gap-3">
        {extraRight}
        {showBell ? (
          <div className="relative">
            <Bell className="h-8 w-8 text-slate-700" />
            <div className="absolute -right-1 -top-2 flex h-7 w-7 items-center justify-center rounded-full bg-pink-400 text-sm font-semibold text-white">
              3
            </div>
          </div>
        ) : null}

        {showProfile ? (
          <div className="h-14 w-14 overflow-hidden rounded-full border-2 border-indigo-200 shadow-sm">
            <img
              src="https://i.pravatar.cc/100?img=12"
              alt="Profil"
              className="h-full w-full object-cover"
            />
          </div>
        ) : null}
      </div>
    </header>
  );
}

function SearchBar({ placeholder = 'Szukaj...' }: { placeholder?: string }) {
  return (
    <div className="mb-4 -mx-5 bg-[linear-gradient(180deg,#edf1f9_0%,#ebedf5_100%)] px-5 py-4">
      <div className="flex items-center gap-3 rounded-[24px] bg-white/70 px-5 py-4 shadow-sm">
        <Search className="h-7 w-7 text-slate-400" />
        <span className="text-[16px] text-slate-400">{placeholder}</span>
      </div>
    </div>
  );
}

function DashboardCard({
  icon,
  title,
  value,
  subtitle,
  bg,
}: {
  icon: React.ReactNode;
  title: string;
  value: string;
  subtitle: string;
  bg: string;
}) {
  return (
    <button className={`h-[118px] rounded-[22px] ${bg} px-4 py-3 text-left shadow-sm`}>
      <div className="mb-2 flex items-start justify-between gap-2">
        <div className="flex min-w-0 items-center gap-3">
          <div className="shrink-0 rounded-2xl bg-white/85 p-2 shadow-sm">{icon}</div>
          <span className="text-[16px] font-semibold text-slate-700">{title}</span>
        </div>
        <ChevronRight className="h-5 w-5 shrink-0 text-slate-400" />
      </div>

      <div className="text-[26px] font-semibold leading-none tracking-[-0.05em] text-slate-800">
        {value}
      </div>
      <div className="mt-2 text-[12px] text-slate-500">{subtitle}</div>
    </button>
  );
}

function NavItem({
  id,
  label,
  activeTab,
  setActiveTab,
  icon: Icon,
}: {
  id: TabId;
  label: string;
  activeTab: TabId;
  setActiveTab: (tab: TabId) => void;
  icon: React.ElementType;
}) {
  const active = activeTab === id;

  return (
    <button
      onClick={() => setActiveTab(id)}
      className="flex flex-col items-center justify-center gap-1"
    >
      <div
        className={`flex h-11 w-11 items-center justify-center rounded-2xl transition ${
          active ? 'bg-indigo-100 text-indigo-500' : 'text-slate-500'
        }`}
      >
        <Icon className="h-6 w-6" />
      </div>
      <span className={`text-[11px] ${active ? 'text-indigo-500' : 'text-slate-600'}`}>
        {label}
      </span>
    </button>
  );
}

function BottomNav({
  activeTab,
  setActiveTab,
}: {
  activeTab: TabId;
  setActiveTab: (tab: TabId) => void;
}) {
  return (
    <nav className="rounded-[30px] bg-white/75 px-4 py-4 shadow-[0_10px_24px_rgba(15,23,42,0.06)]">
      <div className="grid grid-cols-5 items-center">
        <NavItem id="home" label={copy.navHome} activeTab={activeTab} setActiveTab={setActiveTab} icon={Home} />
        <NavItem id="chat" label={copy.navChat} activeTab={activeTab} setActiveTab={setActiveTab} icon={MessageCircle} />
        <NavItem id="calendar" label={copy.navCalendar} activeTab={activeTab} setActiveTab={setActiveTab} icon={Calendar} />
        <NavItem id="inbox" label={copy.navInbox} activeTab={activeTab} setActiveTab={setActiveTab} icon={Package} />
        <NavItem id="settings" label={copy.navSettings} activeTab={activeTab} setActiveTab={setActiveTab} icon={Settings} />
      </div>
    </nav>
  );
}

function PhoneShell({
  children,
  activeTab,
  setActiveTab,
}: {
  children: React.ReactNode;
  activeTab: TabId;
  setActiveTab: (tab: TabId) => void;
}) {
  return (
    <div className="min-h-screen bg-[linear-gradient(180deg,#f3f3f9_0%,#ececf5_100%)] px-4 py-4">
      <div className="mx-auto w-full max-w-[430px]">
        <div className="relative h-[860px] overflow-hidden rounded-[46px] border border-white/70 bg-[linear-gradient(180deg,rgba(255,255,255,0.86),rgba(243,241,249,0.98))] px-5 pb-5 pt-4 shadow-[0_30px_70px_rgba(99,102,241,0.10)]">
          <div className="mx-auto mb-3 h-1.5 w-28 rounded-full bg-indigo-200" />
          <div className="flex h-[calc(100%-18px)] flex-col">
            <div className="min-h-0 flex-1 overflow-hidden">{children}</div>
            <div className="mt-4">
              <BottomNav activeTab={activeTab} setActiveTab={setActiveTab} />
              <div className="mx-auto mt-4 h-1.5 w-40 rounded-full bg-slate-800" />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function HomeScreen() {
  return (
    <div className="flex h-full flex-col">
      <Header title="Home" subtitle={copy.version} beta />

      <section className="-mx-5 mb-3 bg-[linear-gradient(180deg,#edf1f9_0%,#ebedf5_100%)] px-5 py-0">
        <div className="flex h-[122px] items-center gap-3">
          <div className="flex w-[170px] shrink-0 items-center justify-center">
            <img
              src="/robot-premium.png"
              alt="Jarvis robot"
              className="object-contain drop-shadow-[0_18px_24px_rgba(99,102,241,0.18)]"
              style={{ width: 168, height: 168 }}
            />
          </div>

          <div className="min-w-0 flex-1 pr-1">
            <h2 className="text-[24px] font-semibold leading-tight tracking-[-0.05em] text-slate-800">
              {copy.welcome} {copy.wave}
            </h2>
            <p className="mt-1 text-[14px] leading-5 text-slate-600">
              {copy.todayLine1}
              <span className="font-semibold text-slate-800">{copy.tasks10}</span>
              {copy.todayLine2}
              <span className="font-semibold text-slate-800">{copy.meeting1}</span>
              {copy.todayLine3}
              <span className="font-semibold text-slate-800">{copy.todayLine4}</span>.
            </p>
          </div>
        </div>
      </section>

      <section className="mb-3 grid grid-cols-2 gap-4">
        <DashboardCard
          icon={<CheckSquare className="h-5 w-5 text-orange-400" />}
          title={copy.cardToday}
          value="10"
          subtitle={copy.tasksLabel}
          bg="bg-[linear-gradient(135deg,#f7efe9_0%,#f4efed_100%)]"
        />
        <DashboardCard
          icon={<Calendar className="h-5 w-5 text-violet-400" />}
          title={copy.cardTodo}
          value="5"
          subtitle={copy.tasksLabel}
          bg="bg-[linear-gradient(135deg,#f0eefb_0%,#f2f0fb_100%)]"
        />
        <DashboardCard
          icon={<CalendarDays className="h-5 w-5 text-cyan-400" />}
          title={copy.cardWeek}
          value="3"
          subtitle={copy.tasksLabel}
          bg="bg-[linear-gradient(135deg,#ecf5f5_0%,#edf2f2_100%)]"
        />
        <DashboardCard
          icon={<Inbox className="h-5 w-5 text-violet-400" />}
          title={copy.cardProjects}
          value="15"
          subtitle={copy.tasksLabel}
          bg="bg-[linear-gradient(135deg,#f0eefb_0%,#f2f0fb_100%)]"
        />
      </section>

      <section className="mb-2">
        <div className="mb-2 flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <Settings className="h-7 w-7 text-violet-400" />
            <h3 className="text-[18px] font-semibold tracking-[-0.03em] text-slate-800">
              {copy.upcoming}
            </h3>
          </div>

          <button className="flex shrink-0 items-center gap-1 text-[14px] font-medium text-indigo-400">
            {copy.seeAll}
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>

        <div className="rounded-[22px] bg-white/75 p-3 shadow-sm">
          <div className="flex items-center justify-between gap-3 border-b border-slate-200 pb-3">
            <div className="flex min-w-0 items-center gap-3">
              <div className="h-4 w-4 shrink-0 rounded-full bg-violet-400" />
              <div className="shrink-0 text-[15px] font-semibold text-slate-800">11:00</div>
              <div className="truncate text-[15px] text-slate-700">{copy.event1}</div>
            </div>

            <div className="shrink-0 rounded-2xl bg-violet-100 px-3 py-1.5 text-[13px] font-medium text-violet-500">
              {copy.meetingTag}
            </div>
          </div>

          <div className="flex items-center justify-between gap-3 pt-3">
            <div className="flex min-w-0 items-center gap-3">
              <div className="h-4 w-4 shrink-0 rounded-full bg-orange-300" />
              <div className="shrink-0 text-[15px] font-semibold text-slate-800">15:30</div>
              <div className="truncate text-[15px] text-slate-700">{copy.event2}</div>
            </div>

            <div className="shrink-0 rounded-2xl bg-orange-100 px-3 py-1.5 text-[13px] font-medium text-orange-400">
              {copy.taskTag}
            </div>
          </div>
        </div>
      </section>

      <div className="mt-auto flex justify-end pb-2 pr-2">
        <button className="z-20 flex h-14 w-14 items-center justify-center rounded-full bg-[linear-gradient(180deg,#7196ff_0%,#4f75ff_100%)] text-white shadow-[0_18px_30px_rgba(77,116,255,0.28)] transition hover:scale-105">
          <Plus className="h-7 w-7" />
        </button>
      </div>
    </div>
  );
}

function ChatScreen() {
  const inputRef = useRef<HTMLInputElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [message, setMessage] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isSending]);

  async function sendMessage() {
    const trimmed = message.trim();
    if (!trimmed || isSending) return;

    const userMessage: ChatMessage = {
      id: `u-${Date.now()}`,
      role: 'user',
      text: trimmed,
    };

    const nextMessages = [...messages, userMessage];
    setMessages(nextMessages);
    setMessage('');
    setIsSending(true);

    try {
      const response = await fetch('http://127.0.0.1:11434/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model: OLLAMA_MODEL,
          stream: false,
          messages: nextMessages
            .filter((m) => m.role !== 'system')
            .map((m) => ({
              role: m.role,
              content: m.text,
            })),
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();
      const assistantText =
        data?.message?.content?.trim() ||
        'Nie udało się pobrać odpowiedzi z Ollamy.';

      setMessages((prev) => [
        ...prev,
        {
          id: `a-${Date.now()}`,
          role: 'assistant',
          text: assistantText,
        },
      ]);
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        {
          id: `e-${Date.now()}`,
          role: 'assistant',
          text: 'Nie mogę połączyć się z Ollamą. Upewnij się, że Ollama działa lokalnie i masz model ' + OLLAMA_MODEL + '.',
        },
      ]);
    } finally {
      setIsSending(false);
      inputRef.current?.focus();
    }
  }

  return (
    <div className="flex h-full flex-col">
      <Header
        title="Chat"
        subtitle={copy.version}
        showProfile={false}
        showBell={false}
        extraLeft={<ChevronLeft className="mt-1 h-10 w-10 text-indigo-500" />}
        extraRight={
          <div className="rounded-full border border-indigo-200 p-3">
            <MoreVertical className="h-8 w-8 text-indigo-400" />
          </div>
        }
      />

      <div className="-mx-5 min-h-0 flex-1 bg-[linear-gradient(180deg,#edf1f9_0%,#ebedf5_100%)] px-5 py-5">
        <div className="flex h-full flex-col">
          <div className="min-h-0 flex-1 overflow-y-auto rounded-[30px] bg-transparent">
            {messages.length === 0 ? (
              <div className="flex h-full items-center justify-center px-8 text-center text-[16px] text-slate-400">
                Napisz pierwszą wiadomość do Jarvisa.
              </div>
            ) : (
              <div className="space-y-4 pb-4">
                {messages.map((msg) => (
                  <div
                    key={msg.id}
                    className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                  >
                    <div
                      className={`max-w-[80%] rounded-[24px] px-4 py-3 text-[16px] leading-6 shadow-sm ${
                        msg.role === 'user'
                          ? 'rounded-br-[8px] bg-[linear-gradient(180deg,#7196ff_0%,#4f75ff_100%)] text-white'
                          : 'rounded-bl-[8px] bg-white/85 text-slate-800'
                      }`}
                    >
                      {msg.text}
                    </div>
                  </div>
                ))}

                {isSending ? (
                  <div className="flex justify-start">
                    <div className="rounded-[24px] rounded-bl-[8px] bg-white/85 px-4 py-3 text-slate-500 shadow-sm">
                      <Loader2 className="h-5 w-5 animate-spin" />
                    </div>
                  </div>
                ) : null}

                <div ref={messagesEndRef} />
              </div>
            )}
          </div>

          <div className="mt-4">
            <div className="flex items-center gap-3 rounded-[28px] bg-white/80 px-5 py-4 shadow-sm">
              <input
                ref={inputRef}
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault();
                    sendMessage();
                  }
                }}
                placeholder="Napisz do Jarvisa..."
                className="flex-1 bg-transparent text-[18px] text-slate-700 outline-none placeholder:text-slate-400"
                autoFocus
              />
              <button className="text-indigo-400" type="button">
                <Mic className="h-7 w-7" />
              </button>
              <button
                className="rounded-full bg-[linear-gradient(180deg,#7196ff_0%,#4f75ff_100%)] p-4 text-white shadow-sm disabled:opacity-60"
                onClick={sendMessage}
                disabled={isSending || !message.trim()}
                type="button"
              >
                <Send className="h-6 w-6" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function CalendarScreen() {
  const events = [
    ['09:00', 'Joga', 'Fitness Club', '45 min', 'bg-violet-500', 'bg-violet-500/10 text-violet-600'],
    ['10:30', 'Spotkanie z zespołem', 'Biuro + Online (4 osoby)', 'Zespół', 'bg-blue-500', 'bg-blue-500/10 text-blue-600'],
    ['12:00', 'Lunch z Anna', 'Restauracja „Zdrowa Kuchnia”', '90 min', 'bg-emerald-500', 'bg-emerald-500/10 text-emerald-600'],
    ['14:00', 'Przegląd projektu', 'Przygotować prezentację', 'Praca', 'bg-orange-500', 'bg-orange-500/10 text-orange-600'],
    ['16:30', 'Dentysta', 'Klinika zdrowy uśmiech', '60 min', 'bg-rose-500', 'bg-rose-500/10 text-rose-600'],
    ['18:00', 'Trening siłowy', 'Siłownia Power Gym', '75 min', 'bg-slate-500', 'bg-slate-500/10 text-slate-600'],
  ] as const;

  return (
    <div className="flex h-full flex-col">
      <Header
        title="Kalendarz"
        subtitle={copy.version}
        icon={<Calendar className="h-10 w-10 text-indigo-500" />}
        extraRight={<Mail className="h-8 w-8 text-indigo-300" />}
      />

      <div className="-mx-5 mb-4 bg-[linear-gradient(180deg,#edf1f9_0%,#ebedf5_100%)] px-5 py-4">
        <div className="mb-4 flex items-center justify-between">
          <ChevronLeft className="h-8 w-8 text-indigo-500" />
          <div className="flex items-center gap-2 text-[24px] font-semibold text-slate-800">
            Kwiecień 2024
            <ChevronDown className="h-6 w-6 text-slate-400" />
          </div>
          <ChevronRight className="h-8 w-8 text-indigo-500" />
        </div>

        <div className="rounded-[26px] bg-white/80 p-5 shadow-sm">
          <div className="grid grid-cols-7 text-center">
            {[
              ['Pon', '22'],
              ['Wt', '23'],
              ['Śr', '24'],
              ['Czw', '25'],
              ['Pt', '26'],
              ['Sob', '27'],
              ['Ndz', '28'],
            ].map(([day, num], index) => {
              const active = index === 2;
              const accent = index === 3 || index === 6;
              return (
                <div key={day} className="flex flex-col items-center gap-2">
                  <span className={`text-[14px] font-medium ${accent ? 'text-indigo-500' : 'text-slate-700'}`}>{day}</span>
                  <div
                    className={`flex h-12 w-12 items-center justify-center rounded-full text-[18px] ${
                      active ? 'bg-indigo-500 text-white' : accent ? 'text-indigo-500' : 'text-slate-800'
                    }`}
                  >
                    {num}
                  </div>
                  <div className="h-2.5 w-2.5 rounded-full bg-indigo-500" />
                </div>
              );
            })}
          </div>
        </div>

        <div className="mt-4 flex items-center justify-between">
          <h3 className="text-[22px] font-semibold text-slate-800">Czwartek, 24 kwietnia</h3>
          <button className="flex items-center gap-2 rounded-full bg-[linear-gradient(90deg,#4f75ff,#3b82f6)] px-5 py-3 text-[16px] text-white shadow-sm">
            <Plus className="h-5 w-5" />
            Nowe wydarzenie
          </button>
        </div>
      </div>

      <div className="-mx-5 min-h-0 flex-1 overflow-y-auto bg-white/20 px-5 pb-2">
        <div className="space-y-0">
          {events.map(([time, title, subtitle, badge, dotClass, badgeClass]) => (
            <div key={title} className="grid grid-cols-[88px_1fr] border-b border-indigo-100 py-4">
              <div className="text-[18px] text-slate-500">{time}</div>
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0">
                  <div className="flex items-center gap-3">
                    <div className={`h-5 w-5 shrink-0 rounded-full ${dotClass}`} />
                    <div className="text-[18px] font-semibold text-slate-800">{title}</div>
                  </div>
                  <div className="ml-8 mt-2 flex items-center gap-2 text-[14px] text-slate-500">
                    <MapPin className="h-4 w-4" />
                    <span className="truncate">{subtitle}</span>
                  </div>
                </div>
                <div className={`shrink-0 rounded-xl px-3 py-1.5 text-[14px] font-medium ${badgeClass}`}>
                  {badge}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function ProjectsScreen() {
  const groups = useMemo(
    () => [
      {
        title: 'Ogólne',
        count: '5',
        icon: <Box className="h-7 w-7 text-indigo-400" />,
        items: [
          'Umówić spotkanie z zespołem',
          'Jak poprawić stronę główną?',
          'Przestać raport kwartalny',
          'Kupić prezent na urodziny Ani',
          'Znaleźć dobrą aplikację do CRM',
        ],
      },
      {
        title: 'Lista zakupów',
        count: '3',
        icon: <ShoppingCart className="h-7 w-7 text-indigo-400" />,
        items: ['Mleko i pieczywo', 'Makaron i warzywa na obiad'],
      },
      {
        title: 'Pomysły',
        count: '6',
        icon: <Lightbulb className="h-7 w-7 text-indigo-400" />,
        items: ['Pomysły na opis nowego projektu', 'Nowy artykuł na bloga o produktywności'],
      },
      {
        title: 'Przeczytać',
        count: '4',
        icon: <BookOpen className="h-7 w-7 text-indigo-400" />,
        items: [],
      },
    ],
    []
  );

  return (
    <div className="flex h-full flex-col">
      <Header title="Projekty" subtitle={copy.version} icon={<Package className="h-10 w-10 text-indigo-300" />} />
      <SearchBar />

      <div className="min-h-0 flex-1 space-y-4 overflow-y-auto pr-1">
        {groups.map((group, groupIndex) => (
          <div key={group.title}>
            <div className="mb-3 flex items-center justify-between">
              <div className="flex items-center gap-3">
                {group.icon}
                <h3 className="text-[20px] font-semibold text-slate-800">{group.title}</h3>
              </div>

              <div className="flex items-center gap-3">
                <div className="rounded-xl bg-indigo-100 px-3 py-1 text-[16px] font-medium text-indigo-400">
                  {group.count}
                </div>
                <ChevronDown className="h-6 w-6 text-indigo-400" />
              </div>
            </div>

            <div className="rounded-[22px] bg-white/75 p-3 shadow-sm">
              {group.items.length === 0 ? (
                <div className="h-20 rounded-[18px] bg-white/40" />
              ) : (
                group.items.map((item, itemIndex) => (
                  <div
                    key={item}
                    className={`flex items-center justify-between gap-3 px-3 py-3 ${
                      itemIndex !== group.items.length - 1 ? 'border-b border-slate-200' : ''
                    }`}
                  >
                    <div className="flex min-w-0 items-center gap-3">
                      <div className={`h-7 w-7 rounded-md border-2 ${groupIndex === 0 && itemIndex === 0 ? 'border-indigo-300 bg-indigo-50' : 'border-slate-300'}`}>
                        {groupIndex === 0 && itemIndex === 0 ? (
                          <Check className="m-0.5 h-5 w-5 text-indigo-400" />
                        ) : null}
                      </div>
                      <span className="truncate text-[17px] text-slate-700">{item}</span>
                    </div>

                    {groupIndex === 0 ? (
                      <div className="rounded-xl bg-indigo-50 px-3 py-1 text-[16px] font-medium text-indigo-400">
                        {[5, 3, 6, 4, 2][itemIndex]}
                      </div>
                    ) : null}
                  </div>
                ))
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function ToggleRow({
  icon,
  title,
}: {
  icon: React.ReactNode;
  title: string;
}) {
  return (
    <div className="flex items-center justify-between px-3 py-4">
      <div className="flex items-center gap-4 min-w-0">
        {icon}
        <span className="text-[18px] text-slate-700">{title}</span>
      </div>

      <div className="flex h-9 w-20 shrink-0 items-center rounded-full bg-indigo-400 px-1">
        <div className="ml-auto flex h-7 w-7 items-center justify-center rounded-full bg-white text-indigo-300">
          <Check className="h-4 w-4" />
        </div>
      </div>
    </div>
  );
}

function SettingsScreen() {
  return (
    <div className="flex h-full flex-col">
      <Header title="Ustawienia" subtitle={copy.version} icon={<Cog className="h-10 w-10 text-indigo-300" />} />
      <SearchBar />

      <div className="min-h-0 flex-1 overflow-y-auto pr-1 pb-6">
        <div className="space-y-5">
          <div>
            <h3 className="mb-3 text-[20px] font-semibold text-slate-800">Konto</h3>

            <div className="rounded-[22px] bg-white/75 p-3 shadow-sm">
              {[
                { icon: <UserCircle2 className="h-8 w-8 text-indigo-300" />, title: 'Moje konto' },
                { icon: <SlidersHorizontal className="h-8 w-8 text-indigo-300" />, title: 'Preferencje' },
              ].map((item) => (
                <div key={item.title} className="flex items-center justify-between border-b border-slate-200 px-3 py-4 last:border-b-0">
                  <div className="flex items-center gap-4">
                    {item.icon}
                    <span className="text-[18px] text-slate-700">{item.title}</span>
                  </div>
                  <ChevronRight className="h-7 w-7 text-indigo-300" />
                </div>
              ))}
            </div>

            <div className="mt-4 rounded-[22px] bg-white/75 p-5 shadow-sm">
              <div className="flex items-start justify-between gap-4">
                <div className="flex gap-4">
                  <div className="flex h-20 w-20 items-center justify-center rounded-[18px] bg-indigo-100 text-[34px]">
                    🦙
                  </div>
                  <div>
                    <div className="text-[18px] font-semibold text-slate-800">Ollama</div>
                    <div className="mt-2 max-w-[250px] text-[16px] leading-7 text-slate-500">
                      Sprawdź status Ollamy i skonfiguruj środowisko sztucznej inteligencji
                    </div>
                  </div>
                </div>
                <ChevronRight className="h-7 w-7 shrink-0 text-indigo-300" />
              </div>
            </div>
          </div>

          <div>
            <h3 className="mb-3 text-[20px] font-semibold text-slate-800">Pozwolenia</h3>

            <div className="rounded-[22px] bg-white/75 p-3 shadow-sm">
              <ToggleRow icon={<Bell className="h-7 w-7 text-indigo-300" />} title="Powiadomienia" />
              <div className="border-b border-slate-200" />
              <ToggleRow icon={<Mic className="h-7 w-7 text-indigo-300" />} title="Dostęp do mikrofonu" />
              <div className="border-b border-slate-200" />
              <ToggleRow icon={<MapPin className="h-7 w-7 text-indigo-300" />} title="Dostęp do lokalizacji" />
            </div>
          </div>

          <div className="h-12 rounded-[22px] bg-white/40" />
        </div>
      </div>
    </div>
  );
}

export default function App() {
  const [activeTab, setActiveTab] = useState<TabId>('home');

  let screen: React.ReactNode;

  switch (activeTab) {
    case 'chat':
      screen = <ChatScreen />;
      break;
    case 'calendar':
      screen = <CalendarScreen />;
      break;
    case 'inbox':
      screen = <ProjectsScreen />;
      break;
    case 'settings':
      screen = <SettingsScreen />;
      break;
    case 'home':
    default:
      screen = <HomeScreen />;
      break;
  }

  return (
    <PhoneShell activeTab={activeTab} setActiveTab={setActiveTab}>
      {screen}
    </PhoneShell>
  );
}
