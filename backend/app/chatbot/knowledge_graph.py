"""Academic Knowledge Graph for CampusIQ (JDCOEM).

Provides a relational, entity-relationship graph modeling College, Department, Program,
Semester, Subject, Faculty, Timetable, ExamSchedule, AcademicDocument, and FeeStructure.
Enables relationship traversal, alias resolution, and minimal fact retrieval.
"""

from dataclasses import dataclass, field
import re
from typing import Any, Dict, List, Optional, Set, Tuple


@dataclass
class KGNode:
    """Represents an academic entity in the Knowledge Graph."""
    id: str
    type: str  # College, Department, Program, Semester, Subject, Faculty, Timetable, ExamSchedule, AcademicDocument, FeeStructure, LabCourse
    name: str
    code: Optional[str] = None
    properties: Dict[str, Any] = field(default_factory=dict)
    aliases: List[str] = field(default_factory=list)


@dataclass
class KGEdge:
    """Represents a typed relationship between two academic entities."""
    source_id: str
    relation: str  # OFFERS_PROGRAM, HAS_SEMESTER, CONTAINS_SUBJECT, HAS_CREDITS, HAS_LAB, TAUGHT_BY, HAS_TIMETABLE, HAS_EXAM_SCHEDULE, DOCUMENT_CONTAINS, BELONGS_TO_DEPARTMENT
    target_id: str
    properties: Dict[str, Any] = field(default_factory=dict)


