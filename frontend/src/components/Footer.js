import React, { useState } from "react";

// ── Inline SVG icons (no external deps) ───────────────────────────────────────
const TwitterIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
    <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
  </svg>
);

const GithubIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
    <path d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" />
  </svg>
);

const LinkedInIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
    <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 01-2.063-2.065 2.064 2.064 0 112.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z" />
  </svg>
);

const MailIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="2" y="4" width="20" height="16" rx="2" /><path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7" />
  </svg>
);

const PhoneIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.127.96.361 1.903.7 2.81a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0 1 22 16.92z" />
  </svg>
);

const MapPinIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z" /><circle cx="12" cy="10" r="3" />
  </svg>
);

const ArrowRightIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
    <path d="M5 12h14" /><path d="m12 5 7 7-7 7" />
  </svg>
);

const ScalesLogo = () => (
  <svg width="28" height="28" viewBox="0 0 32 32" fill="none">
    <rect x="15.2" y="3.5" width="1.6" height="21" rx="0.8" fill="currentColor" opacity="0.95" />
    <rect x="8" y="24.5" width="16" height="2.2" rx="1.1" fill="currentColor" opacity="0.88" />
    <rect x="5.5" y="26.7" width="21" height="1.4" rx="0.7" fill="currentColor" opacity="0.6" />
    <rect x="3.5" y="7.5" width="25" height="1.8" rx="0.9" fill="currentColor" opacity="0.95" />
    <circle cx="16" cy="4.5" r="2" fill="currentColor" opacity="0.95" />
    <line x1="6.5" y1="9.3" x2="6.5" y2="15.5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" opacity="0.85" />
    <line x1="25.5" y1="9.3" x2="25.5" y2="15.5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" opacity="0.85" />
    <path d="M3 15.5 Q6.5 21.5 10 15.5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" fill="rgba(255,255,255,0.1)" />
    <path d="M22 15.5 Q25.5 21.5 29 15.5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" fill="rgba(255,255,255,0.1)" />
    <line x1="3" y1="15.5" x2="10" y2="15.5" stroke="currentColor" strokeWidth="0.9" opacity="0.35" />
    <line x1="22" y1="15.5" x2="29" y2="15.5" stroke="currentColor" strokeWidth="0.9" opacity="0.35" />
  </svg>
);

