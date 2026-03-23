import { useState } from "react";
import { DARK, LIGHT, Ic, ICONS, Toast } from "./components/UI";
import Home       from "./pages/Home";
import Analyzer   from "./pages/Analyzer";
import Compliance from "./pages/Compliance";
import Evidence   from "./pages/Evidence";
import CaseLaws   from "./pages/CaseLaws";
import Footer     from "./components/Footer";

const T = {
  dark:  { ...DARK,  amber: "#fbbf24", amberDim: "#2d1f07" },
  light: { ...LIGHT, amber: "#d97706", amberDim: "#fef3c7" },
};

const LINKS = [
  { id: "home",       label: "Home",       icon: "home"   },
  { id: "analyzer",   label: "Analyzer",   icon: "doc"    },
  { id: "compliance", label: "Compliance", icon: "shield" },
  { id: "evidence",   label: "Evidence",   icon: "camera" },
  { id: "caselaws",   label: "Case Laws",  icon: "search" },
];

const Nav = ({ page, go, theme, toggle, t }) => {
  const [open, setOpen] = useState(false);
  return (
    <>
      <nav style={{
        position: "fixed", top: 0, left: 0, right: 0, zIndex: 1000,
        background: t.nav, backdropFilter: "blur(20px) saturate(180%)",
        borderBottom: `1px solid ${t.border}`,
        height: 64, display: "flex", alignItems: "center",
        padding: "0 28px", justifyContent: "space-between",
      }}>
        <button onClick={() => go("home")} style={{ background: "none", border: "none", cursor: "pointer", display: "flex", alignItems: "center", gap: 12, padding: 0, flexShrink: 0 }}>
          <div style={{ width: 36, height: 36, borderRadius: 10, background: `linear-gradient(135deg, ${t.blue} 0%, #1a3580 100%)`, display: "flex", alignItems: "center", justifyContent: "center", boxShadow: `0 4px 14px ${t.blue}55` }}>
            <Ic d={ICONS.scale} size={17} color="#fff" sw={2} />
          </div>
          <div>
            <div style={{ fontSize: 17, fontWeight: 900, color: t.text, letterSpacing: "-0.03em", lineHeight: 1.1 }}>Nyaya<span style={{ color: t.blue }}>Setu</span></div>
            <div style={{ fontSize: 9, color: t.sub, fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase" }}>Bridge to Justice</div>
          </div>
        </button>

        <div style={{ display: "flex", gap: 2 }} className="dnav">
          {LINKS.map(l => (
            <button key={l.id} onClick={() => go(l.id)} style={{
              background: page === l.id ? `${t.blue}18` : "transparent",
              border: `1px solid ${page === l.id ? `${t.blue}44` : "transparent"}`,
              color: page === l.id ? t.blue : t.sub,
              borderRadius: 9, padding: "7px 15px", cursor: "pointer",
              fontSize: 13, fontWeight: 700, fontFamily: "inherit", transition: "all 0.15s",
              display: "flex", alignItems: "center", gap: 6,
            }}
              onMouseEnter={e => { if (page !== l.id) { e.currentTarget.style.background = `${t.blue}0a`; e.currentTarget.style.color = t.text; } }}
              onMouseLeave={e => { if (page !== l.id) { e.currentTarget.style.background = "transparent"; e.currentTarget.style.color = t.sub; } }}
            >
              <Ic d={ICONS[l.icon]} size={13} color={page === l.id ? t.blue : "inherit"} />
              {l.label}
            </button>
          ))}
        </div>

        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <div style={{ padding: "4px 12px", borderRadius: 99, background: `linear-gradient(90deg, ${t.blue}, #1a3580)`, color: "#fff", fontSize: 10, fontWeight: 800, letterSpacing: "0.08em", textTransform: "uppercase", boxShadow: `0 2px 8px ${t.blue}44` }} className="dnav">BNS 2023</div>
          <button onClick={toggle} style={{ background: t.surfaceUp, border: `1.5px solid ${t.border}`, borderRadius: 9, padding: "7px 10px", cursor: "pointer", display: "flex", alignItems: "center" }}
            onMouseEnter={e => e.currentTarget.style.borderColor = t.borderHover}
            onMouseLeave={e => e.currentTarget.style.borderColor = t.border}
          >
            <Ic d={ICONS[theme === "dark" ? "sun" : "moon"]} size={14} color={t.sub} />
          </button>
          <button onClick={() => setOpen(!open)} className="mnav" style={{ background: "none", border: "none", cursor: "pointer", color: t.sub, display: "none", padding: 4 }}>
            <Ic d={ICONS[open ? "x" : "menu"]} size={20} />
          </button>
        </div>
      </nav>

      {open && (
        <div style={{ position: "fixed", top: 64, left: 0, right: 0, zIndex: 999, background: t.surface, borderBottom: `1px solid ${t.border}`, padding: "10px 16px 16px", display: "flex", flexDirection: "column", gap: 4 }}>
          {LINKS.map(l => (
            <button key={l.id} onClick={() => { go(l.id); setOpen(false); }} style={{ background: page === l.id ? `${t.blue}18` : "transparent", border: "none", color: page === l.id ? t.blue : t.sub, borderRadius: 9, padding: "12px 16px", cursor: "pointer", fontSize: 14, fontWeight: 700, textAlign: "left", fontFamily: "inherit", display: "flex", alignItems: "center", gap: 10 }}>
              <Ic d={ICONS[l.icon]} size={16} color={page === l.id ? t.blue : t.sub} />
              {l.label}
            </button>
          ))}
        </div>
      )}
    </>
  );
};

function App() {
  const [theme, setTheme] = useState("dark");
  const [page,  setPage]  = useState("home");
  const [toast, setToast] = useState(null);

  // ── Persisted state for each tool ─────────────────────────────────────────
  const [analyzerState,   setAnalyzerState]   = useState({ file: null, result: null, qaHist: [], err: null });
  const [complianceState, setComplianceState] = useState({ text: "", file: null, result: null, mode: "text" });
  const [evidenceState,   setEvidenceState]   = useState({ file: null, prev: null, cert: null, name: "", brief: "" });
  const [caseLawState,    setCaseLawState]    = useState({ q: "", results: [], searched: "" });

  const t = T[theme];

  const showToast = (msg, type) => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 4000);
  };

  const pages = {
    home:       <Home       t={t} go={setPage} />,
    analyzer:   <Analyzer   t={t} toast={showToast} state={analyzerState}   setState={setAnalyzerState} />,
    compliance: <Compliance t={t} toast={showToast} state={complianceState} setState={setComplianceState} />,
    evidence:   <Evidence   t={t} toast={showToast} state={evidenceState}   setState={setEvidenceState} />,
    caselaws:   <CaseLaws   t={t} toast={showToast} state={caseLawState}    setState={setCaseLawState} />,
  };

  return (
    <div style={{ minHeight: "100vh", background: t.bg, color: t.text, fontFamily: "'DM Sans','Inter',system-ui,sans-serif" }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800;900&family=DM+Serif+Display&display=swap');
        * { box-sizing: border-box; margin: 0; padding: 0; }
        @keyframes spin    { to { transform: rotate(360deg); } }
        @keyframes fadeUp  { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
        @keyframes slideUp { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: translateY(0); } }
        @keyframes pulse   { 0%,100% { opacity: 1; transform: scale(1); } 50% { opacity: 0.6; transform: scale(0.85); } }
        input:focus, textarea:focus { outline: none; border-color: ${t.blue} !important; box-shadow: 0 0 0 3px ${t.blue}1a !important; }
        ::-webkit-scrollbar { width: 5px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: ${t.border}; border-radius: 3px; }
        ::-webkit-scrollbar-thumb:hover { background: ${t.borderHover}; }
        @media (max-width: 640px) { .dnav { display: none !important; } .mnav { display: flex !important; } }
        ::selection { background: ${t.blue}44; color: ${t.text}; }
      `}</style>

      <Nav page={page} go={setPage} theme={theme} toggle={() => setTheme(theme === "dark" ? "light" : "dark")} t={t} />
      <main style={{ paddingTop: 64 }}>
        {pages[page]}
      </main>
      {page === "home" && <Footer t={t} go={setPage} />}
      {toast && <Toast msg={toast.msg} type={toast.type} t={t} onClose={() => setToast(null)} />}
    </div>
  );
}

export default App;