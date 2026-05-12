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
        {sub && <p style={{ fontSize: 15, color: t.sub, maxWidth: 560, margin: center ? "0 auto" : 0, lineHeight: 1.8 }}>{sub}</p>}
      </div>
    </Reveal>
  );
}

// ── Safe icon renderer with emoji fallback ────────────────────────────────────
function SafeIcon({ name, size = 16, color = "#4d7cfe", sw = 2 }) {
  const d = ICONS[name];
  if (!d) {
    const emojiMap = {
      doc: "\ud83d\udcc4", shield: "\ud83d\udee1\ufe0f", scale: "\u2696\ufe0f", camera: "\ud83d\udcf7", search: "\ud83d\udd0d",
      globe: "\ud83c\udf0d", edit: "\u270f\ufe0f", layout: "\ud83d\udcca", calendar: "\ud83d\udcc5", briefcase: "\ud83d\udcbc",
      user: "\ud83d\udc64", upload: "\ud83d\udce4", check: "\u2713", arrow: "\u2192", alert: "\u26a0\ufe0f",
      mic: "\ud83c\udf99\ufe0f", bot: "\ud83e\udd16", file: "\ud83d\udcc1", clock: "\u23f0", dollar: "\ud83d\udcb0",
      lock: "\ud83d\udd12", phone: "\ud83d\udcf1", mail: "\u2709", star: "\u2b50", heart: "\u2764",
      chart: "\ud83d\udcc8", code: "\ud83d\udcbb", database: "\ud83d\uddc4", wifi: "\ud83d\udce1", sun: "\u2600",
      moon: "\ud83c\udf19", menu: "\u2630", close: "\u2715", back: "\u2190", forward: "\u2192",
      refresh: "\u21bb", download: "\u2b07", share: "\u2197", trash: "\ud83d\uddd1", settings: "\u2699",
      help: "\u003f", info: "\u2139", success: "\u2713", error: "\u2715", warning: "\u26a0",
      filter: "\ud83d\udd3d", sort: "\u21c5", expand: "\u2922", collapse: "\u2921", link: "\ud83d\udd17",
      copy: "\ud83d\udccb", paste: "\ud83d\udccc", cut: "\u2702", undo: "\u21b6", redo: "\u21b7",
      print: "\ud83d\udda8", export: "\ud83d\udce4", import: "\ud83d\udce5", save: "\ud83d\udcbe", folder: "\ud83d\udcc2",
      tag: "\ud83c\udff7", flag: "\ud83d\udea9", pin: "\ud83d\udccd", bookmark: "\ud83d\udd16", bell: "\ud83d\udd14",
      mute: "\ud83d\udd15", volume: "\ud83d\udd0a", play: "\u25b6", pause: "\u23f8", stop: "\u23f9",
      next: "\u23ed", prev: "\u23ee", shuffle: "\ud83d\udd00", repeat: "\ud83d\udd01", list: "\u2630",
      grid: "\u229e", map: "\ud83d\uddfa", location: "\ud83d\udccd", directions: "\ud83e\udded", compass: "\ud83e\udded",
      home: "\ud83c\udfe0", building: "\ud83c\udfe2", bank: "\ud83c\udfdb", hospital: "\ud83c\udfe5", school: "\ud83c\udfeb",
      store: "\ud83c\udfea", factory: "\ud83c\udfed", warehouse: "\ud83c\udfed", farm: "\ud83c\udf3e", garden: "\ud83c\udf3c",
      park: "\ud83c\udf33", tree: "\ud83c\udf32", flower: "\ud83c\udf38", leaf: "\ud83c\udf43", mountain: "\u26f0",
      ocean: "\ud83c\udf0a", river: "\ud83c\udfde", lake: "\ud83c\udfde", beach: "\ud83c\udfd6", desert: "\ud83c\udfdc",
      island: "\ud83c\udfdd", forest: "\ud83c\udf32", jungle: "\ud83c\udf34", savanna: "\ud83c\udf3e", tundra: "\u2744",
      arctic: "\ud83e\uddca", volcano: "\ud83c\udf0b", cave: "\ud83d\udd73", canyon: "\ud83c\udfdc", waterfall: "\ud83d\udca6",
      glacier: "\ud83e\uddca", iceberg: "\ud83e\uddca", reef: "\ud83d\udc20", atoll: "\ud83c\udfdd", lagoon: "\ud83c\udfdd",
      estuary: "\ud83c\udf0a", fjord: "\ud83c\udfde", bay: "\ud83c\udf0a", gulf: "\ud83c\udf0a", strait: "\ud83c\udf0a",
      channel: "\ud83c\udf0a", canal: "\ud83d\udea3", port: "\u2693", dock: "\u2693", harbor: "\u2693",
      marina: "\u2693", pier: "\ud83d\udee3", wharf: "\ud83d\udee3", quay: "\ud83d\udee3", jetty: "\ud83d\udee3",
      breakwater: "\ud83c\udf0a", seawall: "\ud83c\udf0a", promenade: "\ud83d\udeb6", boardwalk: "\ud83d\udeb6",
    };
    return <span style={{ fontSize: size, color, lineHeight: 1 }}>{emojiMap[name] || "\u25cf"}</span>;
  }
  return <Ic d={d} size={size} color={color} sw={sw} />;
}

// ── Data ──────────────────────────────────────────────────────────────────────
const STATS = [
  { value: "3,254", label: "Legal chunks indexed", icon: "doc", color: "#4d7cfe" },
  { value: "70+", label: "IPC to BNS mappings", icon: "shield", color: "#34d399" },
  { value: "100%", label: "Local zero data sent", icon: "lock", color: "#a78bfa" },
  { value: "18", label: "BNS offences covered", icon: "scale", color: "#fbbf24" },
  { value: "0", label: "Cloud API calls", icon: "wifi", color: "#f87171" },
];

