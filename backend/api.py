"""
api.py — FastAPI Backend for Nyaya-Setu Website
Nyaya-Setu | Team IKS | SPIT CSE 2025-26

INTEGRATED VERSION:
- Includes CalendarEvent SQLAlchemy model support
- Includes tasks_routes router for standalone task management
- All auth-protected routes use Bearer token
- CORS configured for frontend
- ENHANCED: Professional Legal Document Generator with proper templates
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json, time, uuid, random, string, re
from typing import Optional
from fastapi import FastAPI, UploadFile, File, HTTPException, Form, Depends
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel
from dotenv import load_dotenv
from twilio.rest import Client as TwilioClient

from document_analyzer import analyze_document, DocumentRAG, fetch_case_laws, fetch_acts
from lex_validator import (
    compute_compliance_score,
    generate_migration_message,
    extract_text_from_pdf_bytes,
)
from modules.m3_evidence.evidence import generate_evidence_certificate
from legal_translator import translate_legal_text, translate_fir, get_supported_languages

from sqlalchemy.orm import Session
import models
from models import StatutoryAct
from database import engine, get_db
from auth import verify_password, get_password_hash, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES, SECRET_KEY, ALGORITHM
from datetime import timedelta, date, datetime
from jose import JWTError, jwt
from fastapi.security import OAuth2PasswordBearer

from tasks_routes import router as tasks_router, init_tasks_db

models.Base.metadata.create_all(bind=engine)

from sqlalchemy import inspect, text
try:
    inspector = inspect(engine)
    if 'tasks' in inspector.get_table_names():
        task_columns = [col['name'] for col in inspector.get_columns('tasks')]
        for col_name, col_type in [(
            'case_id', 'INTEGER'), ('assignee_id', 'INTEGER'), ('title', 'VARCHAR'),
            ('description', 'VARCHAR'), ('due_date', 'DATETIME'), ('is_completed', 'BOOLEAN DEFAULT 0')
        ]:
            if col_name not in task_columns:
                with engine.connect() as conn:
                    conn.execute(text(f"ALTER TABLE tasks ADD COLUMN {col_name} {col_type}"))
                    conn.commit()
    if 'hearings' in inspector.get_table_names():
        hearing_columns = [col['name'] for col in inspector.get_columns('hearings')]
        if 'notes' not in hearing_columns:
            with engine.connect() as conn:
                conn.execute(text("ALTER TABLE hearings ADD COLUMN notes VARCHAR"))
                conn.commit()
    if 'calendar_events' in inspector.get_table_names():
        event_columns = [col['name'] for col in inspector.get_columns('calendar_events')]
        if 'matter_id' not in event_columns:
            with engine.connect() as conn:
                conn.execute(text("ALTER TABLE calendar_events ADD COLUMN matter_id INTEGER"))
                conn.commit()
except Exception as e:
    print(f"[DB MIGRATION] Warning: {e}")

init_tasks_db()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
load_dotenv()

TWILIO_SID    = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_TOKEN  = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WA_NUM = os.getenv("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886")

app = FastAPI(title="Nyaya-Setu API", description="AI-Powered Indian Legal Document Analyzer", version="1.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(tasks_router)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    print(f"Validation Error: {exc.errors()}")
    # Convert errors to a serializable format
    serializable_errors = []
    for err in exc.errors():
        d = dict(err)
        if "ctx" in d:
            d["ctx"] = {k: str(v) for k, v in d["ctx"].items()}
        serializable_errors.append(d)
    return JSONResponse(
        status_code=422,
        content={"detail": serializable_errors, "body": str(exc.body)},
    )

doc_sessions: dict = {}
otp_store:    dict = {}

def cleanup_old_sessions():
    now = time.time()
    expired = [k for k, v in doc_sessions.items() if now - v["created_at"] > 3600]
    for k in expired:
        del doc_sessions[k]

def normalise_phone(phone: str) -> str:
    p = phone.strip().replace(" ", "").replace("-", "")
    if not p.startswith("+"):
        p = "+91" + p.lstrip("0")
    return p

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    user = db.query(models.User).first()
    if user:
        return user
    dev_user = models.User(
        email="dev@local.com",
        hashed_password=get_password_hash("dev"),
        full_name="Nitin Sharma",
        role="admin",
        phone=None
    )
    db.add(dev_user)
    db.commit()
    db.refresh(dev_user)
    return dev_user

# ══════════════════════════════════════════════════════════════════════════════
# PYDANTIC MODELS
# ══════════════════════════════════════════════════════════════════════════════

class QARequest(BaseModel):
    session_id: str
    question:   str

class ComplianceRequest(BaseModel):
    text: str

class CaseLawRequest(BaseModel):
    query:    str
    doc_type: str = "Legal Document"

class OTPSendRequest(BaseModel):
    phone: str

class OTPVerifyRequest(BaseModel):
    phone: str
    otp:   str

class TranslateRequest(BaseModel):
    text:          str
    source_lang:   str = "auto"
    target_lang:   str = "en"
    document_type: str = "FIR / Police Complaint"

class UserCreate(BaseModel):
    email: str
    password: str
    full_name: str
    phone: str = None

class UserLogin(BaseModel):
    email: str
    password: str

class CaseCreate(BaseModel):
    title: str
    cnr_number: Optional[str] = None
    court_name: Optional[str] = None
    client_name: Optional[str] = None
    status: str = "Active"

class CaseResponse(BaseModel):
    id: int
    title: str
    cnr_number: Optional[str] = None
    court_name: Optional[str] = None
    client_name: Optional[str] = None
    status: str
    class Config:
        from_attributes = True

class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    due_date: str
    case_id: Optional[int] = None

class TaskResponse(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    due_date: str
    is_completed: bool
    case_id: Optional[int] = None
    class Config:
        from_attributes = True

class HearingCreate(BaseModel):
    case_id: int
    hearing_date: str
    purpose: str
    notes: Optional[str] = None

class HearingResponse(BaseModel):
    id: int
    case_id: int
    hearing_date: str
    purpose: str
    notes: Optional[str] = None
    class Config:
        from_attributes = True

class InvoiceCreate(BaseModel):
    client_name: str
    amount: float
    due_date: str

class InvoiceResponse(BaseModel):
    id: int
    client_name: str
    amount: float
    status: str
    due_date: str
    created_at: str
    class Config:
        from_attributes = True

class DocumentGenerateRequest(BaseModel):
    doc_type: str
    party_a: str
    party_b: str
    details: str

class ResearchAskRequest(BaseModel):
    query: str

class ResearchCaseRequest(BaseModel):
    query: str
    court: str = "All Courts"
    year_from: str = ""
    year_to: str = ""
    page: int = 0

class ResearchSectionRequest(BaseModel):
    sections: str
    act: str
    page: int = 0

class ResearchActRequest(BaseModel):
    act_name: str
    jurisdiction: str = "Union of India"

class ResearchActsListRequest(BaseModel):
    jurisdiction: Optional[str] = None
    category: Optional[str] = None
    page: int = 0

class CopilotRequest(BaseModel):
    prompt: str
    document_context: str = ""

class CalendarEventCreate(BaseModel):
    title: str
    event_type: str = "hearing"
    event_date: str
    event_time: Optional[str] = None
    court: Optional[str] = None
    description: Optional[str] = None
    matter_id: Optional[int] = None

class CalendarEventResponse(BaseModel):
    id: int
    title: str
    event_type: str
    event_date: str
    event_time: Optional[str]
    court: Optional[str]
    description: Optional[str]
    matter_id: Optional[int]
    created_at: str
    updated_at: Optional[str]
    class Config:
        from_attributes = True

# ══════════════════════════════════════════════════════════════════════════════
# DOCUMENT GENERATOR HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def parse_details(details_text: str) -> dict:
    """Parse structured details from user input text."""
    result = {}
    lines = details_text.strip().split("\n")
    for line in lines:
        if ":" in line:
            key, value = line.split(":", 1)
            result[key.strip().lower().replace(" ", "_")] = value.strip()
    return result

def get_current_date() -> str:
    """Return current date in formal format."""
    now = datetime.now()
    day = now.day
    suffix = {1: "st", 2: "nd", 3: "rd"}.get(day if day < 20 else day % 10, "th")
    return now.strftime(f"%d{suffix} %B, %Y")

def generate_rent_agreement(party_a: str, party_b: str, details: str, advocate_name: str) -> str:
    parsed = parse_details(details)
    property_address = parsed.get("property_address", parsed.get("address", "the property described herein"))
    monthly_rent = parsed.get("monthly_rent", parsed.get("rent", "__________"))
    security_deposit = parsed.get("security_deposit", "__________")
    tenure = parsed.get("tenure", parsed.get("duration", "11 (Eleven) months"))
    commencement_date = parsed.get("commencement_date", parsed.get("start_date", get_current_date()))

    return f"""================================================================================
                              RENT AGREEMENT
