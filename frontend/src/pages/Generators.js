import { useState, useEffect } from "react";
import { PageTitle, Card, Btn, Input, Textarea, Ic, ICONS } from "../components/UI";

const API_BASE = process.env.REACT_APP_API_URL || "http://localhost:8001";

const DOC_TEMPLATES = {
  "Rent Agreement": {
    party_a: "Landlord Name",
    party_b: "Tenant Name",
    fields: [
      { key: "property_address", label: "Property Address", type: "text" },
      { key: "monthly_rent", label: "Monthly Rent (INR)", type: "text" },
      { key: "security_deposit", label: "Security Deposit (INR)", type: "text" },
      { key: "tenure", label: "Tenure (e.g. 11 months)", type: "text" },
      { key: "commencement_date", label: "Start Date", type: "text" },
      { key: "place", label: "Place of Execution", type: "text" },
      { key: "jurisdiction", label: "Court Jurisdiction", type: "text" },
      { key: "other_details", label: "Other Details", type: "textarea" },
    ]
  },
  "Legal Notice": {
    party_a: "Sender Name",
    party_b: "Recipient Name",
    fields: [
      { key: "subject", label: "Subject", type: "text" },
      { key: "cause_of_action", label: "Cause of Action", type: "textarea" },
      { key: "relief_sought", label: "Relief Sought / Demands", type: "textarea" },
      { key: "other_details", label: "Other Details", type: "textarea" },
    ]
  },
  "Affidavit": {
    party_a: "Deponent Name",
    party_b: "N/A (Leave empty or NA)",
    fields: [
      { key: "purpose", label: "Purpose of Affidavit", type: "text" },
      { key: "specific_facts", label: "Specific Facts", type: "textarea" },
    ]
  },
  "Power of Attorney": {
    party_a: "Principal Name",
    party_b: "Attorney Name",
    fields: [
      { key: "purpose", label: "Purpose of POA", type: "text" },
      { key: "duration", label: "Duration", type: "text" },
      { key: "schedule_of_properties", label: "Schedule of Properties", type: "textarea" },
      { key: "other_details", label: "Other Details", type: "textarea" },
    ]
  },
  "Will": {
    party_a: "Testator Name",
    party_b: "Executor Name",
    fields: [
      { key: "bequests", label: "Bequests / Distribution", type: "textarea" },
      { key: "other_details", label: "Other Directions", type: "textarea" },
    ]
  },
  "Partnership Deed": {
    party_a: "Partner 1 Name",
    party_b: "Partner 2 Name",
    fields: [
      { key: "business_object", label: "Business Object", type: "textarea" },
      { key: "business_address", label: "Business Address", type: "text" },
      { key: "capital_a", label: "Capital Contribution (Partner 1)", type: "text" },
      { key: "capital_b", label: "Capital Contribution (Partner 2)", type: "text" },
      { key: "other_details", label: "Other Details", type: "textarea" },
    ]
  }
};

