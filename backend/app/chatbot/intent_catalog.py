"""Declarative Intent Catalog for Rule-Based Classification — CampusIQ (JDCOEM).

Tailored for JD College of Engineering and Management (JDCOEM), Nagpur, with primary
emphasis on the Master of Computer Applications (MCA) department, its leadership,
curriculum, admissions, incubation (TBI), placements, and campus facilities.
"""

from dataclasses import dataclass, field
import enum
import re
from typing import List, Optional, Pattern


class IntentCategory(str, enum.Enum):
    """Categorical classification of user inquiry intents."""

    GREETING = "greeting"
    FAREWELL = "farewell"
    HELP = "help"
    COLLEGE_INFO = "college_info"
    COURSES = "courses"
    COURSE_FEES = "course_fees"
    ADMISSION = "admission"
    ELIGIBILITY = "eligibility"
    FACULTY = "faculty"
    DEPARTMENT = "department"
    LIBRARY = "library"
    HOSTEL = "hostel"
    SPORTS = "sports"
    FACILITIES = "facilities"
    ATTENDANCE = "attendance"
    EXAMINATION = "examination"
    NCC_NSS = "ncc_nss"
    CONTACT = "contact"
    CLARIFICATION = "clarification"
    UNKNOWN = "unknown"


@dataclass
class IntentDefinition:
    """Specification of an inquiry rule pattern, priority tier, and entity tags."""

    intent_id: str
    category: IntentCategory
    priority: int  # 1 to 100: Specific intents have priority >= 80, generic have 20-50
    patterns: List[Pattern] = field(default_factory=list)
    keywords_all: List[str] = field(default_factory=list)      # All must match
    keywords_any: List[str] = field(default_factory=list)      # At least one must match
    target_entity: Optional[str] = None                        # e.g., 'MCA', 'BTECH_CSE', 'TBI'
    description: str = ""