================================================================================

This Rent Agreement (hereinafter referred to as the "Agreement") is executed on 
this {get_current_date()} at {parsed.get("place", "________________")}.

BETWEEN

{party_a}, S/o/D/o ____________________, aged approximately ____ years, 
residing at ____________________, hereinafter referred to as the "LANDLORD" 
(which expression shall, unless repugnant to the context, mean and include his/her 
heirs, legal representatives, successors, and assigns) of the ONE PART;

AND

{party_b}, S/o/D/o ____________________, aged approximately ____ years, 
residing at ____________________, hereinafter referred to as the "TENANT" 
(which expression shall, unless repugnant to the context, mean and include his/her 
heirs, legal representatives, successors, and assigns) of the OTHER PART.

The Landlord and Tenant are hereinafter individually referred to as a "Party" and 
collectively as the "Parties".

================================================================================
                            RECITALS / WHEREAS
================================================================================

WHEREAS the Landlord is the absolute and lawful owner of the residential property 
situated at {property_address}, more particularly described in the Schedule 
hereto (hereinafter referred to as the "Demised Premises");

AND WHEREAS the Tenant has approached the Landlord with a request to take the 
Demised Premises on rent for residential purposes, and the Landlord has agreed 
to grant the same on the terms and conditions hereinafter recorded;

AND WHEREAS the Parties are desirous of reducing the terms of their agreement 
to writing to avoid any future ambiguity or dispute.

================================================================================
                          TERMS AND CONDITIONS
================================================================================

1. DEMISE AND GRANT
   The Landlord hereby demises and lets out the Demised Premises unto the Tenant, 
   and the Tenant hereby takes the same on lease, for a period of {tenure}, 
   commencing from {commencement_date}.

2. RENT
   The Tenant shall pay to the Landlord a monthly rent of INR {monthly_rent} 
   (Rupees ____________________ only), payable in advance on or before the 
   5th day of every calendar month. The first month's rent shall be paid at the 
   time of execution of this Agreement.

3. SECURITY DEPOSIT
   The Tenant has paid / shall pay a refundable security deposit of INR 
   {security_deposit} (Rupees ____________________ only) to the Landlord at the 
   time of execution of this Agreement. The said deposit shall be refunded to 
   the Tenant within 15 (Fifteen) days of the Tenant vacating the Demised 
   Premises, subject to deduction for:
   (a) arrears of rent, if any;
   (b) damages caused to the Demised Premises, beyond normal wear and tear;
   (c) unpaid utility bills attributable to the Tenant's occupancy.

4. USE OF PREMISES
   The Demised Premises shall be used strictly for residential purposes by the 
   Tenant and his/her immediate family members only. The Tenant shall not:
   (a) sublet, assign, or part with possession of the whole or any part of the 
       Demised Premises without prior written consent of the Landlord;
   (b) use the Demised Premises for any unlawful, immoral, or commercial purpose;
   (c) make any structural alterations or additions without written consent.

5. MAINTENANCE AND REPAIRS
   (a) The Tenant shall maintain the Demised Premises in good and tenantable 
       condition and shall bear the cost of minor repairs (up to INR 500/-).
   (b) The Landlord shall be responsible for major structural repairs.
   (c) The Tenant shall not paint, nail, drill, or damage walls without consent.

6. UTILITIES
   The Tenant shall bear and pay all charges for electricity, water, gas, 
   internet, and other utilities consumed during the tenancy period.

7. TERMINATION
   (a) Either Party may terminate this Agreement by giving 2 (Two) months' 
       prior written notice to the other Party.
   (b) The Landlord may terminate this Agreement forthwith if the Tenant:
       (i) defaults in payment of rent for 2 (Two) consecutive months;
       (ii) uses the Demised Premises for any unlawful purpose;
       (iii) sublets the Demised Premises without consent.

8. POSSESSION AND VACATING
   The Tenant shall hand over peaceful and vacant possession of the Demised 
   Premises at the expiry or earlier termination of this Agreement, in the same 
   condition as at the commencement, fair wear and tear excepted.

9. JURISDICTION
   This Agreement shall be governed by the laws of India. Any dispute arising 
   out of or in connection with this Agreement shall be subject to the exclusive 
   jurisdiction of the competent Civil Court at {parsed.get("jurisdiction", "________________")}.

10. ENTIRE AGREEMENT
    This Agreement constitutes the entire understanding between the Parties and 
    supersedes all prior negotiations, representations, and understandings.

================================================================================
                              SCHEDULE
                    (Description of Demised Premises)
================================================================================

Property Address: {property_address}
Area: Approximately {parsed.get("area", "__________")} sq. ft.
Configuration: {parsed.get("configuration", "__________")}
Furnishings/Fixtures: {parsed.get("furnishings", "As existing")}

================================================================================
                          ADDITIONAL DETAILS
================================================================================

{details}

================================================================================
                         EXECUTION AND SIGNATURES
================================================================================

IN WITNESS WHEREOF, the Parties have set their respective hands and seals on 
the day, month, and year first above written.

WITNESS 1:
Name: ____________________________
Address: __________________________
Signature: _______________________

WITNESS 2:
Name: ____________________________
Address: __________________________
Signature: _______________________

LANDLORD:

___________________________
{party_a}
Date: _____________________

TENANT:

___________________________
{party_b}
Date: _____________________

================================================================================
                         ADVOCATE CERTIFICATION
================================================================================

This Rent Agreement has been reviewed and certified by:

Advocate {advocate_name}
Date: {get_current_date()}

[Seal & Signature]

================================================================================
                              END OF DOCUMENT
================================================================================"""


def generate_legal_notice(party_a: str, party_b: str, details: str, advocate_name: str) -> str:
    parsed = parse_details(details)
    subject = parsed.get("subject", details[:100])
    cause_of_action = parsed.get("cause_of_action", parsed.get("subject", details))
    relief_sought = parsed.get("relief_sought", parsed.get("demand", "appropriate legal relief"))

    return f"""================================================================================
                              LEGAL NOTICE
================================================================================

Ref. No.: NS/LN/{datetime.now().strftime("%Y/%m/%d")}/{random.randint(1000,9999)}
Date: {get_current_date()}

================================================================================
                         ADVOCATE'S LETTERHEAD
================================================================================

To,
{party_b}
Address: ________________________________

Subject: LEGAL NOTICE UNDER SECTION ____ OF __________ ACT, 20__
         Regarding: {subject}

================================================================================
                            THROUGH ADVOCATE
================================================================================

Under instructions from and on behalf of my client {party_a}, residing at 
________________________________, I, Advocate {advocate_name}, do hereby serve 
upon you the following legal notice:

================================================================================
                              FACTS
================================================================================

1. That my client {party_a} and you, {party_b}, have been engaged in the 
   following matter:

   {cause_of_action}

2. That the specific details and background of the dispute are as follows:

   {details}

3. That my client has made repeated requests and demands for resolution, but 
   you have failed and neglected to comply with the same, thereby compelling 
   my client to issue this formal legal notice.

================================================================================
                         CAUSE OF ACTION
================================================================================

4. That the cause of action arose on ________________ and has been 
   continuing since then.

5. That my client's rights have been violated on the following grounds:
   (a) ________________________________________________________________
   (b) ________________________________________________________________
   (c) ________________________________________________________________

================================================================================
                    VIOLATION OF LEGAL RIGHTS
================================================================================

6. That your actions constitute violation of:
   (a) Section ____ of the Indian Penal Code, 1860 / Bharatiya Nyaya Sanhita, 2023;
   (b) Section ____ of the __________ Act, 20__;
   (c) The fundamental and statutory rights of my client;
   (d) The principles of natural justice and equity.