export default function Generators({ t, toast }) {
  const [token] = useState(localStorage.getItem("ns_token"));
  const [loading, setLoading] = useState(false);
  const [docType, setDocType] = useState("Rent Agreement");
  const [form, setForm] = useState({ party_a: "", party_b: "" });
  const [result, setResult] = useState("");
  const [generatedDocType, setGeneratedDocType] = useState("");

  const template = DOC_TEMPLATES[docType];

  useEffect(() => {
    // Reset form when doc type changes
    setForm({ party_a: "", party_b: "" });
    setResult("");
    setGeneratedDocType("");
  }, [docType]);

  const handleGenerate = async () => {
    if (!token) return toast("Please login via Dashboard first", "error");
    if (!form.party_a) return toast("Fill all required fields", "error");

    setLoading(true);
    try {
      // Assemble details payload
      let detailsText = "";
      template.fields.forEach(f => {
        if (form[f.key]) {
          detailsText += `${f.key}: ${form[f.key]}\n`;
        }
      });

      const res = await fetch(`${API_BASE}/api/generate_doc`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "Authorization": `Bearer ${token}` },
        body: JSON.stringify({
          doc_type: docType,
          party_a: form.party_a,
          party_b: form.party_b || "NA",
          details: detailsText
        })
      });
      const data = await res.json();
      if (res.ok) {
        setResult(data.content);
        setGeneratedDocType(data.doc_type);
        toast("Document Generated", "success");
      } else {
        toast(data.detail || "Error generating document", "error");
      }
    } catch (e) {
      toast("Server Error", "error");
    }
    setLoading(false);
  };

  // ══════════════════════════════════════════════════════════════════════════════
  // OPEN IN EDITOR — Pass generated content to Editor via localStorage
  // ══════════════════════════════════════════════════════════════════════════════
  const handleOpenInEditor = () => {
    if (!result) return;

    // Convert plain text to HTML for the rich text editor
    const htmlContent = convertToEditorHtml(result, generatedDocType);

    // Save to localStorage for Editor to pick up
    const editorPayload = {
      content: htmlContent,
      title: `${generatedDocType} — ${form.party_a} vs ${form.party_b || "N/A"}`,
      documentType: generatedDocType,
      source: "generator",
      timestamp: Date.now(),
      generatorData: {
        docType: generatedDocType,
        partyA: form.party_a,
        partyB: form.party_b,
        formData: { ...form }
      }
    };

    localStorage.setItem("ns_editor_from_generator", JSON.stringify(editorPayload));

    // Navigate to editor — assumes your router uses /editor or similar
    // Adjust this based on your actual routing setup
    window.location.hash = "#/editor";

    toast("Opening in Editor...", "success");
  };

  // Convert generator plain text to Editor-friendly HTML
  const convertToEditorHtml = (text, docType) => {
    // Split by double newlines to create paragraphs
    const paragraphs = text
      .split("\n\n")
      .filter(p => p.trim())
      .map(p => {
        // Check if it's a heading (lines with === or all caps)
        const trimmed = p.trim();
        if (trimmed.startsWith("====") || trimmed.startsWith("----")) {
          return null; // Skip separator lines
        }
        if (/^[A-Z][A-Z\s\/&]+$/.test(trimmed) && trimmed.length < 80) {
          return `<h3>${trimmed}</h3>`;
        }
        // Check for numbered clauses
        if (/^\d+\.\s/.test(trimmed)) {
          return `<p><strong>${trimmed.split(".")[0]}.</strong> ${trimmed.substring(trimmed.indexOf(".") + 1).trim()}</p>`;
        }
        // Regular paragraph
        return `<p>${trimmed.replace(/\n/g, "<br/>")}</p>`;
      })
      .filter(Boolean)
      .join("\n");

    return paragraphs;
  };

  return (
    <div style={{ maxWidth: 1000, margin: "40px auto", padding: "0 20px" }}>
      <PageTitle
        icon="doc"
        title="AI Legal Document Generator"
        desc="Instantly draft Rent Agreements, Legal Notices, and more using structured templates. Open in Editor for advanced formatting, templates, and AI Copilot assistance."
        badge="BETA"
        t={t}
      />

      <div style={{ display: "grid", gridTemplateColumns: "340px 1fr", gap: 24 }}>
        <Card t={t} style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <h3 style={{ margin: "0 0 8px", fontSize: 16, fontWeight: 800 }}>Document Details</h3>

          <select
            value={docType}
            onChange={e => setDocType(e.target.value)}
            style={{
              background: t.surfaceUp,
              border: `1.5px solid ${t.border}`,
              borderRadius: 9,
              padding: "10px 16px",
              color: t.text,
              fontFamily: "inherit",
              fontSize: 14,
              cursor: "pointer"
            }}
          >
            {Object.keys(DOC_TEMPLATES).map(type => (
              <option key={type} value={type}>{type}</option>
            ))}
          </select>

          <Input
            value={form.party_a || ""}
            onChange={e => setForm({ ...form, party_a: e.target.value })}
            placeholder={template.party_a}
            t={t}
          />
          <Input
            value={form.party_b || ""}
            onChange={e => setForm({ ...form, party_b: e.target.value })}
            placeholder={template.party_b}
            t={t}
          />

          <div style={{ height: "1px", background: t.border, margin: "8px 0" }}></div>

          {template.fields.map(f => (
            f.type === "textarea" ? (
              <Textarea
                key={f.key}
                value={form[f.key] || ""}
                onChange={e => setForm({ ...form, [f.key]: e.target.value })}
                placeholder={f.label}
                rows={3}
                t={t}
              />
            ) : (
              <Input
                key={f.key}
                value={form[f.key] || ""}
                onChange={e => setForm({ ...form, [f.key]: e.target.value })}
                placeholder={f.label}
                t={t}
              />
            )
          ))}

          <Btn onClick={handleGenerate} loading={loading} t={t} style={{ width: "100%", justifyContent: "center", marginTop: 8 }}>
            Generate Document
          </Btn>
        </Card>

        <Card t={t} style={{ display: "flex", flexDirection: "column" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}>
            <div>
              <h3 style={{ margin: 0, fontSize: 16, fontWeight: 800 }}>Generated Output</h3>
              {generatedDocType && (
                <div style={{ fontSize: 12, color: t.muted, marginTop: 4 }}>
                  {generatedDocType} • {form.party_a} vs {form.party_b || "N/A"}
                </div>
              )}
            </div>
            <div style={{ display: "flex", gap: 8 }}>
              {result && (
                <>
                  <Btn
                    outline
                    small
                    onClick={() => { navigator.clipboard.writeText(result); toast("Copied!", "success"); }}
                    t={t}
                  >
                    Copy Text
                  </Btn>
                  {/* ══ NEW: Open in Editor Button ══ */}
                  <Btn
                    primary
                    small
                    onClick={handleOpenInEditor}
                    t={t}
                    style={{
                      background: t.blue,
                      color: "white",
                      display: "flex",
                      alignItems: "center",
                      gap: 6
                    }}
                  >
                    <Ic d={ICONS.edit} size={14} color="white" />
                    Open in Editor
                  </Btn>
                </>
              )}
            </div>
          </div>

          <div style={{
            background: t.surfaceUp,
            border: `1.5px solid ${t.border}`,
            borderRadius: 12,
            padding: 20,
            minHeight: 400,
            whiteSpace: "pre-wrap",
            fontFamily: "monospace",
            fontSize: 13,
            lineHeight: 1.6,
            color: result ? t.text : t.sub,
            flex: 1,
            overflow: "auto"
          }}>
            {result || (
              <div style={{ textAlign: "center", paddingTop: 80 }}>
                <Ic d={ICONS.doc} size={48} color={t.border} style={{ marginBottom: 16, opacity: 0.5 }} />
                <div style={{ color: t.muted, fontSize: 14 }}>
                  Your generated document will appear here...
                </div>
                <div style={{ color: t.muted, fontSize: 12, marginTop: 8 }}>
                  Fill the form and click "Generate Document"
                </div>
              </div>
            )}
          </div>

          {result && (
            <div style={{
              marginTop: 12,
              padding: 12,
              background: `${t.blue}0a`,
              border: `1px solid ${t.blue}30`,
              borderRadius: 8,
              display: "flex",
              alignItems: "center",
              gap: 10,
              fontSize: 12,
              color: t.sub
            }}>
              <Ic d={ICONS.info} size={16} color={t.blue} />
              <span>
                <strong style={{ color: t.text }}>Tip:</strong> Click "Open in Editor" to format this document,
                apply court-specific templates, use AI Copilot for clause drafting, and export to PDF/Word.
              </span>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}