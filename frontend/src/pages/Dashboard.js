import { useState, useEffect, useCallback } from "react";
import { PageTitle, Card, Btn, Input, Ic, ICONS, Tag, Spinner } from "../components/UI";

/* ═══════════════════════════════════════════════════════════════════════════════
   UNIFIED DASHBOARD — Nyaya-Setu Legal Management System
   Single-page layout. No internal tabs (top nav handles routing).
   All sections visible: Overview Stats, Cases, Tasks, Hearings, 
   Calendar Events, Invoices, Tools (CNR + Doc Gen)
   ═══════════════════════════════════════════════════════════════════════════════ */

const API_BASE = "http://localhost:8001";

export default function Dashboard({ t, toast }) {
  // ── Auth State ──────────────────────────────────────────────────────────────
  const [token, setToken] = useState(localStorage.getItem("ns_token"));
  const [user, setUser] = useState(null);
  const [authLoading, setAuthLoading] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isRegister, setIsRegister] = useState(false);
  const [fullName, setFullName] = useState("");
  const [phone, setPhone] = useState("");

  // ── Data State ────────────────────────────────────────────────────────────────
  const [cases, setCases] = useState([]);
  const [tasks, setTasks] = useState([]);
  const [hearings, setHearings] = useState([]);
  const [invoices, setInvoices] = useState([]);
  const [calendarEvents, setCalendarEvents] = useState([]);
  const [calendarStats, setCalendarStats] = useState(null);
  const [cnrResult, setCnrResult] = useState(null);
  const [docResult, setDocResult] = useState(null);

  // ── Loading States ────────────────────────────────────────────────────────────
  const [loading, setLoading] = useState({
    cases: false, tasks: false, hearings: false, invoices: false,
    calendar: false, cnr: false, doc: false, deleteCase: null,
  });

  // ── Form State ────────────────────────────────────────────────────────────────
  const [newCase, setNewCase] = useState({ title: "", cnr_number: "", court_name: "", client_name: "", status: "Active" });
  const [newTask, setNewTask] = useState({ title: "", description: "", due_date: "", case_id: "" });
  const [newHearing, setNewHearing] = useState({ purpose: "", hearing_date: "", case_id: "", notes: "" });
  const [newInvoice, setNewInvoice] = useState({ client_name: "", amount: "", due_date: "" });
  const [newCalendarEvent, setNewCalendarEvent] = useState({
    title: "", event_type: "hearing", event_date: "", event_time: "", court: "", description: "", matter_id: "",
  });
  const [cnrNumber, setCnrNumber] = useState("");
  const [docGen, setDocGen] = useState({ doc_type: "Rent Agreement", party_a: "", party_b: "", details: "" });

  // ── UI State ──────────────────────────────────────────────────────────────────
  const [selectedCase, setSelectedCase] = useState(null);
  const [showCaseDetail, setShowCaseDetail] = useState(false);
  const [expandedSection, setExpandedSection] = useState(null);

  useEffect(() => { if (token) fetchUser(); }, [token]);

  const fetchUser = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/auth/me`, { headers: { Authorization: `Bearer ${token}` } });
      if (res.ok) { setUser(await res.json()); fetchAllData(); }
      else handleLogout();
    } catch (e) { toast("Connection error — backend may be offline", "error"); }
  }, [token]);

  const handleLogout = () => {
    localStorage.removeItem("ns_token"); setToken(null); setUser(null);
    setCases([]); setTasks([]); setHearings([]); setInvoices([]);
    setCalendarEvents([]); setCalendarStats(null);
    toast("Logged out", "info");
  };

  const fetchAllData = useCallback(async () => {
    const headers = { Authorization: `Bearer ${token}` };
    try {
      const [cRes, tRes, hRes, iRes, calRes, calStatsRes] = await Promise.all([
        fetch(`${API_BASE}/api/cases`, { headers }), fetch(`${API_BASE}/api/tasks`, { headers }),
        fetch(`${API_BASE}/api/hearings`, { headers }), fetch(`${API_BASE}/api/invoices`, { headers }),
        fetch(`${API_BASE}/api/calendar/events`, { headers }), fetch(`${API_BASE}/api/calendar/stats/summary`, { headers }),
      ]);
      if (cRes.ok) setCases(await cRes.json()); if (tRes.ok) setTasks(await tRes.json());
      if (hRes.ok) setHearings(await hRes.json()); if (iRes.ok) setInvoices(await iRes.json());
      if (calRes.ok) setCalendarEvents(await calRes.json()); if (calStatsRes.ok) setCalendarStats(await calStatsRes.json());
    } catch (e) { console.error("[Dashboard] fetchAllData error:", e); toast("Failed to load dashboard data", "error"); }
  }, [token]);

  const handleAuth = async () => {
    if (!email || !password) { toast("Email and password are required", "error"); return; }
    if (isRegister && !fullName) { toast("Full name is required", "error"); return; }
    setAuthLoading(true);
    const url = isRegister ? `${API_BASE}/api/auth/register` : `${API_BASE}/api/auth/login`;
    const body = isRegister ? JSON.stringify({ email, password, full_name: fullName || email.split("@")[0], phone: phone || "0000000000" }) : JSON.stringify({ email, password });
    try {
      const res = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body });
      const data = await res.json();
      if (res.ok) {
        if (isRegister) { toast("Registration successful — please log in", "success"); setIsRegister(false); setFullName(""); setPhone(""); }
        else { localStorage.setItem("ns_token", data.access_token); setToken(data.access_token); toast(`Welcome back, ${data.user?.full_name || ""}`, "success"); }
      } else toast(data.detail || "Authentication failed", "error");
    } catch (e) { toast("Server connection failed", "error"); }
    setAuthLoading(false);
  };

  const handleCreateCase = async () => {
    if (!newCase.title.trim()) { toast("Case title is required", "error"); return; }
    setLoading(p => ({ ...p, cases: true }));
    try {
      const res = await fetch(`${API_BASE}/api/cases`, {
        method: "POST", headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify(newCase),
      });
      if (res.ok) { const created = await res.json(); toast(`Case "${created.title}" created`, "success"); setNewCase({ title: "", cnr_number: "", court_name: "", client_name: "", status: "Active" }); fetchAllData(); }
      else { const err = await res.json(); toast(err.detail || "Failed to create case", "error"); }
    } catch (e) { toast("Error creating case", "error"); }
    setLoading(p => ({ ...p, cases: false }));
  };

  const handleDeleteCase = async (caseId) => {
    if (!window.confirm("Delete this case and all associated tasks/hearings?")) return;
    setLoading(p => ({ ...p, deleteCase: caseId }));
    try {
      const res = await fetch(`${API_BASE}/api/cases/${caseId}`, { method: "DELETE", headers: { Authorization: `Bearer ${token}` } });
      if (res.ok) { toast("Case deleted successfully", "success"); fetchAllData(); }
      else { const err = await res.json(); toast(err.detail || "Failed to delete case", "error"); }
    } catch (e) { toast("Error deleting case", "error"); }
    setLoading(p => ({ ...p, deleteCase: null }));
  };

  const fetchCaseDetail = async (caseId) => {
    try {
      const res = await fetch(`${API_BASE}/api/cases/${caseId}`, { headers: { Authorization: `Bearer ${token}` } });
      if (res.ok) { setSelectedCase(await res.json()); setShowCaseDetail(true); }
    } catch (e) { toast("Failed to load case details", "error"); }
  };

  const handleCreateTask = async () => {
    if (!newTask.title.trim() || !newTask.due_date) { toast("Title and Due Date are required", "error"); return; }
    setLoading(p => ({ ...p, tasks: true }));
    try {
      const res = await fetch(`${API_BASE}/api/tasks`, {
        method: "POST", headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ ...newTask, due_date: new Date(newTask.due_date).toISOString() }),
      });
      if (res.ok) { toast("Task created", "success"); setNewTask({ title: "", description: "", due_date: "", case_id: "" }); fetchAllData(); }
      else { const err = await res.json(); toast(err.detail || "Failed to create task", "error"); }
    } catch (e) { toast("Error creating task", "error"); }
    setLoading(p => ({ ...p, tasks: false }));
  };

  const handleCreateHearing = async () => {
    if (!newHearing.purpose.trim() || !newHearing.hearing_date || !newHearing.case_id) { toast("Purpose, Date, and Case are required", "error"); return; }
    setLoading(p => ({ ...p, hearings: true }));
    try {
      const res = await fetch(`${API_BASE}/api/hearings`, {
        method: "POST", headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ ...newHearing, hearing_date: new Date(newHearing.hearing_date).toISOString() }),
      });
      if (res.ok) { toast("Hearing scheduled", "success"); setNewHearing({ purpose: "", hearing_date: "", case_id: "", notes: "" }); fetchAllData(); }
      else { const err = await res.json(); toast(err.detail || "Not authorized for this case", "error"); }
    } catch (e) { toast("Error scheduling hearing", "error"); }
    setLoading(p => ({ ...p, hearings: false }));
  };

  const handleCreateInvoice = async () => {
    if (!newInvoice.client_name.trim() || !newInvoice.amount || !newInvoice.due_date) { toast("Client name, amount, and due date are required", "error"); return; }
    setLoading(p => ({ ...p, invoices: true }));
    try {
      const res = await fetch(`${API_BASE}/api/invoices`, {
        method: "POST", headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ ...newInvoice, amount: parseFloat(newInvoice.amount), due_date: new Date(newInvoice.due_date).toISOString() }),
      });
      if (res.ok) { toast("Invoice created", "success"); setNewInvoice({ client_name: "", amount: "", due_date: "" }); fetchAllData(); }
      else { const err = await res.json(); toast(err.detail || "Failed to create invoice", "error"); }
    } catch (e) { toast("Error creating invoice", "error"); }
    setLoading(p => ({ ...p, invoices: false }));
  };

  const handleCreateCalendarEvent = async () => {
    if (!newCalendarEvent.title.trim() || !newCalendarEvent.event_date) { toast("Title and event date are required", "error"); return; }
    setLoading(p => ({ ...p, calendar: true }));
    try {
      const res = await fetch(`${API_BASE}/api/calendar/events`, {
        method: "POST", headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify(newCalendarEvent),
      });
      if (res.ok) { toast("Calendar event added", "success"); setNewCalendarEvent({ title: "", event_type: "hearing", event_date: "", event_time: "", court: "", description: "", matter_id: "" }); fetchAllData(); }
      else { const err = await res.json(); toast(err.detail || "Failed to add event", "error"); }
    } catch (e) { toast("Error adding calendar event", "error"); }
    setLoading(p => ({ ...p, calendar: false }));
  };

  const handleDeleteCalendarEvent = async (eventId) => {
    if (!window.confirm("Delete this calendar event?")) return;
    try {
      const res = await fetch(`${API_BASE}/api/calendar/events/${eventId}`, { method: "DELETE", headers: { Authorization: `Bearer ${token}` } });
      if (res.ok) { toast("Event deleted", "success"); fetchAllData(); }
    } catch (e) { toast("Error deleting event", "error"); }
  };

  const handleCnrLookup = async () => {
    if (!cnrNumber.trim() || cnrNumber.length < 16) { toast("Enter a valid 16-character CNR number", "error"); return; }
    setLoading(p => ({ ...p, cnr: true })); setCnrResult(null);
    try {
      const res = await fetch(`${API_BASE}/api/cnr/${encodeURIComponent(cnrNumber.trim())}`);
      if (res.ok) { setCnrResult(await res.json()); toast("CNR data fetched", "success"); }
      else { const err = await res.json(); toast(err.detail || "Invalid CNR number", "error"); }
    } catch (e) { toast("CNR lookup failed", "error"); }
    setLoading(p => ({ ...p, cnr: false }));
  };

  const handleGenerateDoc = async () => {
    if (!docGen.party_a.trim() || !docGen.party_b.trim() || !docGen.details.trim()) { toast("All document fields are required", "error"); return; }
    setLoading(p => ({ ...p, doc: true })); setDocResult(null);
    try {
      const res = await fetch(`${API_BASE}/api/generate_doc`, { method: "POST", headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` }, body: JSON.stringify(docGen) });
      if (res.ok) { setDocResult(await res.json()); toast("Document generated", "success"); }
      else { const err = await res.json(); toast(err.detail || "Document generation failed", "error"); }
    } catch (e) { toast("Error generating document", "error"); }
    setLoading(p => ({ ...p, doc: false }));
  };

  const formatDate = (d) => { if (!d) return "—"; try { return new Date(d).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" }); } catch { return String(d); } };
  const formatDateTime = (d, tm) => { if (!d) return "—"; const ds = formatDate(d); return tm ? `${ds} at ${tm}` : ds; };
  const getStatusColor = (status) => { const s = (status || "").toLowerCase(); if (s.includes("active") || s.includes("open")) return t.green; if (s.includes("pending") || s.includes("wait")) return t.amber; if (s.includes("disposed") || s.includes("closed") || s.includes("resolved")) return t.blue; if (s.includes("overdue") || s.includes("urgent")) return t.red; return t.sub; };
  const getEventTypeIcon = (type) => { const map = { hearing: ICONS.calendar, deadline: ICONS.clock, meeting: ICONS.users, reminder: ICONS.bell }; return map[type] || ICONS.calendar; };
  const pendingTasks = tasks.filter(t => !t.is_completed);
  const upcomingHearings = hearings.filter(h => new Date(h.hearing_date) >= new Date()).sort((a, b) => new Date(a.hearing_date) - new Date(b.hearing_date));
  const totalRevenue = invoices.reduce((sum, i) => sum + (i.amount || 0), 0);
  const pendingRevenue = invoices.filter(i => i.status === "Pending").reduce((sum, i) => sum + (i.amount || 0), 0);

  const SectionHeader = ({ icon, title, count, action }) => (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16, paddingBottom: 12, borderBottom: `1px solid ${t.border}` }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <div style={{ width: 32, height: 32, borderRadius: 8, background: `${t.blue}15`, display: "flex", alignItems: "center", justifyContent: "center" }}>
          <Ic d={icon} size={16} color={t.blue} />
        </div>
        <h2 style={{ fontSize: 18, fontWeight: 800, margin: 0 }}>{title}</h2>
        {count !== undefined && <Tag label={String(count)} variant="info" t={t} style={{ fontSize: 11, padding: "2px 8px" }} />}
      </div>
      {action}
    </div>
  );

  // ═══════════════════════════════════════════════════════════════════════════════
  // RENDER: AUTH SCREEN
  // ═══════════════════════════════════════════════════════════════════════════════

  if (!token || !user) {
    return (
      <div style={{ maxWidth: 420, margin: "80px auto", padding: "0 20px" }}>
        <Card t={t}>
          <div style={{ textAlign: "center", marginBottom: 28 }}>
            <div style={{ width: 56, height: 56, background: `${t.blue}18`, borderRadius: 14, display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 18px" }}>
              <Ic d={ICONS.grid} size={28} color={t.blue} />
            </div>
            <h2 style={{ fontSize: 24, fontWeight: 800, margin: "0 0 6px" }}>{isRegister ? "Create Account" : "Lawyer Login"}</h2>
            <p style={{ fontSize: 14, color: t.sub, margin: 0 }}>{isRegister ? "Join Nyaya-Setu Legal Platform" : "Access your firm dashboard"}</p>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <Input value={email} onChange={e => setEmail(e.target.value)} placeholder="Email address" type="email" t={t} />
            <Input value={password} onChange={e => setPassword(e.target.value)} placeholder="Password" type="password" t={t} />
            {isRegister && (
              <>
                <Input value={fullName} onChange={e => setFullName(e.target.value)} placeholder="Full Name" t={t} />
                <Input value={phone} onChange={e => setPhone(e.target.value)} placeholder="Phone (Optional)" t={t} />
              </>
            )}
            <Btn onClick={handleAuth} loading={authLoading} t={t} style={{ width: "100%", justifyContent: "center", marginTop: 4 }}>
              {isRegister ? "Create Account" : "Sign In"}
            </Btn>
            <button onClick={() => { setIsRegister(!isRegister); setFullName(""); setPhone(""); }} style={{ background: "none", border: "none", color: t.blue, cursor: "pointer", fontSize: 13, marginTop: 8, textAlign: "center" }}>
              {isRegister ? "Already have an account? Sign in" : "Need an account? Register"}
            </button>
          </div>
        </Card>
      </div>
    );
  }

  // ═══════════════════════════════════════════════════════════════════════════════
  // RENDER: UNIFIED DASHBOARD (No internal tabs — uses top nav)
  // ═══════════════════════════════════════════════════════════════════════════════

  return (
    <div style={{ maxWidth: 1200, margin: "0 auto", padding: "24px 20px 60px" }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 28, flexWrap: "wrap", gap: 12 }}>
        <PageTitle icon="grid" title={`Welcome back, ${user.full_name || user.email}`} desc="Manage your cases, hearings, tasks, billing & calendar in one place." badge={user.role?.toUpperCase() || "LAWYER"} t={t} />
        <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
          <Tag label={`${cases.length} Cases`} variant="info" t={t} style={{ fontSize: 12 }} />
          <button onClick={handleLogout} style={{ background: t.surfaceUp, border: `1.5px solid ${t.border}`, borderRadius: 8, padding: "8px 16px", color: t.red, fontSize: 13, fontWeight: 600, cursor: "pointer", fontFamily: "inherit" }}>Logout</button>
        </div>
      </div>

      {/* ═══════════════════════════════════════════════════════════════════════════
         STATS ROW
         ═══════════════════════════════════════════════════════════════════════════ */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 16, marginBottom: 32 }}>
        <Card t={t} style={{ padding: "20px 24px" }}>
          <div style={{ fontSize: 12, color: t.sub, fontWeight: 600, marginBottom: 8 }}>ACTIVE CASES</div>
          <div style={{ fontSize: 36, fontWeight: 800, color: t.text }}>{cases.length}</div>
          <div style={{ fontSize: 12, color: t.green, marginTop: 4 }}>{cases.filter(c => (c.status || "").toLowerCase() === "active").length} active</div>
        </Card>
        <Card t={t} style={{ padding: "20px 24px" }}>
          <div style={{ fontSize: 12, color: t.sub, fontWeight: 600, marginBottom: 8 }}>UPCOMING HEARINGS</div>
          <div style={{ fontSize: 36, fontWeight: 800, color: t.text }}>{upcomingHearings.length}</div>
          <div style={{ fontSize: 12, color: t.amber, marginTop: 4 }}>Next: {upcomingHearings[0] ? formatDate(upcomingHearings[0].hearing_date) : "None"}</div>
        </Card>
        <Card t={t} style={{ padding: "20px 24px" }}>
          <div style={{ fontSize: 12, color: t.sub, fontWeight: 600, marginBottom: 8 }}>PENDING TASKS</div>
          <div style={{ fontSize: 36, fontWeight: 800, color: t.text }}>{pendingTasks.length}</div>
          <div style={{ fontSize: 12, color: pendingTasks.length > 0 ? t.red : t.green, marginTop: 4 }}>{pendingTasks.length > 0 ? `${pendingTasks.length} need attention` : "All caught up"}</div>
        </Card>
        <Card t={t} style={{ padding: "20px 24px" }}>
          <div style={{ fontSize: 12, color: t.sub, fontWeight: 600, marginBottom: 8 }}>TOTAL BILLED</div>
          <div style={{ fontSize: 36, fontWeight: 800, color: t.text }}>₹{totalRevenue.toLocaleString("en-IN")}</div>
          <div style={{ fontSize: 12, color: t.blue, marginTop: 4 }}>₹{pendingRevenue.toLocaleString("en-IN")} pending</div>
        </Card>
        <Card t={t} style={{ padding: "20px 24px" }}>
          <div style={{ fontSize: 12, color: t.sub, fontWeight: 600, marginBottom: 8 }}>CALENDAR EVENTS</div>
          <div style={{ fontSize: 36, fontWeight: 800, color: t.text }}>{calendarEvents.length}</div>
          <div style={{ fontSize: 12, color: t.purple || t.blue, marginTop: 4 }}>{calendarStats?.upcoming_events || 0} upcoming</div>
        </Card>
      </div>

      {/* ═══════════════════════════════════════════════════════════════════════════
         CASES SECTION
         ═══════════════════════════════════════════════════════════════════════════ */}
      <Card t={t} style={{ padding: 24, marginBottom: 24 }}>
        <SectionHeader icon={ICONS.file} title="Cases" count={cases.length} action={
          <button onClick={() => setExpandedSection(expandedSection === "cases" ? null : "cases")} style={{ background: "none", border: "none", color: t.blue, cursor: "pointer", fontSize: 13, fontWeight: 600 }}>
            {expandedSection === "cases" ? "Collapse ↑" : "Expand ↓"}
          </button>
        } />

        {showCaseDetail && selectedCase ? (
          <div style={{ padding: 20, background: t.surfaceUp, borderRadius: 12, marginBottom: 16 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 16 }}>
              <div>
                <h3 style={{ fontSize: 20, fontWeight: 800, margin: "0 0 8px" }}>{selectedCase.title}</h3>
                <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
                  {selectedCase.cnr_number && <Tag label={`CNR: ${selectedCase.cnr_number}`} variant="info" t={t} />}
                  <Tag label={selectedCase.status || "Active"} variant="info" t={t} />
                  {selectedCase.court_name && <span style={{ fontSize: 13, color: t.sub }}>{selectedCase.court_name}</span>}
                </div>
              </div>
              <button onClick={() => setShowCaseDetail(false)} style={{ background: "none", border: "none", color: t.sub, cursor: "pointer", fontSize: 18 }}>×</button>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 16 }}>
              <div style={{ padding: 12, background: t.surfaceUp, borderRadius: 8, border: `1px solid ${t.border}` }}><div style={{ fontSize: 11, color: t.sub }}>CLIENT</div><div style={{ fontSize: 14, fontWeight: 600, marginTop: 4 }}>{selectedCase.client_name || "—"}</div></div>
              <div style={{ padding: 12, background: t.surfaceUp, borderRadius: 8, border: `1px solid ${t.border}` }}><div style={{ fontSize: 11, color: t.sub }}>CREATED</div><div style={{ fontSize: 14, fontWeight: 600, marginTop: 4 }}>{formatDate(selectedCase.created_at)}</div></div>
            </div>
            <div style={{ marginBottom: 12 }}>
              <h4 style={{ fontSize: 13, fontWeight: 700, margin: "0 0 8px" }}>Linked Tasks ({tasks.filter(t2 => t2.case_id === selectedCase.id).length})</h4>
              {tasks.filter(t2 => t2.case_id === selectedCase.id).length === 0 ? <div style={{ color: t.sub, fontSize: 12 }}>No tasks.</div> : <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>{tasks.filter(t2 => t2.case_id === selectedCase.id).map(t2 => <div key={t2.id} style={{ padding: "6px 10px", background: t.surfaceUp, borderRadius: 6, fontSize: 12, display: "flex", justifyContent: "space-between" }}><span>{t2.title}</span><span style={{ color: t.sub }}>{t2.is_completed ? "Done" : `Due ${formatDate(t2.due_date)}`}</span></div>)}</div>}
            </div>
            <div>
              <h4 style={{ fontSize: 13, fontWeight: 700, margin: "0 0 8px" }}>Linked Hearings ({hearings.filter(h => h.case_id === selectedCase.id).length})</h4>
              {hearings.filter(h => h.case_id === selectedCase.id).length === 0 ? <div style={{ color: t.sub, fontSize: 12 }}>No hearings.</div> : <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>{hearings.filter(h => h.case_id === selectedCase.id).map(h => <div key={h.id} style={{ padding: "6px 10px", background: t.surfaceUp, borderRadius: 6, fontSize: 12, display: "flex", justifyContent: "space-between" }}><span>{h.purpose}</span><span style={{ color: t.sub }}>{formatDate(h.hearing_date)}</span></div>)}</div>}
            </div>
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 10, marginBottom: 16 }}>
            {cases.length === 0 ? <div style={{ color: t.sub, fontSize: 13, textAlign: "center", padding: 30 }}>No cases yet. Add one below.</div> : cases.map(c => (
              <div key={c.id} style={{ padding: "12px 16px", background: t.surfaceUp, borderRadius: 8, border: `1px solid ${t.border}`, display: "flex", alignItems: "center", justifyContent: "space-between", cursor: "pointer" }} onClick={() => fetchCaseDetail(c.id)}>
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 700, fontSize: 14 }}>{c.title}</div>
                  <div style={{ fontSize: 11, color: t.sub, marginTop: 3, display: "flex", gap: 12, flexWrap: "wrap" }}>
                    {c.cnr_number && <span>CNR: {c.cnr_number}</span>}{c.court_name && <span>🏛 {c.court_name}</span>}{c.client_name && <span>👤 {c.client_name}</span>}
                    <span>📋 {tasks.filter(t2 => t2.case_id === c.id).length} tasks</span><span>📅 {hearings.filter(h => h.case_id === c.id).length} hearings</span>
                  </div>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <Tag label={c.status || "Active"} variant="info" t={t} style={{ background: `${getStatusColor(c.status)}22`, color: getStatusColor(c.status), border: `1px solid ${getStatusColor(c.status)}44`, fontSize: 10 }} />
                  <button onClick={e => { e.stopPropagation(); handleDeleteCase(c.id); }} disabled={loading.deleteCase === c.id} style={{ background: "none", border: "none", color: t.red, cursor: "pointer", fontSize: 16, opacity: loading.deleteCase === c.id ? 0.5 : 1 }} title="Delete">{loading.deleteCase === c.id ? <Spinner size={12} /> : "🗑"}</button>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Add Case Form */}
        {expandedSection === "cases" && (
          <div style={{ padding: 16, background: t.surfaceUp, borderRadius: 10, border: `1px solid ${t.border}` }}>
            <h4 style={{ fontSize: 14, fontWeight: 700, margin: "0 0 12px" }}>Add New Case</h4>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 12 }}>
              <Input value={newCase.title} onChange={e => setNewCase({ ...newCase, title: e.target.value })} placeholder="Case Title *" t={t} />
              <Input value={newCase.cnr_number} onChange={e => setNewCase({ ...newCase, cnr_number: e.target.value })} placeholder="CNR (Optional)" t={t} />
              <Input value={newCase.court_name} onChange={e => setNewCase({ ...newCase, court_name: e.target.value })} placeholder="Court Name" t={t} />
              <Input value={newCase.client_name} onChange={e => setNewCase({ ...newCase, client_name: e.target.value })} placeholder="Client Name" t={t} />
              <select value={newCase.status} onChange={e => setNewCase({ ...newCase, status: e.target.value })} style={{ background: t.surfaceUp, border: `1.5px solid ${t.border}`, borderRadius: 9, padding: "10px 16px", color: t.text, fontFamily: "inherit", fontSize: 14 }}>
                <option value="Active">Active</option><option value="Pending">Pending</option><option value="Disposed">Disposed</option><option value="Closed">Closed</option>
              </select>
              <Btn onClick={handleCreateCase} loading={loading.cases} t={t} style={{ width: "100%", justifyContent: "center" }}>Create Case</Btn>
            </div>
          </div>
        )}
      </Card>

      {/* ═══════════════════════════════════════════════════════════════════════════
         TASKS SECTION
         ═══════════════════════════════════════════════════════════════════════════ */}
      <Card t={t} style={{ padding: 24, marginBottom: 24 }}>
        <SectionHeader icon={ICONS.check} title="Tasks" count={tasks.length} action={
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <Tag label={`${pendingTasks.length} Pending`} variant="warning" t={t} style={{ fontSize: 11 }} />
            <button onClick={() => setExpandedSection(expandedSection === "tasks" ? null : "tasks")} style={{ background: "none", border: "none", color: t.blue, cursor: "pointer", fontSize: 13, fontWeight: 600 }}>{expandedSection === "tasks" ? "Collapse ↑" : "Expand ↓"}</button>
          </div>
        } />
        <div style={{ display: "flex", flexDirection: "column", gap: 10, marginBottom: 16 }}>
          {tasks.length === 0 ? <div style={{ color: t.sub, fontSize: 13, textAlign: "center", padding: 30 }}>No tasks yet. Add one below.</div> : tasks.map(task => {
            const caseObj = cases.find(c => c.id === task.case_id);
            const isOverdue = !task.is_completed && new Date(task.due_date) < new Date();
            return (
              <div key={task.id} style={{ padding: "12px 16px", background: t.surfaceUp, borderRadius: 8, border: `1px solid ${isOverdue ? t.red : t.border}`, borderLeft: `4px solid ${task.is_completed ? t.green : isOverdue ? t.red : t.amber}`, display: "flex", alignItems: "flex-start", gap: 12 }}>
                <div style={{ width: 18, height: 18, borderRadius: 4, border: `2px solid ${task.is_completed ? t.green : t.border}`, background: task.is_completed ? t.green : "transparent", flexShrink: 0, marginTop: 2 }} />
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 700, fontSize: 14, textDecoration: task.is_completed ? "line-through" : "none", color: task.is_completed ? t.sub : t.text }}>{task.title}</div>
                  {task.description && <div style={{ fontSize: 12, color: t.sub, marginTop: 3 }}>{task.description}</div>}
                  <div style={{ fontSize: 11, color: t.sub, marginTop: 5, display: "flex", gap: 12 }}>
                    <span style={{ color: isOverdue ? t.red : t.sub }}>📅 {formatDate(task.due_date)}{isOverdue && " · OVERDUE"}</span>{caseObj && <span>📁 {caseObj.title}</span>}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
        {expandedSection === "tasks" && (
          <div style={{ padding: 16, background: t.surfaceUp, borderRadius: 10, border: `1px solid ${t.border}` }}>
            <h4 style={{ fontSize: 14, fontWeight: 700, margin: "0 0 12px" }}>Add Task</h4>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 12 }}>
              <Input value={newTask.title} onChange={e => setNewTask({ ...newTask, title: e.target.value })} placeholder="Task title *" t={t} />
              <Input value={newTask.description} onChange={e => setNewTask({ ...newTask, description: e.target.value })} placeholder="Description" t={t} />
              <input type="date" value={newTask.due_date} onChange={e => setNewTask({ ...newTask, due_date: e.target.value })} style={{ background: t.surfaceUp, border: `1.5px solid ${t.border}`, borderRadius: 9, padding: "10px 16px", color: t.text, fontFamily: "inherit", fontSize: 14 }} />
              <select value={newTask.case_id} onChange={e => setNewTask({ ...newTask, case_id: e.target.value })} style={{ background: t.surfaceUp, border: `1.5px solid ${t.border}`, borderRadius: 9, padding: "10px 16px", color: t.text, fontFamily: "inherit", fontSize: 14 }}>
                <option value="">Select Case (Optional)</option>{cases.map(c => <option key={c.id} value={c.id}>{c.title}</option>)}
              </select>
              <Btn onClick={handleCreateTask} loading={loading.tasks} t={t} style={{ width: "100%", justifyContent: "center" }}>Add Task</Btn>
            </div>
          </div>
        )}
      </Card>

      {/* ═══════════════════════════════════════════════════════════════════════════
         HEARINGS SECTION
         ═══════════════════════════════════════════════════════════════════════════ */}
      <Card t={t} style={{ padding: 24, marginBottom: 24 }}>
        <SectionHeader icon={ICONS.calendar} title="Hearings" count={hearings.length} action={
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <Tag label={`${upcomingHearings.length} Upcoming`} variant="success" t={t} style={{ fontSize: 11 }} />
            <button onClick={() => setExpandedSection(expandedSection === "hearings" ? null : "hearings")} style={{ background: "none", border: "none", color: t.blue, cursor: "pointer", fontSize: 13, fontWeight: 600 }}>{expandedSection === "hearings" ? "Collapse ↑" : "Expand ↓"}</button>
          </div>
        } />
        <div style={{ display: "flex", flexDirection: "column", gap: 10, marginBottom: 16 }}>
          {hearings.length === 0 ? <div style={{ color: t.sub, fontSize: 13, textAlign: "center", padding: 30 }}>No hearings scheduled. Add one below.</div> : hearings.sort((a, b) => new Date(a.hearing_date) - new Date(b.hearing_date)).map(h => {
            const caseObj = cases.find(c => c.id === h.case_id);
            const isPast = new Date(h.hearing_date) < new Date();
            return (
              <div key={h.id} style={{ padding: "12px 16px", background: t.surfaceUp, borderRadius: 8, border: `1px solid ${t.border}`, borderLeft: `4px solid ${isPast ? t.sub : t.blue}`, opacity: isPast ? 0.6 : 1, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <div style={{ fontWeight: 700, fontSize: 14 }}>{h.purpose}</div>
                  <div style={{ fontSize: 11, color: t.sub, marginTop: 3, display: "flex", gap: 12 }}>
                    <span>📅 {formatDate(h.hearing_date)}</span>{caseObj && <span>📁 {caseObj.title}</span>}{h.notes && <span>📝 {h.notes}</span>}
                  </div>
                </div>
                {isPast && <Tag label="Past" variant="info" t={t} style={{ fontSize: 10, padding: "2px 6px" }} />}
              </div>
            );
          })}
        </div>
        {expandedSection === "hearings" && (
          <div style={{ padding: 16, background: t.surfaceUp, borderRadius: 10, border: `1px solid ${t.border}` }}>
            <h4 style={{ fontSize: 14, fontWeight: 700, margin: "0 0 12px" }}>Schedule Hearing</h4>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 12 }}>
              <Input value={newHearing.purpose} onChange={e => setNewHearing({ ...newHearing, purpose: e.target.value })} placeholder="Purpose *" t={t} />
              <input type="date" value={newHearing.hearing_date} onChange={e => setNewHearing({ ...newHearing, hearing_date: e.target.value })} style={{ background: t.surfaceUp, border: `1.5px solid ${t.border}`, borderRadius: 9, padding: "10px 16px", color: t.text, fontFamily: "inherit", fontSize: 14 }} />
              <select value={newHearing.case_id} onChange={e => setNewHearing({ ...newHearing, case_id: e.target.value })} style={{ background: t.surfaceUp, border: `1.5px solid ${t.border}`, borderRadius: 9, padding: "10px 16px", color: t.text, fontFamily: "inherit", fontSize: 14 }}>
                <option value="">Select Case *</option>{cases.map(c => <option key={c.id} value={c.id}>{c.title}</option>)}
              </select>
              <Input value={newHearing.notes} onChange={e => setNewHearing({ ...newHearing, notes: e.target.value })} placeholder="Notes" t={t} />
              <Btn onClick={handleCreateHearing} loading={loading.hearings} t={t} style={{ width: "100%", justifyContent: "center" }}>Schedule Hearing</Btn>
            </div>
          </div>
        )}
      </Card>

      {/* ═══════════════════════════════════════════════════════════════════════════
         INVOICES SECTION
         ═══════════════════════════════════════════════════════════════════════════ */}
      <Card t={t} style={{ padding: 24, marginBottom: 24 }}>
        <SectionHeader icon={ICONS.dollar} title="Invoices & Billing" count={invoices.length} action={
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <Tag label={`₹${pendingRevenue.toLocaleString("en-IN")} Pending`} variant="warning" t={t} style={{ fontSize: 11 }} />
            <button onClick={() => setExpandedSection(expandedSection === "invoices" ? null : "invoices")} style={{ background: "none", border: "none", color: t.blue, cursor: "pointer", fontSize: 13, fontWeight: 600 }}>{expandedSection === "invoices" ? "Collapse ↑" : "Expand ↓"}</button>
          </div>
        } />
        <div style={{ display: "flex", flexDirection: "column", gap: 10, marginBottom: 16 }}>
          {invoices.length === 0 ? <div style={{ color: t.sub, fontSize: 13, textAlign: "center", padding: 30 }}>No invoices yet. Add one below.</div> : invoices.map(inv => (
            <div key={inv.id} style={{ padding: "12px 16px", background: t.surfaceUp, borderRadius: 8, border: `1px solid ${t.border}`, borderLeft: `4px solid ${inv.status === "Paid" ? t.green : inv.status === "Overdue" ? t.red : t.amber}`, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div>
                <div style={{ fontWeight: 700, fontSize: 14 }}>{inv.client_name}</div>
                <div style={{ fontSize: 11, color: t.sub, marginTop: 3 }}>Due {formatDate(inv.due_date)} · Created {formatDate(inv.created_at)}</div>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <div style={{ fontSize: 18, fontWeight: 800, color: t.text }}>₹{inv.amount?.toLocaleString("en-IN") || "0"}</div>
                <Tag label={inv.status || "Pending"} variant={inv.status === "Paid" ? "success" : inv.status === "Overdue" ? "danger" : "warning"} t={t} style={{ fontSize: 10 }} />
              </div>
            </div>
          ))}
        </div>
        {expandedSection === "invoices" && (
          <div style={{ padding: 16, background: t.surfaceUp, borderRadius: 10, border: `1px solid ${t.border}` }}>
            <h4 style={{ fontSize: 14, fontWeight: 700, margin: "0 0 12px" }}>New Invoice</h4>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 12 }}>
              <Input value={newInvoice.client_name} onChange={e => setNewInvoice({ ...newInvoice, client_name: e.target.value })} placeholder="Client Name *" t={t} />
              <Input value={newInvoice.amount} onChange={e => setNewInvoice({ ...newInvoice, amount: e.target.value })} placeholder="Amount (₹) *" type="number" t={t} />
              <input type="date" value={newInvoice.due_date} onChange={e => setNewInvoice({ ...newInvoice, due_date: e.target.value })} style={{ background: t.surfaceUp, border: `1.5px solid ${t.border}`, borderRadius: 9, padding: "10px 16px", color: t.text, fontFamily: "inherit", fontSize: 14 }} />
              <Btn onClick={handleCreateInvoice} loading={loading.invoices} t={t} style={{ width: "100%", justifyContent: "center" }}>Create Invoice</Btn>
            </div>
          </div>
        )}
      </Card>

      {/* ═══════════════════════════════════════════════════════════════════════════
         CALENDAR EVENTS SECTION
         ═══════════════════════════════════════════════════════════════════════════ */}
      <Card t={t} style={{ padding: 24, marginBottom: 24 }}>
        <SectionHeader icon={ICONS.calendar} title="Calendar Events" count={calendarEvents.length} action={
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            {calendarStats && <Tag label={`${calendarStats.upcoming_events} Upcoming`} variant="success" t={t} style={{ fontSize: 11 }} />}
            <button onClick={() => setExpandedSection(expandedSection === "calendar" ? null : "calendar")} style={{ background: "none", border: "none", color: t.blue, cursor: "pointer", fontSize: 13, fontWeight: 600 }}>{expandedSection === "calendar" ? "Collapse ↑" : "Expand ↓"}</button>
          </div>
        } />
        {calendarStats && (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(120px, 1fr))", gap: 10, marginBottom: 16 }}>
            <div style={{ textAlign: "center", padding: 12, background: t.surfaceUp, borderRadius: 8 }}><div style={{ fontSize: 22, fontWeight: 800, color: t.blue }}>{calendarStats.total_events}</div><div style={{ fontSize: 11, color: t.sub }}>Total</div></div>
            <div style={{ textAlign: "center", padding: 12, background: t.surfaceUp, borderRadius: 8 }}><div style={{ fontSize: 22, fontWeight: 800, color: t.green }}>{calendarStats.upcoming_events}</div><div style={{ fontSize: 11, color: t.sub }}>Upcoming</div></div>
            <div style={{ textAlign: "center", padding: 12, background: t.surfaceUp, borderRadius: 8 }}><div style={{ fontSize: 22, fontWeight: 800, color: t.amber }}>{calendarStats.this_week}</div><div style={{ fontSize: 11, color: t.sub }}>This Week</div></div>
            {calendarStats.by_type && Object.entries(calendarStats.by_type).map(([type, count]) => <div key={type} style={{ textAlign: "center", padding: 12, background: t.surfaceUp, borderRadius: 8 }}><div style={{ fontSize: 22, fontWeight: 800, color: t.purple || t.blue }}>{count}</div><div style={{ fontSize: 11, color: t.sub, textTransform: "capitalize" }}>{type}s</div></div>)}
          </div>
        )}
        <div style={{ display: "flex", flexDirection: "column", gap: 10, marginBottom: 16 }}>
          {calendarEvents.length === 0 ? <div style={{ color: t.sub, fontSize: 13, textAlign: "center", padding: 30 }}>No calendar events. Add one below.</div> : calendarEvents.map(evt => {
            const caseObj = cases.find(c => c.id === evt.matter_id);
            return (
              <div key={evt.id} style={{ padding: "12px 16px", background: t.surfaceUp, borderRadius: 8, border: `1px solid ${t.border}`, display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                <div style={{ display: "flex", gap: 12, alignItems: "flex-start" }}>
                  <div style={{ width: 36, height: 36, borderRadius: 8, background: `${t.blue}15`, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                    <Ic d={getEventTypeIcon(evt.event_type)} size={18} color={t.blue} />
                  </div>
                  <div>
                    <div style={{ fontWeight: 700, fontSize: 14 }}>{evt.title}</div>
                    <div style={{ fontSize: 11, color: t.sub, marginTop: 3, display: "flex", gap: 10, flexWrap: "wrap" }}>
                      <span>📅 {formatDateTime(evt.event_date, evt.event_time)}</span><span style={{ textTransform: "capitalize" }}>🏷 {evt.event_type}</span>{evt.court && <span>🏛 {evt.court}</span>}{caseObj && <span>📁 {caseObj.title}</span>}
                    </div>
                    {evt.description && <div style={{ fontSize: 11, color: t.sub, marginTop: 4, fontStyle: "italic" }}>{evt.description}</div>}
                  </div>
                </div>
                <button onClick={() => handleDeleteCalendarEvent(evt.id)} style={{ background: "none", border: "none", color: t.red, cursor: "pointer", fontSize: 14, padding: "2px" }} title="Delete">🗑</button>
              </div>
            );
          })}
        </div>
        {expandedSection === "calendar" && (
          <div style={{ padding: 16, background: t.surfaceUp, borderRadius: 10, border: `1px solid ${t.border}` }}>
            <h4 style={{ fontSize: 14, fontWeight: 700, margin: "0 0 12px" }}>Add Calendar Event</h4>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 12 }}>
              <Input value={newCalendarEvent.title} onChange={e => setNewCalendarEvent({ ...newCalendarEvent, title: e.target.value })} placeholder="Event Title *" t={t} />
              <select value={newCalendarEvent.event_type} onChange={e => setNewCalendarEvent({ ...newCalendarEvent, event_type: e.target.value })} style={{ background: t.surfaceUp, border: `1.5px solid ${t.border}`, borderRadius: 9, padding: "10px 16px", color: t.text, fontFamily: "inherit", fontSize: 14 }}>
                <option value="hearing">Hearing</option><option value="deadline">Deadline</option><option value="meeting">Meeting</option><option value="reminder">Reminder</option>
              </select>
              <input type="date" value={newCalendarEvent.event_date} onChange={e => setNewCalendarEvent({ ...newCalendarEvent, event_date: e.target.value })} style={{ background: t.surfaceUp, border: `1.5px solid ${t.border}`, borderRadius: 9, padding: "10px 16px", color: t.text, fontFamily: "inherit", fontSize: 14 }} />
              <input type="time" value={newCalendarEvent.event_time} onChange={e => setNewCalendarEvent({ ...newCalendarEvent, event_time: e.target.value })} style={{ background: t.surfaceUp, border: `1.5px solid ${t.border}`, borderRadius: 9, padding: "10px 16px", color: t.text, fontFamily: "inherit", fontSize: 14 }} />
              <Input value={newCalendarEvent.court} onChange={e => setNewCalendarEvent({ ...newCalendarEvent, court: e.target.value })} placeholder="Court / Venue" t={t} />
              <select value={newCalendarEvent.matter_id} onChange={e => setNewCalendarEvent({ ...newCalendarEvent, matter_id: e.target.value })} style={{ background: t.surfaceUp, border: `1.5px solid ${t.border}`, borderRadius: 9, padding: "10px 16px", color: t.text, fontFamily: "inherit", fontSize: 14 }}>
                <option value="">Link to Case (Optional)</option>{cases.map(c => <option key={c.id} value={c.id}>{c.title}</option>)}
              </select>
              <Input value={newCalendarEvent.description} onChange={e => setNewCalendarEvent({ ...newCalendarEvent, description: e.target.value })} placeholder="Description" t={t} />
              <Btn onClick={handleCreateCalendarEvent} loading={loading.calendar} t={t} style={{ width: "100%", justifyContent: "center" }}>Add Event</Btn>
            </div>
          </div>
        )}
      </Card>

      {/* ═══════════════════════════════════════════════════════════════════════════
         TOOLS SECTION (CNR + Document Generator)
         ═══════════════════════════════════════════════════════════════════════════ */}
      <Card t={t} style={{ padding: 24, marginBottom: 24 }}>
        <SectionHeader icon={ICONS.tool} title="Quick Tools" count={undefined} action={
          <button onClick={() => setExpandedSection(expandedSection === "tools" ? null : "tools")} style={{ background: "none", border: "none", color: t.blue, cursor: "pointer", fontSize: 13, fontWeight: 600 }}>{expandedSection === "tools" ? "Collapse ↑" : "Expand ↓"}</button>
        } />

        {/* CNR Lookup */}
        <div style={{ marginBottom: 20 }}>
          <h4 style={{ fontSize: 14, fontWeight: 700, margin: "0 0 10px", display: "flex", alignItems: "center", gap: 8 }}>
            <Ic d={ICONS.search} size={16} color={t.blue} />CNR Number Lookup
          </h4>
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginBottom: 12 }}>
            <Input value={cnrNumber} onChange={e => setCnrNumber(e.target.value.toUpperCase())} placeholder="Enter 16-character CNR" style={{ flex: 1, minWidth: 220 }} t={t} />
            <Btn onClick={handleCnrLookup} loading={loading.cnr} t={t}>Lookup</Btn>
          </div>
          {cnrResult && (
            <div style={{ padding: 16, background: t.surfaceUp, borderRadius: 10, border: `1px solid ${t.border}` }}>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 12 }}>
                <div><div style={{ fontSize: 11, color: t.sub }}>CNR</div><div style={{ fontSize: 14, fontWeight: 700 }}>{cnrResult.cnr_number}</div></div>
                <div><div style={{ fontSize: 11, color: t.sub }}>TITLE</div><div style={{ fontSize: 14, fontWeight: 700 }}>{cnrResult.title}</div></div>
                <div><div style={{ fontSize: 11, color: t.sub }}>COURT</div><div style={{ fontSize: 14, fontWeight: 600 }}>{cnrResult.court_name}</div></div>
                <div><div style={{ fontSize: 11, color: t.sub }}>STATUS</div><Tag label={cnrResult.status} variant="info" t={t} style={{ background: `${getStatusColor(cnrResult.status)}22`, color: getStatusColor(cnrResult.status), fontSize: 11 }} /></div>
                <div><div style={{ fontSize: 11, color: t.sub }}>FILING</div><div style={{ fontSize: 14, fontWeight: 600 }}>{formatDate(cnrResult.filing_date)}</div></div>
                <div><div style={{ fontSize: 11, color: t.sub }}>NEXT HEARING</div><div style={{ fontSize: 14, fontWeight: 600, color: t.blue }}>{formatDate(cnrResult.next_hearing)}</div></div>
              </div>
            </div>
          )}
        </div>

        {/* Document Generator */}
        {expandedSection === "tools" && (
          <div style={{ padding: 16, background: t.surfaceUp, borderRadius: 10, border: `1px solid ${t.border}` }}>
            <h4 style={{ fontSize: 14, fontWeight: 700, margin: "0 0 12px", display: "flex", alignItems: "center", gap: 8 }}>
              <Ic d={ICONS.file} size={16} color={t.blue} />Document Generator
            </h4>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 12, marginBottom: 12 }}>
              <div>
                <label style={{ fontSize: 12, color: t.sub, fontWeight: 600, display: "block", marginBottom: 4 }}>Type</label>
                <select value={docGen.doc_type} onChange={e => setDocGen({ ...docGen, doc_type: e.target.value })} style={{ background: t.surfaceUp, border: `1.5px solid ${t.border}`, borderRadius: 9, padding: "10px 16px", color: t.text, fontFamily: "inherit", fontSize: 14, width: "100%" }}>
                  <option value="Rent Agreement">Rent Agreement</option><option value="Legal Notice">Legal Notice</option>
                </select>
              </div>
              <Input value={docGen.party_a} onChange={e => setDocGen({ ...docGen, party_a: e.target.value })} placeholder="Party A (Client) *" t={t} />
              <Input value={docGen.party_b} onChange={e => setDocGen({ ...docGen, party_b: e.target.value })} placeholder="Party B *" t={t} />
            </div>
            <div style={{ marginBottom: 12 }}>
              <label style={{ fontSize: 12, color: t.sub, fontWeight: 600, display: "block", marginBottom: 4 }}>Details</label>
              <textarea value={docGen.details} onChange={e => setDocGen({ ...docGen, details: e.target.value })} placeholder="Document details..." rows={3} style={{ background: t.surfaceUp, border: `1.5px solid ${t.border}`, borderRadius: 9, padding: "10px 16px", color: t.text, fontFamily: "inherit", fontSize: 14, width: "100%", resize: "vertical" }} />
            </div>
            <Btn onClick={handleGenerateDoc} loading={loading.doc} t={t}>Generate Document</Btn>
            {docResult && (
              <div style={{ marginTop: 16, padding: 16, background: t.surfaceUp, borderRadius: 10, border: `1px solid ${t.border}` }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
                  <h5 style={{ margin: 0, fontSize: 14 }}>{docResult.doc_type}</h5>
                  <button onClick={() => { navigator.clipboard.writeText(docResult.content); toast("Copied!", "success"); }} style={{ background: t.blue, color: "#fff", border: "none", borderRadius: 6, padding: "5px 12px", fontSize: 11, fontWeight: 600, cursor: "pointer" }}>Copy</button>
                </div>
                <pre style={{ whiteSpace: "pre-wrap", fontFamily: "inherit", fontSize: 12, lineHeight: 1.5, color: t.text, margin: 0, maxHeight: 300, overflow: "auto" }}>{docResult.content}</pre>
              </div>
            )}
          </div>
        )}
      </Card>
    </div>
  );
}