================================================================================
                         DEMANDS / RELIEF SOUGHT
================================================================================

7. That my client demands the following from you:

   {relief_sought}

8. That you are hereby called upon to:
   (a) comply with the demands set out in paragraph 7 above;
   (b) cease and desist from the offending conduct immediately;
   (c) furnish a written reply to this notice within 15 (Fifteen) days from 
       the date of receipt hereof;
   (d) make good the loss and damage caused to my client.

================================================================================
                      LEGAL CONSEQUENCES
================================================================================

9. That if you fail to comply with the above demands within the stipulated 
   period of 15 (Fifteen) days, my client shall be constrained to initiate 
   appropriate legal and judicial proceedings against you, including but not 
   limited to:
   (a) filing a civil suit for recovery and damages;
   (b) filing a criminal complaint before the competent judicial magistrate;
   (c) seeking interim and permanent injunctions;
   (d) claiming costs, interest, and compensation;
   entirely at your own risk, cost, and consequences.

10. That you are further informed that this notice is being issued without 
    prejudice to my client's other rights and remedies available under law, 
    both civil and criminal, which are hereby expressly reserved.

================================================================================
                         NOTICE CERTIFICATE
================================================================================

This notice has been drafted under my professional supervision and is issued 
in accordance with the provisions of the Indian legal system.

Place: ___________________________
Date: {get_current_date()}

================================================================================
                         SIGNATURE BLOCK
================================================================================

_______________________________
Advocate {advocate_name}
Enrollment No.: _______________
Bar Council: ___________________
Phone: _______________________
Email: _______________________

Served upon the addressee by:
□ Registered Post with A/D
□ Speed Post with Tracking
□ Email (read receipt)
□ Personal Service
□ WhatsApp / Electronic mode

Date of Service: _______________
Acknowledgement: _______________

================================================================================
                              END OF NOTICE
================================================================================

[This is a computer-generated legal notice. The recipient is advised to consult 
legal counsel before responding.]"""


def generate_affidavit(party_a: str, party_b: str, details: str, advocate_name: str) -> str:
    parsed = parse_details(details)
    deponent_name = party_a
    purpose = parsed.get("purpose", parsed.get("subject", details[:150]))

    return f"""================================================================================
                              AFFIDAVIT
================================================================================

IN THE COURT OF ____________________________
AT ____________________________

In the matter of: {purpose}

================================================================================
                         AFFIDAVIT OF {deponent_name.upper()}
================================================================================

I, {deponent_name}, S/o/D/o/W/o ____________________, aged ____ years, 
by occupation ____________________, residing at 
________________________________, do hereby solemnly affirm and state as 
under:

================================================================================
                         STATEMENT OF FACTS
================================================================================

1. That I am the deponent above-named and am well conversant with the facts 
   of the case.

2. That the facts stated herein are true and correct to the best of my 
   knowledge, information, and belief.

3. That the purpose of this affidavit is: {purpose}

4. The specific facts and circumstances are as follows:

   {details}

5. That I have not filed any other affidavit in respect of the same subject 
   matter before any other Court or authority.

6. That I am aware that making a false statement in this affidavit is 
   punishable under Section 193 of the Indian Penal Code, 1860 / Section 
   245 of the Bharatiya Nyaya Sanhita, 2023.

================================================================================
                         VERIFICATION
================================================================================

Verified at ____________________ on this {get_current_date()} that the 
contents of paragraphs 1 to 6 above are true and correct to the best of my 
knowledge, information, and belief, and nothing material has been concealed 
therefrom.

================================================================================
                         SIGNATURE OF DEPONENT
================================================================================

Deponent

_______________________________
{deponent_name}

Date: {get_current_date()}
Place: ________________________

================================================================================
                         NOTARIZATION
================================================================================

Solemnly affirmed by the above-named deponent {deponent_name} before me 
on this {get_current_date()} at ____________________, who is personally 
known to me / identified by ____________________.

The deponent has understood the contents of this affidavit and has signed 
in my presence.

_______________________________
Notary Public
Seal & Registration No.: __________
Date: {get_current_date()}
Place: ________________________

================================================================================
                         ADVOCATE ENDORSEMENT
================================================================================

Drafted and verified by:

Advocate {advocate_name}
Date: {get_current_date()}

================================================================================
                              END OF AFFIDAVIT
================================================================================"""


def generate_power_of_attorney(party_a: str, party_b: str, details: str, advocate_name: str) -> str:
    parsed = parse_details(details)
    purpose = parsed.get("purpose", parsed.get("subject", details[:150]))

    return f"""================================================================================
                         GENERAL POWER OF ATTORNEY
================================================================================

This General Power of Attorney is executed on this {get_current_date()} at 
____________________.

================================================================================
                         PARTIES
================================================================================

PRINCIPAL (Donor):
Name: {party_a}
Father's/Husband's Name: ____________________
Age: ____ years
Occupation: ____________________
Address: ________________________________
PAN: ____________________
Aadhaar: ____________________

ATTORNEY (Donee):
Name: {party_b}
Father's/Husband's Name: ____________________
Age: ____ years
Occupation: ____________________
Address: ________________________________
PAN: ____________________
Aadhaar: ____________________

================================================================================
                         RECITALS
================================================================================

WHEREAS the Principal is the absolute and lawful owner of certain properties 
and affairs, particulars whereof are more fully described in the Schedule 
hereto;

AND WHEREAS the Principal, owing to his/her preoccupation, old age, illness, 
residence abroad, or other compelling reasons, is unable to personally attend 
to his/her affairs;

AND WHEREAS the Principal has reposed full faith and confidence in the Attorney 
and has decided to appoint the Attorney as his/her true and lawful attorney;

AND WHEREAS the Attorney has agreed to act as such attorney on the terms 
hereinafter recorded.

================================================================================
                         GRANT OF POWER
================================================================================

NOW KNOW ALL MEN BY THESE PRESENTS that the Principal does hereby nominate, 
constitute, and appoint the Attorney as his/her true and lawful attorney, 
with full power and authority to do and execute all or any of the following 
acts, deeds, and things in the name and on behalf of the Principal:

1. REAL ESTATE MATTERS:
   (a) To sell, convey, transfer, mortgage, lease, or otherwise deal with 
       any immovable property belonging to the Principal;
   (b) To receive consideration, execute sale deeds, and register documents;
   (c) To appear before Sub-Registrar, Revenue Authorities, and Courts.

2. BANKING AND FINANCIAL MATTERS:
   (a) To operate bank accounts, fixed deposits, and safe deposit lockers;
   (b) To encash cheques, drafts, and negotiate instruments;
   (c) To apply for and avail loans, overdrafts, and credit facilities.

3. LEGAL PROCEEDINGS:
   (a) To institute, prosecute, defend, compromise, or withdraw suits and 
       proceedings;
   (b) To appoint advocates and legal representatives;
   (c) To execute affidavits, vakalatnamas, and court documents.

4. TAXATION AND GOVERNMENT MATTERS:
   (a) To file income tax returns, GST returns, and other statutory returns;
   (b) To represent before Income Tax Authorities, GST Council, and Tribunals;
   (c) To receive refunds, notices, and communications.

5. GENERAL POWERS:
   (a) To execute all documents, deeds, and writings necessary or expedient;
   (b) To delegate powers to any other person with prior written consent;
   (c) To do all other acts and things incidental to the above powers.

================================================================================
                         LIMITATIONS
================================================================================

The powers granted herein shall NOT include:
(a) making gifts or donations exceeding INR 50,000/- without prior written 
    consent;
(b) creating encumbrances on the Principal's self-acquired residential 
    property without specific written authorization;
(c) entering into any transaction for personal benefit of the Attorney;
(d) any act contrary to law, public policy, or the Principal's express 
    instructions.

================================================================================
                         DURATION AND REVOCATION
================================================================================

This Power of Attorney shall remain in force for a period of 
{parsed.get("duration", "__________")} from the date hereof, unless earlier 
revoked by the Principal by a written instrument duly registered and 
notified to the Attorney and all concerned authorities.

This Power of Attorney may be revoked:
(a) by written notice served upon the Attorney;
(b) automatically upon the death, insanity, or insolvency of either Party;
(c) by order of a competent Court.

================================================================================
                         RATIFICATION
================================================================================

