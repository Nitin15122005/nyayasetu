import React, { useState, useMemo, useCallback, useRef, useEffect } from "react";
import { Btn, Card, Ic, ICONS } from "../components/UI";

const API_BASE = "http://localhost:8001/api";
const getToken = () => localStorage.getItem("token") || "dev-token";

const api = {
  async fetchWithAuth(url, options = {}) {
    const token = getToken();
    console.log(`[Calendar] Request: ${options.method || 'GET'} ${url}`);
    console.log(`[Calendar] Token present: ${!!token}, length: ${token?.length || 0}`);

    const res = await fetch(url, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...(token ? { "Authorization": `Bearer ${token}` } : {}),
        ...options.headers,
      },
    });

    console.log(`[Calendar] Response: ${res.status} ${res.statusText}`);

    if (!res.ok) {
      const errText = await res.text();
      console.error(`[Calendar] Error response:`, errText);
      let err;
      try {
        err = JSON.parse(errText);
      } catch {
        err = { detail: errText || `HTTP ${res.status}` };
      }
      throw new Error(err.detail || `HTTP ${res.status}`);
    }
    return res.json();
  },
  async getEvents(year, month) {
    const params = new URLSearchParams();
    if (year) params.append("year", year);
    if (month !== undefined) params.append("month", month + 1);
    return api.fetchWithAuth(`${API_BASE}/calendar/events?${params}`);
  },
  async createEvent(event) {
    return api.fetchWithAuth(`${API_BASE}/calendar/events`, { method: "POST", body: JSON.stringify(event) });
  },
  async updateEvent(id, event) {
    return api.fetchWithAuth(`${API_BASE}/calendar/events/${id}`, { method: "PUT", body: JSON.stringify(event) });
  },
  async deleteEvent(id) {
    return api.fetchWithAuth(`${API_BASE}/calendar/events/${id}`, { method: "DELETE" });
  },
};

