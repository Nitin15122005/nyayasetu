import { useState } from "react";
import { Card, SectionTitle, PageTitle, ErrBox, DropZone, Btn, Input, Tag, Ic, ICONS, ProgressBar, Divider, Spinner } from "../components/UI";

const RISK = {
  "Safe":      { color: "#4d7cfe", dim: "#0a1535", label: "Safe",      icon: "✓" },
  "Caution":   { color: "#94a3b8", dim: "#0f1623", label: "Caution",   icon: "⚠" },
  "High Risk": { color: "#e05c5c", dim: "#1e0a0a", label: "High Risk", icon: "!" },
  "Illegal":   { color: "#c0392b", dim: "#180505", label: "Illegal",   icon: "✕" },
};
const OVERALL_C = { Safe: "#4d7cfe", Moderate: "#94a3b8", High: "#e05c5c", Critical: "#c0392b" };

const ClauseCard = ({ clause, index, t }) => {
  const [open, setOpen] = useState(false);
  const rc   = RISK[clause.risk_level] || RISK["Caution"];
  const text = clause.clause_text || clause.text || "";
  const pct  = Math.round((clause.risk_score || 0) * 100);
  const hasAnalysis = clause.explanation &&
    clause.explanation !== "Could not parse this clause automatically." &&
    clause.explanation !== "Response parsing failed — check raw output above";

  return (
    <div style={{
      borderRadius: 12, border: `1.5px solid ${t.border}`,
      background: t.surface, overflow: "hidden",
      transition: "box-shadow 0.2s, border-color 0.2s",
      animation: "fadeUp 0.3s ease both",
    }}
      onMouseEnter={e => { e.currentTarget.style.borderColor = rc.color + "55"; e.currentTarget.style.boxShadow = `0 4px 20px ${rc.color}14`; }}
      onMouseLeave={e => { e.currentTarget.style.borderColor = t.border; e.currentTarget.style.boxShadow = "none"; }}
    >
      <div style={{ height: 3, background: `linear-gradient(90deg, ${rc.color}, ${rc.color}44)` }} />

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "12px 18px", borderBottom: `1px solid ${t.border}` }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <span style={{ width: 24, height: 24, borderRadius: 6, background: t.surfaceUp, border: `1px solid ${t.border}`, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 10, fontWeight: 800, color: t.muted }}>{index + 1}</span>
          <span style={{ padding: "3px 12px", borderRadius: 99, background: rc.dim, color: rc.color, fontSize: 11, fontWeight: 800, border: `1px solid ${rc.color}30`, display: "flex", alignItems: "center", gap: 5 }}>
            <span style={{ fontSize: 10 }}>{rc.icon}</span>{rc.label}
          </span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <div style={{ padding: "3px 10px", borderRadius: 99, background: t.surfaceUp, border: `1px solid ${t.border}`, display: "flex", alignItems: "center", gap: 6 }}>
            <div style={{ width: 40, height: 3, borderRadius: 2, background: t.muted, overflow: "hidden" }}>
              <div style={{ width: `${pct}%`, height: "100%", background: rc.color, borderRadius: 2 }} />
            </div>
            <span style={{ fontSize: 10, color: rc.color, fontWeight: 800 }}>{pct}%</span>
          </div>
          <button onClick={() => setOpen(!open)} style={{ width: 26, height: 26, borderRadius: 6, background: t.surfaceUp, border: `1px solid ${t.border}`, cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", color: t.sub, fontSize: 10, fontWeight: 700, fontFamily: "inherit" }}>
            {open ? "▲" : "▼"}
          </button>
        </div>
      </div>

      <div style={{ padding: "14px 18px" }}>
        {hasAnalysis ? (
          <>
            <div style={{ padding: "10px 14px", borderRadius: 9, background: `${rc.color}08`, borderLeft: `3px solid ${rc.color}`, marginBottom: 10 }}>
              <p style={{ fontSize: 10, color: rc.color, fontWeight: 800, textTransform: "uppercase", letterSpacing: "0.08em", margin: "0 0 5px" }}>Why flagged</p>
              <p style={{ fontSize: 13, color: t.text, margin: 0, lineHeight: 1.7 }}>{clause.explanation}</p>
            </div>
            {clause.suggestion && (
              <div style={{ padding: "10px 14px", borderRadius: 9, background: t.surfaceUp, border: `1px solid ${t.border}`, display: "flex", gap: 10, alignItems: "flex-start" }}>
                <span style={{ fontSize: 16, flexShrink: 0, lineHeight: 1 }}>💡</span>
                <div>
                  <p style={{ fontSize: 10, color: t.muted, fontWeight: 800, textTransform: "uppercase", letterSpacing: "0.08em", margin: "0 0 4px" }}>Recommendation</p>
                  <p style={{ fontSize: 13, color: t.text, margin: 0, lineHeight: 1.65 }}>{clause.suggestion}</p>
                </div>
              </div>
            )}
          </>
        ) : (
          <div style={{ padding: "10px 14px", borderRadius: 9, background: t.surfaceUp, borderLeft: `3px solid ${rc.color}44`, border: `1px solid ${t.border}` }}>
            <p style={{ fontSize: 10, color: t.muted, fontWeight: 800, textTransform: "uppercase", letterSpacing: "0.08em", margin: "0 0 6px" }}>Clause Content</p>
            <p style={{ fontSize: 13, color: t.sub, margin: 0, lineHeight: 1.75, fontStyle: "italic" }}>
              {text.length > 350 ? text.substring(0, 350) + "…" : text}
            </p>
          </div>
        )}

        {open && (
          <div style={{ marginTop: 12, padding: "12px 14px", borderRadius: 9, background: t.bg, border: `1px solid ${t.border}`, animation: "fadeUp 0.2s ease" }}>
            <p style={{ fontSize: 10, color: t.muted, fontWeight: 800, textTransform: "uppercase", letterSpacing: "0.08em", margin: "0 0 8px" }}>Full clause text</p>
            <p style={{ fontSize: 12, color: t.sub, fontStyle: "italic", lineHeight: 1.8, margin: "0 0 8px" }}>{text || "No text extracted"}</p>
            <p style={{ fontSize: 10, color: t.muted, margin: 0 }}>Confidence: {Math.round((clause.confidence || 0) * 100)}%</p>
          </div>
        )}
      </div>
    </div>
  );
};

// ── Main component — uses state/setState props for persistence ────────────────
export default function Analyzer({ t, toast, state, setState }) {
  // Unpack persisted state
  const { file, result, qaHist, err } = state;
  const setFile   = v => setState(s => ({ ...s, file: v }));
  const setResult = v => setState(s => ({ ...s, result: v }));
  const setQaHist = v => setState(s => ({ ...s, qaHist: typeof v === "function" ? v(s.qaHist) : v }));
  const setErr    = v => setState(s => ({ ...s, err: v }));

  // Local-only (no need to persist)
  const [load,   setLoad]   = useState(false);
  const [tab,    setTab]    = useState("clauses");
  const [q,      setQ]      = useState("");
  const [qaLoad, setQaLoad] = useState(false);
  const [step,   setStep]   = useState(0);

  const STEPS = ["Reading document…", "Segmenting clauses…", "Scoring risk…", "Fetching case laws…", "Done!"];

  const run = async () => {
    setLoad(true); setErr(null); setResult(null); setQaHist([]); setStep(0);
    const si = setInterval(() => setStep(s => Math.min(s + 1, STEPS.length - 2)), 8000);
    try {
      const fd = new FormData(); fd.append("file", file);
      const r = await fetch("http://localhost:8001/api/analyze", { method: "POST", body: fd });
      if (!r.ok) throw new Error((await r.json()).detail || `Error ${r.status}`);
      clearInterval(si); setStep(4);
      setResult(await r.json());
      toast("Analysis complete ✓", "success");
      setTab("clauses");
    } catch (e) { clearInterval(si); setErr(e.message); toast(e.message, "error"); }
    finally { setLoad(false); }
  };

  const ask = async () => {
    if (!q.trim() || !result?.session_id) return;
    const question = q.trim(); setQ(""); setQaLoad(true);
    try {
      const r = await fetch("http://localhost:8001/api/qa", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, session_id: result.session_id }),
      });
      const d = await r.json();
      setQaHist(p => [...p, { question, ...d }]);
    } catch (e) { toast("Q&A failed", "error"); }
    finally { setQaLoad(false); }
  };

  const riskColor = result ? OVERALL_C[result.overall_risk] || "#94a3b8" : null;

  // ── Filter out the "API key not configured" placeholder ──────────────────
  const validCaseLaws = result?.case_laws?.filter(
    c => c.title !== "IndianKanoon API key not configured" && c.title !== "No case laws found"
  ) || [];

  const TABS = [
    { id: "clauses",  label: "Clauses",   count: result?.clauses?.length },
    { id: "qa",       label: "Questions", count: qaHist.length || null },
    { id: "caselaws", label: "Case Laws", count: validCaseLaws.length || null },
  ];

  return (
    <div style={{ maxWidth: 860, margin: "0 auto", padding: "52px 24px", animation: "fadeUp 0.4s ease" }}>
      <PageTitle icon="doc" title="Document Analyzer" badge="BNS 2023"
        desc="Upload any legal document. Every clause is extracted, risk-scored, and explained in plain language."
        t={t} />

      {/* Upload — only shown when no result */}
      {!result && (
        <Card t={t} style={{ marginBottom: 20 }}>
          <DropZone onFile={setFile} accept=".pdf,.png,.jpg,.jpeg"
            hint="Rental agreement · Employment contract · FIR · Legal notice · Loan document" t={t} />
          {file && (
            <div style={{ marginTop: 18, display: "flex", gap: 10, alignItems: "center" }}>
              <Btn onClick={run} disabled={load} loading={load} t={t}>
                {load ? STEPS[step] : "Run Analysis"}
              </Btn>
              <button onClick={() => setFile(null)} style={{ background: "none", border: "none", cursor: "pointer", color: t.sub, fontSize: 13, fontFamily: "inherit" }}>Clear</button>
            </div>
          )}
        </Card>
      )}

      {/* Loading */}
      {load && (
        <Card t={t} style={{ textAlign: "center", padding: "56px 24px" }}>
          <Spinner c={t.blue} size={28} />
          <p style={{ color: t.text, marginTop: 20, fontSize: 16, fontWeight: 700 }}>{STEPS[step]}</p>
          <p style={{ color: t.sub, marginTop: 6, fontSize: 12 }}>This takes 30–60 seconds · Do not close this tab</p>
          <div style={{ maxWidth: 240, margin: "20px auto 0" }}>
            <ProgressBar value={(step + 1) / STEPS.length} color={t.blue} t={t} />
          </div>
        </Card>
      )}

      {err && <ErrBox msg={err} t={t} />}

      {/* Results — persists across page changes */}
      {result && !load && (
        <>
          {/* Overview */}
          <Card t={t} style={{ marginBottom: 16 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12, flexWrap: "wrap", marginBottom: 18 }}>
              <div>
                <div style={{ display: "flex", alignItems: "center", gap: 9, marginBottom: 5 }}>
                  <Ic d={ICONS.doc} size={15} color={t.blue} />
                  <span style={{ fontWeight: 800, color: t.text, fontSize: 15 }}>{result.document_name}</span>
                  <Tag label={result.document_type} variant="info" t={t} />
                </div>
                <p style={{ fontSize: 12, color: t.muted, margin: 0 }}>{result.total_clauses} clauses analyzed</p>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
                <div style={{ padding: "6px 14px", borderRadius: 8, background: `${riskColor}18`, border: `1px solid ${riskColor}44`, color: riskColor, fontSize: 13, fontWeight: 800 }}>
                  {result.overall_risk} Risk
                </div>
                <div style={{ padding: "6px 14px", borderRadius: 8, background: t.surfaceUp, border: `1px solid ${t.border}`, fontSize: 12, color: t.sub, fontWeight: 600 }}>
                  BNS: <strong style={{ color: t.text }}>{result.compliance_score}/100</strong>
                </div>
                <button onClick={() => { setResult(null); setFile(null); setQaHist([]); setErr(null); }} style={{ background: "none", border: "none", cursor: "pointer", color: t.sub, fontSize: 12, fontFamily: "inherit", fontWeight: 600 }}>
                  ← New doc
                </button>
              </div>
            </div>

            {/* Summary */}
            <div style={{ padding: "14px 18px", borderRadius: 10, background: `${t.blue}0a`, border: `1px solid ${t.blue}20`, marginBottom: 16, fontSize: 14, color: t.text, lineHeight: 1.75 }}>
              {result.summary}
            </div>

            {/* Risk distribution */}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 10, marginBottom: 16 }}>
              {Object.entries(RISK).map(([k, rc]) => (
                <div key={k} style={{ textAlign: "center", padding: "14px 8px", borderRadius: 10, background: t.surfaceUp, border: `1.5px solid ${t.border}`, transition: "all 0.2s" }}
                  onMouseEnter={e => { e.currentTarget.style.borderColor = rc.color + "55"; e.currentTarget.style.transform = "scale(1.03)"; }}
                  onMouseLeave={e => { e.currentTarget.style.borderColor = t.border; e.currentTarget.style.transform = "scale(1)"; }}
                >
                  <div style={{ fontSize: "1.8rem", fontWeight: 900, color: rc.color, lineHeight: 1 }}>{result.risk_distribution?.[k] || 0}</div>
                  <div style={{ fontSize: 10, color: t.sub, fontWeight: 700, marginTop: 4, letterSpacing: "0.04em" }}>{k}</div>
                  <div style={{ height: 2, borderRadius: 1, background: rc.color + "44", marginTop: 8 }} />
                </div>
              ))}
            </div>

            {result.recommendations?.map((rec, i) => (
              <p key={i} style={{ fontSize: 13, color: t.sub, margin: "4px 0", lineHeight: 1.6 }}>{rec}</p>
            ))}
          </Card>

          {/* Tabs */}
          <div style={{ display: "flex", gap: 3, marginBottom: 16 }}>
            {TABS.map(tb => (
              <button key={tb.id} onClick={() => setTab(tb.id)} style={{
                padding: "8px 18px", borderRadius: 9,
                fontSize: 13, fontWeight: 700, fontFamily: "inherit", cursor: "pointer",
                background: tab === tb.id ? `${t.blue}18` : "transparent",
                color: tab === tb.id ? t.blue : t.sub,
                border: `1px solid ${tab === tb.id ? `${t.blue}44` : "transparent"}`,
                transition: "all 0.15s",
              }}>
                {tb.label}
                {tb.count != null && <span style={{ marginLeft: 6, fontSize: 11, opacity: 0.7 }}>({tb.count})</span>}
              </button>
            ))}
          </div>

          {/* Clauses tab */}
          {tab === "clauses" && (
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {result.clauses?.length > 0
                ? result.clauses.map((cl, i) => <ClauseCard key={i} clause={cl} index={i} t={t} />)
                : <Card t={t} style={{ textAlign: "center", padding: 40 }}><p style={{ color: t.muted, fontSize: 13 }}>No clauses extracted from this document.</p></Card>
              }
            </div>
          )}

          {/* Q&A tab */}
          {tab === "qa" && (
            <Card t={t}>
              <SectionTitle t={t}>Ask about this document</SectionTitle>
              <p style={{ fontSize: 13, color: t.sub, marginBottom: 16, lineHeight: 1.7 }}>
                Ask anything specific — "What is the notice period?", "Can the landlord raise rent?", "What happens if I miss a payment?"
              </p>
              <div style={{ display: "flex", gap: 8, marginBottom: 20 }}>
                <Input value={q} onChange={e => setQ(e.target.value)}
                  onKeyDown={e => e.key === "Enter" && ask()}
                  placeholder="Ask a question about this document…" t={t} />
                <Btn onClick={ask} disabled={qaLoad || !q.trim()} loading={qaLoad} small t={t}>
                  {!qaLoad && <Ic d={ICONS.arrow} size={14} color="#fff" sw={2.5} />}
                </Btn>
              </div>

              {qaHist.length === 0 && (
                <div style={{ textAlign: "center", padding: "32px 0", color: t.muted, fontSize: 13 }}>No questions yet — type above and press Enter</div>
              )}

              {[...qaHist].reverse().map((qa, i) => (
                <div key={i} style={{ padding: "14px 18px", borderRadius: 10, background: t.surfaceUp, border: `1px solid ${t.border}`, marginBottom: 10, animation: "fadeUp 0.25s ease" }}>
                  <p style={{ fontWeight: 800, color: t.text, fontSize: 13, marginBottom: 8 }}>Q: {qa.question}</p>
                  <p style={{ fontSize: 14, color: t.sub, lineHeight: 1.75, margin: 0 }}>{qa.answer}</p>
                  {qa.confidence != null && (
                    <div style={{ marginTop: 10 }}>
                      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                        <span style={{ fontSize: 10, color: t.muted }}>Confidence</span>
                        <span style={{ fontSize: 10, color: t.muted }}>{Math.round(qa.confidence * 100)}%</span>
                      </div>
                      <ProgressBar value={qa.confidence} color={qa.confidence > 0.7 ? "#4d7cfe" : qa.confidence > 0.4 ? "#94a3b8" : "#e05c5c"} t={t} />
                    </div>
                  )}
                  {qa.disclaimer && (
                    <p style={{ fontSize: 11, color: t.sub, marginTop: 8, padding: "5px 10px", background: t.surfaceUp, border: `1px solid ${t.border}`, borderRadius: 6 }}>
                      ℹ️ {qa.disclaimer}
                    </p>
                  )}
                </div>
              ))}
            </Card>
          )}

          {/* Case laws tab */}
          {tab === "caselaws" && (
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              {validCaseLaws.length === 0 ? (
                <Card t={t} style={{ textAlign: "center", padding: "40px 24px" }}>
                  <Ic d={ICONS.search} size={32} color={t.muted} />
                  <p style={{ color: t.sub, marginTop: 14, fontSize: 14, fontWeight: 600 }}>No relevant case laws found</p>
                  <p style={{ color: t.muted, fontSize: 12, marginTop: 6, lineHeight: 1.7 }}>
                    Make sure <code style={{ background: t.surfaceUp, padding: "2px 6px", borderRadius: 4 }}>INDIANKANOON_API_KEY</code> is set in your .env,
                    or the document may not have enough flagged content to build a relevant query.
                  </p>
                </Card>
              ) : (
                validCaseLaws.map((c, i) => (
                  <Card t={t} key={i} style={{ animation: `fadeUp 0.3s ease ${i * 0.06}s both` }}>
                    <div style={{ display: "flex", justifyContent: "space-between", gap: 8, marginBottom: 8, flexWrap: "wrap" }}>
                      <p style={{ fontWeight: 800, fontSize: 14, color: t.text, margin: 0, lineHeight: 1.4 }}>{c.title}</p>
                      <div style={{ display: "flex", gap: 6 }}>
                        {c.year  && <Tag label={c.year}  variant="info" t={t} />}
                        {c.court && <Tag label={c.court} variant="gold" t={t} />}
                      </div>
                    </div>
                    <p style={{ fontSize: 13, color: t.sub, lineHeight: 1.75, margin: "0 0 12px" }}>{c.summary}</p>
                    {c.url && (
                      <a href={c.url} target="_blank" rel="noreferrer" style={{ color: t.blue, fontSize: 12, fontWeight: 700, textDecoration: "none", display: "inline-flex", alignItems: "center", gap: 5, padding: "6px 14px", borderRadius: 7, background: `${t.blue}10`, border: `1px solid ${t.blue}20` }}>
                        View full judgment <Ic d={ICONS.external} size={11} color={t.blue} />
                      </a>
                    )}
                  </Card>
                ))
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}