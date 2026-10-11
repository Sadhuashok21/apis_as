import uuid
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from skiltrix.models import (
    CodingAssessment, CompanyMock, AssessmentSection,
    AssessmentQuestionItem, AssessmentTestCase, CodingProblems, CompanyBlueprint
)


class Command(BaseCommand):
    help = "Seeds complete company mock assessments, blueprints, sections, and questions in the admin panel."

    def handle(self, *args, **options):
        self.stdout.write("Starting company mocks seeding...")

        # 1. Blueprint definitions and Section Configurations
        blueprints_data = [
            {
                "slug": "amazon-style-sde",
                "name": "Amazon-style SDE Mock",
                "tag": "Amazon-style",
                "category": "Company Mocks",
                "tier": "free",
                "duration": 90,
                "difficulty": "Medium",
                "desc": "Simulated Amazon-style Software Development Engineer assessment testing CS Fundamentals, backend debugging, and scalable DSA algorithms.",
                "sections": [
                    {"title": "Section 1: CS Fundamentals", "type": "technical", "marks": 20.0, "duration": 25},
                    {"title": "Section 2: Backend & System Debugging", "type": "debugging", "marks": 30.0, "duration": 25},
                    {"title": "Section 3: Core DSA & Coding", "type": "coding", "marks": 50.0, "duration": 40},
                ]
            },
            {
                "slug": "deloitte-style-placement",
                "name": "Deloitte-style Placement Mock",
                "tag": "Deloitte-style",
                "category": "Mixed Placement Assessments",
                "tier": "free",
                "duration": 75,
                "difficulty": "Medium",
                "desc": "Deloitte-style comprehensive campus placement test evaluating quantitative problem solving, logical reasoning, relational SQL, and coding.",
                "sections": [
                    {"title": "Section 1: Quantitative Aptitude", "type": "aptitude", "marks": 25.0, "duration": 20},
                    {"title": "Section 2: Logical Reasoning", "type": "reasoning", "marks": 25.0, "duration": 20},
                    {"title": "Section 3: SQL & Database Querying", "type": "sql", "marks": 20.0, "duration": 15},
                    {"title": "Section 4: Hands-on Programming", "type": "coding", "marks": 30.0, "duration": 20},
                ]
            },
            {
                "slug": "tcs-style-placement",
                "name": "TCS-style Placement Mock",
                "tag": "TCS-style",
                "category": "Mixed Placement Assessments",
                "tier": "free",
                "duration": 90,
                "difficulty": "Medium",
                "desc": "TCS NQT-style simulated recruitment test covering numerical aptitude, deductive reasoning, and hands-on algorithmic coding.",
                "sections": [
                    {"title": "Section 1: Numerical Ability", "type": "aptitude", "marks": 25.0, "duration": 30},
                    {"title": "Section 2: Reasoning Ability", "type": "reasoning", "marks": 25.0, "duration": 30},
                    {"title": "Section 3: Hands-on Programming", "type": "coding", "marks": 50.0, "duration": 30},
                ]
            },
            {
                "slug": "accenture-style-coding",
                "name": "Accenture-style Coding Mock",
                "tag": "Accenture-style",
                "category": "Company Mocks",
                "tier": "free",
                "duration": 90,
                "difficulty": "Medium",
                "desc": "Accenture-style assessment focusing on critical reasoning, technical pseudocode execution, and practical coding exercises.",
                "sections": [
                    {"title": "Section 1: Critical Reasoning", "type": "reasoning", "marks": 25.0, "duration": 25},
                    {"title": "Section 2: Technical MCQ & Pseudocode", "type": "technical", "marks": 25.0, "duration": 25},
                    {"title": "Section 3: Coding Assessment", "type": "coding", "marks": 50.0, "duration": 40},
                ]
            },
            {
                "slug": "infosys-style-placement",
                "name": "Infosys-style Placement Mock",
                "tag": "Infosys-style",
                "category": "Company Mocks",
                "tier": "pro",
                "duration": 100,
                "difficulty": "Medium",
                "desc": "Infosys DSE/SE-style recruitment assessment covering mathematical proficiency, pseudocode evaluation, and hands-on coding rounds.",
                "sections": [
                    {"title": "Section 1: Mathematical Abilities", "type": "aptitude", "marks": 20.0, "duration": 30},
                    {"title": "Section 2: Pseudocode Analysis", "type": "technical", "marks": 20.0, "duration": 30},
                    {"title": "Section 3: Hands-on Coding Round", "type": "coding", "marks": 60.0, "duration": 40},
                ]
            },
            {
                "slug": "cognizant-style-placement",
                "name": "Cognizant-style Placement Mock",
                "tag": "Cognizant-style",
                "category": "Company Mocks",
                "tier": "pro",
                "duration": 80,
                "difficulty": "Medium",
                "desc": "Cognizant GenC / Next-style placement mock with analytical aptitude, core computer science concepts, and code debugging challenges.",
                "sections": [
                    {"title": "Section 1: Quantitative & Analytical", "type": "aptitude", "marks": 25.0, "duration": 25},
                    {"title": "Section 2: CS Fundamentals", "type": "technical", "marks": 25.0, "duration": 25},
                    {"title": "Section 3: Coding & Bug Fixing Challenge", "type": "coding", "marks": 50.0, "duration": 30},
                ]
            },
            {
                "slug": "wipro-style-placement",
                "name": "Wipro-style Placement Mock",
                "tag": "Wipro-style",
                "category": "Company Mocks",
                "tier": "pro",
                "duration": 80,
                "difficulty": "Medium",
                "desc": "Wipro Elite / Turbo National Talent Hunt pattern mock with quantitative problems, logical analysis, and coding problems.",
                "sections": [
                    {"title": "Section 1: Quantitative Aptitude", "type": "aptitude", "marks": 30.0, "duration": 25},
                    {"title": "Section 2: Logical Reasoning", "type": "reasoning", "marks": 30.0, "duration": 25},
                    {"title": "Section 3: Programming & Coding", "type": "coding", "marks": 40.0, "duration": 30},
                ]
            },
            {
                "slug": "capgemini-style-placement",
                "name": "Capgemini-style Placement Mock",
                "tag": "Capgemini-style",
                "category": "Company Mocks",
                "tier": "pro",
                "duration": 90,
                "difficulty": "Medium",
                "desc": "Capgemini-style campus recruitment test featuring pseudocode challenges, deductive logical reasoning, and programming questions.",
                "sections": [
                    {"title": "Section 1: Pseudocode Challenge", "type": "technical", "marks": 30.0, "duration": 30},
                    {"title": "Section 2: Logical Reasoning", "type": "reasoning", "marks": 30.0, "duration": 30},
                    {"title": "Section 3: Coding Test", "type": "coding", "marks": 40.0, "duration": 30},
                ]
            },
            {
                "slug": "microsoft-style-placement",
                "name": "Microsoft-style Placement Mock",
                "tag": "Microsoft-style",
                "category": "Coding Assessments",
                "tier": "pro",
                "duration": 90,
                "difficulty": "Hard",
                "desc": "Microsoft-style technical online assessment evaluating operating system internals, algorithm efficiency, dynamic programming, and binary search.",
                "sections": [
                    {"title": "Section 1: CS Fundamentals & OS", "type": "technical", "marks": 20.0, "duration": 30},
                    {"title": "Section 2: Advanced Algorithmic Round", "type": "coding", "marks": 80.0, "duration": 60},
                ]
            },
            {
                "slug": "google-style-placement",
                "name": "Google-style Placement Mock",
                "tag": "Google-style",
                "category": "DSA Assessments",
                "tier": "pro",
                "duration": 105,
                "difficulty": "Hard",
                "desc": "Google-style algorithmic screening mock testing advanced problem solving, heap optimizations, interval greedy scheduling, and dynamic programming.",
                "sections": [
                    {"title": "Section 1: Algorithmic Problem Solving", "type": "coding", "marks": 100.0, "duration": 105},
                ]
            },
            {
                "slug": "general-sde-assessment",
                "name": "General SDE Assessment",
                "tag": "General SDE",
                "category": "Mixed Placement Assessments",
                "tier": "free",
                "duration": 90,
                "difficulty": "Medium",
                "desc": "Universal software engineering placement assessment with CS fundamentals, backend Django debugging, and core data structure programming.",
                "sections": [
                    {"title": "Section 1: CS Fundamentals", "type": "technical", "marks": 20.0, "duration": 25},
                    {"title": "Section 2: Backend Debugging", "type": "debugging", "marks": 30.0, "duration": 25},
                    {"title": "Section 3: Core Coding", "type": "coding", "marks": 50.0, "duration": 40},
                ]
            },
        ]

        total_mocks_created = 0
        total_mocks_updated = 0
        total_sections = 0

        for b_data in blueprints_data:
            # Sync / Update Blueprint
            sections_config = [
                {"title": s["title"], "type": s["type"], "marks": s["marks"], "duration": s["duration"]}
                for s in b_data["sections"]
            ]
            CompanyBlueprint.objects.update_or_create(
                slug=b_data["slug"],
                defaults={
                    "company_name": b_data["name"],
                    "category": b_data["category"],
                    "description": b_data["desc"],
                    "sections_config": sections_config,
                    "recommended_topics": ["DSA", "Aptitude", "Debugging", "CS Fundamentals"],
                    "duration_minutes": b_data["duration"],
                    "tier": b_data["tier"],
                    "is_active": True,
                }
            )

            # Sync / Update CodingAssessment / CompanyMock
            asmt_slug = f"{b_data['slug']}-mock"
            asmt_id = f"asmt_{b_data['slug'].replace('-', '_')}"

            asmt = CodingAssessment.objects.filter(slug=asmt_slug).first()
            if not asmt:
                asmt = CodingAssessment.objects.filter(assessment_id=asmt_id).first()

            created = False
            if asmt:
                asmt.title = b_data["name"]
                asmt.category = b_data["category"]
                asmt.company_tag = b_data["tag"]
                asmt.description = b_data["desc"]
                asmt.difficulty = b_data["difficulty"]
                asmt.duration_minutes = b_data["duration"]
                asmt.is_company_mock = True
                asmt.is_pro_only = b_data["tier"] == "pro"
                asmt.proctoring_enabled = True
                asmt.active = True
                asmt.save()
                total_mocks_updated += 1
            else:
                asmt = CodingAssessment.objects.create(
                    assessment_id=asmt_id,
                    title=b_data["name"],
                    slug=asmt_slug,
                    category=b_data["category"],
                    company_tag=b_data["tag"],
                    description=b_data["desc"],
                    difficulty=b_data["difficulty"],
                    duration_minutes=b_data["duration"],
                    pass_percentage=70,
                    total_marks=100.0,
                    negative_marking_percentage=0.25 if "Aptitude" in b_data["category"] or "Mixed" in b_data["category"] else 0.0,
                    is_company_mock=True,
                    is_pro_only=b_data["tier"] == "pro",
                    proctoring_enabled=True,
                    require_fullscreen=True,
                    require_screen_share=True,
                    max_tab_switches=3,
                    max_fullscreen_exits=3,
                    allow_return_to_previous=True,
                    randomize_questions=False,
                    randomize_options=True,
                    active=True,
                )
                created = True
                total_mocks_created += 1

            # Sync Sections for this assessment
            order = 1
            for s_info in b_data["sections"]:
                sec = AssessmentSection.objects.filter(assessment=asmt, title=s_info["title"]).first()
                if not sec:
                    sec = AssessmentSection.objects.filter(assessment=asmt, order=order).first()
                if sec:
                    sec.title = s_info["title"]
                    sec.section_type = s_info["type"]
                    sec.total_marks = s_info["marks"]
                    sec.duration_minutes = s_info["duration"]
                    sec.order = order
                    sec.save()
                else:
                    sec = AssessmentSection.objects.create(
                        section_id=f"sec_{uuid.uuid4().hex[:12]}",
                        assessment=asmt,
                        title=s_info["title"],
                        section_type=s_info["type"],
                        total_marks=s_info["marks"],
                        duration_minutes=s_info["duration"],
                        order=order,
                    )
                total_sections += 1
                order += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully synced {total_mocks_created} new mocks, {total_mocks_updated} updated mocks, and {total_sections} sections."
            )
        )

        # 2. Attach and populate realistic Question Items for each Mock Assessment
        self.populate_questions()

    def populate_questions(self):
        self.stdout.write("Populating questions for Company Mocks...")

        # Helper mapping of coding problems
        two_sum = CodingProblems.objects.filter(slug__icontains="two-sum").first()
        valid_parens = CodingProblems.objects.filter(slug__icontains="valid-parentheses").first()
        binary_search = CodingProblems.objects.filter(slug__icontains="binary-search").first()
        max_sub = CodingProblems.objects.filter(slug__icontains="maximum-subarray").first()
        coin_change = CodingProblems.objects.filter(slug__icontains="coin-change").first()
        trapping_rain = CodingProblems.objects.filter(slug__icontains="trapping-rain-water").first()
        first_non_rep = CodingProblems.objects.filter(slug__icontains="first-non-repeating").first()
        warehouse = CodingProblems.objects.filter(slug__icontains="warehouse-logistics").first()
        cloud_server = CodingProblems.objects.filter(slug__icontains="cloud-server-allocation").first()
        n_plus_one = CodingProblems.objects.filter(slug__icontains="n-1-query").first()
        drf_bug = CodingProblems.objects.filter(slug__icontains="missing-many-true").first()
        jwt_bug = CodingProblems.objects.filter(slug__icontains="jwt-expiration").first()
        sql_bug = CodingProblems.objects.filter(slug__icontains="sql-query-debugging").first()

        # Iterate all Company Mocks and populate/link questions to each section
        mocks = CodingAssessment.objects.filter(is_company_mock=True)
        questions_linked = 0

        for mock in mocks:
            for sec in mock.sections.all():
                s_type = sec.section_type

                # Coding section questions
                if s_type == "coding":
                    if not mock.question_items.filter(section=sec).exists():
                        prob = None
                        if "Amazon" in mock.company_tag:
                            prob = warehouse or two_sum
                        elif "Google" in mock.company_tag:
                            prob = cloud_server or trapping_rain
                        elif "Microsoft" in mock.company_tag:
                            prob = max_sub or coin_change
                        elif "Deloitte" in mock.company_tag:
                            prob = two_sum
                        elif "TCS" in mock.company_tag:
                            prob = valid_parens or binary_search
                        elif "Accenture" in mock.company_tag:
                            prob = max_sub or two_sum
                        else:
                            prob = binary_search or two_sum

                        if prob:
                            item = AssessmentQuestionItem.objects.create(
                                item_id=str(uuid.uuid4()),
                                assessment=mock,
                                section=sec,
                                problem=prob,
                                question_type="coding",
                                title=prob.title,
                                slug=f"{mock.slug}-{prob.slug}"[:250],
                                category=prob.category,
                                difficulty=prob.difficulty,
                                company_style=mock.company_tag,
                                section_assignment="Coding",
                                marks=sec.total_marks,
                                status="Published",
                                prompt=prob.description,
                                starter_code=prob.starter_python,
                                reference_solution=prob.solution_code,
                                time_limit_seconds=prob.time_limit_seconds,
                                memory_limit_mb=prob.memory_limit_mb,
                                order=1,
                            )
                            # Add test cases
                            AssessmentTestCase.objects.create(
                                case_id=str(uuid.uuid4()),
                                question=item,
                                test_type="sample",
                                weight=30.0,
                                is_active=True,
                                input_data=prob.input_format or "sample_input",
                                expected_output=prob.output_format or "sample_output",
                                explanation="Sample test case validation"
                            )
                            AssessmentTestCase.objects.create(
                                case_id=str(uuid.uuid4()),
                                question=item,
                                test_type="hidden",
                                weight=70.0,
                                is_active=True,
                                input_data="hidden_large_input",
                                expected_output="hidden_expected_output",
                                explanation="Hidden boundary & scale validation"
                            )
                            questions_linked += 1

                # Debugging section questions
                elif s_type == "debugging":
                    if not mock.question_items.filter(section=sec).exists():
                        prob = n_plus_one or drf_bug or jwt_bug
                        item = AssessmentQuestionItem.objects.create(
                            item_id=str(uuid.uuid4()),
                            assessment=mock,
                            section=sec,
                            problem=prob,
                            question_type="django_debugging" if prob and "Django" in prob.title else "backend_debugging",
                            title=prob.title if prob else f"{mock.company_tag} Backend Debugging Challenge",
                            slug=f"{mock.slug}-debugging-{uuid.uuid4().hex[:6]}",
                            category="Backend Debugging",
                            difficulty="Medium",
                            company_style=mock.company_tag,
                            section_assignment="Debugging",
                            marks=sec.total_marks,
                            status="Published",
                            prompt=prob.description if prob else "Diagnose and resolve the production bug in the backend service.",
                            buggy_code=prob.error_snippet if prob else "def handle_request(): ...",
                            error_message="500 Internal Server Error / Subscript Error",
                            expected_behavior="Response 200 OK with correct serialized data payload.",
                            starter_code=prob.starter_python if prob else "",
                            reference_solution=prob.solution_code if prob else "",
                            order=1,
                        )
                        questions_linked += 1

                # SQL section questions
                elif s_type == "sql":
                    if not mock.question_items.filter(section=sec).exists():
                        prob = sql_bug
                        item = AssessmentQuestionItem.objects.create(
                            item_id=str(uuid.uuid4()),
                            assessment=mock,
                            section=sec,
                            problem=prob,
                            question_type="sql",
                            title="SQL Query Row Suppression Debugging" if prob else "Relational SQL Aggregation",
                            slug=f"{mock.slug}-sql-{uuid.uuid4().hex[:6]}",
                            category="SQL & Databases",
                            difficulty="Easy",
                            company_style=mock.company_tag,
                            section_assignment="SQL",
                            marks=sec.total_marks,
                            status="Published",
                            prompt="Write or correct the SQL query to return employee departments with count > 5 without omitting empty departments.",
                            starter_code="SELECT d.dept_name, COUNT(e.emp_id) FROM departments d LEFT JOIN employees e ON d.dept_id = e.dept_id GROUP BY d.dept_name;",
                            reference_solution="SELECT d.dept_name, COUNT(e.emp_id) FROM departments d LEFT JOIN employees e ON d.dept_id = e.dept_id GROUP BY d.dept_name HAVING COUNT(e.emp_id) > 5;",
                            order=1,
                        )
                        questions_linked += 1

                # Aptitude & Reasoning section questions
                elif s_type in ["aptitude", "reasoning"]:
                    if not mock.question_items.filter(section=sec).exists():
                        is_apt = s_type == "aptitude"
                        title = "Speed, Time and Distance Calculation" if is_apt else "Deductive Syllogism and Pattern Analysis"
                        prompt = (
                            "A train running at 72 km/h crosses a 200m long platform in 22 seconds. What is the length of the train in meters?"
                            if is_apt else
                            "In a certain code, 'ORBIT' is written as 'PSCKU'. How is 'GALAXY' written in that code?"
                        )
                        options = (
                            [{"id": "A", "text": "220 m"}, {"id": "B", "text": "240 m"}, {"id": "C", "text": "260 m"}, {"id": "D", "text": "280 m"}]
                            if is_apt else
                            [{"id": "A", "text": "HBMBAZ"}, {"id": "B", "text": "HCLBYZ"}, {"id": "C", "text": "HBMCBZ"}, {"id": "D", "text": "IBMCBZ"}]
                        )
                        correct = ["B"] if is_apt else ["A"]

                        item = AssessmentQuestionItem.objects.create(
                            item_id=str(uuid.uuid4()),
                            assessment=mock,
                            section=sec,
                            question_type="mcq_single",
                            title=title,
                            slug=f"{mock.slug}-{s_type}-{uuid.uuid4().hex[:6]}",
                            category="Aptitude" if is_apt else "Logical Reasoning",
                            difficulty="Easy",
                            company_style=mock.company_tag,
                            section_assignment="Aptitude" if is_apt else "Logical Reasoning",
                            marks=sec.total_marks,
                            negative_marks=sec.total_marks * 0.25,
                            status="Published",
                            prompt=prompt,
                            options=options,
                            correct_answers=correct,
                            explanation="Detailed step-by-step mathematical derivation.",
                            order=1,
                        )
                        questions_linked += 1

                # Technical & CS Fundamentals section questions
                elif s_type == "technical":
                    if not mock.question_items.filter(section=sec).exists():
                        item = AssessmentQuestionItem.objects.create(
                            item_id=str(uuid.uuid4()),
                            assessment=mock,
                            section=sec,
                            question_type="mcq_single",
                            title="Operating Systems: Virtual Memory & Page Faults",
                            slug=f"{mock.slug}-technical-{uuid.uuid4().hex[:6]}",
                            category="CS Fundamentals",
                            difficulty="Medium",
                            company_style=mock.company_tag,
                            section_assignment="CS Fundamentals",
                            marks=sec.total_marks,
                            status="Published",
                            prompt="Which page replacement algorithm suffers from Belady's Anomaly?",
                            options=[
                                {"id": "A", "text": "LRU (Least Recently Used)"},
                                {"id": "B", "text": "FIFO (First In First Out)"},
                                {"id": "C", "text": "Optimal Page Replacement"},
                                {"id": "D", "text": "LFU (Least Frequently Used)"}
                            ],
                            correct_answers=["B"],
                            explanation="FIFO page replacement algorithm is susceptible to Belady's Anomaly, where increasing the number of page frames causes more page faults.",
                            order=1,
                        )
                        questions_linked += 1

        self.stdout.write(self.style.SUCCESS(f"Successfully populated and linked {questions_linked} question items!"))
