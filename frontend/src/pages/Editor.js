import React, { useState, useRef, useEffect, useMemo, useCallback } from "react";
import ReactQuill from "react-quill";
import "react-quill/dist/quill.snow.css";
import { Ic, ICONS } from "../components/UI";

// ── QUILL CUSTOM REGISTRATIONS ───────────────────────────────────────────────
const Quill = ReactQuill.Quill;

const Font = Quill.import("attributors/style/font");
Font.whitelist = [
  "times-new-roman", "arial", "georgia", "garamond",
  "courier-new", "verdana", "helvetica", "calibri",
  "book-antiqua", "cambria", "roboto", "open-sans"
];
Quill.register(Font, true);

const Size = Quill.import("attributors/style/size");
Size.whitelist = [
  "10px", "11px", "12px", "13px", "14px", "16px",
  "18px", "20px", "22px", "24px", "28px", "32px", "36px", "48px"
];
Quill.register(Size, true);

const Parchment = Quill.import("parchment");
const LineHeightStyle = new Parchment.Attributor.Style("lineheight", "line-height", {
  scope: Parchment.Scope.BLOCK,
  whitelist: ["1", "1.15", "1.5", "1.75", "2", "2.5"]
});
Quill.register(LineHeightStyle, true);

const BlockEmbed = Quill.import("blots/block/embed");
class PageBreakBlot extends BlockEmbed {
  static create() {
    const node = super.create();
    node.setAttribute("contenteditable", "false");
    node.innerHTML = `<div style="page-break-after: always; height: 0; border-top: 2px dashed #ccc; margin: 20px 0; text-align: center; color: #999; font-size: 12px;">&#9472;&#9472;&#9472; Page Break &#9472;&#9472;&#9472;</div>`;
    return node;
  }
  static value() { return "page-break"; }
}
PageBreakBlot.blotName = "pageBreak";
PageBreakBlot.tagName = "div";
PageBreakBlot.className = "ql-page-break";
Quill.register(PageBreakBlot, true);

const API_BASE = process.env.REACT_APP_API_URL || "http://localhost:8001";

