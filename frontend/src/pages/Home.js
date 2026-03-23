import { useState, useEffect, useRef } from "react";
import { Ic, ICONS, Tag } from "../components/UI";

// ── Scroll reveal hook ────────────────────────────────────────────────────────
function useReveal(threshold = 0.15) {
  const ref = useRef(null);
  const [visible, setVisible] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const obs = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) { setVisible(true); obs.disconnect(); } },
      { threshold }
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, [threshold]);
  return [ref, visible];
}

// ── Reveal wrapper ────────────────────────────────────────────────────────────
function Reveal({ children, delay = 0, direction = "up", style = {} }) {
  const [ref, visible] = useReveal(0.12);
  const transforms = { up: "translateY(32px)", left: "translateX(-32px)", right: "translateX(32px)", none: "none" };
  return (
    <div ref={ref} style={{
      opacity: visible ? 1 : 0,
      transform: visible ? "none" : transforms[direction],
      transition: `opacity 0.65s ease ${delay}s, transform 0.65s cubic-bezier(0.22,1,0.36,1) ${delay}s`,
      ...style,
    }}>
      {children}
    </div>
  );
}

// ── Animated counter ──────────────────────────────────────────────────────────
function Counter({ target, suffix = "" }) {
  const [val, setVal] = useState(0);
  const [ref, visible] = useReveal(0.3);
  useEffect(() => {
    if (!visible) return;
    const num = parseInt(target.replace(/[^0-9]/g, "")) || 0;
    let start = 0;
    const step = Math.ceil(num / 40);
    const id = setInterval(() => {
      start = Math.min(start + step, num);
      setVal(start);
      if (start >= num) clearInterval(id);
    }, 30);
    return () => clearInterval(id);
  }, [visible, target]);
  const prefix = target.match(/^[^0-9]*/)?.[0] || "";
  const suf = target.match(/[^0-9]*$/)?.[0] || suffix;
  return <span ref={ref}>{prefix}{val}{suf}</span>;
}

// ── Section heading ───────────────────────────────────────────────────────────
function SectionHeading({ eyebrow, title, sub, t, center = false }) {
  return (
    <Reveal>
      <div style={{ textAlign: center ? "center" : "left", marginBottom: 52 }}>
        <div style={{
          display: "inline-flex", alignItems: "center", gap: 7,
          padding: "4px 13px", borderRadius: 99,
          background: `${t.blue}14`, border: `1px solid ${t.blue}2e`,
          marginBottom: 16,
        }}>
          <span style={{ fontSize: 10, color: t.blue, fontWeight: 800, letterSpacing: "0.1em", textTransform: "uppercase" }}>{eyebrow}</span>
        </div>
        <h2 style={{
          fontFamily: "'DM Serif Display', Georgia, serif",
          fontSize: "clamp(1.8rem,3.5vw,2.6rem)",
          fontWeight: 400, color: t.text, lineHeight: 1.2,
          margin: "0 0 14px", letterSpacing: "-0.01em",
        }}>{title}</h2>
        {sub && <p style={{ fontSize: 15, color: t.sub, maxWidth: 520, margin: center ? "0 auto" : 0, lineHeight: 1.8 }}>{sub}</p>}
      </div>
    </Reveal>
  );
}

// ── Data ──────────────────────────────────────────────────────────────────────
const STATS = [
  { value: "3,254", label: "Legal chunks indexed",  icon: "doc",    color: "#4d7cfe" },
  { value: "70+",   label: "IPC → BNS mappings",    icon: "shield", color: "#34d399" },
  { value: "18",    label: "BNS offences covered",  icon: "scale",  color: "#fbbf24" },
  { value: "100%",  label: "Local — zero data sent", icon: "camera", color: "#a78bfa" },
];

