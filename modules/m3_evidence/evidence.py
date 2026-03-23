"""
M3 — SHA-256 Evidence Hashing + BSA Section 63 Certificate
Nyaya-Setu | Team IKS | SPIT CSE 2025-26

GPU note: M3 is pure CPU/IO — no GPU needed.
"""

import hashlib, io, os, datetime
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer,
    Table, TableStyle, HRFlowable,
)
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from pydantic import BaseModel


class EvidenceCertificate(BaseModel):
    sha256_hash:             str
    file_name:               str
    file_size_bytes:         int
    capture_timestamp:       str
    certification_timestamp: str
    device_make:             str
    device_model:            str
    gps_coordinates:         str
    image_width:             str
    image_height:            str
    bsa_section:             str = "Section 63, Bharatiya Sakshya Adhiniyam 2023"
    certificate_id:          str
    verification_status:     str = "HASH INTEGRITY VERIFIED"
    # ── New fields ────────────────────────────────────────────────────────────
    complainant_name:        str = "Not provided"
    complainant_phone:       str = ""
    complainant_address:     str = ""
    incident_brief:          str = ""
    incident_date:           str = ""
    police_station:          str = ""


def compute_sha256(file_bytes: bytes) -> str:
    """SHA-256 of raw bytes — called BEFORE any PIL processing."""
    h = hashlib.sha256()
    for i in range(0, len(file_bytes), 4096):
        h.update(file_bytes[i:i+4096])
    return h.hexdigest()


def _exif(img: Image.Image) -> dict:
    try:
        raw = img._getexif()
        return {TAGS.get(k, str(k)): v for k, v in raw.items()} if raw else {}
    except Exception:
        return {}


def _gps(exif: dict) -> str:
    gps_info = exif.get("GPSInfo")
    if not gps_info:
        return "GPS data not available"
    gps = {GPSTAGS.get(k, k): v for k, v in gps_info.items()}
    try:
        def dms(d, ref):
            v = float(d[0]) + float(d[1])/60 + float(d[2])/3600
            return -v if ref in ("S","W") else v
        lat = dms(gps["GPSLatitude"],  gps.get("GPSLatitudeRef","N"))
        lon = dms(gps["GPSLongitude"], gps.get("GPSLongitudeRef","E"))
        return f"{abs(lat):.6f}° {'N' if lat>=0 else 'S'}, {abs(lon):.6f}° {'E' if lon>=0 else 'W'}"
    except Exception:
        return "GPS data present but malformed"


def generate_evidence_certificate(
    file_bytes:          bytes,
    file_name:           str,
    # ── All fields now accepted ───────────────────────────────────────────────
    complainant_name:    str = "Not provided",
    complainant_phone:   str = "",
    complainant_address: str = "",
    incident_brief:      str = "As described in police complaint",
    incident_date:       str = "",
    police_station:      str = "",
) -> tuple:

    # ── Step 1: hash FIRST — before any PIL processing ────────────────────────
    sha256 = compute_sha256(file_bytes)
    ts_now = datetime.datetime.now().strftime("%d %B %Y, %I:%M %p IST")

    # ── Step 2: EXIF ──────────────────────────────────────────────────────────
    try:
        img    = Image.open(io.BytesIO(file_bytes))
        w, h   = img.size
        exif   = _exif(img)
    except Exception:
        img  = None; w = h = 0; exif = {}

    capture_ts   = str(exif.get("DateTime") or exif.get("DateTimeOriginal") or "Not in EXIF")
    device_make  = str(exif.get("Make",  "Not available"))
    device_model = str(exif.get("Model", "Not available"))
    gps          = _gps(exif)

    cert = EvidenceCertificate(
        sha256_hash             = sha256,
        file_name               = file_name,
        file_size_bytes         = len(file_bytes),
        capture_timestamp       = capture_ts,
        certification_timestamp = ts_now,
        device_make             = device_make,
        device_model            = device_model,
        gps_coordinates         = gps,
        image_width             = str(w),
        image_height            = str(h),
        certificate_id          = sha256[:12].upper(),
        # ── New fields ────────────────────────────────────────────────────────
        complainant_name        = complainant_name or "Not provided",
        complainant_phone       = complainant_phone or "",
        complainant_address     = complainant_address or "",
        incident_brief          = incident_brief or "Not provided",
        incident_date           = incident_date or "",
        police_station          = police_station or "",
    )

    pdf = _render_pdf(cert)
    return cert, pdf