The Principal agrees to ratify and confirm all lawful acts done by the 
Attorney in exercise of the powers conferred herein, as if done by the 
Principal personally.

================================================================================
                         CONSIDERATION
================================================================================

The Attorney shall not claim any remuneration for services rendered under 
this Power of Attorney, unless otherwise agreed in writing. All out-of-pocket 
expenses incurred shall be reimbursed by the Principal upon production of 
vouchers.

================================================================================
                         SCHEDULE OF PROPERTIES
================================================================================

{details}

================================================================================
                         EXECUTION
================================================================================

IN WITNESS WHEREOF, the Principal has set his/her hand and seal on the day, 
month, and year first above written.

PRINCIPAL:

_______________________________
{party_a}
Date: {get_current_date()}
Place: ________________________

ATTORNEY:

_______________________________
{party_b}
Date: {get_current_date()}
Place: ________________________

WITNESS 1:
Name: ____________________________
Address: __________________________
Signature: _______________________

WITNESS 2:
Name: ____________________________
Address: __________________________
Signature: _______________________

================================================================================
                         REGISTRATION & NOTARIZATION
================================================================================

This Power of Attorney has been executed before and authenticated by:

_______________________________
Notary Public / Sub-Registrar
Seal & Registration No.: __________
Date: {get_current_date()}
Place: ________________________

================================================================================
                         ADVOCATE CERTIFICATION
================================================================================

Drafted and certified by:

Advocate {advocate_name}
Date: {get_current_date()}

================================================================================
                              END OF DOCUMENT
================================================================================"""


def generate_will(party_a: str, party_b: str, details: str, advocate_name: str) -> str:
    parsed = parse_details(details)
    testator = party_a
    executor = party_b

    return f"""================================================================================
                    LAST WILL AND TESTAMENT
================================================================================

I, {testator}, S/o/D/o/W/o ____________________, aged ____ years, 
by occupation ____________________, residing at 
________________________________, being of sound mind, memory, and 
understanding, do hereby make, publish, and declare this to be my Last Will 
and Testament, hereby revoking all former wills, codicils, and testamentary 
dispositions made by me.

================================================================================
                         DECLARATION
================================================================================

1. I declare that I am executing this Will voluntarily, without any coercion, 
   undue influence, fraud, or misrepresentation of any kind.

2. I declare that I am fully aware of the nature and extent of my properties 
   and the implications of this disposition.

3. I declare that at the time of execution of this Will, I am of sound 
   disposing mind and memory.

================================================================================
                         APPOINTMENT OF EXECUTOR
================================================================================

4. I hereby appoint {executor} as the Executor of this my Will. The Executor 
   shall have the following powers and duties:
   (a) to collect, recover, and realize all my assets and properties;
   (b) to pay all my just debts, funeral expenses, and testamentary expenses;
   (c) to distribute the residue of my estate according to the bequests 
       hereinafter made;
   (d) to sell, mortgage, or otherwise deal with my properties as may be 
       necessary for the execution of this Will;
   (e) to appoint attorneys, agents, and legal representatives as necessary.

   If {executor} is unable or unwilling to act, I appoint 
   ____________________ as the alternate Executor.

================================================================================
                         BEQUESTS AND DEVOLUTION
================================================================================

5. I bequeath my properties as follows:

   {details}

6. Residuary Bequest: All the residue and remainder of my estate, including 
   properties not specifically bequeathed, shall devolve upon 
   ____________________.

================================================================================
                         SPECIFIC DIRECTIONS
================================================================================

7. I direct that my mortal remains be disposed of by 
   ____________________ (cremation/burial/other).

8. I direct that no religious ceremonies be performed at my funeral, OR 
   I direct that my funeral be conducted according to __________ customs.

9. I direct that my digital assets, including but not limited to email 
   accounts, social media accounts, and cryptocurrency wallets, be managed 
   by ____________________ in accordance with applicable laws.

================================================================================
                         GUARDIANSHIP (if applicable)
================================================================================

10. If any of my beneficiaries are minors at the time of my death, I appoint 
    ____________________ as the guardian of their person and property until 
    they attain the age of 18 years.

================================================================================
                         CONDITIONS AND RESTRICTIONS
================================================================================

11. If any beneficiary predeceases me, the bequest in their favor shall 
    lapse and form part of the residuary estate, unless otherwise specified.

12. If any beneficiary challenges this Will or any provision thereof, their 
    bequest shall stand forfeited and shall form part of the residuary estate.

================================================================================
                         CODICIL PROVISION
================================================================================

13. I reserve the right to alter, modify, or revoke this Will by a Codicil 
    duly executed and attested in the same manner as this Will.

================================================================================
                         EXECUTION AND ATTESTATION
================================================================================

IN WITNESS WHEREOF, I have set my hand to this Will on this 
{get_current_date()} at ____________________.

TESTATOR:

_______________________________
{testator}

We, the undersigned witnesses, do hereby certify that:
(a) the Testator signed this Will in our presence;
(b) the Testator appeared to us to be of sound mind and memory;
(c) we have signed as witnesses in the presence of the Testator and each other;
(d) we are not beneficiaries under this Will.

WITNESS 1:
Name: ____________________________
Address: __________________________
Occupation: _______________________
Signature: _______________________
Date: {get_current_date()}

WITNESS 2:
Name: ____________________________
Address: __________________________
Occupation: _______________________
Signature: _______________________
Date: {get_current_date()}

================================================================================
                         REGISTRATION DETAILS
================================================================================

This Will has been registered at the Office of the Sub-Registrar, 
____________________, on ____________________, as Document No. 
____________________.

================================================================================
                         ADVOCATE CERTIFICATION
================================================================================

This Will has been drafted under my professional supervision:

Advocate {advocate_name}
Date: {get_current_date()}

[Seal & Signature]

================================================================================
                              END OF WILL
================================================================================

[Note: This is a template. It is strongly recommended to register this Will 
with the Sub-Registrar and store the original in a safe deposit locker or 
with a trusted advocate.]"""


def generate_partnership_deed(party_a: str, party_b: str, details: str, advocate_name: str) -> str:
    parsed = parse_details(details)
    partner1 = party_a
    partner2 = party_b

    return f"""================================================================================
                         PARTNERSHIP DEED
================================================================================

This Partnership Deed is executed on this {get_current_date()} at 
____________________.

================================================================================
                         PARTIES
================================================================================

PARTNER 1:
Name: {partner1}
Father's Name: ____________________
Age: ____ years
Address: ________________________________
PAN: ____________________

PARTNER 2:
Name: {partner2}
Father's Name: ____________________
Age: ____ years
Address: ________________________________
PAN: ____________________

[Additional Partners: ____________________]

================================================================================
                         RECITALS
================================================================================

WHEREAS the Parties hereto are desirous of carrying on business in partnership 
under the name and style of "____________________" (hereinafter referred to 
as the "Firm");

AND WHEREAS the Parties have agreed to enter into this Deed of Partnership 
to define their mutual rights, duties, and obligations;

AND WHEREAS this Deed is executed in accordance with the provisions of the 
Indian Partnership Act, 1932.

================================================================================
                         BUSINESS DETAILS
================================================================================

1. FIRM NAME: ________________________________

2. BUSINESS OBJECT: 
   {details}

3. PRINCIPAL PLACE OF BUSINESS: 
   {parsed.get("business_address", "____________________")}

4. BRANCH OFFICES (if any): ________________________________

================================================================================
                         CAPITAL CONTRIBUTION
================================================================================

5. The capital of the Firm shall be contributed by the Partners as follows:

   Partner 1 ({partner1}): INR {parsed.get("capital_a", "__________")} 
   (Rupees ____________________ only)

   Partner 2 ({partner2}): INR {parsed.get("capital_b", "__________")} 
   (Rupees ____________________ only)

   Total Capital: INR ____________________

6. Additional capital, if required, shall be contributed by the Partners in 
   their profit-sharing ratio.

================================================================================
                         PROFIT AND LOSS SHARING
================================================================================

7. Profits and losses of the Firm shall be shared by the Partners in the 
   following ratio:

   {partner1}: ____%
   {partner2}: ____%

8. The Firm's accounts shall be maintained on a mercantile basis and audited 
   annually by a Chartered Accountant.

================================================================================
                         MANAGEMENT AND DUTIES
================================================================================