# Compile intent definitions
INTENT_CATALOG: List[IntentDefinition] = [
    # 1. Greetings (Priority 40)
    IntentDefinition(
        intent_id="greeting",
        category=IntentCategory.GREETING,
        priority=40,
        patterns=[
            re.compile(r"^(hi|hello|hey|hii|helo|greetings|howdy|namaste|ram ram|radhe radhe)(\s|$)", re.IGNORECASE),
            re.compile(r"^(good\s+(morning|afternoon|evening|day))(\s|$)", re.IGNORECASE),
        ],
        description="Greeting the chatbot assistant",
    ),

    # 2. Farewells (Priority 40)
    IntentDefinition(
        intent_id="farewell",
        category=IntentCategory.FAREWELL,
        priority=40,
        patterns=[
            re.compile(r"^(bye|goodbye|see you|farewell|take care|thank you|thanks)(\s|$)", re.IGNORECASE),
        ],
        description="Farewell and gratitude",
    ),

    # 3. Help & Capabilities (Priority 50)
    IntentDefinition(
        intent_id="help_capabilities",
        category=IntentCategory.HELP,
        priority=50,
        patterns=[
            re.compile(r"(what can you do|how can you help|who are you|what is your purpose|help me|menu|features)", re.IGNORECASE),
        ],
        description="Bot identity and capability inquiry",
    ),

    # 4. Specific Course Fees (Priority 90 - Takes precedence over generic fees)
    IntentDefinition(
        intent_id="fees_mca",
        category=IntentCategory.COURSE_FEES,
        priority=90,
        keywords_any=["fee", "fees", "cost", "charge", "tuition", "expenses", "structure"],
        keywords_all=["mca"],
        target_entity="MCA",
        description="MCA course tuition and development fee structure",
    ),
    IntentDefinition(
        intent_id="fees_btech",
        category=IntentCategory.COURSE_FEES,
        priority=90,
        keywords_any=["fee", "fees", "cost", "charge", "tuition", "expenses"],
        keywords_all=["btech"],
        target_entity="BTECH_CSE",
        description="B.Tech course tuition fee structure",
    ),
    IntentDefinition(
        intent_id="fees_mba",
        category=IntentCategory.COURSE_FEES,
        priority=90,
        keywords_any=["fee", "fees", "cost", "charge", "tuition", "expenses"],
        keywords_all=["mba"],
        target_entity="MBA",
        description="MBA course tuition fee structure",
    ),
    # Backward compatibility for existing tests
    IntentDefinition(
        intent_id="fees_bca",
        category=IntentCategory.COURSE_FEES,
        priority=90,
        keywords_any=["fee", "fees", "cost", "charge", "tuition", "expenses"],
        keywords_all=["bca"],
        target_entity="MCA",  # Aliased to MCA in JDCOEM
        description="BCA / MCA course tuition fee structure",
    ),
    IntentDefinition(
        intent_id="fees_bsc",
        category=IntentCategory.COURSE_FEES,
        priority=90,
        keywords_any=["fee", "fees", "cost", "charge", "tuition", "expenses"],
        keywords_all=["bsc"],
        target_entity="BTECH_CSE",
        description="Undergraduate science / engineering fee structure",
    ),
    IntentDefinition(
        intent_id="fees_msc",
        category=IntentCategory.COURSE_FEES,
        priority=90,
        keywords_any=["fee", "fees", "cost", "charge", "tuition", "expenses"],
        keywords_all=["msc"],
        target_entity="MCA",
        description="Postgraduate computing fee structure",
    ),

    # 5. Generic Fees (Priority 50)
    IntentDefinition(
        intent_id="fees_general",
        category=IntentCategory.COURSE_FEES,
        priority=50,
        keywords_any=["fee", "fees", "fee structure", "tuition fee", "college fees", "fee details", "fra fee"],
        description="General overview of college fees",
    ),

    # 6. Specific Course Inquiries (Priority 80)
    IntentDefinition(
        intent_id="course_mca",
        category=IntentCategory.COURSES,
        priority=80,
        patterns=[
            re.compile(r"\b(about mca|mca course|mca syllabus|mca degree|mca intake|mca duration|master of computer applications)\b", re.IGNORECASE),
        ],
        keywords_all=["mca"],
        keywords_any=["course", "syllabus", "degree", "program", "duration", "intake", "curriculum", "scope", "about", "details"],
        target_entity="MCA",
        description="Details about Master of Computer Applications (MCA)",
    ),
    IntentDefinition(
        intent_id="course_btech",
        category=IntentCategory.COURSES,
        priority=80,
        patterns=[
            re.compile(r"\b(about btech|btech course|btech branches|engineering programs|b\.tech)\b", re.IGNORECASE),
        ],
        keywords_all=["btech"],
        keywords_any=["course", "syllabus", "degree", "program", "duration", "intake"],
        target_entity="BTECH_CSE",
        description="Details about B.Tech Engineering Programs",
    ),
    IntentDefinition(
        intent_id="course_mba",
        category=IntentCategory.COURSES,
        priority=80,
        keywords_all=["mba"],
        keywords_any=["course", "syllabus", "degree", "program", "duration", "intake"],
        target_entity="MBA",
        description="Details about Master of Business Administration (MBA)",
    ),
    IntentDefinition(
        intent_id="course_bca",
        category=IntentCategory.COURSES,
        priority=80,
        patterns=[
            re.compile(r"\b(about bca|bca course|bca syllabus|bca degree|bca intake|bca duration)\b", re.IGNORECASE),
        ],
        keywords_all=["bca"],
        keywords_any=["course", "syllabus", "degree", "program", "duration", "intake", "curriculum", "scope", "about"],
        target_entity="MCA",
        description="Undergraduate computing / MCA preparatory track",
    ),

    # 7. Generic Courses Offered (Priority 45)
    IntentDefinition(
        intent_id="courses_general",
        category=IntentCategory.COURSES,
        priority=45,
        patterns=[
            re.compile(r"(what courses|courses offered|programs offered|degrees offered|list of courses|available courses|academic programs)", re.IGNORECASE),
        ],
        description="List of all programs offered by JDCOEM",
    ),

    # 8. Admission and Eligibility (Priority 65)
    IntentDefinition(
        intent_id="admission_process",
        category=IntentCategory.ADMISSION,
        priority=65,
        patterns=[
            re.compile(r"(how to apply|admission process|apply for admission|when do admissions start|cap round|cap admission|dte code|04138|admission procedure)", re.IGNORECASE),
        ],
        description="DTE Centralized Admission Process (CAP) and JDCOEM procedures",
    ),
    IntentDefinition(
        intent_id="admission_eligibility",
        category=IntentCategory.ELIGIBILITY,
        priority=65,
        patterns=[
            re.compile(r"(eligibility|eligible for admission|percentage required|minimum marks|cutoff marks|mah cet|mah mca cet)", re.IGNORECASE),
        ],
        description="Admission eligibility requirements (MAH-CET / PCM / Graduation marks)",
    ),

    # 9. Faculty Inquiries (Priority 85 for MCA, 75 for Principal, 50 for general)
    IntentDefinition(
        intent_id="faculty_principal",
        category=IntentCategory.FACULTY,
        priority=75,
        patterns=[
            re.compile(r"(who is (the )?principal|head of college|college principal|director of college|dr\.? shrikant|sonekar|principal contact)", re.IGNORECASE),
        ],
        target_entity="Dr. Shrikant V. Sonekar",
        description="Information about Principal & Director Dr. Shrikant V. Sonekar",
    ),
    IntentDefinition(
        intent_id="faculty_mca",
        category=IntentCategory.FACULTY,
        priority=85,
        patterns=[
            re.compile(r"(mca faculty|mca teacher|who teaches in mca|teach.*mca|mca.*teach|rohan kokate|kokate|chetan padole|padole|sneha sahare|pranay meshram|hod of mca|head of mca|mca coordinator)", re.IGNORECASE),
        ],
        keywords_all=["mca"],
        keywords_any=["faculty", "teacher", "teachers", "teaches", "prof", "professor", "professors", "hod", "coordinator", "staff"],
        target_entity="MCA Faculty",
        description="MCA department faculty, HOD Prof. Rohan Kokate, and Project Coordinator Prof. Chetan Padole",
    ),
    IntentDefinition(
        intent_id="faculty_bca",
        category=IntentCategory.FACULTY,
        priority=85,
        patterns=[
            re.compile(r"(bca faculty|bca teacher|who teaches in bca|teach.*bca|bca.*teach|supatkar|tiwari|hod of bca|coordinator of bca)", re.IGNORECASE),
        ],
        keywords_all=["bca"],
        keywords_any=["faculty", "teacher", "teachers", "teaches", "prof", "professor", "professors", "hod", "coordinator", "staff"],
        target_entity="MCA Faculty",
        description="Computing faculty alias",
    ),
    IntentDefinition(
        intent_id="faculty_general",
        category=IntentCategory.FACULTY,
        priority=50,
        patterns=[
            re.compile(r"(faculty members|teachers in college|professors|department heads|list of hods|teaching staff)", re.IGNORECASE),
        ],
        description="Teaching faculty overview across departments",
    ),

    # 10. Department Inquiries (Priority 60)
    IntentDefinition(
        intent_id="departments_list",
        category=IntentCategory.DEPARTMENT,
        priority=60,
        patterns=[
            re.compile(r"(what departments|departments in college|list of departments|academic departments)", re.IGNORECASE),
        ],
        description="Academic departments at JDCOEM (MCA, CSE, AI/DS, IT, ETC, MBA)",
    ),

    # 11. Campus Facilities (Priority 75 for specific, 50 for general)
    IntentDefinition(
        intent_id="facility_tbi",
        category=IntentCategory.FACILITIES,
        priority=75,
        patterns=[
            re.compile(r"(tbi|incubation|incubator|technology business incubator|startup|innovation wing|entrepreneurship|patents)", re.IGNORECASE),
        ],
        target_entity="Technology Business Incubator (TBI)",
        description="Campus Technology Business Incubator (TBI) and student startup support",
    ),
    IntentDefinition(
        intent_id="facility_bus",
        category=IntentCategory.FACILITIES,
        priority=75,
        patterns=[
            re.compile(r"(bus|transport|transportation|bus routes|college bus|bus stop|pickup|kalmeshwar bus|nagpur bus)", re.IGNORECASE),
        ],
        target_entity="Fleet Bus Transportation",
        description="College bus transportation network across Nagpur",
    ),
    IntentDefinition(
        intent_id="facility_library",
        category=IntentCategory.LIBRARY,
        priority=75,
        patterns=[
            re.compile(r"(library|books in library|library timings|reading room|digital library|ieee|delnet)", re.IGNORECASE),
        ],
        target_entity="Central Library",
        description="Central digital library collection and timings",
    ),
    IntentDefinition(
        intent_id="facility_hostel",
        category=IntentCategory.HOSTEL,
        priority=75,
        patterns=[
            re.compile(r"(hostel|boys hostel|girls hostel|hostel rent|hostel fee|accommodation|hostel mess)", re.IGNORECASE),
        ],
        target_entity="Campus Hostels (Boys & Girls)",
        description="On-campus hostel accommodations and mess dining",
    ),
    IntentDefinition(
        intent_id="facility_sports",
        category=IntentCategory.SPORTS,
        priority=75,
        patterns=[
            re.compile(r"(sports|gymnasium|gym|cricket|turf|football|basketball|badminton|jalsa|cultural fest)", re.IGNORECASE),
        ],
        target_entity="Sports & Cultural Complex",
        description="Sports turf, gymnasium, and cultural fest Jalsa",
    ),
    IntentDefinition(
        intent_id="facility_labs",
        category=IntentCategory.FACILITIES,
        priority=70,
        patterns=[
            re.compile(r"(computer lab|gpu lab|ai lab|practical lab|science lab|laboratories)", re.IGNORECASE),
        ],
        target_entity="High-Performance Computing & AI Labs",
        description="High-performance computing and AI laboratories",
    ),

    # 12. College Policies & Regulations (Priority 65)
    IntentDefinition(
        intent_id="policy_attendance",
        category=IntentCategory.ATTENDANCE,
        priority=65,
        patterns=[
            re.compile(r"(attendance policy|attendance compulsory|minimum attendance|75% attendance|attendance rule)", re.IGNORECASE),
        ],
        description="Mandatory 75% attendance regulations under DBATU/JDCOEM Autonomous norms",
    ),
    IntentDefinition(
        intent_id="policy_placements",
        category=IntentCategory.COLLEGE_INFO,
        priority=70,
        patterns=[
            re.compile(r"(placement|placements|campus placement|highest package|average package|tcs|infosys|wipro|capgemini|recruiters|companies visiting|package)", re.IGNORECASE),
        ],
        description="Campus placement statistics, top recruiters, and salary packages",
    ),
    IntentDefinition(
        intent_id="policy_mca_project",
        category=IntentCategory.COURSES,
        priority=70,
        patterns=[
            re.compile(r"(mca project|capstone project|final year project|internship for mca|software project)", re.IGNORECASE),
        ],
        description="MCA final year capstone software project and industry internship guidelines",
    ),
    IntentDefinition(
        intent_id="policy_ragging",
        category=IntentCategory.COLLEGE_INFO,
        priority=65,
        patterns=[
            re.compile(r"(ragging|anti ragging|bullying in college|is ragging allowed|discipline)", re.IGNORECASE),
        ],
        description="Strict anti-ragging zero tolerance prohibition",
    ),

    # 13. Institutional Background & Contact (Priority 50)
    IntentDefinition(
        intent_id="college_overview",
        category=IntentCategory.COLLEGE_INFO,
        priority=50,
        patterns=[
            re.compile(r"(about college|about jd|about jdcoem|when was college established|is it private or government|college motto|accreditation|naac grade|dbatu|autonomous)", re.IGNORECASE),
        ],
        description="JDCOEM institutional profile, autonomous status, NAAC 'A' grade, and DBATU affiliation",
    ),
    IntentDefinition(
        intent_id="contact_info",
        category=IntentCategory.CONTACT,
        priority=50,
        patterns=[
            re.compile(r"(contact details|address|phone number|email address|where is the college located|office timings|location|kalmeshwar|khandala|borgaon fata)", re.IGNORECASE),
        ],
        description="JDCOEM campus address, phone helplines, email, and location",
    ),
]
