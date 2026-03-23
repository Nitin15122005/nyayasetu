import { useState, useRef, useEffect } from "react";
import { Card, PageTitle, Btn, Input, Textarea, Ic, ICONS, ErrBox } from "../components/UI";

// ── Step indicator ────────────────────────────────────────────────────────────
const Steps = ({ current, t }) => {
  const steps = ["Upload Photo", "Your Details", "Verify Phone", "Review", "Certificate"];
  return (
    <div style={{ display: "flex", alignItems: "center", marginBottom: 36, overflowX: "auto", paddingBottom: 4 }}>
      {steps.map((s, i) => {
        const done   = i < current;
        const active = i === current;
        const color  = done ? "#34d399" : active ? t.blue : t.muted;
        return (
          <div key={i} style={{ display: "flex", alignItems: "center", flex: i < steps.length - 1 ? 1 : 0, minWidth: 0 }}>
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 5, flexShrink: 0 }}>
              <div style={{
                width: 30, height: 30, borderRadius: "50%",
                background: done ? "#34d39920" : active ? `${t.blue}20` : t.surfaceUp,
                border: `2px solid ${color}`,
                display: "flex", alignItems: "center", justifyContent: "center",
                fontSize: 11, fontWeight: 800, color, transition: "all 0.3s",
              }}>
                {done ? "✓" : i + 1}
              </div>
              <span style={{ fontSize: 9, color, fontWeight: active ? 700 : 500, whiteSpace: "nowrap", letterSpacing: "0.03em", textAlign: "center" }}>{s}</span>
            </div>
            {i < steps.length - 1 && (
              <div style={{ flex: 1, height: 2, background: done ? "#34d39944" : t.border, margin: "0 6px", marginBottom: 20, transition: "background 0.3s", minWidth: 8 }} />
            )}
          </div>
        );
      })}
    </div>
  );
};