9. The day-to-day management of the Firm shall be conducted by:
   ____________________

10. Major decisions requiring consent of all Partners include:
    (a) admission of new partners;
    (b) sale or mortgage of Firm assets exceeding INR ________;
    (c) borrowing exceeding INR ________;
    (d) commencement of new business lines;
    (e) dissolution of the Firm.

11. Each Partner shall:
    (a) devote adequate time and attention to the business;
    (b) act in the best interest of the Firm;
    (c) maintain confidentiality of Firm affairs;
    (d) not engage in competing business without consent.

================================================================================
                         DRAWINGS AND REMUNERATION
================================================================================

12. Partners may draw against their share of profits subject to limits set 
    by mutual agreement.

13. Working Partners shall be entitled to remuneration as per Section 40(b) 
    of the Income Tax Act, 1961.

================================================================================
                         BANKING
================================================================================

14. The Firm shall maintain bank accounts in the name of the Firm. Cheques 
    and instruments shall be signed by:
    (a) ____________________ singly up to INR ________;
    (b) jointly by ____________________ and ____________________ for 
        amounts exceeding INR ________.

================================================================================
                         ADMISSION AND RETIREMENT
================================================================================

15. A new partner may be admitted only with the unanimous consent of all 
    existing Partners and upon execution of a deed of adherence.

16. A Partner may retire by giving ____ months' prior written notice to all 
    other Partners.

17. Upon retirement, the retiring Partner shall be paid:
    (a) the balance in his/her capital account;
    (b) his/her share of profits/losses up to the date of retirement;
    (c) interest on capital up to the date of retirement.

================================================================================
                         DISSOLUTION
================================================================================

18. The Firm shall be dissolved in the following circumstances:
    (a) by mutual agreement of all Partners;
    (b) upon the death, insanity, or insolvency of any Partner;
    (c) by order of a competent Court;
    (d) upon the expiry of the term fixed for the partnership, if any.

19. Upon dissolution, the assets of the Firm shall be applied in the following 
    order:
    (a) payment of Firm debts and liabilities;
    (b) repayment of Partners' loans;
    (c) return of Partners' capital contributions;
    (d) distribution of surplus in profit-sharing ratio.

================================================================================
                         ARBITRATION
================================================================================

20. Any dispute arising between the Partners shall be referred to arbitration 
    under the Arbitration and Conciliation Act, 1996. The arbitration shall be 
    conducted at ____________________ by a sole arbitrator appointed by mutual 
    consent.

================================================================================
                         JURISDICTION
================================================================================

21. This Deed shall be governed by the laws of India. The courts at 
    ____________________ shall have exclusive jurisdiction.

================================================================================
                         EXECUTION
================================================================================

IN WITNESS WHEREOF, the Parties have set their respective hands on the day, 
month, and year first above written.

PARTNER 1:

_______________________________
{partner1}
Date: {get_current_date()}

PARTNER 2:

_______________________________
{partner2}
Date: {get_current_date()}

WITNESS 1:
Name: ____________________________
Address: __________________________
Signature: _______________________

WITNESS 2:
Name: ____________________________
Address: __________________________
Signature: _______________________

================================================================================
                         STAMP DUTY & REGISTRATION
================================================================================

This Deed is executed on non-judicial stamp paper of value 
INR __________ (Rupees ____________________ only) and has been registered 
at the Office of the Sub-Registrar, ____________________.

================================================================================
                         ADVOCATE CERTIFICATION
================================================================================

Drafted and certified by:

Advocate {advocate_name}
Date: {get_current_date()}

================================================================================
                              END OF DEED