// ── Footer Component ─────────────────────────────────────────────────────────
export default function Footer({ t, go }) {
  const [email, setEmail] = useState("");
  const [subscribed, setSubscribed] = useState(false);
  const currentYear = new Date().getFullYear();
  const isDark = t.text === "#ffffff" || t.text === "#f8fafc"; // rough dark-mode detection

  const handleSubscribe = (e) => {
    e.preventDefault();
    if (email.includes("@")) {
      setSubscribed(true);
      setEmail("");
      setTimeout(() => setSubscribed(false), 4000);
    }
  };

  const footerBg = isDark
    ? "linear-gradient(180deg, rgba(9,12,18,0) 0%, rgba(9,12,18,1) 100%)"
    : "linear-gradient(180deg, rgba(248,250,252,0) 0%, rgba(248,250,252,1) 100%)";

  const topBorder = isDark
    ? "linear-gradient(90deg, transparent 0%, rgba(59,130,246,0.3) 20%, rgba(234,88,12,0.3) 80%, transparent 100%)"
    : "linear-gradient(90deg, transparent 0%, rgba(59,130,246,0.15) 20%, rgba(234,88,12,0.15) 80%, transparent 100%)";

  const linkHover = isDark ? "#60a5fa" : "#2563eb";

  const Column = ({ title, children }) => (
    <div style={{ minWidth: 160 }}>
      <h4 style={{
        fontSize: 11,
        fontWeight: 800,
        letterSpacing: "0.12em",
        textTransform: "uppercase",
        color: t.sub,
        margin: "0 0 20px",
        opacity: 0.7
      }}>
        {title}
      </h4>
      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {children}
      </div>
    </div>
  );

  const FooterLink = ({ label, onClick, href, external }) => {
    const baseStyle = {
      color: t.muted || t.sub,
      fontSize: 14,
      fontWeight: 500,
      textDecoration: "none",
      cursor: "pointer",
      transition: "color 0.2s, transform 0.2s",
      display: "inline-flex",
      alignItems: "center",
      gap: 6,
      background: "none",
      border: "none",
      padding: 0,
      fontFamily: "inherit"
    };

    if (external) {
      return (
        <a
          href={href}
          target="_blank"
          rel="noopener noreferrer"
          style={baseStyle}
          onMouseEnter={e => { e.currentTarget.style.color = linkHover; e.currentTarget.style.transform = "translateX(2px)"; }}
          onMouseLeave={e => { e.currentTarget.style.color = t.muted || t.sub; e.currentTarget.style.transform = "translateX(0)"; }}
        >
          {label}
        </a>
      );
    }

    return (
      <button
        onClick={onClick}
        style={baseStyle}
        onMouseEnter={e => { e.currentTarget.style.color = linkHover; e.currentTarget.style.transform = "translateX(2px)"; }}
        onMouseLeave={e => { e.currentTarget.style.color = t.muted || t.sub; e.currentTarget.style.transform = "translateX(0)"; }}
      >
        {label}
      </button>
    );
  };

  return (
    <footer style={{
      marginTop: "auto",
      position: "relative",
      background: t.surface || t.bg
    }}>
      {/* Animated top gradient border */}
      <div style={{
        height: 1,
        background: topBorder,
        opacity: 0.6
      }} />

      {/* Newsletter Band */}
      <div style={{
        padding: "48px 28px 40px",
        background: isDark
          ? "linear-gradient(135deg, rgba(59,130,246,0.06) 0%, rgba(234,88,12,0.04) 100%)"
          : "linear-gradient(135deg, rgba(59,130,246,0.04) 0%, rgba(234,88,12,0.03) 100%)"
      }}>
        <div style={{ maxWidth: 1200, margin: "0 auto", display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 24 }}>
          <div style={{ maxWidth: 420 }}>
            <h3 style={{ fontSize: 22, fontWeight: 800, color: t.text, margin: "0 0 8px", letterSpacing: "-0.02em" }}>
              Stay ahead of legal updates
            </h3>
            <p style={{ fontSize: 14, color: t.sub, margin: 0, lineHeight: 1.6 }}>
              Get weekly briefings on BNS, BNSS & BSA amendments, new case laws, and AI legal tool updates.
            </p>
          </div>

          <form onSubmit={handleSubscribe} style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
            <div style={{ position: "relative" }}>
              <input
                type="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="advocate@nyayasetu.in"
                required
                style={{
                  width: 260,
                  padding: "12px 16px",
                  borderRadius: 10,
                  border: `1px solid ${t.border}`,
                  background: t.bg,
                  color: t.text,
                  fontSize: 14,
                  fontFamily: "inherit",
                  outline: "none"
                }}
              />
            </div>
            <button
              type="submit"
              style={{
                padding: "12px 22px",
                borderRadius: 10,
                border: "none",
                background: "linear-gradient(135deg, #ea580c 0%, #c2410c 100%)",
                color: "#fff",
                fontSize: 14,
                fontWeight: 700,
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                gap: 8,
                transition: "all 0.2s",
                boxShadow: "0 4px 14px rgba(234,88,12,0.3)"
              }}
              onMouseEnter={e => { e.currentTarget.style.transform = "translateY(-1px)"; e.currentTarget.style.boxShadow = "0 6px 20px rgba(234,88,12,0.4)"; }}
              onMouseLeave={e => { e.currentTarget.style.transform = "translateY(0)"; e.currentTarget.style.boxShadow = "0 4px 14px rgba(234,88,12,0.3)"; }}
            >
              {subscribed ? "Subscribed ✓" : "Subscribe"}
              {!subscribed && <ArrowRightIcon />}
            </button>
          </form>
        </div>
      </div>

      {/* Main Footer Content */}
      <div style={{ padding: "56px 28px 40px", maxWidth: 1200, margin: "0 auto" }}>
        <div style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))",
          gap: "40px 32px",
          marginBottom: 48
        }}>
          {/* Brand Column */}
          <div style={{ minWidth: 240, maxWidth: 300 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 16 }}>
              <div style={{
                width: 40, height: 40, borderRadius: 10,
                background: "linear-gradient(150deg, " + (t.blue || "#3b82f6") + " 0%, #0d1e5a 100%)",
                display: "flex", alignItems: "center", justifyContent: "center",
                color: "#fff",
                boxShadow: "0 2px 12px " + (t.blue || "#3b82f6") + "50"
              }}>
                <ScalesLogo />
              </div>
              <div>
                <div style={{ fontSize: 18, fontWeight: 900, color: t.text, letterSpacing: "-0.03em", lineHeight: 1.2 }}>
                  Nyaya<span style={{ color: t.blue || "#3b82f6" }}>Setu</span>
                </div>
                <div style={{ fontSize: 10, fontWeight: 700, color: t.sub, letterSpacing: "0.14em", textTransform: "uppercase" }}>
                  Bridge to Justice
                </div>
              </div>
            </div>
            <p style={{ fontSize: 13, color: t.muted || t.sub, lineHeight: 1.7, margin: "0 0 20px" }}>
              AI-powered legal utilities for Indian citizens. Navigate BNS, BNSS & BSA with confidence. Built for privacy — your data never leaves your device.
            </p>

            {/* Contact mini */}
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 10, fontSize: 13, color: t.sub }}>
                <MailIcon /> <span>contact@nyayasetu.in</span>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 10, fontSize: 13, color: t.sub }}>
                <PhoneIcon /> <span>+91 9007723783</span>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 10, fontSize: 13, color: t.sub }}>
                <MapPinIcon /> <span>New Delhi, India</span>
              </div>
            </div>
          </div>

          {/* Product Column */}
          <Column title="Product">
            <FooterLink label="Document Analyzer" onClick={() => go("analyzer")} />
            <FooterLink label="IPC → BNS Checker" onClick={() => go("compliance")} />
            <FooterLink label="Evidence Certifier" onClick={() => go("evidence")} />
            <FooterLink label="Legal Research" onClick={() => go("research")} />
            <FooterLink label="Drafting Editor" onClick={() => go("editor")} />
            <FooterLink label="Case Law Search" onClick={() => go("caselaws")} />
          </Column>

          {/* Resources Column */}
          <Column title="Resources">
            <FooterLink label="BNS 2023 Guide" href="https://www.indiacode.nic.in/handle/123456789/19443?view_type=browse&sam_handle=123456789/19443" external />
            <FooterLink label="BNSS 2023 Guide" href="https://www.indiacode.nic.in/handle/123456789/19444?view_type=browse&sam_handle=123456789/19444" external />
            <FooterLink label="BSA 2023 Guide" href="https://www.indiacode.nic.in/handle/123456789/19445?view_type=browse&sam_handle=123456789/19445" external />
            <FooterLink label="Supreme Court Judgments" href="https://main.sci.gov.in/judgments" external />
            <FooterLink label="eCourts Services" href="https://ecourts.gov.in/ecourts_home/" external />
          </Column>

          {/* Company Column */}
          <Column title="Company">
            <FooterLink label="Dashboard" onClick={() => go("dashboard")} />
            <FooterLink label="Matters" onClick={() => go("matters")} />
            <FooterLink label="Calendar" onClick={() => go("calendar")} />
            <FooterLink label="Tasks" onClick={() => go("tasks")} />
            <FooterLink label="Billing" onClick={() => go("billing")} />
          </Column>

          {/* Legal Column */}
          <Column title="Legal">
            <FooterLink label="Privacy Policy" onClick={() => go("home")} />
            <FooterLink label="Terms of Service" onClick={() => go("home")} />
            <FooterLink label="Disclaimer" onClick={() => go("home")} />
            <FooterLink label="Data Security" onClick={() => go("home")} />
          </Column>
        </div>

        {/* Bottom Bar */}
        <div style={{
          borderTop: `1px solid ${t.border}`,
          paddingTop: 24,
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: 16
        }}>
          <div style={{ fontSize: 12, color: t.muted || t.sub, fontWeight: 500 }}>
            © {currentYear} NyayaSetu. All rights reserved. Built with ❤️ for Indian citizens.
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span style={{ fontSize: 11, color: t.muted || t.sub, marginRight: 8, fontWeight: 600, letterSpacing: "0.05em", textTransform: "uppercase" }}>
              Follow
            </span>
            {[
              { icon: <TwitterIcon />, label: "Twitter", href: "https://twitter.com" },
              { icon: <GithubIcon />, label: "GitHub", href: "https://github.com" },
              { icon: <LinkedInIcon />, label: "LinkedIn", href: "https://linkedin.com" },
            ].map((social) => (
              <a
                key={social.label}
                href={social.href}
                target="_blank"
                rel="noopener noreferrer"
                aria-label={social.label}
                style={{
                  width: 36, height: 36, borderRadius: 8,
                  display: "flex", alignItems: "center", justifyContent: "center",
                  color: t.sub,
                  background: isDark ? "rgba(255,255,255,0.03)" : "rgba(0,0,0,0.03)",
                  border: `1px solid ${t.border}`,
                  transition: "all 0.2s",
                  textDecoration: "none"
                }}
                onMouseEnter={e => {
                  e.currentTarget.style.color = t.blue || "#3b82f6";
                  e.currentTarget.style.background = isDark ? "rgba(59,130,246,0.1)" : "rgba(59,130,246,0.08)";
                  e.currentTarget.style.borderColor = (t.blue || "#3b82f6") + "40";
                  e.currentTarget.style.transform = "translateY(-2px)";
                }}
                onMouseLeave={e => {
                  e.currentTarget.style.color = t.sub;
                  e.currentTarget.style.background = isDark ? "rgba(255,255,255,0.03)" : "rgba(0,0,0,0.03)";
                  e.currentTarget.style.borderColor = t.border;
                  e.currentTarget.style.transform = "translateY(0)";
                }}
              >
                {social.icon}
              </a>
            ))}
          </div>
        </div>
      </div>
    </footer>
  );
}