import React, { useState, useMemo, useEffect, useCallback } from "react";
import { Btn, Card, Ic, ICONS } from "../components/UI";

// ── API Base ──────────────────────────────────────────────────────────────────
const API_BASE = "http://localhost:8001";

const getToken = () => localStorage.getItem("ns_token") || "";

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

  async getTasks(filters = {}) {
    const params = new URLSearchParams();
    if (filters.status && filters.status !== "all") params.append("status", filters.status);
    if (filters.priority && filters.priority !== "all") params.append("priority", filters.priority);
    if (filters.search) params.append("search", filters.search);
    if (filters.sort_by) params.append("sort_by", filters.sort_by);
    return api.fetchWithAuth(`${API_BASE}/tasks?${params}`);
  },
  async createTask(task) {
    return api.fetchWithAuth(`${API_BASE}/tasks`, {
      method: "POST",
      body: JSON.stringify(task),
    });
  },
  async updateTask(id, task) {
    return api.fetchWithAuth(`${API_BASE}/tasks/${id}`, {
      method: "PUT",
      body: JSON.stringify(task),
    });
  },
  async deleteTask(id) {
    return api.fetchWithAuth(`${API_BASE}/tasks/${id}`, { method: "DELETE" });
  },
  async getStats() {
    return api.fetchWithAuth(`${API_BASE}/tasks/stats/summary`);
  },
};

