"""Contextual & Grounded Intent-Specific Answer Builder for CampusIQ.

Replaces raw chunk dumps with concise, relevant, structured, and question-specific answers
grounded in the Academic Knowledge Graph and verified institutional records.
"""

from typing import Any, Dict, List, Optional
from app.chatbot.knowledge_graph import knowledge_graph, KGNode


class AnswerBuilder:
    """Builds concise, structured, and source-grounded answers for each user inquiry intent."""

    @classmethod
    def build_syllabus_overview(
        cls, semester: int = 2, program: str = "MCA"
    ) -> Dict[str, Any]:
        """Generate structured syllabus overview for MCA Semester 1 or 2."""
        sem_data = knowledge_graph.get_semester_overview(program, semester)
        if not sem_data:
            return {
                "text": f"Syllabus records for {program} Semester {semester} are not available in current college records.",
                "sources": ["College Handbook"],
                "suggestions": ["MCA Sem 1 Syllabus", "MCA Sem 2 Syllabus"],
                "format": "text",
                "items": [],
                "links": [],
            }

        theory_list = []
        items = []
        for i, s in enumerate(sem_data["theory_subjects"], start=1):
            display_name = s.name
            if "Elective" in s.name:
                display_name = "Department Elective-I"
            theory_list.append(
                f"{i}. **{display_name} ({s.code})** — {s.properties.get('credits')} Credits ({s.properties.get('ltp', '3-0-0')}) | {s.properties.get('description', '')}"
            )
            items.append({
                "title": s.name,
                "code": s.code,
                "credits": s.properties.get("credits"),
                "category": "Theory",
                "description": s.properties.get("description"),
            })

        lab_list = []
        start_idx = len(sem_data["theory_subjects"]) + 1
        for i, s in enumerate(sem_data["lab_courses"], start=start_idx):
            display_name = s.properties.get("short_name") or s.name
            lab_list.append(
                f"{i}. **{display_name} ({s.code})** — {s.properties.get('credits')} Credits ({s.properties.get('ltp', '0-0-4')}) | {s.properties.get('description', '')}"
            )
            items.append({
                "title": s.name,
                "code": s.code,
                "credits": s.properties.get("credits"),
                "category": "Laboratory",
                "description": s.properties.get("description"),
            })

        view_url = sem_data["view_url"]
        doc_filename = sem_data["document_filename"]
        doc_id = sem_data["document_id"]

        text = (
            f"## 🎓 MCA Semester {semester} Academic Scheme & Syllabus\n"
            f"**Autonomous Curriculum (DBATU Affiliated | DTE Code: 04138)**\n\n"
            f"The MCA Semester {semester} curriculum includes the following core theory and practical courses:\n\n"
            f"### 📖 Core Theory Courses:\n" + "\n".join(theory_list) + "\n\n"
            f"### 💻 Practical Laboratory Courses:\n" + "\n".join(lab_list) + "\n\n"
            f"---\n"
            f"- **Total Semester Credits:** **{sem_data['total_credits']} Credits** (Total Scheme Marks: {sem_data['total_marks']})\n"
            f"- **Evaluation Pattern:** Continuous Assessment (CA: 40 Marks), End-Semester Examination (ESE: 60 Marks)\n\n"
            f"[📄 View Full Official Semester {semester} Syllabus PDF]({view_url})"
        )

        return {
            "text": text,
            "sources": [f"{doc_filename} (Official Autonomous Curriculum)"],
            "suggestions": [
                f"MCA Sem {1 if semester == 2 else 2} Syllabus",
                "Tell me about DBMS" if semester == 2 else "Tell me about DSA",
                "How many credits does AI have?" if semester == 2 else "How many credits does Java have?",
                "Show MCA timetable",
            ],
            "format": "structured_list",
            "items": items,
            "links": [
                {"label": f"Open MCA Semester {semester} Syllabus PDF", "url": view_url, "doc_id": doc_id, "file_type": "pdf"}
            ],
        }

    @classmethod
    def build_subject_details(cls, subject_key: str) -> Dict[str, Any]:
        """Generate focused, grounded summary for a specific academic subject."""
        node = knowledge_graph.find_node(subject_key)
        if not node or node.type not in ("Subject", "LabCourse"):
            return {
                "text": f"I couldn't locate verified syllabus details for subject '{subject_key}' in the official course records.",
                "sources": ["College Handbook"],
                "suggestions": ["MCA Sem 1 Syllabus", "MCA Sem 2 Syllabus"],
                "format": "text",
                "items": [],
                "links": [],
            }

        p = node.properties
        units = p.get("units", [])
        unit_bullets = "\n".join([f"- **{u.split(':')[0] if ':' in u else u}**: {u.split(':', 1)[1].strip() if ':' in u else ''}" for u in units]) if units else "- Full units detailed in official syllabus."

        lab_mention = ""
        lab_edges = knowledge_graph.get_outgoing(node.id, "HAS_LAB")
        if lab_edges:
            lab_node = lab_edges[0][1]
            lab_mention = f"- **Associated Practical:** `{lab_node.code}` ({lab_node.name} — {lab_node.properties.get('credits')} Credits)\n"

        view_url = p.get("view_url", "/api/v1/documents/6/view")
        doc_filename = p.get("document_filename", "MCA Syllabus Final.pdf")

        text = (
            f"## 📘 {node.name} ({node.code})\n\n"
            f"{p.get('description', '')}\n\n"
            f"### 📋 Course Details:\n"
            f"- **Course Code:** `{node.code}`\n"
            f"- **Semester:** MCA Semester {p.get('semester')}\n"
            f"- **Credits:** **{p.get('credits')} Credits** ({p.get('ltp', '3-0-0')})\n"
            f"- **Marks Distribution:** CA: {p.get('ca_marks')} Marks, ESE: {p.get('ese_marks')} Marks (Total: {p.get('total_marks')} Marks)\n"
            f"{lab_mention}"
            f"- **Passing Requirement:** Minimum 40% aggregate in CA + ESE\n\n"
            f"### 📑 Main Syllabus Units:\n"
            f"{unit_bullets}\n\n"
            f"[📄 View Official Subject Syllabus]({view_url})"
        )

        return {
            "text": text,
            "sources": [f"{doc_filename}, Page {p.get('page_number', 1)}"],
            "suggestions": [
                f"How many credits does {node.name} have?",
                f"When is my {node.name} exam?",
                f"MCA Sem {p.get('semester')} Syllabus",
            ],
            "format": "subject_card",
            "items": [{"title": node.name, "code": node.code, "credits": p.get("credits")}],
            "links": [{"label": f"View {node.name} Syllabus PDF", "url": view_url, "doc_id": p.get("document_id")}],
        }

    @classmethod
    def build_credits_and_marks(cls, subject_key: Optional[str], semester: Optional[int] = None) -> Dict[str, Any]:
        """Generate concise, factual response for credits or marks inquiries."""
        if subject_key:
            node = knowledge_graph.find_node(subject_key)
            if node:
                p = node.properties
                text = (
                    f"**{node.name} ({node.code})** carries **{p.get('credits')} credits** "
                    f"({p.get('ltp', 'Theory')} hours/week) with **{p.get('total_marks')} total marks** "
                    f"(Continuous Assessment CA: {p.get('ca_marks')} Marks, End-Semester Exam ESE: {p.get('ese_marks')} Marks) "
                    f"in the MCA Semester {p.get('semester')} autonomous curriculum."
                )
                return {
                    "text": text,
                    "sources": [f"{p.get('document_filename', 'Official Syllabus')}, Page {p.get('page_number', 1)}"],
                    "suggestions": [f"Explain {node.name} subject", f"MCA Sem {p.get('semester')} Syllabus"],
                    "format": "text",
                    "items": [{"title": node.name, "credits": p.get("credits"), "marks": p.get("total_marks")}],
                    "links": [],
                }

        sem_num = semester or 2
        sem_data = knowledge_graph.get_semester_overview("MCA", sem_num)
        if sem_data:
            text = (
                f"**MCA Semester {sem_num} Total Credits:** **{sem_data['total_credits']} Credits** "
                f"(Total Scheme Marks: **{sem_data['total_marks']} Marks** across 5 theory subjects and 3 practical laboratory courses)."
            )
            return {
                "text": text,
                "sources": [f"{sem_data['document_filename']} (JDCOEM Autonomous Scheme)"],
                "suggestions": [f"MCA Sem {sem_num} Syllabus", "Show MCA timetable"],
                "format": "text",
                "items": [{"semester": sem_num, "total_credits": sem_data["total_credits"]}],
                "links": [{"label": f"Open Sem {sem_num} Syllabus PDF", "url": sem_data["view_url"]}],
            }

        return {
            "text": "In the JDCOEM Autonomous MCA Curriculum, each semester comprises 22 credits (Total: 88 credits across 4 semesters).",
            "sources": ["Autonomous Academic Regulations"],
            "suggestions": ["MCA Sem 1 Syllabus", "MCA Sem 2 Syllabus"],
            "format": "text",
            "items": [],
            "links": [],
        }

    @classmethod
    def build_timetable(cls, semester: int = 2) -> Dict[str, Any]:
        """Generate structured timetable schedule and document link."""
        node = knowledge_graph.get_timetable(semester)
        p = node.properties if node else {}
        slots = p.get("slots", [])

        table_rows = []
        for s in slots:
            table_rows.append(f"| **{s['time']}** | {s['type']} | {s['subject']} |")

        table_md = "\n".join(table_rows)
        view_url = p.get("view_url", "/api/v1/documents/7/view")

        text = (
            f"## 📅 MCA Semester {semester} Academic Timetable\n\n"
            f"The standard autonomous lecture and practical schedule for MCA Semester {semester} is:\n\n"
            f"| Time Slot | Session Type | Activity / Subject |\n"
            f"| :--- | :--- | :--- |\n"
            f"{table_md}\n\n"
            f"---\n"
            f"💡 *College timings: Monday through Friday, 09:30 AM to 04:30 PM.*\n\n"
            f"[📅 Open Official MCA Academic Calendar & Timetable]({view_url})"
        )

        return {
            "text": text,
            "sources": ["MCA Department Academic Calendar & Lecture Timetable"],
            "suggestions": ["When is my DBMS exam?", "MCA Sem 2 Syllabus", "75% Attendance Rule"],
            "format": "table",
            "items": slots,
            "links": [{"label": "Open MCA Academic Calendar & Timetable", "url": view_url, "doc_id": 7, "file_type": "pdf"}],
        }

    @classmethod
    def build_exam_schedule(cls, subject_key: Optional[str] = None, semester: int = 2) -> Dict[str, Any]:
        """Generate examination schedule details and evaluation model."""
        subj_name = "MCA Semester Courses"
        specific_line = ""
        if subject_key:
            node = knowledge_graph.find_node(subject_key)
            if node:
                subj_name = f"{node.name} ({node.code})"
                p = node.properties
                specific_line = (
                    f"### 🎯 Evaluation Breakdown for {node.name}:\n"
                    f"- **End-Semester Written Exam (ESE):** {p.get('ese_marks', 60)} Marks (3-Hour Autonomous Exam)\n"
                    f"- **Continuous Assessment (CA):** {p.get('ca_marks', 40)} Marks (Internal Tests, Assignments & Quizzes)\n"
                )
                if p.get("lab_code"):
                    specific_line += f"- **Practical Exam:** `{p.get('lab_code')}` (40 Marks external practical & viva)\n"

        view_url = "/api/v1/documents/7/view"

        text = (
            f"## 📝 Examination Schedule & Scheme: {subj_name}\n\n"
            f"As per the JDCOEM Autonomous Examination Guidelines for MCA Semester {semester}:\n\n"
            f"{specific_line}\n"
            f"### 📋 General Autonomous Examination Scheme:\n"
            f"- **Mid-Semester Examination (MSE):** 20 Marks conducted midway through the semester.\n"
            f"- **End-Semester Examination (ESE):** 60 Marks theory papers conducted by the Controller of Examinations (COE).\n"
            f"- **Continuous Assessment (CA):** 40 Marks internally evaluated.\n"
            f"- **Passing Standard:** Minimum 40% aggregate in CA + MSE + ESE.\n\n"
            f"Official examination dates are notified through circulars on the departmental notice board and the Academic Calendar:\n\n"
            f"[📄 View MCA Academic Calendar & Exam Schedule]({view_url})"
        )

        return {
            "text": text,
            "sources": ["JDCOEM Autonomous Examination Regulations & Academic Calendar"],
            "suggestions": ["MCA Sem 2 Timetable", "MCA Sem 2 Syllabus", "75% Attendance Rule"],
            "format": "document_link",
            "items": [],
            "links": [{"label": "Open Academic Calendar & Exam Schedule", "url": view_url, "doc_id": 7}],
        }

    @classmethod
    def build_course_structure(cls, subject_key: Optional[str] = None) -> Dict[str, Any]:
        """Generate course code or program structural information."""
        if subject_key:
            node = knowledge_graph.find_node(subject_key)
            if node:
                p = node.properties
                text = (
                    f"The official course code for **{node.name}** in MCA Semester {p.get('semester')} is **`{node.code}`** "
                    f"({p.get('category')}, {p.get('credits')} Credits, DBATU Autonomous Curriculum)."
                )
                return {
                    "text": text,
                    "sources": [f"{p.get('document_filename', 'Official Syllabus')}"],
                    "suggestions": [f"Explain {node.name}", f"How many credits does {node.name} have?"],
                    "format": "text",
                    "items": [{"code": node.code, "name": node.name}],
                    "links": [],
                }

        text = (
            f"**Master of Computer Applications (MCA) Program Structure:**\n\n"
            f"- **Duration:** 2 Years (4 Semesters), Full-Time Postgraduate Program\n"
            f"- **Total Program Credits:** 88 Credits (22 Credits per semester)\n"
            f"- **Approved Intake:** 120 Seats\n"
            f"- **Affiliation & Autonomy:** Affiliated to DBATU, Lonere; NAAC 'A' Grade Autonomous Institute (DTE Code: 04138)\n"
            f"- **Course Prefix:** `MC1` for Semester 1, `MC2` for Semester 2 (e.g. `MC2T001` for DBMS)"
        )
        return {
            "text": text,
            "sources": ["JDCOEM Academic Regulations"],
            "suggestions": ["MCA Sem 1 Syllabus", "MCA Sem 2 Syllabus", "What is the MCA fee?"],
            "format": "text",
            "items": [],
            "links": [],
        }

    @classmethod
    def build_fees(cls, program: str = "MCA") -> Dict[str, Any]:
        """Generate verified fee structure breakdown."""
        fee_node = knowledge_graph.get_fee_structure(program)
        p = fee_node.properties if fee_node else {}

        text = (
            f"## 💰 MCA Tuition & College Fee Schedule (JDCOEM)\n\n"
            f"For the **Master of Computer Applications (MCA)** program, the official Fee Regulating Authority (FRA) sanctioned fee structure is:\n\n"
            f"- **Tuition Fee:** ₹{p.get('tuition_fee', 81364):,} / year\n"
            f"- **Development Fee:** ₹{p.get('development_fee', 10136):,} / year\n"
            f"- **Total Annual Fee (Open Category):** **₹{p.get('total_annual_fee', 91500):,} / year**\n"
            f"- **Total 2-Year Program Cost:** ₹{p.get('total_program_fee', 183000):,}\n\n"
            f"### 🎓 Category Fee Concessions (Maharashtra State Scholarships):\n"
            f"- **OBC / EBC / EWS:** 50% concession on tuition fee (~₹50,818 / year)\n"
            f"- **SC / ST / VJ-NT / SBC:** 100% tuition and development fee waiver under Government of Maharashtra scholarship schemes\n\n"
            f"*Source: {p.get('source', 'Fee Regulating Authority (FRA) Maharashtra')}*"
        )

        return {
            "text": text,
            "sources": [
                "Official Fee Ledger & FRA Sanctioned Schedule",
                "JDCOEM Accounts Office",
            ],
            "suggestions": ["Which documents are required for admission?", "MCA Eligibility Criteria", "Contact JDCOEM"],
            "format": "text",
            "items": [
                {"category": "Open", "annual_fee": 91500},
                {"category": "OBC / EBC / EWS", "annual_fee": 50818},
                {"category": "SC / ST / VJ-NT", "annual_fee": 0},
            ],
            "links": [],
        }

    @classmethod
    def build_documents_required(cls) -> Dict[str, Any]:
        """Generate verified checklist of admission documents."""
        text = (
            f"## 📄 Documents Required for MCA Admission (JDCOEM — DTE Code: 04138)\n\n"
            f"Candidates securing admission through the Centralized Admission Process (CAP) must submit the following original documents along with three sets of attested photocopies:\n\n"
            f"1. **MAH-MCA-CET Score Card** & **CAP Allotment Letter**\n"
            f"2. **SSC (Class 10) & HSC (Class 12) Marksheets & Passing Certificates**\n"
            f"3. **Graduation Marksheets** (All Semesters / Years) & Degree / Provisional Certificate\n"
            f"4. **College Leaving Certificate (Transfer Certificate - TC)**\n"
            f"5. **Migration Certificate** (Mandatory for students from universities other than DBATU)\n"
            f"6. **Domicile and Nationality Certificate** (or Birth Certificate specifying Maharashtra birthplace)\n"
            f"7. **Caste Certificate & Caste Validity Certificate** (For reserved categories)\n"
            f"8. **Non-Creamy Layer (NCL) Certificate** (Valid for current financial year; for OBC, VJ/NT, SBC)\n"
            f"9. **Income Certificate** (Issued by Competent Authority for scholarship/EWS beneficiaries)\n"
            f"10. **Aadhaar Card Copy** & 4 Recent Passport-Size Photographs\n\n"
            f"*Source: Directorate of Technical Education (DTE) Maharashtra & JDCOEM Admission Authority.*"
        )

        return {
            "text": text,
            "sources": ["DTE Maharashtra CAP Information Brochure & JDCOEM Admission Cell"],
            "suggestions": ["MCA Eligibility Criteria", "What is the MCA fee?", "MCA Course Details"],
            "format": "structured_list",
            "items": [],
            "links": [],
        }

    @classmethod
    def build_admission_process(cls) -> Dict[str, Any]:
        """Generate official admission guidance."""
        text = (
            f"## 🎓 MCA Admission Procedure (JDCOEM Nagpur — DTE Code: 04138)\n\n"
            f"Admissions to the 2-Year MCA program are strictly merit-based through the Centralized Admission Process (CAP):\n\n"
            f"1. **Entrance Exam:** Candidate must appear for and obtain a non-zero positive score in the **MAH-MCA-CET** examination.\n"
            f"2. **CAP Registration:** Register online on the Maharashtra State CET Cell portal and verify documents at designated Scrutiny Centers (FC).\n"
            f"3. **Option Form Filling:** Enter choice codes in order of preference. The DTE Choice Code for JDCOEM MCA is **`0413824110`**.\n"
            f"4. **Seat Allotment & Reporting:** Accept the allotted seat online and report to JDCOEM Admission Office with original documents and fees.\n"
            f"5. **Institute-Level Seats:** Direct vacant / institute quota inquiries can be made at the college campus in Khandala, Nagpur."
        )

        return {
            "text": text,
            "sources": ["State CET Cell Maharashtra & JDCOEM Central Admission Office"],
            "suggestions": ["Which documents are required for admission?", "What is the MCA fee?", "MCA Eligibility Criteria"],
            "format": "text",
            "items": [],
            "links": [],
        }

    @classmethod
    def build_eligibility(cls) -> Dict[str, Any]:
        """Generate verified eligibility criteria."""
        text = (
            f"## 📋 MCA Admission Eligibility Criteria\n\n"
            f"As prescribed by AICTE New Delhi and Government of Maharashtra State CET Cell:\n\n"
            f"- **Educational Qualification:** Passed Bachelor's Degree in BCA / Computer Science Engineering or equivalent degree, **OR** passed B.Sc. / B.Com. / B.A. with Mathematics at 10+2 level or at graduation level.\n"
            f"- **Minimum Qualifying Marks:** At least **50% marks** in aggregate (at least **45% marks** for candidates belonging to Backward Class categories, EWS, and Persons with Disability belonging to Maharashtra State only).\n"
            f"- **Entrance Examination:** Valid non-zero score in the **MAH-MCA-CET** for the current academic session."
        )

        return {
            "text": text,
            "sources": ["AICTE Process Handbook & Maharashtra State CET Cell Regulations"],
            "suggestions": ["Which documents are required for admission?", "What is the MCA fee?", "How to get admission in MCA?"],
            "format": "text",
            "items": [],
            "links": [],
        }

    @classmethod
    def build_faculty_info(cls, query_name: Optional[str] = None) -> Dict[str, Any]:
        """Generate verified faculty profiles."""
        node = knowledge_graph.find_node(query_name or "rohan kokate", node_type="Faculty")
        if not node:
            node = knowledge_graph.get_node("fac:rohan_kokate")

        p = node.properties if node else {}
        text = (
            f"## 👨‍🏫 {node.name}\n\n"
            f"- **Designation:** {p.get('designation', '')}\n"
            f"- **Department:** Department of Master of Computer Applications (MCA)\n"
            f"- **Qualification:** {p.get('qualification', '')}\n"
            f"- **Specialization Areas:** {p.get('specialization', '')}\n"
            f"- **Email:** [{p.get('email', '')}](mailto:{p.get('email', '')})\n\n"
            f"Prof. Kokate oversees academic operations, DBATU autonomous curriculum delivery, student mentorship, and industry-oriented project portfolios for the MCA department."
        )

        return {
            "text": text,
            "sources": ["JDCOEM Department of MCA Faculty Directory"],
            "suggestions": ["Tell me about MCA department", "TBI Startup Incubation", "Contact JDCOEM"],
            "format": "text",
            "items": [],
            "links": [],
        }

    @classmethod
    def build_department_info(cls) -> Dict[str, Any]:
        """Generate MCA department profile."""
        text = (
            f"## 🏛️ Department of Master of Computer Applications (MCA)\n"
            f"**JD College of Engineering and Management (JDCOEM), Nagpur**\n\n"
            f"- **Leadership:** Headed by **Prof. Rohan Kokate**\n"
            f"- **Approved Intake:** 120 Students / Year\n"
            f"- **Program Offered:** 2-Year Full-Time MCA (Autonomous, affiliated to DBATU, Lonere)\n"
            f"- **DTE Institute Code:** 04138 | **Choice Code:** 0413824110\n"
            f"- **Laboratories:** Dedicated High-Performance Computing Labs equipped with Python, DBMS (Oracle/MySQL), Web Development, and AI workstations.\n"
            f"- **Innovation & Startup:** Closely partnered with the on-campus **Technology Business Incubator (TBI)** for student software ventures."
        )

        return {
            "text": text,
            "sources": ["JDCOEM Institutional Profile & DTE Portal"],
            "suggestions": ["MCA Sem 2 Syllabus", "What is the MCA fee?", "Prof. Rohan Kokate (HOD MCA)"],
            "format": "text",
            "items": [],
            "links": [],
        }

    @classmethod
    def build_contact_info(cls) -> Dict[str, Any]:
        """Generate verified institutional contact information."""
        inst = knowledge_graph.get_node("inst:jdcoem")
        p = inst.properties if inst else {}

        text = (
            f"## 📞 Contact JD College of Engineering and Management (JDCOEM)\n\n"
            f"- **Campus Address:** {p.get('address', 'Khandala, Kalmeshwar Road, Nagpur — 441501')}\n"
            f"- **Helpline Phone:** {p.get('phone', '+91-90110 10038 / +91-7774041329')}\n"
            f"- **Email Inquiries:** [{p.get('email', 'info@jdcoem.ac.in')}](mailto:{p.get('email', 'info@jdcoem.ac.in')})\n"
            f"- **Official Website:** [{p.get('website', 'https://jdcoem.ac.in')}]({p.get('website', 'https://jdcoem.ac.in')})\n"
            f"- **Office Working Hours:** Monday to Saturday, 09:30 AM to 05:30 PM\n"
            f"- **Transport Connectivity:** Over 20 GPS-enabled college buses operate citywide across Sitabuldi, Dharampeth, Manewada, Trimurti Nagar, Sadar, and Wadi."
        )

        return {
            "text": text,
            "sources": ["Official Institutional Contact Directory & DTE Portal"],
            "suggestions": ["MCA Admission Procedure", "College Bus Routes", "What is the MCA fee?"],
            "format": "text",
            "items": [],
            "links": [],
        }

    @classmethod
    def build_academic_calendar(cls) -> Dict[str, Any]:
        """Generate academic calendar summary with clickable link."""
        view_url = "/api/v1/documents/7/view"
        text = (
            f"## 📆 JDCOEM Autonomous Academic Calendar\n\n"
            f"The official Academic Calendar outlines key instructional terms, continuous assessment windows, Mid-Semester Examinations (MSE), End-Semester Examinations (ESE), and semester breaks.\n\n"
            f"- **Semester Duration:** Approximately 15–16 instructional weeks per semester.\n"
            f"- **Instruction Milestone:** Continuous assessment quizzes and lab evaluations conducted every 3–4 weeks.\n"
            f"- **Mid-Term Examination:** Conducted mid-session across all autonomous departments.\n"
            f"- **Examination Notification:** Published by the Controller of Examinations (COE).\n\n"
            f"[📄 View Official MCA Academic Calendar Document]({view_url})"
        )

        return {
            "text": text,
            "sources": ["MCA-Ist sem Academic Calendar .pdf (Official Calendar Document)"],
            "suggestions": ["Show MCA timetable", "When is my DBMS exam?", "75% Attendance Rule"],
            "format": "document_link",
            "items": [],
            "links": [{"label": "Open MCA Academic Calendar Document", "url": view_url, "doc_id": 7, "file_type": "pdf"}],
        }

    @classmethod
    def build_practical_lab(cls, lab_key: str) -> Dict[str, Any]:
        """Generate focused summary for a laboratory or practical course."""
        # 1. Search directly for LabCourse node
        node = knowledge_graph.find_node(lab_key, node_type="LabCourse")
        if not node:
            node = knowledge_graph.find_node(f"{lab_key}_lab", node_type="LabCourse")
        if not node:
            node = knowledge_graph.find_node(f"{lab_key} lab", node_type="LabCourse")
        # 2. If a theory node was matched, traverse HAS_LAB relationship
        if not node:
            theory_node = knowledge_graph.find_node(lab_key)
            if theory_node:
                if theory_node.type == "LabCourse":
                    node = theory_node
                else:
                    lab_edges = knowledge_graph.get_outgoing(theory_node.id, "HAS_LAB")
                    if lab_edges:
                        node = lab_edges[0][1]

        if not node:
            return {
                "text": f"I couldn't locate specific laboratory records for '{lab_key}'.",
                "sources": ["Official Syllabus"],
                "suggestions": ["Explain Python Lab", "DBMS Lab", "MCA Sem 2 Syllabus"],
                "format": "text",
                "items": [],
                "links": [],
            }

        p = node.properties
        units = p.get("units", [])
        practicals_md = "\n".join([f"- **{u.split(':')[0] if ':' in u else u}**: {u.split(':', 1)[1].strip() if ':' in u else ''}" for u in units])

        view_url = p.get("view_url", "/api/v1/documents/6/view")

        text = (
            f"## 💻 {node.name} ({node.code})\n\n"
            f"{p.get('description', '')}\n\n"
            f"### 📋 Practical Specifications:\n"
            f"- **Course Code:** `{node.code}`\n"
            f"- **Credits:** **{p.get('credits')} Credits** ({p.get('ltp', '0-0-4')} — 4 Practical hours/week)\n"
            f"- **Evaluation Scheme:** Continuous Assessment (CA: {p.get('ca_marks', 60)} Marks), End-Semester Practical & Viva Exam (ESE: {p.get('ese_marks', 40)} Marks)\n\n"
            f"### 🧪 Laboratory Experiment Domains:\n"
            f"{practicals_md}\n\n"
            f"[📄 View Full Lab Syllabus]({view_url})"
        )

        return {
            "text": text,
            "sources": [f"{p.get('document_filename', 'Official Syllabus Final.pdf')}, Page {p.get('page_number', 1)}"],
            "suggestions": [f"MCA Sem {p.get('semester')} Syllabus", "How many credits does it have?", "Show MCA timetable"],
            "format": "document_link",
            "items": [{"code": node.code, "name": node.name, "credits": p.get("credits")}],
            "links": [{"label": f"Open {node.name} Syllabus PDF", "url": view_url, "doc_id": p.get("document_id")}],
        }

    @classmethod
    def build_unknown_response(cls) -> Dict[str, Any]:
        """Return zero-hallucination deterministic fallback for unknown/out-of-domain inquiries."""
        text = (
            "I couldn't find a verified answer in the available JDCOEM college records "
            "(couldn't locate specific information in official records). "
            "Please try another question or contact the college office."
        )
        return {
            "text": text,
            "sources": ["JDCOEM Information Helpdesk & Academic System"],
            "suggestions": [
                "MCA Sem 2 Syllabus",
                "What is the MCA fee?",
                "Which documents are required for admission?",
                "Show MCA timetable",
            ],
            "format": "text",
            "items": [],
            "links": [],
        }

    @classmethod
    def build_concept_answer(cls, analysis: Any, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Legacy concept formatting method for backward compatibility."""
        top = chunks[0] if chunks else {}
        heading = top.get("section_heading") or "Concept Overview"
        content = top.get("content", "")
        citation = top.get("citation", "JDCOEM Academic Records")
        sources = [c.get("citation", citation) for c in chunks] if chunks else [citation]
        text = (
            f"## 📘 {heading}\n\n"
            f"{content}\n\n"
            f"**Sources & Institutional Citations:**\n"
            f"- {sources[0]}"
        )
        return {
            "format": "text",
            "text": text,
            "sources": sources,
            "suggestions": ["Explain DBMS", "MCA Sem 2 Syllabus"],
            "items": [],
            "links": [],
        }

    @classmethod
    def build_syllabus_answer(
        cls, analysis: Any, chunks: List[Dict[str, Any]], semester: Optional[int] = None
    ) -> Dict[str, Any]:
        """Legacy syllabus formatting method for backward compatibility."""
        sem = semester or getattr(analysis, "semester_focus", 2) or 2
        res = cls.build_syllabus_overview(semester=sem)
        citations = [c.get("citation") for c in chunks if c.get("citation")] if chunks else []
        if citations:
            res["sources"] = citations + [s for s in res["sources"] if s not in citations]
        if "Continuous Assessment (CA)" not in res["text"]:
            res["text"] += (
                "\n\n### 📋 General Assessment Policy:\n"
                "- **Continuous Assessment (CA):** 40 Marks\n"
                "- **End-Semester Examination (ESE):** 60 Marks\n"
            )
        return res