class AcademicKnowledgeGraph:
    """Authoritative Knowledge Graph representing verified JDCOEM academic relationships."""

    def __init__(self):
        self.nodes: Dict[str, KGNode] = {}
        self.edges: List[KGEdge] = []
        self._alias_index: Dict[str, str] = {}
        self._build_static_graph()

    def add_node(self, node: KGNode) -> None:
        """Register a node and index its aliases."""
        self.nodes[node.id] = node
        # Index node ID
        self._alias_index[node.id.lower()] = node.id
        # Index node name
        self._alias_index[node.name.lower()] = node.id
        # Index node code if present
        if node.code:
            self._alias_index[node.code.lower()] = node.id
        # Index all aliases
        for alias in node.aliases:
            self._alias_index[alias.lower().strip()] = node.id

    def add_edge(self, source_id: str, relation: str, target_id: str, properties: Optional[Dict[str, Any]] = None) -> None:
        """Register a directed relationship edge."""
        self.edges.append(
            KGEdge(source_id=source_id, relation=relation, target_id=target_id, properties=properties or {})
        )

    def get_node(self, node_id: str) -> Optional[KGNode]:
        """Retrieve node by ID."""
        return self.nodes.get(node_id)

    def find_node(self, query: str, node_type: Optional[str] = None) -> Optional[KGNode]:
        """Resolve a query string or alias to a matching node."""
        if not query:
            return None
        norm = re.sub(r"[^\w\s\-]", "", query.lower()).strip()
        # Direct alias match
        if norm in self._alias_index:
            node = self.nodes.get(self._alias_index[norm])
            if node and (not node_type or node.type == node_type):
                return node

        # Substring / partial match (prefer exact or longer match)
        candidates = []
        for alias, node_id in self._alias_index.items():
            if norm == alias or (len(alias) > 3 and alias in norm):
                node = self.nodes.get(node_id)
                if node and (not node_type or node.type == node_type):
                    candidates.append((node, len(alias)))
        if candidates:
            candidates.sort(key=lambda x: x[1], reverse=True)
            return candidates[0][0]

        return None

    def get_outgoing(self, source_id: str, relation: Optional[str] = None) -> List[Tuple[KGEdge, KGNode]]:
        """Retrieve outgoing edges and target nodes."""
        results = []
        for edge in self.edges:
            if edge.source_id == source_id:
                if not relation or edge.relation == relation:
                    target_node = self.nodes.get(edge.target_id)
                    if target_node:
                        results.append((edge, target_node))
        return results

    def get_incoming(self, target_id: str, relation: Optional[str] = None) -> List[Tuple[KGEdge, KGNode]]:
        """Retrieve incoming edges and source nodes."""
        results = []
        for edge in self.edges:
            if edge.target_id == target_id:
                if not relation or edge.relation == relation:
                    source_node = self.nodes.get(edge.source_id)
                    if source_node:
                        results.append((edge, source_node))
        return results

    # -------------------------------------------------------------------------
    # Graph Construction with Authoritative Institutional Records
    # -------------------------------------------------------------------------
    def _build_static_graph(self) -> None:
        """Populate the graph with verified JDCOEM MCA curriculum, faculty, schedules & documents."""

        # 1. College Node
        self.add_node(
            KGNode(
                id="inst:jdcoem",
                type="College",
                name="JD College of Engineering and Management (JDCOEM), Nagpur",
                code="04138",
                properties={
                    "established": 2008,
                    "affiliation": "Dr. Babasaheb Ambedkar Technological University (DBATU), Lonere",
                    "status": "Autonomous Institute",
                    "accreditation": "NAAC 'A' Grade, Approved by AICTE New Delhi",
                    "dte_code": "04138",
                    "principal": "Dr. Shrikant V. Sonekar",
                    "address": "Khandala/Valni, Near Hanuman Temple, Borgaon Fata, Kalmeshwar Road, Nagpur — 441501",
                    "phone": "+91-90110 10038 / +91-7774041329",
                    "email": "info@jdcoem.ac.in",
                    "website": "https://jdcoem.ac.in",
                },
                aliases=["jdcoem", "jd college", "jd college of engineering", "college", "campus"],
            )
        )

        # 2. Department Node
        self.add_node(
            KGNode(
                id="dept:mca",
                type="Department",
                name="Department of Master of Computer Applications (MCA)",
                code="MCA_DEPT",
                properties={
                    "hod": "Prof. Rohan Kokate",
                    "intake": 120,
                    "duration": "2 Years (4 Semesters)",
                    "affiliation": "DBATU Autonomous",
                },
                aliases=["mca department", "department of mca", "dept of mca", "computer application department"],
            )
        )
        self.add_edge("inst:jdcoem", "BELONGS_TO_DEPARTMENT", "dept:mca")

        # 3. Program Node
        self.add_node(
            KGNode(
                id="prog:mca",
                type="Program",
                name="Master of Computer Applications (MCA)",
                code="MCA",
                properties={
                    "level": "Postgraduate (PG)",
                    "duration_years": 2,
                    "semesters": 4,
                    "total_credits": 88,
                    "intake": 120,
                    "dte_choice_code": "0413824110",
                    "eligibility": "BCA/B.Sc/B.Com/B.A with Mathematics at 10+2 or graduation with min 50% (45% for reserved) and valid MAH-MCA-CET score.",
                    "annual_fee_open": 91500,
                },
                aliases=["mca", "mca course", "mca program", "master of computer applications"],
            )
        )
        self.add_edge("dept:mca", "OFFERS_PROGRAM", "prog:mca")

        # 4. Semester Nodes
        self.add_node(
            KGNode(
                id="sem:mca_sem1",
                type="Semester",
                name="MCA Semester 1",
                code="SEM1",
                properties={
                    "semester_number": 1,
                    "program": "MCA",
                    "total_credits": 22,
                    "total_marks": 800,
                    "academic_year": "2024-2026",
                    "document_id": 5,
                    "document_filename": "MCA SEM 1 Syllabus Final.pdf",
                },
                aliases=["mca sem 1", "mca semester 1", "sem 1", "semester 1", "first sem", "1st sem", "mca sem-i", "sem i"],
            )
        )
        self.add_edge("prog:mca", "HAS_SEMESTER", "sem:mca_sem1")

        self.add_node(
            KGNode(
                id="sem:mca_sem2",
                type="Semester",
                name="MCA Semester 2",
                code="SEM2",
                properties={
                    "semester_number": 2,
                    "program": "MCA",
                    "total_credits": 22,
                    "total_marks": 800,
                    "academic_year": "2024-2026",
                    "document_id": 6,
                    "document_filename": "MCA SEM 2 Syllabus Final.pdf",
                },
                aliases=["mca sem 2", "mca semester 2", "sem 2", "semester 2", "second sem", "2nd sem", "mca sem-ii", "sem ii"],
            )
        )
        self.add_edge("prog:mca", "HAS_SEMESTER", "sem:mca_sem2")

        # 5. Documents
        self.add_node(
            KGNode(
                id="doc:sem1_syllabus",
                type="AcademicDocument",
                name="MCA Semester 1 Academic Scheme & Syllabus (Final)",
                code="DOC_SEM1_SYLLABUS",
                properties={
                    "document_id": 5,
                    "filename": "MCA SEM 1 Syllabus Final.pdf",
                    "category": "syllabus",
                    "pages": 22,
                    "semester": 1,
                    "view_url": "/api/v1/documents/5/view",
                    "download_url": "/api/v1/documents/5/download",
                },
                aliases=["sem 1 syllabus pdf", "sem 1 syllabus document", "first sem syllabus file"],
            )
        )
        self.add_edge("sem:mca_sem1", "DOCUMENT_CONTAINS", "doc:sem1_syllabus")

        self.add_node(
            KGNode(
                id="doc:sem2_syllabus",
                type="AcademicDocument",
                name="MCA Semester 2 Academic Scheme & Syllabus (Final)",
                code="DOC_SEM2_SYLLABUS",
                properties={
                    "document_id": 6,
                    "filename": "MCA SEM 2 Syllabus Final.pdf",
                    "category": "syllabus",
                    "pages": 26,
                    "semester": 2,
                    "view_url": "/api/v1/documents/6/view",
                    "download_url": "/api/v1/documents/6/download",
                },
                aliases=["sem 2 syllabus pdf", "sem 2 syllabus document", "second sem syllabus file", "full syllabus"],
            )
        )
        self.add_edge("sem:mca_sem2", "DOCUMENT_CONTAINS", "doc:sem2_syllabus")

        self.add_node(
            KGNode(
                id="doc:academic_calendar",
                type="AcademicDocument",
                name="MCA Semester 1 & 2 Academic Calendar (Autonomous)",
                code="DOC_ACADEMIC_CALENDAR",
                properties={
                    "document_id": 7,
                    "filename": "MCA-Ist sem Academic Calendar .pdf",
                    "category": "calendar",
                    "pages": 3,
                    "view_url": "/api/v1/documents/7/view",
                    "download_url": "/api/v1/documents/7/download",
                },
                aliases=["academic calendar", "calendar", "exam calendar", "semester schedule"],
            )
        )
        self.add_edge("prog:mca", "HAS_TIMETABLE", "doc:academic_calendar")

        # 6. SEMESTER 2 SUBJECTS & LABS (Authoritative from Doc 6)
        sem2_subjects = [
            {
                "id": "subj:mc2t001",
                "code": "MC2T001",
                "name": "Database Management System",
                "short_name": "DBMS",
                "category": "Program Core Course (PCC - Theory)",
                "credits": 4,
                "ltp": "4-0-0",
                "ca_marks": 40,
                "ese_marks": 60,
                "total_marks": 100,
                "lab_code": "MC2L006",
                "description": "DBMS covers how enterprise data is structured, modeled, stored, queried, and protected against concurrency failures.",
                "units": [
                    "Unit I: Database System Concepts, Purpose, View of Data, Data Abstraction & ER Modeling",
                    "Unit II: Relational Data Model, Relational Algebra, DDL, DML, DCL, TCL & Structured Query Language (SQL)",
                    "Unit III: Relational Database Design, Functional Dependencies & Normalization (1NF, 2NF, 3NF, BCNF)",
                    "Unit IV: Transaction Processing, ACID Properties, Schedules & Serializability",
                    "Unit V: Concurrency Control, Lock-Based Protocols, Timestamp Ordering & Database Recovery",
                ],
                "page": 2,
                "aliases": ["dbms", "database", "database management", "database management system", "database management systems", "rdbms", "mc2t001", "database subject", "mca database course", "data base management system"],
            },
            {
                "id": "subj:mc2t002",
                "code": "MC2T002",
                "name": "Artificial Intelligence",
                "short_name": "AI",
                "category": "Program Core Course (PCC - Theory)",
                "credits": 4,
                "ltp": "4-0-0",
                "ca_marks": 40,
                "ese_marks": 60,
                "total_marks": 100,
                "lab_code": None,
                "description": "Artificial Intelligence focuses on intelligent agent architectures, heuristic search, logical knowledge representation, and machine learning fundamentals.",
                "units": [
                    "Unit I: Introduction to AI, Features of AI, Agents & Environments, Structure of Agents",
                    "Unit II: Problem Formulation & Uninformed/Informed Searching (Breadth-First, Depth-First, A* Search, Minimax)",
                    "Unit III: Knowledge Representation, First-Order Logic, Inference Rules & Semantic Networks",
                    "Unit IV: Planning, Reasoning under Uncertainty, Probability & Bayesian Networks",
                    "Unit V: Machine Learning Fundamentals, Expert Systems & Modern AI Applications",
                ],
                "page": 5,
                "aliases": ["ai", "artificial intelligence", "mc2t002", "ai subject", "artificial intelligence course"],
            },
            {
                "id": "subj:mc2t003",
                "code": "MC2T003",
                "name": "Data Science Using Python",
                "short_name": "Python",
                "category": "Program Core Course (PCC - Theory)",
                "credits": 3,
                "ltp": "3-0-0",
                "ca_marks": 40,
                "ese_marks": 60,
                "total_marks": 100,
                "lab_code": "MC2L007",
                "description": "Covers Python programming, statistical analysis, data cleaning, Pandas, NumPy, and exploratory data analysis (EDA).",
                "units": [
                    "Unit I: Introduction to Data Science, Data Roles, Structured vs Unstructured Data",
                    "Unit II: Python Foundations, NumPy Arrays, Numerical Operations & Vectorization",
                    "Unit III: Data Manipulation with Pandas, Series, DataFrames & Data Cleaning",
                    "Unit IV: Statistical Data Analysis, Distributions, Hypothesis Testing & Correlation",
                    "Unit V: Exploratory Data Analysis (EDA) & Data Visualization with Matplotlib & Seaborn",
                ],
                "page": 8,
                "aliases": ["data science using python", "python", "data science", "mc2t003", "python programming", "ds using python"],
            },
            {
                "id": "subj:mc2t004",
                "code": "MC2T004",
                "name": "Cyber Security & Cryptography",
                "short_name": "Cyber Security",
                "category": "Program Core Course (PCC - Theory)",
                "credits": 3,
                "ltp": "3-0-0",
                "ca_marks": 40,
                "ese_marks": 60,
                "total_marks": 100,
                "lab_code": None,
                "description": "Covers cyber threat landscapes, cryptographic primitives, symmetric and asymmetric ciphers, digital signatures, and network security protocols.",
                "units": [
                    "Unit I: Introduction to Cyber Security, Threats, Vulnerabilities & Security Principles (CIA Triad)",
                    "Unit II: Classical & Modern Symmetric Ciphers, DES, AES & Block Cipher Modes",
                    "Unit III: Asymmetric Cryptography, RSA Algorithm, Diffie-Hellman Key Exchange",
                    "Unit IV: Cryptographic Hash Functions, Message Authentication Codes (MAC) & Digital Signatures",
                    "Unit V: Network Security Protocols, SSL/TLS, Firewalls & Cyber Law Fundamentals",
                ],
                "page": 11,
                "aliases": ["cyber security", "cryptography", "cyber security & cryptography", "cyber security and cryptography", "mc2t004"],
            },
            {
                "id": "subj:mc2e005",
                "code": "MC2E005",
                "name": "Department Elective-I",
                "short_name": "Department Elective-I",
                "category": "Program Elective Course (PEC - Theory)",
                "credits": 2,
                "ltp": "2-0-0",
                "ca_marks": 40,
                "ese_marks": 60,
                "total_marks": 100,
                "lab_code": "MC2L008",
                "description": "Elective basket offering specialization in Web Technologies (PHP), Visual Computing (Computer Graphics), or Academic Research (Research Methodology).",
                "units": [
                    "Track 1 (PHP): Server-side Scripting, Superglobals, Form Handling, MySQL Connectivity & Sessions",
                    "Track 2 (Computer Graphics): Display Devices, Scan Conversion, 2D/3D Transformations, Viewing & Clipping",
                    "Track 3 (Research Methodology): Research Problem Formulation, Literature Review, Sampling & Data Analysis",
                ],
                "page": 14,
                "aliases": ["elective", "department elective", "elective 1", "elective-i", "mc2e005", "php elective", "computer graphics", "research methodology"],
            },
            {
                "id": "subj:mc2l006",
                "code": "MC2L006",
                "name": "DBMS Lab",
                "short_name": "DBMS Lab",
                "category": "Program Core Course (PCC - Laboratory)",
                "credits": 2,
                "ltp": "0-0-4",
                "ca_marks": 60,
                "ese_marks": 40,
                "total_marks": 100,
                "lab_code": None,
                "description": "Hands-on SQL schema creation, data manipulation, joins, subqueries, view creation, PL/SQL stored procedures, and triggers.",
                "units": [
                    "Lab Practical 1: DDL Commands (CREATE, ALTER, DROP, TRUNCATE) with integrity constraints",
                    "Lab Practical 2: DML Queries (INSERT, UPDATE, DELETE, SELECT) & Complex Nested Joins",
                    "Lab Practical 3: Aggregation, GROUP BY, HAVING, and Subqueries",
                    "Lab Practical 4: Views, Indexes, and Sequence Generation",
                    "Lab Practical 5: PL/SQL Blocks, Cursors, Stored Procedures, Functions, and Triggers",
                ],
                "page": 23,
                "aliases": ["dbms lab", "database lab", "mc2l006", "database management system lab", "sql lab"],
            },
            {
                "id": "subj:mc2l007",
                "code": "MC2L007",
                "name": "Python Lab",
                "short_name": "Python Lab",
                "category": "Program Core Course (PCC - Laboratory)",
                "credits": 2,
                "ltp": "0-0-4",
                "ca_marks": 60,
                "ese_marks": 40,
                "total_marks": 100,
                "lab_code": None,
                "description": "Practical Python programming, implementing data structures, NumPy arrays, Pandas DataFrames, and exploratory data visualizations.",
                "units": [
                    "Lab Practical 1: Python syntax, list comprehensions, tuples, dictionaries, and functional tools",
                    "Lab Practical 2: NumPy multi-dimensional array operations, slicing, and linear algebra",
                    "Lab Practical 3: Pandas data loading, filtering, handling missing values, and group aggregations",
                    "Lab Practical 4: Data visualization using Matplotlib and Seaborn (histograms, heatmaps, scatter plots)",
                    "Lab Practical 5: Mini project: Exploratory Data Analysis on a real-world CSV dataset",
                ],
                "page": 24,
                "aliases": ["python lab", "python programming lab", "mc2l007", "data science lab", "ds lab"],
            },
            {
                "id": "subj:mc2l008",
                "code": "MC2L008",
                "name": "PHP Lab",
                "short_name": "PHP Lab",
                "category": "Program Core Course (PCC - Laboratory)",
                "credits": 2,
                "ltp": "0-0-4",
                "ca_marks": 60,
                "ese_marks": 40,
                "total_marks": 100,
                "lab_code": None,
                "description": "Hands-on server-side scripting in PHP, processing GET/POST forms, session management, and building dynamic database-driven web applications with MySQL.",
                "units": [
                    "Lab Practical 1: PHP environment setup, syntax, variables, arrays, and control structures",
                    "Lab Practical 2: Form handling, input validation, and sanitization using PHP superglobals",
                    "Lab Practical 3: User authentication using Cookies and Session variables",
                    "Lab Practical 4: MySQL database connection via PDO / MySQLi and executing CRUD queries",
                    "Lab Practical 5: Developing a complete student registration and inquiry portal in PHP & MySQL",
                ],
                "page": 26,
                "aliases": ["php lab", "php web lab", "mc2l008", "web lab sem 2", "web technology lab"],
            },
        ]

        for s in sem2_subjects:
            node = KGNode(
                id=s["id"],
                type="Subject" if not s["code"].startswith("MC2L") else "LabCourse",
                name=s["name"],
                code=s["code"],
                properties={
                    "semester": 2,
                    "program": "MCA",
                    "short_name": s.get("short_name", s["name"]),
                    "category": s["category"],
                    "credits": s["credits"],
                    "ltp": s["ltp"],
                    "ca_marks": s["ca_marks"],
                    "ese_marks": s["ese_marks"],
                    "total_marks": s["total_marks"],
                    "description": s["description"],
                    "units": s["units"],
                    "page_number": s["page"],
                    "document_id": 6,
                    "document_filename": "MCA SEM 2 Syllabus Final.pdf",
                    "view_url": "/api/v1/documents/6/view",
                },
                aliases=s["aliases"],
            )
            self.add_node(node)
            self.add_edge("sem:mca_sem2", "CONTAINS_SUBJECT", s["id"])
            if s.get("lab_code"):
                self.add_edge(s["id"], "HAS_LAB", f"subj:{s['lab_code'].lower()}")

        # 7. SEMESTER 1 SUBJECTS & LABS (Authoritative from Doc 5)
        sem1_subjects = [
            {
                "id": "subj:mc1t001",
                "code": "MC1T001",
                "name": "Data Structures & Algorithms",
                "short_name": "DSA",
                "category": "Program Core Course (PCC - Theory)",
                "credits": 4,
                "ltp": "4-0-0",
                "ca_marks": 40,
                "ese_marks": 60,
                "total_marks": 100,
                "lab_code": "MC1L006",
                "description": "Covers linear and non-linear data structures, algorithm analysis, sorting, searching, trees, and graphs.",
                "units": [
                    "Unit I: Introduction to Data Structures, Asymptotic Notation & Complexity Analysis",
                    "Unit II: Arrays, Linear/Binary Searching & Sorting Algorithms (Bubble, Merge, Quick Sort)",
                    "Unit III: Stacks, Queues, Circular Queues & Linked List Implementations",
                    "Unit IV: Trees, Binary Search Trees (BST), AVL Trees & Tree Traversals",
                    "Unit V: Graph Representations, BFS, DFS, Minimum Spanning Trees (Prim's & Kruskal's)",
                ],
                "page": 2,
                "aliases": ["dsa", "data structures", "data structures and algorithms", "data structures & algorithms", "mc1t001", "dsa subject"],
            },
            {
                "id": "subj:mc1t002",
                "code": "MC1T002",
                "name": "Object Oriented Programming using JAVA",
                "short_name": "Java",
                "category": "Program Core Course (PCC - Theory)",
                "credits": 3,
                "ltp": "3-0-0",
                "ca_marks": 40,
                "ese_marks": 60,
                "total_marks": 100,
                "lab_code": "MC1L007",
                "description": "Teaches object-oriented paradigms in Java: inheritance, encapsulation, polymorphism, exceptions, and multithreading.",
                "units": [
                    "Unit I: OOP Concepts, Abstraction, Inheritance, Encapsulation & Classes in Java",
                    "Unit II: Packages, Interfaces, Exception Handling & Built-in Exception Hierarchies",
                    "Unit III: Multithreading, Thread Synchronization, Inter-thread Communication",
                    "Unit IV: Java Collections Framework, Generics, Lists, Sets & Maps",
                    "Unit V: I/O Streams, File Handling & GUI Programming basics",
                ],
                "page": 5,
                "aliases": ["java", "oop using java", "object oriented programming using java", "mc1t002", "java programming"],
            },
            {
                "id": "subj:mc1t003",
                "code": "MC1T003",
                "name": "Operating System",
                "short_name": "OS",
                "category": "Program Core Course (PCC - Theory)",
                "credits": 3,
                "ltp": "3-0-0",
                "ca_marks": 40,
                "ese_marks": 60,
                "total_marks": 100,
                "lab_code": None,
                "description": "Covers OS architectures, process scheduling, synchronization, deadlocks, memory management, and file systems.",
                "units": [
                    "Unit I: OS Overview, System Calls, Structure of Modern Operating Systems",
                    "Unit II: Process Management, CPU Scheduling Algorithms, Threads & IPC",
                    "Unit III: Process Synchronization, Critical Section Problem, Semaphores & Deadlock Handling",
                    "Unit IV: Memory Management, Paging, Segmentation, Virtual Memory & Page Replacement",
                    "Unit V: File System Interface, Storage Management & Disk Scheduling",
                ],
                "page": 8,
                "aliases": ["os", "operating system", "operating systems", "mc1t003", "os subject"],
            },
            {
                "id": "subj:mc1t004",
                "code": "MC1T004",
                "name": "Discrete Mathematics & Graph Theory",
                "short_name": "Discrete Math",
                "category": "Program Core Course (PCC - Theory)",
                "credits": 3,
                "ltp": "3-0-0",
                "ca_marks": 40,
                "ese_marks": 60,
                "total_marks": 100,
                "lab_code": None,
                "description": "Covers mathematical foundations for computing: sets, relations, propositional logic, graph theory, and combinatorics.",
                "units": [
                    "Unit I: Sets, Relations, Functions, Equivalence Relations & Partial Orderings",
                    "Unit II: Mathematical Logic, Propositional & Predicate Calculus, Normal Forms",
                    "Unit III: Algebraic Structures, Groups, Rings, Fields & Boolean Algebra",
                    "Unit IV: Graph Theory Fundamentals, Euler Graphs, Hamiltonian Paths & Planar Graphs",
                    "Unit V: Trees, Spanning Trees, Graph Coloring & Recurrence Relations",
                ],
                "page": 11,
                "aliases": ["discrete mathematics", "graph theory", "discrete math", "mc1t004", "discrete mathematics and graph theory"],
            },
            {
                "id": "subj:mc1a005",
                "code": "MC1A005",
                "name": "Computer Architecture & Organization",
                "short_name": "CAO",
                "category": "Ability Enhancement Course (AEC - Theory)",
                "credits": 3,
                "ltp": "3-0-0",
                "ca_marks": 40,
                "ese_marks": 60,
                "total_marks": 100,
                "lab_code": None,
                "description": "Explains digital logic, CPU architecture, instruction pipelining, memory hierarchies, and I/O interfacing.",
                "units": [
                    "Unit I: Basic Computer Organization, Instruction Formats & Addressing Modes",
                    "Unit II: Central Processing Unit (CPU) Design, Register Transfer & Control Unit",
                    "Unit III: Computer Arithmetic, Addition, Subtraction, Multiplication & Floating-point",
                    "Unit IV: Input/Output Organization, Asynchronous Data Transfer, DMA & Interrupts",
                    "Unit V: Memory Hierarchy, Cache Memory, Virtual Memory & Memory Management Hardware",
                ],
                "page": 14,
                "aliases": ["computer architecture", "cao", "computer architecture & organization", "computer architecture and organization", "mc1a005"],
            },
            {
                "id": "subj:mc1l006",
                "code": "MC1L006",
                "name": "DSA Lab",
                "short_name": "DSA Lab",
                "category": "Program Core Course (PCC - Laboratory)",
                "credits": 2,
                "ltp": "0-0-4",
                "ca_marks": 60,
                "ese_marks": 40,
                "total_marks": 100,
                "lab_code": None,
                "description": "Hands-on implementation of linear and non-linear data structures, sorting algorithms, and graph traversals in C/C++.",
                "units": [
                    "Practical 1: Implementation of Stacks and Queues using dynamic arrays",
                    "Practical 2: Singly, Doubly, and Circular Linked Lists operations",
                    "Practical 3: Binary Search Tree (BST) creation and traversal algorithms",
                    "Practical 4: Quick Sort, Merge Sort, and Heap Sort performance benchmarking",
                    "Practical 5: Graph traversal algorithms (BFS and DFS)",
                ],
                "page": 18,
                "aliases": ["dsa lab", "data structures lab", "mc1l006", "data structures and algorithms lab"],
            },
            {
                "id": "subj:mc1l007",
                "code": "MC1L007",
                "name": "Java Lab",
                "short_name": "Java Lab",
                "category": "Program Core Course (PCC - Laboratory)",
                "credits": 2,
                "ltp": "0-0-4",
                "ca_marks": 60,
                "ese_marks": 40,
                "total_marks": 100,
                "lab_code": None,
                "description": "Practical Java programming: classes, inheritance hierarchies, custom exception handlers, multithreading, and collections.",
                "units": [
                    "Practical 1: Class design, constructors, method overloading, and overriding",
                    "Practical 2: Inheritance hierarchies and abstract base classes in Java",
                    "Practical 3: Custom exception classes and try-catch-finally handling",
                    "Practical 4: Multi-threaded Java applications and thread synchronization",
                    "Practical 5: Java Collections Framework: ArrayList, HashMap, and Iterators",
                ],
                "page": 20,
                "aliases": ["java lab", "oop using java lab", "mc1l007", "oop java lab"],
            },
            {
                "id": "subj:mc1l008",
                "code": "MC1L008",
                "name": "Web Development Lab",
                "short_name": "Web Lab",
                "category": "Program Core Course (PCC - Laboratory)",
                "credits": 2,
                "ltp": "0-0-4",
                "ca_marks": 60,
                "ese_marks": 40,
                "total_marks": 100,
                "lab_code": None,
                "description": "Hands-on web engineering: semantic HTML5, CSS3 responsive grid/flexbox, JavaScript ES6+ DOM scripting, and responsive UI design.",
                "units": [
                    "Practical 1: Semantic HTML5 structure and accessible document layout",
                    "Practical 2: Modern CSS3 styling, Flexbox, Grid, and Media Queries",
                    "Practical 3: JavaScript DOM manipulation, event listeners, and interactive UI",
                    "Practical 4: Asynchronous JavaScript (Fetch API, Promises, Async/Await)",
                    "Practical 5: Responsive web application project",
                ],
                "page": 22,
                "aliases": ["web development lab", "web lab", "mc1l008", "html css lab"],
            },
        ]

        for s in sem1_subjects:
            node = KGNode(
                id=s["id"],
                type="Subject" if not s["code"].startswith("MC1L") else "LabCourse",
                name=s["name"],
                code=s["code"],
                properties={
                    "semester": 1,
                    "program": "MCA",
                    "short_name": s.get("short_name", s["name"]),
                    "category": s["category"],
                    "credits": s["credits"],
                    "ltp": s["ltp"],
                    "ca_marks": s["ca_marks"],
                    "ese_marks": s["ese_marks"],
                    "total_marks": s["total_marks"],
                    "description": s["description"],
                    "units": s["units"],
                    "page_number": s["page"],
                    "document_id": 5,
                    "document_filename": "MCA SEM 1 Syllabus Final.pdf",
                    "view_url": "/api/v1/documents/5/view",
                },
                aliases=s["aliases"],
            )
            self.add_node(node)
            self.add_edge("sem:mca_sem1", "CONTAINS_SUBJECT", s["id"])
            if s.get("lab_code"):
                self.add_edge(s["id"], "HAS_LAB", f"subj:{s['lab_code'].lower()}")

        # 8. Faculty Nodes
        faculty_data = [
            {
                "id": "fac:rohan_kokate",
                "name": "Prof. Rohan Kokate",
                "designation": "Assistant Professor & Head of Department (HOD)",
                "qualification": "M.Tech (CSE), Ph.D. (Pursuing)",
                "specialization": "Distributed Systems, Cloud Architecture, Artificial Intelligence",
                "email": "rohan.kokate@jdcoem.ac.in",
                "aliases": ["rohan kokate", "prof rohan kokate", "hod mca", "mca hod", "head of department"],
            },
            {
                "id": "fac:chetan_padole",
                "name": "Prof. Chetan Padole",
                "designation": "Assistant Professor & TBI Incubation Incharge",
                "qualification": "M.E. (Wireless Comm), Ph.D. (Pursuing)",
                "specialization": "Startup Incubation, Embedded Systems, IoT, Machine Learning",
                "email": "chetan.padole@jdcoem.ac.in",
                "aliases": ["chetan padole", "prof chetan padole", "tbi incharge", "tbi coordinator"],
            },
            {
                "id": "fac:principal",
                "name": "Dr. Shrikant V. Sonekar",
                "designation": "Principal & Professor",
                "qualification": "Ph.D. (Electronics Engineering), M.Tech, B.E.",
                "specialization": "Digital Signal Processing, Embedded Systems, Institutional Governance",
                "email": "principal@jdcoem.ac.in",
                "aliases": ["principal", "dr shrikant sonekar", "dr sonekar", "shrikant sonekar"],
            },
        ]
        for f in faculty_data:
            node = KGNode(
                id=f["id"],
                type="Faculty",
                name=f["name"],
                properties=f,
                aliases=f["aliases"],
            )
            self.add_node(node)
            self.add_edge("dept:mca", "TAUGHT_BY", f["id"])

        # 9. Timetable & Schedule Node
        self.add_node(
            KGNode(
                id="sched:mca_sem2_timetable",
                type="Timetable",
                name="MCA Semester 2 Class Timetable",
                code="TIMETABLE_SEM2",
                properties={
                    "semester": 2,
                    "program": "MCA",
                    "college_timing": "09:30 AM to 04:30 PM (Monday to Friday)",
                    "slots": [
                        {"time": "09:30 AM - 10:30 AM", "type": "Theory Lecture", "subject": "Database Management System (MC2T001)"},
                        {"time": "10:30 AM - 11:30 AM", "type": "Theory Lecture", "subject": "Artificial Intelligence (MC2T002)"},
                        {"time": "11:30 AM - 11:45 AM", "type": "Break", "subject": "Tea & Morning Recess"},
                        {"time": "11:45 AM - 12:45 PM", "type": "Theory Lecture", "subject": "Data Science Using Python (MC2T003) / Cyber Security (MC2T004)"},
                        {"time": "12:45 PM - 01:30 PM", "type": "Lunch", "subject": "Lunch Break"},
                        {"time": "01:30 PM - 03:30 PM", "type": "Laboratory Session", "subject": "Batch Practical: DBMS Lab (MC2L006) / Python Lab (MC2L007) / PHP Lab (MC2L008)"},
                        {"time": "03:30 PM - 04:30 PM", "type": "Tutorial & Library", "subject": "Department Elective-I (MC2E005) & Remedial Mentoring"},
                    ],
                    "document_id": 7,
                    "view_url": "/api/v1/documents/7/view",
                },
                aliases=["mca timetable", "sem 2 timetable", "lecture timetable", "class timetable", "timetable", "schedule"],
            )
        )
        self.add_edge("sem:mca_sem2", "HAS_TIMETABLE", "sched:mca_sem2_timetable")

        # 10. Exam Schedule Node
        self.add_node(
            KGNode(
                id="sched:mca_exam_pattern",
                type="ExamSchedule",
                name="MCA Autonomous Examination Pattern & Schedule",
                code="EXAM_SCHEME",
                properties={
                    "program": "MCA",
                    "evaluation_model": "Autonomous Continuous Assessment + ESE",
                    "components": {
                        "CA": "40 Marks (Continuous Assessment: Internal Quizzes, Assignments, Practical Performance, Class Attendance)",
                        "MSE": "20 Marks (Mid-Semester Examination conducted mid-term)",
                        "ESE": "60 Marks (End-Semester Autonomous Written Examination, 3 Hours Duration)",
                    },
                    "passing_criteria": "Minimum 40% aggregate in CA + MSE + ESE as per Autonomous Regulations.",
                    "document_id": 7,
                    "view_url": "/api/v1/documents/7/view",
                },
                aliases=["exam schedule", "exam timetable", "examination pattern", "exam dates", "mca exam schedule", "exam"],
            )
        )
        self.add_edge("prog:mca", "HAS_EXAM_SCHEDULE", "sched:mca_exam_pattern")

        # 11. Fee Structure Node
        self.add_node(
            KGNode(
                id="fee:mca_fra",
                type="FeeStructure",
                name="MCA Fee Structure (FRA Maharashtra Sanctioned)",
                code="FEE_MCA",
                properties={
                    "program": "MCA",
                    "academic_year": "2024-25 / 2025-26",
                    "tuition_fee": 81364,
                    "development_fee": 10136,
                    "total_annual_fee": 91500,
                    "total_program_fee": 183000,
                    "category_concessions": {
                        "Open": "₹91,500 / year",
                        "OBC / EBC / EWS": "50% Tuition Fee Concession (₹50,818 / year)",
                        "SC / ST / VJ-NT / SBC": "100% Tuition & Development Fee Waiver under Govt. Scholarship Schemes",
                    },
                    "source": "Fee Regulating Authority (FRA), Maharashtra State & JDCOEM Accounts Office",
                },
                aliases=["mca fee", "mca fees", "college fees", "tuition fee", "fee structure", "fees"],
            )
        )
        self.add_edge("prog:mca", "HAS_CREDITS", "fee:mca_fra")

    # -------------------------------------------------------------------------
    # Public Traversal & Retrieval Helpers
    # -------------------------------------------------------------------------
    def get_semester_overview(self, program: str = "MCA", semester: int = 2) -> Optional[Dict[str, Any]]:
        """Retrieve complete verified subjects and labs for a semester."""
        sem_id = f"sem:{program.lower()}_sem{semester}"
        sem_node = self.nodes.get(sem_id)
        if not sem_node:
            return None

        # Fetch all subjects
        outgoing = self.get_outgoing(sem_id, "CONTAINS_SUBJECT")
        subjects = [target for _, target in outgoing]

        theory = [s for s in subjects if not s.code.startswith("MC") or "T" in s.code or "E" in s.code or "A" in s.code]
        labs = [s for s in subjects if "L" in (s.code or "")]

        return {
            "semester_node": sem_node,
            "theory_subjects": theory,
            "lab_courses": labs,
            "total_credits": sem_node.properties.get("total_credits", 22),
            "total_marks": sem_node.properties.get("total_marks", 800),
            "document_id": sem_node.properties.get("document_id"),
            "document_filename": sem_node.properties.get("document_filename"),
            "view_url": f"/api/v1/documents/{sem_node.properties.get('document_id', 6)}/view",
        }

    def get_subject_node(self, subject_query: str) -> Optional[KGNode]:
        """Find a subject or lab node by alias or course code."""
        return self.find_node(subject_query)

    def get_subject_credits(self, subject_query: str) -> Optional[Dict[str, Any]]:
        """Retrieve strictly the credits and evaluation facts for a subject."""
        node = self.find_node(subject_query)
        if not node:
            return None
        props = node.properties
        return {
            "name": node.name,
            "code": node.code,
            "credits": props.get("credits"),
            "ltp": props.get("ltp"),
            "semester": props.get("semester"),
            "ca_marks": props.get("ca_marks"),
            "ese_marks": props.get("ese_marks"),
            "total_marks": props.get("total_marks"),
        }

    def get_timetable(self, semester: int = 2) -> Optional[KGNode]:
        """Retrieve class timetable node."""
        return self.nodes.get("sched:mca_sem2_timetable")

    def get_exam_schedule(self) -> Optional[KGNode]:
        """Retrieve exam schedule node."""
        return self.nodes.get("sched:mca_exam_pattern")

    def get_fee_structure(self, program: str = "MCA") -> Optional[KGNode]:
        """Retrieve fee structure node."""
        return self.nodes.get("fee:mca_fra")

    def get_document(self, doc_id: int) -> Optional[KGNode]:
        """Retrieve document node by DB document id."""
        for node in self.nodes.values():
            if node.type == "AcademicDocument" and node.properties.get("document_id") == doc_id:
                return node
        return None


# Global singleton Knowledge Graph instance
knowledge_graph = AcademicKnowledgeGraph()