// ── ALL TOOLS ARE LAWYER-FOCUSED ─────────────────────────────────────────────
const LAWYER_TOOLS = [
  {
    id: "analyzer", icon: "doc", color: "#4d7cfe",
    title: "Document Analyzer",
    badge: "AI Risk Scoring",
    desc: "Upload any legal document — rental agreement, employment letter, FIR, loan contract, or client brief. Every clause is scored Safe, Caution, High Risk, or Illegal with plain-English explanations and actionable suggestions powered by Llama-3. Perfect for quick client intake review and contract vetting.",
    bullets: ["Clause-by-clause risk breakdown with confidence scores", "IRAC reasoning via Llama-3 with source citations", "Inline Q&A about the document for client meetings", "Relevant case law per clause for argument building"],
    who: "Litigators, corporate lawyers, in-house counsel",
  },
  {
    id: "compliance", icon: "shield", color: "#34d399",
    title: "BNS Compliance Checker",
    badge: "IPC to BNS 2023",
    desc: "Courts are rejecting FIRs and petitions that still cite IPC sections — IPC was repealed in December 2023. Paste any legal text to instantly detect outdated references and get the correct BNS/BNSS/BSA equivalent with a compliance score. Essential for drafting court filings that will not be returned.",
    bullets: ["70+ IPC/CrPC/IEA to BNS/BNSS/BSA mappings", "Compliance score 0-100 for every document", "Abolished sections flagged with migration guidance", "Batch-check entire petitions before filing"],
    who: "Criminal lawyers, police prosecutors, paralegals",
  },
  {
    id: "evidence", icon: "camera", color: "#fbbf24",
    title: "Evidence Certificate",
    badge: "BSA Section 63",
    desc: "Digital photos and screenshots submitted to police are routinely dismissed for lack of certification. Under BSA Section 63, electronic evidence requires a cryptographic hash. Generate SHA-256 before any processing — chain of custody intact. Advise clients on proper evidence preservation from day one.",
    bullets: ["SHA-256 computed before any modification", "EXIF metadata extracted (GPS, device, timestamp)", "PDF certificate for direct court submission", "WhatsApp OTP verification for client authentication"],
    who: "Criminal lawyers, cyber law practitioners, DRT advocates",
  },
  {
    id: "caselaws", icon: "search", color: "#a78bfa",
    title: "Case Law Search",
    badge: "IndianKanoon Live",
    desc: "Search thousands of Indian High Court and Supreme Court judgments by topic, section, or keyword. Results are fetched live from IndianKanoon and summarised in plain English by Llama-3 running locally — no data sent to the cloud. Build stronger arguments with cited precedents in minutes.",
    bullets: ["Live IndianKanoon API integration", "Llama-3 plain-English summaries of judgments", "Direct links to full judgments for verification", "Suggested search topics by practice area"],
    who: "Advocates, law firm associates, legal researchers",
  },
  {
    id: "translator", icon: "globe", color: "#f472b6",
    title: "Legal Translator",
    badge: "36 Languages",
    desc: "FIRs, complaints, and client documents often arrive in regional languages. Upload a document in Hindi, Marathi, Tamil, Bengali, or any of 36 Indian languages and get an accurate legal translation preserving technical terminology. Understand your vernacular client documents without external translators.",
    bullets: ["36 Indian languages supported via BHASHINI", "Legal terminology preserved in translation", "FIR-specific translation mode for criminal practice", "Upload PDF or image directly — no retyping"],
    who: "Lawyers with vernacular clients, district court practitioners",
  },
  {
    id: "generator", icon: "edit", color: "#fb923c",
    title: "Document Generator",
    badge: "Auto-Draft",
    desc: "Draft rent agreements, legal notices, employment contracts, and more in seconds. Fill in party details and get a professionally drafted document ready for execution — formatted for Indian jurisdiction with proper legal clauses under Indian Contract Act. Reduce drafting time by 80%.",
    bullets: ["Rent agreements and legal notices", "Employment contracts and NDAs", "Formatted for Indian courts and registrars", "Download as ready-to-use text for final editing"],
    who: "Corporate lawyers, real estate attorneys, family lawyers",
  },
  {
    id: "editor", icon: "edit", color: "#f472b6",
    title: "AI Legal Copilot",
    badge: "Gemini 2.5 Flash",
    desc: "Your AI drafting assistant powered by Gemini 2.5 Flash. Generate watertight legal clauses, pleadings, and correspondence grounded in Indian law — BNS, BNSS, BSA, CPC, and the Indian Contract Act. Draft faster without compromising on legal precision.",
    bullets: ["Clause drafting in plain text (no markdown)", "Indian law jurisdiction default in all outputs", "Context-aware from your uploaded documents", "Ready to paste into any word processor or CMS"],
    who: "Senior advocates, drafting associates, law firm partners",
  },
  {
    id: "research", icon: "search", color: "#a78bfa",
    title: "Legal Research Suite",
    badge: "Statutes + Cases",
    desc: "Comprehensive research tools for Indian statutes and case law. Ask legal questions, search by sections, get full act summaries, or browse statutory acts by jurisdiction. Every answer is citation-backed with confidence scores — no hallucinations.",
    bullets: ["Ask legal research questions with live citations", "Search by act and section number (BNS/BNSS/BSA)", "Statutory act summaries with key provisions", "Citation-backed answers with confidence scores"],
    who: "Law firm researchers, appellate advocates, law students",
  },
];

const PRACTICE_TOOLS = [
  {
    id: "dashboard", icon: "layout", color: "#4d7cfe",
    title: "Practice Dashboard",
    desc: "Complete matter management for lawyers and law firms. Track cases, hearings, tasks, and billing in one unified workspace with role-based access for partners, associates, and clerks.",
    bullets: ["Matter and case management with CNR lookup", "Client intake and conflict checking", "Task assignment with deadline tracking", "Invoice generation and payment status"],
  },
  {
    id: "calendar", icon: "calendar", color: "#34d399",
    title: "Hearing Calendar",
    desc: "Never miss a hearing. Calendar integrates with your matters, sends reminders, and tracks court appearances across all your cases with event-type categorization and matter linking.",
    bullets: ["Court-specific event scheduling", "7-day upcoming summary dashboard", "Matter-linked appointments with case context", "Hearing, deadline, meeting, reminder types"],
  },
  {
    id: "tasks", icon: "check", color: "#fbbf24",
    title: "Task Management",
    desc: "Assign, track, and complete tasks across your firm. Link tasks to specific matters, set priorities, and monitor associate workload — all in one place.",
    bullets: ["Task assignment to associates and clerks", "Priority levels and due date tracking", "Matter-linked task organization", "Progress reporting for partners"],
  },
  {
    id: "billing", icon: "dollar", color: "#a78bfa",
    title: "Firm Billing",
    desc: "Generate invoices, track payments, and manage client accounts. From time tracking to final invoice — streamline your firm's revenue cycle.",
    bullets: ["Invoice generation with matter references", "Payment status tracking (Pending/Paid/Overdue)", "Client account summaries", "Export-ready billing reports"],
  },
];

const RESEARCH_GAPS = [
  { num: "01", title: "No BNS 2023 knowledge in LLMs", desc: "Every major LLM (GPT-4, Gemini, Claude) was trained before December 2023. None know BNS, BNSS, or BSA. ChatGPT-4 scores only 34% on BNS-specific queries. NyayaSetu is built on the actual statutes.", color: "#f87171", stat: "34% accuracy" },
  { num: "02", title: "91% hallucination rate", desc: "GPT-4 gets Indian law wrong 91% of the time (Jones et al., 2024). Generic LLMs hallucinate non-existent BNS sections and cite repealed IPC provisions. Our RAG engine is grounded in verified statutory PDFs — not training data.", color: "#fbbf24", stat: "91% error rate" },
  { num: "03", title: "No IPC-to-BNS migration tool existed", desc: "Lawyers in India still cite IPC sections in 2025. Courts are returning petitions. No automated tool existed to detect outdated references and map them to BNS equivalents before NyayaSetu.", color: "#34d399", stat: "163-year gap" },
  { num: "04", title: "Digital evidence dismissed without hash", desc: "BSA Section 63 requires SHA-256 certification for digital evidence to be court-admissible. No lawyer-facing tool existed to generate these certificates with proper chain of custody for client advisement.", color: "#a78bfa", stat: "Section 63" },
  { num: "05", title: "No integrated practice management for Indian lawyers", desc: "Lawyers use fragmented tools — Excel for cases, WhatsApp for reminders, manual billing, separate research subscriptions. No integrated platform existed for matter management, hearing calendars, task tracking, and invoicing in one place.", color: "#4d7cfe", stat: "5+ tools avg" },
  { num: "06", title: "US/EU tools do not understand Indian law", desc: "CUAD, DoNotPay, ContractNLI — all trained on Western contracts under New York/English law. They fail on Indian indemnification structures, stamp duty clauses, and SEBI/RBI regulatory references that Indian lawyers deal with daily.", color: "#fb923c", stat: "0% Indian context" },
  { num: "07", title: "No explainable AI for judicial trust", desc: "Kerala High Court prohibited AI tools in district judiciary due to black-box opacity. NyayaSetu uses attention-mechanism RAG with source citations — every answer traces back to the actual statute text, building lawyer and judicial confidence.", color: "#f87171", stat: "0% explainability" },
  { num: "08", title: "No offline-first legal AI for courtrooms", desc: "Generic AI tools require constant cloud connectivity. Courtrooms and district courts often lack reliable internet. NyayaSetu runs entirely locally — Llama-3 on-device, no API calls, full functionality offline even in basement courtrooms.", color: "#34d399", stat: "40% offline need" },
];

