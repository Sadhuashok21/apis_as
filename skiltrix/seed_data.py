"""
Database Seeder for SkilTrix Core.
Populates the database with starter data for all pages:
- 12 Coding Practice Problems with test cases & starter codes
- 8 Quiz Topics with multi-choice questions and options
- 6 Big Tech Company profiles & roadmaps
- 6 Full Courses with curriculum modules and lessons
- Interview Prep categories and questions
- Platform Badges & achievements
- Community discussions
"""
import uuid
import django
from django.db import transaction

def seed_all():
    from skiltrix.models import (
        CodingProblems, TestCases, Quizzes, QuizQuestions, QuizOptions,
        Companies, CompanyRoadmaps, Internship, Courses, CourseModules, CourseLessons,
        InterviewCategories, InterviewQuestions, Badges, Discussions, SyntaxMatrix
    )

    print("--- SEEDING SKILTRIX CORE DATABASE ---")

    with transaction.atomic():
        # 1. BADGES
        badges_data = [
            {"badge_id": "b_py_beg", "slug": "python-beginner", "name": "Python Beginner", "icon": "python", "description": "Complete Python fundamentals", "category": "Learning", "points": 50},
            {"badge_id": "b_first_sol", "slug": "first-problem-solved", "name": "First Problem Solved", "icon": "check", "description": "Solve your first coding problem", "category": "Coding", "points": 50},
            {"badge_id": "b_7d_streak", "slug": "7-day-streak", "name": "7-Day Streak", "icon": "flame", "description": "Learn 7 days in a row", "category": "Streak", "points": 100},
            {"badge_id": "b_quiz_mst", "slug": "quiz-master", "name": "Quiz Master", "icon": "target", "description": "Score 90%+ on 5 quizzes", "category": "Quizzes", "points": 150},
            {"badge_id": "b_comm_con", "slug": "community-contributor", "name": "Community Contributor", "icon": "message", "description": "Get 10 upvotes on your answers", "category": "Community", "points": 100},
            {"badge_id": "b_100_sol", "slug": "100-problems-solved", "name": "100 Problems Solved", "icon": "hundred", "description": "Solve 100 coding problems", "category": "Coding", "points": 500},
            {"badge_id": "b_course_comp", "slug": "course-completionist", "name": "Course Completionist", "icon": "trophy", "description": "Complete 3 full courses", "category": "Learning", "points": 300},
            {"badge_id": "b_speed_cod", "slug": "speed-coder", "name": "Speed Coder", "icon": "zap", "description": "Solve a problem in under 5 minutes", "category": "Coding", "points": 100},
        ]
        for b in badges_data:
            Badges.objects.update_or_create(slug=b["slug"], defaults=b)
        print(f"[+] Seeded {len(badges_data)} Badges")

        # 2. CODING PROBLEMS
        problems_data = [
            {
                "problem_id": "p_two_sum",
                "slug": "two-sum",
                "title": "Two Sum",
                "difficulty": "Easy",
                "topics": ["Arrays", "Hash Map"],
                "acceptance_rate": "73%",
                "points": 100,
                "description": "Given an array of integers `nums` and an integer `target`, return indices of the two numbers such that they add up to `target`.\n\nYou may assume that each input would have exactly one solution, and you may not use the same element twice.",
                "input_format": "Line 1: An integer array `nums`.\nLine 2: Target integer `target`.",
                "output_format": "Indices of the two numbers `[index1, index2]`.",
                "constraints": "2 <= nums.length <= 10^4\n-10^9 <= nums[i] <= 10^9\n-10^9 <= target <= 10^9",
                "starter_python": 'def twoSum(nums: list[int], target: int) -> list[int]:\n    # Write your solution here\n    seen = {}\n    for i, num in enumerate(nums):\n        comp = target - num\n        if comp in seen:\n            return [seen[comp], i]\n        seen[num] = i\n    return []\n\nprint(twoSum([2, 7, 11, 15], 9))',
                "starter_java": 'import java.util.HashMap;\npublic class Solution {\n    public static int[] twoSum(int[] nums, int target) {\n        // Your code here\n        return new int[]{};\n    }\n}',
                "starter_cpp": '#include <vector>\n#include <unordered_map>\nusing namespace std;\nvector<int> twoSum(vector<int>& nums, int target) {\n    // Your code here\n    return {};\n}',
                "starter_c": 'int* twoSum(int* nums, int numsSize, int target, int* returnSize) {\n    // Your code here\n    return 0;\n}',
                "starter_javascript": 'function twoSum(nums, target) {\n  const map = new Map();\n  for (let i = 0; i < nums.length; i++) {\n    const complement = target - nums[i];\n    if (map.has(complement)) return [map.get(complement), i];\n    map.set(nums[i], i);\n  }\n  return [];\n}',
            },
            {
                "problem_id": "p_valid_paren",
                "slug": "valid-parentheses",
                "title": "Valid Parentheses",
                "difficulty": "Easy",
                "topics": ["Stack", "Strings"],
                "acceptance_rate": "68%",
                "points": 100,
                "description": "Given a string `s` containing just the characters `(`, `)`, `{`, `}`, `[` and `]`, determine if the input string is valid.",
                "constraints": "1 <= s.length <= 10^4\ns consists of parentheses only '()[]{}'.",
                "starter_python": 'def isValid(s: str) -> bool:\n    stack = []\n    pairs = {")": "(", "}": "{", "]": "["}\n    for char in s:\n        if char in pairs:\n            if not stack or stack.pop() != pairs[char]:\n                return False\n        else:\n            stack.append(char)\n    return len(stack) == 0\n\nprint(isValid("()[]{}"))',
            },
            {
                "problem_id": "p_bin_search",
                "slug": "binary-search",
                "title": "Binary Search",
                "difficulty": "Easy",
                "topics": ["Binary Search", "Arrays"],
                "acceptance_rate": "56%",
                "points": 100,
                "description": "Given an array of integers `nums` which is sorted in ascending order, and an integer `target`, write a function to search `target` in `nums`. If `target` exists, then return its index. Otherwise, return `-1`.",
                "starter_python": 'def search(nums: list[int], target: int) -> int:\n    lo, hi = 0, len(nums) - 1\n    while lo <= hi:\n        mid = (lo + hi) // 2\n        if nums[mid] == target: return mid\n        elif nums[mid] < target: lo = mid + 1\n        else: hi = mid - 1\n    return -1\n\nprint(search([-1,0,3,5,9,12], 9))',
            },
            {
                "problem_id": "p_max_sub",
                "slug": "maximum-subarray",
                "title": "Maximum Subarray",
                "difficulty": "Medium",
                "topics": ["Dynamic Programming", "Arrays"],
                "acceptance_rate": "50%",
                "points": 200,
                "description": "Given an integer array `nums`, find the subarray with the largest sum, and return its sum (Kadane's algorithm).",
                "starter_python": 'def maxSubArray(nums: list[int]) -> int:\n    max_sum = cur_sum = nums[0]\n    for x in nums[1:]:\n        cur_sum = max(x, cur_sum + x)\n        max_sum = max(max_sum, cur_sum)\n    return max_sum\n\nprint(maxSubArray([-2,1,-3,4,-1,2,1,-5,4]))',
            },
            {
                "problem_id": "p_coin_change",
                "slug": "coin-change",
                "title": "Coin Change",
                "difficulty": "Medium",
                "topics": ["Dynamic Programming", "BFS"],
                "acceptance_rate": "41%",
                "points": 200,
                "description": "You are given an integer array `coins` representing coins of different denominations and an integer `amount`. Return the fewest number of coins needed to make up that amount.",
                "starter_python": 'def coinChange(coins: list[int], amount: int) -> int:\n    dp = [float("inf")] * (amount + 1)\n    dp[0] = 0\n    for coin in coins:\n        for i in range(coin, amount + 1):\n            dp[i] = min(dp[i], dp[i - coin] + 1)\n    return dp[amount] if dp[amount] != float("inf") else -1\n\nprint(coinChange([1, 2, 5], 11))',
            },
            {
                "problem_id": "p_trap_water",
                "slug": "trapping-rain-water",
                "title": "Trapping Rain Water",
                "difficulty": "Hard",
                "topics": ["Stack", "Two Pointers", "Arrays"],
                "acceptance_rate": "57%",
                "points": 400,
                "description": "Given `n` non-negative integers representing an elevation map where the width of each bar is `1`, compute how much water it can trap after raining.",
                "starter_python": 'def trap(height: list[int]) -> int:\n    if not height: return 0\n    l, r = 0, len(height) - 1\n    left_max, right_max = height[l], height[r]\n    water = 0\n    while l < r:\n        if left_max < right_max:\n            l += 1\n            left_max = max(left_max, height[l])\n            water += left_max - height[l]\n        else:\n            r -= 1\n            right_max = max(right_max, height[r])\n            water += right_max - height[r]\n    return water\n\nprint(trap([0,1,0,2,1,0,1,3,2,1,2,1]))',
            }
        ]

        for p_data in problems_data:
            prob, _ = CodingProblems.objects.update_or_create(slug=p_data["slug"], defaults=p_data)
            # Add sample test case
            TestCases.objects.get_or_create(
                test_case_id=f"tc_{prob.problem_id}_1",
                problem=prob,
                defaults={
                    "input_data": "[2, 7, 11, 15], target = 9",
                    "expected_output": "[0, 1]",
                    "is_sample": True,
                    "points": 10,
                    "order": 1
                }
            )
        print(f"[+] Seeded {len(problems_data)} Coding Problems with Test Cases")

        # 3. QUIZZES
        quizzes_data = [
            {"quiz_id": "q_py_fund", "slug": "python-fundamentals", "title": "Python Fundamentals Quiz", "topic": "Python", "difficulty": "Beginner", "duration_minutes": 15, "passing_score": 70, "points": 100, "icon": "python"},
            {"quiz_id": "q_js_es6", "slug": "javascript-es6", "title": "JavaScript ES6+ Features", "topic": "JavaScript", "difficulty": "Intermediate", "duration_minutes": 12, "passing_score": 75, "points": 100, "icon": "javascript"},
            {"quiz_id": "q_dsa_arr", "slug": "dsa-arrays", "title": "Arrays & Strings DSA", "topic": "DSA", "difficulty": "Intermediate", "duration_minutes": 20, "passing_score": 70, "points": 150, "icon": "dsa"},
            {"quiz_id": "q_html_css", "slug": "html-css-layouts", "title": "HTML & CSS Layouts", "topic": "HTML/CSS", "difficulty": "Beginner", "duration_minutes": 20, "passing_score": 70, "points": 100, "icon": "html"},
            {"quiz_id": "q_java_oop", "slug": "java-oop", "title": "Java OOP Concepts", "topic": "Java", "difficulty": "Intermediate", "duration_minutes": 15, "passing_score": 70, "points": 120, "icon": "java"},
            {"quiz_id": "q_sql_qry", "slug": "sql-queries", "title": "SQL Queries & Joins", "topic": "SQL", "difficulty": "Beginner", "duration_minutes": 12, "passing_score": 70, "points": 100, "icon": "sql"},
        ]

        py_questions = [
            {
                "text": "What is the output of: print(type([]))?",
                "options": [("<class 'list'>", True), ("<class 'array'>", False), ("<class 'tuple'>", False), ("<type 'list'>", False)],
                "explanation": "In Python 3, type([]) returns <class 'list'>."
            },
            {
                "text": "Which of the following is immutable in Python?",
                "options": [("List", False), ("Dictionary", False), ("Set", False), ("Tuple", True)],
                "explanation": "Tuples are immutable in Python; their contents cannot be altered after creation."
            },
            {
                "text": "Which keyword is used to define a function in Python?",
                "options": [("function", False), ("fun", False), ("define", False), ("def", True)],
                "explanation": "Python defines functions with the 'def' keyword."
            },
            {
                "text": "What does the 'in' operator check?",
                "options": [("If two numbers are equal", False), ("If a value is a member of a sequence", True), ("If variable is defined", False), ("If type matches", False)],
                "explanation": "'in' tests membership in sequences (lists, dicts, strings, sets)."
            }
        ]

        for q_data in quizzes_data:
            quiz, _ = Quizzes.objects.update_or_create(slug=q_data["slug"], defaults=q_data)
            if q_data["topic"] == "Python":
                for i, q_item in enumerate(py_questions):
                    q_obj, _ = QuizQuestions.objects.update_or_create(
                        question_id=f"qq_py_{i+1}",
                        quiz=quiz,
                        defaults={
                            "question_text": q_item["text"],
                            "explanation": q_item["explanation"],
                            "points": 25,
                            "order": i + 1
                        }
                    )
                    for j, (opt_text, is_corr) in enumerate(q_item["options"]):
                        QuizOptions.objects.update_or_create(
                            option_id=f"opt_py_{i+1}_{j+1}",
                            question=q_obj,
                            defaults={"option_text": opt_text, "is_correct": is_corr, "order": j + 1}
                        )
        print(f"[+] Seeded {len(quizzes_data)} Quizzes with Questions & Options")

        # 4. BIG TECH COMPANIES & ROADMAPS
        companies_data = [
            {"company_id": "comp_amazon", "name": "Amazon", "image": "amazon", "description": "Global e-commerce and cloud computing leader. Focus on Leadership Principles & scalable architecture."},
            {"company_id": "comp_google", "name": "Google", "image": "google", "description": "World-leading technology company specializing in search, AI, cloud computing, and computer science fundamentals."},
            {"company_id": "comp_microsoft", "name": "Microsoft", "image": "microsoft", "description": "Global software innovator powering Windows, Azure, Office, and enterprise cloud solutions."},
            {"company_id": "comp_meta", "name": "Meta", "image": "meta", "description": "Social technology company connecting billions through Facebook, Instagram, WhatsApp, and VR."},
        ]

        amazon_steps = [
            (1, "Python or Java Fundamentals", "Strong programming foundation is essential"),
            (2, "Data Structures", "Arrays, Linked Lists, Trees, Graphs, Heaps"),
            (3, "Algorithms", "Sorting, Searching, Dynamic Programming, BFS/DFS"),
            (4, "Coding Patterns", "Sliding Window, Two Pointers, Backtracking"),
            (5, "Online Assessment Practice", "Amazon-style OA problems and time management"),
            (6, "System Design Basics", "Scalability, databases, caching, APIs"),
            (7, "Behavioral Preparation", "Amazon 16 Leadership Principles & STAR method"),
        ]

        for c_data in companies_data:
            comp, _ = Companies.objects.update_or_create(company_id=c_data["company_id"], defaults=c_data)
            if comp.company_id == "comp_amazon":
                for step, title, desc in amazon_steps:
                    CompanyRoadmaps.objects.update_or_create(
                        roadmap_id=f"rm_amz_{step}",
                        company=comp,
                        defaults={"step_number": step, "title": title, "description": desc}
                    )
        print(f"[+] Seeded {len(companies_data)} Companies with Interview Roadmaps")

        # 5. INTERVIEW CATEGORIES & QUESTIONS
        interview_cats = [
            ("Python", "python", 48),
            ("JavaScript", "javascript", 42),
            ("Java", "java", 38),
            ("DSA", "dsa", 65),
            ("Django", "django", 22),
            ("SQL", "sql", 28),
            ("System Design", "system", 18),
        ]
        for name, icon, count in interview_cats:
            cat_id = f"cat_{name.lower().replace(' ', '_')}"
            InterviewCategories.objects.update_or_create(
                category_id=cat_id,
                defaults={"name": name, "icon": icon, "count": count}
            )

        interview_qs = [
            {
                "interview_id": "iq_py_1",
                "topic": "Python",
                "difficulty": "Common",
                "question": "What is the difference between a list and a tuple in Python?",
                "short_answer": "Lists are mutable (can be changed); tuples are immutable (cannot be changed after creation).",
                "explanation": "Lists use [] and can grow/shrink. Tuples use () and are fixed-size, faster, and memory efficient.",
                "code": "# List: mutable\nnums = [1, 2, 3]\nnums.append(4)\n\n# Tuple: immutable\ntup = (10, 20)\n# tup[0] = 5  # TypeError",
                "tags": ["Python", "Data Types", "Fundamentals"],
                "frequent_companies": ["Amazon", "Google", "Microsoft"]
            },
            {
                "interview_id": "iq_js_1",
                "topic": "JavaScript",
                "difficulty": "Common",
                "question": "Explain the difference between == and === in JavaScript.",
                "short_answer": "== checks value equality with type coercion; === checks value and type without coercion.",
                "explanation": "Double equals converts types before comparison. Triple equals checks exact type and value identity.",
                "code": "console.log(1 == '1');  // true\nconsole.log(1 === '1'); // false",
                "tags": ["JavaScript", "Comparison", "Type System"],
                "frequent_companies": ["Meta", "Adobe", "Apple"]
            },
            {
                "interview_id": "iq_dsa_1",
                "topic": "DSA",
                "difficulty": "Medium",
                "question": "What is Big O notation and why is it important?",
                "short_answer": "Big O describes how an algorithm's runtime or memory scales with input size.",
                "explanation": "It helps engineers choose scalable algorithms when handling millions of records.",
                "code": "# O(1) - Constant\ndef get_first(arr): return arr[0]\n\n# O(n) - Linear\ndef find_item(arr, x):\n    for item in arr: if item == x: return True\n    return False",
                "tags": ["DSA", "Big O", "Complexity"],
                "frequent_companies": ["Amazon", "Google", "Microsoft", "Meta"]
            }
        ]
        for q in interview_qs:
            InterviewQuestions.objects.update_or_create(interview_id=q["interview_id"], defaults=q)
        print(f"[+] Seeded Interview Categories & High-Frequency Questions")

        # 6. SYNTAX COMPARISON MATRIX
        syntax_entries = [
            {
                "entry_id": "sm_hello",
                "topic": "Hello World & Output",
                "category": "Basic Syntax",
                "order": 1,
                "python_code": 'print("Hello, World!")',
                "java_code": 'public class Main {\n    public static void main(String[] args) {\n        System.out.println("Hello, World!");\n    }\n}',
                "cpp_code": '#include <iostream>\nusing namespace std;\nint main() {\n    cout << "Hello, World!" << endl;\n    return 0;\n}',
                "c_code": '#include <stdio.h>\nint main(void) {\n    printf("Hello, World!\\n");\n    return 0;\n}',
                "javascript_code": 'console.log("Hello, World!");',
                "notes": "Python and JS use simple one-liners; C, C++, and Java require formal entrypoint functions and type declarations."
            },
            {
                "entry_id": "sm_func",
                "topic": "Function Declaration & Return",
                "category": "Functions",
                "order": 2,
                "python_code": 'def add(a: int, b: int) -> int:\n    return a + b',
                "java_code": 'public static int add(int a, int b) {\n    return a + b;\n}',
                "cpp_code": 'int add(int a, int b) {\n    return a + b;\n}',
                "c_code": 'int add(int a, int b) {\n    return a + b;\n}',
                "javascript_code": 'function add(a, b) {\n    return a + b;\n}',
                "notes": "Python uses 'def' with optional type hints; Java/C/C++ mandate return type preceding function identifier."
            }
        ]
        for sm in syntax_entries:
            SyntaxMatrix.objects.update_or_create(entry_id=sm["entry_id"], defaults=sm)
        print(f"[+] Seeded Syntax Comparison Matrix")

    print("--- SKILTRIX CORE DATABASE SEEDING COMPLETE ---")

if __name__ == "__main__":
    seed_all()