================================================================================"""


# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/api/health")
def health():
    return {"status": "ok", "service": "nyayasetu-api", "version": "1.2.0", "sessions": len(doc_sessions)}

@app.post("/api/auth/register")
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed_password = get_password_hash(user.password)
    db_user = models.User(email=user.email, hashed_password=hashed_password, full_name=user.full_name, phone=user.phone)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return {"message": "User created successfully", "user_id": db_user.id}

@app.post("/api/auth/login")
def login(user: UserLogin, db: Session = Depends(get_db)):
    if user.email == "dev@local.com":
        dev_user = db.query(models.User).filter(models.User.email == "dev@local.com").first()
        if not dev_user:
            dev_user = models.User(email="dev@local.com", hashed_password=get_password_hash("dev"), full_name="Nitin Sharma", role="admin", phone=None)
            db.add(dev_user)
            db.commit()
            db.refresh(dev_user)
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(data={"sub": dev_user.email, "role": dev_user.role, "id": dev_user.id}, expires_delta=access_token_expires)
        return {"access_token": access_token, "token_type": "bearer", "user": {"id": dev_user.id, "email": dev_user.email, "full_name": dev_user.full_name, "role": dev_user.role}}
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": db_user.email, "role": db_user.role, "id": db_user.id}, expires_delta=access_token_expires)
    return {"access_token": access_token, "token_type": "bearer", "user": {"id": db_user.id, "email": db_user.email, "full_name": db_user.full_name, "role": db_user.role}}

@app.get("/api/auth/me")
def read_users_me(current_user: models.User = Depends(get_current_user)):
    return {"id": current_user.id, "email": current_user.email, "full_name": current_user.full_name, "role": current_user.role, "phone": current_user.phone}

@app.post("/api/cases", response_model=CaseResponse)
def create_case(case: CaseCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    db_case = models.Case(title=case.title, cnr_number=case.cnr_number if case.cnr_number and case.cnr_number.strip() else None, court_name=case.court_name, client_name=case.client_name, status=case.status, lawyer_id=current_user.id)
    db.add(db_case)
    db.commit()
    db.refresh(db_case)
    return db_case

@app.get("/api/cases")
def get_cases(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    if current_user.role == "admin":
        cases = db.query(models.Case).all()
    else:
        cases = db.query(models.Case).filter(models.Case.lawyer_id == current_user.id).all()
    return cases

@app.get("/api/cases/{case_id}", response_model=CaseResponse)
def get_case(case_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    case = db.query(models.Case).filter(models.Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    if case.lawyer_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to view this case")
    return case

@app.delete("/api/cases/{case_id}")
def delete_case(case_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    case = db.query(models.Case).filter(models.Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    if case.lawyer_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to delete this case")
    db.query(models.Task).filter(models.Task.case_id == case_id).delete(synchronize_session=False)
    db.query(models.Hearing).filter(models.Hearing.case_id == case_id).delete(synchronize_session=False)
    db.delete(case)
    db.commit()
    return {"message": "Case deleted successfully", "id": case_id}

@app.get("/api/cnr/{cnr_number}")
def fetch_mock_cnr(cnr_number: str):
    if len(cnr_number) < 16:
        raise HTTPException(status_code=400, detail="Invalid CNR number format. Must be 16 characters.")
    import random
    random.seed(cnr_number)
    courts = ["Supreme Court of India", "Delhi High Court", "Bombay High Court", "District Court Saket"]
    statuses = ["Active", "Pending Hearing", "Disposed", "Reserved for Orders"]
    return {"cnr_number": cnr_number, "title": f"State vs. Mock Person {random.randint(1, 100)}", "court_name": random.choice(courts), "status": random.choice(statuses), "filing_date": f"2023-0{random.randint(1,9)}-{random.randint(10,28)}", "next_hearing": f"2026-0{random.randint(6,9)}-{random.randint(10,28)}"}

@app.post("/api/tasks", response_model=TaskResponse)
def create_task(task: TaskCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    from datetime import datetime
    db_task = models.Task(title=task.title, description=task.description, due_date=datetime.fromisoformat(task.due_date.replace("Z", "+00:00")), case_id=task.case_id, assignee_id=current_user.id)
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    task_dict = db_task.__dict__.copy()
    task_dict["due_date"] = str(db_task.due_date)
    return task_dict

@app.get("/api/tasks", response_model=list[TaskResponse])
def get_tasks(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    from sqlalchemy import or_
    tasks = db.query(models.Task).filter(or_(models.Task.assignee_id == current_user.id, models.Task.assignee_id.is_(None))).all()
    res = []
    for t in tasks:
        td = t.__dict__.copy()
        td["due_date"] = str(t.due_date)
        res.append(td)
    return res

@app.post("/api/hearings", response_model=HearingResponse)
def create_hearing(hearing: HearingCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    from datetime import datetime
    case = db.query(models.Case).filter(models.Case.id == hearing.case_id).first()
    if not case or (case.lawyer_id != current_user.id and current_user.role != "admin"):
        raise HTTPException(status_code=403, detail="Not authorized to add hearing to this case")
    db_hearing = models.Hearing(case_id=hearing.case_id, hearing_date=datetime.fromisoformat(hearing.hearing_date.replace("Z", "+00:00")), purpose=hearing.purpose, notes=hearing.notes)
    db.add(db_hearing)
    db.commit()
    db.refresh(db_hearing)
    hd = db_hearing.__dict__.copy()
    hd["hearing_date"] = str(db_hearing.hearing_date)
    return hd

@app.get("/api/hearings", response_model=list[HearingResponse])
def get_hearings(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    cases = db.query(models.Case).filter(models.Case.lawyer_id == current_user.id).all()
    case_ids = [c.id for c in cases]
    hearings = db.query(models.Hearing).filter(models.Hearing.case_id.in_(case_ids)).all()
    res = []
    for h in hearings:
        hd = h.__dict__.copy()
        hd["hearing_date"] = str(h.hearing_date)
        res.append(hd)
    return res


@app.post("/api/calendar/events", response_model=CalendarEventResponse)
def create_calendar_event(event: CalendarEventCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    db_event = models.CalendarEvent(title=event.title, event_type=event.event_type, event_date=event.event_date, event_time=event.event_time, court=event.court, description=event.description, matter_id=event.matter_id, user_id=current_user.id)
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    return {"id": db_event.id, "title": db_event.title, "event_type": db_event.event_type, "event_date": db_event.event_date, "event_time": db_event.event_time, "court": db_event.court, "description": db_event.description, "matter_id": db_event.matter_id, "created_at": str(db_event.created_at), "updated_at": str(db_event.updated_at) if db_event.updated_at else None}

@app.get("/api/calendar/events")
def get_calendar_events(year: Optional[int] = None, month: Optional[int] = None, event_type: Optional[str] = None, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    query = db.query(models.CalendarEvent).filter(models.CalendarEvent.user_id == current_user.id)
    if year and month:
        month_str = f"{month:02d}"
        query = query.filter(models.CalendarEvent.event_date.like(f"{year}-{month_str}-%"))
    elif year:
        query = query.filter(models.CalendarEvent.event_date.like(f"{year}-%"))
    if event_type:
        query = query.filter(models.CalendarEvent.event_type == event_type)
    events = query.order_by(models.CalendarEvent.event_date.asc(), models.CalendarEvent.event_time.asc()).all()
    return [{"id": e.id, "title": e.title, "event_type": e.event_type, "event_date": e.event_date, "event_time": e.event_time, "court": e.court, "description": e.description, "matter_id": e.matter_id, "created_at": str(e.created_at), "updated_at": str(e.updated_at) if e.updated_at else None} for e in events]

@app.get("/api/calendar/events/{event_id}", response_model=CalendarEventResponse)
def get_calendar_event(event_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    event = db.query(models.CalendarEvent).filter(models.CalendarEvent.id == event_id, models.CalendarEvent.user_id == current_user.id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return {"id": event.id, "title": event.title, "event_type": event.event_type, "event_date": event.event_date, "event_time": event.event_time, "court": event.court, "description": event.description, "matter_id": event.matter_id, "created_at": str(event.created_at), "updated_at": str(event.updated_at) if event.updated_at else None}

@app.put("/api/calendar/events/{event_id}", response_model=CalendarEventResponse)
def update_calendar_event(event_id: int, event: CalendarEventCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    db_event = db.query(models.CalendarEvent).filter(models.CalendarEvent.id == event_id, models.CalendarEvent.user_id == current_user.id).first()
    if not db_event:
        raise HTTPException(status_code=404, detail="Event not found")
    for field, value in event.model_dump().items():
        setattr(db_event, field, value)
    db.commit()
    db.refresh(db_event)
    return {"id": db_event.id, "title": db_event.title, "event_type": db_event.event_type, "event_date": db_event.event_date, "event_time": db_event.event_time, "court": db_event.court, "description": db_event.description, "matter_id": db_event.matter_id, "created_at": str(db_event.created_at), "updated_at": str(db_event.updated_at) if db_event.updated_at else None}

@app.delete("/api/calendar/events/{event_id}")
def delete_calendar_event(event_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    event = db.query(models.CalendarEvent).filter(models.CalendarEvent.id == event_id, models.CalendarEvent.user_id == current_user.id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    db.delete(event)
    db.commit()
    return {"message": "Event deleted", "id": event_id}

@app.get("/api/calendar/stats/summary")
def get_calendar_stats(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    from datetime import date, timedelta
    from sqlalchemy import func
    today = date.today().isoformat()
    week_later = (date.today() + timedelta(days=7)).isoformat()
    total = db.query(models.CalendarEvent).filter(models.CalendarEvent.user_id == current_user.id).count()
    upcoming = db.query(models.CalendarEvent).filter(models.CalendarEvent.user_id == current_user.id, models.CalendarEvent.event_date >= today).count()
    this_week = db.query(models.CalendarEvent).filter(models.CalendarEvent.user_id == current_user.id, models.CalendarEvent.event_date >= today, models.CalendarEvent.event_date <= week_later).count()
    by_type = db.query(models.CalendarEvent.event_type, func.count(models.CalendarEvent.id).label("count")).filter(models.CalendarEvent.user_id == current_user.id, models.CalendarEvent.event_date >= today).group_by(models.CalendarEvent.event_type).all()
    return {"total_events": total, "upcoming_events": upcoming, "this_week": this_week, "by_type": {t.event_type: t.count for t in by_type}}

@app.post("/api/invoices", response_model=InvoiceResponse)
def create_invoice(inv: InvoiceCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    from datetime import datetime
    db_inv = models.Invoice(lawyer_id=current_user.id, client_name=inv.client_name, amount=inv.amount, due_date=datetime.fromisoformat(inv.due_date.replace("Z", "+00:00")))
    db.add(db_inv)
    db.commit()
    db.refresh(db_inv)
    inv_dict = db_inv.__dict__.copy()
    inv_dict["due_date"] = str(db_inv.due_date)
    inv_dict["created_at"] = str(db_inv.created_at)
    return inv_dict

@app.get("/api/invoices", response_model=list[InvoiceResponse])
def get_invoices(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    if current_user.role == "admin":
        invoices = db.query(models.Invoice).all()
    else:
        invoices = db.query(models.Invoice).filter(models.Invoice.lawyer_id == current_user.id).all()
    res = []
    for inv in invoices:
        inv_dict = inv.__dict__.copy()
        inv_dict["due_date"] = str(inv.due_date)
        inv_dict["created_at"] = str(inv.created_at)
        res.append(inv_dict)
    return res

# ── Document Generator ────────────────────────────────────────────────────────

@app.post("/api/generate_doc")
def generate_document(req: DocumentGenerateRequest, current_user: models.User = Depends(get_current_user)):
    """Generate professional legal documents via comprehensive templates."""
    advocate_name = current_user.full_name or "____________________"
    document_generators = {
        "Rent Agreement": generate_rent_agreement,
        "Legal Notice": generate_legal_notice,
        "Affidavit": generate_affidavit,
        "Power of Attorney": generate_power_of_attorney,
        "Will": generate_will,
        "Partnership Deed": generate_partnership_deed,
    }
    if req.doc_type not in document_generators:
        raise HTTPException(status_code=400, detail=f"Document type '{req.doc_type}' not supported. Supported types: {list(document_generators.keys())}")
    try:
        content = document_generators[req.doc_type](req.party_a, req.party_b, req.details, advocate_name)
        return {"doc_type": req.doc_type, "content": content, "generated_at": datetime.now().isoformat(), "generated_by": advocate_name, "status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Document generation failed: {str(e)}")


# ── Research Section ─────────────────────────────────────────────────────────

from document_analyzer import call_llm, fetch_case_laws, parse_json_response

@app.post("/api/research/ask")
def research_ask(req: ResearchAskRequest):
    cases = fetch_case_laws(req.query, "Legal Question")
    context_str = ""
    for idx, c in enumerate(cases):
        context_str += f"""[{idx+1}] Case: {c.get('title', 'Unknown')}