const TEMPLATES_DATA = [
  {
    category: "Supreme Court",
    desc: "SLPs, Civil Appeals, Art. 32 Writs, Review & Curative",
    count: "6 templates",
    icon: "book",
    items: [
      { name: "Art. 32 Petition", desc: "Supreme Court writ for enforcement of fundamental rights", content: `<h3 style='text-align: center; margin-bottom: 0'>IN THE SUPREME COURT OF INDIA</h3><p style='text-align: center; font-weight: bold'>WRIT PETITION (CIVIL/CRIMINAL) NO. _____ OF 2026</p><br/><p>IN THE MATTER OF:</p><p><strong>{{PETITIONER_NAME}}</strong>,<br/>S/o / D/o ___________,<br/>Aged about ___ years,<br/>Resident of ___________</p><p style='text-align: right; font-weight: bold'>...PETITIONER</p><p style='text-align: center; font-weight: bold'>VERSUS</p><p>1. State of ___________<br/>&nbsp;&nbsp;&nbsp;Through its Secretary,<br/>&nbsp;&nbsp;&nbsp;Department of ___________<br/>2. <strong>{{RESPONDENT_NAME}}</strong></p><p style='text-align: right; font-weight: bold'>...RESPONDENTS</p><br/><p style='text-align: center; font-weight: bold; text-decoration: underline'>WRIT PETITION UNDER ARTICLE 32 OF THE CONSTITUTION OF INDIA</p><br/><p><strong>MOST RESPECTFULLY SHOWETH:</strong></p><p>That the present Writ Petition is being filed under Article 32 of the Constitution of India seeking issuance of appropriate writ(s) against arbitrary and illegal action of the Respondents.</p><p>That the Petitioner is a law-abiding citizen and is aggrieved by the order dated __/__/____ passed by Respondent No. ___, the details whereof are already part of the official record maintained by the Respondent authority.</p><br/><p><strong>SYNOPSIS &amp; LIST OF DATES:</strong></p><p>[To be filled with chronological summary of events]</p><br/><p><strong>FACTS IN BRIEF:</strong></p><p>That on __/__/____, the Petitioner applied for ___________, which application was duly acknowledged and recorded in the Respondent's internal system.</p><p>That despite repeated representations, no action was taken, compelling the Petitioner to approach this Hon'ble Court.</p><br/><p><strong>GROUNDS:</strong></p><p>A. Because the impugned action is arbitrary and violative of Article 14 of the Constitution of India.</p><p>B. Because principles of natural justice have been grossly violated.</p><p>C. Because the impugned order is without jurisdiction and authority of law.</p><p>D. Because the Petitioner has no other equally efficacious remedy.</p><p>E. Because the balance of convenience lies in favour of the Petitioner.</p><p>F. Because the Petitioner shall suffer irreparable loss if relief is not granted.</p><br/><p><strong>INTERIM RELIEF:</strong></p><p>Pending final disposal, this Hon'ble Court may kindly stay the operation of the impugned order dated __/__/____.</p><br/><p><strong>PRAYER:</strong></p><p>It is therefore most respectfully prayed that this Hon'ble Court may be pleased to:</p><p>a) Issue a writ of Certiorari quashing the impugned order dated __/__/____;</p><p>b) Issue a writ of Mandamus directing the Respondents to ___________;</p><p>c) Grant interim relief as prayed above;</p><p>d) Pass any other order or direction as this Hon'ble Court may deem fit and proper.</p><br/><p><strong>AND FOR THIS ACT OF KINDNESS, THE PETITIONER SHALL EVER PRAY.</strong></p><br/><br/><p style='text-align: right'>Filed by:</p><p style='text-align: right'><strong>[Advocate Name]</strong><br/>Counsel for the Petitioner</p>` },
      { name: "SLP", desc: "Special Leave Petition under Article 136", variables: [{ key: "YEAR", label: "Year", placeholder: "2026" }, { key: "HIGH_COURT_NAME", label: "High Court Name", placeholder: "e.g., Manipur" }, { key: "HC_CASE_NUMBER", label: "High Court Case Number", placeholder: "e.g., W.P.(C) No. 1234/2024" }, { key: "HC_JUDGMENT_DATE", label: "High Court Judgment Date", placeholder: "dd-mm-yyyy" }, { key: "PETITIONER_NAME", label: "Petitioner's Full Name", placeholder: "Enter petitioner's full name" }, { key: "RESPONDENT_NAME", label: "Respondent's Full Name", placeholder: "Enter respondent's full name" }], content: `<h3 style='text-align: center'>IN THE SUPREME COURT OF INDIA</h3><p style='text-align: center'>CIVIL/CRIMINAL APPELLATE JURISDICTION</p><p style='text-align: center; font-weight: bold'>SPECIAL LEAVE PETITION (CIVIL/CRIMINAL) NO. _____ OF {{YEAR}}</p><p style='text-align: center'>(Against the judgment and order dated {{HC_JUDGMENT_DATE}} passed by the Hon'ble High Court of {{HIGH_COURT_NAME}} in {{HC_CASE_NUMBER}})</p><br/><p>IN THE MATTER OF:</p><div style='display: flex; justify-content: space-between;'><p><strong>{{PETITIONER_NAME}}</strong></p><p style='font-weight: bold'>...PETITIONER(S)</p></div><p style='text-align: center; font-weight: bold'>VERSUS</p><div style='display: flex; justify-content: space-between;'><p><strong>{{RESPONDENT_NAME}}</strong></p><p style='font-weight: bold'>...RESPONDENT(S)</p></div><br/><p style='text-align: center; font-weight: bold; text-decoration: underline'>SPECIAL LEAVE PETITION UNDER ARTICLE 136 OF THE CONSTITUTION OF INDIA</p><br/><p><strong>SYNOPSIS &amp; LIST OF DATES:</strong></p><p>[Chronological summary of the case to be inserted]</p><br/><p><strong>QUESTIONS OF LAW:</strong></p><p>The following substantial questions of law arise for consideration:</p><p>1. Whether the High Court erred in law in holding that _________?</p><p>2. Whether the impugned order is contrary to settled principles of law?</p><br/><p><strong>GROUNDS:</strong></p><p>A. Because the impugned judgment suffers from manifest error of law apparent on the face of the record.</p><p>B. Because the High Court failed to appreciate the settled legal position.</p><p>C. Because the impugned order results in grave miscarriage of justice.</p><br/><p><strong>PRAYER:</strong></p><p>In view of the above, it is most respectfully prayed that this Hon'ble Court may:</p><p>(a) Grant special leave to appeal against the impugned judgment;</p><p>(b) Set aside the impugned judgment and order;</p><p>(c) Pass such other order(s) as this Hon'ble Court may deem fit.</p>` },
      { name: "SLP (Civil)", desc: "Appeal to Supreme Court in civil matters under Article 136", variables: [{ key: "YEAR", label: "Year", placeholder: "2026" }, { key: "HIGH_COURT_NAME", label: "High Court Name", placeholder: "e.g., Uttarakhand" }, { key: "HC_CASE_NUMBER", label: "High Court Case Number", placeholder: "e.g., W.P.(C) No. 1234/2024" }, { key: "HC_JUDGMENT_DATE", label: "High Court Judgment Date", placeholder: "dd-mm-yyyy" }, { key: "PETITIONER_NAME", label: "Petitioner's Full Name", placeholder: "Enter petitioner's full name" }, { key: "RESPONDENT_NAME", label: "Respondent's Full Name", placeholder: "Enter respondent's full name" }], content: `<h3 style='text-align: center'>IN THE SUPREME COURT OF INDIA</h3><p style='text-align: center'>CIVIL APPELLATE JURISDICTION</p><p style='text-align: center; font-weight: bold'>SPECIAL LEAVE PETITION (CIVIL) NO. _____ OF {{YEAR}}</p><p style='text-align: center'>(Against the judgment and order dated {{HC_JUDGMENT_DATE}} passed by the High Court of {{HIGH_COURT_NAME}} in {{HC_CASE_NUMBER}})</p><br/><div style='display: flex; justify-content: space-between;'><p><strong>{{PETITIONER_NAME}}</strong></p><p style='font-weight: bold'>...PETITIONER(S)</p></div><p style='text-align: center; font-weight: bold'>VERSUS</p><div style='display: flex; justify-content: space-between;'><p><strong>{{RESPONDENT_NAME}}</strong></p><p style='font-weight: bold'>...RESPONDENT(S)</p></div><br/><p style='text-align: center; font-weight: bold; text-decoration: underline'>SPECIAL LEAVE PETITION UNDER ARTICLE 136 OF THE CONSTITUTION</p><br/><p><strong>SYNOPSIS &amp; LIST OF DATES:</strong></p><p>[Chronological summary of the case]</p><br/><p><strong>QUESTIONS OF LAW:</strong></p><p>1. Whether the High Court erred in law in holding that ___________?</p><p>2. Whether the impugned judgment is contrary to the settled principles?</p><br/><p><strong>GROUNDS:</strong></p><p>A. Because the impugned judgment suffers from manifest error of law.</p><p>B. Because the High Court ignored binding precedents of this Hon'ble Court.</p><p>C. Because the impugned order results in grave miscarriage of justice.</p><br/><p><strong>PRAYER:</strong></p><p>It is most respectfully prayed that this Hon'ble Court may:</p><p>(a) Grant special leave to appeal against the impugned judgment;</p><p>(b) Set aside the impugned judgment and order;</p><p>(c) Pass such other order(s) as deemed fit.</p><br/><p style='text-align: right'>Filed by:</p><p style='text-align: right'><strong>[Advocate-on-Record]</strong></p>` },
      { name: "SLP (Criminal)", desc: "Appeal to Supreme Court in criminal matters under Article 136", variables: [{ key: "YEAR", label: "Year", placeholder: "2026" }, { key: "HIGH_COURT_NAME", label: "High Court Name", placeholder: "e.g., Orissa" }, { key: "HC_CASE_NUMBER", label: "High Court Case Number", placeholder: "e.g., W.P.(C) No. 1234/2024" }, { key: "HC_JUDGMENT_DATE", label: "High Court Judgment Date", placeholder: "dd-mm-yyyy" }, { key: "PETITIONER_NAME", label: "Petitioner's Full Name", placeholder: "Enter petitioner's full name" }, { key: "RESPONDENT_NAME", label: "Respondent's Full Name", placeholder: "e.g., State of Maharashtra" }], content: `<h3 style='text-align: center'>IN THE SUPREME COURT OF INDIA</h3><p style='text-align: center'>CRIMINAL APPELLATE JURISDICTION</p><p style='text-align: center; font-weight: bold'>SPECIAL LEAVE PETITION (CRIMINAL) NO. _____ OF {{YEAR}}</p><p style='text-align: center'>(Against the judgment and order dated {{HC_JUDGMENT_DATE}} passed by the High Court of {{HIGH_COURT_NAME}} in {{HC_CASE_NUMBER}})</p><br/><div style='display: flex; justify-content: space-between;'><p><strong>{{PETITIONER_NAME}}</strong></p><p style='font-weight: bold'>...PETITIONER(S)/ACCUSED</p></div><p style='text-align: center; font-weight: bold'>VERSUS</p><div style='display: flex; justify-content: space-between;'><p><strong>{{RESPONDENT_NAME}}</strong></p><p style='font-weight: bold'>...RESPONDENT(S)</p></div><br/><p style='text-align: center; font-weight: bold; text-decoration: underline'>SPECIAL LEAVE PETITION UNDER ARTICLE 136 OF THE CONSTITUTION</p><br/><p><strong>SYNOPSIS &amp; LIST OF DATES:</strong></p><p>[Chronological summary of the criminal proceedings]</p><br/><p><strong>QUESTIONS OF LAW:</strong></p><p>1. Whether the conviction is sustainable in law?</p><p>2. Whether the High Court erred in appreciating the evidence?</p><br/><p><strong>GROUNDS:</strong></p><p>A. Because the conviction is based on no evidence.</p><p>B. Because the confession was obtained under coercion.</p><p>C. Because mandatory provisions of law were violated.</p><p>D. Because the sentence is disproportionate to the offence.</p><br/><p><strong>PRAYER:</strong></p><p>It is most respectfully prayed that this Hon'ble Court may:</p><p>(a) Grant special leave to appeal;</p><p>(b) Set aside the conviction and sentence;</p><p>(c) In the alternative, reduce the sentence;</p><p>(d) Grant bail pending disposal of the SLP.</p><br/><p style='text-align: right'>Filed by:</p><p style='text-align: right'><strong>[Advocate-on-Record]</strong></p>` },
      { name: "Civil Appeal", desc: "Appeal in civil matters to Supreme Court after leave granted", variables: [{ key: "YEAR", label: "Year", placeholder: "2026" }, { key: "APPELLANT_NAME", label: "Appellant's Full Name", placeholder: "Enter appellant's full name" }, { key: "RESPONDENT_NAME", label: "Respondent's Full Name", placeholder: "Enter respondent's full name" }], content: `<h3 style='text-align: center'>IN THE SUPREME COURT OF INDIA</h3><p style='text-align: center'>CIVIL APPELLATE JURISDICTION</p><p style='text-align: center; font-weight: bold'>CIVIL APPEAL NO. _____ OF {{YEAR}}</p><br/><div style='display: flex; justify-content: space-between;'><p><strong>{{APPELLANT_NAME}}</strong></p><p style='font-weight: bold'>...APPELLANT</p></div><p style='text-align: center; font-weight: bold'>VERSUS</p><div style='display: flex; justify-content: space-between;'><p><strong>{{RESPONDENT_NAME}}</strong></p><p style='font-weight: bold'>...RESPONDENT</p></div><br/><p style='text-align: center; font-weight: bold; text-decoration: underline'>CIVIL APPEAL</p><br/><p>The Appellant above named most respectfully submits:</p><p>Leave having been granted by this Hon'ble Court on __/__/____, the present Civil Appeal is being filed.</p><br/><p><strong>GROUNDS:</strong></p><p>[State grounds for appeal]</p><br/><p><strong>PRAYER:</strong></p><p>It is therefore prayed that this Hon'ble Court may be pleased to allow the appeal and set aside the impugned judgment.</p><br/><p style='text-align: right'>Filed by:</p><p style='text-align: right'><strong>[Advocate-on-Record]</strong></p>` },
      { name: "Curative Petition", desc: "Last remedy in Supreme Court after review dismissed", variables: [{ key: "YEAR", label: "Year", placeholder: "2026" }, { key: "PETITIONER_NAME", label: "Petitioner's Full Name", placeholder: "Enter petitioner's full name" }, { key: "RESPONDENT_NAME", label: "Respondent's Full Name", placeholder: "Enter respondent's full name" }, { key: "REVIEW_PETITION_NUMBER", label: "Review Petition Number", placeholder: "Enter review petition number" }, { key: "ORIGINAL_CASE_NUMBER", label: "Original Case Number", placeholder: "Enter original case number" }], content: `<h3 style='text-align: center'>IN THE SUPREME COURT OF INDIA</h3><p style='text-align: center; font-weight: bold'>CURATIVE PETITION (CIVIL/CRIMINAL) NO. _____ OF {{YEAR}}</p><br/><p style='text-align: center'>IN</p><p style='text-align: center'>REVIEW PETITION NO. {{REVIEW_PETITION_NUMBER}}</p><br/><p style='text-align: center'>IN</p><p style='text-align: center'>{{ORIGINAL_CASE_NUMBER}}</p><br/><div style='display: flex; justify-content: space-between;'><p><strong>{{PETITIONER_NAME}}</strong></p><p style='font-weight: bold'>...PETITIONER</p></div><p style='text-align: center; font-weight: bold'>VERSUS</p><div style='display: flex; justify-content: space-between;'><p><strong>{{RESPONDENT_NAME}}</strong></p><p style='font-weight: bold'>...RESPONDENT</p></div><br/><p style='text-align: center; font-weight: bold; text-decoration: underline'>CURATIVE PETITION</p><br/><p><strong>CERTIFICATION:</strong></p><p>This Petition is accompanied by a certification from a Senior Advocate stating that the case falls within the principles laid down in Rupa Ashok Hurra v. Ashok Hurra (2002) 4 SCC 388.</p><br/><p><strong>GROUNDS:</strong></p><p>That there has been gross miscarriage of justice.</p><p>That principles of natural justice were violated.</p><p>That the judgment was passed without hearing the Petitioner.</p><br/><p><strong>PRAYER:</strong></p><p>It is prayed that this Hon'ble Court may entertain this Curative Petition and set aside the impugned judgment in the interest of justice.</p><br/><p style='text-align: right'>Filed by:</p><p style='text-align: right'><strong>[Advocate-on-Record]</strong></p>` }
    ]
  },
  {
    category: "High Court",
    desc: "Writ Petitions, Bail, Quashing, Revision, Contempt",
    count: "6 templates",
    icon: "doc",
    items: [
      { name: "Writ Petition", desc: "High Court writ for fundamental rights, service matters, govt action challenges", variables: [{ key: "COURT_NAME", label: "High Court Name/Location", placeholder: "e.g., DELHI" }, { key: "PETITIONER_NAME", label: "Petitioner's Full Name", placeholder: "Enter petitioner's full name" }, { key: "RESPONDENT_NAME", label: "Respondent's Full Name", placeholder: "Enter respondent's full name" }], content: `<h3 style='text-align: center; margin-bottom: 0'>IN THE HIGH COURT OF {{COURT_NAME}}</h3><p style='text-align: center'>AT {{COURT_NAME}}</p><p style='text-align: center; font-weight: bold'>WRIT PETITION (CIVIL) NO. _____ OF 2026</p><br/><p>IN THE MATTER OF:</p><p><strong>{{PETITIONER_NAME}}</strong>,<br/>S/o / D/o ___________,<br/>Aged about ___ years,<br/>Resident of ___________</p><p style='text-align: right; font-weight: bold'>...PETITIONER</p><p style='text-align: center; font-weight: bold'>VERSUS</p><p>1. State of ___________<br/>&nbsp;&nbsp;&nbsp;Through its Secretary,<br/>&nbsp;&nbsp;&nbsp;Department of ___________<br/>2. <strong>{{RESPONDENT_NAME}}</strong></p><p style='text-align: right; font-weight: bold'>...RESPONDENTS</p><br/><p style='text-align: center; font-weight: bold; text-decoration: underline'>WRIT PETITION UNDER ARTICLE 226 OF THE CONSTITUTION OF INDIA</p><br/><p><strong>MOST RESPECTFULLY SHOWETH:</strong></p><p>That the present Writ Petition is being filed under Article 226 of the Constitution of India seeking issuance of appropriate writ(s) against arbitrary and illegal action of the Respondents.</p><p>That the Petitioner is a law-abiding citizen and is aggrieved by the order dated __/__/____ passed by Respondent No. ___, the details whereof are already part of the official record maintained by the Respondent authority.</p><br/><p><strong>SYNOPSIS &amp; LIST OF DATES:</strong></p><p>[To be filled with chronological summary of events]</p><br/><p><strong>FACTS IN BRIEF:</strong></p><p>That on __/__/____, the Petitioner applied for ___________, which application was duly acknowledged and recorded in the Respondent's internal system.</p><p>That despite repeated representations, no action was taken, compelling the Petitioner to approach this Hon'ble Court.</p><br/><p><strong>GROUNDS:</strong></p><p>A. Because the impugned action is arbitrary and violative of Article 14 of the Constitution of India.</p><p>B. Because principles of natural justice have been grossly violated.</p><p>C. Because the impugned order is without jurisdiction and authority of law.</p><p>D. Because the Petitioner has no other equally efficacious remedy.</p><p>E. Because the balance of convenience lies in favour of the Petitioner.</p><p>F. Because the Petitioner shall suffer irreparable loss if relief is not granted.</p><br/><p><strong>INTERIM RELIEF:</strong></p><p>Pending final disposal, this Hon'ble Court may kindly stay the operation of the impugned order dated __/__/____.</p><br/><p><strong>PRAYER:</strong></p><p>It is therefore most respectfully prayed that this Hon'ble Court may be pleased to:</p><p>a) Issue a writ of Certiorari quashing the impugned order dated __/__/____;</p><p>b) Issue a writ of Mandamus directing the Respondents to ___________;</p><p>c) Grant interim relief as prayed above;</p><p>d) Pass any other order or direction as this Hon'ble Court may deem fit and proper.</p><br/><p><strong>AND FOR THIS ACT OF KINDNESS, THE PETITIONER SHALL EVER PRAY.</strong></p><br/><br/><p style='text-align: right'>Filed by:</p><p style='text-align: right'><strong>[Advocate Name]</strong><br/>Counsel for the Petitioner</p>` },
      { name: "Writ Appeal", desc: "Appeal against single judge writ petition order", variables: [{ key: "YEAR", label: "Year", placeholder: "2026" }, { key: "COURT_NAME", label: "High Court Name/Location", placeholder: "e.g., DELHI" }, { key: "APPELLANT_NAME", label: "Appellant's Full Name", placeholder: "Enter appellant's full name" }, { key: "RESPONDENT_NAME", label: "Respondent's Full Name", placeholder: "Enter respondent's full name" }, { key: "ORIGINAL_WP_NUMBER", label: "Original Writ Petition Number", placeholder: "e.g., W.P.(C) No. 1234/2024" }, { key: "IMPUGNED_ORDER_DATE", label: "Impugned Order Date", placeholder: "dd-mm-yyyy" }], content: `<h3 style='text-align: center'>IN THE HIGH COURT OF {{COURT_NAME}}</h3><p style='text-align: center'>AT {{COURT_NAME}}</p><p style='text-align: center; font-weight: bold'>WRIT APPEAL NO. _____ OF {{YEAR}}</p><p style='text-align: center'>(Against the order dated {{IMPUGNED_ORDER_DATE}} in {{ORIGINAL_WP_NUMBER}})</p><br/><div style='display: flex; justify-content: space-between;'><p><strong>{{APPELLANT_NAME}}</strong>,</p><p style='font-weight: bold'>...APPELLANT</p></div><p style='text-align: center; font-weight: bold'>VERSUS</p><div style='display: flex; justify-content: space-between;'><p><strong>{{RESPONDENT_NAME}}</strong></p><p style='font-weight: bold'>...RESPONDENT</p></div><br/><p style='text-align: center; font-weight: bold; text-decoration: underline'>WRIT APPEAL UNDER CLAUSE 15 OF LETTERS PATENT</p><br/><p><strong>MOST RESPECTFULLY SHOWETH:</strong></p><br/><p><strong>IMPUGNED ORDER:</strong></p><p>That the learned Single Judge was pleased to pass the impugned order dated {{IMPUGNED_ORDER_DATE}} dismissing/allowing the Writ Petition No. {{ORIGINAL_WP_NUMBER}}.</p><p>That the Appellant is aggrieved by the said order on the grounds mentioned hereinafter.</p><br/><p><strong>GROUNDS:</strong></p><p>A. Because the learned Single Judge failed to appreciate the facts and law.</p><p>B. Because the impugned order is contrary to settled legal principles.</p><p>C. Because there is error apparent on the face of the record.</p><p>D. Because the order is perverse and against the weight of evidence.</p><br/><p><strong>PRAYER:</strong></p><p>It is therefore prayed that this Hon'ble Court may be pleased to:</p><p>a) Set aside the impugned order dated {{IMPUGNED_ORDER_DATE}};</p><p>b) Allow the Writ Appeal and grant the relief prayed in the original petition;</p><p>c) Pass any other order as deemed fit.</p><br/><p style='text-align: right'>Filed by:</p><p style='text-align: right'><strong>[Advocate Name]</strong><br/>Counsel for the Appellant</p>` },
      { name: "Anticipatory Bail", desc: "Pre-arrest bail under Section 438 CrPC / 482 BNSS", variables: [{ key: "YEAR", label: "Year", placeholder: "2026" }, { key: "COURT_NAME", label: "Court Name / State", placeholder: "e.g., DELHI" }, { key: "APPLICANT_NAME", label: "Applicant's Full Name", placeholder: "Enter applicant's full name" }, { key: "FIR_NUMBER", label: "FIR Number (if registered)", placeholder: "Enter fir number" }, { key: "POLICE_STATION", label: "Police Station", placeholder: "Enter police station" }, { key: "SECTIONS", label: "Sections", placeholder: "e.g., 302, 120B IPC" }], content: `<h3 style='text-align: center'>IN THE COURT OF SESSIONS / HIGH COURT OF {{COURT_NAME}}</h3><p style='text-align: center'>AT {{COURT_NAME}}</p><p style='text-align: center; font-weight: bold'>ANTICIPATORY BAIL APPLICATION NO. _____ OF {{YEAR}}</p><br/><div style='display: flex; justify-content: space-between;'><p><strong>{{APPLICANT_NAME}}</strong></p><p style='font-weight: bold'>...APPLICANT</p></div><p style='text-align: center; font-weight: bold'>VERSUS</p><div style='display: flex; justify-content: space-between;'><p><strong>State of {{COURT_NAME}}</strong></p><p style='font-weight: bold'>...RESPONDENT</p></div><br/><p style='text-align: center; font-weight: bold; text-decoration: underline'>APPLICATION FOR ANTICIPATORY BAIL UNDER SECTION 438 Cr.P.C.</p><br/><p><strong>CASE DETAILS:</strong></p><p>FIR No.: {{FIR_NUMBER}} (if registered)</p><p>Police Station: {{POLICE_STATION}}</p><p>Sections: {{SECTIONS}}</p><br/><p>The Applicant above named most respectfully submits:</p><br/><p><strong>APPREHENSION OF ARREST:</strong></p><p>That the Applicant has reason to believe that he may be arrested on accusation of having committed a non-bailable offence.</p><p>That the Applicant apprehends arrest due to ___________.</p><br/><p><strong>GROUNDS:</strong></p><p>That the Applicant is innocent and has been falsely implicated.</p><p>That the Applicant has no criminal antecedents.</p><p>That the Applicant has deep roots in society and is not a flight risk.</p><p>That custodial interrogation is not necessary as the Applicant is ready to cooperate with investigation.</p><p>That the Applicant undertakes to join investigation as and when required.</p><br/><p><strong>PRAYER:</strong></p><p>It is therefore most respectfully prayed that this Hon'ble Court may be pleased to grant anticipatory bail to the Applicant, and in the event of arrest, he be released on bail.</p><br/><br/><p style='text-align: right'>Filed by:</p><p style='text-align: right'><strong>APPLICANT</strong><br/>Through Counsel</p>` },
      { name: "482 CrPC Petition", desc: "FIR quashing, abuse of process", variables: [{ key: "YEAR", label: "Year", placeholder: "2026" }, { key: "COURT_NAME", label: "Court Name / State", placeholder: "e.g., DELHI" }, { key: "PETITIONER_NAME", label: "Petitioner's Full Name", placeholder: "Enter petitioner's full name" }, { key: "FIR_NUMBER", label: "FIR Number", placeholder: "Enter fir number" }, { key: "POLICE_STATION", label: "Police Station", placeholder: "Enter police station" }, { key: "SECTIONS", label: "Sections", placeholder: "Enter sections" }, { key: "FIR_DATE", label: "FIR Date", placeholder: "dd-mm-yyyy" }], content: `<h3 style='text-align: center'>IN THE HIGH COURT OF {{COURT_NAME}}</h3><p style='text-align: center'>AT {{COURT_NAME}}</p><p style='text-align: center; font-weight: bold'>CRIMINAL PETITION NO. _____ OF {{YEAR}}</p><p style='text-align: center'>(Under Section 482 of the Code of Criminal Procedure, 1973)</p><br/><div style='display: flex; justify-content: space-between;'><p><strong>{{PETITIONER_NAME}}</strong></p><p style='font-weight: bold'>...PETITIONER</p></div><p style='text-align: center; font-weight: bold'>VERSUS</p><div style='display: flex; justify-content: space-between;'><p><strong>State of {{COURT_NAME}}</strong></p><p style='font-weight: bold'>...RESPONDENT</p></div><br/><p style='text-align: center; font-weight: bold; text-decoration: underline'>PETITION FOR QUASHING OF FIR / PROCEEDINGS</p><br/><p><strong>IMPUGNED FIR:</strong></p><p>FIR No.: {{FIR_NUMBER}}</p><p>Police Station: {{POLICE_STATION}}</p><p>Sections: {{SECTIONS}}</p><p>Date of FIR: {{FIR_DATE}}</p><br/><p>The Petitioner above named most respectfully submits:</p><p>That the impugned FIR is an abuse of the process of law and has been lodged with mala fide intention to harass the Petitioner.</p><p>That even if the allegations in the FIR are taken at face value, no offence is made out against the Petitioner.</p><p>That the continuation of the proceedings would amount to abuse of the process of law.</p><br/><p><strong>LEGAL GROUNDS:</strong></p><p>That this Hon'ble Court has inherent power under Section 482 Cr.P.C. to quash proceedings to prevent abuse of process or to secure ends of justice.</p><p>That as per the law laid down in Bhajan Lal's case (1992) 1 SCC 335, the FIR is liable to be quashed.</p><br/><p><strong>PRAYER:</strong></p><p>It is therefore most respectfully prayed that this Hon'ble Court may be pleased to:</p><p>a) Quash the impugned FIR No. {{FIR_NUMBER}};</p><p>b) Stay the investigation pending disposal of this petition;</p><p>c) Pass any other order as deemed fit.</p><br/><p style='text-align: right'>Filed by:</p><p style='text-align: right'><strong>Counsel for Petitioner</strong></p>` },
      { name: "Revision Petition", desc: "Against lower court orders in criminal matters", variables: [{ key: "YEAR", label: "Year", placeholder: "2026" }, { key: "COURT_NAME", label: "Court Name / State", placeholder: "e.g., DELHI" }, { key: "PETITIONER_NAME", label: "Petitioner's Full Name", placeholder: "Enter petitioner's full name" }, { key: "IMPUGNED_ORDER_DATE", label: "Impugned Order Date", placeholder: "dd-mm-yyyy" }, { key: "LOWER_COURT_NAME", label: "Lower Court Name", placeholder: "e.g., Additional Sessions Judge, Gurgaon" }, { key: "LOWER_COURT_CASE_NUMBER", label: "Lower Court Case Number", placeholder: "Enter lower court case number" }], content: `<h3 style='text-align: center'>IN THE HIGH COURT OF {{COURT_NAME}}</h3><p style='text-align: center'>AT {{COURT_NAME}}</p><p style='text-align: center; font-weight: bold'>CRIMINAL REVISION PETITION NO. _____ OF {{YEAR}}</p><p style='text-align: center'>(Under Section 397/401 Cr.P.C.)</p><br/><div style='display: flex; justify-content: space-between;'><p><strong>{{PETITIONER_NAME}}</strong></p><p style='font-weight: bold'>...PETITIONER/REVISIONIST</p></div><p style='text-align: center; font-weight: bold'>VERSUS</p><div style='display: flex; justify-content: space-between;'><p><strong>State of {{COURT_NAME}}</strong></p><p style='font-weight: bold'>...RESPONDENT</p></div><br/><p><strong>IMPUGNED ORDER:</strong></p><p>Order dated {{IMPUGNED_ORDER_DATE}} passed by the learned {{LOWER_COURT_NAME}} in {{LOWER_COURT_CASE_NUMBER}}</p><br/><p><strong>GROUNDS:</strong></p><p>That the impugned order is illegal and erroneous in law.</p><p>That the learned Court below failed to appreciate the evidence.</p><br/><p><strong>PRAYER:</strong></p><p>It is prayed that this Hon'ble Court may be pleased to set aside the impugned order.</p><br/><br/><p style='text-align: right'>Filed by:</p><p style='text-align: right'><strong>Counsel for Petitioner</strong></p>` },
      { name: "Review", desc: "Application for review of judgment under Order 47 CPC", variables: [{ key: "YEAR", label: "Year", placeholder: "2026" }, { key: "COURT_NAME", label: "Court Name", placeholder: "e.g., BOMBAY HIGH COURT" }, { key: "PETITIONER_NAME", label: "Petitioner's Full Name", placeholder: "Enter petitioner's full name" }, { key: "RESPONDENT_NAME", label: "Respondent's Full Name", placeholder: "Enter respondent's full name" }, { key: "ORIGINAL_CASE_NUMBER", label: "Original Case Number", placeholder: "Enter original case number" }, { key: "JUDGMENT_DATE", label: "Judgment Date", placeholder: "dd-mm-yyyy" }], content: `<h3 style='text-align: center; text-transform: uppercase'>IN THE {{COURT_NAME}}</h3><p style='text-align: center; font-weight: bold'>REVIEW PETITION NO. _____ OF {{YEAR}}</p><p style='text-align: center'>(In {{ORIGINAL_CASE_NUMBER}})</p><br/><div style='display: flex; justify-content: space-between;'><p><strong>{{PETITIONER_NAME}}</strong></p><p style='font-weight: bold'>...REVIEW PETITIONER</p></div><p style='text-align: center; font-weight: bold'>VERSUS</p><div style='display: flex; justify-content: space-between;'><p><strong>{{RESPONDENT_NAME}}</strong></p><p style='font-weight: bold'>...RESPONDENT</p></div><br/><p style='text-align: center; font-weight: bold; text-decoration: underline'>REVIEW PETITION UNDER ORDER 47 RULE 1 CPC</p><br/><p><strong>BRIEF FACTS:</strong></p><p>That this Hon'ble Court was pleased to pass judgment dated {{JUDGMENT_DATE}} in the above matter.</p><p>That there is an error apparent on the face of the record which warrants review.</p><br/><p><strong>GROUNDS FOR REVIEW:</strong></p><p>A. Discovery of new and important matter or evidence.</p><p>B. Mistake or error apparent on the face of the record.</p><p>C. Any other sufficient reason.</p><br/><p><strong>PRAYER:</strong></p><p>It is prayed that this Hon'ble Court may review and modify/recall the judgment dated {{JUDGMENT_DATE}}.</p><br/><br/><p style='text-align: right'>Filed by:</p><p style='text-align: right'><strong>Counsel for Petitioner</strong></p>` },
      { name: "Contempt Petition", desc: "Petition for initiation of civil/criminal contempt proceedings", variables: [{ key: "YEAR", label: "Year", placeholder: "2026" }, { key: "COURT_NAME", label: "High Court Name / Bench", placeholder: "e.g., DELHI" }, { key: "PETITIONER_NAME", label: "Petitioner's Full Name", placeholder: "Enter petitioner's full name" }, { key: "CONTEMNOR_NAME", label: "Contemnor's Full Name", placeholder: "Enter contemnor's full name" }, { key: "ORIGINAL_CASE_NUMBER", label: "Original Case Number", placeholder: "Enter original case number" }, { key: "ORIGINAL_ORDER_DATE", label: "Original Order Date", placeholder: "dd-mm-yyyy" }], content: `<h3 style='text-align: center'>IN THE HIGH COURT OF {{COURT_NAME}}</h3><p style='text-align: center'>AT {{COURT_NAME}}</p><p style='text-align: center; font-weight: bold'>CONTEMPT PETITION (CIVIL) NO. _____ OF {{YEAR}}</p><br/><p style='text-align: center'>IN</p><p style='text-align: center'>{{ORIGINAL_CASE_NUMBER}}</p><br/><div style='display: flex; justify-content: space-between;'><p><strong>{{PETITIONER_NAME}}</strong></p><p style='font-weight: bold'>...PETITIONER</p></div><p style='text-align: center; font-weight: bold'>VERSUS</p><div style='display: flex; justify-content: space-between;'><p><strong>{{CONTEMNOR_NAME}}</strong></p><p style='font-weight: bold'>...RESPONDENT/CONTEMNOR</p></div><br/><p style='text-align: center; font-weight: bold; text-decoration: underline'>PETITION FOR INITIATION OF CONTEMPT PROCEEDINGS</p><br/><p>The Petitioner above named most respectfully submits:</p><br/><p><strong>ORIGINAL ORDER:</strong></p><p>That this Hon'ble Court was pleased to pass an order dated {{ORIGINAL_ORDER_DATE}} in {{ORIGINAL_CASE_NUMBER}} directing the Respondent to ___________.</p><br/><p><strong>WILFUL DISOBEDIENCE:</strong></p><p>That despite service of the order, the Respondent has wilfully disobeyed and violated the same.</p><p>That the Respondent's conduct amounts to civil contempt as defined under Section 2(b) of the Contempt of Courts Act, 1971.</p><p>That the Petitioner has suffered due to the wilful disobedience of the order.</p><br/><p><strong>PRAYER:</strong></p><p>It is therefore prayed that this Hon'ble Court may be pleased to:</p><p>a) Initiate contempt proceedings against the Respondent;</p><p>b) Punish the Respondent for contempt of court;</p><p>c) Direct compliance with the original order;</p><p>d) Pass any other order as deemed fit.</p><br/><br/><p style='text-align: right'>Filed by:</p><p style='text-align: right'><strong>Counsel for Petitioner</strong></p>` },
      { name: "IA", desc: "Interlocutory Application for interim relief or stay", variables: [{ key: "YEAR", label: "Year", placeholder: "2026" }, { key: "COURT_NAME", label: "High Court Name / Bench", placeholder: "e.g., DELHI" }, { key: "APPLICANT_NAME", label: "Applicant's Full Name", placeholder: "Enter applicant's full name" }, { key: "RESPONDENT_NAME", label: "Respondent's Full Name", placeholder: "Enter respondent's full name" }, { key: "MAIN_CASE_NUMBER", label: "Main Case Number", placeholder: "e.g., W.P.(C) No. 1234/2024" }], content: `<h3 style='text-align: center'>IN THE HIGH COURT OF {{COURT_NAME}}</h3><p style='text-align: center'>AT {{COURT_NAME}}</p><p style='text-align: center; font-weight: bold'>INTERLOCUTORY APPLICATION NO. _____ OF {{YEAR}}</p><br/><p style='text-align: center'>IN</p><p style='text-align: center'>WRIT PETITION / SUIT NO. {{MAIN_CASE_NUMBER}}</p><br/><div style='display: flex; justify-content: space-between;'><p><strong>{{APPLICANT_NAME}}</strong></p><p style='font-weight: bold'>...APPLICANT</p></div><p style='text-align: center; font-weight: bold'>VERSUS</p><div style='display: flex; justify-content: space-between;'><p><strong>{{RESPONDENT_NAME}}</strong></p><p style='font-weight: bold'>...RESPONDENT</p></div><br/><p style='text-align: center; font-weight: bold; text-decoration: underline'>APPLICATION FOR INTERIM RELIEF / STAY</p><br/><p>The Applicant above named most respectfully submits:</p><p>That the main petition/suit is pending adjudication before this Hon'ble Court.</p><p>That irreparable loss and injury shall be caused to the Applicant if interim protection is not granted.</p><p>That the balance of convenience lies in favour of the Applicant.</p><p>That the Applicant has a prima facie case in his favour.</p><p>That this application is being filed bona fide and in the interest of justice.</p><br/><p><strong>PRAYER:</strong></p><p>It is therefore most respectfully prayed that this Hon'ble Court may kindly:</p><p>a) Stay the operation of the impugned order/action till final disposal of the main petition;</p><p>b) Grant ad-interim relief pending notice;</p><p>c) Pass any other order as deemed fit.</p><br/><br/><p style='text-align: right'>Filed by:</p><p style='text-align: right'><strong>Counsel for Applicant</strong></p>` }
    ]
  },
  {
    category: "District / Sessions Court",
    desc: "Civil Suits, Bail Applications, Written Statements, IAs",
    count: "4 templates",
    icon: "grid",
    items: [
      { name: "Plaint", desc: "Original suit for civil matters - recovery, declaration, injunction", variables: [{ key: "COURT_NAME", label: "Court Name", placeholder: "e.g., Civil Judge (Senior Division), Lucknow" }, { key: "YEAR", label: "Year", placeholder: "2026" }, { key: "PLAINTIFF_NAME", label: "Plaintiff's Full Name", placeholder: "Enter plaintiff's full name" }, { key: "DEFENDANT_NAME", label: "Defendant's Full Name", placeholder: "Enter defendant's full name" }, { key: "SUIT_VALUATION", label: "Suit Valuation (Rs.)", placeholder: "Monetary value for court fee calculation" }], content: `<h3 style='text-align: center'>IN THE COURT OF {{COURT_NAME}}</h3><p style='text-align: center; font-weight: bold'>CIVIL SUIT NO. _____ OF {{YEAR}}</p><p style='text-align: right'>Suit valued at Rs. {{SUIT_VALUATION}}/-</p><p style='text-align: right'>Court Fee: Rs. ___/-</p><br/><div style='display: flex; justify-content: space-between;'><p><strong>{{PLAINTIFF_NAME}}</strong></p><p style='font-weight: bold'>...PLAINTIFF</p></div><p style='text-align: center; font-weight: bold'>VERSUS</p><div style='display: flex; justify-content: space-between;'><p><strong>{{DEFENDANT_NAME}}</strong></p><p style='font-weight: bold'>...DEFENDANT</p></div><br/><p style='text-align: center; font-weight: bold; text-decoration: underline'>SUIT FOR RECOVERY / DECLARATION / INJUNCTION</p><br/><p><strong>JURISDICTION:</strong></p><p>This Hon'ble Court has jurisdiction to try and entertain this suit as the cause of action arose within the territorial jurisdiction of this Court.</p><br/><p><strong>FACTS OF THE CASE:</strong></p><p>That the Plaintiff is the rightful owner/entitled to ___________.</p><p>That the Defendant has wrongfully ___________.</p><p>That despite repeated demands, the Defendant has failed to ___________.</p><br/><p><strong>CAUSE OF ACTION:</strong></p><p>The cause of action arose on __/__/____ when the Defendant ___________.</p><br/><p><strong>RELIEF CLAIMED:</strong></p><p>The Plaintiff prays for:</p><p>(a) Decree for recovery of Rs. ___________/- with interest;</p><p>(b) Costs of the suit;</p><p>(c) Any other relief deemed fit.</p>` },
      { name: "Written Statement", desc: "Defendant's reply to plaint with preliminary objections", variables: [{ key: "YEAR", label: "Year", placeholder: "2026" }, { key: "COURT_NAME", label: "Court Name / Location", placeholder: "e.g., Civil Judge, Delhi" }, { key: "PLAINTIFF_NAME", label: "Plaintiff's Full Name", placeholder: "Enter plaintiff's full name" }, { key: "DEFENDANT_NAME", label: "Defendant's Full Name", placeholder: "Enter defendant's full name" }], content: `<h3 style='text-align: center'>IN THE COURT OF {{COURT_NAME}}</h3><p style='text-align: center'>AT {{COURT_NAME}}</p><p style='text-align: center; font-weight: bold'>CIVIL SUIT NO. _____ OF {{YEAR}}</p><br/><div style='display: flex; justify-content: space-between;'><p><strong>{{PLAINTIFF_NAME}}</strong></p><p style='font-weight: bold'>...PLAINTIFF</p></div><p style='text-align: center; font-weight: bold'>VERSUS</p><div style='display: flex; justify-content: space-between;'><p><strong>{{DEFENDANT_NAME}}</strong></p><p style='font-weight: bold'>...DEFENDANT</p></div><br/><p style='text-align: center; font-weight: bold; text-decoration: underline'>WRITTEN STATEMENT ON BEHALF OF THE DEFENDANT</p><br/><p>The Defendant above named most respectfully submits as under:</p><br/><p><strong>PRELIMINARY OBJECTIONS:</strong></p><p>That the present suit is not maintainable in its present form.</p><p>That this Hon'ble Court has no jurisdiction to try the suit.</p><p>That the suit is barred by limitation.</p><p>That the Plaintiff has no locus standi to file the present suit.</p><p>That the suit is bad for non-joinder/mis-joinder of necessary parties.</p><br/><p><strong>PARA-WISE REPLY:</strong></p><p>The contents of para 1 of the plaint are denied. [Or: admitted/not admitted/matter of record]</p><p>The contents of para 2 of the plaint are denied.</p><p>The contents of para 3 of the plaint are denied.</p><br/><p><strong>ADDITIONAL PLEAS:</strong></p><p>That the Defendant is the rightful owner of ___________.</p><p>That the Plaintiff's claim is false and frivolous.</p><br/><p><strong>PRAYER:</strong></p><p>It is therefore prayed that this Hon'ble Court may be pleased to dismiss the suit with costs.</p><br/><br/><p style='text-align: right'>Filed by:</p><p style='text-align: right'><strong>DEFENDANT</strong><br/>Through Counsel</p>` },
      { name: "IA", desc: "Application for stay, injunction, amendment, documents", content: `<h3 style='text-align: center'>IN THE COURT OF CIVIL JUDGE, ________</h3><p style='text-align: center'>INTERLOCUTORY APPLICATION NO. _____ IN CIVIL SUIT NO. _____ OF 20__</p><br/><p>IN THE MATTER OF:</p><p>[Plaintiff Name] ... Plaintiff</p><p>VERSUS</p><p>[Defendant Name] ... Defendant</p><br/><p><strong>APPLICATION UNDER ORDER XXXIX RULE 1 & 2 CPC FOR AD-INTERIM INJUNCTION.</strong></p>` },
      { name: "Bail", desc: "Application for regular bail in criminal matters", variables: [{ key: "COURT_NAME", label: "Court Name", placeholder: "e.g., Sessions Judge, Patiala House Courts" }, { key: "ACCUSED_NAME", label: "Accused's Full Name", placeholder: "Enter accused's full name" }, { key: "FIR_NUMBER", label: "FIR Number", placeholder: "e.g., 123/2024" }, { key: "POLICE_STATION", label: "Police Station", placeholder: "Enter police station" }, { key: "SECTIONS_CHARGED", label: "Sections Charged", placeholder: "e.g., 420, 467, 468 IPC" }], content: `<h3 style='text-align: center'>IN THE COURT OF {{COURT_NAME}}</h3><p style='text-align: center; font-weight: bold; text-decoration: underline'>BAIL APPLICATION</p><br/><p>In the matter of FIR No. {{FIR_NUMBER}}</p><p>P.S. {{POLICE_STATION}}</p><p>Under Sections {{SECTIONS_CHARGED}}</p><br/><div style='display: flex; justify-content: space-between;'><p><strong>{{ACCUSED_NAME}}</strong></p><p style='font-weight: bold'>...APPLICANT/ACCUSED</p></div><p style='text-align: center; font-weight: bold'>VERSUS</p><div style='display: flex; justify-content: space-between;'><p><strong>State</strong></p><p style='font-weight: bold'>...RESPONDENT</p></div><br/><p><strong>BRIEF FACTS:</strong></p><p>That the applicant has been falsely implicated in the present case.</p><p>That the applicant was arrested on __/__/____ and is in judicial custody since then.</p><p>That the investigation is complete and chargesheet has been filed.</p><br/><p><strong>GROUNDS FOR BAIL:</strong></p><p>A. The applicant is not a flight risk and has deep roots in society.</p><p>B. The applicant is willing to abide by all conditions imposed.</p><p>C. Continued detention is not necessary as investigation is complete.</p><p>D. The applicant has no prior criminal antecedents.</p><br/><p><strong>UNDERTAKING:</strong></p><p>The applicant undertakes to:</p><p>(a) Not tamper with evidence or influence witnesses;</p><p>(b) Appear before the Court on all hearing dates;</p><p>(c) Not leave the jurisdiction without permission.</p><br/><p><strong>PRAYER:</strong></p><p>It is therefore prayed that this Hon'ble Court may be pleased to release the applicant on bail on such terms and conditions as deemed fit.</p><br/><br/><p style='text-align: right'>Filed by:</p><p style='text-align: right'><strong>Counsel for Applicant</strong></p>` }
    ]
  },
  {
    category: "General",
    desc: "Affidavits, Vakalatnama, Court Forms",
    count: "5 templates",
    icon: "file",
    items: [
      { name: "Affidavit", desc: "General purpose affidavit for court proceedings", content: `<h3 style='text-align: center'>AFFIDAVIT</h3><br/><p>I, ________, S/o ________, aged about ________ years, resident of ________, do hereby solemnly affirm and state as under:</p><br/><p>1. That I am the Deponent herein and am fully conversant with the facts and circumstances of the case.</p><p>2. That the contents of the accompanying application are true and correct to the best of my knowledge.</p><br/><br/><p style='text-align: right'><strong>DEPONENT</strong></p><br/><p><strong>VERIFICATION:</strong></p><p>Verified at ________ on this _____ day of ________, 20__, that the contents of the above affidavit are true and correct to my knowledge and nothing material has been concealed therefrom.</p><br/><br/><p style='text-align: right'><strong>DEPONENT</strong></p>` },
      { name: "Counter Affidavit", desc: "Reply affidavit filed by respondent", content: `<h3 style='text-align: center'>BEFORE THE HON'BLE COURT OF ________</h3><br/><p>IN THE MATTER OF:</p><p>[Petitioner Name] ... Petitioner</p><p>VERSUS</p><p>[Respondent Name] ... Respondent</p><br/><p><strong>COUNTER AFFIDAVIT ON BEHALF OF THE RESPONDENT</strong></p><br/><p>I, ________, S/o ________, aged about ________ years, do hereby solemnly affirm and declare as under:</p><p>1. That the averments made in paragraph 1 of the Petition are vehemently denied as false and baseless...</p>` },
      { name: "Rejoinder", desc: "Reply to counter affidavit by petitioner", content: `<h3 style='text-align: center'>BEFORE THE HON'BLE COURT OF ________</h3><br/><p>IN THE MATTER OF:</p><p>[Petitioner Name] ... Petitioner</p><p>VERSUS</p><p>[Respondent Name] ... Respondent</p><br/><p><strong>REJOINDER AFFIDAVIT ON BEHALF OF THE PETITIONER TO THE COUNTER AFFIDAVIT FILED BY THE RESPONDENT</strong></p><br/><p>I, ________, do hereby solemnly affirm and declare as under:</p><p>1. That the contents of the Counter Affidavit are denied, and the contents of the Original Petition are reiterated...</p>` },
      { name: "CA Form 7", desc: "eCourts CA Form 7: application for certified copy from court records", content: `<h3 style='text-align: center'>CA FORM 7</h3><p style='text-align: center'>APPLICATION FOR CERTIFIED COPY</p><br/><p>To,<br/>The Superintendent, Copying Branch,<br/>Court of ________.</p><br/><p>Sir,<br/>Please supply me with a certified copy of the following document(s) in the under-mentioned case:</p><p>Case No: ________</p><p>Parties: ________ vs ________</p><p>Date of Decision/Order: ________</p><p>Document required: ________</p><br/><br/><p style='text-align: right'><strong>Signature of Applicant/Advocate</strong></p>` },
      { name: "Vakalatnama", desc: "Authorization to represent in court proceedings", content: `<h3 style='text-align: center'>VAKALATNAMA</h3><br/><p>IN THE COURT OF ________</p><p>SUIT/APPEAL/PETITION NO. _____ OF 20__</p><br/><p>[Plaintiff/Appellant/Petitioner]</p><p>VERSUS</p><p>[Defendant/Respondent]</p><br/><p>KNOW ALL to whom these present shall come that I/We ________ do hereby appoint ________, Advocate(s) to be my/our Advocate in the above-noted case to appear, act and plead on my/our behalf.</p><br/><p>Date: ________</p><p style='text-align: right'><strong>Client Signature</strong></p><p>ACCEPTED</p><p><strong>Advocate Signature</strong></p>` }
    ]
  }
];

