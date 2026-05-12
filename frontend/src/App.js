import { useState, useEffect } from "react";
import { DARK, LIGHT, Ic, ICONS, Toast } from "./components/UI";
import Home from "./pages/Home";
import Analyzer from "./pages/Analyzer";
import Compliance from "./pages/Compliance";
import Evidence from "./pages/Evidence";
import CaseLaws from "./pages/CaseLaws";
import Dashboard from "./pages/Dashboard";
import Generators from "./pages/Generators";
import Billing from "./pages/Billing";
import Research from "./pages/Research";
import Editor from "./pages/Editor";
import Matters from "./pages/Matters";
import Tasks from "./pages/Tasks";
import Calendar from "./pages/Calendar";
import Footer from "./components/Footer";

// ── Theme ─────────────────────────────────────────────────────────────────────
const T = {
  dark: {
    ...DARK,
    amber: "#fbbf24",
    amberDim: "#2d1f07",
  },
  light: {
    ...LIGHT,
    amber: "#d97706",
    amberDim: "#fef3c7",
  },
};

const LINKS = [
  { id: "home", label: "Home", icon: "home" },
  { id: "dashboard", label: "Dashboard", icon: "grid" },
  { id: "matters", label: "Matters", icon: "grid" },
  { id: "tasks", label: "Tasks", icon: "check" },
  { id: "calendar", label: "Calendar", icon: "doc" },
  { id: "editor", label: "Editor", icon: "file" },
  { id: "research", label: "Research", icon: "book" },
  {
    id: "ai_tools",
    label: "AI Tools",
    icon: "search",
    subLinks: [
      { id: "analyzer", label: "Analyzer", icon: "search" },
      { id: "generators", label: "Generators", icon: "doc" },
      { id: "compliance", label: "Compliance", icon: "shield" },
      { id: "evidence", label: "Evidence", icon: "camera" },
      { id: "caselaws", label: "Case Laws", icon: "book" },
      { id: "billing", label: "Billing", icon: "file" }
    ]
  },
];

// ── Scales of Justice SVG ─────────────────────────────────────────────────────
const ScalesLogo = () => (
  <svg width="20" height="20" viewBox="0 0 32 32" fill="none">
    {/* Pillar */}
    <rect x="15.2" y="3.5" width="1.6" height="21" rx="0.8" fill="white" opacity="0.95" />
    {/* Base */}
    <rect x="8" y="24.5" width="16" height="2.2" rx="1.1" fill="white" opacity="0.88" />
    <rect x="5.5" y="26.7" width="21" height="1.4" rx="0.7" fill="white" opacity="0.6" />
    {/* Horizontal beam */}
    <rect x="3.5" y="7.5" width="25" height="1.8" rx="0.9" fill="white" opacity="0.95" />
    {/* Top cap */}
    <circle cx="16" cy="4.5" r="2" fill="white" opacity="0.95" />
    {/* Left chain */}
    <line x1="6.5" y1="9.3" x2="6.5" y2="15.5" stroke="white" strokeWidth="1.2" strokeLinecap="round" opacity="0.85" />
    {/* Right chain */}
    <line x1="25.5" y1="9.3" x2="25.5" y2="15.5" stroke="white" strokeWidth="1.2" strokeLinecap="round" opacity="0.85" />
    {/* Left pan arc */}
    <path d="M3 15.5 Q6.5 21.5 10 15.5" stroke="white" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" fill="rgba(255,255,255,0.1)" />
    {/* Right pan arc */}
    <path d="M22 15.5 Q25.5 21.5 29 15.5" stroke="white" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" fill="rgba(255,255,255,0.1)" />
    {/* Pan rim lines */}
    <line x1="3" y1="15.5" x2="10" y2="15.5" stroke="white" strokeWidth="0.9" opacity="0.35" />
    <line x1="22" y1="15.5" x2="29" y2="15.5" stroke="white" strokeWidth="0.9" opacity="0.35" />
  </svg>
);

