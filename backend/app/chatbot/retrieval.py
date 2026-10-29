"""Database-backed Knowledge Retriever for CampusIQ Chatbot.

Dynamically fetches authoritative institutional records from PostgreSQL to formulate
accurate, factual, and formatted responses.
"""

import re
from typing import Any, Dict, List, Optional, Set, Tuple
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models.college import (
    CollegeInfo,
    Course,
    CourseFee,
    Department,
    Facility,
    Faculty,
    KnowledgeDocument,
)
from app.models.knowledge import KBChunk, KBDocument


class KnowledgeRetriever:
    """Retrieves institutional data from PostgreSQL and formats conversational responses."""

    def __init__(self, db: Session):
        self.db = db

    # -------------------------------------------------------------------------
    # College Information & Contact
    # -------------------------------------------------------------------------
    def get_college_info(self) -> Dict[str, Any]:
        """Fetch general college overview."""
        info = self.db.query(CollegeInfo).first()
        if not info:
            return {
                "text": "JD College of Engineering and Management (JDCOEM), Nagpur is a premier autonomous institute accredited with NAAC 'A' Grade, approved by AICTE, and affiliated to DBATU (DTE Code: 04138).",
                "sources": ["Institutional Handbook"],
            }

        text = (
            f"**{info.name}**\n\n"
            f"- **Established:** {info.established_year}\n"
            f"- **Affiliation:** {info.affiliation}\n"
            f"- **Accreditation:** {info.accreditation}\n"
            f"- **Campus:** {info.campus_size}\n"
            f"- **Motto:** *\"{info.motto}\"*\n"
            f"- **Address:** {info.address}\n\n"
            f"Official Website: [{info.website}]({info.website})"
        )
        return {
            "text": text,
            "sources": ["JDCOEM Institutional Profile & NAAC SSR"],
            "suggestions": ["MCA Course Details", "MCA Fees (FRA Sanctioned)", "Who is the Principal?", "TBI Startup Incubation"],
        }

    def get_contact_info(self) -> Dict[str, Any]:
        """Fetch college contact channels."""
        info = self.db.query(CollegeInfo).first()
        if not info:
            return {
                "text": "Contact JD College of Engineering and Management (JDCOEM) at +91-90110 10038 or email info@jdcoem.ac.in.",
                "sources": ["Contact Directory"],
            }

        text = (
            f"**Contact Details for {info.name}:**\n\n"
            f"- **Address:** {info.address}\n"
            f"- **Phone / Helplines:** {info.contact_phone}\n"
            f"- **Email:** {info.contact_email}\n"
            f"- **Website:** [{info.website}]({info.website})\n"
            f"- **Office Hours:** Monday to Saturday, 9:30 AM – 5:30 PM\n"
            f"- **DTE Choice Code:** 04138 (JDCOEM, Nagpur)"
        )
        return {
            "text": text,
            "sources": ["Official Contact Directory & DTE Portal"],
            "suggestions": ["MCA Admission Guidelines", "College Bus Routes", "Campus Location"],
        }

    # -------------------------------------------------------------------------
    # Courses & Academic Programs
    # -------------------------------------------------------------------------
    def get_courses_list(self) -> Dict[str, Any]:
        """List all available academic programs."""
        courses = self.db.query(Course).join(Department).all()
        if not courses:
            return {"text": "No active course records found in the institutional database.", "sources": []}

        ug_courses = [c for c in courses if c.level == "UG"]
        pg_courses = [c for c in courses if c.level == "PG"]

        text_parts = ["**Academic Programs Offered at CampusIQ:**\n"]
        if ug_courses:
            text_parts.append("\n**Undergraduate (UG) Programs:**")
            for c in ug_courses:
                text_parts.append(
                    f"- **{c.name}** ({c.duration_years} Years) — Intake: {c.intake_capacity or 'N/A'}\n"
                    f"  *Eligibility:* {c.eligibility}"
                )

        if pg_courses:
            text_parts.append("\n**Postgraduate (PG) Programs:**")
            for c in pg_courses:
                text_parts.append(
                    f"- **{c.name}** ({c.duration_years} Years) — Intake: {c.intake_capacity or 'N/A'}\n"
                    f"  *Eligibility:* {c.eligibility}"
                )

        text_parts.append("\nYou can ask: *\"What are the BCA fees?\"* or *\"Tell me about B.Sc. eligibility.\"*")
        return {
            "text": "\n".join(text_parts),
            "sources": ["Academic Prospectus 2024-25"],
            "suggestions": ["BCA course fees", "B.Sc. course fees", "Admission eligibility", "Hostel facilities"],
        }

    COURSE_ALIASES = {
        "MCA": ["MCA", "Master of Computer Applications"],
        "BCA": ["MCA", "BCA", "Master of Computer Applications"],
        "BTECH": ["BTECH_CSE", "BTECH_AI", "BTECH_DS", "BTECH_IT", "B.Tech", "Computer Science"],
        "CSE": ["BTECH_CSE", "Computer Science & Engineering"],
        "AI": ["BTECH_AI", "Artificial Intelligence"],
        "DS": ["BTECH_DS", "Data Science"],
        "IT": ["BTECH_IT", "Information Technology"],
        "MBA": ["MBA", "Master of Business Administration"],
        "MTECH": ["MTECH_CSE", "M.Tech"],
        "BSC": ["BTECH_CSE", "BSC", "B.Sc"],
        "MSC": ["MCA", "MSC", "M.Sc"],
    }

    def _find_course(self, term: str) -> Optional[Course]:
        """Find course by code, name, or known academic acronyms."""
        term_upper = term.upper().strip()
        aliases = self.COURSE_ALIASES.get(term_upper, [term_upper])
        conditions = []
        for alias in aliases:
            conditions.append(Course.code.ilike(f"%{alias}%"))
            conditions.append(Course.name.ilike(f"%{alias}%"))
        return self.db.query(Course).filter(or_(*conditions)).first()

    def get_course_detail(self, target_entity: str) -> Dict[str, Any]:
        """Retrieve in-depth information about a specific course."""
        course = self._find_course(target_entity)

        if not course:
            return self.get_courses_list()

        dept_name = course.department.name if course.department else "Academic Division"
        text = (
            f"**{course.name} ({course.level})**\n\n"
            f"- **Department:** {dept_name}\n"
            f"- **Duration:** {course.duration_years} Years (Full Time)\n"
            f"- **Intake Capacity:** {course.intake_capacity or 'N/A'} Seats\n"
            f"- **Eligibility:** {course.eligibility}\n"
            f"- **Overview:** {course.description or 'Comprehensive university syllabus curriculum aligned with SGBAU norms.'}\n"
        )

        # Check if fee is attached
        fees = self.db.query(CourseFee).filter(CourseFee.course_id == course.id).order_by(CourseFee.year_of_study).all()
        if fees:
            text += "\n**Fee Structure (Annual Breakdown):**\n"
            for f in fees:
                text += f"- Year {f.year_of_study}: ₹{float(f.total_fee):,.2f} (Tuition: ₹{float(f.tuition_fee):,.2f}, Lab: ₹{float(f.lab_fee):,.2f})\n"

        return {
            "text": text,
            "sources": ["Course Catalog & SGBAU Affiliation Records"],
            "suggestions": [f"{target_entity} fees", "Admission procedure", "Faculty members"],
        }

    # -------------------------------------------------------------------------
    # Course Fees
    # -------------------------------------------------------------------------
    def get_course_fees(self, target_entity: Optional[str] = None) -> Dict[str, Any]:
        """Fetch verified fee breakdown for a specific program or provide general summary."""
        if not target_entity:
            # General fee summary across courses
            fees = (
                self.db.query(CourseFee, Course)
                .join(Course, CourseFee.course_id == Course.id)
                .filter(CourseFee.year_of_study == 1)
                .all()
            )
            if not fees:
                return {
                    "text": "Detailed fee schedule is currently being synchronized with the academic registry.",
                    "sources": ["Finance Department"],
                }

            text_parts = ["**Annual Fee Structure Summary (1st Year):**\n"]
            for fee, course in fees:
                text_parts.append(f"- **{course.name}:** ₹{float(fee.total_fee):,.2f} per year")

            text_parts.append("\n*Note:* Installment payment plans and government scholarship concessions (EBC/SC/ST/OBC) apply.")
            text_parts.append("Ask about a specific course (e.g., *\"BCA fees\"* or *\"B.Sc. fees\"*) for full multi-year breakdown.")
            return {
                "text": "\n".join(text_parts),
                "sources": ["College Prospectus Fee Schedule 2024-25"],
                "suggestions": ["BCA fees", "B.Sc. fees", "M.Sc. fees", "Scholarships available"],
            }

        # Specific course fee lookup
        course = self._find_course(target_entity)

        if not course:
            return self.get_course_fees(None)

        fees = (
            self.db.query(CourseFee)
            .filter(CourseFee.course_id == course.id)
            .order_by(CourseFee.year_of_study)
            .all()
        )

        if not fees:
            return {
                "text": f"Fee structure for **{course.name}** is determined by government university guidelines. Please contact the administrative office.",
                "sources": ["Fee Regulatory Authority"],
            }

        text_parts = [f"**Fee Structure for {course.name} ({fees[0].academic_year}):**\n"]
        total_degree_cost = 0.0

        for f in fees:
            total_fee = float(f.total_fee)
            total_degree_cost += total_fee
            text_parts.append(
                f"- **Year {f.year_of_study}:** ₹{total_fee:,.2f}\n"
                f"  *Breakdown:* Tuition ₹{float(f.tuition_fee):,.2f} | Lab ₹{float(f.lab_fee):,.2f} | Dev ₹{float(f.development_fee):,.2f}"
            )
            if f.notes:
                text_parts.append(f"  *Notes:* {f.notes}")

        text_parts.append(f"\n**Estimated Total Course Cost:** ₹{total_degree_cost:,.2f}")
        text_parts.append("\n*Concessions available for reserved category students as per Maharashtra State regulations.*")

        return {
            "text": "\n".join(text_parts),
            "sources": [f"Official Fee Ledger — {course.name}"],
            "suggestions": [f"{target_entity} eligibility", "Admission procedure", "Hostel fees"],
        }

    # -------------------------------------------------------------------------
    # Faculty Inquiries
    # -------------------------------------------------------------------------
    def get_faculty_info(self, target_entity: Optional[str] = None) -> Dict[str, Any]:
        """Fetch teaching faculty information."""
        entity_lower = (target_entity or "").lower()
        if "principal" in entity_lower or "director" in entity_lower or "sonekar" in entity_lower or "dhote" in entity_lower:
            principal = self.db.query(Faculty).filter(Faculty.designation.ilike("%Principal%")).first()
            if principal:
                text = (
                    f"**Principal & Director Information:**\n\n"
                    f"- **Name:** {principal.name}\n"
                    f"- **Designation:** {principal.designation}\n"
                    f"- **Qualification:** {principal.qualification}\n"
                    f"- **Experience:** {principal.experience_years}+ years of academic & engineering leadership\n"
                    f"- **Specialization:** {principal.specialization or 'Electronics & Administration'}\n"
                    f"- **Email:** {principal.email or 'principal@jdcoem.ac.in'}\n"
                    f"- **Office Phone:** {principal.phone or '+91-90110 10038'}"
                )
                return {
                    "text": text,
                    "sources": ["JDCOEM Administration Directory"],
                    "suggestions": ["MCA Department HOD", "College Contact Details", "TBI Incubation"],
                }

        if "mca" in entity_lower or "bca" in entity_lower or "kokate" in entity_lower or "padole" in entity_lower:
            dept = self.db.query(Department).filter(or_(Department.code == "MCA", Department.name.ilike("%Computer Applications%"))).first()
            if dept:
                faculties = self.db.query(Faculty).filter(Faculty.department_id == dept.id).all()
                text_parts = [
                    f"**Faculty Members — {dept.name} Department:**\n",
                    f"**Head of Department (HOD):** {dept.hod_name}\n",
                ]
                for fac in faculties:
                    text_parts.append(
                        f"- **{fac.name}** ({fac.designation})\n"
                        f"  *Qualification:* {fac.qualification} | *Experience:* {fac.experience_years} years\n"
                        f"  *Specialization:* {fac.specialization or 'Advanced Computing'}\n"
                        f"  *Email:* {fac.email or 'mca@jdcoem.ac.in'}"
                    )
                return {
                    "text": "\n".join(text_parts),
                    "sources": ["Department of Master of Computer Applications (MCA) — JDCOEM"],
                    "suggestions": ["MCA Course Fees", "MCA Project & TBI Incubation", "MAH-MCA-CET Eligibility"],
                }

        # General faculty list
        faculties = self.db.query(Faculty).join(Department).all()
        if not faculties:
            return {"text": "Faculty roster is currently being updated.", "sources": ["HR Directory"]}

        text_parts = ["**Key Teaching Faculty & Department Heads:**\n"]
        for f in faculties[:6]:
            dept_name = f.department.name if f.department else "General"
            text_parts.append(
                f"- **{f.name}** — {f.designation} ({dept_name})\n"
                f"  *Specialization:* {f.specialization or 'Academic Research'}"
            )

        text_parts.append("\nYou can ask specifically about: *\"Principal details\"* or *\"BCA faculty\"*.")
        return {
            "text": "\n".join(text_parts),
            "sources": ["College Faculty Directory 2024"],
            "suggestions": ["Who is the principal?", "BCA faculty", "List of departments"],
        }

    # -------------------------------------------------------------------------
    # Campus Facilities & Infrastructure
    # -------------------------------------------------------------------------
    def get_facility_info(self, target_entity: Optional[str] = None) -> Dict[str, Any]:
        """Fetch campus facility details."""
        if target_entity:
            facility = self.db.query(Facility).filter(Facility.name.ilike(f"%{target_entity}%")).first()
            if facility:
                text = (
                    f"**{facility.name} ({facility.category}):**\n\n"
                    f"{facility.description}\n\n"
                    f"**Key Details:**\n{facility.details or 'Accessible to all enrolled students with valid ID cards.'}"
                )
                return {
                    "text": text,
                    "sources": [f"Campus Facility Records — {facility.name}"],
                    "suggestions": ["Hostel facilities", "Library timings", "Sports complex"],
                }

        # List all facilities
        all_fac = self.db.query(Facility).all()
        if not all_fac:
            return {"text": "Campus facility details are currently offline.", "sources": []}

        text_parts = ["**Campus Facilities & Infrastructure:**\n"]
        for fac in all_fac:
            text_parts.append(f"- **{fac.name}** ({fac.category}): {fac.description}")

        text_parts.append("\nAsk for details on any facility, e.g., *\"Library timings\"* or *\"Hostel fees\"*.")
        return {
            "text": "\n".join(text_parts),
            "sources": ["Institutional Infrastructure Inventory"],
            "suggestions": ["Library details", "Girls' hostel", "Computer labs", "Sports complex"],
        }

    # -------------------------------------------------------------------------
    # Departments
    # -------------------------------------------------------------------------
    def get_departments_list(self) -> Dict[str, Any]:
        """Fetch list of all academic departments."""
        depts = self.db.query(Department).all()
        if not depts:
            return {"text": "Academic departments list not found.", "sources": []}

        text_parts = ["**Academic Departments at Brijlal Biyani Science College:**\n"]
        for d in depts:
            text_parts.append(f"- **{d.name} ({d.code}):** Head of Department: {d.hod_name}")

        return {
            "text": "\n".join(text_parts),
            "sources": ["Academic Department Directory"],
            "suggestions": ["Courses offered", "Faculty directory", "BCA coordinator"],
        }

    # -------------------------------------------------------------------------
    # Knowledge Documents (Policies, Attendance, Discipline, NCC/NSS)
    # -------------------------------------------------------------------------
    def get_knowledge_document(self, category_or_title: str) -> Dict[str, Any]:
        """Fetch institutional policy documents."""
        key = category_or_title.lower().replace("policy_", "").replace("general_", "").strip()
        doc = (
            self.db.query(KnowledgeDocument)
            .filter(
                or_(
                    KnowledgeDocument.category.ilike(f"%{key}%"),
                    KnowledgeDocument.title.ilike(f"%{key}%"),
                )
            )
            .first()
        )

        if not doc:
            return {
                "text": "The requested institutional regulation document is not available in the public catalog. Please refer to the College Student Handbook.",
                "sources": ["Student Handbook"],
            }

        text = (
            f"**{doc.title}:**\n\n"
            f"{doc.content}\n\n"
            f"*Source:* {doc.source_reference or 'College Administration Circular'}"
        )
        return {
            "text": text,
            "sources": [doc.source_reference or "College Handbook"],
            "suggestions": ["Attendance rules", "Anti-ragging policy", "NCC and NSS", "Admission guidelines"],
        }

    # -------------------------------------------------------------------------
    # Knowledge_Base Chunk-Level Multi-Strategy Retrieval
    # -------------------------------------------------------------------------
    STOPWORDS = {
        "what", "is", "are", "the", "in", "of", "and", "for", "a", "an", "to", "how", "why",
        "tell", "me", "about", "can", "you", "explain", "give", "details", "on", "with",
        "please", "does", "do", "i", "my", "we", "our", "it", "its", "at", "by", "from",
        "this", "that", "these", "those", "have", "has", "had", "will", "would", "which"
    }

    SUBJECT_DOC_MAP = {
        "dbms": ["dbms", "database"],
        "dsa": ["dsa", "data_structure", "algorithm"],
        "os": ["operating_system", "os"],
        "cloud": ["cloud", "cloud computing"],
        "discrete_math": ["discrete", "graph_theory", "mathematics"],
        "php": ["php", "web technology"],
        "ai": ["ai", "artificial intelligence"],
    }

    def search_knowledge_chunks(
        self,
        query: str,
        subject: Optional[str] = None,
        semester: Optional[int] = None,
        limit: int = 5,
        min_score: float = 0.2,
    ) -> List[Dict[str, Any]]:
        """Multi-strategy retrieval over ingested knowledge base chunks.
        
        Applies exact phrase matching, heading matching, keyword frequency scoring,
        and subject/semester domain boosting.
        """
        # 1. Normalize and extract query tokens
        clean = re.sub(r"[^\w\s]", " ", query.lower()).strip()
        tokens = [t for t in clean.split() if len(t) > 2 and t not in self.STOPWORDS]
        if not tokens and not subject and not semester:
            return []

        # 2. Base query: only indexed documents
        base_query = (
            self.db.query(KBChunk, KBDocument)
            .join(KBDocument, KBChunk.document_id == KBDocument.id)
            .filter(KBDocument.ingestion_status == "indexed")
        )

        # 3. Subject-specific document filtering if specified
        if subject and subject in self.SUBJECT_DOC_MAP:
            patterns = self.SUBJECT_DOC_MAP[subject]
            subj_conditions = [KBDocument.filename.ilike(f"%{p}%") for p in patterns]
            base_query = base_query.filter(or_(*subj_conditions))

        # 4. Semester-specific document filtering
        if semester == 1:
            base_query = base_query.filter(KBDocument.filename.ilike("%sem 1%"))
        elif semester == 2:
            base_query = base_query.filter(KBDocument.filename.ilike("%sem 2%"))

        # Fetch candidate chunks
        all_candidates = base_query.all()
        if not all_candidates:
            # Fall back to searching all indexed chunks if strict filter returned 0
            all_candidates = (
                self.db.query(KBChunk, KBDocument)
                .join(KBDocument, KBChunk.document_id == KBDocument.id)
                .filter(KBDocument.ingestion_status == "indexed")
                .all()
            )

        scored_results: List[Dict[str, Any]] = []
        clean_phrase = " ".join(tokens)

        for chunk, doc in all_candidates:
            c_text = (chunk.content or "").lower()
            h_text = (chunk.section_heading or "").lower()
            fn_text = doc.filename.lower()

            score = 0.0
            matched_terms = set()

            # Exact phrase match boost
            if clean_phrase and len(tokens) >= 2 and clean_phrase in c_text:
                score += 4.0

            # Heading exact or partial match
            for t in tokens:
                if t in h_text:
                    score += 2.5
                    matched_terms.add(t)

            # Content keyword matches
            for t in tokens:
                count = c_text.count(t)
                if count > 0:
                    matched_terms.add(t)
                    # logarithmic diminishing return on repeated words
                    score += min(count * 0.4, 2.0)

            # Subject alignment boost
            if subject and any(p in fn_text for p in self.SUBJECT_DOC_MAP.get(subject, [])):
                score += 2.0

            # Semester alignment boost
            if semester:
                sem_str = f"sem {semester}"
                if sem_str in fn_text or sem_str in c_text:
                    score += 2.0

            # Coverage ratio: what fraction of the search tokens appeared in this chunk?
            if tokens:
                coverage = len(matched_terms) / len(tokens)
                score += coverage * 3.0

            if score >= min_score and (matched_terms or score >= 1.5):
                scored_results.append({
                    "chunk_id": chunk.id,
                    "doc_id": doc.id,
                    "filename": doc.filename,
                    "page_number": chunk.page_number,
                    "section_heading": chunk.section_heading,
                    "content": chunk.content,
                    "score": round(score, 2),
                    "citation": f"{doc.filename}, Page {chunk.page_number}",
                })

        # Sort descending by score
        scored_results.sort(key=lambda x: x["score"], reverse=True)
        return scored_results[:limit]

    def get_kb_syllabus(
        self, semester: Optional[int] = None, subject: Optional[str] = None, query: str = ""
    ) -> Dict[str, Any]:
        """Retrieve syllabus & curriculum structure from MCA syllabus documents."""
        sem_target = semester or 1
        chunks = self.search_knowledge_chunks(
            query=query or f"syllabus scheme subjects semester {sem_target}",
            semester=sem_target,
            limit=4,
        )

        if not chunks:
            # Fallback search without strict semester
            chunks = self.search_knowledge_chunks(
                query="mca syllabus scheme subjects credits",
                limit=3,
            )

        sources = []
        passages = []
        for c in chunks:
            if c["citation"] not in sources:
                sources.append(c["citation"])
            heading = f"### {c['section_heading']}\n" if c.get("section_heading") else ""
            passages.append(f"{heading}{c['content']}")

        combined_text = "\n\n".join(passages)
        return {
            "text": combined_text,
            "sources": sources or [f"MCA SEM {sem_target} Syllabus Final.pdf"],
            "chunks": chunks,
            "semester": sem_target,
        }

    def get_kb_question_bank(
        self, subject: Optional[str] = None, limit: int = 5
    ) -> Dict[str, Any]:
        """Retrieve authentic exam questions from ingested question banks."""
        subj_filter = subject or "dbms"
        chunks = self.search_knowledge_chunks(
            query=f"question bank questions {subj_filter}",
            subject=subj_filter,
            limit=limit,
        )

        sources = []
        passages = []
        for c in chunks:
            if c["citation"] not in sources:
                sources.append(c["citation"])
            heading = f"**{c['section_heading']}**\n" if c.get("section_heading") else ""
            passages.append(f"{heading}{c['content']}")

        return {
            "text": "\n\n---\n\n".join(passages),
            "sources": sources or ["Question Bank Catalog"],
            "chunks": chunks,
            "subject": subj_filter,
        }

    def get_kb_concept(
        self, query: str, subject: Optional[str] = None
    ) -> Dict[str, Any]:
        """Retrieve detailed concept explanation from subject notes."""
        chunks = self.search_knowledge_chunks(
            query=query,
            subject=subject,
            limit=4,
        )

        sources = []
        passages = []
        for c in chunks:
            if c["citation"] not in sources:
                sources.append(c["citation"])
            heading = f"### {c['section_heading']}\n" if c.get("section_heading") else ""
            passages.append(f"{heading}{c['content']}")

        return {
            "text": "\n\n".join(passages),
            "sources": sources,
            "chunks": chunks,
            "subject": subject,
        }

    def check_scanned_document_inquiry(self, query: str) -> Optional[Dict[str, Any]]:
        """Transparently alert if user is asking about an unextracted scanned file."""
        norm = query.lower()
        scanned_docs = (
            self.db.query(KBDocument)
            .filter(KBDocument.ingestion_status == "scanned_ocr_required")
            .all()
        )

        for doc in scanned_docs:
            name_base = re.sub(r"[^\w]", " ", doc.filename.lower())
            tokens = [t for t in name_base.split() if len(t) > 3]
            # If query strongly matches a scanned file (e.g. academic calendar or php unit 2)
            if any(t in norm for t in ["calendar", "academic calendar"]) and "calendar" in doc.filename.lower():
                return {
                    "text": (
                        f"📄 **Notice on Document Availability:**\n\n"
                        f"The file **`{doc.filename}`** in the institutional repository contains scanned image pages. "
                        f"Text extraction is currently pending an OCR (Optical Character Recognition) pipeline pass. "
                        f"Please refer to the physical notice board or contact the Academic Dean's office for the official calendar dates."
                    ),
                    "sources": [f"{doc.filename} (Scanned Image Document)"],
                    "suggestions": ["MCA Syllabus", "Attendance Rules", "HOD MCA", "MCA Fees"],
                }
            elif "php unit 2" in norm and "php unit 2" in doc.filename.lower():
                return {
                    "text": (
                        f"📄 **Notice on Document Availability:**\n\n"
                        f"The document **`{doc.filename}`** (44 pages) consists of scanned image pages and requires OCR processing before text can be queried directly. "
                        f"However, PHP exam questions are available in **`Question Bank PHP 2026.pdf`**."
                    ),
                    "sources": [f"{doc.filename} (Scanned Image Document)"],
                    "suggestions": ["PHP Question Bank", "DBMS Notes", "DSA Notes", "MCA Syllabus"],
                }
        return None