export default function Tasks({ t, toast }) {
  const [tab, setTab] = useState("Tasks");
  const [tasks, setTasks] = useState([]);
  const [stats, setStats] = useState({ total: 0, pending: 0, done: 0, high: 0, overdue: 0 });
  const [loading, setLoading] = useState(false);

  // Filters
  const [statusFilter, setStatusFilter] = useState("all");
  const [priorityFilter, setPriorityFilter] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [sortBy, setSortBy] = useState("due_date");

  // Modal
  const [showModal, setShowModal] = useState(false);
  const [modalMode, setModalMode] = useState("add");
  const [editingTask, setEditingTask] = useState(null);
  const [formData, setFormData] = useState({
    title: "", priority: "medium", due_date: "", matter: "", status: "pending", description: ""
  });

  const isDark = t.text === "#ffffff" || t.text === "#f8fafc";

  // ── Priority Config ─────────────────────────────────────────────────────────
  const priorityConfig = useMemo(() => ({
    high: { color: "#ef4444", bg: isDark ? "rgba(239,68,68,0.15)" : "rgba(239,68,68,0.08)", label: "High" },
    medium: { color: "#f59e0b", bg: isDark ? "rgba(245,158,11,0.15)" : "rgba(245,158,11,0.08)", label: "Medium" },
    low: { color: "#22c55e", bg: isDark ? "rgba(34,197,94,0.15)" : "rgba(34,197,94,0.08)", label: "Low" },
  }), [isDark]);

  // ── Load Data ─────────────────────────────────────────────────────────────
  const loadData = useCallback(async () => {
    console.log("[Tasks] Loading data with filters:", { statusFilter, priorityFilter, searchQuery, sortBy });
    setLoading(true);
    try {
      const [tasksData, statsData] = await Promise.all([
        api.getTasks({ status: statusFilter, priority: priorityFilter, search: searchQuery, sort_by: sortBy }),
        api.getStats()
      ]);
      console.log("[Tasks] Raw response:", tasksData);

      // Handle case where response might not be an array
      const tasksArray = Array.isArray(tasksData) ? tasksData : (tasksData.results || tasksData.tasks || []);
      console.log("[Tasks] Parsed array:", tasksArray.length, "items");

      const mapped = tasksArray.map(t => ({
        id: t.id,
        title: t.title,
        status: t.status,
        priority: t.priority,
        dueDate: t.due_date,
        matter: t.matter || "General",
        assignee: t.assignee || "You",
        description: t.description || "",
        createdAt: t.created_at
      }));
      console.log("[Tasks] Mapped tasks:", mapped);
      setTasks(mapped);
      setStats(statsData);
    } catch (err) {
      console.error("[Tasks] Load failed:", err);
      toast("Failed to load tasks: " + err.message, "error");
    } finally {
      setLoading(false);
    }
  }, [statusFilter, priorityFilter, searchQuery, sortBy]);

  // Load on mount and when filters change
  useEffect(() => {
    loadData();
  }, [loadData]);

  // ── Templates ───────────────────────────────────────────────────────────────
  const templates = useMemo(() => [
    { title: "Draft Legal Notice", priority: "high", matter: "General", description: "Draft and send legal notice to opposing party" },
    { title: "File FIR / Complaint", priority: "high", matter: "Criminal", description: "Prepare and file FIR or complaint document" },
    { title: "Evidence Collection", priority: "medium", matter: "General", description: "Gather and organize all case evidence" },
    { title: "Witness Preparation", priority: "medium", matter: "Trial", description: "Prepare witness statements and questions" },
    { title: "Contract Review", priority: "medium", matter: "Civil", description: "Review contract terms and flag risks" },
    { title: "Court Appearance", priority: "high", matter: "Trial", description: "Prepare for upcoming court hearing" },
    { title: "Client Consultation", priority: "low", matter: "General", description: "Initial consultation with new client" },
    { title: "Compliance Check", priority: "medium", matter: "Corporate", description: "Verify BNS/BNSS/BSA compliance" },
  ], []);

  // ── CRUD ────────────────────────────────────────────────────────────────────
  const openAddModal = () => {
    setModalMode("add");
    setEditingTask(null);
    setFormData({ title: "", priority: "medium", due_date: "", matter: "", status: "pending", description: "" });
    setShowModal(true);
  };

  const openEditModal = (task) => {
    setModalMode("edit");
    setEditingTask(task);
    setFormData({
      title: task.title,
      priority: task.priority,
      due_date: task.dueDate || "",
      matter: task.matter === "General" ? "" : task.matter,
      status: task.status,
      description: task.description || ""
    });
    setShowModal(true);
  };

  const saveTask = async () => {
    if (!formData.title.trim()) {
      toast("Task title is required", "error");
      return;
    }
    try {
      const payload = {
        title: formData.title,
        priority: formData.priority,
        due_date: formData.due_date || null,
        matter: formData.matter || null,
        status: formData.status,
        description: formData.description || null
      };
      if (modalMode === "add") {
        await api.createTask(payload);
        toast("Task created", "success");
      } else {
        await api.updateTask(editingTask.id, payload);
        toast("Task updated", "success");
      }
      await loadData();
      setShowModal(false);
    } catch (err) {
      toast(err.message, "error");
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm("Delete this task?")) return;
    try {
      await api.deleteTask(id);
      toast("Task deleted", "success");
      await loadData();
    } catch (err) {
      toast(err.message, "error");
    }
  };

  const toggleStatus = async (task) => {
    const newStatus = task.status === "done" ? "pending" : "done";
    try {
      await api.updateTask(task.id, { status: newStatus });
      toast(newStatus === "done" ? "Task marked done" : "Task reopened", "success");
      await loadData();
    } catch (err) {
      toast(err.message, "error");
    }
  };

  const useTemplate = async (template) => {
    const today = new Date();
    const due = new Date(today);
    due.setDate(due.getDate() + (template.priority === "high" ? 2 : template.priority === "medium" ? 5 : 7));
    try {
      await api.createTask({
        title: template.title,
        priority: template.priority,
        due_date: due.toISOString().split("T")[0],
        matter: template.matter,
        status: "pending",
        description: template.description
      });
      toast(`Task "${template.title}" created from template`, "success");
      await loadData();
    } catch (err) {
      toast(err.message, "error");
    }
  };

  // ── Format Date ─────────────────────────────────────────────────────────────
  const formatDate = (dateStr) => {
    if (!dateStr) return "No date";
    const d = new Date(dateStr);
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const target = new Date(d);
    target.setHours(0, 0, 0, 0);
    const diff = Math.ceil((target - today) / (1000 * 60 * 60 * 24));
    if (diff < 0) return `Overdue by ${Math.abs(diff)} day${Math.abs(diff) > 1 ? "s" : ""}`;
    if (diff === 0) return "Due today";
    if (diff === 1) return "Due tomorrow";
    return d.toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
  };

  const isOverdue = (task) => {
    if (task.status === "done" || !task.dueDate) return false;
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const due = new Date(task.dueDate);
    due.setHours(0, 0, 0, 0);
    return due < today;
  };

  // ── Render Task Row ───────────────────────────────────────────────────────
  const renderTaskRow = (task) => {
    const p = priorityConfig[task.priority];
    const overdue = isOverdue(task);
    return (
      <div key={task.id} style={{
        display: "flex", alignItems: "center", gap: 16,
        padding: "14px 18px", borderRadius: 10,
        border: `1px solid ${t.border}`,
        background: task.status === "done" ? (isDark ? "rgba(255,255,255,0.02)" : "rgba(0,0,0,0.01)") : t.surface,
        opacity: task.status === "done" ? 0.6 : 1,
        transition: "all 0.15s"
      }}>
        <button
          onClick={() => toggleStatus(task)}
          style={{
            width: 22, height: 22, borderRadius: 6,
            border: `2px solid ${task.status === "done" ? "#22c55e" : t.border}`,
            background: task.status === "done" ? "#22c55e" : "transparent",
            display: "flex", alignItems: "center", justifyContent: "center",
            cursor: "pointer", flexShrink: 0, transition: "all 0.15s"
          }}
        >
          {task.status === "done" && (
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>
          )}
        </button>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{
            fontSize: 14, fontWeight: 700, color: t.text,
            textDecoration: task.status === "done" ? "line-through" : "none",
            marginBottom: 4, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap"
          }}>{task.title}</div>
          <div style={{ fontSize: 12, color: t.sub, display: "flex", gap: 12, flexWrap: "wrap", alignItems: "center" }}>
            <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
              <Ic d={ICONS.doc} size={12} color={t.sub} /> {task.matter}
            </span>
            <span style={{
              padding: "2px 8px", borderRadius: 4, fontSize: 10, fontWeight: 700,
              background: p.bg, color: p.color, textTransform: "uppercase"
            }}>{p.label}</span>
            <span style={{ color: overdue ? "#ef4444" : t.sub, fontWeight: overdue ? 700 : 400 }}>
              📅 {formatDate(task.dueDate)}
            </span>
          </div>
        </div>
        <div style={{ display: "flex", gap: 6, flexShrink: 0 }}>
          <button onClick={() => openEditModal(task)} title="Edit" style={{
            width: 32, height: 32, borderRadius: 6, border: `1px solid ${t.border}`,
            background: "transparent", color: t.sub, cursor: "pointer",
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: 14, transition: "all 0.15s"
          }} onMouseEnter={e => { e.currentTarget.style.color = t.blue || "#3b82f6"; e.currentTarget.style.borderColor = (t.blue || "#3b82f6") + "60"; }}
            onMouseLeave={e => { e.currentTarget.style.color = t.sub; e.currentTarget.style.borderColor = t.border; }}>✏️</button>
          <button onClick={() => handleDelete(task.id)} title="Delete" style={{
            width: 32, height: 32, borderRadius: 6, border: `1px solid ${t.border}`,
            background: "transparent", color: "#ef4444", cursor: "pointer",
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: 14, transition: "all 0.15s"
          }} onMouseEnter={e => { e.currentTarget.style.background = "rgba(239,68,68,0.08)"; e.currentTarget.style.borderColor = "#ef444460"; }}
            onMouseLeave={e => { e.currentTarget.style.background = "transparent"; e.currentTarget.style.borderColor = t.border; }}>🗑️</button>
        </div>
      </div>
    );
  };

  // ── Render Templates ──────────────────────────────────────────────────────
  const renderTemplates = () => (
    <div>
      <div style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 18, fontWeight: 700, color: t.text, margin: "0 0 8px" }}>Task Templates</h2>
        <p style={{ fontSize: 14, color: t.sub, margin: 0 }}>Quick-start common legal workflows</p>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 16 }}>
        {templates.map((tmpl, idx) => {
          const p = priorityConfig[tmpl.priority];
          return (
            <div key={idx} onClick={() => useTemplate(tmpl)} style={{
              padding: "20px", borderRadius: 12, border: `1px solid ${t.border}`,
              background: t.surface, cursor: "pointer", transition: "all 0.15s"
            }} onMouseEnter={e => { e.currentTarget.style.borderColor = t.blue || "#3b82f6"; e.currentTarget.style.transform = "translateY(-2px)"; e.currentTarget.style.boxShadow = isDark ? "0 8px 24px rgba(0,0,0,0.3)" : "0 8px 24px rgba(0,0,0,0.08)"; }}
              onMouseLeave={e => { e.currentTarget.style.borderColor = t.border; e.currentTarget.style.transform = "translateY(0)"; e.currentTarget.style.boxShadow = "none"; }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 10 }}>
                <h3 style={{ fontSize: 15, fontWeight: 700, color: t.text, margin: 0, flex: 1 }}>{tmpl.title}</h3>
                <span style={{ padding: "2px 8px", borderRadius: 4, fontSize: 10, fontWeight: 700, background: p.bg, color: p.color, textTransform: "uppercase", flexShrink: 0 }}>{p.label}</span>
              </div>
              <p style={{ fontSize: 13, color: t.sub, margin: "0 0 12px", lineHeight: 1.5 }}>{tmpl.description}</p>
              <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: t.muted || t.sub }}>
                <Ic d={ICONS.doc} size={12} color={t.sub} /> {tmpl.matter}
              </div>
              <div style={{ marginTop: 12, paddingTop: 12, borderTop: `1px solid ${t.border}` }}>
                <span style={{ fontSize: 12, color: t.blue || "#3b82f6", fontWeight: 600 }}>+ Click to create task</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );

  // ── Render Tasks Tab ──────────────────────────────────────────────────────
  const renderTasks = () => (
    <>
      {/* Stats Bar */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12, marginBottom: 24 }}>
        {[
          { label: "Total", value: stats.total, color: t.text },
          { label: "Pending", value: stats.pending, color: "#f59e0b" },
          { label: "Done", value: stats.done, color: "#22c55e" },
          { label: "High Priority", value: stats.high, color: "#ef4444" },
        ].map(s => (
          <div key={s.label} style={{ padding: "16px 20px", borderRadius: 10, border: `1px solid ${t.border}`, background: t.surface, textAlign: "center" }}>
            <div style={{ fontSize: 24, fontWeight: 800, color: s.color, marginBottom: 4 }}>{s.value}</div>
            <div style={{ fontSize: 12, fontWeight: 600, color: t.sub, textTransform: "uppercase", letterSpacing: "0.05em" }}>{s.label}</div>
          </div>
        ))}
      </div>

      {/* Toolbar */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: 24, flexWrap: "wrap", gap: 16 }}>
        <div style={{ display: "flex", flexDirection: "column", gap: 12, flex: 1, minWidth: 280 }}>
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
            <div style={{ position: "relative", flex: 1, minWidth: 200 }}>
              <input type="text" placeholder="Search tasks..." value={searchQuery} onChange={e => setSearchQuery(e.target.value)}
                style={{ width: "100%", padding: "8px 14px 8px 36px", borderRadius: 8, border: `1px solid ${t.border}`, background: t.surface, color: t.text, fontSize: 14, fontFamily: "inherit", outline: "none" }}
              />
              <div style={{ position: "absolute", left: 12, top: "50%", transform: "translateY(-50%)", pointerEvents: "none" }}>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke={t.sub} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" /></svg>
              </div>
            </div>
            <div style={{ position: "relative" }}>
              <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}
                style={{ appearance: "none", background: t.surface, border: `1px solid ${t.border}`, borderRadius: 8, padding: "8px 36px 8px 16px", color: t.text, fontSize: 14, outline: "none", cursor: "pointer", fontFamily: "inherit", minWidth: 140 }}>
                <option value="all">All statuses</option>
                <option value="pending">Pending</option>
                <option value="done">Done</option>
              </select>
              <div style={{ position: "absolute", right: 12, top: "50%", transform: "translateY(-50%)", pointerEvents: "none", opacity: 0.5 }}>
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="6 9 12 15 18 9"></polyline></svg>
              </div>
            </div>
            <div style={{ position: "relative" }}>
              <select value={priorityFilter} onChange={e => setPriorityFilter(e.target.value)}
                style={{ appearance: "none", background: t.surface, border: `1px solid ${t.border}`, borderRadius: 8, padding: "8px 36px 8px 16px", color: t.text, fontSize: 14, outline: "none", cursor: "pointer", fontFamily: "inherit", minWidth: 140 }}>
                <option value="all">All priorities</option>
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
              </select>
              <div style={{ position: "absolute", right: 12, top: "50%", transform: "translateY(-50%)", pointerEvents: "none", opacity: 0.5 }}>
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="6 9 12 15 18 9"></polyline></svg>
              </div>
            </div>
            <div style={{ position: "relative" }}>
              <select value={sortBy} onChange={e => setSortBy(e.target.value)}
                style={{ appearance: "none", background: t.surface, border: `1px solid ${t.border}`, borderRadius: 8, padding: "8px 36px 8px 16px", color: t.text, fontSize: 14, outline: "none", cursor: "pointer", fontFamily: "inherit", minWidth: 120 }}>
                <option value="due_date">Due Date</option>
                <option value="priority">Priority</option>
                <option value="status">Status</option>
                <option value="created">Created</option>
              </select>
              <div style={{ position: "absolute", right: 12, top: "50%", transform: "translateY(-50%)", pointerEvents: "none", opacity: 0.5 }}>
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="6 9 12 15 18 9"></polyline></svg>
              </div>
            </div>
          </div>
          <div style={{ fontSize: 12, color: t.sub, display: "flex", gap: 12 }}>
            <span>{stats.pending} pending</span>
            <span>{stats.done} done</span>
            {stats.overdue > 0 && <span style={{ color: "#ef4444", fontWeight: 700 }}>{stats.overdue} overdue</span>}
          </div>
        </div>
        <Btn t={t} onClick={openAddModal}>+ Add Task</Btn>
      </div>

      {/* Loading */}
      {loading && (
        <div style={{ textAlign: "center", padding: 20, color: t.sub, fontSize: 14 }}>
          <span style={{ display: "inline-block", width: 16, height: 16, border: `2px solid ${t.border}`, borderTopColor: t.blue, borderRadius: "50%", animation: "spin 0.8s linear infinite", marginRight: 8, verticalAlign: "middle" }} />
          Loading tasks...
        </div>
      )}

      {/* Task List */}
      {!loading && tasks.length === 0 ? (
        <div style={{ padding: "80px 20px", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center" }}>
          <div style={{ width: 48, height: 48, borderRadius: 12, background: t.surfaceUp, border: `1px solid ${t.border}`, display: "flex", alignItems: "center", justifyContent: "center", marginBottom: 16 }}>
            <Ic d={ICONS.check} size={24} color={t.sub} />
          </div>
          <h3 style={{ fontSize: 16, fontWeight: 700, margin: "0 0 6px", color: t.text }}>{searchQuery ? "No matching tasks" : "No tasks found"}</h3>
          <p style={{ fontSize: 14, color: t.sub, margin: 0 }}>{searchQuery ? "Try a different search term." : "Create a task or use a template."}</p>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {tasks.map(renderTaskRow)}
        </div>
      )}
    </>
  );

  return (
    <div style={{ maxWidth: 1100, margin: "40px auto", padding: "0 24px", minHeight: "calc(100vh - 60px - 40px)" }}>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 24, fontWeight: 800, color: t.text, margin: "0 0 6px" }}>Tasks</h1>
        <p style={{ fontSize: 14, color: t.sub, margin: 0 }}>Manage tasks and workflows across all matters</p>
      </div>
      <div style={{ display: "flex", borderBottom: `1px solid ${t.border}`, marginBottom: 24, gap: 24 }}>
        {["Tasks", "Task Templates"].map(m => (
          <button key={m} onClick={() => setTab(m)} style={{
            background: "transparent", color: tab === m ? t.text : t.sub, border: "none",
            borderBottom: tab === m ? `2px solid ${t.text}` : "2px solid transparent",
            padding: "0 4px 12px", fontSize: 14, fontWeight: 600, cursor: "pointer",
            transition: "all 0.2s", fontFamily: "inherit"
          }}>{m}</button>
        ))}
      </div>
      {tab === "Tasks" ? renderTasks() : renderTemplates()}

      {/* Modal */}
      {showModal && (
        <div style={{ position: "fixed", top: 0, left: 0, right: 0, bottom: 0, background: "rgba(0,0,0,0.6)", zIndex: 2000, display: "flex", alignItems: "center", justifyContent: "center", padding: 24, backdropFilter: "blur(4px)" }} onClick={() => setShowModal(false)}>
          <div style={{ background: t.surface, borderRadius: 16, border: `1px solid ${t.border}`, width: "100%", maxWidth: 480, maxHeight: "90vh", overflow: "auto", boxShadow: "0 24px 48px rgba(0,0,0,0.3)" }} onClick={e => e.stopPropagation()}>
            <div style={{ padding: "24px 24px 16px", borderBottom: `1px solid ${t.border}` }}>
              <h3 style={{ margin: 0, fontSize: 18, fontWeight: 700, color: t.text }}>{modalMode === "add" ? "Add Task" : "Edit Task"}</h3>
            </div>
            <div style={{ padding: "20px 24px", display: "flex", flexDirection: "column", gap: 16 }}>
              <div>
                <label style={{ display: "block", fontSize: 12, fontWeight: 600, color: t.sub, marginBottom: 6, textTransform: "uppercase", letterSpacing: "0.05em" }}>Title *</label>
                <input type="text" value={formData.title} onChange={e => setFormData({ ...formData, title: e.target.value })} placeholder="e.g., Draft reply to eviction notice"
                  style={{ width: "100%", padding: "10px 14px", borderRadius: 8, border: `1px solid ${t.border}`, background: t.bg, color: t.text, fontSize: 14, fontFamily: "inherit" }} />
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                <div>
                  <label style={{ display: "block", fontSize: 12, fontWeight: 600, color: t.sub, marginBottom: 6, textTransform: "uppercase", letterSpacing: "0.05em" }}>Priority</label>
                  <select value={formData.priority} onChange={e => setFormData({ ...formData, priority: e.target.value })}
                    style={{ width: "100%", padding: "10px 14px", borderRadius: 8, border: `1px solid ${t.border}`, background: t.bg, color: t.text, fontSize: 14, fontFamily: "inherit", cursor: "pointer" }}>
                    <option value="high">High</option>
                    <option value="medium">Medium</option>
                    <option value="low">Low</option>
                  </select>
                </div>
                <div>
                  <label style={{ display: "block", fontSize: 12, fontWeight: 600, color: t.sub, marginBottom: 6, textTransform: "uppercase", letterSpacing: "0.05em" }}>Due Date</label>
                  <input type="date" value={formData.due_date} onChange={e => setFormData({ ...formData, due_date: e.target.value })}
                    style={{ width: "100%", padding: "10px 14px", borderRadius: 8, border: `1px solid ${t.border}`, background: t.bg, color: t.text, fontSize: 14, fontFamily: "inherit" }} />
                </div>
              </div>
              <div>
                <label style={{ display: "block", fontSize: 12, fontWeight: 600, color: t.sub, marginBottom: 6, textTransform: "uppercase", letterSpacing: "0.05em" }}>Matter / Case</label>
                <input type="text" value={formData.matter} onChange={e => setFormData({ ...formData, matter: e.target.value })} placeholder="e.g., Singh Tenancy Dispute"
                  style={{ width: "100%", padding: "10px 14px", borderRadius: 8, border: `1px solid ${t.border}`, background: t.bg, color: t.text, fontSize: 14, fontFamily: "inherit" }} />
              </div>
              <div>
                <label style={{ display: "block", fontSize: 12, fontWeight: 600, color: t.sub, marginBottom: 6, textTransform: "uppercase", letterSpacing: "0.05em" }}>Status</label>
                <div style={{ display: "flex", gap: 8 }}>
                  {["pending", "done"].map(s => (
                    <button key={s} onClick={() => setFormData({ ...formData, status: s })} style={{
                      flex: 1, padding: "10px 14px", borderRadius: 8,
                      border: `1px solid ${formData.status === s ? (s === "done" ? "#22c55e" : "#f59e0b") : t.border}`,
                      background: formData.status === s ? (s === "done" ? "rgba(34,197,94,0.1)" : "rgba(245,158,11,0.1)") : t.bg,
                      color: formData.status === s ? (s === "done" ? "#22c55e" : "#f59e0b") : t.sub,
                      fontSize: 14, fontWeight: 600, cursor: "pointer", textTransform: "capitalize"
                    }}>{s === "done" ? "✓ Done" : "○ Pending"}</button>
                  ))}
                </div>
              </div>
              <div>
                <label style={{ display: "block", fontSize: 12, fontWeight: 600, color: t.sub, marginBottom: 6, textTransform: "uppercase", letterSpacing: "0.05em" }}>Description</label>
                <textarea value={formData.description} onChange={e => setFormData({ ...formData, description: e.target.value })} placeholder="Additional notes..." rows={3}
                  style={{ width: "100%", padding: "10px 14px", borderRadius: 8, border: `1px solid ${t.border}`, background: t.bg, color: t.text, fontSize: 14, fontFamily: "inherit", resize: "vertical" }} />
              </div>
            </div>
            <div style={{ padding: "16px 24px 24px", display: "flex", gap: 10, justifyContent: "flex-end", borderTop: `1px solid ${t.border}` }}>
              <button onClick={() => setShowModal(false)} style={{ padding: "10px 18px", borderRadius: 8, border: `1px solid ${t.border}`, background: "transparent", color: t.text, fontSize: 13, fontWeight: 600, cursor: "pointer" }}>Cancel</button>
              <button onClick={saveTask} style={{ padding: "10px 18px", borderRadius: 8, border: "none", background: "#ea580c", color: "#fff", fontSize: 13, fontWeight: 700, cursor: "pointer" }}>{modalMode === "add" ? "Add Task" : "Save Changes"}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}