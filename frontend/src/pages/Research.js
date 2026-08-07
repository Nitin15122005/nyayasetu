import { useState, useEffect } from "react";
import { PageTitle, Card, Btn, Input, Ic, ICONS } from "../components/UI";
import ReactMarkdown from "react-markdown";

const API_BASE = process.env.REACT_APP_API_URL || "http://localhost:8001";

const getSafeUrl = (url) => {
  if (!url) return null;
  const lowerUrl = url.toLowerCase();
  if (lowerUrl.startsWith("http://") || lowerUrl.startsWith("https://")) return url;
  return null;
};

export default function Research({ t, toast }) {
  const [activeTab, setActiveTab] = useState("research");
  const [researchMode, setResearchMode] = useState("AI"); // "AI" or "Acts"
  const [expandedJurisdiction, setExpandedJurisdiction] = useState(null);
  const [activeCategory, setActiveCategory] = useState("All");
  const [selectedAct, setSelectedAct] = useState(null);
  const [actSummary, setActSummary] = useState(null);
  const [actLoading, setActLoading] = useState(false);
  const [actsList, setActsList] = useState([]);
  const [actsLoading, setActsLoading] = useState(false);

  useEffect(() => {
    if (!expandedJurisdiction) return;

    const fetchActs = async () => {
      setActsLoading(true);
      try {
        const token = localStorage.getItem("ns_token");
        const headers = { "Content-Type": "application/json" };
        if (token) headers["Authorization"] = `Bearer ${token}`;

        const res = await fetch(`${API_BASE}/api/research/acts`, {
          method: "POST",
          headers,
          body: JSON.stringify({
            jurisdiction: expandedJurisdiction,
            category: activeCategory
          })
        });
        const data = await res.json();
        if (res.ok && data.acts) {
          setActsList(data.acts);
        } else {
          setActsList([]);
        }
      } catch (err) {
        setActsList([]);
      }
      setActsLoading(false);
    };

    fetchActs();
  }, [expandedJurisdiction, activeCategory]);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);

  // Ask states
  const [askQuery, setAskQuery] = useState("");

  // Case Search states
  const [caseQuery, setCaseQuery] = useState("");
  const [court, setCourt] = useState("All Courts");
  const [yearFrom, setYearFrom] = useState("");
  const [yearTo, setYearTo] = useState("");

  // Section Search states
  const [sectionQuery, setSectionQuery] = useState("");
  const [act, setAct] = useState("");

  // Topics states
  const [expandedTopics, setExpandedTopics] = useState(["Constitutional & Administrative", "Criminal Law"]);
  const [selectedSubtopics, setSelectedSubtopics] = useState([]);

  const TOPICS_DATA = [
    { name: "Constitutional & Administrative", subtopics: ["Constitution of India", "Constitutional Law", "Administrative Law", "Human and Civil Rights", "Election", "Natural Justice"] },
    { name: "Criminal Law", subtopics: ["Criminal Law", "Evidence Act, 1872", "Juvenile Justice and Children's Acts", "Narcotics, Intoxicants and Liquor", "Public Accountability", "Preventive Detention"] },
    { name: "Civil & Property", subtopics: ["Property Law", "Limitation", "Specific Relief", "Transfer of Property", "Rent Control"] },
    { name: "Corporate & Commercial", subtopics: ["Company Law", "Insolvency and Bankruptcy", "Arbitration", "Contracts", "Competition Law"] },
    { name: "Tax Laws", subtopics: ["Income Tax", "GST", "Customs", "Excise", "Corporate Tax"] }
  ];

  const JURISDICTIONS_DATA = [
    { name: "Union of India", count: 3914 },
    { name: "Central Provinces And Berar", count: 22 },
    { name: "State of Rajasthan", count: 1190 },
    { name: "State of Tamilnadu- Act", count: 1078 },
    { name: "State of Punjab", count: 987 },
    { name: "State of Uttar Pradesh", count: 944 },
    { name: "State of Madhya Pradesh", count: 927 },
    { name: "State of Odisha", count: 860 },
    { name: "State of Bihar", count: 766 },
    { name: "State of Andhra Pradesh", count: 757 },
    { name: "State of Haryana", count: 745 },
    { name: "State of Maharashtra", count: 716 },
    { name: "State of West Bengal", count: 630 },
    { name: "State of Gujarat", count: 523 },
    { name: "State of Jammu-Kashmir", count: 443 },
    { name: "State of Assam", count: 409 },
    { name: "State of Karnataka", count: 334 },
    { name: "State of Jharkhand", count: 327 },
    { name: "State of Goa", count: 322 },
    { name: "State of Telangana", count: 320 },
    { name: "State of Chattisgarh", count: 255 },
    { name: "NCT Delhi", count: 252 },
    { name: "State of Himachal Pradesh", count: 242 },
    { name: "State of Kerala", count: 230 },
    { name: "Bombay Presidency", count: 214 },
    { name: "State of Uttarakhand", count: 150 },
    { name: "Bengal Presidency", count: 149 },
    { name: "State of Meghalaya", count: 133 },
    { name: "State of Sikkim", count: 115 },
    { name: "Constitution and Amendments", count: 107 },
    { name: "State of Mizoram", count: 88 },
    { name: "State of Manipur", count: 83 },
    { name: "State of Tripura", count: 83 },
    { name: "State of Arunachal Pradesh", count: 80 },
    { name: "International Treaty", count: 78 },
    { name: "State of Nagaland", count: 54 },
    { name: "British India", count: 49 },
    { name: "UT Chandigarh", count: 47 },
    { name: "State of Madhya Bharat", count: 31 },
    { name: "Daman and Diu", count: 29 },
    { name: "State of Puducherry", count: 27 },
    { name: "Andaman and Nicobar Islands", count: 13 },
    { name: "Greater Bengaluru City Corporation", count: 13 },
    { name: "Dadra And Nagar Haveli", count: 12 },
    { name: "Madras Presidency", count: 12 },
    { name: "Chota Nagpur Division", count: 8 },
    { name: "United Nations Conventions", count: 8 },
    { name: "Lakshadweep", count: 5 },
    { name: "UT Ladakh", count: 5 },
    { name: "United Province", count: 5 },
    { name: "Vindhya Province", count: 4 },
    { name: "Nagpur Province", count: 3 },
    { name: "Mysore State", count: 2 },
    { name: "Bhopal State", count: 1 }
  ];

  const ACT_CATEGORIES = [
    "All", "Agriculture & Rural", "Banking & Finance", "Civil Procedure",
    "Constitutional Law", "Contract & Commercial", "Criminal Law",
    "Criminal Law (2023)", "Defense & Security", "Education", "Environment",
    "Family Law", "Healthcare", "IT & Cyber Law", "Infrastructure & Transport",
    "Labor Law", "Media & Information", "Other", "Property Law",
    "Social Welfare", "Tax Law"
  ];

  // Removed static ACTS_LIST

  const toggleSubtopic = (sub) => {
    setSelectedSubtopics(prev => prev.includes(sub) ? prev.filter(s => s !== sub) : [...prev, sub]);
  };

  const toggleTopic = (name) => {
    setExpandedTopics(prev => prev.includes(name) ? prev.filter(n => n !== name) : [...prev, name]);
  };

  const [currentSearch, setCurrentSearch] = useState(null);
  const [loadingMore, setLoadingMore] = useState(false);

  const handleSearch = async (endpoint, payload, isLoadMore = false) => {
    if (isLoadMore) setLoadingMore(true);
    else {
      setLoading(true);
      setResults(null);
      setCurrentSearch({ endpoint, payload, page: 0 });
    }

    try {
      const pageToFetch = isLoadMore ? currentSearch.page + 1 : 0;
      const finalPayload = { ...payload, page: pageToFetch };
      const token = localStorage.getItem("ns_token");
      const headers = { "Content-Type": "application/json" };
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const res = await fetch(`${API_BASE}/api/research/${endpoint}`, {
        method: endpoint === "topics" ? "GET" : "POST",
        headers,
        body: endpoint === "topics" ? null : JSON.stringify(finalPayload)
      });
      const data = await res.json();
      if (res.ok) {
        if (isLoadMore) {
          setResults(prev => ({
            ...data,
            results: [...(prev?.results || []), ...(data.results || [])]
          }));
          setCurrentSearch(prev => ({ ...prev, page: pageToFetch }));
        } else {
          setResults(data);
        }
      } else {
        toast("Search failed", "error");
      }
    } catch (e) {
      toast("Server Error", "error");
    }
    setLoading(false);
    setLoadingMore(false);
  };

  const handleActSelect = async (act) => {
    setSelectedAct(act);
    setActSummary(null);
    setActLoading(true);
    try {
      const token = localStorage.getItem("ns_token");
      const headers = { "Content-Type": "application/json" };
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const res = await fetch(`${API_BASE}/api/research/act_summary`, {
        method: "POST",
        headers,
        body: JSON.stringify({ act_name: act.name, jurisdiction: expandedJurisdiction || "Union of India" })
      });
      const data = await res.json();
      if (res.ok) {
        setActSummary(data);
      } else {
        toast("Failed to load act summary", "error");
      }
    } catch (e) {
      toast("Server Error", "error");
    }
    setActLoading(false);
  };

  const tabs = [
    { id: "research", label: "Research", icon: "book" },
    { id: "case_search", label: "Case Search", icon: "search" },
    { id: "sections", label: "Sections", icon: "doc" },
    { id: "topics", label: "Topics", icon: "grid" }
  ];

  return (
    <div style={{ maxWidth: 1200, margin: "0 auto", padding: "40px 20px" }}>
      {/* Top Header & Tabs */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 32 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <div style={{ padding: 12, borderRadius: 12, background: `${t.blue}22` }}>
            <Ic d={ICONS.book} size={24} color={t.blue} />
          </div>
          <h1 style={{ margin: 0, fontSize: 24, fontWeight: 800 }}>Research</h1>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 24 }}>
          {/* Sub-tabs (Only show in AI mode) */}
          {researchMode === "AI" && (
            <div style={{ display: "flex", background: t.surfaceUp, borderRadius: 24, padding: 4, border: `1px solid ${t.border}` }}>
              {tabs.map(tab => (
                <button
                  key={tab.id}
                  onClick={() => { setActiveTab(tab.id); setResults(null); }}
                  style={{
                    background: activeTab === tab.id ? t.surface : "transparent",
                    border: activeTab === tab.id ? `1px solid ${t.border}` : "none",
                    color: activeTab === tab.id ? t.text : t.sub,
                    padding: "8px 16px",
                    borderRadius: 20,
                    fontSize: 14,
                    fontWeight: activeTab === tab.id ? 700 : 500,
                    cursor: "pointer",
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                    transition: "all 0.2s ease"
                  }}
                >
                  <Ic d={ICONS[tab.icon]} size={16} color={activeTab === tab.id ? t.text : t.sub} />
                  {tab.label}
                </button>
              ))}
            </div>
          )}

          {/* Mode Toggle */}
          <div style={{ display: "flex", background: t.surfaceUp, borderRadius: 24, padding: 4, border: `1px solid ${t.border}` }}>
            {["AI", "Acts"].map(mode => (
              <button
                key={mode}
                onClick={() => { setResearchMode(mode); setResults(null); }}
                style={{
                  background: researchMode === mode ? t.surface : "transparent",
                  border: researchMode === mode ? `1px solid ${t.border}` : "none",
                  color: researchMode === mode ? t.text : t.sub,
                  padding: "8px 16px",
                  borderRadius: 20,
                  fontSize: 14,
                  fontWeight: researchMode === mode ? 700 : 500,
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  transition: "all 0.2s ease"
                }}
              >
                <Ic d={mode === "AI" ? ICONS.book : ICONS.doc} size={16} color={researchMode === mode ? t.text : t.sub} />
                {mode}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div style={{ background: t.surface, borderRadius: 16, border: `1px solid ${t.border}`, minHeight: 600, padding: 40, display: "flex", flexDirection: "column" }}>

        {researchMode === "AI" ? (
          <>
            {/* 1. RESEARCH (Ask a Legal Question) */}
            {activeTab === "research" && (
              <div style={{ margin: "0 auto", maxWidth: results ? "100%" : 700, width: "100%", textAlign: "center" }}>
                <div style={{ marginBottom: 32 }}>
                  <div style={{ width: 64, height: 64, margin: "0 auto 24px", background: `${t.blue}11`, borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center" }}>
                    <Ic d={ICONS.search} size={32} color={t.blue} />
                  </div>
                  <h2 style={{ fontSize: 28, fontWeight: 800, margin: "0 0 12px" }}>Ask a Legal Question</h2>
                  <p style={{ fontSize: 16, color: t.sub, margin: 0 }}>Ask any legal question and get comprehensive research backed by Supreme Court judgments.</p>
                </div>

                <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "center", gap: 12, marginBottom: 40 }}>
                  {["Right to Privacy under Article 21", "Anticipatory Bail principles", "NCLT jurisdiction", "Article 14 reasonable classification"].map((pill, i) => (
                    <button key={i} onClick={() => setAskQuery(pill)} style={{ background: "transparent", border: `1px solid ${t.border}`, borderRadius: 24, padding: "8px 16px", color: t.sub, fontSize: 13, cursor: "pointer" }}>
                      {pill}
                    </button>
                  ))}
                </div>

                <div style={{ position: "relative" }}>
                  <input
                    value={askQuery}
                    onChange={e => setAskQuery(e.target.value)}
                    onKeyDown={e => e.key === "Enter" && handleSearch("ask", { query: askQuery })}
                    placeholder="Rights"
                    style={{ width: "100%", padding: "16px 56px", fontSize: 16, borderRadius: 32, border: `1px solid ${t.border}`, background: t.surfaceUp, color: t.text }}
                  />
                  <div style={{ position: "absolute", left: 24, top: 18 }}>
                    <Ic d={ICONS.search} size={20} color={t.sub} />
                  </div>
                </div>
                <div style={{ display: "flex", justifyContent: "center", gap: 16, marginTop: 16, fontSize: 12, color: t.sub }}>
                  <span>Press Enter to search</span>
                </div>

                {results && results.response && (
                  <div style={{ marginTop: 40, display: "grid", gridTemplateColumns: results.citations ? "1fr 340px" : "1fr", gap: 24, textAlign: "left" }}>
                    <div className="markdown-body" style={{ padding: 32, background: t.surfaceUp, borderRadius: 12, border: `1px solid ${t.border}`, lineHeight: 1.8, fontSize: 15 }}>
                      <ReactMarkdown>{results.response}</ReactMarkdown>
                    </div>
                    {results.citations && results.citations.length > 0 && (
                      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                        <div style={{ fontWeight: 600, color: t.text, display: "flex", alignItems: "center", gap: 8, padding: "0 4px" }}>
                          <Ic d={ICONS.book} size={16} color={t.amber} /> Citations
                        </div>
                        {results.citations.map((c, i) => (
                          <Card key={i} t={t} style={{ padding: 16 }}>
                            <div style={{ fontSize: 12, color: t.amber, marginBottom: 4, fontWeight: 700 }}>[{i + 1}]</div>
                            <h4 style={{ margin: "0 0 8px", color: t.blue, fontSize: 14, lineHeight: 1.4 }}>{c.title}</h4>
                            <div style={{ fontSize: 12, color: t.sub, marginBottom: 12 }}>{c.court} • {c.year}</div>
                            {getSafeUrl(c.url) && (
                              <a href={getSafeUrl(c.url)} target="_blank" rel="noopener noreferrer" style={{ fontSize: 12, color: t.amber, textDecoration: "none", fontWeight: 600, display: "flex", alignItems: "center", gap: 4 }}>
                                Read Judgment ↗
                              </a>
                            )}
                          </Card>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* 2. CASE SEARCH */}
            {activeTab === "case_search" && (
              <div style={{ display: "grid", gridTemplateColumns: "1fr 340px", gap: 40, height: "100%" }}>
                <div>
                  <div style={{ textAlign: "center", marginBottom: 32 }}>
                    <h2 style={{ fontSize: 24, fontWeight: 800, margin: "0 0 8px", color: t.amber }}>Find Relevant Cases</h2>
                    <p style={{ color: t.sub, margin: 0 }}>Search for cases using keywords, legal issues, or topics.</p>
                  </div>

                  <div style={{ background: t.surfaceUp, border: `1px solid ${t.border}`, borderRadius: 16, overflow: "hidden" }}>
                    <div style={{ padding: 16, borderBottom: `1px solid ${t.border}` }}>
                      <input
                        value={caseQuery}
                        onChange={e => setCaseQuery(e.target.value)}
                        placeholder="e.g., anticipatory bail in cheating cases, Section 138 NI Act..."
                        style={{ width: "100%", padding: "12px 16px", fontSize: 15, borderRadius: 8, border: "none", background: "transparent", color: t.text, outline: "none" }}
                      />
                    </div>
                    <div style={{ padding: 16, display: "flex", gap: 16, alignItems: "center" }}>
                      <div style={{ flex: 1, display: "flex", alignItems: "center", gap: 8, fontSize: 13, color: t.sub }}>
                        COURT:
                        <select value={court} onChange={e => setCourt(e.target.value)} style={{ padding: "8px", borderRadius: 6, background: t.surface, border: `1px solid ${t.border}`, color: t.text }}>
                          <option>All Courts</option>
                          <option>Supreme Court</option>
                          <option>High Courts</option>
                        </select>
                        YEAR:
                        <input type="number" value={yearFrom} onChange={e => setYearFrom(e.target.value)} placeholder="From" style={{ width: 80, padding: "8px", borderRadius: 6, background: t.surface, border: `1px solid ${t.border}`, color: t.text, outline: "none" }} />
                        <input type="number" value={yearTo} onChange={e => setYearTo(e.target.value)} placeholder="To" style={{ width: 80, padding: "8px", borderRadius: 6, background: t.surface, border: `1px solid ${t.border}`, color: t.text, outline: "none" }} />
                      </div>
                      <Btn onClick={() => handleSearch("cases", { query: caseQuery, court, year_from: yearFrom, year_to: yearTo })} loading={loading} t={t}>
                        <Ic d={ICONS.search} size={16} /> Search
                      </Btn>
                    </div>
                  </div>

                  {results && results.results && (
                    <div style={{ marginTop: 32, display: "flex", flexDirection: "column", gap: 16 }}>
                      {results.results.map((r, i) => (
                        <Card key={i} t={t} style={{ padding: 20 }}>
                          <h4 style={{ margin: "0 0 8px", color: t.blue, fontSize: 16 }}>{r.title}</h4>
                          <div style={{ fontSize: 13, color: t.sub, marginBottom: 8 }}>{r.court} • {r.year}</div>
                          <p style={{ margin: "0 0 12px", fontSize: 14 }}>{r.snippet}</p>
                          {getSafeUrl(r.url) && (
                            <a href={getSafeUrl(r.url)} target="_blank" rel="noopener noreferrer" style={{ fontSize: 13, color: t.amber, textDecoration: "none", fontWeight: 600 }}>
                              Read Full Judgment on Indian Kanoon ↗
                            </a>
                          )}
                        </Card>
                      ))}
                      {results.results.length > 0 && (
                        <div style={{ display: "flex", justifyContent: "center", marginTop: 16 }}>
                          <Btn onClick={() => handleSearch(currentSearch.endpoint, currentSearch.payload, true)} loading={loadingMore} t={t} style={{ background: "transparent", border: `1px solid ${t.amber}`, color: t.amber }}>
                            Load More Results
                          </Btn>
                        </div>
                      )}
                    </div>
                  )}
                </div>

                <div style={{ borderLeft: `1px solid ${t.border}`, paddingLeft: 40, display: "flex", flexDirection: "column", alignItems: "center", paddingTop: 40 }}>
                  <div style={{ width: 64, height: 64, background: `${t.amber}22`, borderRadius: 16, display: "flex", alignItems: "center", justifyContent: "center", marginBottom: 24 }}>
                    <Ic d={ICONS.search} size={32} color={t.amber} />
                  </div>
                  <h3 style={{ fontSize: 18, margin: "0 0 24px" }}>Case Search</h3>
                  <div style={{ fontSize: 13, color: t.sub, lineHeight: 1.6, textAlign: "center", marginBottom: 32 }}>
                    Find relevant cases using AI-powered semantic search
                  </div>
                  <div style={{ display: "flex", flexDirection: "column", gap: 12, width: "100%" }}>
                    {["Anticipatory bail in economic offences", "Section 138 NI Act dishonour of cheque"].map((ex, i) => (
                      <div key={i} onClick={() => setCaseQuery(ex)} style={{ padding: "12px 16px", borderRadius: 24, border: `1px solid ${t.border}`, fontSize: 13, color: t.sub, cursor: "pointer", textAlign: "center" }}>
                        {ex}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* 3. SECTIONS */}
            {activeTab === "sections" && (
              <div style={{ display: "grid", gridTemplateColumns: "1fr 340px", gap: 40, height: "100%" }}>
                <div>
                  <div style={{ textAlign: "center", marginBottom: 32 }}>
                    <h2 style={{ fontSize: 24, fontWeight: 800, margin: "0 0 8px", color: t.amber }}>Find Cases by Statutory Section</h2>
                    <p style={{ color: t.sub, margin: 0 }}>Enter a section number and act to find relevant case law.</p>
                  </div>

                  <div style={{ background: t.surfaceUp, border: `1px solid ${t.border}`, borderRadius: 16, padding: 24, marginBottom: 32 }}>
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 16 }}>
                      <div>
                        <div style={{ fontSize: 12, color: t.sub, marginBottom: 8, fontWeight: 600 }}>SECTION / ARTICLE</div>
                        <Input value={sectionQuery} onChange={e => setSectionQuery(e.target.value)} placeholder="e.g., 438, 302, 21, 226" t={t} />
                      </div>
                      <div>
                        <div style={{ fontSize: 12, color: t.sub, marginBottom: 8, fontWeight: 600 }}>ACT / STATUTE</div>
                        <select value={act} onChange={e => setAct(e.target.value)} style={{ width: "100%", padding: "12px 16px", borderRadius: 8, background: t.surface, border: `1px solid ${t.border}`, color: t.text }}>
                          <option value="">Select Act</option>
                          <option value="IPC">Indian Penal Code (IPC)</option>
                          <option value="BNS">Bharatiya Nyaya Sanhita (BNS)</option>
                          <option value="CrPC">Code of Criminal Procedure (CrPC)</option>
                          <option value="BNSS">Bharatiya Nagarik Suraksha Sanhita (BNSS)</option>
                          <option value="CPC">Code of Civil Procedure (CPC)</option>
                          <option value="Constitution">Constitution of India</option>
                          <option value="Evidence Act">Indian Evidence Act</option>
                          <option value="BSA">Bharatiya Sakshya Adhiniyam (BSA)</option>
                          <option value="Contract Act">Indian Contract Act</option>
                          <option value="TPA">Transfer of Property Act (TPA)</option>
                          <option value="Limitation Act">Limitation Act</option>
                          <option value="NI Act">Negotiable Instruments Act (NI Act)</option>
                          <option value="Arbitration Act">Arbitration and Conciliation Act</option>
                          <option value="Companies Act">Companies Act</option>
                          <option value="IT Act">Income Tax Act</option>
                          <option value="GST">GST Act</option>
                          <option value="RERA">Real Estate (Regulation and Development) Act (RERA)</option>
                          <option value="PMLA">Prevention of Money Laundering Act (PMLA)</option>
                          <option value="NDPS">Narcotic Drugs and Psychotropic Substances Act (NDPS)</option>
                          <option value="POCSO">Protection of Children from Sexual Offences Act (POCSO)</option>
                          <option value="MV Act">Motor Vehicles Act (MV Act)</option>
                        </select>
                      </div>
                    </div>
                    <Btn onClick={() => handleSearch("sections", { sections: sectionQuery, act })} loading={loading} t={t} style={{ width: "100%", justifyContent: "center" }}>
                      <Ic d={ICONS.search} size={16} /> Search Cases
                    </Btn>
                  </div>

                  {!results ? (
                    <>
                      <h4 style={{ fontSize: 14, color: t.sub, textAlign: "center", margin: "0 0 16px" }}>POPULAR SECTIONS</h4>
                      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
                        {[
                          { sec: "Section 438 CrPC", desc: "Anticipatory Bail" },
                          { sec: "Section 482 CrPC", desc: "Inherent Powers of High Court" },
                          { sec: "Section 302 IPC", desc: "Murder" },
                          { sec: "Article 21", desc: "Right to Life" }
                        ].map((s, i) => (
                          <Card key={i} t={t} hover onClick={() => { setSectionQuery(s.sec); setAct(s.sec.includes("CrPC") ? "CrPC" : "IPC"); }}>
                            <div style={{ fontWeight: 700, marginBottom: 4 }}>{s.sec}</div>
                            <div style={{ fontSize: 13, color: t.sub }}>{s.desc}</div>
                          </Card>
                        ))}
                      </div>
                    </>
                  ) : (
                    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                      {results.results.map((r, i) => (
                        <Card key={i} t={t} style={{ padding: 20 }}>
                          <h4 style={{ margin: "0 0 8px", color: t.blue, fontSize: 16 }}>{r.title}</h4>
                          <div style={{ fontSize: 13, color: t.sub, marginBottom: 8 }}>{r.court} • {r.year}</div>
                          <p style={{ margin: "0 0 12px", fontSize: 14 }}>{r.snippet}</p>
                          {getSafeUrl(r.url) && (
                            <a href={getSafeUrl(r.url)} target="_blank" rel="noopener noreferrer" style={{ fontSize: 13, color: t.amber, textDecoration: "none", fontWeight: 600 }}>
                              Read Full Judgment on Indian Kanoon ↗
                            </a>
                          )}
                        </Card>
                      ))}
                      {results.results.length > 0 && (
                        <div style={{ display: "flex", justifyContent: "center", marginTop: 16 }}>
                          <Btn onClick={() => handleSearch(currentSearch.endpoint, currentSearch.payload, true)} loading={loadingMore} t={t} style={{ background: "transparent", border: `1px solid ${t.amber}`, color: t.amber }}>
                            Load More Results
                          </Btn>
                        </div>
                      )}
                    </div>
                  )}
                </div>

                <div style={{ borderLeft: `1px solid ${t.border}`, paddingLeft: 40, display: "flex", flexDirection: "column", alignItems: "center", paddingTop: 40 }}>
                  <div style={{ width: 64, height: 64, background: `${t.amber}22`, borderRadius: 16, display: "flex", alignItems: "center", justifyContent: "center", marginBottom: 24 }}>
                    <Ic d={ICONS.search} size={32} color={t.amber} />
                  </div>
                  <h3 style={{ fontSize: 18, margin: "0 0 24px", textAlign: "center" }}>Search by Section</h3>
                  <div style={{ fontSize: 13, color: t.sub, lineHeight: 1.6, textAlign: "center", marginBottom: 32 }}>
                    Enter a statutory section or constitutional article to find citing cases.
                  </div>
                </div>
              </div>
            )}

            {/* 4. TOPICS */}
            {activeTab === "topics" && (
              <div style={{ display: "grid", gridTemplateColumns: "360px 1fr", gap: 40, height: "100%", alignItems: "start" }}>

                {/* LEFT SIDE: TOPIC SELECTOR */}
                <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
                  <div style={{ textAlign: "center", marginBottom: 8 }}>
                    <h2 style={{ fontSize: 24, fontWeight: 800, margin: "0 0 8px", color: t.amber }}>Find Acts by Legal Topic</h2>
                    <p style={{ color: t.sub, margin: 0, fontSize: 14 }}>Select topics to discover relevant statutory acts.</p>
                  </div>

                  <div style={{ display: "flex", gap: 12 }}>
                    <input placeholder="Search within selected topics..." style={{ flex: 1, padding: "12px 16px", borderRadius: 24, border: `1px solid ${t.border}`, background: t.surfaceUp, color: t.text, outline: "none" }} />
                    <Btn onClick={() => handleSearch("acts", { category: selectedSubtopics.join(", ") })} loading={loading} t={t} style={{ borderRadius: 24, padding: "0 24px" }}>Search</Btn>
                  </div>

                  {selectedSubtopics.length > 0 && (
                    <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
                      {selectedSubtopics.map(sub => (
                        <div key={sub} style={{ background: `${t.amber}15`, border: `1px solid ${t.amber}44`, color: t.amber, padding: "6px 12px", borderRadius: 20, fontSize: 13, display: "flex", alignItems: "center", gap: 8 }}>
                          {sub} <span style={{ cursor: "pointer", fontWeight: 700 }} onClick={() => toggleSubtopic(sub)}>×</span>
                        </div>
                      ))}
                      <div style={{ fontSize: 13, color: t.sub, cursor: "pointer", marginLeft: 8 }} onClick={() => setSelectedSubtopics([])}>Clear all</div>
                    </div>
                  )}

                  <input placeholder="Filter topics..." style={{ width: "100%", padding: "12px 16px", borderRadius: 8, border: `1px solid ${t.border}`, background: t.surfaceUp, color: t.text, outline: "none" }} />

                  <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                    {TOPICS_DATA.map((topic, i) => (
                      <div key={i} style={{ borderBottom: `1px solid ${t.border}` }}>
                        <div onClick={() => toggleTopic(topic.name)} style={{ padding: "16px 8px", display: "flex", alignItems: "center", justifyContent: "space-between", cursor: "pointer" }}>
                          <div style={{ display: "flex", alignItems: "center", gap: 12, fontWeight: 600, fontSize: 15 }}>
                            <Ic d={ICONS.book} size={18} color={t.amber} />
                            {topic.name} <span style={{ color: t.sub, fontWeight: 400, fontSize: 13 }}>({topic.subtopics.length})</span>
                          </div>
                          <div style={{ transform: expandedTopics.includes(topic.name) ? "rotate(180deg)" : "rotate(0deg)", transition: "transform 0.2s" }}>
                            <Ic d={ICONS.menu} size={16} color={t.sub} />
                          </div>
                        </div>
                        {expandedTopics.includes(topic.name) && (
                          <div style={{ padding: "0 8px 16px", display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                            {topic.subtopics.map(sub => (
                              <label key={sub} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, cursor: "pointer", color: t.sub }}>
                                <input
                                  type="checkbox"
                                  checked={selectedSubtopics.includes(sub)}
                                  onChange={() => toggleSubtopic(sub)}
                                  style={{ width: 16, height: 16, accentColor: t.amber, cursor: "pointer" }}
                                />
                                {sub}
                              </label>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>

                {/* RIGHT SIDE: RESULTS OR PLACEHOLDER */}
                <div style={{ borderLeft: `1px solid ${t.border}`, paddingLeft: 40, display: "flex", flexDirection: "column", minHeight: 600 }}>
                  {!results ? (
                    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", paddingTop: 80 }}>
                      <div style={{ width: 64, height: 64, background: `${t.amber}22`, borderRadius: 16, display: "flex", alignItems: "center", justifyContent: "center", marginBottom: 24 }}>
                        <Ic d={ICONS.book} size={32} color={t.amber} />
                      </div>
                      <h3 style={{ fontSize: 18, margin: "0 0 24px", textAlign: "center" }}>Select Topics to Search</h3>
                      <div style={{ fontSize: 13, color: t.sub, lineHeight: 1.6, textAlign: "center", maxWidth: 300 }}>
                        Choose one or more legal topics from the left panel to discover relevant statutory acts.
                      </div>
                    </div>
                  ) : (
                    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                        <div>
                          <h3 style={{ margin: 0, fontSize: 18 }}>Search Results</h3>
                          <div style={{ fontSize: 13, color: t.sub }}>{(results.acts || results.results)?.length || 0} acts found</div>
                        </div>
                        <div style={{ fontSize: 13, color: t.blue, cursor: "pointer", fontWeight: 600 }} onClick={() => setResults(null)}>Clear Results</div>
                      </div>

                      {(results.acts || results.results)?.map((r, i) => (
                        <Card key={i} t={t} style={{ padding: 20 }}>
                          <h4 style={{ margin: "0 0 8px", color: t.blue, fontSize: 16 }}>{r.title || r.name}</h4>
                          <div style={{ fontSize: 13, color: t.sub, marginBottom: 8 }}>{r.court ? `${r.court} • ` : ""}{r.year}</div>
                          <p style={{ margin: "0 0 12px", fontSize: 14 }}>{r.snippet}</p>
                          {getSafeUrl(r.url) && (
                            <a href={getSafeUrl(r.url)} target="_blank" rel="noopener noreferrer" style={{ fontSize: 13, color: t.amber, textDecoration: "none", fontWeight: 600 }}>
                              Read on Indian Kanoon ↗
                            </a>
                          )}
                        </Card>
                      ))}
                      {results.results?.length > 0 && (
                        <div style={{ display: "flex", justifyContent: "center", marginTop: 16 }}>
                          <Btn onClick={() => handleSearch(currentSearch.endpoint, currentSearch.payload, true)} loading={loadingMore} t={t} style={{ background: "transparent", border: `1px solid ${t.amber}`, color: t.amber }}>
                            Load More Results
                          </Btn>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            )}
          </>
        ) : (
          /* ACTS EXPLORER MODE */
          <div style={{ display: "grid", gridTemplateColumns: "360px 1fr", gap: 40, height: "100%", alignItems: "start" }}>

            {/* LEFT SIDE: ACTS SELECTOR */}
            <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
              <div>
                <h2 style={{ fontSize: 20, fontWeight: 800, margin: "0 0 4px", display: "flex", alignItems: "center", gap: 8, color: t.amber }}>
                  <div style={{ width: 32, height: 32, background: `${t.amber}22`, borderRadius: 8, display: "flex", alignItems: "center", justifyContent: "center" }}>
                    <Ic d={ICONS.doc} size={16} color={t.amber} />
                  </div>
                  Acts Explorer
                </h2>
                <div style={{ fontSize: 13, color: t.sub, marginLeft: 40 }}>18,801 Acts • 54 jurisdictions</div>
              </div>

              <input placeholder="Search acts..." style={{ width: "100%", padding: "12px 16px", borderRadius: 8, border: `1px solid ${t.border}`, background: t.surfaceUp, color: t.text, outline: "none" }} />

              <div style={{ display: "flex", flexDirection: "column", gap: 8, overflowY: "auto", maxHeight: 500, paddingRight: 8 }}>
                {JURISDICTIONS_DATA.map((jur, i) => (
                  <div key={i} style={{ borderBottom: `1px solid ${t.border}` }}>
                    <div onClick={() => setExpandedJurisdiction(expandedJurisdiction === jur.name ? null : jur.name)} style={{ padding: "16px 8px", display: "flex", alignItems: "center", justifyContent: "space-between", cursor: "pointer" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 12, fontWeight: 500, fontSize: 14, color: t.text }}>
                        <div style={{ transform: expandedJurisdiction === jur.name ? "rotate(90deg)" : "rotate(0deg)", transition: "transform 0.2s" }}>
                          <Ic d={ICONS.menu} size={14} color={t.sub} />
                        </div>
                        {jur.name}
                      </div>
                      <div style={{ background: t.surfaceUp, padding: "2px 8px", borderRadius: 12, fontSize: 11, color: t.sub }}>{jur.count}</div>
                    </div>
                    {expandedJurisdiction === jur.name && (
                      <div style={{ padding: "16px", background: `${t.surfaceUp}88`, borderRadius: 12, marginBottom: 8 }}>
                        {jur.name === "Union of India" && (
                          <>
                            <div style={{ fontSize: 11, fontWeight: 700, color: t.sub, marginBottom: 12 }}>CATEGORY</div>
                            <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 24 }}>
                              {ACT_CATEGORIES.map(cat => (
                                <div
                                  key={cat}
                                  onClick={() => setActiveCategory(cat)}
                                  style={{
                                    padding: "6px 12px",
                                    borderRadius: 16,
                                    fontSize: 12,
                                    cursor: "pointer",
                                    background: activeCategory === cat ? t.amber : t.surface,
                                    color: activeCategory === cat ? "#FFF" : t.text,
                                    border: `1px solid ${activeCategory === cat ? t.amber : t.border}`,
                                    transition: "all 0.2s"
                                  }}
                                >
                                  {cat}
                                </div>
                              ))}
                            </div>
                          </>
                        )}

                        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                          {actsLoading ? (
                            Array(5).fill(0).map((_, i) => (
                              <div key={i} style={{ padding: 16, borderRadius: 12, border: `1px solid ${t.border}`, background: t.surface }}>
                                <div style={{ width: "60%", height: 16, background: `${t.border}88`, borderRadius: 4, marginBottom: 12, animation: "pulse 1.5s infinite" }} />
                                <div style={{ width: "40%", height: 12, background: `${t.border}88`, borderRadius: 4, animation: "pulse 1.5s infinite" }} />
                              </div>
                            ))
                          ) : actsList.length > 0 ? (
                            actsList.map((act, idx) => (
                              <div
                                key={idx}
                                onClick={() => handleActSelect(act)}
                                style={{
                                  padding: 16,
                                  borderRadius: 12,
                                  cursor: "pointer",
                                  background: selectedAct?.name === act.name ? `${t.amber}11` : t.surface,
                                  border: `1px solid ${selectedAct?.name === act.name ? t.amber : t.border}`
                                }}
                              >
                                <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 8, color: selectedAct?.name === act.name ? t.amber : t.text }}>{act.name}</div>
                                <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 11, color: t.sub }}>
                                  <span>{act.year || "Indian Kanoon Result"}</span>
                                  {act.isNew && <span style={{ color: t.amber, fontWeight: 700 }}>NEW</span>}
                                  {act.replaces && <span>Replaces: {act.replaces}</span>}
                                </div>
                              </div>
                            ))
                          ) : (
                            <div style={{ padding: 16, textAlign: "center", color: t.sub, fontSize: 13 }}>No acts found for this selection.</div>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {/* RIGHT SIDE: RESULTS OR PLACEHOLDER */}
            <div style={{ borderLeft: `1px solid ${t.border}`, paddingLeft: 40, display: "flex", flexDirection: "column", minHeight: 600 }}>
              {!selectedAct ? (
                <div style={{ display: "flex", flexDirection: "column", alignItems: "center", paddingTop: 80 }}>
                  <div style={{ width: 80, height: 80, background: `${t.amber}11`, borderRadius: 20, display: "flex", alignItems: "center", justifyContent: "center", marginBottom: 24 }}>
                    <Ic d={ICONS.doc} size={40} color={t.amber} />
                  </div>
                  <h3 style={{ fontSize: 20, margin: "0 0 16px", textAlign: "center" }}>Select an Act to explore</h3>
                  <div style={{ fontSize: 14, color: t.sub, lineHeight: 1.6, textAlign: "center", maxWidth: 360 }}>
                    Choose a jurisdiction from the left panel, then select an Act to view its AI summary and full document.
                  </div>
                </div>
              ) : (
                <div style={{ display: "flex", flexDirection: "column" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 24, paddingBottom: 24, borderBottom: `1px solid ${t.border}` }}>
                    <div>
                      <h2 style={{ margin: "0 0 8px", fontSize: 22, fontWeight: 700 }}>{selectedAct.name}</h2>
                      <div style={{ display: "flex", gap: 16, color: t.sub, fontSize: 13 }}>
                        <span style={{ display: "flex", alignItems: "center", gap: 4 }}><Ic d={ICONS.book} size={14} /> {selectedAct.year}</span>
                        <span style={{ display: "flex", alignItems: "center", gap: 4 }}><Ic d={ICONS.doc} size={14} /> {expandedJurisdiction || "Union of India"}</span>
                      </div>
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
                      {getSafeUrl(selectedAct.url) && (
                        <a href={getSafeUrl(selectedAct.url)} target="_blank" rel="noopener noreferrer" style={{ color: t.amber, textDecoration: "none", fontSize: 13, fontWeight: 600, display: "flex", alignItems: "center", gap: 4 }}>
                          View on Indian Kanoon ↗
                        </a>
                      )}
                      <div onClick={() => setSelectedAct(null)} style={{ cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", width: 24, height: 24, borderRadius: "50%", background: `${t.sub}22` }}>×</div>
                    </div>
                  </div>

                  <Card t={t} style={{ padding: 32, marginBottom: 24 }}>
                    <h3 style={{ fontSize: 18, margin: "0 0 24px", display: "flex", alignItems: "center", gap: 8, color: t.amber }}>
                      <Ic d={ICONS.doc} size={20} /> AI Summary
                    </h3>

                    {actLoading ? (
                      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                        <div style={{ height: 16, width: "30%", background: `${t.border}88`, borderRadius: 4, animation: "pulse 1.5s infinite" }} />
                        <div style={{ height: 12, width: "100%", background: `${t.surfaceUp}`, borderRadius: 4, animation: "pulse 1.5s infinite" }} />
                        <div style={{ height: 12, width: "90%", background: `${t.surfaceUp}`, borderRadius: 4, animation: "pulse 1.5s infinite" }} />
                        <div style={{ height: 12, width: "95%", background: `${t.surfaceUp}`, borderRadius: 4, animation: "pulse 1.5s infinite" }} />
                        <div style={{ height: 16, width: "30%", background: `${t.border}88`, borderRadius: 4, animation: "pulse 1.5s infinite", marginTop: 16 }} />
                        <div style={{ height: 12, width: "100%", background: `${t.surfaceUp}`, borderRadius: 4, animation: "pulse 1.5s infinite" }} />
                        <div style={{ height: 12, width: "85%", background: `${t.surfaceUp}`, borderRadius: 4, animation: "pulse 1.5s infinite" }} />
                      </div>
                    ) : (
                      <>
                        <div style={{ marginBottom: 24 }}>
                          <div style={{ fontSize: 12, fontWeight: 700, color: t.amber, marginBottom: 8, textTransform: "uppercase" }}>PURPOSE & OBJECTIVE</div>
                          <div className="markdown-body" style={{ fontSize: 14, color: t.text, lineHeight: 1.6 }}>
                            <ReactMarkdown>{actSummary?.purpose || "No purpose summary available."}</ReactMarkdown>
                          </div>
                        </div>

                        <div style={{ marginBottom: 24 }}>
                          <div style={{ fontSize: 12, fontWeight: 700, color: t.amber, marginBottom: 8, textTransform: "uppercase" }}>KEY PROVISIONS</div>
                          <div className="markdown-body" style={{ fontSize: 14, color: t.text, lineHeight: 1.6 }}>
                            <ReactMarkdown>{actSummary?.key_provisions || "No provisions summary available."}</ReactMarkdown>
                          </div>
                        </div>

                        <div>
                          <div style={{ fontSize: 12, fontWeight: 700, color: t.amber, marginBottom: 8, textTransform: "uppercase" }}>LEGAL IMPLICATIONS</div>
                          <div className="markdown-body" style={{ fontSize: 14, color: t.text, lineHeight: 1.6 }}>
                            <ReactMarkdown>{actSummary?.implications || "No implications available."}</ReactMarkdown>
                          </div>
                        </div>
                      </>
                    )}
                  </Card>
                </div>
              )}
            </div>
          </div>
        )}

      </div>
    </div>
  );
}
