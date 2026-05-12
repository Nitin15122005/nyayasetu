import React, { useState, useEffect, useCallback } from "react";
import { PageTitle, Card, Btn, Input, Ic, ICONS, Tag } from "../components/UI";

const API_BASE = "http://localhost:8001/api";
const getToken = () => localStorage.getItem("token") || "dev-token";

const api = {
  async fetchWithAuth(url, options = {}) {
    const token = getToken();
    const res = await fetch(url, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...(token ? { "Authorization": `Bearer ${token}` } : {}),
        ...options.headers,
      },
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Request failed" }));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }
    return res.json();
  },
  async getCases() {
    return api.fetchWithAuth(`${API_BASE}/cases`);
  },
  async createCase(caseData) {
    return api.fetchWithAuth(`${API_BASE}/cases`, {
      method: "POST",
      body: JSON.stringify(caseData),
    });
  },
  async deleteCase(id) {
    return api.fetchWithAuth(`${API_BASE}/cases/${id}`, {
      method: "DELETE",
    });
  },
  async getCase(id) {
    return api.fetchWithAuth(`${API_BASE}/cases/${id}`);
  },
  async getTasks() {
    return api.fetchWithAuth(`${API_BASE}/tasks`);
  },
  async createTask(task) {
    return api.fetchWithAuth(`${API_BASE}/tasks`, {
      method: "POST",
      body: JSON.stringify(task),
    });
  },
  async getHearings() {
    return api.fetchWithAuth(`${API_BASE}/hearings`);
  },
  async getCNR(cnr) {
    return api.fetchWithAuth(`${API_BASE}/cnr/${cnr}`);
  },
};

