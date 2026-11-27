"""Seed realistic SkilTrix assessments across MCQ, Technical, Coding, and Company categories."""

from __future__ import annotations

import uuid
from django.core.management.base import BaseCommand
from django.db import transaction

from skiltrix.django_assessment_runner import (
    DEFAULT_AMAZON_HIDDEN_TEST_FILES,
    DEFAULT_AMAZON_PROJECT_FILES,
)
from skiltrix.models import (
    AssessmentQuestionItem,
    AssessmentSection,
    CodingAssessment,
    CodingProblems,
    TestCases,
)


PROBLEMS_SEED = [
    {
        "problem_id": "prob_st_two_sum_count",
        "title": "Pair Sum Target Indices",
        "slug": "pair-sum-target-indices",
        "difficulty": "Easy",
        "category": "Arrays & Hashing",
        "topics": ["Arrays", "Hash Table"],
        "points": 100,
        "time_limit_seconds": 2.0,
        "memory_limit_mb": 256,
        "description": (
            "Given N and target K on the first line, followed by N space-separated integers "
            "on the second line, find two distinct 0-based indices i < j such that "
            "nums[i] + nums[j] == K. Print 'i j' if a valid pair exists (preferring the first "
            "valid pair found), or '-1 -1' otherwise."
        ),
        "input_format": "Line 1: Two integers N and K\nLine 2: N space-separated integers",
        "output_format": "Two space-separated indices i j (with i < j), or -1 -1",
        "constraints": "2 <= N <= 10^5\n-10^9 <= nums[i], K <= 10^9",
        "sample_input": "4 9\n2 7 11 15",
        "sample_output": "0 1",
        "sample_explanation": "nums[0] + nums[1] = 2 + 7 = 9.",
        "explanation": "Store seen values and their earliest index in a hash map for O(N) lookup.",
        "starter_python": (
            "import sys\n\n"
            "def solve():\n"
            "    tokens = sys.stdin.read().split()\n"
            "    if not tokens: return\n"
            "    n, k = int(tokens[0]), int(tokens[1])\n"
            "    nums = list(map(int, tokens[2:2+n]))\n"
            "    # Print two indices or -1 -1\n\n"
            "if __name__ == '__main__':\n"
            "    solve()\n"
        ),
        "starter_java": (
            "import java.io.*;\n"
            "import java.util.*;\n\n"
            "public class Main {\n"
            "    public static void main(String[] args) throws Exception {\n"
            "        Scanner sc = new Scanner(System.in);\n"
            "        if (!sc.hasNextInt()) return;\n"
            "        int n = sc.nextInt();\n"
            "        long k = sc.nextLong();\n"
            "        long[] nums = new long[n];\n"
            "        for (int i = 0; i < n; i++) nums[i] = sc.nextLong();\n"
            "        // Print i + \" \" + j or \"-1 -1\"\n"
            "    }\n"
            "}\n"
        ),
        "starter_c": (
            "#include <stdio.h>\n\n"
            "int main(void) {\n"
            "    int n; long long k;\n"
            "    if (scanf(\"%d %lld\", &n, &k) != 2) return 0;\n"
            "    /* Read n integers and print matching indices */\n"
            "    return 0;\n"
            "}\n"
        ),
        "starter_cpp": (
            "#include <bits/stdc++.h>\n"
            "using namespace std;\n\n"
            "int main() {\n"
            "    ios::sync_with_stdio(false);\n"
            "    cin.tie(nullptr);\n"
            "    int n; long long k;\n"
            "    if (!(cin >> n >> k)) return 0;\n"
            "    vector<long long> nums(n);\n"
            "    for (int i = 0; i < n; i++) cin >> nums[i];\n"
            "    // Write your solution\n"
            "    return 0;\n"
            "}\n"
        ),
        "starter_javascript": (
            "'use strict';\n"
            "const fs = require('fs');\n\n"
            "const tokens = fs.readFileSync(0, 'utf8').trim().split(/\\s+/);\n"
            "if (tokens.length >= 2 && tokens[0]) {\n"
            "    const n = Number(tokens[0]);\n"
            "    const k = Number(tokens[1]);\n"
            "    const nums = tokens.slice(2, 2 + n).map(Number);\n"
            "    // console.log(i + ' ' + j);\n"
            "}\n"
        ),
        "test_cases": [
            {"input": "4 9\n2 7 11 15", "output": "0 1", "hidden": False, "points": 20, "exp": "2 + 7 = 9"},
            {"input": "3 6\n3 2 4", "output": "1 2", "hidden": False, "points": 20, "exp": "2 + 4 = 6"},
            {"input": "2 6\n3 3", "output": "0 1", "hidden": True, "points": 20},
            {"input": "5 100\n1 2 3 4 5", "output": "-1 -1", "hidden": True, "points": 20},
            {"input": "4 -8\n-1 -2 -5 -3", "output": "2 3", "hidden": True, "points": 20},
        ],
    },
    {
        "problem_id": "prob_st_balanced_brackets",
        "title": "Valid Bracket Sequence",
        "slug": "valid-bracket-sequence",
        "difficulty": "Easy",
        "category": "Stacks",
        "topics": ["Stack", "Strings"],
        "points": 100,
        "time_limit_seconds": 2.0,
        "memory_limit_mb": 256,
        "description": (
            "Given a string S consisting strictly of '(', ')', '{', '}', '[' and ']', "
            "determine whether every opening bracket is closed by the same type in the "
            "correct order. Print YES if valid, otherwise NO."
        ),
        "input_format": "A single line string S",
        "output_format": "YES or NO",
        "constraints": "1 <= |S| <= 10^5",
        "sample_input": "{[()]}",
        "sample_output": "YES",
        "sample_explanation": "All nested brackets match in LIFO order.",
        "explanation": "Use a stack: push opening brackets and pop/verify matching pairs on closing brackets.",
        "starter_python": (
            "import sys\n\n"
            "def solve():\n"
            "    s = sys.stdin.read().strip()\n"
            "    # Print YES or NO\n\n"
            "if __name__ == '__main__':\n"
            "    solve()\n"
        ),
        "starter_java": (
            "import java.io.*;\n\n"
            "public class Main {\n"
            "    public static void main(String[] args) throws Exception {\n"
            "        BufferedReader br = new BufferedReader(new InputStreamReader(System.in));\n"
            "        String s = br.readLine();\n"
            "        // Print YES or NO\n"
            "    }\n"
            "}\n"
        ),
        "starter_c": (
            "#include <stdio.h>\n"
            "#include <string.h>\n\n"
            "int main(void) {\n"
            "    char s[100005];\n"
            "    if (scanf(\"%100000s\", s) != 1) return 0;\n"
            "    /* Print YES or NO */\n"
            "    return 0;\n"
            "}\n"
        ),
        "starter_cpp": (
            "#include <bits/stdc++.h>\n"
            "using namespace std;\n\n"
            "int main() {\n"
            "    string s;\n"
            "    if (!(cin >> s)) return 0;\n"
            "    // Print YES or NO\n"
            "    return 0;\n"
            "}\n"
        ),
        "starter_javascript": (
            "'use strict';\n"
            "const fs = require('fs');\n"
            "const s = fs.readFileSync(0, 'utf8').trim();\n"
            "// Print YES or NO\n"
        ),
        "test_cases": [
            {"input": "{[()]}", "output": "YES", "hidden": False, "points": 25, "exp": "Properly nested brackets"},
            {"input": "([)]", "output": "NO", "hidden": False, "points": 25, "exp": "Mismatched nesting order"},
            {"input": "()", "output": "YES", "hidden": True, "points": 25},
            {"input": "((((", "output": "NO", "hidden": True, "points": 25},
        ],
    },
    {
        "problem_id": "prob_st_kadane_max",
        "title": "Maximum Contiguous Subarray Sum",
        "slug": "maximum-contiguous-subarray-sum",
        "difficulty": "Medium",
        "category": "Dynamic Programming",
        "topics": ["Arrays", "Kadane Algorithm", "Dynamic Programming"],
        "points": 150,
        "time_limit_seconds": 2.0,
        "memory_limit_mb": 256,
        "description": (
            "Given an integer array of length N containing positive and negative numbers, "
            "find the contiguous non-empty subarray with the largest possible sum and print that sum."
        ),
        "input_format": "Line 1: Integer N\nLine 2: N space-separated integers",
        "output_format": "A single integer representing the maximum subarray sum",
        "constraints": "1 <= N <= 10^5\n-10^5 <= A[i] <= 10^5",
        "sample_input": "9\n-2 1 -3 4 -1 2 1 -5 4",
        "sample_output": "6",
        "sample_explanation": "The subarray [4, -1, 2, 1] has sum 6.",
        "explanation": "Kadane's algorithm scans linearly keeping cur_max = max(x, cur_max + x) and updating global best.",
        "starter_python": (
            "import sys\n\n"
            "def solve():\n"
            "    tokens = sys.stdin.read().split()\n"
            "    if not tokens: return\n"
            "    n = int(tokens[0])\n"
            "    nums = list(map(int, tokens[1:1+n]))\n"
            "    # Compute and print max subarray sum\n\n"
            "if __name__ == '__main__':\n"
            "    solve()\n"
        ),
        "starter_java": (
            "import java.util.*;\n\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Scanner sc = new Scanner(System.in);\n"
            "        if (!sc.hasNextInt()) return;\n"
            "        int n = sc.nextInt();\n"
            "        long[] a = new long[n];\n"
            "        for (int i = 0; i < n; i++) a[i] = sc.nextLong();\n"
            "        // Print max subarray sum\n"
            "    }\n"
            "}\n"
        ),
        "starter_c": (
            "#include <stdio.h>\n\n"
            "int main(void) {\n"
            "    int n;\n"
            "    if (scanf(\"%d\", &n) != 1) return 0;\n"
            "    /* Compute Kadane max sum */\n"
            "    return 0;\n"
            "}\n"
        ),
        "starter_cpp": (
            "#include <bits/stdc++.h>\n"
            "using namespace std;\n\n"
            "int main() {\n"
            "    ios::sync_with_stdio(false);\n"
            "    cin.tie(nullptr);\n"
            "    int n; cin >> n;\n"
            "    // Compute max subarray sum\n"
            "    return 0;\n"
            "}\n"
        ),
        "starter_javascript": (
            "'use strict';\n"
            "const fs = require('fs');\n"
            "const tokens = fs.readFileSync(0, 'utf8').trim().split(/\\s+/);\n"
            "if (tokens[0]) {\n"
            "    const n = Number(tokens[0]);\n"
            "    const nums = tokens.slice(1, 1 + n).map(Number);\n"
            "    // console.log(ans);\n"
            "}\n"
        ),
        "test_cases": [
            {"input": "9\n-2 1 -3 4 -1 2 1 -5 4", "output": "6", "hidden": False, "points": 30, "exp": "[4, -1, 2, 1] -> 6"},
            {"input": "5\n5 4 -1 7 8", "output": "23", "hidden": False, "points": 30, "exp": "Entire array sums to 23"},
            {"input": "4\n-5 -2 -9 -3", "output": "-2", "hidden": True, "points": 45},
            {"input": "1\n42", "output": "42", "hidden": True, "points": 45},
        ],
    },
]


