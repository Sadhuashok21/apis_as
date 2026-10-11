import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "apis.settings")
django.setup()

from skiltrix.models import (
    CodingAssessment,
    AssessmentSection,
    AssessmentQuestionItem,
    AssessmentQuestion,
    CodingProblems,
    CompanyBlueprint,
)


def seed_company_mocks():
    print("Seeding Company Mock Assessments & Blueprints...")

    # 1. SEED COMPANY BLUEPRINTS
    blueprints_data = [
        {
            "blueprint_id": "bp_amazon_sde",
            "company_name": "Amazon-style SDE Mock",
            "slug": "amazon-style-sde",
            "description": "Inspired by Amazon SDE hiring rounds testing dynamic programming, min-heaps, scalable data structures, system debugging, and algorithmic efficiency.",
            "category": "Company Mocks",
            "tier": "free",
            "duration_minutes": 90,
            "recommended_topics": ["Graphs", "Dynamic Programming", "Min-Heap", "System Debugging"],
            "sections_config": [
                {"title": "CS Fundamentals", "type": "technical", "count": 5, "marks": 10},
                {"title": "Debugging Round", "type": "debugging", "count": 2, "marks": 20},
                {"title": "Core DSA & Coding", "type": "coding", "count": 2, "marks": 70},
            ]
        },
        {
            "blueprint_id": "bp_deloitte_placement",
            "company_name": "Deloitte-style Placement Mock",
            "slug": "deloitte-style-placement",
            "description": "Simulates Deloitte hiring tests featuring quantitative aptitude, logical deduction, relational SQL queries, and fundamental coding.",
            "category": "Mixed Placement Assessments",
            "tier": "free",
            "duration_minutes": 75,
            "recommended_topics": ["Quantitative Aptitude", "Logical Reasoning", "SQL Queries", "Coding"],
            "sections_config": [
                {"title": "Quantitative Aptitude", "type": "aptitude", "count": 5, "marks": 20},
                {"title": "Logical Reasoning", "type": "reasoning", "count": 5, "marks": 20},
                {"title": "SQL & Databases", "type": "sql", "count": 2, "marks": 20},
                {"title": "Hands-on Programming", "type": "coding", "count": 1, "marks": 40},
            ]
        },
        {
            "blueprint_id": "bp_accenture_coding",
            "company_name": "Accenture-style Coding Mock",
            "slug": "accenture-style-coding",
            "description": "Designed around Accenture recruitment structure testing cognitive critical reasoning, technical pseudocode, and hands-on algorithms.",
            "category": "Company Mocks",
            "tier": "free",
            "duration_minutes": 90,
            "recommended_topics": ["Critical Reasoning", "Abstract Thinking", "Core Coding", "Debugging"],
            "sections_config": [
                {"title": "Critical Reasoning", "type": "reasoning", "count": 5, "marks": 25},
                {"title": "Technical MCQ & Pseudocode", "type": "technical", "count": 5, "marks": 25},
                {"title": "Coding Assessment", "type": "coding", "count": 2, "marks": 50},
            ]
        },
        {
            "blueprint_id": "bp_tcs_placement",
            "company_name": "TCS-style Placement Mock",
            "slug": "tcs-style-placement",
            "description": "Replicates TCS NQT exam format with strict sectional discipline covering numerical ability, reasoning ability, and algorithmic programming.",
            "category": "Mixed Placement Assessments",
            "tier": "free",
            "duration_minutes": 90,
            "recommended_topics": ["Numerical Ability", "Reasoning Ability", "Hands-on Coding", "SQL"],
            "sections_config": [
                {"title": "Numerical Ability", "type": "aptitude", "count": 5, "marks": 25},
                {"title": "Reasoning Ability", "type": "reasoning", "count": 5, "marks": 25},
                {"title": "Hands-on Coding", "type": "coding", "count": 2, "marks": 50},
            ]
        },
        {
            "blueprint_id": "bp_infosys_placement",
            "company_name": "Infosys-style Placement Mock",
            "slug": "infosys-style-placement",
            "description": "Modeled after Infosys hiring evaluations testing mathematical reasoning, pseudocode analysis, and two-tier coding challenges.",
            "category": "Company Mocks",
            "tier": "pro",
            "duration_minutes": 100,
            "recommended_topics": ["Mathematical Abilities", "Pseudocode", "DSA", "Problem Solving"],
            "sections_config": [
                {"title": "Mathematical Abilities", "type": "aptitude", "count": 5, "marks": 20},
                {"title": "Pseudocode Analysis", "type": "technical", "count": 5, "marks": 20},
                {"title": "Hands-on Coding Round", "type": "coding", "count": 2, "marks": 60},
            ]
        },
        {
            "blueprint_id": "bp_cognizant_placement",
            "company_name": "Cognizant-style Placement Mock",
            "slug": "cognizant-style-placement",
            "description": "GenC Next inspired pattern focusing on advanced data interpretation, analytical deduction, and complex algorithm optimization.",
            "category": "Company Mocks",
            "tier": "pro",
            "duration_minutes": 80,
            "recommended_topics": ["Verbal Ability", "Data Interpretation", "CS Basics", "Coding"],
            "sections_config": [
                {"title": "Quantitative & Analytical", "type": "aptitude", "count": 5, "marks": 25},
                {"title": "CS Fundamentals", "type": "technical", "count": 5, "marks": 25},
                {"title": "Coding Challenge", "type": "coding", "count": 1, "marks": 50},
            ]
        },
        {
            "blueprint_id": "bp_wipro_placement",
            "company_name": "Wipro-style Placement Mock",
            "slug": "wipro-style-placement",
            "description": "Modeled after Wipro Elite NLTH testing logical and quantitative foundations paired with hands-on code development.",
            "category": "Company Mocks",
            "tier": "pro",
            "duration_minutes": 80,
            "recommended_topics": ["Quantitative", "Logical", "Basic Programming", "Essay/Comprehension"],
            "sections_config": [
                {"title": "Quantitative Aptitude", "type": "aptitude", "count": 5, "marks": 30},
                {"title": "Logical Reasoning", "type": "reasoning", "count": 5, "marks": 30},
                {"title": "Programming & Coding", "type": "coding", "count": 1, "marks": 40},
            ]
        },
        {
            "blueprint_id": "bp_capgemini_placement",
            "company_name": "Capgemini-style Placement Mock",
            "slug": "capgemini-style-placement",
            "description": "Simulates Capgemini Exceller recruitment with pseudocode comprehension, logical reasoning, and clean coding standards.",
            "category": "Company Mocks",
            "tier": "pro",
            "duration_minutes": 90,
            "recommended_topics": ["Pseudocode", "English Communication", "Game-Based Aptitude", "Coding"],
            "sections_config": [
                {"title": "Pseudocode Challenge", "type": "technical", "count": 5, "marks": 30},
                {"title": "Logical Reasoning", "type": "reasoning", "count": 5, "marks": 30},
                {"title": "Coding Test", "type": "coding", "count": 1, "marks": 40},
            ]
        },
        {
            "blueprint_id": "bp_microsoft_placement",
            "company_name": "Microsoft-style Placement Mock",
            "slug": "microsoft-style-placement",
            "description": "High-rigor software engineering mock assessing binary search, interval management, dynamic trees, and low-latency database queries.",
            "category": "Coding Assessments",
            "tier": "pro",
            "duration_minutes": 90,
            "recommended_topics": ["Trees & Graphs", "Intervals", "Concurrency", "High-Scale SQL"],
            "sections_config": [
                {"title": "CS Fundamentals & OS", "type": "technical", "count": 4, "marks": 20},
                {"title": "Advanced Algorithmic Round", "type": "coding", "count": 2, "marks": 80},
            ]
        },
        {
            "blueprint_id": "bp_google_placement",
            "company_name": "Google-style Placement Mock",
            "slug": "google-style-placement",
            "description": "Advanced algorithmic problem-solving mock testing complex state transformations, greedy optimization, and boundary stress testing.",
            "category": "DSA Assessments",
            "tier": "pro",
            "duration_minutes": 105,
            "recommended_topics": ["Advanced Dynamic Programming", "Combinatorics", "Graph Theory", "Optimization"],
            "sections_config": [
                {"title": "Algorithmic Problem Solving", "type": "coding", "count": 2, "marks": 100},
            ]
        },
        {
            "blueprint_id": "bp_general_sde",
            "company_name": "General SDE Assessment",
            "slug": "general-sde-assessment",
            "description": "Comprehensive full-stack software engineer benchmark test covering data structures, backend Django debugging, and relational SQL queries.",
            "category": "Mixed Placement Assessments",
            "tier": "free",
            "duration_minutes": 90,
            "recommended_topics": ["Arrays & Strings", "Hash Maps", "Two Pointers", "Backend Debugging"],
            "sections_config": [
                {"title": "CS Fundamentals", "type": "technical", "count": 5, "marks": 20},
                {"title": "Backend Debugging", "type": "debugging", "count": 1, "marks": 30},
                {"title": "Core Coding", "type": "coding", "count": 1, "marks": 50},
            ]
        },
    ]

    for bp in blueprints_data:
        CompanyBlueprint.objects.update_or_create(
            blueprint_id=bp["blueprint_id"],
            defaults={
                "company_name": bp["company_name"],
                "slug": bp["slug"],
                "description": bp["description"],
                "category": bp["category"],
                "sections_config": bp["sections_config"],
                "recommended_topics": bp["recommended_topics"],
                "duration_minutes": bp["duration_minutes"],
                "tier": bp["tier"],
                "is_active": True,
            }
        )
    print("Seeded 11 Company Blueprints.")

    # 2. SEED COMPLETE COMPANY MOCK ASSESSMENTS WITH SECTIONS & QUESTIONS
    # We will seed 3 rich multi-section Company Mocks:
    # A) Amazon-style SDE Mock
    # B) Deloitte-style Placement Mock
    # C) TCS-style Placement Mock

    # Existing Coding Problems to attach
    prob_stream = CodingProblems.objects.filter(problem_id="prob_stream_first_unique").first()
    prob_pack = CodingProblems.objects.filter(problem_id="prob_warehouse_packing").first()
    prob_velocity = CodingProblems.objects.filter(problem_id="prob_order_velocity").first()
    prob_server = CodingProblems.objects.filter(problem_id="prob_cloud_job_servers").first()
    prob_drf = CodingProblems.objects.filter(problem_id="prob_drf_many_true").first()
    prob_sql = CodingProblems.objects.filter(problem_id="prob_sql_left_join").first()

    # -------------------------------------------------------------
    # MOCK 1: Amazon-style SDE Mock
    # -------------------------------------------------------------
    asmt_amazon, _ = CodingAssessment.objects.update_or_create(
        assessment_id="asmt_amazon_sde1",
        defaults={
            "title": "Amazon-style SDE Technical Mock",
            "slug": "amazon-style-sde-mock",
            "company_tag": "Amazon-style",
            "category": "Company Mocks",
            "description": "Multi-section assessment inspired by Amazon SDE technical evaluations. Features CS Fundamentals, Backend Debugging, and Algorithmic Coding under strict server-side proctoring.",
            "difficulty": "Hard",
            "duration_minutes": 90,
            "total_marks": 100.0,
            "pass_percentage": 70,
            "negative_marking_percentage": 0.25,
            "is_company_mock": True,
            "is_pro_only": False,
            "proctoring_enabled": True,
            "require_fullscreen": True,
            "require_screen_share": True,
            "max_tab_switches": 3,
            "max_fullscreen_exits": 3,
            "allow_return_to_previous": True,
            "auto_submit_on_violations": False,
            "randomize_questions": False,
            "active": True,
        }
    )

    # Sections for Amazon
    sec_amz_cs, _ = AssessmentSection.objects.update_or_create(
        section_id="sec_amz_cs",
        defaults={
            "assessment": asmt_amazon,
            "title": "Section 1: CS Fundamentals",
            "section_type": "technical",
            "order": 1,
            "instructions": "Answer the multiple choice questions below. Negative marking of 0.25 applies for incorrect answers.",
            "total_marks": 20.0,
        }
    )
    sec_amz_debug, _ = AssessmentSection.objects.update_or_create(
        section_id="sec_amz_debug",
        defaults={
            "assessment": asmt_amazon,
            "title": "Section 2: Backend & System Debugging",
            "section_type": "debugging",
            "order": 2,
            "instructions": "Identify and fix the root causes in the provided backend production error snippet.",
            "total_marks": 30.0,
        }
    )
    sec_amz_code, _ = AssessmentSection.objects.update_or_create(
        section_id="sec_amz_code",
        defaults={
            "assessment": asmt_amazon,
            "title": "Section 3: Core DSA & Algorithms",
            "section_type": "coding",
            "order": 3,
            "instructions": "Solve the algorithmic challenges within time and space constraints.",
            "total_marks": 50.0,
        }
    )

    # Questions for Section 1 (CS Fundamentals)
    AssessmentQuestionItem.objects.update_or_create(
        item_id="item_amz_q1",
        defaults={
            "assessment": asmt_amazon,
            "section": sec_amz_cs,
            "question_type": "mcq_single",
            "title": "TCP 3-Way Handshake Termination Flag",
            "prompt": "During the standard termination of a TCP connection, which flag is transmitted by the initiating endpoint to signify that no more data will be sent?",
            "options": [
                {"id": "A", "text": "RST (Reset)"},
                {"id": "B", "text": "FIN (Finish)"},
                {"id": "C", "text": "SYN (Synchronize)"},
                {"id": "D", "text": "URG (Urgent)"},
            ],
            "correct_answers": ["B"],
            "explanation": "The FIN flag is sent to gracefully initiate termination of a TCP connection after transmitting remaining payloads.",
            "order": 1,
            "marks": 10.0,
            "negative_marks": 2.5,
        }
    )
    AssessmentQuestionItem.objects.update_or_create(
        item_id="item_amz_q2",
        defaults={
            "assessment": asmt_amazon,
            "section": sec_amz_cs,
            "question_type": "mcq_single",
            "title": "DBMS ACID Isolation Levels",
            "prompt": "Which SQL transaction isolation level prevents 'Dirty Reads' and 'Non-repeatable Reads' but permits 'Phantom Reads'?",
            "options": [
                {"id": "A", "text": "Read Uncommitted"},
                {"id": "B", "text": "Read Committed"},
                {"id": "C", "text": "Repeatable Read"},
                {"id": "D", "text": "Serializable"},
            ],
            "correct_answers": ["C"],
            "explanation": "Repeatable Read locks all selected rows across the transaction lifecycle, preventing dirty and non-repeatable reads, while new rows inserted by other transactions (phantom reads) may still appear.",
            "order": 2,
            "marks": 10.0,
            "negative_marks": 2.5,
        }
    )

    # Question for Section 2 (Backend Debugging)
    if prob_drf:
        AssessmentQuestionItem.objects.update_or_create(
            item_id="item_amz_q3",
            defaults={
                "assessment": asmt_amazon,
                "section": sec_amz_debug,
                "problem": prob_drf,
                "question_type": "debugging",
                "title": "Fix DRF List Serializer Crash",
                "prompt": prob_drf.description,
                "order": 3,
                "marks": 30.0,
                "negative_marks": 0.0,
            }
        )

    # Question for Section 3 (Coding)
    if prob_stream:
        AssessmentQuestionItem.objects.update_or_create(
            item_id="item_amz_q4",
            defaults={
                "assessment": asmt_amazon,
                "section": sec_amz_code,
                "problem": prob_stream,
                "question_type": "coding",
                "title": "Stream First Non-Repeating Character",
                "prompt": prob_stream.description,
                "order": 4,
                "marks": 50.0,
                "negative_marks": 0.0,
            }
        )

    # -------------------------------------------------------------
    # MOCK 2: Deloitte-style Placement Mock
    # -------------------------------------------------------------
    asmt_deloitte, _ = CodingAssessment.objects.update_or_create(
        assessment_id="asmt_deloitte_placement",
        defaults={
            "title": "Deloitte-style Placement Mock",
            "slug": "deloitte-style-placement-mock",
            "company_tag": "Deloitte-style",
            "category": "Mixed Placement Assessments",
            "description": "Placement mock inspired by Deloitte campus recruitment tests covering Quantitative Aptitude, Logical Reasoning, and Practical Database & Code rounds.",
            "difficulty": "Medium",
            "duration_minutes": 75,
            "total_marks": 100.0,
            "pass_percentage": 65,
            "negative_marking_percentage": 0.25,
            "is_company_mock": True,
            "is_pro_only": False,
            "proctoring_enabled": True,
            "require_fullscreen": True,
            "require_screen_share": True,
            "max_tab_switches": 3,
            "max_fullscreen_exits": 3,
            "active": True,
        }
    )

    sec_del_apt, _ = AssessmentSection.objects.update_or_create(
        section_id="sec_del_apt",
        defaults={
            "assessment": asmt_deloitte,
            "title": "Section 1: Quantitative Aptitude",
            "section_type": "aptitude",
            "order": 1,
            "total_marks": 30.0,
        }
    )
    sec_del_logic, _ = AssessmentSection.objects.update_or_create(
        section_id="sec_del_logic",
        defaults={
            "assessment": asmt_deloitte,
            "title": "Section 2: Logical Reasoning",
            "section_type": "reasoning",
            "order": 2,
            "total_marks": 30.0,
        }
    )
    sec_del_code, _ = AssessmentSection.objects.update_or_create(
        section_id="sec_del_code",
        defaults={
            "assessment": asmt_deloitte,
            "title": "Section 3: Practical Coding",
            "section_type": "coding",
            "order": 3,
            "total_marks": 40.0,
        }
    )

    # Aptitude Question
    AssessmentQuestionItem.objects.update_or_create(
        item_id="item_del_q1",
        defaults={
            "assessment": asmt_deloitte,
            "section": sec_del_apt,
            "question_type": "mcq_single",
            "title": "Time and Work Efficiency",
            "prompt": "Worker A can complete an operational audit in 12 days, while Worker B can complete the same audit in 18 days. If they collaborate together for 4 days, what fraction of the audit remains unfinished?",
            "options": [
                {"id": "A", "text": "4/9"},
                {"id": "B", "text": "5/9"},
                {"id": "C", "text": "2/3"},
                {"id": "D", "text": "1/3"},
            ],
            "correct_answers": ["A"],
            "explanation": "Rate per day = 1/12 + 1/18 = (3+2)/36 = 5/36. In 4 days, work completed = 4 * (5/36) = 20/36 = 5/9. Unfinished fraction = 1 - 5/9 = 4/9.",
            "order": 1,
            "marks": 15.0,
            "negative_marks": 3.75,
        }
    )
    AssessmentQuestionItem.objects.update_or_create(
        item_id="item_del_q2",
        defaults={
            "assessment": asmt_deloitte,
            "section": sec_del_apt,
            "question_type": "numerical",
            "title": "Compound Ratio Calculation",
            "prompt": "In an enterprise supply chain, two warehouses stock inventory in the ratio 7 : 5. If 15 units are moved from the first to the second warehouse, the new ratio becomes 1 : 1. Enter the total combined inventory across both warehouses.",
            "options": [],
            "correct_answers": ["180"],
            "explanation": "Let inventories be 7x and 5x. 7x - 15 = 5x + 15 => 2x = 30 => x = 15. Total inventory = 12x = 12 * 15 = 180.",
            "order": 2,
            "marks": 15.0,
            "negative_marks": 0.0,
        }
    )

    # Logical Reasoning Question
    AssessmentQuestionItem.objects.update_or_create(
        item_id="item_del_q3",
        defaults={
            "assessment": asmt_deloitte,
            "section": sec_del_logic,
            "question_type": "mcq_single",
            "title": "Sequence Pattern Deduction",
            "prompt": "Find the next token in the hexadecimal memory offset sequence: 0x1B, 0x36, 0x6C, 0xD8, ?",
            "options": [
                {"id": "A", "text": "0x1B0"},
                {"id": "B", "text": "0x2B0"},
                {"id": "C", "text": "0x1A0"},
                {"id": "D", "text": "0x2A8"},
            ],
            "correct_answers": ["A"],
            "explanation": "Each token doubles the previous value (shifted left 1 bit): 27 * 2 = 54 (0x36), 54 * 2 = 108 (0x6C), 108 * 2 = 216 (0xD8), 216 * 2 = 432 (0x1B0).",
            "order": 3,
            "marks": 30.0,
            "negative_marks": 7.5,
        }
    )

    if prob_pack:
        AssessmentQuestionItem.objects.update_or_create(
            item_id="item_del_q4",
            defaults={
                "assessment": asmt_deloitte,
                "section": sec_del_code,
                "problem": prob_pack,
                "question_type": "coding",
                "title": "Warehouse Logistics Container Packing",
                "prompt": prob_pack.description,
                "order": 4,
                "marks": 40.0,
            }
        )

    # -------------------------------------------------------------
    # MOCK 3: TCS-style Placement Mock
    # -------------------------------------------------------------
    asmt_tcs, _ = CodingAssessment.objects.update_or_create(
        assessment_id="asmt_tcs_placement",
        defaults={
            "title": "TCS-style Placement Mock",
            "slug": "tcs-style-placement-mock",
            "company_tag": "TCS-style",
            "category": "Mixed Placement Assessments",
            "description": "Standard national qualifier test simulation featuring Numerical Ability, Logical Deduction, and Algorithmic Coding.",
            "difficulty": "Medium",
            "duration_minutes": 90,
            "total_marks": 100.0,
            "pass_percentage": 60,
            "negative_marking_percentage": 0.0,
            "is_company_mock": True,
            "is_pro_only": False,
            "proctoring_enabled": True,
            "require_fullscreen": True,
            "require_screen_share": True,
            "max_tab_switches": 3,
            "max_fullscreen_exits": 3,
            "active": True,
        }
    )

    sec_tcs_num, _ = AssessmentSection.objects.update_or_create(
        section_id="sec_tcs_num",
        defaults={
            "assessment": asmt_tcs,
            "title": "Section 1: Numerical Ability",
            "section_type": "aptitude",
            "order": 1,
            "total_marks": 30.0,
        }
    )
    sec_tcs_code, _ = AssessmentSection.objects.update_or_create(
        section_id="sec_tcs_code",
        defaults={
            "assessment": asmt_tcs,
            "title": "Section 2: Hands-on Programming",
            "section_type": "coding",
            "order": 2,
            "total_marks": 70.0,
        }
    )

    AssessmentQuestionItem.objects.update_or_create(
        item_id="item_tcs_q1",
        defaults={
            "assessment": asmt_tcs,
            "section": sec_tcs_num,
            "question_type": "mcq_single",
            "title": "Speed, Time and Distance",
            "prompt": "An express train moving at 72 km/h crosses a 180m bridge in 15 seconds. What is the length of the train in meters?",
            "options": [
                {"id": "A", "text": "100 m"},
                {"id": "B", "text": "120 m"},
                {"id": "C", "text": "140 m"},
                {"id": "D", "text": "150 m"},
            ],
            "correct_answers": ["B"],
            "explanation": "Speed = 72 * (5/18) = 20 m/s. Total distance crossed in 15s = 20 * 15 = 300m. Train length = 300 - 180 = 120m.",
            "order": 1,
            "marks": 30.0,
        }
    )

    if prob_velocity:
        AssessmentQuestionItem.objects.update_or_create(
            item_id="item_tcs_q2",
            defaults={
                "assessment": asmt_tcs,
                "section": sec_tcs_code,
                "problem": prob_velocity,
                "question_type": "coding",
                "title": "Longest Increasing Order Velocity",
                "prompt": prob_velocity.description,
                "order": 2,
                "marks": 70.0,
            }
        )

    print("Seeded Company Mocks (Amazon-style, Deloitte-style, TCS-style) successfully with multi-sections!")

if __name__ == "__main__":
    seed_company_mocks()