export default function Calendar({ t, toast }) {
  const [viewMode, setViewMode] = useState("Month");
  const [currentDate, setCurrentDate] = useState(new Date());
  const [selectedDate, setSelectedDate] = useState(null);
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(false);
  const [hasLoaded, setHasLoaded] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [modalMode, setModalMode] = useState("add");
  const [editingEvent, setEditingEvent] = useState(null);
  const [formData, setFormData] = useState({
    title: "", event_type: "hearing", event_date: "", event_time: "", court: "", description: ""
  });

  const monthNames = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
  const days = ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"];
  const isDark = t.text === "#ffffff" || t.text === "#f8fafc";

  // ── Auto-load events on mount and when month changes ────────────────────
  const loadEvents = useCallback(async (showLoading = true) => {
    const year = currentDate.getFullYear();
    const month = currentDate.getMonth();
    if (showLoading) setLoading(true);
    try {
      console.log(`[Calendar] Loading events for ${year}-${month + 1}`);
      const data = await api.getEvents(year, month);
      console.log(`[Calendar] Loaded ${data?.length || 0} events`);
      const mapped = (Array.isArray(data) ? data : []).map(e => ({
        id: e.id, date: e.event_date, title: e.title, type: e.event_type,
        time: e.event_time || "", court: e.court || "N/A", description: e.description || ""
      }));
      setEvents(mapped);
      setHasLoaded(true);
    } catch (err) {
      console.error(`[Calendar] Failed to load:`, err);
      toast("Failed to load events: " + err.message, "error");
    } finally {
      if (showLoading) setLoading(false);
    }
  }, [currentDate]);

  // Auto-load when month changes
  useEffect(() => {
    loadEvents();
  }, [loadEvents]);

  // ── Calendar Math ─────────────────────────────────────────────────────────
  const calendarData = useMemo(() => {
    const year = currentDate.getFullYear();
    const month = currentDate.getMonth();
    const firstDayOfMonth = new Date(year, month, 1).getDay();
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    const daysInPrevMonth = new Date(year, month, 0).getDate();
    const prevDays = [];
    for (let i = firstDayOfMonth - 1; i >= 0; i--) prevDays.push(daysInPrevMonth - i);
    const currentDays = Array.from({ length: daysInMonth }, (_, i) => i + 1);
    const totalCells = prevDays.length + currentDays.length;
    const nextDaysCount = totalCells <= 35 ? 35 - totalCells : 42 - totalCells;
    const nextDays = Array.from({ length: nextDaysCount }, (_, i) => i + 1);
    return { prevDays, currentDays, nextDays, year, month };
  }, [currentDate]);

  const formatDateKey = (year, month, day) => `${year}-${String(month + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
  const getEventsForDate = (year, month, day) => events.filter(e => e.date === formatDateKey(year, month, day));

  // ── Navigation ────────────────────────────────────────────────────────────
  const goToPrevMonth = () => { setCurrentDate(new Date(currentDate.getFullYear(), currentDate.getMonth() - 1, 1)); setSelectedDate(null); };
  const goToNextMonth = () => { setCurrentDate(new Date(currentDate.getFullYear(), currentDate.getMonth() + 1, 1)); setSelectedDate(null); };
  const goToToday = () => {
    const today = new Date();
    setCurrentDate(new Date(today.getFullYear(), today.getMonth(), 1));
    setSelectedDate({ year: today.getFullYear(), month: today.getMonth(), day: today.getDate() });
  };

  // ── Event Management ──────────────────────────────────────────────────────
  const openAddModal = (defaultType = "hearing") => {
    if (!selectedDate) { toast("Please select a date first", "warn"); return; }
    setModalMode("add"); setEditingEvent(null);
    setFormData({
      title: "", event_type: defaultType,
      event_date: formatDateKey(selectedDate.year, selectedDate.month, selectedDate.day),
      event_time: "", court: "", description: ""
    });
    setShowModal(true);
  };

  const openEditModal = (event) => {
    setModalMode("edit"); setEditingEvent(event);
    setFormData({
      title: event.title, event_type: event.type, event_date: event.date,
      event_time: event.time || "", court: event.court === "N/A" ? "" : event.court, description: event.description || ""
    });
    setShowModal(true);
  };

  const saveEvent = async () => {
    if (!formData.title.trim()) { toast("Title is required", "error"); return; }
    try {
      const payload = {
        title: formData.title, event_type: formData.event_type, event_date: formData.event_date,
        event_time: formData.event_time || null, court: formData.court || null, description: formData.description || null
      };
      if (modalMode === "add") {
        await api.createEvent(payload);
        toast("Event added", "success");
      }
      else {
        await api.updateEvent(editingEvent.id, payload);
        toast("Event updated", "success");
      }
      await loadEvents(false);
      setShowModal(false);
    } catch (err) {
      toast(err.message, "error");
    }
  };

  const handleDeleteEvent = async (id) => {
    if (!window.confirm("Delete this event?")) return;
    try {
      await api.deleteEvent(id);
      toast("Event deleted", "success");
      await loadEvents(false);
    }
    catch (err) {
      toast(err.message, "error");
    }
  };

  const getEventColors = (type) => {
    switch (type) {
      case "hearing": return { bg: isDark ? "rgba(234,88,12,0.25)" : "rgba(234,88,12,0.12)", color: "#ea580c" };
      case "deadline": return { bg: isDark ? "rgba(239,68,68,0.25)" : "rgba(239,68,68,0.12)", color: "#ef4444" };
      case "meeting": return { bg: isDark ? "rgba(59,130,246,0.25)" : "rgba(59,130,246,0.12)", color: "#3b82f6" };
      case "reminder": return { bg: isDark ? "rgba(245,158,11,0.25)" : "rgba(245,158,11,0.12)", color: "#f59e0b" };
      default: return { bg: isDark ? "rgba(100,116,139,0.25)" : "rgba(100,116,139,0.12)", color: "#64748b" };
    }
  };

  // ── Render Cell ───────────────────────────────────────────────────────────
  const renderCell = (num, isCurrentMonth, isPrev) => {
    const { year, month } = calendarData;
    const cellYear = isPrev ? (month === 0 ? year - 1 : year) : (isCurrentMonth ? year : (month === 11 ? year + 1 : year));
    const cellMonth = isPrev ? (month === 0 ? 11 : month - 1) : (isCurrentMonth ? month : (month === 11 ? 0 : month + 1));
    const dateKey = formatDateKey(cellYear, cellMonth, num);
    const dayEvents = events.filter(e => e.date === dateKey);
    const isSelected = selectedDate && selectedDate.year === cellYear && selectedDate.month === cellMonth && selectedDate.day === num;
    const isToday = new Date().toDateString() === new Date(cellYear, cellMonth, num).toDateString();

    return (
      <div key={`${isCurrentMonth ? "curr" : isPrev ? "prev" : "next"}-${num}`}
        onClick={() => setSelectedDate({ year: cellYear, month: cellMonth, day: num })}
        style={{
          minHeight: 100, padding: "8px 12px",
          borderRight: `1px solid ${t.border}`, borderBottom: `1px solid ${t.border}`,
          color: isCurrentMonth ? t.text : t.sub, opacity: isCurrentMonth ? 1 : 0.35,
          fontSize: 13, fontWeight: 600, display: "flex", flexDirection: "column", alignItems: "flex-start",
          background: isSelected ? (isDark ? "rgba(234,88,12,0.15)" : "rgba(234,88,12,0.08)") : isToday ? (isDark ? "rgba(59,130,246,0.1)" : "rgba(59,130,246,0.05)") : "transparent",
          cursor: "pointer", transition: "background 0.15s", position: "relative"
        }}>
        <div style={{
          width: 26, height: 26, borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center",
          background: isSelected ? "#ea580c" : isToday ? "#3b82f6" : "transparent",
          color: (isSelected || isToday) ? "#fff" : "inherit", fontSize: 12, marginBottom: 4
        }}>{num}</div>
        <div style={{ display: "flex", flexDirection: "column", gap: 3, width: "100%" }}>
          {dayEvents.slice(0, 2).map(ev => {
            const colors = getEventColors(ev.type);
            return (
              <div key={ev.id} style={{ fontSize: 10, fontWeight: 600, padding: "2px 6px", borderRadius: 4, background: colors.bg, color: colors.color, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                {ev.title}
              </div>
            );
          })}
          {dayEvents.length > 2 && <div style={{ fontSize: 10, color: t.sub, paddingLeft: 4 }}>+{dayEvents.length - 2} more</div>}
        </div>
      </div>
    );
  };

  // ── List View ─────────────────────────────────────────────────────────────
  const renderListView = () => {
    const sortedEvents = [...events].sort((a, b) => new Date(a.date) - new Date(b.date));
    return (
      <Card t={t} style={{ padding: 0, overflow: "hidden" }}>
        <div style={{ padding: "20px 24px", borderBottom: `1px solid ${t.border}`, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <h2 style={{ fontSize: 18, fontWeight: 700, margin: 0, color: t.text }}>All Events ({sortedEvents.length})</h2>
          <button onClick={() => openAddModal("hearing")} style={{ background: "#ea580c", color: "#fff", border: "none", borderRadius: 8, padding: "8px 16px", fontSize: 13, fontWeight: 700, cursor: "pointer" }}>+ Add Event</button>
        </div>
        <div style={{ padding: "16px 24px" }}>
          {sortedEvents.length === 0 ? (
            <div style={{ textAlign: "center", color: t.sub, padding: 40 }}>No events scheduled</div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              {sortedEvents.map(ev => {
                const evDate = new Date(ev.date);
                const colors = getEventColors(ev.type);
                return (
                  <div key={ev.id} style={{ display: "flex", alignItems: "center", gap: 16, padding: "14px 16px", borderRadius: 10, border: `1px solid ${t.border}`, background: t.surface }}>
                    <div style={{ width: 48, height: 48, borderRadius: 10, background: colors.bg, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", color: colors.color, fontWeight: 800, fontSize: 12, flexShrink: 0 }}>
                      <div>{evDate.toLocaleString("default", { month: "short" })}</div><div style={{ fontSize: 16 }}>{evDate.getDate()}</div>
                    </div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontWeight: 700, fontSize: 14, color: t.text, marginBottom: 4 }}>{ev.title}</div>
                      <div style={{ fontSize: 12, color: t.sub, display: "flex", gap: 12, flexWrap: "wrap" }}>
                        <span>{ev.time || "All day"}</span><span>{ev.court}</span>
                        <span style={{ padding: "2px 8px", borderRadius: 4, fontSize: 10, fontWeight: 700, background: colors.bg, color: colors.color, textTransform: "uppercase" }}>{ev.type}</span>
                      </div>
                    </div>
                    <div style={{ display: "flex", gap: 6, flexShrink: 0 }}>
                      <button onClick={() => openEditModal(ev)} style={{ width: 32, height: 32, borderRadius: 6, border: `1px solid ${t.border}`, background: "transparent", color: t.sub, cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 14 }}>✏️</button>
                      <button onClick={() => handleDeleteEvent(ev.id)} style={{ width: 32, height: 32, borderRadius: 6, border: `1px solid ${t.border}`, background: "transparent", color: "#ef4444", cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 14 }}>🗑️</button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </Card>
    );
  };

  const { prevDays, currentDays, nextDays, year, month } = calendarData;
  const selectedEvents = selectedDate ? getEventsForDate(selectedDate.year, selectedDate.month, selectedDate.day) : [];

  return (
    <div style={{ maxWidth: 1200, margin: "40px auto", padding: "0 24px", minHeight: "calc(100vh - 60px - 40px)" }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 32, flexWrap: "wrap", gap: 16 }}>
        <div>
          <h1 style={{ fontSize: 24, fontWeight: 800, color: t.text, margin: "0 0 6px" }}>Calendar</h1>
          <p style={{ fontSize: 14, color: t.sub, margin: 0 }}>Hearings & deadlines across all matters</p>
        </div>
        <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
          <div style={{ display: "flex", background: t.surface, border: `1px solid ${t.border}`, borderRadius: 8, padding: 4 }}>
            {["Month", "List"].map(m => (
              <button key={m} onClick={() => setViewMode(m)} style={{
                background: viewMode === m ? (isDark ? "rgba(255,255,255,0.05)" : "rgba(0,0,0,0.04)") : "transparent",
                color: viewMode === m ? t.text : t.sub, border: "none", borderRadius: 6,
                padding: "6px 14px", fontSize: 13, fontWeight: 600, cursor: "pointer", transition: "all 0.2s", display: "flex", alignItems: "center", gap: 6
              }}>
                {m === "Month" && <Ic d={ICONS.grid} size={14} color="inherit" />}
                {m === "List" && <Ic d={ICONS.menu} size={14} color="inherit" />}
                {m}
              </button>
            ))}
          </div>
          <button onClick={() => loadEvents()} style={{ padding: "10px 18px", borderRadius: 8, border: `1px solid ${t.border}`, background: t.surface, color: t.text, fontSize: 13, fontWeight: 600, cursor: "pointer" }}>🔄 Refresh</button>
          <button onClick={() => openAddModal("hearing")} style={{ background: "#ea580c", color: "#fff", border: "none", borderRadius: 8, padding: "10px 18px", fontSize: 13, fontWeight: 700, cursor: "pointer", display: "flex", alignItems: "center", gap: 6 }}>+ Hearing</button>
          <button onClick={() => openAddModal("deadline")} style={{ background: "#ef4444", color: "#fff", border: "none", borderRadius: 8, padding: "10px 18px", fontSize: 13, fontWeight: 700, cursor: "pointer", display: "flex", alignItems: "center", gap: 6 }}>+ Deadline</button>
        </div>
      </div>

      {loading && (
        <div style={{ textAlign: "center", padding: 20, color: t.sub, fontSize: 14 }}>
          <span style={{ display: "inline-block", width: 16, height: 16, border: `2px solid ${t.border}`, borderTopColor: t.blue, borderRadius: "50%", animation: "spin 0.8s linear infinite", marginRight: 8, verticalAlign: "middle" }} />
          Loading events...
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: viewMode === "List" ? "1fr" : "1fr 300px", gap: 24 }}>
        {viewMode === "Month" ? (
          <Card t={t} style={{ padding: 0, overflow: "hidden" }}>
            {/* Month Navigation */}
            <div style={{ padding: "20px 24px", display: "flex", alignItems: "center", justifyContent: "space-between", borderBottom: `1px solid ${t.border}` }}>
              <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
                <button onClick={goToPrevMonth} style={{ background: "none", border: "none", cursor: "pointer", color: t.sub, padding: 4 }}>
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="15 18 9 12 15 6"></polyline></svg>
                </button>
                <h2 style={{ fontSize: 18, fontWeight: 700, margin: 0, minWidth: 140, textAlign: "center", color: t.text }}>{monthNames[month]} {year}</h2>
                <button onClick={goToNextMonth} style={{ background: "none", border: "none", cursor: "pointer", color: t.sub, padding: 4 }}>
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="9 18 15 12 9 6"></polyline></svg>
                </button>
              </div>
              <div style={{ display: "flex", gap: 10 }}>
                <button onClick={() => loadEvents()} style={{ background: "transparent", border: `1px solid ${t.border}`, borderRadius: 8, padding: "6px 14px", fontSize: 13, fontWeight: 600, color: t.text, cursor: "pointer" }}>🔄 Refresh</button>
                <button onClick={goToToday} style={{ background: "transparent", border: `1px solid ${t.border}`, borderRadius: 8, padding: "6px 14px", fontSize: 13, fontWeight: 600, color: t.text, cursor: "pointer" }}>Today</button>
              </div>
            </div>

            {/* Days Header */}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(7, 1fr)", borderBottom: `1px solid ${t.border}` }}>
              {days.map(d => (
                <div key={d} style={{ padding: "12px", textAlign: "center", fontSize: 11, fontWeight: 700, color: t.sub, letterSpacing: "0.05em", borderRight: `1px solid ${t.border}` }}>{d}</div>
              ))}
            </div>

            {/* Grid */}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(7, 1fr)" }}>
              {prevDays.map(d => renderCell(d, false, true))}
              {currentDays.map(d => renderCell(d, true, false))}
              {nextDays.map(d => renderCell(d, false, false))}
            </div>
          </Card>
        ) : (
          renderListView()
        )}

        {/* Right Sidebar */}
        {viewMode === "Month" && (
          <div>
            <h3 style={{ fontSize: 16, fontWeight: 700, margin: "0 0 16px", color: t.text }}>
              {selectedDate ? `${monthNames[selectedDate.month]} ${selectedDate.day}, ${selectedDate.year}` : "Select a date"}
            </h3>
            {!hasLoaded && !loading ? (
              <div style={{ textAlign: "center", color: t.sub, marginTop: 40, fontSize: 14, padding: "20px", border: `1px dashed ${t.border}`, borderRadius: 10 }}>
                <div style={{ fontSize: 24, marginBottom: 8 }}>📅</div>
                Loading events...
              </div>
            ) : selectedDate ? (
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {selectedEvents.length === 0 ? (
                  <div style={{ padding: "24px 16px", textAlign: "center", color: t.sub, fontSize: 14, border: `1px dashed ${t.border}`, borderRadius: 10 }}>
                    <div style={{ marginBottom: 8, fontSize: 24 }}>📅</div>
                    No events on this day<br />
                    <button onClick={() => openAddModal("hearing")} style={{ marginTop: 12, background: "none", border: "none", color: t.blue, fontSize: 13, fontWeight: 600, cursor: "pointer", textDecoration: "underline" }}>Add an event</button>
                  </div>
                ) : (
                  selectedEvents.map(ev => {
                    const colors = getEventColors(ev.type);
                    return (
                      <div key={ev.id} onClick={() => openEditModal(ev)} style={{ padding: "14px 16px", borderRadius: 10, border: `1px solid ${t.border}`, background: t.surface, cursor: "pointer" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
                          <div style={{ width: 8, height: 8, borderRadius: "50%", background: colors.color }} />
                          <span style={{ fontSize: 10, fontWeight: 700, textTransform: "uppercase", color: colors.color }}>{ev.type}</span>
                        </div>
                        <div style={{ fontWeight: 700, fontSize: 14, color: t.text, marginBottom: 6 }}>{ev.title}</div>
                        <div style={{ fontSize: 12, color: t.sub, display: "flex", flexDirection: "column", gap: 4 }}>
                          <span>🕐 {ev.time || "All day"}</span><span>📍 {ev.court}</span>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            ) : (
              <div style={{ textAlign: "center", color: t.sub, marginTop: 40, fontSize: 14, padding: "20px", border: `1px dashed ${t.border}`, borderRadius: 10 }}>
                <div style={{ fontSize: 24, marginBottom: 8 }}>📅</div>
                Click on any date to view or add events
              </div>
            )}
          </div>
        )}
      </div>

      {/* Modal */}
      {showModal && (
        <div style={{ position: "fixed", top: 0, left: 0, right: 0, bottom: 0, background: "rgba(0,0,0,0.6)", zIndex: 2000, display: "flex", alignItems: "center", justifyContent: "center", padding: 24 }} onClick={() => setShowModal(false)}>
          <div style={{ background: t.surface, borderRadius: 16, border: `1px solid ${t.border}`, width: "100%", maxWidth: 440, maxHeight: "90vh", overflow: "auto" }} onClick={e => e.stopPropagation()}>
            <div style={{ padding: "24px 24px 16px", borderBottom: `1px solid ${t.border}` }}>
              <h3 style={{ margin: 0, fontSize: 18, fontWeight: 700, color: t.text }}>{modalMode === "add" ? "Add Event" : "Edit Event"}</h3>
              <p style={{ margin: "4px 0 0", fontSize: 13, color: t.sub }}>{selectedDate && `${monthNames[selectedDate.month]} ${selectedDate.day}, ${selectedDate.year}`}</p>
            </div>
            <div style={{ padding: "20px 24px", display: "flex", flexDirection: "column", gap: 16 }}>
              <div>
                <label style={{ display: "block", fontSize: 12, fontWeight: 600, color: t.sub, marginBottom: 6, textTransform: "uppercase" }}>Title *</label>
                <input type="text" value={formData.title} onChange={e => setFormData({ ...formData, title: e.target.value })} placeholder="e.g., Hearing: State v. Sharma"
                  style={{ width: "100%", padding: "10px 14px", borderRadius: 8, border: `1px solid ${t.border}`, background: t.bg, color: t.text, fontSize: 14, fontFamily: "inherit" }} />
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                <div>
                  <label style={{ display: "block", fontSize: 12, fontWeight: 600, color: t.sub, marginBottom: 6, textTransform: "uppercase" }}>Type</label>
                  <select value={formData.event_type} onChange={e => setFormData({ ...formData, event_type: e.target.value })}
                    style={{ width: "100%", padding: "10px 14px", borderRadius: 8, border: `1px solid ${t.border}`, background: t.bg, color: t.text, fontSize: 14, fontFamily: "inherit", cursor: "pointer" }}>
                    <option value="hearing">Hearing</option><option value="deadline">Deadline</option><option value="meeting">Meeting</option><option value="reminder">Reminder</option>
                  </select>
                </div>
                <div>
                  <label style={{ display: "block", fontSize: 12, fontWeight: 600, color: t.sub, marginBottom: 6, textTransform: "uppercase" }}>Time</label>
                  <input type="text" value={formData.event_time} onChange={e => setFormData({ ...formData, event_time: e.target.value })} placeholder="e.g., 10:00"
                    style={{ width: "100%", padding: "10px 14px", borderRadius: 8, border: `1px solid ${t.border}`, background: t.bg, color: t.text, fontSize: 14, fontFamily: "inherit" }} />
                </div>
              </div>
              <div>
                <label style={{ display: "block", fontSize: 12, fontWeight: 600, color: t.sub, marginBottom: 6, textTransform: "uppercase" }}>Court / Location</label>
                <input type="text" value={formData.court} onChange={e => setFormData({ ...formData, court: e.target.value })} placeholder="e.g., Delhi High Court"
                  style={{ width: "100%", padding: "10px 14px", borderRadius: 8, border: `1px solid ${t.border}`, background: t.bg, color: t.text, fontSize: 14, fontFamily: "inherit" }} />
              </div>
              <div>
                <label style={{ display: "block", fontSize: 12, fontWeight: 600, color: t.sub, marginBottom: 6, textTransform: "uppercase" }}>Description</label>
                <textarea value={formData.description} onChange={e => setFormData({ ...formData, description: e.target.value })} placeholder="Additional notes..." rows={3}
                  style={{ width: "100%", padding: "10px 14px", borderRadius: 8, border: `1px solid ${t.border}`, background: t.bg, color: t.text, fontSize: 14, fontFamily: "inherit", resize: "vertical" }} />
              </div>
            </div>
            <div style={{ padding: "16px 24px 24px", display: "flex", gap: 10, justifyContent: "flex-end", borderTop: `1px solid ${t.border}` }}>
              <button onClick={() => setShowModal(false)} style={{ padding: "10px 18px", borderRadius: 8, border: `1px solid ${t.border}`, background: "transparent", color: t.text, fontSize: 13, fontWeight: 600, cursor: "pointer" }}>Cancel</button>
              <button onClick={saveEvent} style={{ padding: "10px 18px", borderRadius: 8, border: "none", background: "#ea580c", color: "#fff", fontSize: 13, fontWeight: 700, cursor: "pointer" }}>{modalMode === "add" ? "Add Event" : "Save Changes"}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}