const COPILOT_SYSTEM_LEGAL = `You are NyayaSetu AI — an elite Senior Advocate-level Indian legal drafting assistant with 30+ years of experience across all Indian courts (Supreme Court, High Courts, District Courts, Tribunals).

YOUR EXPERTISE:
- Constitutional Law (Articles 14, 19, 21, 32, 226, 300A)
- Criminal Law (BNS 2023, BNSS 2023, IPC legacy, CrPC)
- Civil Procedure (CPC 1908, Specific Relief Act, Limitation Act)
- Contract Law (Indian Contract Act 1872, Sale of Goods)
- Corporate Law (Companies Act 2013, SEBI, IBC)
- Family Law (HMA 1955, HAMA 1956, DV Act, PWDV Act)
- Labour Law (ID Act, Factories Act, Minimum Wages)
- Property Law (Transfer of Property Act, RERA, Benami Act)
- Tax Law (Income Tax, GST, Customs)
- Evidence Law (BSA 2023, Indian Evidence Act legacy)

DRAFTING RULES:
1. ALWAYS use Indian legal terminology and cite Indian statutes/judgments
2. Format output as clean HTML with proper legal structure (headings, paragraphs, numbered clauses)
3. Use formal legal language: "most respectfully", "whereas", "hereinafter", "aforesaid"
4. Include proper prayer clauses, verification clauses, and signature blocks
5. For court documents: include proper cause title, court header, and party designations
6. Use {{VARIABLE}} syntax for placeholders that need user input
7. NEVER use markdown (** ##) — output clean HTML only
8. Cite relevant sections of BNS 2023 / BNSS 2023 / BSA 2023 where applicable
9. Reference landmark Supreme Court judgments when relevant
10. Ensure all clauses are jurisdiction-appropriate for Indian courts`;