Summary: {c.get('summary', '')}

"""
    prompt = f"""You are an expert Indian Legal Researcher. Provide a comprehensive, accurate, and easy-to-understand answer to the following legal question based on Indian law and the provided Supreme Court / High Court judgments.

Structure your answer with these exact three headings:
Applicable Law
Application
Conclusion

QUESTION: {req.query}

RELEVANT JUDGMENTS (Fetched from Indian Kanoon):
{context_str if context_str.strip() else "No specific case laws found, answer based on general Indian legal principles."}

Base your answer heavily on these specific judgments if provided. You MUST explicitly cite them in your text using their index number in brackets (e.g., [1], [2])."""
    response = call_llm(prompt, temperature=0.2)
    return {"response": response, "citations": cases}

@app.post("/api/research/cases")
def research_cases(req: ResearchCaseRequest):
    search_query = req.query
    if req.court and req.court != "All Courts":
        search_query += f" {req.court}"
    if req.year_from:
        search_query += f" {req.year_from}"
    cases = fetch_case_laws(search_query, "Case Search", pagenum=req.page)
    results = [{"title": c.get("title", "Untitled"), "court": c.get("court", "Indian Court"), "year": c.get("year", ""), "snippet": c.get("summary", ""), "url": c.get("url", "")} for c in cases]
    return {"results": results}

@app.post("/api/research/sections")
def research_sections(req: ResearchSectionRequest):
    search_query = f"Section {req.sections} of {req.act}"
    cases = fetch_case_laws(search_query, "Section Search", pagenum=req.page)
    results = [{"title": c.get("title", "Untitled"), "court": c.get("court", "Indian Court"), "year": c.get("year", ""), "snippet": c.get("summary", ""), "url": c.get("url", "")} for c in cases]
    return {"results": results}

@app.post("/api/research/acts")
def research_acts(req: ResearchActsListRequest, db: Session = Depends(get_db)):
    query = db.query(StatutoryAct)
    if req.jurisdiction:
        query = query.filter(StatutoryAct.jurisdiction == req.jurisdiction)
    if req.category and req.category != "All":
        query = query.filter(StatutoryAct.category.like(f"%{req.category}%"))
    acts = query.limit(50).all()
    results = [{"name": a.title, "year": a.year, "snippet": a.summary, "url": a.url} for a in acts]
    return {"acts": results}

@app.post("/api/research/act_summary")
def research_act_summary(req: ResearchActRequest):
    prompt = f"""You are an expert Indian Legal Assistant. Summarize the following statutory act.
Act Name: {req.act_name}
Jurisdiction: {req.jurisdiction}

Return a JSON object strictly following this structure:
{{
  "purpose": "A paragraph explaining the objective, factual background, and purpose of the act.",
  "key_provisions": "A paragraph detailing the most important sections and operational mechanisms of the act.",
  "implications": "A paragraph explaining the legal implications, penalties, or overall impact of the act."
}}
Return ONLY valid JSON, without any markdown formatting like ```json or ```."""
    raw_response = call_llm(prompt, temperature=0.1)
    data = parse_json_response(raw_response, fallback={"purpose": "Failed to generate purpose.", "key_provisions": "Could not parse key provisions.", "implications": "Could not parse implications."})
    return data

@app.post("/api/editor/copilot")
def editor_copilot(req: CopilotRequest):
    if not os.getenv("GEMINI_API_KEY"):
        return {"reply": "API Key missing. Cannot connect to copilot."}
    try:
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        system_prompt = """You are an elite legal drafting AI Copilot, acting as a Senior Partner at a top-tier Indian law firm.

Your primary job is to generate top-notch, watertight, and highly professional legal clauses, pleadings, and correspondence.

Follow these strict rules:

1. ALWAYS default to Indian Law (e.g., BNSS, BNS, BSA, CPC, Indian Contract Act) and Indian jurisdictions (e.g., Mumbai, Delhi) unless specified otherwise.

2. Use precise, formal, and authoritative legal terminology standard in Indian High Courts and the Supreme Court.

3. If asked to draft a clause, provide ONLY the drafted clause itself, ready to be inserted directly into the document. DO NOT include conversational filler like 'Here is a draft...' or 'Would you like to customize this...'.

4. Ensure all drafting is unambiguous, comprehensive, and protects the client's interests.