const HOW_STEPS = [
  { icon: "upload", title: "Upload or paste", desc: "Drop a PDF, image, or paste any legal text — FIR, notice, agreement, petition, or client brief.", color: "#4d7cfe" },
  { icon: "shield", title: "AI analysis", desc: "Llama-3 reads every clause, cross-references BNS/BNSS/BSA via RAG, and identifies risks with source citations.", color: "#34d399" },
  { icon: "doc", title: "Plain English", desc: "Get a clear, jargon-free breakdown with exact section references, confidence scores, and actionable next steps.", color: "#fbbf24" },
  { icon: "check", title: "Take action", desc: "Download certificates, share compliance reports, search case law, generate documents, or update your practice dashboard.", color: "#a78bfa" },
];

const COMPARE = [
  { tool: "GPT-4 / ChatGPT", bns: false, ipc: false, hash: false, india: false, local: false, explain: false, practice: false },
  { tool: "Vakil.ai", bns: false, ipc: false, hash: false, india: true, local: false, explain: false, practice: false },
  { tool: "ContractNLI", bns: false, ipc: false, hash: false, india: false, local: false, explain: false, practice: false },
  { tool: "InLegalBERT", bns: false, ipc: false, hash: false, india: true, local: false, explain: false, practice: false },
  { tool: "ChatLaw", bns: true, ipc: false, hash: false, india: true, local: false, explain: true, practice: false },
  { tool: "NyayaSetu", bns: true, ipc: true, hash: true, india: true, local: true, explain: true, practice: true },
];

const FUTURE_ROADMAP = [
  { icon: "mic", color: "#f472b6", title: "Voice-First Interface", desc: "BHASHINI-powered voice input in 23 Indian languages. Dictate case notes, query statutes, and draft pleadings hands-free — built for lawyers who think faster than they type.", eta: "Q3 2026" },
  { icon: "bot", color: "#4d7cfe", title: "DISHIKA AI Mascot", desc: "Interactive AI mascot for guided legal workflows. DISHIKA walks junior associates through complex procedures — from filing to argument drafting — with contextual help at every step.", eta: "Q4 2026" },
  { icon: "phone", color: "#34d399", title: "WhatsApp Case Updates", desc: "Automated WhatsApp notifications for clients on hearing dates, case status, and document requirements. Reduce client follow-up calls by 70%.", eta: "Q2 2026" },
  { icon: "chart", color: "#fbbf24", title: "Predictive Case Analytics", desc: "ML-powered outcome prediction based on judge history, case type, and precedent patterns. Know your odds before you file.", eta: "Q1 2027" },
];