export default function Matters({ t, toast }) {
  const [viewMode, setViewMode] = useState("list");
  const [search, setSearch] = useState("");
  const [cases, setCases] = useState([]);
  const [tasks, setTasks] = useState([]);
  const [hearings, setHearings] = useState([]);
  const [loading, setLoading] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [modalMode, setModalMode] = useState("case"); // "case" or "task"
  const [selectedCase, setSelectedCase] = useState(null);
  const [caseForm, setCaseForm] = useState({
    title: "",
    cnr_number: "",
    court_name: "",
    client_name: "",
    status: "Active"
  });
  const [taskForm, setTaskForm] = useState({
    title: "",
    description: "",
    due_date: "",
    case_id: ""
  });
  const [cnrInput, setCnrInput] = useState("");
  const [cnrResult, setCnrResult] = useState(null);

  const isDark = t.text === "#ffffff" || t.text === "#f8fafc";

  // ── Load Data ─────────────────────────────────────────────────────────────
  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [casesData, tasksData, hearingsData] = await Promise.all([
        api.getCases(),
        api.getTasks(),
        api.getHearings()
      ]);
      setCases(Array.isArray(casesData) ? casesData : []);
      setTasks(Array.isArray(tasksData) ? tasksData : []);
      setHearings(Array.isArray(hearingsData) ? hearingsData : []);
    } catch (err) {
      toast("Failed to load matters: " + err.message, "error");
      console.error("[Matters] Load error:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // ── Stats ─────────────────────────────────────────────────────────────────
  const stats = useCallback(() => {
    const total = cases.length;
    const pending = cases.filter(c => c.status === "Active" || c.status === "Pending Hearing").length;
    const disposed = cases.filter(c => c.status === "Disposed").length;
    return [
      { label: "Total Cases", value: total.toString(), bg: t.text, fg: t.bg },
      { label: "Pending", value: pending.toString(), bg: t.surface, fg: t.text },
      { label: "Disposed", value: disposed.toString(), bg: t.surface, fg: t.text },
    ];
  }, [cases, t]);

  const currentStats = stats();

  // ── Filtered Cases ────────────────────────────────────────────────────────
  const filteredCases = cases.filter(c => {
    const q = search.toLowerCase();
    return (
      (c.title && c.title.toLowerCase().includes(q)) ||
      (c.client_name && c.client_name.toLowerCase().includes(q)) ||
      (c.court_name && c.court_name.toLowerCase().includes(q)) ||
      (c.cnr_number && c.cnr_number.toLowerCase().includes(q))
    );
  });

  // ── Case Helpers ──────────────────────────────────────────────────────────
  const getCaseTasks = (caseId) => tasks.filter(task => task.case_id === caseId);
  const getCaseHearings = (caseId) => hearings.filter(h => h.case_id === caseId);

  const getStatusColor = (status) => {
    switch (status?.toLowerCase()) {
      case "active": return { bg: isDark ? "rgba(34,197,94,0.15)" : "rgba(34,197,94,0.08)", color: "#22c55e" };
      case "pending hearing": return { bg: isDark ? "rgba(245,158,11,0.15)" : "rgba(245,158,11,0.08)", color: "#f59e0b" };
      case "disposed": return { bg: isDark ? "rgba(100,116,139,0.15)" : "rgba(100,116,139,0.08)", color: "#64748b" };
      case "reserved for orders": return { bg: isDark ? "rgba(59,130,246,0.15)" : "rgba(59,130,246,0.08)", color: "#3b82f6" };
      default: return { bg: isDark ? "rgba(234,88,12,0.15)" : "rgba(234,88,12,0.08)", color: "#ea580c" };
    }
  };

  // ── CRUD ──────────────────────────────────────────────────────────────────
  const openCaseModal = () => {
    setModalMode("case");
    setCaseForm({ title: "", cnr_number: "", court_name: "", client_name: "", status: "Active" });
    setCnrResult(null);
    setShowModal(true);
  };

  const openTaskModal = (caseId = "") => {
    setModalMode("task");
    setTaskForm({ title: "", description: "", due_date: "", case_id: caseId.toString() });
    setShowModal(true);
  };

  const saveCase = async () => {
    if (!caseForm.title.trim()) {
      toast("Case title is required", "error");
      return;
    }
    try {
      const payload = {
        ...caseForm,
        cnr_number: caseForm.cnr_number && caseForm.cnr_number.trim() ? caseForm.cnr_number.trim() : null
      };
      await api.createCase(payload);
      toast("Case created successfully", "success");
      await loadData();
      setShowModal(false);
    } catch (err) {
      toast(err.message, "error");
    }
  };

  const deleteCase = async (caseId, e) => {
    e.stopPropagation();
    if (!window.confirm("Are you sure you want to delete this matter? This will also delete all associated tasks and hearings.")) {
      return;
    }
    try {
      await api.deleteCase(caseId);
      toast("Matter deleted successfully", "success");
      if (selectedCase?.id === caseId) setSelectedCase(null);
      await loadData();
    } catch (err) {
      toast(err.message, "error");
    }
  };

  const saveTask = async () => {
    if (!taskForm.title.trim()) {
      toast("Task title is required", "error");
      return;
    }
    try {
      const payload = {
        ...taskForm,
        case_id: taskForm.case_id ? parseInt(taskForm.case_id) : null,
        due_date: taskForm.due_date ? new Date(taskForm.due_date).toISOString() : null
      };
      await api.createTask(payload);
      toast("Task created successfully", "success");
      await loadData();
      setShowModal(false);
    } catch (err) {
      toast(err.message, "error");
    }
  };

  const lookupCNR = async () => {
    if (!cnrInput.trim() || cnrInput.length < 16) {
      toast("CNR number must be at least 16 characters", "error");
      return;
    }
    try {
      const data = await api.getCNR(cnrInput.trim());
      setCnrResult(data);
      setCaseForm(prev => ({
        ...prev,
        title: data.title || prev.title,
        court_name: data.court_name || prev.court_name,
        status: data.status || "Active"
      }));
      toast("CNR data fetched", "success");
    } catch (err) {
      toast(err.message, "error");
    }
  };

  const selectCase = (c) => {
    setSelectedCase(selectedCase?.id === c.id ? null : c);
  };

  // ── Render Case Card ─────────────────────────────────────────────────────
  const renderCaseCard = (c) => {
    const statusColors = getStatusColor(c.status);
    const caseTasks = getCaseTasks(c.id);
    const caseHearings = getCaseHearings(c.id);
    const isSelected = selectedCase?.id === c.id;

    return (
      <div key={c.id} style={{
        background: t.surface,
        border: `1px solid ${isSelected ? t.blue || "#3b82f6" : t.border}`,
        borderRadius: 12,
        padding: "20px",
        cursor: "pointer",
        transition: "all 0.15s",
        boxShadow: isSelected ? (isDark ? "0 0 0 1px " + (t.blue || "#3b82f6") : "0 0 0 1px " + (t.blue || "#3b82f6")) : "none"
      }} onClick={() => selectCase(c)}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 12 }}>
          <div style={{ flex: 1, minWidth: 0 }}>
            <h3 style={{ fontSize: 16, fontWeight: 700, color: t.text, margin: "0 0 6px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              {c.title}
            </h3>
            <div style={{ fontSize: 12, color: t.sub, display: "flex", gap: 12, flexWrap: "wrap", alignItems: "center" }}>
              {c.cnr_number && <span>CNR: {c.cnr_number}</span>}
              {c.court_name && <span>📍 {c.court_name}</span>}
              <span style={{ padding: "3px 10px", borderRadius: 6, fontSize: 11, fontWeight: 700, background: statusColors.bg, color: statusColors.color, textTransform: "uppercase" }}>
                {c.status || "Active"}
              </span>
            </div>
          </div>
          <div style={{ display: "flex", gap: 6, flexShrink: 0 }}>
            <button
              onClick={(e) => { e.stopPropagation(); openTaskModal(c.id); }}
              style={{
                background: "transparent", border: `1px solid ${t.border}`, borderRadius: 6,
                padding: "6px 12px", fontSize: 12, fontWeight: 600, color: t.sub,
                cursor: "pointer"
              }}
            >
              + Task
            </button>
            <button
              onClick={(e) => deleteCase(c.id, e)}
              style={{
                background: "transparent", border: `1px solid ${t.border}`, borderRadius: 6,
                padding: "6px 10px", fontSize: 12, fontWeight: 600, color: "#ef4444",
                cursor: "pointer"
              }}
              title="Delete matter"
            >
              🗑
            </button>
          </div>
        </div>

        {c.client_name && (
          <div style={{ fontSize: 13, color: t.sub, marginBottom: 12 }}>
            Client: <span style={{ color: t.text, fontWeight: 600 }}>{c.client_name}</span>
          </div>
        )}

        {/* Case Details Expanded */}
        {isSelected && (
          <div style={{ marginTop: 16, paddingTop: 16, borderTop: `1px solid ${t.border}` }}>
            {/* Tasks */}
            <div style={{ marginBottom: 16 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
                <h4 style={{ fontSize: 13, fontWeight: 700, color: t.text, margin: 0, textTransform: "uppercase", letterSpacing: "0.05em" }}>Tasks</h4>
                <button onClick={() => openTaskModal(c.id)} style={{ background: "none", border: "none", color: t.blue || "#3b82f6", fontSize: 12, fontWeight: 600, cursor: "pointer" }}>+ Add</button>
              </div>
              {caseTasks.length === 0 ? (
                <div style={{ fontSize: 12, color: t.sub, padding: "8px 0" }}>No tasks for this case</div>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  {caseTasks.map(task => (
                    <div key={task.id} style={{ display: "flex", alignItems: "center", gap: 10, padding: "10px 12px", borderRadius: 8, background: isDark ? "rgba(255,255,255,0.02)" : "rgba(0,0,0,0.02)", border: `1px solid ${t.border}` }}>
                      <div style={{ width: 18, height: 18, borderRadius: 4, border: `2px solid ${task.is_completed ? "#22c55e" : t.border}`, background: task.is_completed ? "#22c55e" : "transparent", display: "flex", alignItems: "center", justifyContent: "center" }}>
                        {task.is_completed && <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="3"><polyline points="20 6 9 17 4 12" /></svg>}
                      </div>
                      <div style={{ flex: 1 }}>
                        <div style={{ fontSize: 13, fontWeight: 600, color: t.text, textDecoration: task.is_completed ? "line-through" : "none" }}>{task.title}</div>
                        {task.due_date && <div style={{ fontSize: 11, color: t.sub }}>Due: {new Date(task.due_date).toLocaleDateString()}</div>}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Hearings */}
            <div>
              <h4 style={{ fontSize: 13, fontWeight: 700, color: t.text, margin: "0 0 10px", textTransform: "uppercase", letterSpacing: "0.05em" }}>Hearings</h4>
              {caseHearings.length === 0 ? (
                <div style={{ fontSize: 12, color: t.sub, padding: "8px 0" }}>No hearings scheduled</div>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  {caseHearings.map(h => (
                    <div key={h.id} style={{ padding: "10px 12px", borderRadius: 8, background: isDark ? "rgba(234,88,12,0.08)" : "rgba(234,88,12,0.04)", border: `1px solid ${isDark ? "rgba(234,88,12,0.2)" : "rgba(234,88,12,0.12)"}` }}>
                      <div style={{ fontSize: 13, fontWeight: 600, color: t.text }}>{h.purpose}</div>
                      <div style={{ fontSize: 11, color: t.sub }}>{h.hearing_date ? new Date(h.hearing_date).toLocaleString() : "TBD"}</div>
                      {h.notes && <div style={{ fontSize: 11, color: t.sub, marginTop: 4 }}>{h.notes}</div>}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    );
  };

  // ── Render Case Row (List View) ──────────────────────────────────────────
  const renderCaseRow = (c) => {
    const statusColors = getStatusColor(c.status);
    return (
      <div key={c.id} style={{
        display: "flex", alignItems: "center", gap: 16,
        padding: "14px 18px", borderRadius: 10,
        border: `1px solid ${t.border}`,
        background: t.surface,
        cursor: "pointer",
        transition: "all 0.15s"
      }} onClick={() => selectCase(c)}>
        <div style={{ width: 40, height: 40, borderRadius: 10, background: statusColors.bg, display: "flex", alignItems: "center", justifyContent: "center", color: statusColors.color, fontWeight: 800, fontSize: 14, flexShrink: 0 }}>
          {c.title?.charAt(0)?.toUpperCase() || "M"}
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 14, fontWeight: 700, color: t.text, marginBottom: 4, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            {c.title}
          </div>
          <div style={{ fontSize: 12, color: t.sub, display: "flex", gap: 12, flexWrap: "wrap" }}>
            {c.client_name && <span>👤 {c.client_name}</span>}
            {c.court_name && <span>📍 {c.court_name}</span>}
            {c.cnr_number && <span>🔢 {c.cnr_number}</span>}
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 12, flexShrink: 0 }}>
          <span style={{ padding: "3px 10px", borderRadius: 6, fontSize: 11, fontWeight: 700, background: statusColors.bg, color: statusColors.color, textTransform: "uppercase" }}>
            {c.status || "Active"}
          </span>
          <button
            onClick={(e) => { e.stopPropagation(); openTaskModal(c.id); }}
            style={{ background: "transparent", border: `1px solid ${t.border}`, borderRadius: 6, padding: "6px 12px", fontSize: 12, fontWeight: 600, color: t.sub, cursor: "pointer" }}
          >
            + Task
          </button>
          <button
            onClick={(e) => deleteCase(c.id, e)}
            style={{ background: "transparent", border: `1px solid ${t.border}`, borderRadius: 6, padding: "6px 10px", fontSize: 12, fontWeight: 600, color: "#ef4444", cursor: "pointer" }}
            title="Delete matter"
          >
            🗑
          </button>
        </div>
      </div>
    );
  };

  // ── Render Board View ────────────────────────────────────────────────────
  const renderBoardView = () => {
    const columns = [
      { status: "Active", label: "Active", color: "#22c55e" },
      { status: "Pending Hearing", label: "Pending", color: "#f59e0b" },
      { status: "Disposed", label: "Disposed", color: "#64748b" },
    ];

    return (
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16 }}>
        {columns.map(col => (
          <div key={col.status}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
              <div style={{ width: 8, height: 8, borderRadius: "50%", background: col.color }} />
              <span style={{ fontSize: 13, fontWeight: 700, color: t.text, textTransform: "uppercase", letterSpacing: "0.05em" }}>{col.label}</span>
              <span style={{ fontSize: 12, color: t.sub, marginLeft: "auto" }}>{filteredCases.filter(c => c.status === col.status).length}</span>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {filteredCases.filter(c => c.status === col.status).map(renderCaseCard)}
            </div>
          </div>
        ))}
      </div>
    );
  };

  return (
    <div style={{ maxWidth: 1100, margin: "40px auto", padding: "0 24px", minHeight: "calc(100vh - 60px - 40px)" }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 32, flexWrap: "wrap", gap: 16 }}>
        <div>
          <h1 style={{ fontSize: 24, fontWeight: 800, color: t.text, margin: "0 0 6px" }}>Matters</h1>
          <p style={{ fontSize: 14, color: t.sub, margin: 0 }}>Active litigations, filings, and advisory</p>
        </div>
        <div style={{ display: "flex", gap: 16, alignItems: "center", flexWrap: "wrap" }}>
          {/* View Toggles */}
          <div style={{ display: "flex", background: t.surface, border: `1px solid ${t.border}`, borderRadius: 8, padding: 4 }}>
            {["List", "Cards", "Board"].map(m => (
              <button
                key={m}
                onClick={() => setViewMode(m.toLowerCase())}
                style={{
                  background: viewMode === m.toLowerCase() ? (isDark ? "rgba(255,255,255,0.05)" : "rgba(0,0,0,0.04)") : "transparent",
                  color: viewMode === m.toLowerCase() ? t.text : t.sub,
                  border: "none", borderRadius: 6, padding: "6px 14px", fontSize: 13, fontWeight: 600,
                  cursor: "pointer", transition: "all 0.2s"
                }}
              >
                {m}
              </button>
            ))}
          </div>
          <Btn t={t} onClick={openCaseModal}>+ New Matter</Btn>
        </div>
      </div>

      {/* Search Bar */}
      <div style={{ marginBottom: 24 }}>
        <div style={{ position: "relative" }}>
          <div style={{ position: "absolute", left: 14, top: 12, opacity: 0.5 }}>
            <Ic d={ICONS.search} size={16} color={t.text} />
          </div>
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search matters by title, client, court, or CNR..."
            style={{
              width: "100%", padding: "12px 16px 12px 40px", borderRadius: 10,
              background: t.surface, border: `1px solid ${t.border}`,
              color: t.text, fontSize: 14, outline: "none",
              transition: "border-color 0.2s", fontFamily: "inherit"
            }}
          />
        </div>
      </div>

      {/* Stats row */}
      <div style={{ display: "flex", gap: 16, marginBottom: 32, flexWrap: "wrap" }}>
        {currentStats.map((s, i) => (
          <div key={i} style={{
            background: s.bg, color: s.fg,
            padding: "16px 20px", borderRadius: 12,
            border: `1px solid ${t.border}`,
            minWidth: 140, display: "flex", flexDirection: "column", gap: 4,
            flex: 1
          }}>
            <div style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.05em", opacity: 0.7 }}>{s.label}</div>
            <div style={{ fontSize: 24, fontWeight: 800 }}>{s.value}</div>
          </div>
        ))}
      </div>

      {/* Loading */}
      {loading && (
        <div style={{ textAlign: "center", padding: 40, color: t.sub }}>
          <span style={{ display: "inline-block", width: 20, height: 20, border: `2px solid ${t.border}`, borderTopColor: t.blue, borderRadius: "50%", animation: "spin 0.8s linear infinite", marginRight: 10, verticalAlign: "middle" }} />
          Loading matters...
        </div>
      )}

      {/* Content */}
      {!loading && filteredCases.length === 0 ? (
        <div style={{
          background: t.surface, border: `1px solid ${t.border}`, borderRadius: 16,
          padding: "80px 20px", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center"
        }}>
          <div style={{ width: 48, height: 48, borderRadius: 12, background: t.surfaceUp, display: "flex", alignItems: "center", justifyContent: "center", marginBottom: 16 }}>
            <Ic d={ICONS.file} size={24} color={t.sub} />
          </div>
          <h3 style={{ fontSize: 16, fontWeight: 700, margin: "0 0 6px", color: t.text }}>
            {search ? "No matching matters" : "No matters yet"}
          </h3>
          <p style={{ fontSize: 14, color: t.sub, margin: 0 }}>
            {search ? "Try a different search term." : "Create your first matter to get started."}
          </p>
          {!search && (
            <button onClick={openCaseModal} style={{ marginTop: 16, background: "#ea580c", color: "#fff", border: "none", borderRadius: 8, padding: "10px 20px", fontSize: 14, fontWeight: 700, cursor: "pointer" }}>
              + Create Matter
            </button>
          )}
        </div>
      ) : (
        <>
          {viewMode === "list" && (
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {filteredCases.map(renderCaseRow)}
            </div>
          )}
          {viewMode === "cards" && (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))", gap: 16 }}>
              {filteredCases.map(renderCaseCard)}
            </div>
          )}
          {viewMode === "board" && renderBoardView()}
        </>
      )}

      {/* Modal */}
      {showModal && (
        <div style={{ position: "fixed", top: 0, left: 0, right: 0, bottom: 0, background: "rgba(0,0,0,0.6)", zIndex: 2000, display: "flex", alignItems: "center", justifyContent: "center", padding: 24, backdropFilter: "blur(4px)" }} onClick={() => setShowModal(false)}>
          <div style={{ background: t.surface, borderRadius: 16, border: `1px solid ${t.border}`, width: "100%", maxWidth: 520, maxHeight: "90vh", overflow: "auto" }} onClick={e => e.stopPropagation()}>
            <div style={{ padding: "24px 24px 16px", borderBottom: `1px solid ${t.border}` }}>
              <h3 style={{ margin: 0, fontSize: 18, fontWeight: 700, color: t.text }}>
                {modalMode === "case" ? "New Matter" : "New Task"}
              </h3>
            </div>

            {modalMode === "case" ? (
              <div style={{ padding: "20px 24px", display: "flex", flexDirection: "column", gap: 16 }}>
                {/* CNR Lookup */}
                <div>
                  <label style={{ display: "block", fontSize: 12, fontWeight: 600, color: t.sub, marginBottom: 6, textTransform: "uppercase" }}>CNR Number (Optional)</label>
                  <div style={{ display: "flex", gap: 8 }}>
                    <input
                      type="text"
                      value={cnrInput}
                      onChange={e => setCnrInput(e.target.value)}
                      placeholder="e.g., MHPU010000012023"
                      style={{ flex: 1, padding: "10px 14px", borderRadius: 8, border: `1px solid ${t.border}`, background: t.bg, color: t.text, fontSize: 14 }}
                    />
                    <button onClick={lookupCNR} style={{ padding: "10px 16px", borderRadius: 8, border: `1px solid ${t.border}`, background: t.surface, color: t.text, fontSize: 13, fontWeight: 600, cursor: "pointer", whiteSpace: "nowrap" }}>
                      🔍 Lookup
                    </button>
                  </div>
                  {cnrResult && (
                    <div style={{ marginTop: 8, padding: "10px 14px", borderRadius: 8, background: isDark ? "rgba(34,197,94,0.1)" : "rgba(34,197,94,0.05)", border: `1px solid ${isDark ? "rgba(34,197,94,0.2)" : "rgba(34,197,94,0.15)"}`, fontSize: 12, color: t.sub }}>
                      <div style={{ color: t.text, fontWeight: 600 }}>{cnrResult.title}</div>
                      <div>{cnrResult.court_name} • {cnrResult.status}</div>
                    </div>
                  )}
                </div>

                <div>
                  <label style={{ display: "block", fontSize: 12, fontWeight: 600, color: t.sub, marginBottom: 6, textTransform: "uppercase" }}>Title *</label>
                  <input type="text" value={caseForm.title} onChange={e => setCaseForm({ ...caseForm, title: e.target.value })} placeholder="e.g., Singh vs. State of Maharashtra"
                    style={{ width: "100%", padding: "10px 14px", borderRadius: 8, border: `1px solid ${t.border}`, background: t.bg, color: t.text, fontSize: 14 }} />
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                  <div>
                    <label style={{ display: "block", fontSize: 12, fontWeight: 600, color: t.sub, marginBottom: 6, textTransform: "uppercase" }}>Court</label>
                    <input type="text" value={caseForm.court_name} onChange={e => setCaseForm({ ...caseForm, court_name: e.target.value })} placeholder="e.g., Bombay High Court"
                      style={{ width: "100%", padding: "10px 14px", borderRadius: 8, border: `1px solid ${t.border}`, background: t.bg, color: t.text, fontSize: 14 }} />
                  </div>
                  <div>
                    <label style={{ display: "block", fontSize: 12, fontWeight: 600, color: t.sub, marginBottom: 6, textTransform: "uppercase" }}>Client Name</label>
                    <input type="text" value={caseForm.client_name} onChange={e => setCaseForm({ ...caseForm, client_name: e.target.value })} placeholder="e.g., Rajesh Singh"
                      style={{ width: "100%", padding: "10px 14px", borderRadius: 8, border: `1px solid ${t.border}`, background: t.bg, color: t.text, fontSize: 14 }} />
                  </div>
                </div>

                <div>
                  <label style={{ display: "block", fontSize: 12, fontWeight: 600, color: t.sub, marginBottom: 6, textTransform: "uppercase" }}>Status</label>
                  <select value={caseForm.status} onChange={e => setCaseForm({ ...caseForm, status: e.target.value })}
                    style={{ width: "100%", padding: "10px 14px", borderRadius: 8, border: `1px solid ${t.border}`, background: t.bg, color: t.text, fontSize: 14, cursor: "pointer" }}>
                    <option value="Active">Active</option>
                    <option value="Pending Hearing">Pending Hearing</option>
                    <option value="Disposed">Disposed</option>
                    <option value="Reserved for Orders">Reserved for Orders</option>
                  </select>
                </div>
              </div>
            ) : (
              <div style={{ padding: "20px 24px", display: "flex", flexDirection: "column", gap: 16 }}>
                <div>
                  <label style={{ display: "block", fontSize: 12, fontWeight: 600, color: t.sub, marginBottom: 6, textTransform: "uppercase" }}>Task Title *</label>
                  <input type="text" value={taskForm.title} onChange={e => setTaskForm({ ...taskForm, title: e.target.value })} placeholder="e.g., Draft reply affidavit"
                    style={{ width: "100%", padding: "10px 14px", borderRadius: 8, border: `1px solid ${t.border}`, background: t.bg, color: t.text, fontSize: 14 }} />
                </div>
                <div>
                  <label style={{ display: "block", fontSize: 12, fontWeight: 600, color: t.sub, marginBottom: 6, textTransform: "uppercase" }}>Description</label>
                  <textarea value={taskForm.description} onChange={e => setTaskForm({ ...taskForm, description: e.target.value })} placeholder="Additional details..." rows={2}
                    style={{ width: "100%", padding: "10px 14px", borderRadius: 8, border: `1px solid ${t.border}`, background: t.bg, color: t.text, fontSize: 14, resize: "vertical" }} />
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                  <div>
                    <label style={{ display: "block", fontSize: 12, fontWeight: 600, color: t.sub, marginBottom: 6, textTransform: "uppercase" }}>Due Date</label>
                    <input type="date" value={taskForm.due_date} onChange={e => setTaskForm({ ...taskForm, due_date: e.target.value })}
                      style={{ width: "100%", padding: "10px 14px", borderRadius: 8, border: `1px solid ${t.border}`, background: t.bg, color: t.text, fontSize: 14 }} />
                  </div>
                  <div>
                    <label style={{ display: "block", fontSize: 12, fontWeight: 600, color: t.sub, marginBottom: 6, textTransform: "uppercase" }}>Linked Matter</label>
                    <select value={taskForm.case_id} onChange={e => setTaskForm({ ...taskForm, case_id: e.target.value })}
                      style={{ width: "100%", padding: "10px 14px", borderRadius: 8, border: `1px solid ${t.border}`, background: t.bg, color: t.text, fontSize: 14, cursor: "pointer" }}>
                      <option value="">None</option>
                      {cases.map(c => (
                        <option key={c.id} value={c.id}>{c.title}</option>
                      ))}
                    </select>
                  </div>
                </div>
              </div>
            )}

            <div style={{ padding: "16px 24px 24px", display: "flex", gap: 10, justifyContent: "flex-end", borderTop: `1px solid ${t.border}` }}>
              <button onClick={() => setShowModal(false)} style={{ padding: "10px 18px", borderRadius: 8, border: `1px solid ${t.border}`, background: "transparent", color: t.text, fontSize: 13, fontWeight: 600, cursor: "pointer" }}>Cancel</button>
              <button onClick={modalMode === "case" ? saveCase : saveTask} style={{ padding: "10px 18px", borderRadius: 8, border: "none", background: "#ea580c", color: "#fff", fontSize: 13, fontWeight: 700, cursor: "pointer" }}>
                {modalMode === "case" ? "Create Matter" : "Create Task"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}