const COPILOT_CLAUSE_PROMPTS = {
  jurisdiction: `Draft a comprehensive GOVERNING LAW AND JURISDICTION clause for an Indian commercial agreement. Include governing law (laws of India), exclusive jurisdiction clause, arbitration reference, waiver of objections, severability. Output as clean HTML paragraphs with proper numbering.`,
  indemnity: `Draft a comprehensive INDEMNITY clause for an Indian commercial contract. Include scope of indemnification, notice and defense of claims, limitation on indemnity, survival clause, third-party claims procedure. Output as clean HTML with numbered sub-clauses.`,
  termination: `Draft a comprehensive TERMINATION clause for an Indian contract. Include termination for convenience, termination for cause/breach, notice period requirements, consequences of termination, survival of obligations, return of confidential information. Output as clean HTML with proper legal formatting.`,
  confidentiality: `Draft a comprehensive CONFIDENTIALITY / NON-DISCLOSURE clause for an Indian agreement. Include definition of confidential information, permitted disclosures, return/destruction of information, duration of confidentiality, remedies for breach, exceptions. Output as clean HTML with numbered paragraphs.`,
  force_majeure: `Draft a comprehensive FORCE MAJEURE clause for an Indian contract. Include definition of force majeure events, notice requirements, suspension of obligations, mitigation duties, termination after prolonged event, exclusions. Output as clean HTML with proper legal structure.`,
  dispute_resolution: `Draft a comprehensive DISPUTE RESOLUTION clause for an Indian commercial agreement. Include negotiation and escalation, mediation, arbitration under Arbitration and Conciliation Act 1996, seat and venue, governing law, confidentiality of proceedings, cost allocation. Output as clean HTML with numbered clauses.`,
  limitation: `Draft a comprehensive LIMITATION OF LIABILITY clause for an Indian contract. Include cap on liability, exclusion of consequential damages, exceptions, insurance requirements, indemnification carve-out. Output as clean HTML with proper legal formatting.`,
  ip_assignment: `Draft a comprehensive INTELLECTUAL PROPERTY ASSIGNMENT clause for an Indian agreement. Include assignment of existing IP, future IP rights, moral rights waiver, registration obligations, warranty of title, infringement indemnity. Output as clean HTML with numbered sub-clauses.`,
  non_compete: `Draft a comprehensive NON-COMPETE / RESTRICTIVE COVENANT clause enforceable under Indian law. Include geographic scope, duration, scope of restricted activities, consideration, blue-pencil severability, remedies for breach. Output as clean HTML with proper legal structure.`,
  warranty: `Draft a comprehensive WARRANTY clause for an Indian commercial contract. Include express warranties, implied warranties disclaimer, warranty period, remedies for breach, limitation on warranties, independent investigation. Output as clean HTML with numbered paragraphs.`
};