const FEATURES = [
  {
    id: "analyzer", icon: "doc", color: "#4d7cfe",
    title: "Document Analyzer",
    badge: "AI Risk Scoring",
    desc: "Upload any legal document — rental agreement, employment letter, FIR, loan contract. Every clause is scored Safe, Caution, High Risk, or Illegal with a plain-English explanation and actionable suggestion.",
    bullets: ["Clause-by-clause risk breakdown", "IRAC reasoning via Llama-3", "Inline Q&A about the document", "Relevant case law per clause"],
    who: "Tenants, employees, small business owners",
  },
  {
    id: "compliance", icon: "shield", color: "#34d399",
    title: "BNS Compliance Checker",
    badge: "IPC → BNS 2023",
    desc: "Courts are rejecting FIRs and petitions that still cite IPC sections — because IPC was repealed in December 2023. Paste any legal text to instantly detect outdated references and get the correct BNS equivalent.",
    bullets: ["70+ IPC/CrPC/IEA → BNS/BNSS/BSA mappings", "Compliance score 0–100", "Abolished sections flagged clearly", "Try with sample FIR text"],
    who: "Lawyers, paralegals, police officers",
  },
  {
    id: "evidence", icon: "camera", color: "#fbbf24",
    title: "Evidence Certificate",
    badge: "BSA Section 63",
    desc: "Digital photos and screenshots submitted to police are routinely dismissed for lack of certification. Under BSA Section 63, electronic evidence requires a cryptographic hash. We generate it before any processing — chain of custody intact.",
    bullets: ["SHA-256 computed before any modification", "EXIF metadata extracted (GPS, device, time)", "PDF certificate for court submission", "Verify with standard sha256sum tool"],
    who: "Harassment victims, theft complainants, businesses",
  },
  {
    id: "caselaws", icon: "search", color: "#a78bfa",
    title: "Case Law Search",
    badge: "IndianKanoon Live",
    desc: "Search thousands of Indian High Court and Supreme Court judgments by topic. Results are fetched live from IndianKanoon and summarised in plain English by Llama-3 running locally — no data sent to the cloud.",
    bullets: ["Live IndianKanoon API integration", "Llama-3 plain-English summaries", "Direct links to full judgments", "Suggested search topics included"],
    who: "Law students, advocates, researchers",
  },
];

const RESEARCH_GAPS = [
  { num: "01", title: "No BNS 2023 knowledge", desc: "Every major LLM (GPT-4, Gemini, Claude) was trained before December 2023. None of them know BNS, BNSS, or BSA. NyayaSetu was built on the actual statutes.", color: "#f87171" },
  { num: "02", title: "91% hallucination rate", desc: "GPT-4 gets Indian law wrong 91% of the time (Jones et al., 2024). Our RAG engine is grounded in the actual PDF text of BNS, BNSS, and BSA — not training data.", color: "#fbbf24" },
  { num: "03", title: "No IPC→BNS tool existed", desc: "Lawyers in India still cite IPC sections in 2025. Courts are returning petitions. No tool existed to automate this migration before NyayaSetu.", color: "#34d399" },
  { num: "04", title: "Digital evidence dismissed", desc: "BSA Section 63 requires SHA-256 certification for digital evidence to be court-admissible. No citizen-facing app existed to generate these certificates.", color: "#a78bfa" },
  { num: "05", title: "All legal AI targets lawyers", desc: "ContractNLI, LegalBERT, InLegalBERT — all built for researchers and lawyers. NyayaSetu is built for the citizen who doesn't have a lawyer yet.", color: "#4d7cfe" },
  { num: "06", title: "US/EU tools, not India", desc: "CUAD, DoNotPay, ContractNLI — all trained on US/EU contracts and law. Indian legal language, Indian statutes, Indian courts. NyayaSetu is built for India.", color: "#fb923c" },
];

const HOW_STEPS = [
  { icon: "upload", title: "Upload or paste", desc: "Drop a PDF, image, or paste any legal text — FIR, notice, agreement, petition.", color: "#4d7cfe" },
  { icon: "scale",  title: "AI analysis",    desc: "Llama-3 reads every clause, cross-references BNS/BNSS/BSA, and identifies risks.", color: "#34d399" },
  { icon: "doc",    title: "Plain English",  desc: "Get a clear, jargon-free breakdown with exact section references and what to do.", color: "#fbbf24" },
  { icon: "shield", title: "Take action",    desc: "Download your certificate, share the report, or search relevant case law.", color: "#a78bfa" },
];

const COMPARE = [
  { tool: "GPT-4 / ChatGPT",    bns: false, ipc: false, hash: false, india: false, local: false },
  { tool: "Vakil.ai",           bns: false, ipc: false, hash: false, india: true,  local: false },
  { tool: "ContractNLI",        bns: false, ipc: false, hash: false, india: false, local: false },
  { tool: "InLegalBERT",        bns: false, ipc: false, hash: false, india: true,  local: false },
  { tool: "NyayaSetu ✦",        bns: true,  ipc: true,  hash: true,  india: true,  local: true  },
];