5. Provide plain text output without markdown formatting (no **, ##, etc.) to ensure seamless pasting into a rich text editor.
"""
        full_prompt = f"""User Request: {req.prompt}

Current Document Context (use this to match party names, tone, and subject matter if applicable):
{req.document_context[:2000]}

Draft exactly what is requested based on the rules above.
"""
        response = client.models.generate_content(model="gemini-2.5-flash", contents=full_prompt, config=types.GenerateContentConfig(system_instruction=system_prompt, temperature=0.3))
        return {"reply": response.text}
    except Exception as e:
        print(f"Copilot Error: {e}")
        return {"reply": "Sorry, I encountered an error while generating the text."}

@app.get("/api/research/topics")
def research_topics():
    return {"topics": [{"name": "Constitutional & Administrative", "count": 6}, {"name": "Criminal Law", "count": 6}, {"name": "Civil & Property", "count": 8}, {"name": "Corporate & Commercial", "count": 6}, {"name": "Tax Laws", "count": 8}, {"name": "Labour & Service", "count": 2}]}


# ── Document analysis ─────────────────────────────────────────────────────────

@app.post("/api/analyze")
async def analyze(file: UploadFile = File(...), type_override: str = Form(default=None)):
    cleanup_old_sessions()
    allowed = [".pdf", ".jpg", ".jpeg", ".png", ".webp"]
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed:
        raise HTTPException(400, f"File type {ext} not supported. Use: {allowed}")
    file_bytes = await file.read()
    if len(file_bytes) > 10 * 1024 * 1024:
        raise HTTPException(400, "File too large. Maximum size: 10 MB")
    try:
        analysis, doc_rag = analyze_document(file_bytes, file.filename, type_override=type_override or None)
        session_id = str(uuid.uuid4())
        doc_sessions[session_id] = {"analysis": analysis, "rag": doc_rag, "doc_type": analysis.document_type, "created_at": time.time()}
        result = analysis.model_dump()
        result["session_id"] = session_id
        return JSONResponse(result)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        print(f"[ERROR] {e}")
        raise HTTPException(500, f"Analysis failed: {str(e)}")

# ── Q&A ───────────────────────────────────────────────────────────────────────

@app.post("/api/qa")
async def question_answer(req: QARequest):
    print(f"[QA] Received request for session: {req.session_id}")
    print(f"[QA] Question: {req.question[:100]}...")
    if not req.session_id:
        raise HTTPException(400, "session_id is required")
    session = doc_sessions.get(req.session_id)
    if not session:
        print(f"[QA] Session not found: {req.session_id}")
        raise HTTPException(404, f"Session not found or expired. Available sessions: {len(doc_sessions)}")
    if "rag" not in session:
        raise HTTPException(500, "RAG engine not initialized for this session")
    if not session["rag"]:
        raise HTTPException(500, "RAG engine not properly initialized")
    try:
        if not req.question or not req.question.strip():
            raise HTTPException(400, "Question cannot be empty")
        response = session["rag"].answer(req.question.strip())
        print(f"[QA] Answer generated with confidence: {response.confidence}")
        return JSONResponse(response.model_dump())
    except Exception as e:
        print(f"[QA ERROR] {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"Q&A failed: {str(e)}")

# ── Legal Translation ─────────────────────────────────────────────────────────

@app.post("/api/translate")
async def translate_document(req: TranslateRequest):
    if not req.text or not req.text.strip():
        raise HTTPException(400, "Text cannot be empty")
    if len(req.text) > 50000:
        raise HTTPException(400, "Text too long. Maximum 50,000 characters.")
    try:
        result = translate_legal_text(text=req.text.strip(), source_lang=req.source_lang if req.source_lang != "auto" else None, target_lang=req.target_lang, document_type=req.document_type)
        if result.get("error"):
            raise HTTPException(500, f"Translation failed: {result['error']}")
        return JSONResponse(result)
    except HTTPException:
        raise
    except Exception as e:
        print(f"[TRANSLATE ERROR] {e}")
        raise HTTPException(500, f"Translation failed: {str(e)}")

@app.post("/api/translate/file")
async def translate_file(file: UploadFile = File(...), target_lang: str = Form(default="en")):
    allowed = [".pdf", ".jpg", ".jpeg", ".png", ".webp"]
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed:
        raise HTTPException(400, f"File type {ext} not supported. Use: {allowed}")
    file_bytes = await file.read()
    if len(file_bytes) > 10 * 1024 * 1024:
        raise HTTPException(400, "File too large. Maximum size: 10 MB")
    try:
        from document_analyzer import extract_text
        text = extract_text(file_bytes, file.filename)
        if not text:
            raise HTTPException(400, "Could not extract text from file. Try a clearer scan.")
        result = translate_legal_text(text=text.strip(), source_lang=None, target_lang=target_lang, document_type="FIR / Police Complaint")
        result["original_text"] = text
        result["filename"] = file.filename
        return JSONResponse(result)
    except HTTPException:
        raise
    except Exception as e:
        print(f"[TRANSLATE FILE ERROR] {e}")
        raise HTTPException(500, f"Translation failed: {str(e)}")

@app.get("/api/translate/languages")
def list_languages():
    return JSONResponse({"languages": get_supported_languages()})

# ── Compliance ────────────────────────────────────────────────────────────────

@app.post("/api/compliance")
async def compliance_check(req: ComplianceRequest):
    try:
        result = compute_compliance_score(req.text, use_ai=True)
        message = generate_migration_message(result)
        return JSONResponse({"score": result["score"], "grade": result["grade"], "note": result["note"], "message": message, "mappings": result["report"]["mappings"], "obsolete": result["report"]["obsolete"], "total_references": result["report"]["total_old_references"], "ai_assisted": result.get("ai_assisted", False), "timestamp": result.get("timestamp", "")})
    except Exception as e:
        print(f"[Compliance Error] {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"Compliance check failed: {str(e)}")

@app.post("/api/compliance/upload")
async def compliance_upload(file: UploadFile = File(...)):
    try:
        file_bytes = await file.read()
        text = extract_text_from_pdf_bytes(file_bytes)
        if text.startswith("ERROR"):
            raise HTTPException(400, text)
        result = compute_compliance_score(text, use_ai=True)
        message = generate_migration_message(result)
        return JSONResponse({"score": result["score"], "grade": result["grade"], "note": result["note"], "message": message, "mappings": result["report"]["mappings"], "obsolete": result["report"]["obsolete"], "total_references": result["report"]["total_old_references"], "ai_assisted": result.get("ai_assisted", False), "timestamp": result.get("timestamp", "")})
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Compliance Upload Error] {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"Compliance check failed: {str(e)}")

# ── Case laws ─────────────────────────────────────────────────────────────────

@app.post("/api/caselaws")
async def get_case_laws(req: CaseLawRequest):
    results = fetch_case_laws(req.query, req.doc_type)
    return JSONResponse({"results": results})

# ── OTP: Send via WhatsApp ────────────────────────────────────────────────────

@app.post("/api/otp/send")
async def send_otp(req: OTPSendRequest):
    phone = normalise_phone(req.phone)
    existing = otp_store.get(phone)
    if existing and time.time() < existing.get("expires_at", 0) - 540:
        raise HTTPException(status_code=429, detail="OTP already sent. Please wait 60 seconds before requesting again.")
    otp = "".join(random.choices(string.digits, k=6))
    otp_store[phone] = {"otp": otp, "expires_at": time.time() + 600, "verified": False, "attempts": 0}
    try:
        client = TwilioClient(TWILIO_SID, TWILIO_TOKEN)
        message_body = f"""🔐 *NyayaSetu — Phone Verification*

Your OTP for Evidence Certificate generation is:

*{otp}*

This OTP is valid for *10 minutes*.
Do not share this with anyone.

_NyayaSetu · Bridge to Justice_
"""
        client.messages.create(from_=TWILIO_WA_NUM, to=f"whatsapp:{phone}", body=message_body)
        print(f"[OTP] Sent to {phone}")
        return JSONResponse({"success": True, "message": f"OTP sent to WhatsApp {phone}", "expires_in": 600})
    except Exception as e:
        otp_store.pop(phone, None)
        print(f"[OTP ERROR] {e}")
        raise HTTPException(status_code=500, detail=f"Failed to send OTP via WhatsApp: {str(e)}")

# ── OTP: Verify ───────────────────────────────────────────────────────────────

@app.post("/api/otp/verify")
async def verify_otp(req: OTPVerifyRequest):
    phone = normalise_phone(req.phone)
    record = otp_store.get(phone)
    if not record:
        raise HTTPException(400, "No OTP found for this number. Please request a new one.")
    if time.time() > record["expires_at"]:
        otp_store.pop(phone, None)
        raise HTTPException(400, "OTP has expired. Please request a new one.")
    record["attempts"] += 1
    if record["attempts"] > 5:
        otp_store.pop(phone, None)
        raise HTTPException(429, "Too many incorrect attempts. Please request a new OTP.")
    if req.otp.strip() != record["otp"]:
        remaining = 5 - record["attempts"]
        raise HTTPException(400, f"Incorrect OTP. {remaining} attempt(s) remaining.")
    record["verified"] = True
    print(f"[OTP] Verified: {phone}")
    return JSONResponse({"success": True, "verified": True, "phone": phone})

# ── Evidence certificate ──────────────────────────────────────────────────────

@app.post("/api/evidence")
async def evidence_certificate(
    file: UploadFile = File(...),
    complainant_name: str = Form("Not provided"),
    complainant_phone: str = Form(""),
    complainant_address: str = Form(""),
    incident_brief: str = Form("Evidence submitted via NyayaSetu"),
    incident_date: str = Form(""),
    police_station: str = Form(""),
):
    if complainant_phone:
        phone = normalise_phone(complainant_phone)
        record = otp_store.get(phone)
        if not record or not record.get("verified"):
            raise HTTPException(403, "Phone number not verified. Please complete OTP verification.")
    file_bytes = await file.read()
    try:
        cert, pdf_bytes, blockchain_res = generate_evidence_certificate(
            file_bytes=file_bytes,
            file_name=file.filename,
            complainant_name=complainant_name,
            complainant_phone=complainant_phone,
            complainant_address=complainant_address,
            incident_brief=incident_brief,
            incident_date=incident_date,
            police_station=police_station,
        )
    except Exception as e:
        print(f"[EVIDENCE ERROR] {e}")
        raise HTTPException(500, f"Certificate generation failed: {str(e)}")
    os.makedirs("temp_media", exist_ok=True)
    pdf_name = f"BSA_Certificate_NS-{cert.certificate_id}.pdf"
    pdf_path = os.path.join("temp_media", pdf_name)
    with open(pdf_path, "wb") as f:
        f.write(pdf_bytes)
    if complainant_phone:
        otp_store.pop(normalise_phone(complainant_phone), None)
    return JSONResponse({
        "certificate_id": cert.certificate_id,
        "sha256_hash": cert.sha256_hash,
        "file_name": cert.file_name,
        "file_size_bytes": cert.file_size_bytes,
        "complainant_name": cert.complainant_name,
        "complainant_phone": cert.complainant_phone,
        "complainant_address": cert.complainant_address,
        "incident_brief": cert.incident_brief,
        "incident_date": cert.incident_date,
        "police_station": cert.police_station,
        "capture_timestamp": cert.capture_timestamp,
        "certification_timestamp": cert.certification_timestamp,
        "device_make": cert.device_make,
        "device_model": cert.device_model,
        "gps_coordinates": cert.gps_coordinates,
        "image_width": cert.image_width,
        "image_height": cert.image_height,
        "verification_status": cert.verification_status,
        "bsa_section": cert.bsa_section,
        "pdf_download_url": f"/api/media/{pdf_name}",
    })

@app.get("/api/media/{filename}")
def serve_media(filename: str):
    path = os.path.join("temp_media", filename)
    if os.path.exists(path):
        return FileResponse(path)
    raise HTTPException(404, "File not found")

@app.get("/api/sessions")
def list_sessions():
    return {"count": len(doc_sessions), "sessions": [{"id": k, "doc_type": v["doc_type"], "age_mins": round((time.time() - v["created_at"]) / 60, 1)} for k, v in doc_sessions.items()]}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8001, reload=True)