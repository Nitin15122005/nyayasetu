import { Ic, ICONS } from "../components/UI";

const LINKS = [
  { label: "Document Analyzer", id: "analyzer",   desc: "Risk-score any legal document" },
  { label: "BNS Compliance",    id: "compliance",  desc: "IPC → BNS 2023 migration" },
  { label: "Evidence Cert",     id: "evidence",    desc: "BSA Section 63 SHA-256" },
  { label: "Case Laws",         id: "caselaws",    desc: "IndianKanoon search" },
];

const LAWS = [
  { label: "BNS 2023",  href: "https://indiacode.nic.in/bitstream/123456789/20062/1/bharatiya_nyaya_sanhita_2023.pdf" },
  { label: "BNSS 2023", href: "https://indiacode.nic.in/bitstream/123456789/20063/1/bharatiya_nagarik_suraksha_sanhita_2023.pdf" },
  { label: "BSA 2023",  href: "https://indiacode.nic.in/bitstream/123456789/20064/1/bharatiya_sakshya_adhiniyam_2023.pdf" },
  { label: "India Code",href: "https://indiacode.nic.in" },
  { label: "IndianKanoon", href: "https://indiankanoon.org" },
];

export default function Footer({ t, go }) {
  const year = new Date().getFullYear();
  return (
    <footer style={{
      background: t.surface,
      borderTop: `1px solid ${t.border}`,
      padding: "56px 24px 28px",
      fontFamily: "'DM Sans', system-ui, sans-serif",
    }}>
      <div style={{ maxWidth: 1000, margin: "0 auto" }}>

        {/* Top row */}
        <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr 1fr 1fr", gap: 40, marginBottom: 48 }} className="footer-grid">

          {/* Brand column */}
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 16 }}>
              <div style={{
                width: 36, height: 36, borderRadius: 10,
                background: `linear-gradient(135deg, ${t.blue} 0%, #1a3580 100%)`,
                display: "flex", alignItems: "center", justifyContent: "center",
                boxShadow: `0 4px 12px ${t.blue}44`,
              }}>
                <Ic d={ICONS.scale} size={16} color="#fff" sw={2} />
              </div>
              <div>
                <div style={{ fontSize: 17, fontWeight: 900, color: t.text, letterSpacing: "-0.02em", lineHeight: 1 }}>
                  Nyaya<span style={{ color: t.blue }}>Setu</span>
                </div>
                <div style={{ fontSize: 9, color: t.muted, fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase" }}>
                  Bridge to Justice
                </div>
              </div>
            </div>
            <p style={{ fontSize: 13, color: t.sub, lineHeight: 1.8, margin: "0 0 20px", maxWidth: 280 }}>
              AI-powered legal tools for Indian citizens. Built on BNS, BNSS, and BSA 2023.
              Runs locally — zero data leaves your device.
            </p>
            {/* Status pills */}
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              {[
                { label: "BNS 2023", color: "#4d7cfe" },
                { label: "Local LLM", color: "#34d399" },
                { label: "Open Source", color: "#a78bfa" },
              ].map(p => (
                <span key={p.label} style={{
                  padding: "3px 10px", borderRadius: 99, fontSize: 10, fontWeight: 700,
                  background: `${p.color}14`, border: `1px solid ${p.color}2e`, color: p.color,
                }}>
                  {p.label}
                </span>
              ))}
            </div>
          </div>

          {/* Tools column */}
          <div>
            <div style={{ fontSize: 11, fontWeight: 800, color: t.muted, letterSpacing: "0.1em", textTransform: "uppercase", marginBottom: 16 }}>Tools</div>
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {LINKS.map(l => (
                <button key={l.id} onClick={() => go(l.id)} style={{
                  background: "none", border: "none", cursor: "pointer",
                  padding: 0, textAlign: "left", fontFamily: "inherit",
                }}>
                  <div style={{ fontSize: 13, fontWeight: 600, color: t.sub, marginBottom: 1, transition: "color 0.15s" }}
                    onMouseEnter={e => e.currentTarget.style.color = t.blue}
                    onMouseLeave={e => e.currentTarget.style.color = t.sub}
                  >
                    {l.label}
                  </div>
                  <div style={{ fontSize: 11, color: t.muted }}>{l.desc}</div>
                </button>
              ))}
            </div>
          </div>

          {/* Legal resources */}
          <div>
            <div style={{ fontSize: 11, fontWeight: 800, color: t.muted, letterSpacing: "0.1em", textTransform: "uppercase", marginBottom: 16 }}>Legal Resources</div>
            <div style={{ display: "flex", flexDirection: "column", gap: 9 }}>
              {LAWS.map(l => (
                <a key={l.label} href={l.href} target="_blank" rel="noreferrer" style={{
                  fontSize: 13, color: t.sub, textDecoration: "none", fontWeight: 500,
                  display: "flex", alignItems: "center", gap: 5, transition: "color 0.15s",
                }}
                  onMouseEnter={e => e.currentTarget.style.color = t.blue}
                  onMouseLeave={e => e.currentTarget.style.color = t.sub}
                >
                  {l.label} <Ic d={ICONS.external} size={10} color="inherit" />
                </a>
              ))}
            </div>
          </div>

          {/* Built with */}
          <div>
            <div style={{ fontSize: 11, fontWeight: 800, color: t.muted, letterSpacing: "0.1em", textTransform: "uppercase", marginBottom: 16 }}>Built With</div>
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {["Llama-3 8B (Ollama)", "ChromaDB", "FastAPI", "React", "MiniLM + BM25", "ReportLab", "PyMuPDF"].map(s => (
                <span key={s} style={{ fontSize: 12, color: t.muted, fontWeight: 500 }}>{s}</span>
              ))}
            </div>
          </div>
        </div>

        {/* Divider */}
        <div style={{ height: 1, background: t.border, marginBottom: 24 }} />

        {/* Bottom row */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 12 }}>
          <p style={{ fontSize: 12, color: t.muted, margin: 0 }}>
            © {year} NyayaSetu · Team IKS · SPIT CSE 2025–26
          </p>
          <p style={{ fontSize: 12, color: t.muted, margin: 0, textAlign: "right", maxWidth: 480, lineHeight: 1.6 }}>
            Informational purposes only. Not legal advice. Consult a qualified Indian advocate for legal matters.
          </p>
        </div>
      </div>

      <style>{`
        @media (max-width: 760px) {
          .footer-grid { grid-template-columns: 1fr 1fr !important; }
        }
        @media (max-width: 480px) {
          .footer-grid { grid-template-columns: 1fr !important; }
        }
      `}</style>
    </footer>
  );
}