// ── Main component ────────────────────────────────────────────────────────────
export default function Home({ t, go }) {
  const [heroVisible, setHeroVisible] = useState(false);
  const [activeTab, setActiveTab] = useState("legal");
  const [hoveredGap, setHoveredGap] = useState(null);

  useEffect(() => {
    const id = setTimeout(() => setHeroVisible(true), 80);
    return () => clearTimeout(id);
  }, []);

  const isBold = t.text === "#e2e8f4";

  return (
    <div style={{ fontFamily: "'DM Sans', system-ui, sans-serif" }}>

      {/* ══════════════ HERO ══════════════ */}
      <section style={{
        position: "relative", overflow: "hidden",
        padding: "110px 24px 120px",
        background: `linear-gradient(160deg, ${t.bg} 0%, ${t.surface} 50%, ${t.bg} 100%)`,
      }}>
        <div style={{
          position: "absolute", inset: 0, pointerEvents: "none",
          backgroundImage: `linear-gradient(${t.border} 1px, transparent 1px), linear-gradient(90deg, ${t.border} 1px, transparent 1px)`,
          backgroundSize: "52px 52px", opacity: 0.3,
          maskImage: "radial-gradient(ellipse 80% 60% at 50% 0%, black 30%, transparent 100%)",
          WebkitMaskImage: "radial-gradient(ellipse 80% 60% at 50% 0%, black 30%, transparent 100%)",
        }} />
        <div style={{ position: "absolute", top: -140, left: "50%", transform: "translateX(-50%)", width: 700, height: 450, borderRadius: "50%", background: `radial-gradient(ellipse, ${t.blue}18 0%, transparent 70%)`, pointerEvents: "none" }} />
        <div style={{ position: "absolute", bottom: -100, right: "8%", width: 350, height: 350, borderRadius: "50%", background: `radial-gradient(ellipse, #a78bfa15 0%, transparent 70%)`, pointerEvents: "none" }} />
        <div style={{ position: "absolute", top: "40%", left: "5%", width: 200, height: 200, borderRadius: "50%", background: `radial-gradient(ellipse, #34d39910 0%, transparent 70%)`, pointerEvents: "none" }} />

        <div style={{ maxWidth: 960, margin: "0 auto", position: "relative", textAlign: "center" }}>
          <div style={{
            opacity: heroVisible ? 1 : 0,
            transform: heroVisible ? "none" : "translateY(16px)",
            transition: "opacity 0.6s ease, transform 0.6s ease",
            display: "inline-flex", alignItems: "center", gap: 10,
            padding: "8px 20px", borderRadius: 99,
            background: `${t.blue}12`, border: `1.5px solid ${t.blue}30`,
            marginBottom: 32,
          }}>
            <span style={{ width: 8, height: 8, borderRadius: "50%", background: t.blue, display: "inline-block", animation: "pulse 2.5s ease infinite" }} />
            <span style={{ fontSize: 11, color: t.blue, fontWeight: 800, letterSpacing: "0.12em", textTransform: "uppercase" }}>
              Indian Legal AI · BNS 2023 · Runs Locally · Built for Lawyers
            </span>
          </div>

          <h1 style={{
            fontFamily: "'DM Serif Display', Georgia, serif",
            fontSize: "clamp(2.8rem,6.5vw,4.8rem)",
            fontWeight: 400, lineHeight: 1.05, color: t.text,
            margin: "0 0 28px", letterSpacing: "-0.03em",
            opacity: heroVisible ? 1 : 0,
            transform: heroVisible ? "none" : "translateY(28px)",
            transition: "opacity 0.7s ease 0.1s, transform 0.7s cubic-bezier(0.22,1,0.36,1) 0.1s",
          }}>
            The complete legal platform
            <br />
            <span style={{
              color: t.blue,
              backgroundImage: `linear-gradient(135deg, ${t.blue}, #a78bfa)`,
              WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent",
            }}>
              for Indian lawyers.
            </span>
          </h1>

          <p style={{
            fontSize: 18, color: t.sub, maxWidth: 640, margin: "0 auto 44px",
            lineHeight: 1.85,
            opacity: heroVisible ? 1 : 0,
            transform: heroVisible ? "none" : "translateY(22px)",
            transition: "opacity 0.7s ease 0.2s, transform 0.7s ease 0.2s",
          }}>
            From analyzing client documents to certifying digital evidence, checking BNS compliance,
            searching case law, and managing your entire practice — NyayaSetu is the only platform
            built specifically for Indian legal professionals. Zero data leaves your device.
          </p>

          <div style={{
            display: "flex", gap: 14, justifyContent: "center", flexWrap: "wrap", marginBottom: 72,
            opacity: heroVisible ? 1 : 0,
            transform: heroVisible ? "none" : "translateY(18px)",
            transition: "opacity 0.7s ease 0.3s, transform 0.7s ease 0.3s",
          }}>
            {[
              { label: "Analyze Document", icon: "doc", fn: () => go("analyzer"), primary: true },
              { label: "Check BNS Compliance", icon: "shield", fn: () => go("compliance"), primary: false },
              { label: "Search Case Law", icon: "search", fn: () => go("caselaws"), primary: false },
            ].map(btn => (
              <button key={btn.label} onClick={btn.fn} style={{
                padding: "14px 28px", borderRadius: 12,
                background: btn.primary ? t.blue : "transparent",
                color: btn.primary ? "#fff" : t.text,
                border: btn.primary ? "none" : `1.5px solid ${t.border}`,
                fontSize: 14, fontWeight: 700, cursor: "pointer",
                display: "flex", alignItems: "center", gap: 10,
                fontFamily: "inherit", transition: "all 0.25s cubic-bezier(0.22,1,0.36,1)",
                boxShadow: btn.primary ? `0 6px 24px ${t.blue}40` : "none",
              }}
                onMouseEnter={e => { e.currentTarget.style.transform = "translateY(-3px)"; if (btn.primary) e.currentTarget.style.boxShadow = `0 12px 32px ${t.blue}55`; else e.currentTarget.style.borderColor = t.borderHover; }}
                onMouseLeave={e => { e.currentTarget.style.transform = "translateY(0)"; if (btn.primary) e.currentTarget.style.boxShadow = `0 6px 24px ${t.blue}40`; else e.currentTarget.style.borderColor = t.border; }}
              >
                <SafeIcon name={btn.icon} size={16} color={btn.primary ? "#fff" : t.sub} sw={2} />
                {btn.label}
              </button>
            ))}
          </div>

          <div style={{
            display: "grid", gridTemplateColumns: "repeat(5,1fr)", gap: 14,
            opacity: heroVisible ? 1 : 0,
            transform: heroVisible ? "none" : "translateY(22px)",
            transition: "opacity 0.7s ease 0.4s, transform 0.7s ease 0.4s",
          }} className="stat-grid">
            {STATS.map((s, i) => (
              <div key={i} style={{
                background: t.surface, border: `1.5px solid ${t.border}`,
                borderRadius: 16, padding: "22px 14px", textAlign: "center",
                transition: "border-color 0.25s, transform 0.25s, box-shadow 0.25s",
                cursor: "default",
              }}
                onMouseEnter={e => { e.currentTarget.style.borderColor = s.color + "50"; e.currentTarget.style.transform = "translateY(-4px)"; e.currentTarget.style.boxShadow = `0 12px 32px ${s.color}15`; }}
                onMouseLeave={e => { e.currentTarget.style.borderColor = t.border; e.currentTarget.style.transform = "translateY(0)"; e.currentTarget.style.boxShadow = "none"; }}
              >
                <div style={{ width: 36, height: 36, borderRadius: 10, background: `${s.color}15`, border: `1px solid ${s.color}30`, display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 12px" }}>
                  <SafeIcon name={s.icon} size={15} color={s.color} />
                </div>
                <div style={{ fontSize: "1.5rem", fontWeight: 900, color: t.text, letterSpacing: "-0.03em", lineHeight: 1 }}>
                  <Counter target={s.value} />
                </div>
                <div style={{ fontSize: 11, color: t.sub, marginTop: 6, fontWeight: 500, lineHeight: 1.4 }}>{s.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ══════════════ HOW IT WORKS ══════════════ */}
      <section style={{ padding: "100px 24px", background: t.bg }}>
        <div style={{ maxWidth: 1000, margin: "0 auto" }}>
          <SectionHeading
            eyebrow="How it works"
            title="Four steps to better legal practice"
            sub="No cloud uploads. No subscription tiers. Everything runs on your local machine — even in courtrooms with no internet."
            t={t} center
          />
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 16 }} className="step-grid">
            {HOW_STEPS.map((s, i) => (
              <Reveal key={i} delay={i * 0.12}>
                <div style={{ textAlign: "center", padding: "32px 22px 28px", borderRadius: 18, background: t.surface, border: `1.5px solid ${t.border}`, position: "relative", transition: "border-color 0.25s, transform 0.25s, box-shadow 0.25s" }}
                  onMouseEnter={e => { e.currentTarget.style.borderColor = s.color + "50"; e.currentTarget.style.transform = "translateY(-4px)"; e.currentTarget.style.boxShadow = `0 12px 32px ${s.color}12`; }}
                  onMouseLeave={e => { e.currentTarget.style.borderColor = t.border; e.currentTarget.style.transform = "none"; e.currentTarget.style.boxShadow = "none"; }}
                >
                  <div style={{ position: "absolute", top: -14, left: "50%", transform: "translateX(-50%)", width: 28, height: 28, borderRadius: "50%", background: s.color, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 11, fontWeight: 900, color: "#fff", boxShadow: `0 4px 12px ${s.color}40` }}>
                    {String(i + 1).padStart(2, "0")}
                  </div>
                  <div style={{ width: 52, height: 52, borderRadius: 16, background: `${s.color}12`, border: `1px solid ${s.color}25`, display: "flex", alignItems: "center", justifyContent: "center", margin: "10px auto 18px" }}>
                    <SafeIcon name={s.icon} size={22} color={s.color} />
                  </div>
                  <div style={{ fontSize: 15, fontWeight: 800, color: t.text, marginBottom: 10 }}>{s.title}</div>
                  <p style={{ fontSize: 13, color: t.sub, lineHeight: 1.7, margin: 0 }}>{s.desc}</p>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* ══════════════ TOOL SUITE: TABS ══════════════ */}
      <section style={{ padding: "100px 24px", background: t.surface }}>
        <div style={{ maxWidth: 1080, margin: "0 auto" }}>
          <SectionHeading
            eyebrow="The platform"
            title="Everything a lawyer needs"
            sub="Eight integrated tools. One unified workspace. From document analysis to practice management — built specifically for Indian legal professionals."
            t={t} center
          />

          {/* Tab switcher */}
          <div style={{ display: "flex", justifyContent: "center", gap: 10, marginBottom: 56 }}>
            {[
              { id: "legal", label: "Legal Tools", icon: "scale" },
              { id: "practice", label: "Practice Management", icon: "briefcase" },
            ].map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                style={{
                  padding: "12px 28px", borderRadius: 99,
                  background: activeTab === tab.id ? t.blue : "transparent",
                  color: activeTab === tab.id ? "#fff" : t.sub,
                  border: `1.5px solid ${activeTab === tab.id ? t.blue : t.border}`,
                  fontSize: 14, fontWeight: 700, cursor: "pointer",
                  fontFamily: "inherit", display: "flex", alignItems: "center", gap: 10,
                  transition: "all 0.25s cubic-bezier(0.22,1,0.36,1)",
                  boxShadow: activeTab === tab.id ? `0 4px 16px ${t.blue}35` : "none",
                }}
              >
                <SafeIcon name={tab.icon} size={15} color={activeTab === tab.id ? "#fff" : t.sub} sw={2} />
                {tab.label}
              </button>
            ))}
          </div>

          {/* Legal Tools */}
          {activeTab === "legal" && (
            <div style={{ display: "flex", flexDirection: "column", gap: 90 }}>
              {LAWYER_TOOLS.map((f, i) => (
                <Reveal key={f.id} delay={0} direction={i % 2 === 0 ? "left" : "right"}>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 56, alignItems: "center" }} className="feat-grid">
                    {/* Text side */}
                    <div style={{ order: i % 2 === 0 ? 0 : 1 }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 18 }}>
                        <div style={{ width: 44, height: 44, borderRadius: 12, background: `${f.color}12`, border: `1.5px solid ${f.color}30`, display: "flex", alignItems: "center", justifyContent: "center" }}>
                          <SafeIcon name={f.icon} size={20} color={f.color} />
                        </div>
                        <span style={{ fontSize: 11, fontWeight: 800, color: f.color, letterSpacing: "0.1em", textTransform: "uppercase", padding: "4px 12px", borderRadius: 8, background: `${f.color}10`, border: `1px solid ${f.color}20` }}>{f.badge}</span>
                      </div>
                      <h3 style={{ fontFamily: "'DM Serif Display', serif", fontSize: "clamp(1.6rem,2.8vw,2.2rem)", fontWeight: 400, color: t.text, margin: "0 0 16px", letterSpacing: "-0.01em" }}>{f.title}</h3>
                      <p style={{ fontSize: 15, color: t.sub, lineHeight: 1.85, margin: "0 0 22px" }}>{f.desc}</p>
                      <ul style={{ listStyle: "none", padding: 0, margin: "0 0 26px", display: "flex", flexDirection: "column", gap: 10 }}>
                        {f.bullets.map((b, bi) => (
                          <li key={bi} style={{ display: "flex", alignItems: "flex-start", gap: 10, fontSize: 14, color: t.sub }}>
                            <span style={{ width: 20, height: 20, borderRadius: "50%", background: `${f.color}12`, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0, marginTop: 2, border: `1px solid ${f.color}25` }}>
                              <SafeIcon name="check" size={10} color={f.color} sw={3} />
                            </span>
                            {b}
                          </li>
                        ))}
                      </ul>
                      <div style={{ display: "flex", gap: 14, alignItems: "center", flexWrap: "wrap" }}>
                        <button onClick={() => go(f.id)} style={{
                          padding: "12px 24px", borderRadius: 10, background: f.color,
                          color: "#fff", border: "none", fontSize: 14, fontWeight: 700,
                          cursor: "pointer", fontFamily: "inherit", transition: "all 0.2s cubic-bezier(0.22,1,0.36,1)",
                          display: "flex", alignItems: "center", gap: 8,
                        }}
                          onMouseEnter={e => { e.currentTarget.style.transform = "translateY(-2px)"; e.currentTarget.style.boxShadow = `0 8px 24px ${f.color}45`; }}
                          onMouseLeave={e => { e.currentTarget.style.transform = "none"; e.currentTarget.style.boxShadow = "none"; }}
                        >
                          Open tool <SafeIcon name="arrow" size={14} color="#fff" sw={2.5} />
                        </button>
                        <span style={{ fontSize: 12, color: t.muted, fontWeight: 500 }}>For: {f.who}</span>
                      </div>
                    </div>

                    {/* Visual side */}
                    <div style={{ order: i % 2 === 0 ? 1 : 0 }}>
                      <div style={{
                        borderRadius: 20, padding: "32px 28px",
                        background: isBold ? `linear-gradient(145deg, ${t.surface} 0%, ${t.surfaceUp} 100%)` : `linear-gradient(145deg, ${t.surfaceUp} 0%, ${t.bg} 100%)`,
                        border: `1.5px solid ${f.color}30`,
                        boxShadow: `0 24px 64px ${f.color}15`,
                        position: "relative", overflow: "hidden",
                      }}>
                        <div style={{ position: "absolute", top: -50, right: -50, width: 180, height: 180, borderRadius: "50%", background: `radial-gradient(circle, ${f.color}12 0%, transparent 70%)`, pointerEvents: "none" }} />
                        <div style={{ marginBottom: 16 }}>
                          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 16 }}>
                            {[f.color, t.border, t.border].map((c, ci) => (
                              <div key={ci} style={{ width: 10, height: 10, borderRadius: "50%", background: c }} />
                            ))}
                            <div style={{ flex: 1, height: 7, borderRadius: 4, background: t.border, marginLeft: 8 }} />
                          </div>
                          {[100, 85, 92, 70, 88, 75].map((w, wi) => (
                            <div key={wi} style={{ display: "flex", gap: 10, marginBottom: 10, alignItems: "center" }}>
                              {wi === 0 && <div style={{ width: 32, height: 32, borderRadius: 8, background: `${f.color}20`, flexShrink: 0, display: "flex", alignItems: "center", justifyContent: "center" }}><SafeIcon name={f.icon} size={14} color={f.color} /></div>}
                              <div style={{ height: wi === 0 ? 12 : 8, borderRadius: 4, background: wi === 0 ? `${f.color}40` : t.border, width: `${w}%`, maxWidth: wi === 0 ? "55%" : "100%" }} />
                              {wi > 0 && wi < 5 && (
                                <div style={{ padding: "3px 10px", borderRadius: 5, background: [null, `${f.color}18`, "#f8717118", "#34d39918", "#fbbf2418", `${f.color}18`][wi], border: `1px solid ${[null, `${f.color}30`, "#f8717130", "#34d39930", "#fbbf2430", `${f.color}30`][wi]}`, fontSize: 10, fontWeight: 800, color: [null, f.color, "#f87171", "#34d399", "#fbbf24", f.color][wi], flexShrink: 0, letterSpacing: "0.02em" }}>
                                  {["", "Caution", "High Risk", "Safe", "Caution", "Review"][wi]}
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                        <div style={{ padding: "12px 16px", borderRadius: 10, background: `${f.color}10`, border: `1px solid ${f.color}20`, fontSize: 12, color: f.color, fontWeight: 600, lineHeight: 1.6, display: "flex", alignItems: "flex-start", gap: 8 }}>
                          <span style={{ fontSize: 14, lineHeight: 1 }}>💡</span>
                          <span>{f.bullets[0]}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </Reveal>
              ))}
            </div>
          )}

          {/* Practice Management */}
          {activeTab === "practice" && (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(2,1fr)", gap: 24 }} className="lawyer-grid">
              {PRACTICE_TOOLS.map((f, i) => (
                <Reveal key={f.id} delay={i * 0.1}>
                  <div style={{
                    padding: "32px 28px", borderRadius: 18,
                    background: t.surface, border: `1.5px solid ${t.border}`,
                    transition: "border-color 0.25s, transform 0.25s, box-shadow 0.25s",
                    cursor: "pointer", height: "100%",
                    display: "flex", flexDirection: "column",
                  }}
                    onClick={() => go(f.id)}
                    onMouseEnter={e => { e.currentTarget.style.borderColor = f.color + "45"; e.currentTarget.style.transform = "translateY(-4px)"; e.currentTarget.style.boxShadow = `0 16px 40px ${f.color}15`; }}
                    onMouseLeave={e => { e.currentTarget.style.borderColor = t.border; e.currentTarget.style.transform = "none"; e.currentTarget.style.boxShadow = "none"; }}
                  >
                    <div style={{ display: "flex", alignItems: "center", gap: 14, marginBottom: 16 }}>
                      <div style={{ width: 44, height: 44, borderRadius: 12, background: `${f.color}12`, border: `1.5px solid ${f.color}30`, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                        <SafeIcon name={f.icon} size={20} color={f.color} />
                      </div>
                      <div>
                        <div style={{ fontSize: 15, fontWeight: 800, color: t.text }}>{f.title}</div>
                      </div>
                    </div>
                    <p style={{ fontSize: 14, color: t.sub, lineHeight: 1.8, margin: "0 0 20px", flex: 1 }}>{f.desc}</p>
                    <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "flex", flexDirection: "column", gap: 8 }}>
                      {f.bullets.map((b, bi) => (
                        <li key={bi} style={{ display: "flex", alignItems: "center", gap: 10, fontSize: 13, color: t.sub }}>
                          <span style={{ width: 16, height: 16, borderRadius: "50%", background: `${f.color}12`, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0, border: `1px solid ${f.color}25` }}>
                            <SafeIcon name="check" size={8} color={f.color} sw={3} />
                          </span>
                          {b}
                        </li>
                      ))}
                    </ul>
                    <div style={{ marginTop: 22, fontSize: 12, color: f.color, fontWeight: 700, display: "flex", alignItems: "center", gap: 6 }}>
                      Open workspace <SafeIcon name="arrow" size={12} color={f.color} sw={2.5} />
                    </div>
                  </div>
                </Reveal>
              ))}
            </div>
          )}
        </div>
      </section>

      {/* ══════════════ RESEARCH GAPS ══════════════ */}
      <section style={{ padding: "100px 24px", background: t.bg }}>
        <div style={{ maxWidth: 1080, margin: "0 auto" }}>
          <SectionHeading
            eyebrow="Why this exists"
            title="Eight gaps no one had filled"
            sub="Every major legal AI tool failed Indian lawyers in at least one critical way. NyayaSetu was built to address all eight — backed by peer-reviewed research and judicial observations."
            t={t} center
          />
          <div style={{ display: "grid", gridTemplateColumns: "repeat(2,1fr)", gap: 18 }} className="gap-grid">
            {RESEARCH_GAPS.map((g, i) => (
              <Reveal key={i} delay={i * 0.06}>
                <div style={{
                  padding: "28px 26px", borderRadius: 16,
                  background: t.surface, border: `1.5px solid ${t.border}`,
                  transition: "border-color 0.25s, transform 0.25s, box-shadow 0.25s",
                  cursor: "default",
                  position: "relative", overflow: "hidden",
                }}
                  onMouseEnter={e => { setHoveredGap(i); e.currentTarget.style.borderColor = g.color + "45"; e.currentTarget.style.transform = "translateY(-3px)"; e.currentTarget.style.boxShadow = `0 12px 32px ${g.color}12`; }}
                  onMouseLeave={e => { setHoveredGap(null); e.currentTarget.style.borderColor = t.border; e.currentTarget.style.transform = "none"; e.currentTarget.style.boxShadow = "none"; }}
                >
                  <div style={{ position: "absolute", left: 0, top: 0, bottom: 0, width: 4, background: g.color, borderRadius: "16px 0 0 16px", opacity: hoveredGap === i ? 1 : 0.5, transition: "opacity 0.25s" }} />
                  <div style={{ display: "flex", alignItems: "flex-start", gap: 16 }}>
                    <div style={{ flexShrink: 0 }}>
                      <div style={{ fontSize: 12, fontWeight: 900, color: g.color, letterSpacing: "0.1em", marginBottom: 4, opacity: 0.8 }}>{g.num}</div>
                      <div style={{ padding: "4px 10px", borderRadius: 6, background: `${g.color}12`, border: `1px solid ${g.color}25`, fontSize: 11, fontWeight: 800, color: g.color, letterSpacing: "0.02em" }}>
                        {g.stat}
                      </div>
                    </div>
                    <div>
                      <div style={{ fontSize: 15, fontWeight: 800, color: t.text, marginBottom: 8, lineHeight: 1.4 }}>{g.title}</div>
                      <p style={{ fontSize: 13, color: t.sub, lineHeight: 1.8, margin: 0 }}>{g.desc}</p>
                    </div>
                  </div>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* ══════════════ COMPARISON TABLE ══════════════ */}
      <section style={{ padding: "100px 24px", background: t.surface }}>
        <div style={{ maxWidth: 1080, margin: "0 auto" }}>
          <SectionHeading
            eyebrow="Comparison"
            title="How NyayaSetu compares"
            sub="Every other tool is missing at least two things that matter for Indian legal practice. NyayaSetu is the only complete platform."
            t={t} center
          />
          <Reveal>
            <div style={{ overflowX: "auto", borderRadius: 16, border: `1.5px solid ${t.border}`, background: t.surface }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13, minWidth: 720 }}>
                <thead>
                  <tr style={{ borderBottom: `2px solid ${t.border}` }}>
                    {["Tool", "BNS 2023", "IPC-to-BNS", "Evidence Hash", "Indian Law", "Local", "Explainable", "Practice Mgmt"].map((h, i) => (
                      <th key={i} style={{ padding: "14px 12px", textAlign: i === 0 ? "left" : "center", color: t.muted, fontWeight: 700, fontSize: 10, textTransform: "uppercase", letterSpacing: "0.06em", whiteSpace: "nowrap", background: t.bg }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {COMPARE.map((row, i) => {
                    const isUs = row.tool === "NyayaSetu";
                    return (
                      <tr key={i} style={{ borderBottom: `1px solid ${t.border}`, background: isUs ? `${t.blue}08` : "transparent", transition: "background 0.2s" }}
                        onMouseEnter={e => !isUs && (e.currentTarget.style.background = t.surfaceUp)}
                        onMouseLeave={e => !isUs && (e.currentTarget.style.background = "transparent")}
                      >
                        <td style={{ padding: "16px 14px", fontWeight: isUs ? 800 : 600, color: isUs ? t.blue : t.text, fontSize: isUs ? 14 : 13, whiteSpace: "nowrap" }}>{row.tool}</td>
                        {[row.bns, row.ipc, row.hash, row.india, row.local, row.explain, row.practice].map((v, j) => (
                          <td key={j} style={{ padding: "16px 12px", textAlign: "center" }}>
                            {v
                              ? <span style={{ color: "#34d399", fontSize: 18, fontWeight: 900, display: "inline-flex", alignItems: "center", justifyContent: "center", width: 28, height: 28, borderRadius: "50%", background: "#34d39912", border: "1px solid #34d39930" }}>✓</span>
                              : <span style={{ color: t.muted, fontSize: 15, display: "inline-flex", alignItems: "center", justifyContent: "center", width: 28, height: 28, borderRadius: "50%", background: `${t.muted}08`, border: `1px solid ${t.muted}20` }}>—</span>
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
      <section style={{ padding: "100px 24px", background: t.bg }}>
        <div style={{ maxWidth: 1080, margin: "0 auto" }}>
          <SectionHeading
            eyebrow="Users"
            title="Built for every kind of lawyer"
            sub="From solo practitioners to full-service firms — NyayaSetu adapts to your practice area and firm size."
            t={t} center
          />
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 18 }} className="user-grid">
            {[
              { icon: "⚖️", title: "Litigators", color: "#4d7cfe", desc: "Analyze pleadings, check BNS compliance in FIRs, search case law for precedents, and manage hearing calendars across multiple courts.", cta: "analyzer" },
              { icon: "🏢", title: "Corporate Lawyers", color: "#34d399", desc: "Vet contracts and NDAs with AI risk scoring, generate employment agreements, and track client billing — all in one place.", cta: "analyzer" },
              { icon: "👮", title: "Criminal Lawyers", color: "#fbbf24", desc: "Verify BNS compliance in police reports, certify digital evidence under BSA Section 63, and research relevant precedents instantly.", cta: "compliance" },
              { icon: "🏠", title: "Real Estate Attorneys", color: "#f87171", desc: "Generate rent agreements, analyze sale deeds for risk clauses, and verify stamp duty compliance under state laws.", cta: "generator" },
              { icon: "💼", title: "Solo Practitioners", color: "#a78bfa", desc: "Run your entire practice — from client intake to final invoice — without expensive software subscriptions or IT support.", cta: "dashboard" },
              { icon: "🎓", title: "Law Firm Associates", color: "#fb923c", desc: "Draft faster with AI Copilot, research statutes and case law with confidence scores, and learn from citation-backed answers.", cta: "editor" },
            ].map((u, i) => (
              <Reveal key={i} delay={i * 0.08}>
                <div style={{
                  padding: "28px 24px", borderRadius: 16,
                  background: t.surface, border: `1.5px solid ${t.border}`,
                  cursor: "pointer", transition: "all 0.25s cubic-bezier(0.22,1,0.36,1)",
                }}
                  onClick={() => go(u.cta)}
                  onMouseEnter={e => { e.currentTarget.style.borderColor = u.color + "45"; e.currentTarget.style.transform = "translateY(-4px)"; e.currentTarget.style.boxShadow = `0 16px 40px ${u.color}15`; }}
                  onMouseLeave={e => { e.currentTarget.style.borderColor = t.border; e.currentTarget.style.transform = "none"; e.currentTarget.style.boxShadow = "none"; }}
                >
                  <div style={{ fontSize: 32, marginBottom: 14, lineHeight: 1 }}>{u.icon}</div>
                  <div style={{ fontSize: 15, fontWeight: 800, color: t.text, marginBottom: 10 }}>{u.title}</div>
                  <p style={{ fontSize: 13, color: t.sub, lineHeight: 1.8, margin: "0 0 16px" }}>{u.desc}</p>
                  <span style={{ fontSize: 12, color: u.color, fontWeight: 700, display: "flex", alignItems: "center", gap: 6 }}>
                    Explore tools <SafeIcon name="arrow" size={12} color={u.color} sw={2.5} />
                  </span>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* ══════════════ FUTURE ROADMAP ══════════════ */}
      <section style={{ padding: "100px 24px", background: t.surface }}>
        <div style={{ maxWidth: 1080, margin: "0 auto" }}>
          <SectionHeading
            eyebrow="Future roadmap"
            title="What is coming next"
            sub="We are building the future of legal practice in India. Here is what is on our roadmap for the next 18 months."
            t={t} center
          />
          <div style={{ display: "grid", gridTemplateColumns: "repeat(2,1fr)", gap: 18 }} className="roadmap-grid">
            {FUTURE_ROADMAP.map((item, i) => (
              <Reveal key={i} delay={i * 0.08}>
                <div style={{
                  padding: "28px 26px", borderRadius: 16,
                  background: t.surface, border: `1.5px solid ${t.border}`,
                  transition: "border-color 0.25s, transform 0.25s, box-shadow 0.25s",
                  cursor: "default",
                  position: "relative", overflow: "hidden",
                }}
                  onMouseEnter={e => { e.currentTarget.style.borderColor = item.color + "45"; e.currentTarget.style.transform = "translateY(-3px)"; e.currentTarget.style.boxShadow = `0 12px 32px ${item.color}12`; }}
                  onMouseLeave={e => { e.currentTarget.style.borderColor = t.border; e.currentTarget.style.transform = "none"; e.currentTarget.style.boxShadow = "none"; }}
                >
                  <div style={{ position: "absolute", left: 0, top: 0, bottom: 0, width: 4, background: item.color, borderRadius: "16px 0 0 16px", opacity: 0.6 }} />
                  <div style={{ display: "flex", alignItems: "flex-start", gap: 16 }}>
                    <div style={{ width: 44, height: 44, borderRadius: 12, background: `${item.color}12`, border: `1.5px solid ${item.color}30`, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                      <SafeIcon name={item.icon} size={20} color={item.color} />
                    </div>
                    <div style={{ flex: 1 }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
                        <div style={{ fontSize: 15, fontWeight: 800, color: t.text }}>{item.title}</div>
                        <span style={{ padding: "3px 10px", borderRadius: 6, background: `${item.color}12`, border: `1px solid ${item.color}25`, fontSize: 10, fontWeight: 800, color: item.color, letterSpacing: "0.02em" }}>
                          {item.eta}
                        </span>
                      </div>
                      <p style={{ fontSize: 13, color: t.sub, lineHeight: 1.8, margin: 0 }}>{item.desc}</p>
                    </div>
                  </div>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* ══════════════ TECH STACK ══════════════ */}
      <section style={{ padding: "80px 24px", background: t.bg }}>
        <div style={{ maxWidth: 1080, margin: "0 auto" }}>
          <Reveal>
            <div style={{
              padding: "40px 44px", borderRadius: 24,
              background: isBold ? `linear-gradient(135deg, ${t.surfaceUp} 0%, ${t.surface} 100%)` : `linear-gradient(135deg, ${t.bg} 0%, ${t.surface} 100%)`,
              border: `1.5px solid ${t.border}`,
              position: "relative", overflow: "hidden",
            }}>
              <div style={{ position: "absolute", top: -60, right: -60, width: 200, height: 200, borderRadius: "50%", background: `radial-gradient(circle, ${t.blue}08 0%, transparent 70%)`, pointerEvents: "none" }} />
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 32, position: "relative" }}>
                <div style={{ maxWidth: 420 }}>
                  <div style={{ fontSize: 11, fontWeight: 800, color: t.muted, letterSpacing: "0.12em", textTransform: "uppercase", marginBottom: 12 }}>Technology</div>
                  <h3 style={{ fontFamily: "'DM Serif Display', serif", fontSize: "1.8rem", fontWeight: 400, color: t.text, margin: "0 0 14px", letterSpacing: "-0.01em" }}>Everything runs on your machine</h3>
                  <p style={{ fontSize: 14, color: t.sub, lineHeight: 1.85, margin: 0 }}>
                    Llama-3 8B via Ollama for legal reasoning. ChromaDB for vector search. Gemini 2.5 Flash for drafting assistance.
                    FastAPI backend. React frontend. No cloud API calls for inference. Your client data never leaves your device —
                    critical for attorney-client privilege.
                  </p>
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, minWidth: 320 }}>
                  {[
                    { label: "Reasoning LLM", value: "Llama-3 8B", color: "#4d7cfe" },
                    { label: "Drafting AI", value: "Gemini 2.5", color: "#f472b6" },
                    { label: "Vector DB", value: "ChromaDB", color: "#fbbf24" },
                    { label: "Retrieval", value: "BM25 + Semantic", color: "#a78bfa" },
                    { label: "Backend", value: "FastAPI", color: "#fb923c" },
                    { label: "Frontend", value: "React", color: "#4d7cfe" },
                    { label: "Auth", value: "JWT + OAuth2", color: "#f87171" },
                    { label: "Privacy", value: "100% Local", color: "#34d399" },
                  ].map((item, i) => (
                    <div key={i} style={{ padding: "12px 16px", borderRadius: 10, background: t.surface, border: `1px solid ${t.border}`, transition: "border-color 0.2s, transform 0.2s" }}
                      onMouseEnter={e => { e.currentTarget.style.borderColor = item.color + "40"; e.currentTarget.style.transform = "translateY(-2px)"; }}
                      onMouseLeave={e => { e.currentTarget.style.borderColor = t.border; e.currentTarget.style.transform = "none"; }}
                    >
                      <div style={{ fontSize: 10, color: t.muted, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 4 }}>{item.label}</div>
                      <div style={{ fontSize: 14, color: item.color, fontWeight: 800, letterSpacing: "-0.01em" }}>{item.value}</div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </Reveal>
        </div>
      </section>

      {/* ══════════════ CTA STRIP ══════════════ */}
      <section style={{ padding: "90px 24px", background: t.surface }}>
        <div style={{ maxWidth: 760, margin: "0 auto", textAlign: "center" }}>
          <Reveal>
            <div style={{
              padding: "56px 44px", borderRadius: 28,
              background: `linear-gradient(135deg, ${t.blue}14 0%, #a78bfa14 50%, #f472b610 100%)`,
              border: `1.5px solid ${t.blue}30`,
              position: "relative", overflow: "hidden",
            }}>
              <div style={{ position: "absolute", inset: 0, backgroundImage: `linear-gradient(${t.blue}06 1px, transparent 1px), linear-gradient(90deg, ${t.blue}06 1px, transparent 1px)`, backgroundSize: "32px 32px" }} />
              <div style={{ position: "relative" }}>
                <h2 style={{ fontFamily: "'DM Serif Display', serif", fontSize: "clamp(1.8rem,3.5vw,2.6rem)", fontWeight: 400, color: t.text, margin: "0 0 16px", letterSpacing: "-0.01em" }}>
                  Start with your document
                </h2>
                <p style={{ fontSize: 15, color: t.sub, margin: "0 0 32px", lineHeight: 1.85 }}>
                  No account. No upload to servers. No subscription.<br />
                  Upload a document and get results in under 60 seconds. Your client data stays on your device.
                </p>
                <div style={{ display: "flex", gap: 12, justifyContent: "center", flexWrap: "wrap" }}>
                  {[
                    { label: "Analyze Document", icon: "doc", fn: () => go("analyzer") },
                    { label: "Check Compliance", icon: "shield", fn: () => go("compliance") },
                    { label: "Certify Evidence", icon: "camera", fn: () => go("evidence") },
                    { label: "Search Cases", icon: "search", fn: () => go("caselaws") },
                  ].map(btn => (
                    <button key={btn.label} onClick={btn.fn} style={{
                      padding: "12px 22px", borderRadius: 10,
                      background: t.blue, color: "#fff",
                      border: "none", fontSize: 13, fontWeight: 700,
                      cursor: "pointer", fontFamily: "inherit",
                      display: "flex", alignItems: "center", gap: 8,
                      transition: "all 0.2s cubic-bezier(0.22,1,0.36,1)",
                    }}
                      onMouseEnter={e => { e.currentTarget.style.transform = "translateY(-2px)"; e.currentTarget.style.boxShadow = `0 8px 24px ${t.blue}45`; }}
                      onMouseLeave={e => { e.currentTarget.style.transform = "none"; e.currentTarget.style.boxShadow = "none"; }}
                    >
                      <SafeIcon name={btn.icon} size={14} color="#fff" sw={2} />
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
      <div style={{ padding: "0 24px 48px" }}>
        <div style={{ maxWidth: 1080, margin: "0 auto" }}>
          <Reveal>
            <div style={{ padding: "16px 22px", borderRadius: 14, background: t.amberDim, border: `1px solid ${t.amber}33`, display: "flex", gap: 12, alignItems: "flex-start" }}>
              <SafeIcon name="alert" size={16} color={t.amber} sw={2} />
              <p style={{ fontSize: 13, color: t.amber, margin: 0, lineHeight: 1.7 }}>
                <strong>Disclaimer:</strong> NyayaSetu provides AI-generated legal guidance for informational purposes only. It does not constitute legal advice. For important legal matters, always exercise independent professional judgment and consult relevant statutes directly.
              </p>
            </div>
          </Reveal>
        </div>
      </div>

      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }
        @media (max-width: 760px) {
          .stat-grid  { grid-template-columns: repeat(2,1fr) !important; }
          .step-grid  { grid-template-columns: repeat(2,1fr) !important; }
          .feat-grid  { grid-template-columns: 1fr !important; }
          .gap-grid   { grid-template-columns: 1fr !important; }
          .user-grid  { grid-template-columns: 1fr !important; }
          .lawyer-grid { grid-template-columns: 1fr !important; }
          .roadmap-grid { grid-template-columns: 1fr !important; }
        }
      `}</style>
    </div>
  );
}