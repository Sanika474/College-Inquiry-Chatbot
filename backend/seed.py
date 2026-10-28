"""Database Seeding Script for CampusIQ — JD College of Engineering & Management (JDCOEM), Nagpur.

Populates PostgreSQL with authentic institutional data for JDCOEM with a specialized focus
on the Master of Computer Applications (MCA) department, its HOD Prof. Rohan Kokate,
faculty, fee structures (FRA sanctioned), TBI incubation, placements, and campus facilities.
"""

import sys
from app.core.security import get_password_hash
from app.db.session import SessionLocal
from app.models.college import (
    CollegeInfo,
    Course,
    CourseFee,
    Department,
    Facility,
    Faculty,
    KnowledgeDocument,
)
from app.models.user import User, UserRole

# Ensure clean UTF-8 console output on Windows
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def seed_database():
    """Seed authentic JDCOEM institutional data and baseline accounts."""
    db = SessionLocal()
    try:
        print("[SEED] Starting CampusIQ Database Seeding for JDCOEM, Nagpur...")

        # ---------------------------------------------------------------------
        # 1. Seed Core User Accounts
        # ---------------------------------------------------------------------
        admin_email = "admin@campusiq.edu"
        admin_user = db.query(User).filter(User.email == admin_email).first()
        if not admin_user:
            admin_user = User(
                full_name="CampusIQ Administrator",
                email=admin_email,
                hashed_password=get_password_hash("AdminCampusIQ@2025"),
                role=UserRole.ADMIN,
                is_active=True,
                is_verified=True,
            )
            db.add(admin_user)
            print("  [+] Created Master Admin: admin@campusiq.edu")

        legacy_admin_email = "masss@gmail.com"
        legacy_admin = db.query(User).filter(User.email == legacy_admin_email).first()
        if not legacy_admin:
            legacy_admin = User(
                full_name="Legacy Administrator",
                email=legacy_admin_email,
                hashed_password=get_password_hash("Pappupass"),
                role=UserRole.ADMIN,
                is_active=True,
                is_verified=True,
            )
            db.add(legacy_admin)
            print("  [+] Created Legacy Admin: masss@gmail.com")

        student_email = "student@campusiq.edu"
        student_user = db.query(User).filter(User.email == student_email).first()
        if not student_user:
            student_user = User(
                full_name="Shilpa Tayade",
                email=student_email,
                hashed_password=get_password_hash("StudentCampusIQ@2025"),
                role=UserRole.STUDENT,
                is_active=True,
                is_verified=True,
            )
            db.add(student_user)
            print("  [+] Created Student User: student@campusiq.edu")

        db.commit()

        # ---------------------------------------------------------------------
        # 2. Seed College Info: JD College of Engineering & Management (JDCOEM)
        # ---------------------------------------------------------------------
        info = db.query(CollegeInfo).first()
        if not info:
            info = CollegeInfo(
                name="JD College of Engineering and Management (JDCOEM), Nagpur",
                established_year=2008,
                affiliation="Dr. Babasaheb Ambedkar Technological University (DBATU), Lonere",
                accreditation="NAAC 'A' Grade Accredited, Autonomous Institute, AICTE Approved, DTE Code: 04138",
                campus_size="25+ Acres Green Campus at Khandala, Kalmeshwar Road, Nagpur",
                motto="Education to Eternity",
                address="Khandala/Valni, Near Hanuman Temple, Borgaon Fata, Kalmeshwar Road, Nagpur, Maharashtra — 441501",
                contact_email="info@jdcoem.ac.in",
                contact_phone="+91-90110 10038 / +91-7774041329",
                website="https://jdcoem.ac.in",
            )
            db.add(info)
        else:
            info.name = "JD College of Engineering and Management (JDCOEM), Nagpur"
            info.established_year = 2008
            info.affiliation = "Dr. Babasaheb Ambedkar Technological University (DBATU), Lonere"
            info.accreditation = "NAAC 'A' Grade Accredited, Autonomous Institute, AICTE Approved, DTE Code: 04138"
            info.campus_size = "25+ Acres Green Campus at Khandala, Kalmeshwar Road, Nagpur"
            info.motto = "Education to Eternity"
            info.address = "Khandala/Valni, Near Hanuman Temple, Borgaon Fata, Kalmeshwar Road, Nagpur, Maharashtra — 441501"
            info.contact_email = "info@jdcoem.ac.in"
            info.contact_phone = "+91-90110 10038 / +91-7774041329"
            info.website = "https://jdcoem.ac.in"
        db.commit()
        print("  [+] Seeded College Information: JDCOEM, Nagpur (DTE: 04138)")

        # ---------------------------------------------------------------------
        # 3. Seed Departments (MCA Highlighted)
        # ---------------------------------------------------------------------
        dept_data = [
            ("Master of Computer Applications", "MCA", "Prof. Rohan Kokate", "Postgraduate department specializing in advanced software development, cloud computing, AI/ML, and startup incubation at TBI."),
            ("Computer Science & Engineering", "CSE", "Dr. Nilesh Sambhe", "Department of Computer Science & Engineering covering core computing, algorithms, and systems engineering."),
            ("Artificial Intelligence & Data Science", "AIDS", "Dr. S. R. Sharma", "Specialized department in machine learning, deep neural networks, and big data analytics."),
            ("Information Technology", "IT", "Prof. A. V. Patil", "Department of Information Technology focused on full-stack web, cyber security, and enterprise infrastructure."),
            ("Electronics & Telecommunication", "ETC", "Dr. M. S. Wanjari", "VLSI design, embedded systems, IoT architecture, and wireless communication."),
            ("Management Studies", "MBA", "Dr. Swati Rahate", "Department of Management Studies offering dual-specialization in Finance, Marketing, HR, and Business Analytics."),
            ("Applied Sciences & Humanities", "ASH", "Dr. V. K. Tadas", "First year foundation sciences, engineering mathematics, and professional ethics."),
        ]

        depts = {}
        for name, code, hod, desc in dept_data:
            dept = db.query(Department).filter(Department.code == code).first()
            if not dept:
                dept = Department(name=name, code=code, hod_name=hod, description=desc)
                db.add(dept)
                db.flush()
                print(f"  [+] Created Department: {name} ({code})")
            else:
                dept.name = name
                dept.hod_name = hod
                dept.description = desc
                db.flush()
            depts[code] = dept
        db.commit()

        # ---------------------------------------------------------------------
        # 4. Seed Academic Courses
        # ---------------------------------------------------------------------
        course_data = [
            # (dept_code, code, name, level, duration, eligibility, intake, desc)
            (
                "MCA",
                "MCA",
                "Master of Computer Applications",
                "PG",
                2,
                "Passed BCA / B.Sc.(CS/IT) or Bachelor Degree with Mathematics at 10+2 or Graduate level with minimum 50% marks (45% for Maharashtra reserved categories). Valid MAH-MCA-CET score.",
                120,
                "Premier 2-year autonomous postgraduate program featuring Cloud Computing, Full-Stack Development, AI/ML, and capstone software project with incubation support.",
            ),
            (
                "CSE",
                "BTECH_CSE",
                "B.Tech (Computer Science & Engineering)",
                "UG",
                4,
                "Passed HSC (12th Science) with Physics & Mathematics plus Chemistry/CS with minimum 45% marks (40% reserved). Valid MHT-CET or JEE Main score.",
                180,
                "Comprehensive autonomous engineering program covering distributed systems, web architectures, cybersecurity, and algorithmic design.",
            ),
            (
                "AIDS",
                "BTECH_AI",
                "B.Tech (Artificial Intelligence)",
                "UG",
                4,
                "Passed HSC (12th Science) PCM with minimum 45% marks. Valid MHT-CET / JEE Main.",
                120,
                "Cutting-edge program focusing on deep learning, generative AI, natural language processing, and computer vision.",
            ),
            (
                "AIDS",
                "BTECH_DS",
                "B.Tech (Data Science)",
                "UG",
                4,
                "Passed HSC (12th Science) PCM with minimum 45% marks. Valid MHT-CET / JEE Main.",
                60,
                "Big data pipelines, statistical modeling, data warehousing, and business intelligence.",
            ),
            (
                "IT",
                "BTECH_IT",
                "B.Tech (Information Technology)",
                "UG",
                4,
                "Passed HSC (12th Science) PCM with minimum 45% marks. Valid MHT-CET / JEE Main.",
                60,
                "Enterprise software engineering, cloud architecture, and network security systems.",
            ),
            (
                "MBA",
                "MBA",
                "Master of Business Administration",
                "PG",
                2,
                "Bachelor Degree of minimum 3 years duration with at least 50% marks (45% reserved). Valid MAH-MBA-CET / CAT / CMAT score.",
                60,
                "Industry-ready autonomous MBA program in Finance, Marketing, Human Resources, and Business Analytics.",
            ),
            (
                "CSE",
                "MTECH_CSE",
                "M.Tech (Computer Science & Engineering)",
                "PG",
                2,
                "Passed B.E. / B.Tech in CSE / IT with minimum 50% marks. Valid GATE score.",
                24,
                "Advanced research in parallel computing, neural networks, and cryptography.",
            ),
        ]

        courses = {}
        for dept_code, c_code, c_name, level, duration, elig, intake, desc in course_data:
            course = db.query(Course).filter(Course.code == c_code).first()
            if not course:
                course = Course(
                    department_id=depts[dept_code].id,
                    name=c_name,
                    code=c_code,
                    level=level,
                    duration_years=duration,
                    eligibility=elig,
                    intake_capacity=intake,
                    description=desc,
                )
                db.add(course)
                db.flush()
                print(f"  [+] Created Course: {c_name} ({c_code})")
            else:
                course.name = c_name
                course.level = level
                course.duration_years = duration
                course.eligibility = elig
                course.intake_capacity = intake
                course.description = desc
                db.flush()
            courses[c_code] = course
        db.commit()

        # ---------------------------------------------------------------------
        # 5. Seed Course Fees (FRA Sanctioned Schedules)
        # ---------------------------------------------------------------------
        fee_data = [
            # (course_code, acad_yr, yr_study, tuition, dev, lab/exam, other, total, notes)
            ("MCA", "2024-25", 1, 78000.0, 10000.0, 2000.0, 1500.0, 91500.0, "MCA 1st Year (FRA Sanctioned Tuition & Development Fee)"),
            ("MCA", "2024-25", 2, 78000.0, 10000.0, 2000.0, 1500.0, 91500.0, "MCA 2nd Year (FRA Sanctioned Tuition & Development Fee)"),
            ("BTECH_CSE", "2024-25", 1, 85000.0, 11000.0, 2500.0, 1500.0, 100000.0, "B.Tech CSE 1st Year Fee"),
            ("BTECH_CSE", "2024-25", 2, 85000.0, 11000.0, 2500.0, 1500.0, 100000.0, "B.Tech CSE 2nd Year Fee"),
            ("BTECH_AI", "2024-25", 1, 85000.0, 11000.0, 2500.0, 1500.0, 100000.0, "B.Tech AI 1st Year Fee"),
            ("MBA", "2024-25", 1, 75000.0, 9000.0, 2000.0, 1500.0, 87500.0, "MBA 1st Year Annual Fee"),
            ("MBA", "2024-25", 2, 75000.0, 9000.0, 2000.0, 1500.0, 87500.0, "MBA 2nd Year Annual Fee"),
        ]

        for c_code, acad_yr, yr_study, tuition, dev, lab, other, total, notes in fee_data:
            if c_code in courses:
                fee = db.query(CourseFee).filter(
                    CourseFee.course_id == courses[c_code].id,
                    CourseFee.academic_year == acad_yr,
                    CourseFee.year_of_study == yr_study,
                ).first()
                if not fee:
                    fee = CourseFee(
                        course_id=courses[c_code].id,
                        academic_year=acad_yr,
                        year_of_study=yr_study,
                        tuition_fee=tuition,
                        development_fee=dev,
                        lab_fee=lab,
                        other_fee=other,
                        total_fee=total,
                        notes=notes,
                    )
                    db.add(fee)
                    print(f"  [+] Added Fee: {c_code} Year {yr_study} -> ₹{total}")
                else:
                    fee.tuition_fee = tuition
                    fee.development_fee = dev
                    fee.lab_fee = lab
                    fee.other_fee = other
                    fee.total_fee = total
                    fee.notes = notes
        db.commit()

        # ---------------------------------------------------------------------
        # 6. Seed Faculty Members (MCA Department Front and Center)
        # ---------------------------------------------------------------------
        faculty_data = [
            ("ASH", "Dr. Shrikant V. Sonekar", "Principal & Director", "Ph.D. Electronics, M.Tech", 25, "Electronics, Embedded Systems & Autonomous Institutional Leadership", "principal@jdcoem.ac.in", "+91-90110 10038"),
            ("MCA", "Prof. Rohan Kokate", "Associate Professor & HOD (MCA)", "M.C.A., Ph.D. (Pursuing)", 15, "Full-Stack Web Architectures, Database Systems, Cloud Computing", "rohan.kokate@jdcoem.ac.in", "+91-90110 81548"),
            ("MCA", "Prof. Chetan Padole", "Assistant Professor & Project Coordinator (MCA)", "M.C.A., M.Tech (CSE)", 11, "Machine Learning, Python Programming, Mobile Computing & TBI Mentor", "chetan.padole@jdcoem.ac.in", None),
            ("MCA", "Prof. Sneha Sahare", "Assistant Professor (MCA)", "M.C.A.", 8, "Software Engineering, Object-Oriented Java, Cyber Security", "sneha.sahare@jdcoem.ac.in", None),
            ("MCA", "Prof. Pranay Meshram", "Assistant Professor (MCA)", "M.C.A.", 7, "Cloud Infrastructure, Data Structures, Web Frameworks", "pranay.meshram@jdcoem.ac.in", None),
            ("CSE", "Dr. Nilesh Sambhe", "Professor & HOD (CSE)", "Ph.D. Computer Science", 20, "Distributed Systems, Network Security & AI", "nilesh.sambhe@jdcoem.ac.in", None),
            ("MBA", "Dr. Swati Rahate", "Professor & HOD (MBA)", "Ph.D. Management, MBA", 18, "Strategic Management, Corporate Finance, Human Resources", "swati.rahate@jdcoem.ac.in", None),
        ]

        for dept_code, f_name, desig, qual, exp, spec, email, phone in faculty_data:
            fac = db.query(Faculty).filter(Faculty.name == f_name).first()
            if not fac:
                fac = Faculty(
                    department_id=depts[dept_code].id,
                    name=f_name,
                    designation=desig,
                    qualification=qual,
                    experience_years=exp,
                    specialization=spec,
                    email=email,
                    phone=phone,
                )
                db.add(fac)
                print(f"  [+] Created Faculty: {f_name} ({desig})")
            else:
                fac.department_id = depts[dept_code].id
                fac.designation = desig
                fac.qualification = qual
                fac.experience_years = exp
                fac.specialization = spec
                fac.email = email
                fac.phone = phone
        db.commit()

        # ---------------------------------------------------------------------
        # 7. Seed Campus Facilities & Infrastructure
        # ---------------------------------------------------------------------
        facilities_data = [
            ("Technology Business Incubator (TBI)", "Incubation", "Autonomous startup and innovation incubator on campus fostering student IT ventures, product development, patent filing, and seed capital mentoring.", "Located in the Tech Innovation Wing; actively supports MCA software project commercialization."),
            ("Central Library", "Library", "Automated digital and physical library holding 30,000+ technical volumes, national/international journals, IEEE Xplore, DELNET, and e-book repositories.", "Open Monday to Saturday, 8:00 AM to 7:00 PM with quiet reading rooms."),
            ("High-Performance Computing & AI Labs", "Laboratory", "Air-conditioned laboratories equipped with GPU nodes, high-speed leased line internet, and full-stack development software for MCA & Engineering research.", "Open during academic hours with uninterrupted power backup and cloud sandboxes."),
            ("Campus Hostels (Boys & Girls)", "Hostel", "Safe residential accommodations located on campus with 24/7 biometric security, CCTV, Wi-Fi connectivity, and hygienic mess dining.", "Allotment via merit and distance; lodging + mess approx. ₹3,500/month."),
            ("Fleet Bus Transportation", "Transport", "Dedicated fleet of college buses connecting all major nodes of Nagpur city (Sitabuldi, Dharampeth, Sadar, Wardha Road, Wadi, Trimurti Nagar, Katol, Kalmeshwar).", "Daily scheduled pickup and drop; GPS-tracked student transit."),
            ("Sports & Cultural Complex", "Sports", "Comprehensive sports infrastructure supporting cricket turf, football ground, basketball court, badminton, gymnasium, and annual national fest Jalsa.", "Encourages student fitness and university tournament representation."),
            ("Campus Cafeteria", "Canteen", "Spacious and hygienic cafeteria offering fresh meals, beverages, and student snacks throughout college working hours.", "Located adjacent to the central quadrangle."),
        ]

        for name, cat, desc, details in facilities_data:
            facil = db.query(Facility).filter(Facility.name == name).first()
            if not facil:
                facil = Facility(name=name, category=cat, description=desc, details=details)
                db.add(facil)
                print(f"  [+] Created Facility: {name}")
            else:
                facil.category = cat
                facil.description = desc
                facil.details = details
        db.commit()

        # ---------------------------------------------------------------------
        # 8. Seed Knowledge Documents (Policies, CAP, Attendance, Placements)
        # ---------------------------------------------------------------------
        docs_data = [
            (
                "MCA Admission & DTE CAP Guidelines",
                "admission",
                "Admissions to the Master of Computer Applications (MCA) at JDCOEM (DTE Code: 04138) are conducted through the Centralized Admission Process (CAP) governed by the State CET Cell, Government of Maharashtra. Candidates must possess a valid MAH-MCA-CET score. Reserved category candidates (SC/ST/VJNT/OBC/EBC) are entitled to state government scholarship concessions.",
                "DTE Maharashtra CAP Brochure & State CET Cell 2024",
            ),
            (
                "Mandatory 75% Attendance Regulation",
                "attendance",
                "As per DBATU and JDCOEM Autonomous Academic Regulations, a minimum of 75% attendance in theory lectures and practical laboratory sessions is strictly mandatory. Students falling short of 75% attendance without verified medical clearance are debarred from appearing in end-semester examinations.",
                "JDCOEM Autonomous Academic Regulations, Rule 6.1",
            ),
            (
                "MCA Capstone Project & TBI Incubation",
                "mca_project",
                "Final-year MCA students are required to develop real-world industry capstone projects in areas such as Cloud Computing, AI/Machine Learning, Full-Stack Web Applications, or Mobile Systems. High-performing student software projects receive pre-incubation support, workspace, and mentorship at the campus Technology Business Incubator (TBI).",
                "Department of MCA Project Guidelines & TBI Charter",
            ),
            (
                "Training & Placement (T&P) Highlights",
                "placements",
                "JDCOEM operates an active Centralized Training & Placement Cell offering aptitude training, mock interviews, and coding hackathons. Top recruiters include TCS, Infosys, Wipro, Capgemini, Cognizant, Tech Mahindra, L&T Infotech, Hexaware, and Persistent Systems. Highest CTC reached 12+ LPA with an average package of 4.5 LPA.",
                "Central Placement Cell Report 2024-25",
            ),
            (
                "Anti-Ragging Zero Tolerance Policy",
                "general",
                "Ragging in any form within the college campus, hostel, or transport buses is strictly banned under the Maharashtra Prohibition of Ragging Act and AICTE Anti-Ragging regulations. Any violation results in immediate FIR registration, suspension, and rustication.",
                "Anti-Ragging Committee Charter & AICTE Norms",
            ),
            (
                "Bus Transport Routes & Connectivity",
                "transport",
                "JDCOEM operates a fleet of over 20 GPS-enabled college buses covering Nagpur City routes including Sitabuldi, Dharampeth, Manewada, Trimurti Nagar, Sadar, Wadi, Katol, and Kalmeshwar, ensuring safe and punctual transit for students and faculty.",
                "Transport Department Route Schedule",
            ),
        ]

        for title, cat, content, src in docs_data:
            doc = db.query(KnowledgeDocument).filter(KnowledgeDocument.title == title).first()
            if not doc:
                doc = KnowledgeDocument(title=title, category=cat, content=content, source_reference=src)
                db.add(doc)
                print(f"  [+] Created Knowledge Doc: {title}")
            else:
                doc.category = cat
                doc.content = content
                doc.source_reference = src
        db.commit()

        print("[SUCCESS] CampusIQ database populated with JDCOEM & MCA institutional records!")

    except Exception as e:
        db.rollback()
        print(f"[ERROR] Database seeding failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