class Command(BaseCommand):
    help = "Seed MCQ, Technical, Coding, and Company-Specific Assessments with real test cases."

    @transaction.atomic
    def handle(self, *args, **options):
        problems_by_id = {}
        for pdata in PROBLEMS_SEED:
            prob, _ = CodingProblems.objects.update_or_create(
                problem_id=pdata["problem_id"],
                defaults={
                    "title": pdata["title"],
                    "slug": pdata["slug"],
                    "difficulty": pdata["difficulty"],
                    "question_type": "algorithmic",
                    "category": pdata["category"],
                    "topics": pdata["topics"],
                    "points": pdata["points"],
                    "description": pdata["description"],
                    "input_format": pdata["input_format"],
                    "output_format": pdata["output_format"],
                    "constraints": pdata["constraints"],
                    "sample_input": pdata["sample_input"],
                    "sample_output": pdata["sample_output"],
                    "sample_explanation": pdata["sample_explanation"],
                    "explanation": pdata["explanation"],
                    "time_limit_seconds": pdata["time_limit_seconds"],
                    "memory_limit_mb": pdata["memory_limit_mb"],
                    "supported_languages": ["python", "java", "c", "cpp", "javascript"],
                    "starter_python": pdata["starter_python"],
                    "starter_java": pdata["starter_java"],
                    "starter_c": pdata["starter_c"],
                    "starter_cpp": pdata["starter_cpp"],
                    "starter_javascript": pdata["starter_javascript"],
                    "is_active": True,
                    "status": "active",
                },
            )
            prob.test_cases.all().delete()
            for idx, tc in enumerate(pdata["test_cases"], start=1):
                TestCases.objects.create(
                    test_case_id=f"tc_{prob.problem_id}_{idx}",
                    problem=prob,
                    input_data=tc["input"],
                    expected_output=tc["output"],
                    is_hidden=tc["hidden"],
                    is_sample=not tc["hidden"],
                    category="Hidden" if tc["hidden"] else "Basic",
                    explanation=tc.get("exp", ""),
                    points=tc["points"],
                    order=idx,
                )
            problems_by_id[prob.problem_id] = prob

        django_prob, _ = CodingProblems.objects.update_or_create(
            problem_id="prob_st_amazon_django_post_bug",
            defaults={
                "title": "Issue: Post Creation (Django Backend)",
                "slug": "fix-django-post-upload-endpoint-slug-collision",
                "difficulty": "Medium",
                "question_type": "django_debug",
                "category": "Django Backend",
                "topics": ["Django", "REST API", "ORM", "Unit Testing"],
                "points": 150,
                "description": (
                    "This is a blogging platform where users can discover, read, and share blog posts.\n\n"
                    "However, users are unable to create and publish new blog posts via the Write form or `POST /api/posts/`, "
                    "despite filling all required fields.\n\n"
                    "Steps to Reproduce:\n"
                    "1. Click Run Server in the CodeLab IDE toolbar to launch `manage.py runserver` and open the Preview tab.\n"
                    "2. Fill in Post title, content, and email and click Publish Post (or test `POST /api/posts/`).\n"
                    "3. Click Run Tests to execute `posts/tests.py` (`manage.py test`).\n\n"
                    "Backend Issues to Rectify in `posts/views.py`:\n"
                    "• Parse `application/json` payloads safely in `posts_collection` (with `request.POST` fallback).\n"
                    "• Validate non-empty stripped `title` and `content` -> return HTTP 400 with `{\"status\": False, \"error\": \"...\"}`.\n"
                    "• Handle duplicate titles cleanly by generating a unique slug instead of crashing on `IntegrityError`.\n"
                    "• Return HTTP `201 Created` on successful post creation."
                ),
                "input_format": (
                    "POST /api/posts/ with JSON body:\n"
                    '{"title": "...", "content": "...", "author_email": "..."}'
                ),
                "output_format": (
                    "201 Created: {\"status\": true, \"post\": {\"id\", \"title\", \"slug\", \"content\", \"author_email\"}}\n"
                    "400 Bad Request: {\"status\": false, \"error\": \"...\"}"
                ),
                "constraints": (
                    "Do not break GET /api/posts/.\n"
                    "Both JSON (`application/json`) and form-encoded POST requests should work cleanly.\n"
                    "Passing only public `posts/tests.py` is not enough; hidden grading tests (`tests_hidden.py`) check edge cases."
                ),
                "sample_input": 'POST /api/posts/ {"title": "System Design Caching", "content": "Write-through patterns"}',
                "sample_output": '201 {"status": true, "post": {"title": "System Design Caching", "slug": "system-design-caching", ...}}',
                "sample_explanation": "Fix JSON parsing, blank validation, unique slug generation, and HTTP 201 status in posts/views.py.",
                "explanation": "Parse json.loads(request.body), validate non-empty stripped title & content, ensure unique slug loop, and return status=201.",
                "time_limit_seconds": 25.0,
                "memory_limit_mb": 512,
                "supported_languages": ["django"],
                "project_files": DEFAULT_AMAZON_PROJECT_FILES,
                "hidden_test_files": DEFAULT_AMAZON_HIDDEN_TEST_FILES,
                "is_active": True,
                "status": "active",
            },
        )
        problems_by_id[django_prob.problem_id] = django_prob

        # 1. Coding Assessment
        coding_asmt, _ = CodingAssessment.objects.update_or_create(
            assessment_id="asmt_amazon_coding_2026",
            defaults={
                "title": "Amazon SDE-1 Online Coding Assessment",
                "slug": "amazon-sde1-online-coding-assessment",
                "assessment_type": "coding",
                "category": "Coding Assessments",
                "company_tag": "Amazon",
                "description": "HackerRank/Amazon-style timed coding + Django backend debugging round across Python 3, Java, C, C++, JavaScript, and Django test suites.",
                "instructions": "Solve algorithmic problems using stdin/stdout and fix the Django POST upload bug in Question 2 using `manage.py test`. Hidden test suites determine full acceptance.",
                "difficulty": "Medium",
                "duration_minutes": 90,
                "pass_percentage": 60,
                "total_marks": 500,
                "supported_languages": ["python", "java", "c", "cpp", "javascript", "django"],
                "assignment_mode": "public",
                "show_results_immediately": True,
                "proctoring_enabled": True,
                "require_fullscreen": False,
                "active": True,
            },
        )
        sec_coding, _ = AssessmentSection.objects.update_or_create(
            section_id="sec_asmt_amazon_coding",
            defaults={
                "assessment": coding_asmt,
                "title": "Coding & Backend Debugging",
                "section_type": "Coding",
                "order": 1,
                "duration_minutes": 90,
                "total_marks": 500,
            },
        )
        amazon_items = [
            ("aqi_coding_1", "prob_st_two_sum_count", 1),
            ("aqi_coding_django_post", "prob_st_amazon_django_post_bug", 2),
            ("aqi_coding_2", "prob_st_balanced_brackets", 3),
            ("aqi_coding_3", "prob_st_kadane_max", 4),
        ]
        for item_id, pid, order_num in amazon_items:
            p = problems_by_id[pid]
            AssessmentQuestionItem.objects.update_or_create(
                item_id=item_id,
                defaults={
                    "assessment": coding_asmt,
                    "section": sec_coding,
                    "problem": p,
                    "question_type": "coding",
                    "title": p.title,
                    "slug": f"{p.slug}-coding-{order_num}",
                    "category": p.category or "Coding",
                    "difficulty": p.difficulty,
                    "prompt": p.description,
                    "marks": p.points,
                    "order": order_num,
                    "status": "Published",
                },
            )

        # 2. MCQ Assessment
        mcq_asmt, _ = CodingAssessment.objects.update_or_create(
            assessment_id="asmt_cs_fundamentals_mcq",
            defaults={
                "title": "Core CS & Data Structures MCQ Assessment",
                "slug": "core-cs-data-structures-mcq",
                "assessment_type": "mcq",
                "category": "MCQ Assessments",
                "description": "Timed objective screening covering time complexity, OS scheduling, DBMS normalization, and graph algorithms.",
                "difficulty": "Easy",
                "duration_minutes": 30,
                "pass_percentage": 60,
                "total_marks": 40,
                "negative_marking": True,
                "negative_marking_percentage": 25,
                "assignment_mode": "public",
                "show_results_immediately": True,
                "proctoring_enabled": False,
                "require_fullscreen": False,
                "active": True,
            },
        )
        sec_mcq, _ = AssessmentSection.objects.update_or_create(
            section_id="sec_asmt_cs_mcq",
            defaults={
                "assessment": mcq_asmt,
                "title": "Core CS Concepts",
                "section_type": "CS Fundamentals",
                "order": 1,
                "duration_minutes": 30,
                "total_marks": 40,
            },
        )
        mcq_rows = [
            (
                "aqi_mcq_1",
                "Binary Search Complexity",
                "What is the worst-case time complexity of binary search on a sorted array of length N?",
                [
                    {"id": "a", "text": "O(N)"},
                    {"id": "b", "text": "O(log N)"},
                    {"id": "c", "text": "O(N log N)"},
                    {"id": "d", "text": "O(1)"},
                ],
                ["b"],
                "Halving the search space on every step requires at most log2(N) comparisons.",
            ),
            (
                "aqi_mcq_2",
                "Hash Table Collision Resolution",
                "Which data structure gives O(1) average lookup using key-value hashing?",
                [
                    {"id": "a", "text": "Linked List"},
                    {"id": "b", "text": "Binary Heap"},
                    {"id": "c", "text": "Hash Map"},
                    {"id": "d", "text": "Trie"},
                ],
                ["c"],
                "Hash Maps compute bucket offsets directly in amortized O(1) time.",
            ),
            (
                "aqi_mcq_3",
                "Database Isolation",
                "Which ACID property ensures a committed transaction remains persisted even after a power failure?",
                [
                    {"id": "a", "text": "Atomicity"},
                    {"id": "b", "text": "Consistency"},
                    {"id": "c", "text": "Isolation"},
                    {"id": "d", "text": "Durability"},
                ],
                ["d"],
                "Durability guarantees write-ahead logs flush committed state safely to non-volatile storage.",
            ),
            (
                "aqi_mcq_4",
                "Breadth-First Search Queue",
                "Which linear structure is required to traverse a graph level-by-level in BFS?",
                [
                    {"id": "a", "text": "FIFO Queue"},
                    {"id": "b", "text": "LIFO Stack"},
                    {"id": "c", "text": "Disjoint Set"},
                    {"id": "d", "text": "Segment Tree"},
                ],
                ["a"],
                "BFS visits neighbors in FIFO discovery order using a queue.",
            ),
        ]
        for idx, (iid, title, prompt, opts, ans, exp) in enumerate(mcq_rows, start=1):
            AssessmentQuestionItem.objects.update_or_create(
                item_id=iid,
                defaults={
                    "assessment": mcq_asmt,
                    "section": sec_mcq,
                    "question_type": "mcq_single",
                    "title": title,
                    "slug": f"mcq-{iid}",
                    "category": "CS Fundamentals",
                    "difficulty": "Easy",
                    "prompt": prompt,
                    "options": opts,
                    "correct_answers": ans,
                    "explanation": exp,
                    "marks": 10,
                    "negative_marks": 2.5,
                    "order": idx,
                    "status": "Published",
                },
            )

        # 3. Technical Assessment (Hybrid: CS MCQs + Coding)
        tech_asmt, _ = CodingAssessment.objects.update_or_create(
            assessment_id="asmt_fullstack_technical_round",
            defaults={
                "title": "Software Engineering Technical Assessment",
                "slug": "software-engineering-technical-assessment",
                "assessment_type": "technical",
                "category": "Technical Assessments",
                "description": "Combined technical screening evaluating architecture, complexity reasoning, and live bracket-parsing implementation.",
                "difficulty": "Medium",
                "duration_minutes": 60,
                "pass_percentage": 60,
                "total_marks": 120,
                "supported_languages": ["python", "java", "c", "cpp", "javascript"],
                "assignment_mode": "public",
                "show_results_immediately": True,
                "proctoring_enabled": True,
                "require_fullscreen": False,
                "active": True,
            },
        )
        sec_tech, _ = AssessmentSection.objects.update_or_create(
            section_id="sec_asmt_tech_mixed",
            defaults={
                "assessment": tech_asmt,
                "title": "Technical & Coding",
                "section_type": "Technical",
                "order": 1,
                "duration_minutes": 60,
                "total_marks": 120,
            },
        )
        AssessmentQuestionItem.objects.update_or_create(
            item_id="aqi_tech_1",
            defaults={
                "assessment": tech_asmt,
                "section": sec_tech,
                "question_type": "cs_fundamentals",
                "title": "HTTP Idempotency",
                "slug": "tech-http-idempotency",
                "category": "Backend",
                "difficulty": "Medium",
                "prompt": "Which HTTP method is defined as NOT idempotent when invoked multiple times in REST APIs?",
                "options": [
                    {"id": "a", "text": "GET"},
                    {"id": "b", "text": "PUT"},
                    {"id": "c", "text": "DELETE"},
                    {"id": "d", "text": "POST"},
                ],
                "correct_answers": ["d"],
                "explanation": "Repeated POST calls may create multiple new resources, whereas PUT/DELETE/GET are idempotent.",
                "marks": 20,
                "order": 1,
                "status": "Published",
            },
        )
        AssessmentQuestionItem.objects.update_or_create(
            item_id="aqi_tech_2",
            defaults={
                "assessment": tech_asmt,
                "section": sec_tech,
                "problem": problems_by_id["prob_st_balanced_brackets"],
                "question_type": "coding",
                "title": problems_by_id["prob_st_balanced_brackets"].title,
                "slug": "tech-valid-brackets",
                "category": "Coding",
                "difficulty": "Easy",
                "prompt": problems_by_id["prob_st_balanced_brackets"].description,
                "marks": 100,
                "order": 2,
                "status": "Published",
            },
        )

        # 4. Company-Specific Assessment
        comp_asmt, _ = CodingAssessment.objects.update_or_create(
            assessment_id="asmt_amazon_campus_simulation",
            defaults={
                "title": "Amazon SDE Campus Placement Simulation",
                "slug": "amazon-sde-campus-placement-simulation",
                "assessment_type": "company",
                "category": "Company Mocks",
                "company_tag": "Amazon",
                "description": "Full proctored Amazon Online Assessment (OA) simulation featuring algorithmic coding and CS fundamentals.",
                "difficulty": "Hard",
                "duration_minutes": 90,
                "pass_percentage": 65,
                "total_marks": 270,
                "supported_languages": ["python", "java", "c", "cpp", "javascript"],
                "is_company_mock": True,
                "assignment_mode": "public",
                "show_results_immediately": True,
                "proctoring_enabled": True,
                "require_fullscreen": True,
                "active": True,
            },
        )
        sec_comp, _ = AssessmentSection.objects.update_or_create(
            section_id="sec_asmt_company_amz",
            defaults={
                "assessment": comp_asmt,
                "title": "Amazon OA Coding Round",
                "section_type": "Coding",
                "order": 1,
                "duration_minutes": 90,
                "total_marks": 270,
            },
        )
        AssessmentQuestionItem.objects.update_or_create(
            item_id="aqi_comp_1",
            defaults={
                "assessment": comp_asmt,
                "section": sec_comp,
                "problem": problems_by_id["prob_st_two_sum_count"],
                "question_type": "coding",
                "title": problems_by_id["prob_st_two_sum_count"].title,
                "slug": "comp-two-sum",
                "category": "Coding",
                "difficulty": "Easy",
                "prompt": problems_by_id["prob_st_two_sum_count"].description,
                "marks": 100,
                "order": 1,
                "status": "Published",
            },
        )
        AssessmentQuestionItem.objects.update_or_create(
            item_id="aqi_comp_2",
            defaults={
                "assessment": comp_asmt,
                "section": sec_comp,
                "problem": problems_by_id["prob_st_kadane_max"],
                "question_type": "coding",
                "title": problems_by_id["prob_st_kadane_max"].title,
                "slug": "comp-kadane",
                "category": "Coding",
                "difficulty": "Medium",
                "prompt": problems_by_id["prob_st_kadane_max"].description,
                "marks": 150,
                "order": 2,
                "status": "Published",
            },
        )
        AssessmentQuestionItem.objects.update_or_create(
            item_id="aqi_comp_3",
            defaults={
                "assessment": comp_asmt,
                "section": sec_comp,
                "question_type": "mcq_single",
                "title": "Amazon Work Styles / Complexity",
                "slug": "comp-amortized-complexity",
                "category": "DSA",
                "difficulty": "Medium",
                "prompt": "What is the time complexity of finding the minimum element in a min-heap?",
                "options": [
                    {"id": "a", "text": "O(1)"},
                    {"id": "b", "text": "O(log N)"},
                    {"id": "c", "text": "O(N)"},
                    {"id": "d", "text": "O(N log N)"},
                ],
                "correct_answers": ["a"],
                "marks": 20,
                "order": 3,
                "status": "Published",
            },
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {CodingProblems.objects.count()} problems and {CodingAssessment.objects.count()} assessments."
            )
        )