// ── Navbar ────────────────────────────────────────────────────────────────────
const Nav = ({ page, go, theme, toggle, t }) => {
  const [open, setOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const fn = () => setScrolled(window.scrollY > 10);
    window.addEventListener("scroll", fn, { passive: true });
    return () => window.removeEventListener("scroll", fn);
  }, []);

  useEffect(() => { setOpen(false); }, [page]);

  const isDark = theme === "dark";

  return (
    <>
      <style>{`
        /* ── Nav base ── */
        .ns-nav {
          position: fixed; top: 0; left: 0; right: 0; z-index: 1000;
          height: 60px;
          display: flex; align-items: center;
          padding: 0 28px;
          background: ${isDark ? "rgba(9,12,18,0.88)" : "rgba(255,255,255,0.88)"};
          backdrop-filter: blur(24px) saturate(180%);
          -webkit-backdrop-filter: blur(24px) saturate(180%);
          border-bottom: 1px solid ${t.border};
          font-family: 'DM Sans', system-ui, sans-serif;
          transition: box-shadow 0.3s, background 0.3s;
        }
        .ns-nav.scrolled {
          background: ${isDark ? "rgba(9,12,18,0.97)" : "rgba(255,255,255,0.97)"};
          box-shadow: ${isDark
          ? "0 1px 0 rgba(255,255,255,0.05), 0 8px 32px rgba(0,0,0,0.4)"
          : "0 1px 0 rgba(0,0,0,0.06), 0 4px 20px rgba(0,0,0,0.08)"};
        }

        /* ── Brand ── */
        .ns-brand {
          display: flex; align-items: center; gap: 10px;
          cursor: pointer; background: none; border: none; padding: 0;
          flex-shrink: 0; margin-right: 8px;
          text-decoration: none;
        }
        .ns-logo {
          width: 36px; height: 36px; border-radius: 10px;
          background: linear-gradient(150deg, ${t.blue} 0%, #0d1e5a 100%);
          display: flex; align-items: center; justify-content: center;
          flex-shrink: 0; position: relative; overflow: hidden;
          box-shadow: 0 2px 12px ${t.blue}50, inset 0 1px 0 rgba(255,255,255,0.15);
          transition: transform 0.22s cubic-bezier(0.34,1.56,0.64,1), box-shadow 0.22s;
        }
        .ns-logo::after {
          content: '';
          position: absolute; top: 0; left: 0; right: 0; height: 45%;
          background: linear-gradient(to bottom, rgba(255,255,255,0.14), transparent);
        }
        .ns-brand:hover .ns-logo {
          transform: scale(1.08) rotate(-4deg);
          box-shadow: 0 5px 20px ${t.blue}66, inset 0 1px 0 rgba(255,255,255,0.15);
        }
        .ns-brandtext { display: flex; flex-direction: column; gap: 0; text-align: left; }
        .ns-brandname {
          font-size: 16.5px; font-weight: 900; line-height: 1.15;
          color: ${t.text}; letter-spacing: -0.04em;
        }
        .ns-brandname span { color: ${t.blue}; }
        .ns-brandsub {
          font-size: 8px; font-weight: 700; letter-spacing: 0.16em;
          text-transform: uppercase; color: ${t.muted};
        }

        /* ── Separator ── */
        .ns-divider {
          width: 1px; height: 22px; background: ${t.border};
          margin: 0 20px; flex-shrink: 0;
        }

        /* ── Desktop links ── */
        .ns-links { display: flex; align-items: center; gap: 1px; flex: 1; }
        .ns-link {
          display: inline-flex; align-items: center; gap: 6px;
          padding: 6px 12px; border-radius: 8px;
          font-size: 13px; font-weight: 600;
          color: ${t.sub}; background: transparent;
          border: 1px solid transparent;
          cursor: pointer; white-space: nowrap;
          font-family: 'DM Sans', system-ui, sans-serif;
          letter-spacing: -0.01em;
          transition: color 0.12s, background 0.12s, border-color 0.12s;
          position: relative;
        }
        .ns-link:hover {
          color: ${t.text};
          background: ${isDark ? "rgba(255,255,255,0.05)" : "rgba(0,0,0,0.04)"};
        }
        .ns-link.on {
          color: ${t.blue};
          background: ${t.blue}18;
          border-color: ${t.blue}33;
        }
        .ns-link.on::after {
          content: '';
          position: absolute; bottom: -1px; left: 12px; right: 12px;
          height: 2px; background: ${t.blue};
          border-radius: 2px 2px 0 0;
        }

        .ns-link-wrapper { position: relative; display: inline-flex; height: 100%; align-items: center; }
        .ns-dropdown {
          position: absolute; top: 100%; left: 0;
          background: ${isDark ? "rgba(18,24,38,0.98)" : "rgba(255,255,255,0.98)"};
          border: 1px solid ${t.border};
          border-radius: 12px; padding: 6px;
          display: flex; flex-direction: column; gap: 2px;
          box-shadow: 0 10px 32px rgba(0,0,0,0.2);
          min-width: 160px;
          opacity: 0; pointer-events: none; transform: translateY(-4px);
          transition: all 0.2s cubic-bezier(0.34,1.56,0.64,1);
          backdrop-filter: blur(16px);
        }
        .ns-link-wrapper:hover .ns-dropdown {
          opacity: 1; pointer-events: auto; transform: translateY(0);
        }
        .ns-drop-btn {
          display: flex; align-items: center; gap: 10px;
          padding: 8px 12px; border-radius: 8px; border: none;
          background: transparent; color: ${t.sub};
          font-size: 13px; font-weight: 600; cursor: pointer;
          text-align: left; width: 100%; font-family: 'DM Sans', sans-serif;
          transition: background 0.15s, color 0.15s;
        }
        .ns-drop-btn:hover {
          background: ${t.blue}18; color: ${t.text};
        }


        /* ── Right controls ── */
        .ns-right { display: flex; align-items: center; gap: 8px; margin-left: auto; }

        .ns-pill {
          display: inline-flex; align-items: center; gap: 5px;
          padding: 4px 10px; border-radius: 6px;
          background: ${t.blue}14; border: 1px solid ${t.blue}2a;
          font-size: 9.5px; font-weight: 800; color: ${t.blue};
          letter-spacing: 0.08em; font-family: 'DM Sans', sans-serif;
          user-select: none;
        }
        .ns-dot {
          width: 5px; height: 5px; border-radius: 50%;
          background: ${t.blue}; flex-shrink: 0;
          animation: ndot 2.4s ease-in-out infinite;
        }
        @keyframes ndot { 0%,100%{opacity:1;transform:scale(1)} 50%{opacity:0.3;transform:scale(0.7)} }

        .ns-toggle {
          width: 34px; height: 34px; border-radius: 8px;
          display: flex; align-items: center; justify-content: center;
          background: ${t.surfaceUp}; border: 1.5px solid ${t.border};
          cursor: pointer; transition: all 0.15s; flex-shrink: 0;
        }
        .ns-toggle:hover {
          border-color: ${t.borderHover};
          background: ${t.blue}10;
        }

        .ns-burger {
          display: none; width: 34px; height: 34px; border-radius: 8px;
          align-items: center; justify-content: center;
          background: none; border: none; cursor: pointer; padding: 0;
          color: ${t.sub}; flex-shrink: 0;
        }

        /* ── Mobile drawer ── */
        .ns-drawer {
          position: fixed; top: 60px; left: 0; right: 0; z-index: 998;
          background: ${t.surface};
          border-bottom: 1px solid ${t.border};
          padding: 8px 12px 14px;
          display: flex; flex-direction: column; gap: 2px;
          box-shadow: 0 12px 32px rgba(0,0,0,0.2);
          animation: ndrawer 0.18s ease;
        }
        @keyframes ndrawer {
          from { opacity: 0; transform: translateY(-8px); }
          to   { opacity: 1; transform: none; }
        }
        .ns-dlink {
          display: flex; align-items: center; gap: 12px;
          padding: 11px 14px; border-radius: 9px;
          font-size: 14px; font-weight: 600; color: ${t.sub};
          background: transparent; border: none;
          cursor: pointer; text-align: left; width: 100%;
          font-family: 'DM Sans', system-ui, sans-serif;
          transition: all 0.12s;
        }
        .ns-dlink:hover { background: ${t.blue}0a; color: ${t.text}; }
        .ns-dlink.on    { background: ${t.blue}18; color: ${t.blue}; }

        /* ── Responsive ── */
        @media (max-width: 800px) {
          .ns-links   { display: none !important; }
          .ns-divider { display: none !important; }
          .ns-pill    { display: none !important; }
          .ns-burger  { display: flex !important; }
          .ns-brand   { margin-right: auto !important; }
          .ns-nav     { padding: 0 16px !important; }
        }
      `}</style>

      <nav className={`ns-nav${scrolled ? " scrolled" : ""}`}>

        {/* Logo + brand */}
        <button className="ns-brand" onClick={() => go("home")}>
          <div className="ns-logo">
            <ScalesLogo />
          </div>
          <div className="ns-brandtext">
            <div className="ns-brandname">Nyaya<span>Setu</span></div>
            <div className="ns-brandsub">Bridge to Justice</div>
          </div>
        </button>

        <div className="ns-divider" />

        {/* Desktop nav */}
        <div className="ns-links">
          {LINKS.map(l => l.subLinks ? (
            <div key={l.id} className="ns-link-wrapper">
              <button
                className={`ns-link${(page === l.id || l.subLinks.some(s => s.id === page)) ? " on" : ""}`}
                style={{ cursor: "default" }}
              >
                <Ic d={ICONS[l.icon]} size={12} color={(page === l.id || l.subLinks.some(s => s.id === page)) ? t.blue : "inherit"} sw={2} />
                {l.label}
              </button>
              <div className="ns-dropdown">
                {l.subLinks.map(sub => (
                  <button key={sub.id} className="ns-drop-btn" onClick={() => go(sub.id)}>
                    <Ic d={ICONS[sub.icon]} size={14} />
                    {sub.label}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <button
              key={l.id}
              className={`ns-link${page === l.id ? " on" : ""}`}
              onClick={() => go(l.id)}
            >
              <Ic d={ICONS[l.icon]} size={12} color={page === l.id ? t.blue : "inherit"} sw={2} />
              {l.label}
            </button>
          ))}
        </div>

        {/* Right */}
        <div className="ns-right">
          <div className="ns-pill">
            <div className="ns-dot" /> BNS 2023
          </div>
          <button className="ns-toggle" onClick={toggle} title="Toggle theme">
            <Ic d={ICONS[theme === "dark" ? "sun" : "moon"]} size={14} color={t.sub} />
          </button>
          <button className="ns-burger" onClick={() => setOpen(o => !o)}>
            <Ic d={ICONS[open ? "x" : "menu"]} size={19} color={t.sub} />
          </button>
        </div>
      </nav>

      {/* Mobile drawer */}
      {open && (
        <div className="ns-drawer">
          {LINKS.map(l => l.subLinks ? (
            <React.Fragment key={l.id}>
              <div className="ns-dlink" style={{ opacity: 0.5 }}>{l.label}</div>
              {l.subLinks.map(sub => (
                <button
                  key={sub.id}
                  className={`ns-dlink${page === sub.id ? " on" : ""}`}
                  style={{ paddingLeft: 32 }}
                  onClick={() => { go(sub.id); setOpen(false); }}
                >
                  <Ic d={ICONS[sub.icon]} size={16} color={page === sub.id ? t.blue : t.sub} sw={1.8} />
                  {sub.label}
                </button>
              ))}
            </React.Fragment>
          ) : (
            <button
              key={l.id}
              className={`ns-dlink${page === l.id ? " on" : ""}`}
              onClick={() => { go(l.id); setOpen(false); }}
            >
              <Ic d={ICONS[l.icon]} size={16} color={page === l.id ? t.blue : t.sub} sw={1.8} />
              {l.label}
            </button>
          ))}
        </div>
      )}
    </>
  );
};

// ── App root ──────────────────────────────────────────────────────────────────
function App() {
  const [theme, setTheme] = useState("dark");
  const [page, setPage] = useState("home");
  const [toast, setToast] = useState(null);

  const [analyzerState, setAnalyzerState] = useState({ file: null, result: null, qaHist: [], err: null });
  const [complianceState, setComplianceState] = useState({ text: "", file: null, result: null, mode: "text" });
  const [evidenceState, setEvidenceState] = useState({ file: null, prev: null, cert: null, name: "", brief: "" });
  const [caseLawState, setCaseLawState] = useState({ q: "", results: [], searched: "" });

  const t = T[theme];

  const showToast = (msg, type) => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 4000);
  };

  const pages = {
    home: <Home t={t} go={setPage} />,
    dashboard: <Dashboard t={t} toast={showToast} />,
    matters: <Matters t={t} toast={showToast} />,
    tasks: <Tasks t={t} toast={showToast} />,
    calendar: <Calendar t={t} toast={showToast} />,
    research: <Research t={t} toast={showToast} />,
    editor: <Editor t={t} toast={showToast} />,
    generators: <Generators t={t} toast={showToast} />,
    billing: <Billing t={t} toast={showToast} />,
    analyzer: <Analyzer t={t} toast={showToast} state={analyzerState} setState={setAnalyzerState} />,
    compliance: <Compliance t={t} toast={showToast} state={complianceState} setState={setComplianceState} />,
    evidence: <Evidence t={t} toast={showToast} state={evidenceState} setState={setEvidenceState} />,
    caselaws: <CaseLaws t={t} toast={showToast} state={caseLawState} setState={setCaseLawState} />,
  };

  return (
    <div style={{
      minHeight: "100vh",
      background: t.bg,
      color: t.text,
      fontFamily: "'DM Sans', system-ui, sans-serif",
      display: "flex",
      flexDirection: "column"
    }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;0,9..40,800;0,9..40,900;1,9..40,400&family=DM+Serif+Display&display=swap');
        * { box-sizing: border-box; margin: 0; padding: 0; }
        @keyframes spin    { to { transform: rotate(360deg); } }
        @keyframes fadeUp  { from { opacity: 0; transform: translateY(18px); } to { opacity: 1; transform: translateY(0); } }
        @keyframes slideUp { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
        @keyframes pulse   { 0%,100% { opacity: 1; } 50% { opacity: 0.4; } }
        input:focus, textarea:focus {
          outline: none;
          border-color: ${t.blue} !important;
          box-shadow: 0 0 0 3px ${t.blue}18 !important;
        }
        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: ${t.border}; border-radius: 4px; }
        ::-webkit-scrollbar-thumb:hover { background: ${t.borderHover}; }
        ::selection { background: ${t.blue}3a; color: ${t.text}; }
        button { font-family: inherit; }
        a { font-family: inherit; }
        html, body, #root { 
          min-height: 100vh; 
          background: ${t.bg}; 
        }
      `}</style>

      <Nav page={page} go={setPage} theme={theme} toggle={() => setTheme(theme === "dark" ? "light" : "dark")} t={t} />

      <main style={{
        paddingTop: 60,
        flex: 1,
        display: "flex",
        flexDirection: "column"
      }}>
        {pages[page]}
      </main>

      <Footer t={t} go={setPage} />

      {toast && <Toast msg={toast.msg} type={toast.type} t={t} onClose={() => setToast(null)} />}
    </div>
  );
}

export default App;