// ── Main component ────────────────────────────────────────────────────────────
export default function Home({ t, go }) {
  const [heroVisible, setHeroVisible] = useState(false);
  const [hovCard, setHovCard]         = useState(null);
  const [hovFeature, setHovFeature]   = useState(null);

  useEffect(() => {
    const id = setTimeout(() => setHeroVisible(true), 80);
    return () => clearTimeout(id);
  }, []);

  const isBold = t.text === "#e2e8f4"; // dark mode check

  return (
    <div style={{ fontFamily: "'DM Sans', system-ui, sans-serif" }}>

      {/* ══════════════ HERO ══════════════ */}
      <section style={{
        position: "relative", overflow: "hidden",
        padding: "96px 24px 100px",
        background: `linear-gradient(160deg, ${t.bg} 0%, ${t.surface} 60%, ${t.bg} 100%)`,
      }}>
        {/* Background grid */}
        <div style={{
          position: "absolute", inset: 0, pointerEvents: "none",
          backgroundImage: `linear-gradient(${t.border} 1px, transparent 1px), linear-gradient(90deg, ${t.border} 1px, transparent 1px)`,
          backgroundSize: "52px 52px", opacity: 0.35,
          maskImage: "radial-gradient(ellipse 80% 60% at 50% 0%, black 30%, transparent 100%)",
        }} />
        {/* Glow orbs */}
        <div style={{ position: "absolute", top: -120, left: "50%", transform: "translateX(-50%)", width: 600, height: 400, borderRadius: "50%", background: `radial-gradient(ellipse, ${t.blue}22 0%, transparent 70%)`, pointerEvents: "none" }} />
        <div style={{ position: "absolute", bottom: -80, right: "10%", width: 300, height: 300, borderRadius: "50%", background: `radial-gradient(ellipse, #a78bfa1a 0%, transparent 70%)`, pointerEvents: "none" }} />

        <div style={{ maxWidth: 900, margin: "0 auto", position: "relative", textAlign: "center" }}>
          {/* Eyebrow pill */}
          <div style={{
            opacity: heroVisible ? 1 : 0,
            transform: heroVisible ? "none" : "translateY(16px)",
            transition: "opacity 0.5s ease, transform 0.5s ease",
            display: "inline-flex", alignItems: "center", gap: 8,
            padding: "6px 16px", borderRadius: 99,
            background: `${t.blue}16`, border: `1px solid ${t.blue}33`,
            marginBottom: 28,
          }}>
            <span style={{ width: 6, height: 6, borderRadius: "50%", background: t.blue, display: "inline-block", animation: "pulse 2s ease infinite" }} />
            <span style={{ fontSize: 11, color: t.blue, fontWeight: 800, letterSpacing: "0.1em", textTransform: "uppercase" }}>
              Indian Legal AI · BNS 2023 · Runs Locally
            </span>
          </div>

          {/* Headline */}
          <h1 style={{
            fontFamily: "'DM Serif Display', Georgia, serif",
            fontSize: "clamp(2.6rem,6vw,4.4rem)",
            fontWeight: 400, lineHeight: 1.08, color: t.text,
            margin: "0 0 24px", letterSpacing: "-0.02em",
            opacity: heroVisible ? 1 : 0,
            transform: heroVisible ? "none" : "translateY(24px)",
            transition: "opacity 0.6s ease 0.1s, transform 0.6s cubic-bezier(0.22,1,0.36,1) 0.1s",
          }}>
            Legal clarity,<br />
            <span style={{
              color: t.blue,
              backgroundImage: `linear-gradient(135deg, ${t.blue}, #a78bfa)`,
              WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent",
            }}>
              without a lawyer.
            </span>
          </h1>

          {/* Sub */}
          <p style={{
            fontSize: 17, color: t.sub, maxWidth: 560, margin: "0 auto 40px",
            lineHeight: 1.85,
            opacity: heroVisible ? 1 : 0,
            transform: heroVisible ? "none" : "translateY(20px)",
            transition: "opacity 0.6s ease 0.2s, transform 0.6s ease 0.2s",
          }}>
            Understand legal documents. Check BNS 2023 compliance. Certify digital evidence.
            Search Indian case law — all running locally on your machine. Zero data leaves your device.
          </p>

          {/* CTA buttons */}
          <div style={{
            display: "flex", gap: 12, justifyContent: "center", flexWrap: "wrap", marginBottom: 64,
            opacity: heroVisible ? 1 : 0,
            transform: heroVisible ? "none" : "translateY(16px)",
            transition: "opacity 0.6s ease 0.3s, transform 0.6s ease 0.3s",
          }}>
            {[
              { label: "Analyze a Document", icon: "doc", fn: () => go("analyzer"), primary: true },
              { label: "Check BNS Compliance", icon: "shield", fn: () => go("compliance"), primary: false },
            ].map(btn => (
              <button key={btn.label} onClick={btn.fn} style={{
                padding: "13px 28px", borderRadius: 11,
                background: btn.primary ? t.blue : "transparent",
                color: btn.primary ? "#fff" : t.text,
                border: btn.primary ? "none" : `1.5px solid ${t.border}`,
                fontSize: 14, fontWeight: 700, cursor: "pointer",
                display: "flex", alignItems: "center", gap: 8,
                fontFamily: "inherit", transition: "all 0.2s",
                boxShadow: btn.primary ? `0 4px 20px ${t.blue}44` : "none",
              }}
                onMouseEnter={e => { e.currentTarget.style.transform = "translateY(-2px)"; if (btn.primary) e.currentTarget.style.boxShadow = `0 8px 28px ${t.blue}55`; else e.currentTarget.style.borderColor = t.borderHover; }}
                onMouseLeave={e => { e.currentTarget.style.transform = "translateY(0)"; if (btn.primary) e.currentTarget.style.boxShadow = `0 4px 20px ${t.blue}44`; else e.currentTarget.style.borderColor = t.border; }}
              >
                <Ic d={ICONS[btn.icon]} size={15} color={btn.primary ? "#fff" : t.sub} sw={2} />
                {btn.label}
              </button>
            ))}
          </div>

          {/* Stats row */}
          <div style={{
            display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 16,
            opacity: heroVisible ? 1 : 0,
            transform: heroVisible ? "none" : "translateY(20px)",
            transition: "opacity 0.6s ease 0.4s, transform 0.6s ease 0.4s",
          }} className="stat-grid">
            {STATS.map((s, i) => (
              <div key={i} style={{
                background: t.surface, border: `1.5px solid ${t.border}`,
                borderRadius: 14, padding: "20px 16px", textAlign: "center",
                transition: "border-color 0.2s, transform 0.2s",
              }}
                onMouseEnter={e => { e.currentTarget.style.borderColor = s.color + "55"; e.currentTarget.style.transform = "translateY(-2px)"; }}
                onMouseLeave={e => { e.currentTarget.style.borderColor = t.border; e.currentTarget.style.transform = "translateY(0)"; }}
              >
                <div style={{ width: 32, height: 32, borderRadius: 9, background: `${s.color}1a`, border: `1px solid ${s.color}33`, display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 10px" }}>
                  <Ic d={ICONS[s.icon]} size={14} color={s.color} />
                </div>
                <div style={{ fontSize: "1.6rem", fontWeight: 900, color: t.text, letterSpacing: "-0.03em", lineHeight: 1 }}>
                  <Counter target={s.value} />
                </div>
                <div style={{ fontSize: 11, color: t.sub, marginTop: 4, fontWeight: 500 }}>{s.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ══════════════ HOW IT WORKS ══════════════ */}
      <section style={{ padding: "96px 24px", background: t.bg }}>
        <div style={{ maxWidth: 1000, margin: "0 auto" }}>
          <SectionHeading
            eyebrow="How it works"
            title="Four steps to legal clarity"
            sub="No sign-up. No data collection. Everything runs on your local machine."
            t={t} center
          />
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 14 }} className="step-grid">
            {HOW_STEPS.map((s, i) => (
              <Reveal key={i} delay={i * 0.1}>
                <div style={{ textAlign: "center", padding: "28px 20px 24px", borderRadius: 16, background: t.surface, border: `1.5px solid ${t.border}`, position: "relative", transition: "border-color 0.2s, transform 0.2s" }}
                  onMouseEnter={e => { e.currentTarget.style.borderColor = s.color + "55"; e.currentTarget.style.transform = "translateY(-3px)"; }}
                  onMouseLeave={e => { e.currentTarget.style.borderColor = t.border; e.currentTarget.style.transform = "none"; }}
                >
                  {/* Step number */}
                  <div style={{ position: "absolute", top: -12, left: "50%", transform: "translateX(-50%)", width: 26, height: 26, borderRadius: "50%", background: s.color, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 10, fontWeight: 900, color: "#fff" }}>
                    {String(i + 1).padStart(2, "0")}
                  </div>
                  <div style={{ width: 48, height: 48, borderRadius: 14, background: `${s.color}1a`, border: `1px solid ${s.color}33`, display: "flex", alignItems: "center", justifyContent: "center", margin: "8px auto 16px" }}>
                    <Ic d={ICONS[s.icon]} size={20} color={s.color} />
                  </div>
                  <div style={{ fontSize: 14, fontWeight: 800, color: t.text, marginBottom: 8 }}>{s.title}</div>
                  <p style={{ fontSize: 12, color: t.sub, lineHeight: 1.7, margin: 0 }}>{s.desc}</p>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* ══════════════ FEATURES (alternating) ══════════════ */}
      <section style={{ padding: "96px 24px", background: t.surface }}>
        <div style={{ maxWidth: 1000, margin: "0 auto" }}>
          <SectionHeading
            eyebrow="The tools"
            title="Everything you need, nothing you don't"
            sub="Four standalone tools. Use one or all of them. No account required."
            t={t}
          />

          <div style={{ display: "flex", flexDirection: "column", gap: 80 }}>
            {FEATURES.map((f, i) => (
              <Reveal key={f.id} delay={0} direction={i % 2 === 0 ? "left" : "right"}>
                <div style={{ display: "grid", gridTemplateColumns: i % 2 === 0 ? "1fr 1fr" : "1fr 1fr", gap: 52, alignItems: "center" }} className="feat-grid">
                  {/* Text side */}
                  <div style={{ order: i % 2 === 0 ? 0 : 1 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 16 }}>
                      <div style={{ width: 40, height: 40, borderRadius: 11, background: `${f.color}1a`, border: `1px solid ${f.color}33`, display: "flex", alignItems: "center", justifyContent: "center" }}>
                        <Ic d={ICONS[f.icon]} size={18} color={f.color} />
                      </div>
                      <span style={{ fontSize: 10, fontWeight: 800, color: f.color, letterSpacing: "0.1em", textTransform: "uppercase", padding: "3px 10px", borderRadius: 6, background: `${f.color}14`, border: `1px solid ${f.color}22` }}>{f.badge}</span>
                    </div>
                    <h3 style={{ fontFamily: "'DM Serif Display', serif", fontSize: "clamp(1.5rem,2.5vw,2rem)", fontWeight: 400, color: t.text, margin: "0 0 14px", letterSpacing: "-0.01em" }}>{f.title}</h3>
                    <p style={{ fontSize: 14, color: t.sub, lineHeight: 1.85, margin: "0 0 20px" }}>{f.desc}</p>
                    <ul style={{ listStyle: "none", padding: 0, margin: "0 0 24px", display: "flex", flexDirection: "column", gap: 8 }}>
                      {f.bullets.map((b, bi) => (
                        <li key={bi} style={{ display: "flex", alignItems: "flex-start", gap: 9, fontSize: 13, color: t.sub }}>
                          <span style={{ width: 18, height: 18, borderRadius: "50%", background: `${f.color}1a`, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0, marginTop: 1 }}>
                            <Ic d={ICONS.check} size={9} color={f.color} sw={3} />
                          </span>
                          {b}
                        </li>
                      ))}
                    </ul>
                    <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
                      <button onClick={() => go(f.id)} style={{
                        padding: "10px 22px", borderRadius: 9, background: f.color,
                        color: "#fff", border: "none", fontSize: 13, fontWeight: 700,
                        cursor: "pointer", fontFamily: "inherit", transition: "all 0.15s",
                        display: "flex", alignItems: "center", gap: 7,
                      }}
                        onMouseEnter={e => { e.currentTarget.style.transform = "translateY(-1px)"; e.currentTarget.style.boxShadow = `0 6px 20px ${f.color}44`; }}
                        onMouseLeave={e => { e.currentTarget.style.transform = "none"; e.currentTarget.style.boxShadow = "none"; }}
                      >
                        Open tool <Ic d={ICONS.arrow} size={13} color="#fff" sw={2.5} />
                      </button>
                      <span style={{ fontSize: 11, color: t.muted }}>For: {f.who}</span>
                    </div>
                  </div>

                  {/* Visual side */}
                  <div style={{ order: i % 2 === 0 ? 1 : 0 }}>
                    <div style={{
                      borderRadius: 18, padding: "28px 24px",
                      background: isBold ? `linear-gradient(145deg, ${t.surface} 0%, ${t.surfaceUp} 100%)` : `linear-gradient(145deg, ${t.surfaceUp} 0%, ${t.bg} 100%)`,
                      border: `1.5px solid ${f.color}33`,
                      boxShadow: `0 20px 60px ${f.color}18`,
                      position: "relative", overflow: "hidden",
                    }}>
                      <div style={{ position: "absolute", top: -40, right: -40, width: 160, height: 160, borderRadius: "50%", background: `radial-gradient(circle, ${f.color}14 0%, transparent 70%)`, pointerEvents: "none" }} />
                      {/* Mock UI preview */}
                      <div style={{ marginBottom: 14 }}>
                        <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 14 }}>
                          {[f.color, t.border, t.border].map((c, ci) => (
                            <div key={ci} style={{ width: 9, height: 9, borderRadius: "50%", background: c }} />
                          ))}
                          <div style={{ flex: 1, height: 6, borderRadius: 3, background: t.border, marginLeft: 6 }} />
                        </div>
                        {/* Fake content lines */}
                        {[100, 85, 92, 70, 88].map((w, wi) => (
                          <div key={wi} style={{ display: "flex", gap: 8, marginBottom: 8, alignItems: "center" }}>
                            {wi === 0 && <div style={{ width: 28, height: 28, borderRadius: 7, background: `${f.color}22`, flexShrink: 0, display: "flex", alignItems: "center", justifyContent: "center" }}><Ic d={ICONS[f.icon]} size={12} color={f.color} /></div>}
                            <div style={{ height: wi === 0 ? 10 : 7, borderRadius: 3, background: wi === 0 ? `${f.color}44` : t.border, width: `${w}%`, maxWidth: wi === 0 ? "60%" : "100%" }} />
                            {wi > 0 && wi < 4 && (
                              <div style={{ padding: "2px 8px", borderRadius: 4, background: [null, `${f.color}22`, "#f8717122", "#34d39922", "#fbbf2422"][wi], border: `1px solid ${[null, `${f.color}33`, "#f8717133", "#34d39933", "#fbbf2433"][wi]}`, fontSize: 9, fontWeight: 700, color: [null, f.color, "#f87171", "#34d399", "#fbbf24"][wi], flexShrink: 0 }}>
                                {["", "Caution", "High Risk", "Safe", "Caution"][wi]}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                      <div style={{ padding: "10px 14px", borderRadius: 9, background: `${f.color}12`, border: `1px solid ${f.color}22`, fontSize: 11, color: f.color, fontWeight: 600, lineHeight: 1.6 }}>
                        💡 {f.bullets[0]}
                      </div>
                    </div>
                  </div>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* ══════════════ RESEARCH GAPS ══════════════ */}
      <section style={{ padding: "96px 24px", background: t.bg }}>
        <div style={{ maxWidth: 1000, margin: "0 auto" }}>
          <SectionHeading
            eyebrow="Why this exists"
            title="Six gaps no one had filled"
            sub="Every major legal AI tool failed Indian citizens in at least one critical way. NyayaSetu was built to address all six."
            t={t}
          />
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 16 }} className="gap-grid">
            {RESEARCH_GAPS.map((g, i) => (
              <Reveal key={i} delay={i * 0.07}>
                <div style={{
                  padding: "24px 22px", borderRadius: 14,
                  background: t.surface, border: `1.5px solid ${t.border}`,
                  transition: "border-color 0.2s, transform 0.2s",
                }}
                  onMouseEnter={e => { e.currentTarget.style.borderColor = g.color + "44"; e.currentTarget.style.transform = "translateY(-2px)"; }}
                  onMouseLeave={e => { e.currentTarget.style.borderColor = t.border; e.currentTarget.style.transform = "none"; }}
                >
                  <div style={{ fontSize: 11, fontWeight: 900, color: g.color, letterSpacing: "0.1em", marginBottom: 10, opacity: 0.7 }}>{g.num}</div>
                  <div style={{ fontSize: 14, fontWeight: 800, color: t.text, marginBottom: 8, lineHeight: 1.4 }}>{g.title}</div>
                  <p style={{ fontSize: 12, color: t.sub, lineHeight: 1.75, margin: 0 }}>{g.desc}</p>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* ══════════════ COMPARISON TABLE ══════════════ */}
      <section style={{ padding: "96px 24px", background: t.surface }}>
        <div style={{ maxWidth: 860, margin: "0 auto" }}>
          <SectionHeading
            eyebrow="Comparison"
            title="How NyayaSetu compares"
            sub="Every other tool is missing at least one thing that matters for Indian citizens."
            t={t} center
          />
          <Reveal>
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                <thead>
                  <tr style={{ borderBottom: `2px solid ${t.border}` }}>
                    {["Tool", "BNS 2023", "IPC→BNS", "Evidence Hash", "Indian Law", "Runs Locally"].map((h, i) => (
                      <th key={i} style={{ padding: "12px 16px", textAlign: i === 0 ? "left" : "center", color: t.muted, fontWeight: 700, fontSize: 11, textTransform: "uppercase", letterSpacing: "0.06em" }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {COMPARE.map((row, i) => {
                    const isUs = row.tool.includes("✦");
                    return (
                      <tr key={i} style={{ borderBottom: `1px solid ${t.border}`, background: isUs ? `${t.blue}0a` : "transparent", transition: "background 0.15s" }}
                        onMouseEnter={e => !isUs && (e.currentTarget.style.background = t.surfaceUp)}
                        onMouseLeave={e => !isUs && (e.currentTarget.style.background = "transparent")}
                      >
                        <td style={{ padding: "14px 16px", fontWeight: isUs ? 800 : 500, color: isUs ? t.blue : t.text, fontSize: isUs ? 14 : 13 }}>{row.tool}</td>
                        {[row.bns, row.ipc, row.hash, row.india, row.local].map((v, j) => (
                          <td key={j} style={{ padding: "14px 16px", textAlign: "center" }}>
                            {v
                              ? <span style={{ color: "#34d399", fontSize: 16, fontWeight: 900 }}>✓</span>
                              : <span style={{ color: t.muted, fontSize: 14 }}>—</span>
                            }
                          </td>
                        ))}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </Reveal>
        </div>
      </section>

      {/* ══════════════ WHO IS IT FOR ══════════════ */}
      <section style={{ padding: "96px 24px", background: t.bg }}>
        <div style={{ maxWidth: 1000, margin: "0 auto" }}>
          <SectionHeading
            eyebrow="Users"
            title="Built for citizens, not just lawyers"
            sub="Most legal AI is built for firms with thousands of dollars to spend. NyayaSetu is for everyone else."
            t={t} center
          />
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 16 }} className="user-grid">
            {[
              { icon: "🏠", title: "Tenants",        color: "#4d7cfe", desc: "Signing a rental agreement you don't understand. Upload it — get every unfair clause flagged before you sign.", cta: "analyzer" },
              { icon: "💼", title: "Employees",      color: "#34d399", desc: "Got a termination letter or salary dispute notice. Understand your rights under the new labour codes.", cta: "analyzer" },
              { icon: "📱", title: "Harassment Victims", color: "#fbbf24", desc: "Have screenshots or photos as evidence. Get a SHA-256 certificate that makes them court-admissible.", cta: "evidence" },
              { icon: "👮", title: "Police & Lawyers", color: "#f87171", desc: "Still using IPC sections in FIRs. Check every reference against BNS 2023 before filing.", cta: "compliance" },
              { icon: "🏪", title: "Small Businesses", color: "#a78bfa", desc: "Reviewing vendor contracts, supply agreements, or NDAs without a legal team.", cta: "analyzer" },
              { icon: "🎓", title: "Law Students",   color: "#fb923c", desc: "Research case law, understand BNS sections, and build arguments grounded in real judgments.", cta: "caselaws" },
            ].map((u, i) => (
              <Reveal key={i} delay={i * 0.06}>
                <div style={{
                  padding: "24px 22px", borderRadius: 14,
                  background: t.surface, border: `1.5px solid ${t.border}`,
                  cursor: "pointer", transition: "all 0.2s",
                }}
                  onClick={() => go(u.cta)}
                  onMouseEnter={e => { e.currentTarget.style.borderColor = u.color + "44"; e.currentTarget.style.transform = "translateY(-3px)"; e.currentTarget.style.boxShadow = `0 12px 32px ${u.color}18`; }}
                  onMouseLeave={e => { e.currentTarget.style.borderColor = t.border; e.currentTarget.style.transform = "none"; e.currentTarget.style.boxShadow = "none"; }}
                >
                  <div style={{ fontSize: 28, marginBottom: 12 }}>{u.icon}</div>
                  <div style={{ fontSize: 14, fontWeight: 800, color: t.text, marginBottom: 8 }}>{u.title}</div>
                  <p style={{ fontSize: 12, color: t.sub, lineHeight: 1.75, margin: "0 0 14px" }}>{u.desc}</p>
                  <span style={{ fontSize: 11, color: u.color, fontWeight: 700, display: "flex", alignItems: "center", gap: 4 }}>
                    Try the tool <Ic d={ICONS.arrow} size={11} color={u.color} sw={2.5} />
                  </span>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* ══════════════ TECH STACK ══════════════ */}
      <section style={{ padding: "72px 24px", background: t.surface }}>
        <div style={{ maxWidth: 1000, margin: "0 auto" }}>
          <Reveal>
            <div style={{
              padding: "36px 40px", borderRadius: 20,
              background: isBold ? `linear-gradient(135deg, ${t.surfaceUp} 0%, ${t.surface} 100%)` : `linear-gradient(135deg, ${t.bg} 0%, ${t.surface} 100%)`,
              border: `1.5px solid ${t.border}`,
            }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 24 }}>
                <div style={{ maxWidth: 400 }}>
                  <div style={{ fontSize: 11, fontWeight: 800, color: t.muted, letterSpacing: "0.1em", textTransform: "uppercase", marginBottom: 10 }}>Tech Stack</div>
                  <h3 style={{ fontFamily: "'DM Serif Display', serif", fontSize: "1.6rem", fontWeight: 400, color: t.text, margin: "0 0 10px" }}>Everything runs on your machine</h3>
                  <p style={{ fontSize: 13, color: t.sub, lineHeight: 1.8, margin: 0 }}>Llama-3 8B via Ollama. ChromaDB for vector search. FastAPI backend. No cloud API calls for inference. Your legal data stays on your device.</p>
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                  {[
                    { label: "LLM", value: "Llama-3 8B", color: "#4d7cfe" },
                    { label: "GPU", value: "RTX 4050 6GB", color: "#34d399" },
                    { label: "Vector DB", value: "ChromaDB", color: "#fbbf24" },
                    { label: "Retrieval", value: "BM25 + Semantic", color: "#a78bfa" },
                    { label: "Backend", value: "FastAPI", color: "#fb923c" },
                    { label: "Frontend", value: "React", color: "#4d7cfe" },
                  ].map((item, i) => (
                    <div key={i} style={{ padding: "10px 14px", borderRadius: 9, background: t.surface, border: `1px solid ${t.border}` }}>
                      <div style={{ fontSize: 10, color: t.muted, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 3 }}>{item.label}</div>
                      <div style={{ fontSize: 13, color: item.color, fontWeight: 700 }}>{item.value}</div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </Reveal>
        </div>
      </section>

      {/* ══════════════ CTA STRIP ══════════════ */}
      <section style={{ padding: "80px 24px", background: t.bg }}>
        <div style={{ maxWidth: 700, margin: "0 auto", textAlign: "center" }}>
          <Reveal>
            <div style={{
              padding: "52px 40px", borderRadius: 24,
              background: `linear-gradient(135deg, ${t.blue}18 0%, #a78bfa18 100%)`,
              border: `1.5px solid ${t.blue}33`,
              position: "relative", overflow: "hidden",
            }}>
              <div style={{ position: "absolute", inset: 0, backgroundImage: `linear-gradient(${t.blue}08 1px, transparent 1px), linear-gradient(90deg, ${t.blue}08 1px, transparent 1px)`, backgroundSize: "28px 28px" }} />
              <div style={{ position: "relative" }}>
                <h2 style={{ fontFamily: "'DM Serif Display', serif", fontSize: "clamp(1.6rem,3vw,2.4rem)", fontWeight: 400, color: t.text, margin: "0 0 14px" }}>
                  Start with your document
                </h2>
                <p style={{ fontSize: 14, color: t.sub, margin: "0 0 28px", lineHeight: 1.8 }}>
                  No account. No upload to servers. No subscription.<br />Upload a document and get results in under 60 seconds.
                </p>
                <div style={{ display: "flex", gap: 12, justifyContent: "center", flexWrap: "wrap" }}>
                  {[
                    { label: "Analyze Document", icon: "doc", fn: () => go("analyzer") },
                    { label: "Check Compliance", icon: "shield", fn: () => go("compliance") },
                    { label: "Certify Evidence", icon: "camera", fn: () => go("evidence") },
                  ].map(btn => (
                    <button key={btn.label} onClick={btn.fn} style={{
                      padding: "10px 20px", borderRadius: 9,
                      background: t.blue, color: "#fff",
                      border: "none", fontSize: 13, fontWeight: 700,
                      cursor: "pointer", fontFamily: "inherit",
                      display: "flex", alignItems: "center", gap: 7,
                      transition: "all 0.15s",
                    }}
                      onMouseEnter={e => { e.currentTarget.style.transform = "translateY(-1px)"; e.currentTarget.style.boxShadow = `0 6px 20px ${t.blue}44`; }}
                      onMouseLeave={e => { e.currentTarget.style.transform = "none"; e.currentTarget.style.boxShadow = "none"; }}
                    >
                      <Ic d={ICONS[btn.icon]} size={13} color="#fff" sw={2} />
                      {btn.label}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </Reveal>
        </div>
      </section>

      {/* ══════════════ DISCLAIMER ══════════════ */}
      <div style={{ padding: "0 24px 40px" }}>
        <div style={{ maxWidth: 1000, margin: "0 auto" }}>
          <Reveal>
            <div style={{ padding: "14px 20px", borderRadius: 12, background: t.amberDim, border: `1px solid ${t.amber}33`, display: "flex", gap: 12, alignItems: "flex-start" }}>
              <Ic d={ICONS.alert} size={15} color={t.amber} sw={2} />
              <p style={{ fontSize: 12, color: t.amber, margin: 0, lineHeight: 1.7 }}>
                <strong>Disclaimer:</strong> NyayaSetu provides AI-generated legal guidance for informational purposes only. It does not constitute legal advice. For important legal matters, always consult a qualified Indian advocate.
              </p>
            </div>
          </Reveal>
        </div>
      </div>

      <style>{`
        @media (max-width: 760px) {
          .stat-grid  { grid-template-columns: repeat(2,1fr) !important; }
          .step-grid  { grid-template-columns: repeat(2,1fr) !important; }
          .feat-grid  { grid-template-columns: 1fr !important; }
          .gap-grid   { grid-template-columns: 1fr !important; }
          .user-grid  { grid-template-columns: 1fr !important; }
        }
      `}</style>
    </div>
  );
}