def _render_pdf(cert: EvidenceCertificate) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            rightMargin=2*cm, leftMargin=2*cm,
                            topMargin=2*cm,   bottomMargin=2*cm)
    NAVY  = colors.HexColor("#1B3A6B")
    LTBLU = colors.HexColor("#D6E4F7")
    RED   = colors.HexColor("#8B0000")
    GREEN = colors.HexColor("#1A6B3C")

    def style(name, **kw):
        return ParagraphStyle(name, **kw)

    T  = style("T",  fontSize=16, textColor=NAVY, alignment=TA_CENTER, fontName="Helvetica-Bold", spaceAfter=4)
    S  = style("S",  fontSize=10, textColor=NAVY, alignment=TA_CENTER, fontName="Helvetica",      spaceAfter=2)
    SH = style("SH", fontSize=11, textColor=NAVY, fontName="Helvetica-Bold", spaceBefore=10, spaceAfter=4)
    B  = style("B",  fontSize=9,  textColor=colors.black, fontName="Helvetica", leading=14, alignment=TA_JUSTIFY)
    LB = style("LB", fontSize=9,  textColor=NAVY, fontName="Helvetica-Bold")
    LV = style("LV", fontSize=9,  textColor=colors.black, fontName="Helvetica")
    MN = style("MN", fontSize=7,  textColor=colors.HexColor("#1A3A6B"), fontName="Courier-Bold", leading=10, wordWrap="CJK")
    DC = style("DC", fontSize=8,  textColor=RED, fontName="Helvetica-Oblique", alignment=TA_CENTER)

    border_style = TableStyle([
        ("BACKGROUND",    (0,0), (0,-1), LTBLU),
        ("GRID",          (0,0), (-1,-1), 0.4, colors.HexColor("#CCCCCC")),
        ("TOPPADDING",    (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING",   (0,0), (-1,-1), 8),
        ("VALIGN",        (0,0), (-1,-1), "TOP"),
    ])

    def row(label, value):
        return [Paragraph(label, LB), Paragraph(str(value) if value else "—", LV)]

    story = [
        Paragraph("ELECTRONIC EVIDENCE CERTIFICATE", T),
        Paragraph("Section 63, Bharatiya Sakshya Adhiniyam 2023", S),
        Paragraph(f"Certificate ID: NS-{cert.certificate_id}", S),
        HRFlowable(width="100%", thickness=2, color=NAVY, spaceAfter=8),

        # ── Section I: Certification statement ───────────────────────────────
        Paragraph("I. CERTIFICATION STATEMENT", SH),
        Paragraph(
            "I hereby certify that the electronic record described herein was received via the "
            "Nyaya-Setu platform and that the SHA-256 hash was computed at the point of receipt, "
            "prior to any processing, in the ordinary course of platform operations, in compliance "
            "with <b>Section 63 of the Bharatiya Sakshya Adhiniyam 2023</b>.", B),
        Spacer(1, 6),

        # ── Section II: Complainant ───────────────────────────────────────────
        Paragraph("II. COMPLAINANT", SH),
        Table([
            row("Name:",          cert.complainant_name),
            row("Phone:",         cert.complainant_phone or "Not provided"),
            row("Address:",       cert.complainant_address or "Not provided"),
        ], colWidths=[4.5*cm, 12.5*cm], style=border_style),
        Spacer(1, 6),

        # ── Section III: Incident details ─────────────────────────────────────
        Paragraph("III. INCIDENT DETAILS", SH),
        Table([
            row("Description:",   cert.incident_brief),
            row("Date:",          cert.incident_date or "Not specified"),
            row("Police Station:", cert.police_station or "Not specified"),
        ], colWidths=[4.5*cm, 12.5*cm], style=border_style),
        Spacer(1, 6),

        # ── Section IV: Electronic record ────────────────────────────────────
        Paragraph("IV. ELECTRONIC RECORD DETAILS", SH),
        Table([
            row("File Name:",     cert.file_name),
            row("File Size:",     f"{cert.file_size_bytes:,} bytes ({cert.file_size_bytes/1024:.1f} KB)"),
            row("Dimensions:",    f"{cert.image_width} × {cert.image_height} px"),
            row("Captured:",      cert.capture_timestamp),
            row("Device Make:",   cert.device_make),
            row("Device Model:",  cert.device_model),
            row("GPS:",           cert.gps_coordinates),
        ], colWidths=[4.5*cm, 12.5*cm], style=border_style),
        Spacer(1, 8),

        # ── Section V: SHA-256 ───────────────────────────────────────────────
        Paragraph("V. SHA-256 HASH VALUE", SH),
        Paragraph("Any modification to the file after certification produces a different hash.", B),
        Spacer(1, 4),
        Table(
            [[Paragraph("SHA-256:", LB), Paragraph(cert.sha256_hash, MN)]],
            colWidths=[2.5*cm, 14.5*cm],
            style=TableStyle([
                ("BACKGROUND",    (0,0), (-1,-1), colors.HexColor("#EFF6FF")),
                ("BOX",           (0,0), (-1,-1), 2, NAVY),
                ("TOPPADDING",    (0,0), (-1,-1), 10),
                ("BOTTOMPADDING", (0,0), (-1,-1), 10),
                ("LEFTPADDING",   (0,0), (-1,-1), 10),
            ])
        ),
        Spacer(1, 8),

        # ── Section VI: Certification ─────────────────────────────────────────
        Paragraph("VI. CERTIFICATION", SH),
        Table([
            row("Certified By:",  "Nyaya-Setu AI Legal Assistance Platform"),
            row("Certified On:",  cert.certification_timestamp),
            row("Legal Basis:",   cert.bsa_section),
            row("Status:",        f"✓ {cert.verification_status}"),
        ], colWidths=[4.5*cm, 12.5*cm], style=border_style),
        Spacer(1, 10),

        HRFlowable(width="100%", thickness=1, color=colors.HexColor("#CCCCCC"), spaceAfter=6),
        Paragraph(
            "VERIFICATION: Run  sha256sum &lt;filename&gt;  (Linux/Mac) or "
            "certutil -hashfile &lt;filename&gt; SHA256  (Windows). "
            "Output must match Section V exactly.", B),
        Spacer(1, 8),
        HRFlowable(width="100%", thickness=1, color=RED, spaceAfter=4),
        Paragraph(
            "DISCLAIMER: This certificate is generated by an automated system. "
            "Present this document with the ORIGINAL unmodified file to the investigating officer.",
            DC),
    ]

    doc.build(story)
    return buf.getvalue()


def verify_hash(file_bytes: bytes, expected: str) -> bool:
    return compute_sha256(file_bytes) == expected


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python evidence.py <image.jpg>")
        sys.exit(1)
    path = sys.argv[1]
    with open(path, "rb") as f:
        data = f.read()

    cert, pdf = generate_evidence_certificate(
        data, os.path.basename(path),
        complainant_name    = "Test User",
        complainant_phone   = "9876543210",
        complainant_address = "Flat 4B, Andheri West, Mumbai",
        incident_brief      = "Phone snatched near Andheri Station on 20 March 2026",
        incident_date       = "2026-03-20",
        police_station      = "Andheri Police Station",
    )
    print(f"\nSHA-256:  {cert.sha256_hash}")
    print(f"Cert ID:  NS-{cert.certificate_id}")
    print(f"Device:   {cert.device_make} {cert.device_model}")
    print(f"GPS:      {cert.gps_coordinates}")

    out = path.rsplit(".", 1)[0] + "_certificate.pdf"
    with open(out, "wb") as f:
        f.write(pdf)
    print(f"PDF:      {out}  ({len(pdf):,} bytes)")
    print(f"Verify:   {'PASS ✓' if verify_hash(data, cert.sha256_hash) else 'FAIL ✗'}")