export default function Editor({ t, toast }) {
  const [content, setContent] = useState("");
  const [title, setTitle] = useState("Untitled Document");
  const [showTemplates, setShowTemplates] = useState(false);
  const [formTemplate, setFormTemplate] = useState(null);
  const [formData, setFormData] = useState({});
  const [showCopilot, setShowCopilot] = useState(true);
  const [copilotTab, setCopilotTab] = useState("Chat");
  const [selectedCategory, setSelectedCategory] = useState(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [lastSaved, setLastSaved] = useState(null);
  const [wordCount, setWordCount] = useState(0);
  const [charCount, setCharCount] = useState(0);
  const [pageCount, setPageCount] = useState(1);
  const [showFindReplace, setShowFindReplace] = useState(false);
  const [findText, setFindText] = useState("");
  const [replaceText, setReplaceText] = useState("");
  const [showPageSetup, setShowPageSetup] = useState(false);
  const [pageMargins, setPageMargins] = useState({ top: 96, bottom: 96, left: 96, right: 96 });
  const [lineSpacing, setLineSpacing] = useState("1.5");
  const [fontFamily, setFontFamily] = useState("times-new-roman");
  const [fontSize, setFontSize] = useState("16px");
  const [zoom, setZoom] = useState(100);
  const [showClauseMenu, setShowClauseMenu] = useState(false);
  const [showExportMenu, setShowExportMenu] = useState(false);
  const [documentId, setDocumentId] = useState(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [showRuler, setShowRuler] = useState(true);
  const [watermark, setWatermark] = useState("");
  const [showWatermarkModal, setShowWatermarkModal] = useState(false);
  const [documentType, setDocumentType] = useState("Legal Document");
  const [generatorSource, setGeneratorSource] = useState(null);

  const quillRef = useRef(null);
  const fileInputRef = useRef(null);
  const saveTimeoutRef = useRef(null);

  // AI Copilot States
  const [chats, setChats] = useState([
    { role: "assistant", content: "Hello! I'm your AI legal assistant. I can help you with drafting, reviewing, and research. Try asking me to draft specific clauses or review your document." }
  ]);
  const [chatInput, setChatInput] = useState("");
  const [isChatLoading, setIsChatLoading] = useState(false);
  const [copilotMode, setCopilotMode] = useState("general");

  // ══════════════════════════════════════════════════════════════════════════════
  // CHECK FOR GENERATOR CONTENT ON MOUNT
  // ══════════════════════════════════════════════════════════════════════════════
  useEffect(() => {
    const pendingGenerator = localStorage.getItem("ns_editor_from_generator");
    if (pendingGenerator) {
      try {
        const data = JSON.parse(pendingGenerator);
        // Validate it's not stale (older than 5 minutes)
        if (Date.now() - data.timestamp < 300000) {
          setContent(data.content || "");
          setTitle(data.title || "Untitled Document");
          setDocumentType(data.documentType || "Legal Document");
          setGeneratorSource(data.generatorData || null);

          // Show notification about source
          if (data.source === "generator") {
            toast(`Loaded ${data.documentType} from Generator`, "success");
          }
        }
        // Clear the pending data
        localStorage.removeItem("ns_editor_from_generator");
      } catch (e) {
        console.error("Failed to load generator content:", e);
        localStorage.removeItem("ns_editor_from_generator");
      }
    }
  }, []);

  // ── WORD COUNT & STATS ────────────────────────────────────────────────────
  useEffect(() => {
    const text = content.replace(/<[^>]*>/g, " ");
    const words = text.trim().split(/\s+/).filter(w => w.length > 0);
    setWordCount(words.length);
    setCharCount(text.length);
    setPageCount(Math.max(1, Math.ceil(words.length / 500)));
  }, [content]);

  // ── AUTO-SAVE ─────────────────────────────────────────────────────────────
  useEffect(() => {
    if (saveTimeoutRef.current) clearTimeout(saveTimeoutRef.current);
    saveTimeoutRef.current = setTimeout(() => {
      handleAutoSave();
    }, 30000);
    return () => clearTimeout(saveTimeoutRef.current);
  }, [content, title]);

  const handleAutoSave = useCallback(async () => {
    if (!content.trim()) return;
    try {
      const token = localStorage.getItem("token");
      const payload = {
        title,
        content,
        document_type: documentType,
        word_count: wordCount,
        page_count: pageCount
      };
      if (documentId) payload.id = documentId;

      const res = await fetch(`${API_BASE}/api/documents/save`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify(payload)
      });
      if (res.ok) {
        const data = await res.json();
        if (data.id) setDocumentId(data.id);
        setLastSaved(new Date());
      }
    } catch (err) {
      console.log("Auto-save failed:", err);
    }
  }, [content, title, documentId, documentType, wordCount, pageCount]);

  // ── EDITOR CONFIGURATION ─────────────────────────────────────────────────
  const modules = useMemo(() => ({
    toolbar: {
      container: "#ns-toolbar",
      handlers: {
        undo: function () {
          const editor = this.quill;
          editor.history.undo();
        },
        redo: function () {
          const editor = this.quill;
          editor.history.redo();
        },
        pageBreak: function () {
          const editor = this.quill;
          const range = editor.getSelection(true);
          editor.insertEmbed(range.index, "pageBreak", "page-break", Quill.sources.USER);
          editor.setSelection(range.index + 1);
        }
      }
    },
    history: {
      delay: 1000,
      maxStack: 500,
      userOnly: true
    },
    clipboard: {
      matchVisual: false
    }
  }), []);

  const formats = [
    "header", "font", "size", "bold", "italic", "underline", "strike",
    "color", "background", "script", "blockquote", "code-block",
    "list", "bullet", "indent", "direction", "align", "link", "image",
    "video", "formula", "code", "lineheight", "pageBreak"
  ];

  // ── TEMPLATE HANDLING ────────────────────────────────────────────────────
  const handleTemplateSelect = (template) => {
    if (template.variables && template.variables.length > 0) {
      setFormTemplate(template);
      const initialData = {};
      template.variables.forEach(v => initialData[v.key] = "");
      setFormData(initialData);
    } else {
      setContent(template.content);
      setShowTemplates(false);
      toast("Template loaded successfully", "success");
    }
  };

  const handleFormSubmit = (e) => {
    e.preventDefault();
    let finalContent = formTemplate.content;
    Object.keys(formData).forEach(key => {
      const value = formData[key] || `[${key}]`;
      finalContent = finalContent.replace(new RegExp(`{{${key}}}`, 'g'), value);
    });
    setContent(finalContent);
    setFormTemplate(null);
    setShowTemplates(false);
    toast("Template filled and loaded successfully", "success");
  };

  // ── INSERT AI CONTENT ────────────────────────────────────────────────────
  const insertAIContent = useCallback((text) => {
    if (quillRef.current) {
      const editor = quillRef.current.getEditor();
      const range = editor.getSelection(true);
      editor.insertText(range.index, text);
      editor.setSelection(range.index + text.length);
      toast("Clause inserted into document", "success");
    }
  }, [toast]);

  // ── COPILOT CHAT ─────────────────────────────────────────────────────────
  const handleChatSubmit = async (e) => {
    e.preventDefault();
    if (!chatInput.trim()) return;

    const newChat = { role: "user", content: chatInput };
    setChats(prev => [...prev, newChat]);
    setChatInput("");
    setIsChatLoading(true);

    try {
      const systemPrompt = COPILOT_SYSTEM_LEGAL;
      const fullPrompt = `User Request: ${newChat.content}

Current Document Context (use this to match party names, tone, and subject matter):
${content.slice(0, 2000)}

Document Type: ${documentType}

Draft exactly what is requested. Output clean HTML only, no markdown.`;

      const res = await fetch(`${API_BASE}/api/editor/copilot`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          prompt: fullPrompt,
          document_context: content.slice(0, 2000),
          system_prompt: systemPrompt
        })
      });
      const data = await res.json();

      let cleanReply = data.reply || "Sorry, I couldn't generate a response.";
      cleanReply = cleanReply.replace(/\*\*/g, "").replace(/#{1,6}\s/g, "");

      setChats(prev => [...prev, { role: "assistant", content: cleanReply }]);
    } catch (err) {
      toast("Failed to connect to AI Copilot", "error");
      setChats(prev => [...prev, { role: "assistant", content: "Sorry, I encountered an error. Please try again." }]);
    }
    setIsChatLoading(false);
  };

  // ── QUICK CLAUSE GENERATION ────────────────────────────────────────────────
  const generateClause = async (clauseType) => {
    const prompt = COPILOT_CLAUSE_PROMPTS[clauseType];
    if (!prompt) return;

    setChats(prev => [...prev, {
      role: "user",
      content: `Generate ${clauseType.replace(/_/g, " ")} clause`
    }]);
    setIsChatLoading(true);

    try {
      const res = await fetch(`${API_BASE}/api/editor/copilot`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          prompt: prompt,
          document_context: content.slice(0, 2000),
          system_prompt: COPILOT_SYSTEM_LEGAL
        })
      });
      const data = await res.json();
      let cleanReply = data.reply || "Sorry, I couldn't generate the clause.";
      cleanReply = cleanReply.replace(/\*\*/g, "").replace(/#{1,6}\s/g, "");

      setChats(prev => [...prev, { role: "assistant", content: cleanReply }]);
    } catch (err) {
      toast("Failed to generate clause", "error");
      setChats(prev => [...prev, { role: "assistant", content: "Sorry, I encountered an error." }]);
    }
    setIsChatLoading(false);
    setShowClauseMenu(false);
  };

  // ── DOCUMENT ACTIONS ─────────────────────────────────────────────────────
  const handleSave = async () => {
    setIsSaving(true);
    await handleAutoSave();
    setIsSaving(false);
    toast("Document saved", "success");
  };

  const handleExport = (format) => {
    const editor = quillRef.current?.getEditor();
    if (!editor) return;

    const html = editor.root.innerHTML;

    if (format === "html") {
      const fullHtml = `<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><title>${title}</title>
<style>
body { font-family: 'Times New Roman', serif; font-size: 16px; line-height: 1.5; max-width: 816px; margin: 0 auto; padding: 96px; }
h3 { text-align: center; text-transform: uppercase; }
</style>
</head>
<body>${html}</body>
</html>`;
      const blob = new Blob([fullHtml], { type: "text/html" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${title.replace(/\s+/g, "_")}.html`;
      a.click();
      URL.revokeObjectURL(url);
    } else if (format === "txt") {
      const text = editor.getText();
      const blob = new Blob([text], { type: "text/plain" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${title.replace(/\s+/g, "_")}.txt`;
      a.click();
      URL.revokeObjectURL(url);
    } else if (format === "doc") {
      const docHtml = `<html xmlns:o='urn:schemas-microsoft-com:office:office' xmlns:w='urn:schemas-microsoft-com:office:word' xmlns='http://www.w3.org/TR/REC-html40'>
<head><meta charset="UTF-8"><title>${title}</title>
<style>body { font-family: 'Times New Roman', serif; font-size: 16px; }</style>
</head><body>${html}</body></html>`;
      const blob = new Blob([docHtml], { type: "application/msword" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${title.replace(/\s+/g, "_")}.doc`;
      a.click();
      URL.revokeObjectURL(url);
    }
    setShowExportMenu(false);
    toast(`Exported as ${format.toUpperCase()}`, "success");
  };

  const handlePrint = () => {
    const editor = quillRef.current?.getEditor();
    if (!editor) return;
    const printWindow = window.open("", "_blank");
    printWindow.document.write(`
      <!DOCTYPE html>
      <html>
      <head>
        <title>${title}</title>
        <style>
          @page { size: A4; margin: 1in; }
          body { font-family: 'Times New Roman', serif; font-size: 16px; line-height: 1.5; }
          h3 { text-align: center; text-transform: uppercase; }
          .ql-page-break { page-break-after: always; }
        </style>
      </head>
      <body>${editor.root.innerHTML}</body>
      </html>
    `);
    printWindow.document.close();
    printWindow.focus();
    setTimeout(() => printWindow.print(), 500);
  };

  const handleImport = (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      const text = event.target.result;
      if (file.name.endsWith(".html") || file.name.endsWith(".htm")) {
        setContent(text);
      } else {
        const paragraphs = text.split("\n\n").map(p => `<p>${p.replace(/\n/g, "<br/>")}</p>`).join("");
        setContent(paragraphs);
      }
      setTitle(file.name.replace(/\.[^/.]+$/, ""));
      toast("Document imported successfully", "success");
    };
    reader.readAsText(file);
  };

  // ── FIND & REPLACE ────────────────────────────────────────────────────────
  const handleFindReplace = () => {
    if (!findText) return;
    const editor = quillRef.current?.getEditor();
    if (!editor) return;

    const text = editor.getText();
    if (text.includes(findText)) {
      const newText = text.replace(new RegExp(findText, "g"), replaceText);
      editor.setText(newText);
      toast(`Replaced all occurrences of "${findText}"`, "success");
    } else {
      toast(`"${findText}" not found`, "error");
    }
  };

  // ── PAGE SETUP ───────────────────────────────────────────────────────────
  const applyPageSetup = () => {
    const editor = quillRef.current?.getEditor();
    if (!editor) return;

    const editorEl = editor.root;
    editorEl.style.paddingTop = `${pageMargins.top}px`;
    editorEl.style.paddingBottom = `${pageMargins.bottom}px`;
    editorEl.style.paddingLeft = `${pageMargins.left}px`;
    editorEl.style.paddingRight = `${pageMargins.right}px`;
    editorEl.style.lineHeight = lineSpacing;

    toast("Page setup applied", "success");
    setShowPageSetup(false);
  };

  // ── WATERMARK ─────────────────────────────────────────────────────────────
  const applyWatermark = () => {
    const editor = quillRef.current?.getEditor();
    if (!editor) return;

    const editorEl = editor.root;
    if (watermark) {
      editorEl.style.backgroundImage = `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='400' height='200'%3E%3Ctext x='50%25' y='50%25' font-size='48' fill='rgba(200,200,200,0.15)' transform='rotate(-45 200 100)' text-anchor='middle' font-family='Arial'%3E${encodeURIComponent(watermark)}%3C/text%3E%3C/svg%3E")`;
      editorEl.style.backgroundRepeat = "repeat";
    } else {
      editorEl.style.backgroundImage = "none";
    }
    setShowWatermarkModal(false);
    toast(watermark ? "Watermark applied" : "Watermark removed", "success");
  };

  // ── FULLSCREEN ────────────────────────────────────────────────────────────
  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen();
      setIsFullscreen(true);
    } else {
      document.exitFullscreen();
      setIsFullscreen(false);
    }
  };

  // ── KEYBOARD SHORTCUTS ───────────────────────────────────────────────────
  useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "s") {
        e.preventDefault();
        handleSave();
      }
      if ((e.ctrlKey || e.metaKey) && e.key === "p") {
        e.preventDefault();
        handlePrint();
      }
      if ((e.ctrlKey || e.metaKey) && e.key === "f") {
        e.preventDefault();
        setShowFindReplace(true);
      }
      if ((e.ctrlKey || e.metaKey) && e.key === "o") {
        e.preventDefault();
        fileInputRef.current?.click();
      }
      if (e.key === "Escape") {
        setShowFindReplace(false);
        setShowPageSetup(false);
        setShowClauseMenu(false);
        setShowExportMenu(false);
        setShowWatermarkModal(false);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  // ── RENDER ───────────────────────────────────────────────────────────────
  return (
    <div style={{
      display: "flex",
      height: isFullscreen ? "100vh" : "calc(100vh - 60px)",
      overflow: "hidden",
      background: t.bg
    }}>

      <style>{`
        /* ── Editor Wrapper ── */
        .ns-editor-wrapper {
          display: flex;
          flex-direction: column;
          flex: 1;
          height: 100%;
          background: ${t.name === "dark" ? "#1a1a1a" : "#eaecf0"};
          overflow-y: auto;
          scroll-behavior: smooth;
          position: relative;
        }

        /* ── Toolbar ── */
        #ns-toolbar {
          border: none !important;
          border-bottom: 1px solid ${t.border} !important;
          background: ${t.surface};
          padding: 8px 16px;
          display: flex;
          align-items: center;
          gap: 2px;
          flex-wrap: wrap;
          min-height: 48px;
        }
        #ns-toolbar .ql-picker { color: ${t.text}; }
        #ns-toolbar .ql-stroke { stroke: ${t.sub}; }
        #ns-toolbar .ql-fill { fill: ${t.sub}; }
        #ns-toolbar button:hover .ql-stroke { stroke: ${t.blue}; }
        #ns-toolbar .ql-picker-options { background: ${t.surfaceUp}; border-color: ${t.border}; }
        #ns-toolbar button { padding: 4px 6px; }
        #ns-toolbar .ql-formats { margin-right: 8px; }

        /* ── A4 Page Container ── */
        .ql-container.ql-snow {
          border: none !important;
          display: flex;
          justify-content: center;
          padding: 40px 0;
          overflow: visible;
        }
        .ql-editor {
          background: white;
          width: 816px;
          min-height: 1056px;
          padding: 96px;
          box-shadow: 0 4px 16px rgba(0,0,0,0.1);
          color: black;
          font-family: 'Times New Roman', serif;
          font-size: 16px;
          line-height: 1.5;
          border: 1px solid #ddd;
          flex-shrink: 0;
          height: fit-content;
          text-align: left;
          position: relative;
        }
        ${t.name === "dark" ? `
          .ql-editor {
            background: #2d2d2d;
            color: #f0f0f0;
            box-shadow: 0 4px 24px rgba(0,0,0,0.5);
            border: 1px solid #444;
          }
        ` : ""}

        .ql-editor p { margin-bottom: 1em; }
        .ql-editor h3 { text-align: center; font-size: 1.2em; font-weight: bold; margin-bottom: 1.5em; text-transform: uppercase; }

        /* ── Ruler ── */
        .ns-ruler {
          height: 24px;
          background: ${t.surface};
          border-bottom: 1px solid ${t.border};
          display: flex;
          align-items: center;
          padding: 0 40px;
          font-size: 10px;
          color: ${t.muted};
          position: relative;
        }
        .ns-ruler-mark {
          position: absolute;
          bottom: 0;
          width: 1px;
          height: 8px;
          background: ${t.border};
        }

        /* ── Status Bar ── */
        .ns-status-bar {
          height: 28px;
          background: ${t.surface};
          border-top: 1px solid ${t.border};
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 0 16px;
          font-size: 12px;
          color: ${t.sub};
        }

        /* ── Copilot Sidebar ── */
        .ns-copilot {
          width: 400px;
          background: ${t.surface};
          border-left: 1px solid ${t.border};
          display: flex;
          flex-direction: column;
          flex-shrink: 0;
          box-shadow: -4px 0 24px rgba(0,0,0,0.05);
          transition: margin-right 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }
        .ns-copilot.hidden {
          margin-right: -400px;
          border-left-color: transparent;
          box-shadow: none;
        }

        .ns-copilot-tab {
          flex: 1; padding: 12px; text-align: center; font-size: 13px; font-weight: 600;
          cursor: pointer; border-bottom: 2px solid transparent; color: ${t.sub};
          transition: all 0.2s;
        }
        .ns-copilot-tab.active {
          color: ${t.text}; border-bottom-color: ${t.blue};
        }

        .ns-chip {
          padding: 6px 14px; border-radius: 16px; border: 1px solid ${t.border};
          font-size: 12px; color: ${t.sub}; background: ${t.surfaceUp};
          cursor: pointer; white-space: nowrap; transition: all 0.2s;
        }
        .ns-chip:hover { border-color: ${t.blue}; color: ${t.blue}; background: ${t.blue}0a; }

        /* ── Chat Scroll ── */
        .ns-chat-scroll::-webkit-scrollbar { width: 4px; }
        .ns-chat-scroll::-webkit-scrollbar-thumb { background: ${t.border}; border-radius: 4px; }

        /* ── Clause Menu ── */
        .ns-clause-menu {
          position: absolute;
          top: 100%;
          left: 0;
          background: ${t.surface};
          border: 1px solid ${t.border};
          border-radius: 8px;
          box-shadow: 0 8px 24px rgba(0,0,0,0.15);
          z-index: 1000;
          min-width: 220px;
          padding: 8px 0;
        }
        .ns-clause-item {
          padding: 8px 16px;
          font-size: 13px;
          color: ${t.text};
          cursor: pointer;
          transition: background 0.15s;
        }
        .ns-clause-item:hover {
          background: ${t.surfaceUp};
        }

        /* ── Export Menu ── */
        .ns-export-menu {
          position: absolute;
          top: 100%;
          right: 0;
          background: ${t.surface};
          border: 1px solid ${t.border};
          border-radius: 8px;
          box-shadow: 0 8px 24px rgba(0,0,0,0.15);
          z-index: 1000;
          min-width: 160px;
          padding: 8px 0;
        }

        /* ── Modal Overlays ── */
        .ns-modal-overlay {
          position: fixed;
          inset: 0;
          background: rgba(0,0,0,0.5);
          backdrop-filter: blur(4px);
          z-index: 10000;
          display: flex;
          align-items: center;
          justify-content: center;
          padding: 20px;
        }
        .ns-modal {
          background: ${t.surface};
          border-radius: 12px;
          box-shadow: 0 24px 48px rgba(0,0,0,0.2);
          max-width: 500px;
          width: 100%;
          max-height: 90vh;
          overflow: hidden;
          display: flex;
          flex-direction: column;
        }

        /* ── Loading Dots ── */
        @keyframes ns-dot-bounce {
          0%, 80%, 100% { transform: scale(0); }
          40% { transform: scale(1); }
        }
        .ns-dot {
          width: 6px; height: 6px; border-radius: 50%;
          background: ${t.blue};
          display: inline-block;
          animation: ns-dot-bounce 1.4s infinite ease-in-out both;
        }
        .ns-dot:nth-child(1) { animation-delay: -0.32s; }
        .ns-dot:nth-child(2) { animation-delay: -0.16s; }
      `}</style>

      {/* HIDDEN FILE INPUT FOR IMPORT */}
      <input
        type="file"
        ref={fileInputRef}
        style={{ display: "none" }}
        accept=".html,.htm,.txt,.doc,.docx"
        onChange={handleImport}
      />

      {/* ── MAIN EDITOR AREA ── */}
      <div className="ns-editor-wrapper">
        {/* Top Header Bar */}
        <div style={{
          height: 56,
          borderBottom: `1px solid ${t.border}`,
          background: t.surface,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "0 20px",
          flexShrink: 0
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
            <div style={{
              width: 36, height: 36, background: t.surfaceUp, borderRadius: 8,
              display: "flex", alignItems: "center", justifyContent: "center",
              border: `1px solid ${t.border}`
            }}>
              <Ic d={ICONS.doc} size={18} color={t.sub} />
            </div>
            <div>
              <input
                value={title}
                onChange={e => setTitle(e.target.value)}
                style={{
                  background: "transparent", border: "none", fontSize: 17,
                  fontWeight: 700, color: t.text, outline: "none", padding: 0,
                  margin: "0 0 2px", width: 300
                }}
              />
              <div style={{ fontSize: 11, color: t.sub, display: "flex", gap: 8, alignItems: "center" }}>
                <span>{documentType}</span>
                <span>•</span>
                <span>{wordCount} words</span>
                <span>•</span>
                <span>{pageCount} page{pageCount > 1 ? "s" : ""}</span>
                {lastSaved && (
                  <>
                    <span>•</span>
                    <span style={{ color: t.muted }}>Saved {lastSaved.toLocaleTimeString()}</span>
                  </>
                )}
                {generatorSource && (
                  <>
                    <span>•</span>
                    <span style={{
                      color: t.blue,
                      background: `${t.blue}15`,
                      padding: "1px 6px",
                      borderRadius: 4,
                      fontSize: 10,
                      fontWeight: 600
                    }}>
                      From Generator
                    </span>
                  </>
                )}
              </div>
            </div>
          </div>

          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            {/* Templates Button */}
            <button
              onClick={() => setShowTemplates(true)}
              style={{
                display: "flex", alignItems: "center", gap: 6,
                background: t.surfaceUp, border: `1px solid ${t.border}`,
                color: t.text, padding: "6px 14px", borderRadius: 6,
                fontSize: 13, fontWeight: 600, cursor: "pointer",
                transition: "all 0.2s"
              }}
            >
              <Ic d={ICONS.grid} size={14} color={t.text} /> Templates
            </button>

            {/* Clause Generator Dropdown */}
            <div style={{ position: "relative" }}>
              <button
                onClick={() => setShowClauseMenu(!showClauseMenu)}
                style={{
                  display: "flex", alignItems: "center", gap: 6,
                  background: t.surfaceUp, border: `1px solid ${t.border}`,
                  color: t.text, padding: "6px 14px", borderRadius: 6,
                  fontSize: 13, fontWeight: 600, cursor: "pointer"
                }}
              >
                <Ic d={ICONS.book} size={14} color={t.text} /> Clauses
              </button>
              {showClauseMenu && (
                <div className="ns-clause-menu" style={{ background: t.surface }}>
                  <div className="ns-clause-item" onClick={() => generateClause("jurisdiction")}>Governing Law & Jurisdiction</div>
                  <div className="ns-clause-item" onClick={() => generateClause("indemnity")}>Indemnity</div>
                  <div className="ns-clause-item" onClick={() => generateClause("termination")}>Termination</div>
                  <div className="ns-clause-item" onClick={() => generateClause("confidentiality")}>Confidentiality</div>
                  <div className="ns-clause-item" onClick={() => generateClause("force_majeure")}>Force Majeure</div>
                  <div className="ns-clause-item" onClick={() => generateClause("dispute_resolution")}>Dispute Resolution</div>
                  <div className="ns-clause-item" onClick={() => generateClause("limitation")}>Limitation of Liability</div>
                  <div className="ns-clause-item" onClick={() => generateClause("ip_assignment")}>IP Assignment</div>
                  <div className="ns-clause-item" onClick={() => generateClause("non_compete")}>Non-Compete</div>
                  <div className="ns-clause-item" onClick={() => generateClause("warranty")}>Warranty</div>
                </div>
              )}
            </div>

            {/* Import Button */}
            <button
              onClick={() => fileInputRef.current?.click()}
              style={{
                display: "flex", alignItems: "center", gap: 6,
                background: "transparent", border: "none",
                color: t.sub, fontSize: 13, fontWeight: 600, cursor: "pointer"
              }}
            >
              <Ic d={ICONS.download} size={14} color={t.sub} /> Import
            </button>

            {/* Export Dropdown */}
            <div style={{ position: "relative" }}>
              <button
                onClick={() => setShowExportMenu(!showExportMenu)}
                style={{
                  display: "flex", alignItems: "center", gap: 6,
                  background: "transparent", border: "none",
                  color: t.sub, fontSize: 13, fontWeight: 600, cursor: "pointer"
                }}
              >
                Export <Ic d={ICONS.chevronRight} size={12} color={t.sub} />
              </button>
              {showExportMenu && (
                <div className="ns-export-menu" style={{ background: t.surface }}>
                  <div className="ns-clause-item" onClick={() => handleExport("html")}>Export as HTML</div>
                  <div className="ns-clause-item" onClick={() => handleExport("doc")}>Export as Word (.doc)</div>
                  <div className="ns-clause-item" onClick={() => handleExport("txt")}>Export as Text</div>
                  <div className="ns-clause-item" onClick={handlePrint}>Print / PDF</div>
                </div>
              )}
            </div>

            {/* Save Button */}
            <button
              onClick={handleSave}
              disabled={isSaving}
              style={{
                display: "flex", alignItems: "center", gap: 6,
                background: t.blue, border: "none",
                color: "white", padding: "6px 16px", borderRadius: 6,
                fontSize: 13, fontWeight: 600, cursor: "pointer",
                opacity: isSaving ? 0.7 : 1
              }}
            >
              <Ic d={ICONS.file} size={14} color="white" />
              {isSaving ? "Saving..." : "Save"}
            </button>

            <div style={{ width: 1, height: 20, background: t.border, margin: "0 4px" }}></div>

            {/* Print */}
            <button
              onClick={handlePrint}
              title="Print (Ctrl+P)"
              style={{
                width: 32, height: 32, borderRadius: 6,
                background: "transparent", border: "none",
                display: "flex", alignItems: "center", justifyContent: "center",
                cursor: "pointer", color: t.sub
              }}
            >
              <Ic d={ICONS.download} size={16} />
            </button>

            {/* Find/Replace */}
            <button
              onClick={() => setShowFindReplace(true)}
              title="Find & Replace (Ctrl+F)"
              style={{
                width: 32, height: 32, borderRadius: 6,
                background: "transparent", border: "none",
                display: "flex", alignItems: "center", justifyContent: "center",
                cursor: "pointer", color: t.sub
              }}
            >
              <Ic d={ICONS.search} size={16} />
            </button>

            {/* Page Setup */}
            <button
              onClick={() => setShowPageSetup(true)}
              title="Page Setup"
              style={{
                width: 32, height: 32, borderRadius: 6,
                background: "transparent", border: "none",
                display: "flex", alignItems: "center", justifyContent: "center",
                cursor: "pointer", color: t.sub
              }}
            >
              <Ic d={ICONS.grid} size={16} />
            </button>

            {/* Watermark */}
            <button
              onClick={() => setShowWatermarkModal(true)}
              title="Watermark"
              style={{
                width: 32, height: 32, borderRadius: 6,
                background: "transparent", border: "none",
                display: "flex", alignItems: "center", justifyContent: "center",
                cursor: "pointer", color: t.sub
              }}
            >
              <Ic d={ICONS.shield} size={16} />
            </button>

            {/* Fullscreen */}
            <button
              onClick={toggleFullscreen}
              title="Fullscreen"
              style={{
                width: 32, height: 32, borderRadius: 6,
                background: "transparent", border: "none",
                display: "flex", alignItems: "center", justifyContent: "center",
                cursor: "pointer", color: t.sub
              }}
            >
              <span style={{ fontSize: 14, fontWeight: "bold" }}>&#9974;</span>
            </button>

            {/* Copilot Toggle */}
            <button
              onClick={() => setShowCopilot(!showCopilot)}
              style={{
                width: 36, height: 36, borderRadius: 8,
                background: showCopilot ? t.blue : t.surfaceUp,
                border: `1px solid ${showCopilot ? t.blue : t.border}`,
                display: "flex", alignItems: "center", justifyContent: "center",
                cursor: "pointer", transition: "all 0.2s"
              }}
            >
              <Ic d={ICONS.messageSquare} size={18} color={showCopilot ? "white" : t.blue} />
            </button>
          </div>
        </div>

        {/* Ruler */}
        {showRuler && (
          <div className="ns-ruler" style={{ background: t.surface }}>
            <span style={{ marginRight: 8 }}>Ruler</span>
            {[...Array(20)].map((_, i) => (
              <div key={i} className="ns-ruler-mark" style={{ left: `${40 + i * 40}px` }} />
            ))}
          </div>
        )}

        {/* Custom Toolbar */}
        <div id="ns-toolbar">
          {/* Undo/Redo */}
          <button className="ql-undo" title="Undo (Ctrl+Z)">
            <Ic d={ICONS.arrowLeft} size={14} />
          </button>
          <button className="ql-redo" title="Redo (Ctrl+Y)">
            <Ic d={ICONS.arrowRight} size={14} />
          </button>
          <div style={{ width: 1, height: 20, background: t.border, margin: "0 6px" }}></div>

          {/* Font */}
          <select className="ql-font" defaultValue="times-new-roman" style={{ width: 150 }}>
            <option value="times-new-roman">Times New Roman</option>
            <option value="arial">Arial</option>
            <option value="georgia">Georgia</option>
            <option value="garamond">Garamond</option>
            <option value="courier-new">Courier New</option>
            <option value="verdana">Verdana</option>
            <option value="helvetica">Helvetica</option>
            <option value="calibri">Calibri</option>
            <option value="book-antiqua">Book Antiqua</option>
            <option value="cambria">Cambria</option>
            <option value="roboto">Roboto</option>
            <option value="open-sans">Open Sans</option>
          </select>

          {/* Size */}
          <select className="ql-size" defaultValue="16px" style={{ width: 60 }}>
            <option value="10px">10</option>
            <option value="11px">11</option>
            <option value="12px">12</option>
            <option value="13px">13</option>
            <option value="14px">14</option>
            <option value="16px">16</option>
            <option value="18px">18</option>
            <option value="20px">20</option>
            <option value="22px">22</option>
            <option value="24px">24</option>
            <option value="28px">28</option>
            <option value="32px">32</option>
            <option value="36px">36</option>
            <option value="48px">48</option>
          </select>

          <div style={{ width: 1, height: 20, background: t.border, margin: "0 6px" }}></div>

          {/* Header */}
          <select className="ql-header" defaultValue="" style={{ width: 120 }}>
            <option value="">Paragraph</option>
            <option value="1">Heading 1</option>
            <option value="2">Heading 2</option>
            <option value="3">Heading 3</option>
          </select>

          <div style={{ width: 1, height: 20, background: t.border, margin: "0 6px" }}></div>

          {/* Formatting */}
          <button className="ql-bold" title="Bold (Ctrl+B)" />
          <button className="ql-italic" title="Italic (Ctrl+I)" />
          <button className="ql-underline" title="Underline (Ctrl+U)" />
          <button className="ql-strike" title="Strikethrough" />

          <div style={{ width: 1, height: 20, background: t.border, margin: "0 6px" }}></div>

          {/* Colors */}
          <select className="ql-color" title="Text Color" />
          <select className="ql-background" title="Background Color" />

          <div style={{ width: 1, height: 20, background: t.border, margin: "0 6px" }}></div>

          {/* Alignment */}
          <select className="ql-align" title="Alignment" />

          <div style={{ width: 1, height: 20, background: t.border, margin: "0 6px" }}></div>

          {/* Lists */}
          <button className="ql-list" value="ordered" title="Numbered List" />
          <button className="ql-list" value="bullet" title="Bullet List" />
          <button className="ql-indent" value="-1" title="Decrease Indent" />
          <button className="ql-indent" value="+1" title="Increase Indent" />

          <div style={{ width: 1, height: 20, background: t.border, margin: "0 6px" }}></div>

          {/* Line Spacing */}
          <select className="ql-lineheight" defaultValue="1.5" title="Line Spacing" style={{ width: 80 }}>
            <option value="1">Single</option>
            <option value="1.15">1.15</option>
            <option value="1.5">1.5</option>
            <option value="1.75">1.75</option>
            <option value="2">Double</option>
            <option value="2.5">2.5</option>
          </select>

          <div style={{ width: 1, height: 20, background: t.border, margin: "0 6px" }}></div>

          {/* Page Break */}
          <button className="ql-pageBreak" title="Insert Page Break">
            <span style={{ fontSize: 12, fontWeight: "bold" }}>PB</span>
          </button>

          {/* Zoom */}
          <select
            value={zoom}
            onChange={e => setZoom(Number(e.target.value))}
            style={{ width: 70, marginLeft: 8, fontSize: 12 }}
          >
            <option value={50}>50%</option>
            <option value={75}>75%</option>
            <option value={100}>100%</option>
            <option value={125}>125%</option>
            <option value={150}>150%</option>
            <option value={200}>200%</option>
          </select>
        </div>

        {/* Editor Area */}
        <div style={{ flex: 1, overflow: "auto", padding: "20px 0" }}>
          <ReactQuill
            ref={quillRef}
            value={content}
            onChange={setContent}
            modules={modules}
            formats={formats}
            theme="snow"
            placeholder="Start drafting your legal document..."
            style={{
              transform: `scale(${zoom / 100})`,
              transformOrigin: "top center",
              transition: "transform 0.2s"
            }}
          />
        </div>

        {/* Status Bar */}
        <div className="ns-status-bar" style={{ background: t.surface }}>
          <div style={{ display: "flex", gap: 16 }}>
            <span>Page {pageCount} of {pageCount}</span>
            <span>{wordCount} words</span>
            <span>{charCount} characters</span>
          </div>
          <div style={{ display: "flex", gap: 16 }}>
            <span>Zoom: {zoom}%</span>
            <span>English (India)</span>
            {isSaving && <span style={{ color: t.blue }}>Saving...</span>}
          </div>
        </div>
      </div>

      {/* ── RIGHT SIDEBAR: AI Copilot ── */}
      <div className={`ns-copilot ${showCopilot ? '' : 'hidden'}`}>
        <div style={{
          padding: "16px 20px",
          borderBottom: `1px solid ${t.border}`,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between"
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <div style={{
              width: 32, height: 32, borderRadius: 8, background: t.blue,
              display: "flex", alignItems: "center", justifyContent: "center"
            }}>
              <Ic d={ICONS.book} size={16} color="white" />
            </div>
            <div>
              <h3 style={{ margin: 0, fontSize: 15, fontWeight: 700, color: t.text }}>AI Assistant</h3>
              <div style={{ fontSize: 11, color: t.muted }}>Senior Advocate AI</div>
            </div>
          </div>
          <button
            onClick={() => setShowCopilot(false)}
            style={{ background: "transparent", border: "none", cursor: "pointer" }}
          >
            <Ic d={ICONS.x} size={20} color={t.sub} />
          </button>
        </div>

        {/* Copilot Mode Selector */}
        <div style={{
          padding: "8px 16px",
          borderBottom: `1px solid ${t.border}`,
          display: "flex",
          gap: 8
        }}>
          {[
            { key: "general", label: "General", icon: "messageSquare" },
            { key: "clause", label: "Clauses", icon: "book" },
            { key: "review", label: "Review", icon: "shield" },
            { key: "research", label: "Research", icon: "search" }
          ].map(mode => (
            <button
              key={mode.key}
              onClick={() => setCopilotMode(mode.key)}
              style={{
                padding: "4px 10px",
                borderRadius: 6,
                border: "none",
                background: copilotMode === mode.key ? t.blue : "transparent",
                color: copilotMode === mode.key ? "white" : t.sub,
                fontSize: 11,
                fontWeight: 600,
                cursor: "pointer",
                transition: "all 0.2s"
              }}
            >
              {mode.label}
            </button>
          ))}
        </div>

        <div style={{ display: "flex", padding: "0 20px", borderBottom: `1px solid ${t.border}` }}>
          {["Chat", "Notes", "Health"].map(tab => (
            <div
              key={tab}
              className={`ns-copilot-tab ${copilotTab === tab ? 'active' : ''}`}
              onClick={() => setCopilotTab(tab)}
            >
              {tab === "Chat" && <Ic d={ICONS.messageSquare} size={14} style={{ marginRight: 6, verticalAlign: "middle" }} />}
              {tab === "Notes" && <Ic d={ICONS.file} size={14} style={{ marginRight: 6, verticalAlign: "middle" }} />}
              {tab === "Health" && <Ic d={ICONS.shield} size={14} style={{ marginRight: 6, verticalAlign: "middle" }} />}
              {tab}
            </div>
          ))}
        </div>

        {copilotTab === "Chat" && (
          <>
            <div className="ns-chat-scroll" style={{
              flex: 1, overflowY: "auto", padding: 16,
              display: "flex", flexDirection: "column", gap: 14
            }}>
              {chats.map((chat, idx) => (
                <div key={idx} style={{
                  display: "flex", gap: 10,
                  flexDirection: chat.role === "user" ? "row-reverse" : "row"
                }}>
                  {chat.role === "assistant" && (
                    <div style={{
                      width: 28, height: 28, borderRadius: "50%",
                      background: t.blue, display: "flex",
                      alignItems: "center", justifyContent: "center", flexShrink: 0
                    }}>
                      <Ic d={ICONS.book} size={14} color="white" />
                    </div>
                  )}
                  <div style={{
                    background: chat.role === "user" ? t.blue : t.surfaceUp,
                    color: chat.role === "user" ? "white" : t.text,
                    padding: "12px 14px",
                    borderRadius: chat.role === "user" ? "14px 4px 14px 14px" : "4px 14px 14px 14px",
                    fontSize: 13,
                    lineHeight: 1.5,
                    border: chat.role === "assistant" ? `1px solid ${t.border}` : "none",
                    boxShadow: "0 2px 8px rgba(0,0,0,0.04)",
                    maxWidth: "85%"
                  }}>
                    <div dangerouslySetInnerHTML={{ __html: chat.content }} />
                    {chat.role === "assistant" && idx > 0 && (
                      <button
                        onClick={() => insertAIContent(chat.content)}
                        style={{
                          background: t.surface, border: `1px solid ${t.border}`,
                          color: t.text, fontSize: 11, fontWeight: 600,
                          marginTop: 10, padding: "5px 10px", borderRadius: 6,
                          cursor: "pointer", display: "flex", alignItems: "center",
                          gap: 6, width: "100%", justifyContent: "center"
                        }}
                      >
                        <Ic d={ICONS.download} size={12} color={t.blue} /> Insert into Document
                      </button>
                    )}
                  </div>
                </div>
              ))}
              {isChatLoading && (
                <div style={{ display: "flex", gap: 10 }}>
                  <div style={{
                    width: 28, height: 28, borderRadius: "50%",
                    background: t.blue, display: "flex",
                    alignItems: "center", justifyContent: "center"
                  }}>
                    <Ic d={ICONS.book} size={14} color="white" />
                  </div>
                  <div style={{
                    padding: "12px 14px", background: t.surfaceUp,
                    borderRadius: "4px 14px 14px 14px",
                    border: `1px solid ${t.border}`
                  }}>
                    <div style={{ display: "flex", gap: 4, alignItems: "center" }}>
                      <span className="ns-dot"></span>
                      <span className="ns-dot" style={{ animationDelay: "0.2s" }}></span>
                      <span className="ns-dot" style={{ animationDelay: "0.4s" }}></span>
                    </div>
                  </div>
                </div>
              )}
            </div>

            <div style={{
              padding: 12, borderTop: `1px solid ${t.border}`,
              display: "flex", flexDirection: "column", gap: 10
            }}>
              {/* Quick Action Chips */}
              <div style={{
                display: "flex", gap: 6, overflowX: "auto",
                paddingBottom: 4, scrollbarWidth: "none"
              }}>
                <button className="ns-chip" onClick={() => setChatInput("Draft a jurisdiction clause for Mumbai courts")}>
                  Jurisdiction
                </button>
                <button className="ns-chip" onClick={() => setChatInput("Review document for legal risks")}>
                  Risk Review
                </button>
                <button className="ns-chip" onClick={() => setChatInput("Fix legal citations and references")}>
                  Fix Citations
                </button>
                <button className="ns-chip" onClick={() => setChatInput("Convert IPC sections to BNS 2023")}>
                  IPC to BNS
                </button>
                <button className="ns-chip" onClick={() => setChatInput("Draft a prayer clause for writ petition")}>
                  Prayer Clause
                </button>
              </div>

              <form onSubmit={handleChatSubmit} style={{
                display: "flex", background: t.bg,
                border: `1px solid ${t.border}`, borderRadius: 10,
                padding: "6px 10px", alignItems: "center"
              }}>
                <input
                  value={chatInput}
                  onChange={e => setChatInput(e.target.value)}
                  placeholder="Ask anything about your document..."
                  style={{
                    flex: 1, background: "transparent", border: "none",
                    color: t.text, outline: "none", fontSize: 13
                  }}
                />
                <div style={{ display: "flex", gap: 6 }}>
                  <button type="button" style={{
                    background: "transparent", border: "none",
                    color: t.sub, cursor: "pointer", display: "flex"
                  }}>
                    <Ic d={ICONS.mic} size={16} />
                  </button>
                  <button
                    type="submit"
                    disabled={!chatInput.trim() || isChatLoading}
                    style={{
                      background: "transparent", border: "none",
                      color: chatInput.trim() && !isChatLoading ? t.blue : t.border,
                      cursor: chatInput.trim() && !isChatLoading ? "pointer" : "default",
                      display: "flex"
                    }}
                  >
                    <Ic d={ICONS.send} size={16} />
                  </button>
                </div>
              </form>
            </div>
          </>
        )}

        {copilotTab === "Notes" && (
          <div style={{ flex: 1, padding: 20, overflowY: "auto" }}>
            <div style={{
              background: t.surfaceUp, borderRadius: 8,
              padding: 12, border: `1px solid ${t.border}`,
              fontSize: 13, color: t.text, lineHeight: 1.6,
              minHeight: 200
            }}>
              <strong style={{ color: t.sub, fontSize: 11, textTransform: "uppercase", letterSpacing: 1 }}>
                Document Notes
              </strong>
              <textarea
                placeholder="Add notes about this document..."
                style={{
                  width: "100%", minHeight: 150, background: "transparent",
                  border: "none", color: t.text, fontSize: 13,
                  outline: "none", resize: "vertical", marginTop: 8,
                  fontFamily: "inherit", lineHeight: 1.6
                }}
              />
            </div>
          </div>
        )}

        {copilotTab === "Health" && (
          <div style={{ flex: 1, padding: 20, overflowY: "auto" }}>
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              <div style={{
                background: t.surfaceUp, borderRadius: 8,
                padding: 14, border: `1px solid ${t.border}`
              }}>
                <div style={{ fontSize: 11, color: t.muted, marginBottom: 4 }}>Document Health Score</div>
                <div style={{ fontSize: 24, fontWeight: 700, color: wordCount > 100 ? "#22c55e" : t.sub }}>
                  {wordCount > 100 ? "92" : "45"}/100
                </div>
              </div>

              <div style={{
                background: t.surfaceUp, borderRadius: 8,
                padding: 14, border: `1px solid ${t.border}`
              }}>
                <div style={{ fontSize: 11, color: t.muted, marginBottom: 8 }}>Checks</div>
                {[
                  { label: "Proper court headers", pass: content.includes("IN THE") },
                  { label: "Party designations", pass: content.includes("...PETITIONER") || content.includes("...PLAINTIFF") },
                  { label: "Prayer clause", pass: content.toLowerCase().includes("prayer") },
                  { label: "Signature block", pass: content.includes("Filed by:") || content.includes("Counsel for") },
                  { label: "Date references", pass: /\d{2}\/\d{2}\/\d{4}/.test(content) },
                  { label: "Legal citations", pass: /\d+\s+SCC|\d+\s+SCR|AIR\s+\d{4}/.test(content) }
                ].map((check, i) => (
                  <div key={i} style={{
                    display: "flex", alignItems: "center", gap: 8,
                    padding: "4px 0", fontSize: 12, color: t.text
                  }}>
                    <div style={{
                      width: 16, height: 16, borderRadius: "50%",
                      background: check.pass ? "#22c55e" : t.border,
                      display: "flex", alignItems: "center", justifyContent: "center"
                    }}>
                      {check.pass && <span style={{ color: "white", fontSize: 10 }}>&#10003;</span>}
                    </div>
                    {check.label}
                  </div>
                ))}
              </div>

              <div style={{
                background: t.surfaceUp, borderRadius: 8,
                padding: 14, border: `1px solid ${t.border}`
              }}>
                <div style={{ fontSize: 11, color: t.muted, marginBottom: 4 }}>Suggestions</div>
                <div style={{ fontSize: 12, color: t.sub, lineHeight: 1.5 }}>
                  {!content.includes("MOST RESPECTFULLY") && "• Add formal salutation (Most Respectfully Showeth)"}
                  {!content.includes("VERIFICATION") && "• Add verification clause for affidavits"}
                  {wordCount < 50 && "• Document seems too short for a legal filing"}
                  {!/Section\s+\d+/.test(content) && "• Consider citing relevant statutory sections"}
                  {wordCount > 100 && "• Document structure looks good. Consider adding case citations."}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* ── FIND & REPLACE MODAL ── */}
      {showFindReplace && (
        <div className="ns-modal-overlay" onClick={() => setShowFindReplace(false)}>
          <div className="ns-modal" onClick={e => e.stopPropagation()}>
            <div style={{
              padding: "16px 20px", borderBottom: `1px solid ${t.border}`,
              display: "flex", justifyContent: "space-between", alignItems: "center"
            }}>
              <h3 style={{ margin: 0, fontSize: 16, color: t.text }}>Find & Replace</h3>
              <button onClick={() => setShowFindReplace(false)} style={{ background: "transparent", border: "none", cursor: "pointer" }}>
                <Ic d={ICONS.x} size={20} color={t.sub} />
              </button>
            </div>
            <div style={{ padding: 20, display: "flex", flexDirection: "column", gap: 14 }}>
              <div>
                <label style={{ fontSize: 12, color: t.sub, marginBottom: 6, display: "block" }}>Find</label>
                <input
                  value={findText}
                  onChange={e => setFindText(e.target.value)}
                  style={{
                    width: "100%", padding: "10px 12px", borderRadius: 6,
                    border: `1px solid ${t.border}`, background: t.bg,
                    color: t.text, fontSize: 14, outline: "none"
                  }}
                  autoFocus
                />
              </div>
              <div>
                <label style={{ fontSize: 12, color: t.sub, marginBottom: 6, display: "block" }}>Replace with</label>
                <input
                  value={replaceText}
                  onChange={e => setReplaceText(e.target.value)}
                  style={{
                    width: "100%", padding: "10px 12px", borderRadius: 6,
                    border: `1px solid ${t.border}`, background: t.bg,
                    color: t.text, fontSize: 14, outline: "none"
                  }}
                />
              </div>
              <div style={{ display: "flex", gap: 10, justifyContent: "flex-end", marginTop: 6 }}>
                <button
                  onClick={() => setShowFindReplace(false)}
                  style={{
                    padding: "8px 16px", borderRadius: 6, border: `1px solid ${t.border}`,
                    background: "transparent", color: t.text, fontSize: 13,
                    cursor: "pointer", fontWeight: 600
                  }}
                >
                  Cancel
                </button>
                <button
                  onClick={handleFindReplace}
                  style={{
                    padding: "8px 16px", borderRadius: 6, border: "none",
                    background: t.blue, color: "white", fontSize: 13,
                    cursor: "pointer", fontWeight: 600
                  }}
                >
                  Replace All
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── PAGE SETUP MODAL ── */}
      {showPageSetup && (
        <div className="ns-modal-overlay" onClick={() => setShowPageSetup(false)}>
          <div className="ns-modal" onClick={e => e.stopPropagation()}>
            <div style={{
              padding: "16px 20px", borderBottom: `1px solid ${t.border}`,
              display: "flex", justifyContent: "space-between", alignItems: "center"
            }}>
              <h3 style={{ margin: 0, fontSize: 16, color: t.text }}>Page Setup</h3>
              <button onClick={() => setShowPageSetup(false)} style={{ background: "transparent", border: "none", cursor: "pointer" }}>
                <Ic d={ICONS.x} size={20} color={t.sub} />
              </button>
            </div>
            <div style={{ padding: 20, display: "flex", flexDirection: "column", gap: 16 }}>
              <div>
                <label style={{ fontSize: 12, color: t.sub, marginBottom: 8, display: "block", fontWeight: 600 }}>
                  Margins (pixels)
                </label>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                  {["top", "bottom", "left", "right"].map(side => (
                    <div key={side}>
                      <label style={{ fontSize: 11, color: t.muted, textTransform: "capitalize" }}>{side}</label>
                      <input
                        type="number"
                        value={pageMargins[side]}
                        onChange={e => setPageMargins(prev => ({ ...prev, [side]: Number(e.target.value) }))}
                        style={{
                          width: "100%", padding: "8px 10px", borderRadius: 6,
                          border: `1px solid ${t.border}`, background: t.bg,
                          color: t.text, fontSize: 13, outline: "none", marginTop: 4
                        }}
                      />
                    </div>
                  ))}
                </div>
              </div>

              <div>
                <label style={{ fontSize: 12, color: t.sub, marginBottom: 8, display: "block", fontWeight: 600 }}>
                  Line Spacing
                </label>
                <select
                  value={lineSpacing}
                  onChange={e => setLineSpacing(e.target.value)}
                  style={{
                    width: "100%", padding: "8px 10px", borderRadius: 6,
                    border: `1px solid ${t.border}`, background: t.bg,
                    color: t.text, fontSize: 13, outline: "none"
                  }}
                >
                  <option value="1">Single (1.0)</option>
                  <option value="1.15">1.15</option>
                  <option value="1.5">1.5 (Legal Standard)</option>
                  <option value="1.75">1.75</option>
                  <option value="2">Double (2.0)</option>
                  <option value="2.5">2.5</option>
                </select>
              </div>

              <div style={{ display: "flex", gap: 10, justifyContent: "flex-end", marginTop: 6 }}>
                <button
                  onClick={() => setShowPageSetup(false)}
                  style={{
                    padding: "8px 16px", borderRadius: 6, border: `1px solid ${t.border}`,
                    background: "transparent", color: t.text, fontSize: 13,
                    cursor: "pointer", fontWeight: 600
                  }}
                >
                  Cancel
                </button>
                <button
                  onClick={applyPageSetup}
                  style={{
                    padding: "8px 16px", borderRadius: 6, border: "none",
                    background: t.blue, color: "white", fontSize: 13,
                    cursor: "pointer", fontWeight: 600
                  }}
                >
                  Apply
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── WATERMARK MODAL ── */}
      {showWatermarkModal && (
        <div className="ns-modal-overlay" onClick={() => setShowWatermarkModal(false)}>
          <div className="ns-modal" onClick={e => e.stopPropagation()}>
            <div style={{
              padding: "16px 20px", borderBottom: `1px solid ${t.border}`,
              display: "flex", justifyContent: "space-between", alignItems: "center"
            }}>
              <h3 style={{ margin: 0, fontSize: 16, color: t.text }}>Watermark</h3>
              <button onClick={() => setShowWatermarkModal(false)} style={{ background: "transparent", border: "none", cursor: "pointer" }}>
                <Ic d={ICONS.x} size={20} color={t.sub} />
              </button>
            </div>
            <div style={{ padding: 20, display: "flex", flexDirection: "column", gap: 14 }}>
              <div>
                <label style={{ fontSize: 12, color: t.sub, marginBottom: 6, display: "block" }}>
                  Watermark Text (leave empty to remove)
                </label>
                <input
                  value={watermark}
                  onChange={e => setWatermark(e.target.value)}
                  placeholder="e.g., DRAFT, CONFIDENTIAL, SAMPLE"
                  style={{
                    width: "100%", padding: "10px 12px", borderRadius: 6,
                    border: `1px solid ${t.border}`, background: t.bg,
                    color: t.text, fontSize: 14, outline: "none"
                  }}
                  autoFocus
                />
              </div>
              <div style={{ display: "flex", gap: 10, justifyContent: "flex-end", marginTop: 6 }}>
                <button
                  onClick={() => setShowWatermarkModal(false)}
                  style={{
                    padding: "8px 16px", borderRadius: 6, border: `1px solid ${t.border}`,
                    background: "transparent", color: t.text, fontSize: 13,
                    cursor: "pointer", fontWeight: 600
                  }}
                >
                  Cancel
                </button>
                <button
                  onClick={applyWatermark}
                  style={{
                    padding: "8px 16px", borderRadius: 6, border: "none",
                    background: t.blue, color: "white", fontSize: 13,
                    cursor: "pointer", fontWeight: 600
                  }}
                >
                  Apply
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── TEMPLATES MODAL ── */}
      {showTemplates && (
        <div style={{
          position: "fixed", inset: 0, background: "rgba(0,0,0,0.6)",
          backdropFilter: "blur(4px)", zIndex: 10000,
          display: "flex", alignItems: "center", justifyContent: "center",
          padding: 20
        }}>
          <div style={{
            width: "100%", maxWidth: 850, background: t.surface,
            borderRadius: 16, boxShadow: "0 24px 48px rgba(0,0,0,0.2)",
            display: "flex", flexDirection: "column", maxHeight: "90vh"
          }}>

            <div style={{
              padding: "20px 24px", borderBottom: `1px solid ${t.border}`,
              display: "flex", justifyContent: "space-between", alignItems: "center"
            }}>
              <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                {formTemplate || selectedCategory ? (
                  <button
                    onClick={() => {
                      if (formTemplate) setFormTemplate(null);
                      else setSelectedCategory(null);
                    }}
                    style={{
                      padding: 8, background: "transparent", border: "none",
                      cursor: "pointer", display: "flex", alignItems: "center"
                    }}
                  >
                    <Ic d={ICONS.chevronLeft} size={20} color={t.text} />
                  </button>
                ) : (
                  <div style={{
                    padding: 8, background: t.surfaceUp, borderRadius: 8,
                    border: `1px solid ${t.border}`
                  }}>
                    <Ic d={ICONS.doc} size={20} color={t.text} />
                  </div>
                )}
                <div>
                  <h2 style={{ margin: 0, fontSize: 18, fontWeight: 700, color: t.text }}>
                    {formTemplate ? formTemplate.name : selectedCategory ? selectedCategory.category : "Legal Templates"}
                  </h2>
                  <div style={{ fontSize: 13, color: t.sub }}>
                    {formTemplate ? "Fill in the details below" : selectedCategory ? "Select a document to load" : "Search or browse by court level"}
                  </div>
                </div>
              </div>
              <button
                onClick={() => { setShowTemplates(false); setSelectedCategory(null); setFormTemplate(null); }}
                style={{ background: "transparent", border: "none", cursor: "pointer" }}
              >
                <Ic d={ICONS.x} size={24} color={t.sub} />
              </button>
            </div>

            <div style={{ padding: 24, overflowY: "auto", minHeight: 400 }}>
              {formTemplate ? (
                <form id="template-form" onSubmit={handleFormSubmit} style={{ display: "flex", flexDirection: "column", gap: 18 }}>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
                    {formTemplate.variables.map(v => (
                      <div key={v.key} style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                        <label style={{ fontSize: 12, fontWeight: 600, color: t.text }}>
                          {v.label} <span style={{ color: "#ef4444" }}>*</span>
                        </label>
                        <input
                          required
                          placeholder={v.placeholder}
                          value={formData[v.key]}
                          onChange={e => setFormData({ ...formData, [v.key]: e.target.value })}
                          style={{
                            padding: "10px 14px", borderRadius: 8,
                            border: `1px solid ${t.border}`, background: t.bg,
                            color: t.text, fontSize: 14, outline: "none",
                            transition: "border-color 0.2s"
                          }}
                          onFocus={e => e.target.style.borderColor = t.blue}
                          onBlur={e => e.target.style.borderColor = t.border}
                        />
                      </div>
                    ))}
                  </div>
                  <div style={{
                    background: t.surfaceUp, borderRadius: 8,
                    padding: 14, border: `1px solid ${t.border}`,
                    fontSize: 12, color: t.sub, lineHeight: 1.5
                  }}>
                    <strong style={{ color: t.text }}>Preview:</strong> The template will be filled with your inputs and loaded into the editor. You can then edit it further.
                  </div>
                </form>
              ) : selectedCategory ? (
                <div style={{ display: "flex", flexDirection: "column", gap: 1 }}>
                  {selectedCategory.items.map((item, j) => (
                    <button
                      key={j}
                      onClick={() => handleTemplateSelect(item)}
                      style={{
                        padding: "14px 12px", background: "transparent",
                        border: "none", borderBottom: `1px solid ${t.border}`,
                        cursor: "pointer", display: "flex",
                        alignItems: "center", justifyContent: "space-between",
                        textAlign: "left", transition: "background 0.2s"
                      }}
                      onMouseEnter={e => e.currentTarget.style.background = `${t.blue}0a`}
                      onMouseLeave={e => e.currentTarget.style.background = "transparent"}
                    >
                      <div style={{ display: "flex", alignItems: "flex-start", gap: 14 }}>
                        <Ic d={ICONS.doc} size={18} color={t.sub} style={{ marginTop: 2 }} />
                        <div>
                          <div style={{ fontSize: 14, fontWeight: 600, color: t.text, marginBottom: 3 }}>
                            {item.name}
                          </div>
                          <div style={{ fontSize: 12, color: t.sub }}>{item.desc}</div>
                          {item.variables && (
                            <div style={{ fontSize: 11, color: t.muted, marginTop: 4 }}>
                              {item.variables.length} fields to fill
                            </div>
                          )}
                        </div>
                      </div>
                      <Ic d={ICONS.chevronRight} size={16} color={t.sub} />
                    </button>
                  ))}
                </div>
              ) : (
                <>
                  <div style={{ position: "relative", marginBottom: 28 }}>
                    <Ic d={ICONS.search} size={16} color={t.sub} style={{
                      position: "absolute", left: 14, top: "50%", transform: "translateY(-50%)"
                    }} />
                    <input
                      placeholder="Search templates... (e.g., Vakalatnama, Writ Petition, Bail)"
                      value={searchQuery}
                      onChange={e => setSearchQuery(e.target.value)}
                      style={{
                        width: "100%", padding: "14px 14px 14px 42px",
                        borderRadius: 10, border: `1px solid ${t.border}`,
                        background: t.bg, color: t.text, fontSize: 14, outline: "none"
                      }}
                    />
                  </div>

                  <div style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 20 }}>
                    <div style={{ flex: 1, height: 1, background: t.border }}></div>
                    <div style={{
                      fontSize: 10, fontWeight: 700, color: t.muted,
                      letterSpacing: 1.5, textTransform: "uppercase"
                    }}>
                      Browse by Court Level
                    </div>
                    <div style={{ flex: 1, height: 1, background: t.border }}></div>
                  </div>

                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
                    {TEMPLATES_DATA.filter(cat =>
                      !searchQuery || cat.items.some(i =>
                        i.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                        i.desc.toLowerCase().includes(searchQuery.toLowerCase())
                      )
                    ).map((cat, i) => (
                      <button
                        key={i}
                        onClick={() => setSelectedCategory(cat)}
                        style={{
                          padding: 20, borderRadius: 10,
                          border: `1px solid ${t.border}`, background: t.surface,
                          display: "flex", flexDirection: "column",
                          cursor: "pointer", textAlign: "left", transition: "all 0.2s"
                        }}
                        onMouseEnter={e => {
                          e.currentTarget.style.borderColor = t.blue;
                          e.currentTarget.style.background = t.surfaceUp;
                        }}
                        onMouseLeave={e => {
                          e.currentTarget.style.borderColor = t.border;
                          e.currentTarget.style.background = t.surface;
                        }}
                      >
                        <div style={{
                          width: 44, height: 44, background: t.surfaceUp,
                          borderRadius: 10, display: "flex",
                          alignItems: "center", justifyContent: "center",
                          border: `1px solid ${t.border}`, marginBottom: 12
                        }}>
                          <Ic d={ICONS[cat.icon]} size={22} color={t.sub} />
                        </div>
                        <h3 style={{ margin: "0 0 6px", fontSize: 16, fontWeight: 700, color: t.text }}>
                          {cat.category}
                        </h3>
                        <div style={{ fontSize: 12, color: t.sub, marginBottom: 12, lineHeight: 1.5, flex: 1 }}>
                          {cat.desc}
                        </div>
                        <div style={{
                          fontSize: 11, color: t.muted, fontWeight: 600,
                          display: "flex", alignItems: "center", gap: 6
                        }}>
                          <Ic d={ICONS.doc} size={12} color={t.muted} />
                          {cat.items.length} templates
                        </div>
                      </button>
                    ))}
                  </div>
                </>
              )}
            </div>

            <div style={{
              padding: "14px 24px", borderTop: `1px solid ${t.border}`,
              display: "flex", justifyContent: "space-between",
              alignItems: "center", background: t.surfaceUp,
              borderRadius: "0 0 16px 16px"
            }}>
              <div style={{ display: "flex", gap: 16, alignItems: "center" }}>
                <button
                  onClick={() => {
                    if (formTemplate) setFormTemplate(null);
                    else if (selectedCategory) setSelectedCategory(null);
                    else setShowTemplates(false);
                  }}
                  style={{
                    background: "transparent", border: "none",
                    color: t.sub, fontWeight: 600, cursor: "pointer", fontSize: 13
                  }}
                >
                  {formTemplate ? "Back to Templates" : selectedCategory ? "Back" : "Cancel"}
                </button>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
                {formTemplate ? (
                  <button
                    form="template-form"
                    type="submit"
                    style={{
                      background: t.blue, color: "white", border: "none",
                      padding: "8px 20px", borderRadius: 8,
                      fontWeight: 600, cursor: "pointer", fontSize: 13
                    }}
                  >
                    Load Template
                  </button>
                ) : selectedCategory ? (
                  <div style={{ fontSize: 12, color: t.sub }}>
                    Click a template to preview and load
                  </div>
                ) : (
                  <div style={{ fontSize: 12, color: t.sub }}>
                    {TEMPLATES_DATA.reduce((acc, cat) => acc + cat.items.length, 0)} templates in {TEMPLATES_DATA.length} categories
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}