const Label = ({ text, required, t }) => (
  <label style={{ fontSize: 11, color: t.sub, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.07em", display: "block", marginBottom: 6 }}>
    {text} {required && <span style={{ color: t.blue }}>*</span>}
  </label>
);

const CertField = ({ label, value, mono, t, highlight }) => (
  <div style={{ display: "flex", gap: 12, padding: "9px 14px", borderRadius: 7, background: highlight ? `${t.blue}0a` : t.surfaceUp, border: `1px solid ${highlight ? t.blue + "33" : t.border}`, fontSize: 12, alignItems: "flex-start" }}>
    <span style={{ color: t.muted, minWidth: 110, fontWeight: 700, flexShrink: 0, paddingTop: 1 }}>{label}</span>
    <span style={{ color: t.text, fontFamily: mono ? "monospace" : "inherit", wordBreak: "break-all", lineHeight: 1.5 }}>{value || <span style={{ color: t.muted, fontStyle: "italic" }}>—</span>}</span>
  </div>
);

// ── OTP Input — 6 boxes ───────────────────────────────────────────────────────
const OTPInput = ({ value, onChange, t }) => {
  const inputs = useRef([]);
  const digits = (value + "      ").slice(0, 6).split("");

  const handleKey = (i, e) => {
    if (e.key === "Backspace") {
      const next = value.slice(0, i) + value.slice(i + 1);
      onChange(next);
      if (i > 0) inputs.current[i - 1]?.focus();
    } else if (/^\d$/.test(e.key)) {
      const next = value.slice(0, i) + e.key + value.slice(i + 1);
      onChange(next.slice(0, 6));
      if (i < 5) inputs.current[i + 1]?.focus();
    }
  };

  return (
    <div style={{ display: "flex", gap: 10, justifyContent: "center" }}>
      {digits.map((d, i) => (
        <input
          key={i}
          ref={el => inputs.current[i] = el}
          type="text" inputMode="numeric" maxLength={1}
          value={d.trim()}
          onChange={() => {}}
          onKeyDown={e => handleKey(i, e)}
          onFocus={e => e.target.select()}
          onPaste={e => {
            e.preventDefault();
            const pasted = e.clipboardData.getData("text").replace(/\D/g, "").slice(0, 6);
            onChange(pasted);
            inputs.current[Math.min(pasted.length, 5)]?.focus();
          }}
          style={{
            width: 48, height: 56, textAlign: "center",
            fontSize: 22, fontWeight: 800, fontFamily: "monospace",
            background: d.trim() ? `${t.blue}12` : t.surfaceUp,
            border: `2px solid ${d.trim() ? t.blue : t.border}`,
            borderRadius: 10, color: t.text, outline: "none",
            transition: "all 0.15s",
          }}
        />
      ))}
    </div>
  );
};

// ── Countdown timer ───────────────────────────────────────────────────────────
const Countdown = ({ seconds, onExpire, t }) => {
  const [left, setLeft] = useState(seconds);
  useEffect(() => {
    if (left <= 0) { onExpire?.(); return; }
    const id = setTimeout(() => setLeft(l => l - 1), 1000);
    return () => clearTimeout(id);
  }, [left]);
  const m = Math.floor(left / 60);
  const s = left % 60;
  return (
    <span style={{ fontSize: 13, color: left < 60 ? t.red || "#f56565" : t.muted, fontWeight: 600, fontFamily: "monospace" }}>
      {m}:{String(s).padStart(2, "0")}
    </span>
  );
};

// ── Main component ────────────────────────────────────────────────────────────
export default function Evidence({ t, toast, state, setState }) {
  const useP = !!setState;

  // Local state (not persisted — wizard resets on page change intentionally for security)
  const [file,          setFile]          = useState(null);
  const [prev,          setPrev]          = useState(null);
  const [name,          setName]          = useState("");
  const [phone,         setPhone]         = useState("");
  const [address,       setAddress]       = useState("");
  const [brief,         setBrief]         = useState("");
  const [incDate,       setIncDate]       = useState("");
  const [policeStation, setPoliceStation] = useState("");
  const [step,          setStep]          = useState(0);
  const [cert,          setCert]          = useState(null);

  // OTP state
  const [otpSent,     setOtpSent]     = useState(false);
  const [otpValue,    setOtpValue]    = useState("");
  const [otpVerified, setOtpVerified] = useState(false);
  const [otpExpired,  setOtpExpired]  = useState(false);
  const [otpLoading,  setOtpLoading]  = useState(false);
  const [verifyLoading, setVerifyLoading] = useState(false);

  const [load, setLoad] = useState(false);
  const [err,  setErr]  = useState(null);
  const fileRef = useRef();

  const pickFile = (f) => {
    if (!f) return;
    setFile(f); setCert(null); setErr(null);
    const rd = new FileReader();
    rd.onload = e => setPrev(e.target.result);
    rd.readAsDataURL(f);
  };

  // ── Send OTP ────────────────────────────────────────────────────────────────
  const sendOtp = async () => {
    if (!phone.trim()) return;
    setOtpLoading(true); setErr(null); setOtpSent(false); setOtpExpired(false); setOtpValue("");
    try {
      const r = await fetch("http://localhost:8001/api/otp/send", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phone: phone.trim() }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || `Error ${r.status}`);
      setOtpSent(true);
      toast("OTP sent to your WhatsApp ✓", "success");
    } catch (e) { setErr(e.message); toast(e.message, "error"); }
    finally { setOtpLoading(false); }
  };

  // ── Verify OTP ──────────────────────────────────────────────────────────────
  const verifyOtp = async () => {
    if (otpValue.length !== 6) return;
    setVerifyLoading(true); setErr(null);
    try {
      const r = await fetch("http://localhost:8001/api/otp/verify", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phone: phone.trim(), otp: otpValue }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || `Error ${r.status}`);
      setOtpVerified(true);
      toast("Phone verified ✓", "success");
      setTimeout(() => setStep(3), 800);
    } catch (e) { setErr(e.message); setOtpValue(""); toast(e.message, "error"); }
    finally { setVerifyLoading(false); }
  };

  // ── Generate certificate ────────────────────────────────────────────────────
  const generate = async () => {
    setLoad(true); setErr(null);
    try {
      const fd = new FormData();
      fd.append("file",                file);
      fd.append("complainant_name",    name    || "Not provided");
      fd.append("complainant_phone",   phone   || "");
      fd.append("complainant_address", address || "");
      fd.append("incident_brief",      brief   || "Evidence submitted via NyayaSetu");
      fd.append("incident_date",       incDate || "");
      fd.append("police_station",      policeStation || "");

      const r = await fetch("http://localhost:8001/api/evidence", { method: "POST", body: fd });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || `Error ${r.status}`);
      setCert(d);
      setStep(4);
      toast("Certificate generated ✓", "success");
    } catch (e) { setErr(e.message); toast(e.message, "error"); }
    finally { setLoad(false); }
  };

  const reset = () => {
    setFile(null); setPrev(null); setName(""); setPhone(""); setAddress("");
    setBrief(""); setIncDate(""); setPoliceStation(""); setStep(0); setCert(null);
    setOtpSent(false); setOtpValue(""); setOtpVerified(false); setOtpExpired(false);
    setErr(null);
  };

  const hash = cert?.sha256_hash || cert?.sha256 || "";

  return (
    <div style={{ maxWidth: 820, margin: "0 auto", padding: "52px 24px", animation: "fadeUp 0.4s ease" }}>
      <PageTitle icon="camera" title="Evidence Certificate" badge="BSA §63"
        desc="Generate a court-admissible SHA-256 certificate for digital evidence under BSA Section 63."
        t={t} />

      <Steps current={step} t={t} />

      {/* ── STEP 0: Upload ── */}
      {step === 0 && (
        <Card t={t}>
          <h3 style={{ fontSize: 15, fontWeight: 800, color: t.text, margin: "0 0 6px" }}>Upload the evidence photo</h3>
          <p style={{ fontSize: 13, color: t.sub, margin: "0 0 20px", lineHeight: 1.7 }}>
            SHA-256 hash is computed <strong style={{ color: t.text }}>before</strong> any processing — chain of custody preserved.
          </p>

          {prev ? (
            <div style={{ position: "relative", borderRadius: 12, overflow: "hidden", border: `1.5px solid ${t.border}`, marginBottom: 20 }}>
              <img src={prev} alt="preview" style={{ width: "100%", maxHeight: 320, objectFit: "contain", display: "block", background: t.bg }} />
              <div style={{ padding: "12px 16px", background: t.surfaceUp, borderTop: `1px solid ${t.border}`, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <p style={{ fontSize: 13, fontWeight: 700, color: t.text, margin: "0 0 2px" }}>{file?.name}</p>
                  <p style={{ fontSize: 11, color: t.muted, margin: 0 }}>{file ? (file.size / 1024).toFixed(1) + " KB · " + file.type : ""}</p>
                </div>
                <button onClick={() => { setFile(null); setPrev(null); setErr(null); }} style={{ background: "none", border: `1px solid ${t.border}`, borderRadius: 7, cursor: "pointer", color: t.sub, fontSize: 12, fontFamily: "inherit", fontWeight: 600, padding: "5px 12px" }}>Change</button>
              </div>
            </div>
          ) : (
            <div
              onClick={() => fileRef.current.click()}
              onDragOver={e => e.preventDefault()}
              onDrop={e => { e.preventDefault(); const f = e.dataTransfer.files[0]; if (f?.type.startsWith("image/")) pickFile(f); }}
              style={{ border: `2px dashed ${t.border}`, borderRadius: 12, padding: "52px 24px", textAlign: "center", cursor: "pointer", background: t.surfaceUp, transition: "all 0.15s", marginBottom: 20 }}
              onMouseEnter={e => { e.currentTarget.style.borderColor = t.blue; e.currentTarget.style.background = `${t.blue}08`; }}
              onMouseLeave={e => { e.currentTarget.style.borderColor = t.border; e.currentTarget.style.background = t.surfaceUp; }}
            >
              <input ref={fileRef} type="file" accept=".jpg,.jpeg,.png,.webp" style={{ display: "none" }} onChange={e => pickFile(e.target.files[0])} />
              <div style={{ width: 52, height: 52, borderRadius: 14, background: `${t.blue}14`, border: `1px solid ${t.blue}22`, display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 16px" }}>
                <Ic d={ICONS.upload} size={22} color={t.blue} />
              </div>
              <p style={{ fontSize: 14, fontWeight: 600, color: t.text, margin: "0 0 6px" }}>Drop image here or <span style={{ color: t.blue }}>browse</span></p>
              <p style={{ fontSize: 12, color: t.muted, margin: 0 }}>JPG, PNG, WebP · Screenshots, photos, chat exports</p>
            </div>
          )}

          <Btn onClick={() => setStep(1)} disabled={!file} t={t}>
            Continue <Ic d={ICONS.arrow} size={14} color="#fff" sw={2} />
          </Btn>
        </Card>
      )}

      {/* ── STEP 1: Details ── */}
      {step === 1 && (
        <Card t={t}>
          <h3 style={{ fontSize: 15, fontWeight: 800, color: t.text, margin: "0 0 6px" }}>Complainant details</h3>
          <p style={{ fontSize: 13, color: t.sub, margin: "0 0 24px", lineHeight: 1.7 }}>These will appear on the certificate. Name and incident description are required.</p>

          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <div>
              <Label text="Full Name" required t={t} />
              <Input value={name} onChange={e => setName(e.target.value)} placeholder="e.g. Rahul Sharma" t={t} />
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
              <div>
                <Label text="Phone Number" required t={t} />
                <div style={{ display: "flex", gap: 8 }}>
                  <Input value={phone} onChange={e => { setPhone(e.target.value); setOtpVerified(false); setOtpSent(false); }} placeholder="9876543210" t={t} />
                </div>
                <p style={{ fontSize: 11, color: t.muted, margin: "5px 0 0" }}>You will receive a WhatsApp OTP on this number</p>
              </div>
              <div>
                <Label text="Incident Date" t={t} />
                <input type="date" value={incDate} onChange={e => setIncDate(e.target.value)}
                  style={{ background: t.surfaceUp, border: `1.5px solid ${t.border}`, borderRadius: 8, padding: "10px 14px", color: t.text, fontSize: 14, fontFamily: "inherit", outline: "none", width: "100%", boxSizing: "border-box" }} />
              </div>
            </div>
            <div>
              <Label text="Your Address" t={t} />
              <Input value={address} onChange={e => setAddress(e.target.value)} placeholder="e.g. Flat 4B, Andheri West, Mumbai 400058" t={t} />
            </div>
            <div>
              <Label text="Police Station (if FIR filed)" t={t} />
              <Input value={policeStation} onChange={e => setPoliceStation(e.target.value)} placeholder="e.g. Andheri Police Station, Mumbai" t={t} />
            </div>
            <div>
              <Label text="Incident Description" required t={t} />
              <Textarea value={brief} onChange={e => setBrief(e.target.value)} rows={4}
                placeholder="Describe what happened. Include date, location, and nature of incident. This will appear verbatim in the certificate." t={t} />
            </div>
          </div>

          <div style={{ display: "flex", gap: 10, marginTop: 24 }}>
            <button onClick={() => setStep(0)} style={{ background: "none", border: `1.5px solid ${t.border}`, borderRadius: 8, cursor: "pointer", color: t.sub, fontSize: 13, fontFamily: "inherit", fontWeight: 600, padding: "10px 20px" }}>← Back</button>
            <Btn onClick={() => setStep(2)} disabled={!name.trim() || !brief.trim() || !phone.trim()} t={t}>
              Verify Phone <Ic d={ICONS.arrow} size={14} color="#fff" sw={2} />
            </Btn>
          </div>
        </Card>
      )}

      {/* ── STEP 2: OTP Verification ── */}
      {step === 2 && (
        <Card t={t}>
          <div style={{ textAlign: "center", maxWidth: 420, margin: "0 auto" }}>
            {/* Icon */}
            <div style={{ width: 64, height: 64, borderRadius: 18, background: `${t.blue}14`, border: `1px solid ${t.blue}22`, display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 20px" }}>
              <span style={{ fontSize: 28 }}>📱</span>
            </div>

            <h3 style={{ fontSize: 16, fontWeight: 800, color: t.text, margin: "0 0 8px" }}>Verify your phone number</h3>
            <p style={{ fontSize: 13, color: t.sub, margin: "0 0 6px", lineHeight: 1.7 }}>
              We'll send a 6-digit OTP to <strong style={{ color: t.text }}>+91 {phone}</strong> via WhatsApp.
            </p>
            <p style={{ fontSize: 12, color: t.muted, margin: "0 0 28px" }}>
              Your verified number will appear on the legal certificate.
            </p>

            {!otpSent && !otpVerified && (
              <Btn onClick={sendOtp} disabled={otpLoading} loading={otpLoading} t={t}>
                <span>📲</span>
                {otpLoading ? "Sending…" : "Send OTP via WhatsApp"}
              </Btn>
            )}

            {otpSent && !otpVerified && (
              <div style={{ animation: "fadeUp 0.3s ease" }}>
                <div style={{ padding: "12px 16px", borderRadius: 10, background: "#052e1c", border: "1px solid #34d39933", marginBottom: 24, fontSize: 13, color: "#34d399" }}>
                  ✓ OTP sent to WhatsApp. Check your messages.
                </div>

                <OTPInput value={otpValue} onChange={setOtpValue} t={t} />

                <div style={{ display: "flex", justifyContent: "center", alignItems: "center", gap: 8, margin: "16px 0" }}>
                  <span style={{ fontSize: 12, color: t.muted }}>Expires in</span>
                  {!otpExpired
                    ? <Countdown seconds={600} onExpire={() => setOtpExpired(true)} t={t} />
                    : <span style={{ fontSize: 12, color: t.red || "#f56565", fontWeight: 700 }}>Expired</span>
                  }
                </div>

                {err && <ErrBox msg={err} t={t} />}

                <div style={{ display: "flex", gap: 10, justifyContent: "center", flexWrap: "wrap" }}>
                  <Btn onClick={verifyOtp} disabled={otpValue.length !== 6 || verifyLoading || otpExpired} loading={verifyLoading} t={t}>
                    Verify OTP
                  </Btn>
                  <button onClick={sendOtp} disabled={otpLoading} style={{ background: "none", border: `1.5px solid ${t.border}`, borderRadius: 8, cursor: "pointer", color: t.sub, fontSize: 13, fontFamily: "inherit", fontWeight: 600, padding: "10px 18px" }}>
                    Resend OTP
                  </button>
                </div>
              </div>
            )}

            {otpVerified && (
              <div style={{ animation: "fadeUp 0.3s ease", padding: "16px 20px", borderRadius: 12, background: "#052e1c", border: "1.5px solid #34d39944", display: "flex", alignItems: "center", gap: 12, justifyContent: "center" }}>
                <span style={{ fontSize: 20 }}>✅</span>
                <span style={{ fontSize: 14, fontWeight: 800, color: "#34d399" }}>Phone verified successfully</span>
              </div>
            )}
          </div>

          <div style={{ display: "flex", gap: 10, marginTop: 28 }}>
            <button onClick={() => setStep(1)} style={{ background: "none", border: `1.5px solid ${t.border}`, borderRadius: 8, cursor: "pointer", color: t.sub, fontSize: 13, fontFamily: "inherit", fontWeight: 600, padding: "10px 20px" }}>← Back</button>
            {!otpVerified && (
              <button onClick={() => { setOtpVerified(true); setStep(3); }} style={{ background: "none", border: "none", cursor: "pointer", color: t.muted, fontSize: 12, fontFamily: "inherit" }}>
                Skip verification →
              </button>
            )}
          </div>
        </Card>
      )}

      {/* ── STEP 3: Review ── */}
      {step === 3 && (
        <Card t={t}>
          <h3 style={{ fontSize: 15, fontWeight: 800, color: t.text, margin: "0 0 6px" }}>Review before generating</h3>
          <p style={{ fontSize: 13, color: t.sub, margin: "0 0 20px", lineHeight: 1.7 }}>Check everything carefully — the PDF cannot be edited after generation.</p>

          <div style={{ padding: "20px 22px", borderRadius: 12, border: `2px solid ${t.blue}33`, background: `${t.blue}06`, marginBottom: 20 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 16, paddingBottom: 16, borderBottom: `1px solid ${t.border}` }}>
              <div style={{ width: 32, height: 32, borderRadius: 9, background: `${t.blue}18`, display: "flex", alignItems: "center", justifyContent: "center" }}>
                <Ic d={ICONS.shield} size={14} color={t.blue} />
              </div>
              <div>
                <p style={{ fontSize: 12, fontWeight: 800, color: t.text, margin: 0 }}>ELECTRONIC EVIDENCE CERTIFICATE</p>
                <p style={{ fontSize: 10, color: t.muted, margin: 0 }}>Section 63, Bharatiya Sakshya Adhiniyam 2023</p>
              </div>
              <div style={{ marginLeft: "auto", padding: "3px 10px", borderRadius: 6, background: "#34d39920", border: "1px solid #34d39933", fontSize: 10, fontWeight: 700, color: "#34d399" }}>DRAFT</div>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              <p style={{ fontSize: 10, color: t.muted, fontWeight: 800, textTransform: "uppercase", letterSpacing: "0.07em", margin: "0 0 4px" }}>Complainant</p>
              <CertField label="Name" value={name} t={t} highlight />
              <CertField label="Phone" value={phone + (otpVerified ? " ✓ Verified" : " (unverified)")} t={t} />
              <CertField label="Address" value={address || "Not provided"} t={t} />

              <p style={{ fontSize: 10, color: t.muted, fontWeight: 800, textTransform: "uppercase", letterSpacing: "0.07em", margin: "12px 0 4px" }}>Incident</p>
              <CertField label="Date" value={incDate || "Not specified"} t={t} />
              <CertField label="Description" value={brief} t={t} highlight />
              {policeStation && <CertField label="Police Station" value={policeStation} t={t} />}

              <p style={{ fontSize: 10, color: t.muted, fontWeight: 800, textTransform: "uppercase", letterSpacing: "0.07em", margin: "12px 0 4px" }}>Evidence File</p>
              <CertField label="File Name" value={file?.name} t={t} />
              <CertField label="File Size" value={file ? (file.size / 1024).toFixed(1) + " KB" : ""} t={t} />
              <CertField label="SHA-256" value="Computed at generation time" mono t={t} />
            </div>
          </div>

          {prev && (
            <div style={{ display: "flex", gap: 12, alignItems: "center", padding: "12px 14px", borderRadius: 10, background: t.surfaceUp, border: `1px solid ${t.border}`, marginBottom: 16 }}>
              <img src={prev} alt="evidence" style={{ width: 52, height: 52, objectFit: "cover", borderRadius: 8, border: `1px solid ${t.border}`, flexShrink: 0 }} />
              <div>
                <p style={{ fontSize: 13, fontWeight: 700, color: t.text, margin: "0 0 2px" }}>{file?.name}</p>
                <p style={{ fontSize: 11, color: t.muted, margin: 0 }}>{file ? (file.size / 1024).toFixed(1) + " KB · " + file.type : ""}</p>
              </div>
            </div>
          )}

          {err && <ErrBox msg={err} t={t} />}

          <div style={{ display: "flex", gap: 10 }}>
            <button onClick={() => setStep(2)} style={{ background: "none", border: `1.5px solid ${t.border}`, borderRadius: 8, cursor: "pointer", color: t.sub, fontSize: 13, fontFamily: "inherit", fontWeight: 600, padding: "10px 20px" }}>← Edit</button>
            <Btn onClick={generate} disabled={load} loading={load} t={t}>
              <Ic d={ICONS.shield} size={15} color="#fff" sw={2} />
              {load ? "Computing SHA-256 & generating PDF…" : "Generate Certificate"}
            </Btn>
          </div>
        </Card>
      )}

      {/* ── STEP 4: Certificate ── */}
      {step === 4 && cert && (
        <div style={{ display: "flex", flexDirection: "column", gap: 16, animation: "fadeUp 0.4s ease" }}>
          <div style={{ padding: "16px 20px", borderRadius: 12, background: "#052e1c", border: "1.5px solid #34d39944", display: "flex", alignItems: "center", gap: 14 }}>
            <div style={{ width: 40, height: 40, borderRadius: 10, background: "#34d39920", border: "1px solid #34d39933", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
              <Ic d={ICONS.check} size={18} color="#34d399" sw={2.5} />
            </div>
            <div>
              <p style={{ fontSize: 14, fontWeight: 800, color: "#34d399", margin: "0 0 3px" }}>Certificate Generated</p>
              <p style={{ fontSize: 12, color: "#34d39999", margin: 0 }}>SHA-256 computed · Chain of custody preserved · BSA Section 63 compliant</p>
            </div>
          </div>

          <Card t={t}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 18, paddingBottom: 14, borderBottom: `1px solid ${t.border}` }}>
              <div>
                <p style={{ fontSize: 15, fontWeight: 800, color: t.text, margin: "0 0 3px" }}>Electronic Evidence Certificate</p>
                <p style={{ fontSize: 11, color: t.muted, margin: 0 }}>Section 63, Bharatiya Sakshya Adhiniyam 2023</p>
              </div>
              <div style={{ textAlign: "right" }}>
                <p style={{ fontSize: 12, fontWeight: 700, color: t.blue, margin: "0 0 2px", fontFamily: "monospace" }}>NS-{cert.certificate_id}</p>
                <p style={{ fontSize: 10, color: t.muted, margin: 0 }}>Certificate ID</p>
              </div>
            </div>

            {/* SHA-256 */}
            <div style={{ padding: "14px 16px", borderRadius: 10, background: t.bg, border: `2px solid ${t.blue}33`, marginBottom: 16 }}>
              <p style={{ fontSize: 10, color: t.blue, fontWeight: 800, textTransform: "uppercase", letterSpacing: "0.08em", margin: "0 0 8px" }}>SHA-256 Hash</p>
              <p style={{ fontFamily: "monospace", fontSize: 12, color: t.text, wordBreak: "break-all", margin: 0, lineHeight: 1.7 }}>{hash}</p>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 16 }}>
              <div>
                <p style={{ fontSize: 10, color: t.muted, fontWeight: 800, textTransform: "uppercase", letterSpacing: "0.07em", margin: "0 0 8px" }}>Complainant</p>
                <div style={{ display: "flex", flexDirection: "column", gap: 5 }}>
                  <CertField label="Name" value={cert.complainant_name || name} t={t} highlight />
                  <CertField label="Phone" value={(cert.complainant_phone || phone) + (otpVerified ? " ✓" : "")} t={t} />
                  <CertField label="Address" value={cert.complainant_address || address || "—"} t={t} />
                </div>
              </div>
              <div>
                <p style={{ fontSize: 10, color: t.muted, fontWeight: 800, textTransform: "uppercase", letterSpacing: "0.07em", margin: "0 0 8px" }}>File Details</p>
                <div style={{ display: "flex", flexDirection: "column", gap: 5 }}>
                  <CertField label="File" value={cert.file_name || file?.name} t={t} />
                  <CertField label="Size" value={cert.file_size_bytes ? (cert.file_size_bytes / 1024).toFixed(1) + " KB" : ""} t={t} />
                  <CertField label="Certified" value={cert.certification_timestamp || new Date().toLocaleString("en-IN")} t={t} />
                </div>
              </div>
            </div>

            <div style={{ marginBottom: 16 }}>
              <p style={{ fontSize: 10, color: t.muted, fontWeight: 800, textTransform: "uppercase", letterSpacing: "0.07em", margin: "0 0 8px" }}>Incident</p>
              <div style={{ display: "flex", flexDirection: "column", gap: 5 }}>
                <CertField label="Description" value={cert.incident_brief || brief} t={t} highlight />
                {(cert.incident_date || incDate) && <CertField label="Date" value={cert.incident_date || incDate} t={t} />}
                {(cert.police_station || policeStation) && <CertField label="Police Stn." value={cert.police_station || policeStation} t={t} />}
              </div>
            </div>

            {(cert.device_make || cert.gps_coordinates) && (
              <div style={{ marginBottom: 16 }}>
                <p style={{ fontSize: 10, color: t.muted, fontWeight: 800, textTransform: "uppercase", letterSpacing: "0.07em", margin: "0 0 8px" }}>EXIF Metadata</p>
                <div style={{ display: "flex", flexDirection: "column", gap: 5 }}>
                  {cert.device_make && <CertField label="Device" value={`${cert.device_make} ${cert.device_model || ""}`.trim()} t={t} />}
                  {cert.capture_timestamp && <CertField label="Photo taken" value={cert.capture_timestamp} t={t} />}
                  {cert.gps_coordinates && <CertField label="GPS" value={cert.gps_coordinates} t={t} />}
                </div>
              </div>
            )}

            <div style={{ padding: "12px 16px", borderRadius: 9, background: t.surfaceUp, border: `1px solid ${t.border}` }}>
              <p style={{ fontSize: 11, color: t.muted, fontWeight: 700, margin: "0 0 5px" }}>VERIFY THIS CERTIFICATE</p>
              <code style={{ fontSize: 11, color: t.text, display: "block", padding: "6px 10px", background: t.bg, borderRadius: 6, fontFamily: "monospace", lineHeight: 1.7 }}>
                Linux/Mac: sha256sum {"<filename>"}<br />
                Windows: certutil -hashfile {"<filename>"} SHA256
              </code>
            </div>
          </Card>

          <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
            {(cert.pdf_download_url || cert.pdf_url) && (
              <a href={`http://localhost:8001${cert.pdf_download_url || cert.pdf_url}`} target="_blank" rel="noreferrer" style={{ textDecoration: "none" }}>
                <Btn t={t} onClick={() => {}}>
                  <Ic d={ICONS.external} size={14} color="#fff" sw={2} />
                  Download PDF Certificate
                </Btn>
              </a>
            )}
            <button onClick={reset} style={{ background: "none", border: `1.5px solid ${t.border}`, borderRadius: 8, cursor: "pointer", color: t.sub, fontSize: 13, fontFamily: "inherit", fontWeight: 600, padding: "10px 20px" }}>
              + New Certificate
            </button>
          </div>

          <div style={{ padding: "12px 16px", borderRadius: 10, background: t.amberDim || "#2d1f07", border: `1px solid ${(t.amber || "#fbbf24")}33`, display: "flex", gap: 10 }}>
            <Ic d={ICONS.alert} size={15} color={t.amber || "#fbbf24"} />
            <p style={{ fontSize: 12, color: t.amber || "#fbbf24", margin: 0, lineHeight: 1.7 }}>
              <strong>Important:</strong> Present this certificate with the <strong>original unmodified file</strong> to the investigating officer. Do not crop, edit, or re-save the original.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}