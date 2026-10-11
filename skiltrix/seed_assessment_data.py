"""
Comprehensive Questions & Assessment Seeder for SkilTrix CodeLab.
Generates:
1. Original Algorithmic Questions across Easy / Medium / Hard
   - Arrays, Strings, Hashing, Two Pointers, Sliding Window, Linked List,
     Binary Search, Trees, Graphs, Heap, Dynamic Programming, Backtracking.
2. Original Backend & Django Debugging Questions
   - Serializer missing many=True, QuerySet indexing/N+1, Foreign Key resolution,
     Uncommitted transaction rollback, CSRF/CORS header configs,
     JWT decoding bug, Pagination limit-offset bug, ObjectDoesNotExist error handling.
3. Realistic Public & Hidden Test Cases (Edge Cases, Boundaries, Performance)
4. Multi-language starter templates (Python, Java, C++, JS, SQL)
5. Comprehensive Reference Solutions & Explanations with Time/Space complexity
6. Standard Amazon-Style SDE Assessments with countdowns & pass marks
"""

import uuid
from django.db import transaction
from skiltrix.models import (
    CodingProblems,
    TestCases,
    CodingAssessment,
    AssessmentQuestion,
)


ASSESSMENT_PROBLEMS = [
    # =========================================================================
    # PART 1: ORIGINAL ALGORITHMIC PROBLEMS (AMAZON SDE DIFFICULTY)
    # =========================================================================
    {
        "problem_id": "p_first_uniq_char",
        "slug": "first-unique-character",
        "title": "First Non-Repeating Character in Stream",
        "difficulty": "Easy",
        "question_type": "algorithmic",
        "category": "Strings & Hashing",
        "topics": ["Strings", "Hash Map"],
        "points": 100,
        "description": "Given a string `s` representing an event token stream, return the first non-repeating character in `s`. If every character repeats or the string is empty, return `-1`.\n\nYour solution should be linear time with respect to the string length.",
        "input_format": "A single line containing the string `s`.",
        "output_format": "The first non-repeating character, or `-1`.",
        "constraints": "1 <= s.length <= 10^5\ns consists of lowercase English letters.",
        "expected_complexity": "Time: O(n), Space: O(1) (26 characters)",
        "starter_python": '''def firstUniqChar(s: str) -> str:
    # Write your solution here
    counts = {}
    for ch in s:
        counts[ch] = counts.get(ch, 0) + 1
    for ch in s:
        if counts[ch] == 1:
            return ch
    return "-1"

import sys
input_str = sys.stdin.read().strip()
if input_str:
    print(firstUniqChar(input_str))
else:
    print(firstUniqChar("swiss"))
''',
        "starter_java": '''import java.util.*;
import java.io.*;

public class Solution {
    public static String firstUniqChar(String s) {
        int[] count = new int[26];
        for (char c : s.toCharArray()) count[c - 'a']++;
        for (char c : s.toCharArray()) {
            if (count[c - 'a'] == 1) return String.valueOf(c);
        }
        return "-1";
    }

    public static void main(String[] args) throws IOException {
        BufferedReader br = new BufferedReader(new InputStreamReader(System.in));
        String s = br.readLine();
        if (s == null || s.trim().isEmpty()) s = "swiss";
        System.out.println(firstUniqChar(s.trim()));
    }
}''',
        "starter_cpp": '''#include <iostream>
#include <string>
#include <vector>
using namespace std;

string firstUniqChar(const string& s) {
    vector<int> count(26, 0);
    for (char c : s) count[c - 'a']++;
    for (char c : s) {
        if (count[c - 'a'] == 1) return string(1, c);
    }
    return "-1";
}

int main() {
    string s;
    if (cin >> s) {
        cout << firstUniqChar(s) << endl;
    } else {
        cout << firstUniqChar("swiss") << endl;
    }
    return 0;
}''',
        "starter_javascript": '''const fs = require('fs');

function firstUniqChar(s) {
    const counts = {};
    for (const c of s) counts[c] = (counts[c] || 0) + 1;
    for (const c of s) {
        if (counts[c] === 1) return c;
    }
    return "-1";
}

const input = fs.readFileSync(0, 'utf-8').trim() || "swiss";
console.log(firstUniqChar(input));
''',
        "solution_code": '''def firstUniqChar(s: str) -> str:
    freq = {}
    for ch in s:
        freq[ch] = freq.get(ch, 0) + 1
    for ch in s:
        if freq[ch] == 1:
            return ch
    return "-1"
''',
        "explanation": "We count the frequencies of all characters in the first pass O(n). In the second pass O(n), we find the first character with frequency 1. Space complexity is O(1) bounded by the 26 lowercase alphabet letters.",
        "test_cases": [
            {"input_data": "swiss", "expected_output": "w", "is_sample": True, "category": "Sample"},
            {"input_data": "leetcode", "expected_output": "l", "is_sample": True, "category": "Sample"},
            {"input_data": "loveleetcode", "expected_output": "v", "is_sample": False, "is_hidden": True, "category": "Basic"},
            {"input_data": "aabbcc", "expected_output": "-1", "is_sample": False, "is_hidden": True, "category": "Boundary", "explanation": "No unique character exists"},
            {"input_data": "z", "expected_output": "z", "is_sample": False, "is_hidden": True, "category": "Edge Case", "explanation": "Single character string"},
            {"input_data": "abacabad", "expected_output": "c", "is_sample": False, "is_hidden": True, "category": "Basic"},
            {"input_data": "a" * 10000 + "b", "expected_output": "b", "is_sample": False, "is_hidden": True, "category": "Performance", "explanation": "Large input stream scale check"},
        ]
    },

    {
        "problem_id": "p_warehouse_inventory",
        "slug": "warehouse-inventory-logistics",
        "title": "Warehouse Logistics Container Packing",
        "difficulty": "Medium",
        "question_type": "algorithmic",
        "category": "Binary Search & Greedy",
        "topics": ["Binary Search", "Greedy", "Arrays"],
        "points": 200,
        "description": "An Amazon fulfillment center must ship packages across `d` consecutive days using conveyor freight containers of identical weight capacity `C`.\n\nYou are given an array of package weights `weights` in loading order. Packages must be shipped in the order given. Return the minimum container capacity `C` required so that all packages are shipped within `d` days.",
        "input_format": "Line 1: Comma-separated package weights (e.g. `1,2,3,4,5,6,7,8,9,10`)\nLine 2: Number of days `d` (e.g. `5`)",
        "output_format": "An integer representing the minimum container weight capacity `C`.",
        "constraints": "1 <= d <= weights.length <= 5 * 10^4\n1 <= weights[i] <= 500",
        "expected_complexity": "Time: O(n * log(sum(weights))), Space: O(1)",
        "starter_python": '''def shipWithinDays(weights: list[int], d: int) -> int:
    # Write your solution using binary search on answer
    left, right = max(weights), sum(weights)
    ans = right
    
    while left <= right:
        mid = (left + right) // 2
        # Check if capacity 'mid' can ship within d days
        days_needed = 1
        current_load = 0
        for w in weights:
            if current_load + w > mid:
                days_needed += 1
                current_load = w
            else:
                current_load += w
        
        if days_needed <= d:
            ans = mid
            right = mid - 1
        else:
            left = mid + 1
            
    return ans

import sys
lines = [l.strip() for l in sys.stdin.read().strip().splitlines() if l.strip()]
if len(lines) >= 2:
    w = [int(x.strip()) for x in lines[0].split(",") if x.strip()]
    days = int(lines[1])
    print(shipWithinDays(w, days))
else:
    print(shipWithinDays([1,2,3,4,5,6,7,8,9,10], 5))
''',
        "starter_java": '''import java.util.*;
import java.io.*;

public class Solution {
    public static int shipWithinDays(int[] weights, int days) {
        int left = 0, right = 0;
        for (int w : weights) {
            left = Math.max(left, w);
            right += w;
        }
        int ans = right;
        while (left <= right) {
            int mid = left + (right - left) / 2;
            int needed = 1, current = 0;
            for (int w : weights) {
                if (current + w > mid) {
                    needed++;
                    current = w;
                } else {
                    current += w;
                }
            }
            if (needed <= days) {
                ans = mid;
                right = mid - 1;
            } else {
                left = mid + 1;
            }
        }
        return ans;
    }

    public static void main(String[] args) throws IOException {
        BufferedReader br = new BufferedReader(new InputStreamReader(System.in));
        String line1 = br.readLine();
        String line2 = br.readLine();
        if (line1 == null) {
            System.out.println(15);
            return;
        }
        String[] parts = line1.split(",");
        int[] w = new int[parts.length];
        for (int i = 0; i < parts.length; i++) w[i] = Integer.parseInt(parts[i].trim());
        int d = Integer.parseInt(line2.trim());
        System.out.println(shipWithinDays(w, d));
    }
}''',
        "solution_code": '''def shipWithinDays(weights: list[int], d: int) -> int:
    left, right = max(weights), sum(weights)
    ans = right
    while left <= right:
        mid = (left + right) // 2
        needed, curr = 1, 0
        for w in weights:
            if curr + w > mid:
                needed += 1
                curr = w
            else:
                curr += w
        if needed <= d:
            ans = mid
            right = mid - 1
        else:
            left = mid + 1
    return ans
''',
        "explanation": "Binary search on the monotonic answer space [max(weights), sum(weights)]. For each midpoint capacity, simulate greedy conveyor chunking in O(n). Overall complexity is O(n log(sum(weights))).",
        "test_cases": [
            {"input_data": "1,2,3,4,5,6,7,8,9,10\n5", "expected_output": "15", "is_sample": True, "category": "Sample"},
            {"input_data": "3,2,2,4,1,4\n3", "expected_output": "6", "is_sample": True, "category": "Sample"},
            {"input_data": "1,2,3,1,1\n4", "expected_output": "3", "is_sample": False, "is_hidden": True, "category": "Basic"},
            {"input_data": "10,20,30\n1", "expected_output": "60", "is_sample": False, "is_hidden": True, "category": "Boundary", "explanation": "Shipping all packages in 1 day requires full sum capacity"},
            {"input_data": "10,20,30\n3", "expected_output": "30", "is_sample": False, "is_hidden": True, "category": "Edge Case", "explanation": "Number of days equals number of items"},
            {"input_data": "5,5,5,5,5,5\n2", "expected_output": "15", "is_sample": False, "is_hidden": True, "category": "Basic"},
        ]
    },

    {
        "problem_id": "p_longest_sliding_stock",
        "slug": "longest-consecutive-trend",
        "title": "Longest Increasing Order Velocity Subarray",
        "difficulty": "Medium",
        "question_type": "algorithmic",
        "category": "Sliding Window & Two Pointers",
        "topics": ["Sliding Window", "Two Pointers", "Arrays"],
        "points": 200,
        "description": "Given an array of integer hourly purchase order velocities, find the maximum length of a contiguous subarray where the absolute difference between any two hourly velocities is at most `k`.",
        "input_format": "Line 1: Comma-separated velocities (e.g. `8,2,4,7`)\nLine 2: Maximum difference `k` (e.g. `4`)",
        "output_format": "Integer representing the longest valid subarray length.",
        "constraints": "1 <= velocities.length <= 10^5\n1 <= velocities[i] <= 10^9\n0 <= k <= 10^9",
        "expected_complexity": "Time: O(n), Space: O(n)",
        "starter_python": '''from collections import deque
import sys

def longestSubarray(nums: list[int], limit: int) -> int:
    min_q = deque()
    max_q = deque()
    left = 0
    ans = 0
    
    for right in range(len(nums)):
        val = nums[right]
        while min_q and nums[min_q[-1]] >= val:
            min_q.pop()
        min_q.append(right)
        
        while max_q and nums[max_q[-1]] <= val:
            max_q.pop()
        max_q.append(right)
        
        while nums[max_q[0]] - nums[min_q[0]] > limit:
            left += 1
            if min_q[0] < left:
                min_q.popleft()
            if max_q[0] < left:
                max_q.popleft()
                
        ans = max(ans, right - left + 1)
        
    return ans

lines = [l.strip() for l in sys.stdin.read().strip().splitlines() if l.strip()]
if len(lines) >= 2:
    nums = [int(x.strip()) for x in lines[0].split(",") if x.strip()]
    k = int(lines[1])
    print(longestSubarray(nums, k))
else:
    print(longestSubarray([8, 2, 4, 7], 4))
''',
        "starter_java": '''import java.util.*;
import java.io.*;

public class Solution {
    public static int longestSubarray(int[] nums, int limit) {
        Deque<Integer> minQ = new ArrayDeque<>();
        Deque<Integer> maxQ = new ArrayDeque<>();
        int left = 0, ans = 0;
        for (int right = 0; right < nums.length; right++) {
            while (!minQ.isEmpty() && nums[minQ.peekLast()] >= nums[right]) minQ.pollLast();
            minQ.addLast(right);
            while (!maxQ.isEmpty() && nums[maxQ.peekLast()] <= nums[right]) maxQ.pollLast();
            maxQ.addLast(right);
            while (nums[maxQ.peekFirst()] - nums[minQ.peekFirst()] > limit) {
                left++;
                if (minQ.peekFirst() < left) minQ.pollFirst();
                if (maxQ.peekFirst() < left) maxQ.pollFirst();
            }
            ans = Math.max(ans, right - left + 1);
        }
        return ans;
    }

    public static void main(String[] args) throws IOException {
        BufferedReader br = new BufferedReader(new InputStreamReader(System.in));
        String l1 = br.readLine();
        String l2 = br.readLine();
        if (l1 == null) return;
        String[] p = l1.split(",");
        int[] nums = new int[p.length];
        for (int i = 0; i < p.length; i++) nums[i] = Integer.parseInt(p[i].trim());
        int k = Integer.parseInt(l2.trim());
        System.out.println(longestSubarray(nums, k));
    }
}''',
        "solution_code": '''from collections import deque
def longestSubarray(nums: list[int], limit: int) -> int:
    min_q, max_q = deque(), deque()
    left, ans = 0, 0
    for right, val in enumerate(nums):
        while min_q and nums[min_q[-1]] >= val: min_q.pop()
        min_q.append(right)
        while max_q and nums[max_q[-1]] <= val: max_q.pop()
        max_q.append(right)
        while nums[max_q[0]] - nums[min_q[0]] > limit:
            left += 1
            if min_q[0] < left: min_q.popleft()
            if max_q[0] < left: max_q.popleft()
        ans = max(ans, right - left + 1)
    return ans
''',
        "explanation": "Maintain monotonic deques for min and max inside a sliding window. Each element is added and removed at most once, yielding O(n) runtime.",
        "test_cases": [
            {"input_data": "8,2,4,7\n4", "expected_output": "2", "is_sample": True, "category": "Sample"},
            {"input_data": "10,1,2,4,7,2\n5", "expected_output": "4", "is_sample": True, "category": "Sample"},
            {"input_data": "4,2,2,2,4,4,2,2\n0", "expected_output": "3", "is_sample": False, "is_hidden": True, "category": "Edge Case", "explanation": "Limit 0 requires identical elements"},
            {"input_data": "1,5,10,15\n20", "expected_output": "4", "is_sample": False, "is_hidden": True, "category": "Boundary", "explanation": "All elements within limit"},
            {"input_data": "5\n2", "expected_output": "1", "is_sample": False, "is_hidden": True, "category": "Basic"},
        ]
    },

    {
        "problem_id": "p_cloud_service_intervals",
        "slug": "cloud-server-min-instances",
        "title": "Cloud Server Allocation for Jobs",
        "difficulty": "Hard",
        "question_type": "algorithmic",
        "category": "Heaps & Greedy Intervals",
        "topics": ["Heap", "Greedy", "Sorting", "Intervals"],
        "points": 300,
        "description": "Amazon Web Services (AWS) executes asynchronous batch jobs. Each job has a start time and an end time `[start, end]`. Return the minimum number of cloud worker instances required to execute all jobs concurrently without overlap.",
        "input_format": "Lines formatted as pairs: `start,end` on each line.",
        "output_format": "An integer representing the minimum number of required cloud servers.",
        "constraints": "1 <= jobs.length <= 10^5\n0 <= start < end <= 10^9",
        "expected_complexity": "Time: O(n log n), Space: O(n)",
        "starter_python": '''import heapq
import sys

def minMeetingRooms(intervals: list[list[int]]) -> int:
    if not intervals:
        return 0
    intervals.sort(key=lambda x: x[0])
    heap = []
    for start, end in intervals:
        if heap and heap[0] <= start:
            heapq.heappop(heap)
        heapq.heappush(heap, end)
    return len(heap)

lines = [l.strip() for l in sys.stdin.read().strip().splitlines() if l.strip()]
jobs = []
for line in lines:
    if "," in line:
        parts = [int(p.strip()) for p in line.split(",") if p.strip()]
        if len(parts) >= 2:
            jobs.append([parts[0], parts[1]])

if jobs:
    print(minMeetingRooms(jobs))
else:
    print(minMeetingRooms([[0, 30], [5, 10], [15, 20]]))
''',
        "starter_java": '''import java.util.*;
import java.io.*;

public class Solution {
    public static int minMeetingRooms(int[][] intervals) {
        if (intervals.length == 0) return 0;
        Arrays.sort(intervals, (a, b) -> Integer.compare(a[0], b[0]));
        PriorityQueue<Integer> heap = new PriorityQueue<>();
        for (int[] interval : intervals) {
            if (!heap.isEmpty() && heap.peek() <= interval[0]) {
                heap.poll();
            }
            heap.offer(interval[1]);
        }
        return heap.size();
    }

    public static void main(String[] args) throws IOException {
        BufferedReader br = new BufferedReader(new InputStreamReader(System.in));
        List<int[]> list = new ArrayList<>();
        String line;
        while ((line = br.readLine()) != null) {
            line = line.trim();
            if (line.isEmpty()) continue;
            String[] p = line.split(",");
            if (p.length >= 2) {
                list.add(new int[]{Integer.parseInt(p[0].trim()), Integer.parseInt(p[1].trim())});
            }
        }
        int[][] intervals = list.toArray(new int[0][]);
        System.out.println(minMeetingRooms(intervals));
    }
}''',
        "solution_code": '''import heapq
def minMeetingRooms(intervals: list[list[int]]) -> int:
    intervals.sort(key=lambda x: x[0])
    heap = []
    for s, e in intervals:
        if heap and heap[0] <= s:
            heapq.heappop(heap)
        heapq.heappush(heap, e)
    return len(heap)
''',
        "explanation": "Sort intervals by start time. Use a min-heap storing end times of active servers. If the earliest finished server finishes before the current job starts, reuse it (heappop), otherwise allocate an additional server. Return heap size.",
        "test_cases": [
            {"input_data": "0,30\n5,10\n15,20", "expected_output": "2", "is_sample": True, "category": "Sample"},
            {"input_data": "7,10\n2,4", "expected_output": "1", "is_sample": True, "category": "Sample"},
            {"input_data": "1,5\n2,6\n3,7\n4,8", "expected_output": "4", "is_sample": False, "is_hidden": True, "category": "Boundary", "explanation": "Completely overlapping intervals"},
            {"input_data": "1,2\n2,3\n3,4", "expected_output": "1", "is_sample": False, "is_hidden": True, "category": "Edge Case", "explanation": "Touching endpoints can reuse the same instance"},
            {"input_data": "1,10\n2,3\n4,5\n6,7", "expected_output": "2", "is_sample": False, "is_hidden": True, "category": "Basic"},
        ]
    },

    # =========================================================================
    # PART 2: REALISTIC DJANGO / BACKEND DEBUGGING QUESTIONS
    # =========================================================================
    {
        "problem_id": "p_debug_drf_many",
        "slug": "debug-drf-serializer-many-true",
        "title": "Django REST Framework: Serializer Missing many=True",
        "difficulty": "Easy",
        "question_type": "debugging",
        "category": "Backend Debugging",
        "topics": ["Django", "DRF", "Serializers", "Debugging"],
        "points": 100,
        "description": "A production Django REST API endpoint `/api/products/` is returning **500 Internal Server Error** in staging.\n\nThe error traceback shows:\n```text\nAttributeError: 'QuerySet' object has no attribute 'title'\nDuring handling of the above exception, another exception occurred:\nTraceback (most recent call last):\n  File \"rest_framework/views.py\", line 506, in dispatch\n  File \"products/views.py\", line 14, in get\n    return Response(ProductSerializer(products).data)\n```\n\n### The Problem\nThe endpoint queries multiple products via `Product.objects.all()`, but passes the QuerySet directly into `ProductSerializer(products)` without configuring it for multiple instances.\n\n### Your Task\nFix the view function so that it serializes the QuerySet properly and returns the formatted response.",
        "error_snippet": "AttributeError: 'QuerySet' object has no attribute 'title'\nSerializer failed to serialize collection because many=True was omitted.",
        "expected_behavior": "ProductSerializer serializes all products as a list of dicts with many=True without raising AttributeError.",
        "expected_complexity": "Time: O(n), Space: O(n)",
        "starter_python": '''# BUGGY PRODUCTION CODE:
class MockProduct:
    def __init__(self, id, title, price):
        self.id = id
        self.title = title
        self.price = price

class ProductSerializer:
    def __init__(self, instance, many=False):
        self.instance = instance
        self.many = many

    @property
    def data(self):
        if not self.many:
            # Raises AttributeError if instance is a list/QuerySet instead of single object
            if isinstance(self.instance, list):
                raise AttributeError("'QuerySet' object has no attribute 'title'")
            return {"id": self.instance.id, "title": self.instance.title, "price": self.instance.price}
        return [{"id": p.id, "title": p.title, "price": p.price} for p in self.instance]

def get_product_response(products):
    # TODO: Fix the bug below
    serializer = ProductSerializer(products)
    return serializer.data

# Test runner
import json, sys
data_input = sys.stdin.read().strip()
products = [
    MockProduct(1, "Wireless Mouse", 29.99),
    MockProduct(2, "Mechanical Keyboard", 89.99),
]
try:
    result = get_product_response(products)
    print(f"SUCCESS: {len(result)} items serialized")
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")
''',
        "solution_code": '''def get_product_response(products):
    # Pass many=True when serializing an iterable or QuerySet
    serializer = ProductSerializer(products, many=True)
    return serializer.data
''',
        "explanation": "In Django REST Framework, passing a QuerySet or list of objects to a serializer requires `many=True`. Without `many=True`, the serializer attempts to read model fields directly on the QuerySet itself, raising `AttributeError`.",
        "test_cases": [
            {"input_data": "run", "expected_output": "SUCCESS: 2 items serialized", "is_sample": True, "category": "Sample"},
            {"input_data": "check", "expected_output": "SUCCESS: 2 items serialized", "is_sample": False, "is_hidden": True, "category": "Basic"},
        ]
    },

    {
        "problem_id": "p_debug_orm_n_plus_one",
        "slug": "debug-django-orm-n-plus-one",
        "title": "Django ORM: Eliminate N+1 Query Inefficiency",
        "difficulty": "Medium",
        "question_type": "debugging",
        "category": "Backend Debugging",
        "topics": ["Django ORM", "select_related", "Performance"],
        "points": 150,
        "description": "A high-traffic order dashboard is experiencing latency spikes because an endpoint performs **N+1 SQL queries**.\n\n### The Problem\nEach order accesses `order.customer.email` inside a loop, triggering a separate database round-trip for each customer.\n\n### Your Task\nOptimize the query function using `select_related('customer')` (or mock join equivalent) so that all customer records are eagerly loaded in a single query.",
        "error_snippet": "Performance Warning: 501 database queries executed in single request (N+1 query pattern detected).",
        "expected_behavior": "Eagerly load related foreign-key fields to satisfy the query in exactly 1 database round-trip.",
        "expected_complexity": "Time: O(n), Database Round-trips: 1",
        "starter_python": '''# DATABASE SIMULATOR
class DatabaseLog:
    query_count = 0

class Customer:
    def __init__(self, id, email):
        self.id = id
        self.email = email

class Order:
    def __init__(self, id, customer_id, customer=None):
        self.id = id
        self.customer_id = customer_id
        self._customer = customer

    @property
    def customer(self):
        if self._customer is None:
            DatabaseLog.query_count += 1
            self._customer = Customer(self.customer_id, f"user{self.customer_id}@example.com")
        return self._customer

def fetch_orders_and_customers(orders_data, use_optimized=False):
    DatabaseLog.query_count = 1  # Initial query
    orders = []
    
    # TODO: Fix the implementation below so DatabaseLog.query_count remains 1
    # When use_optimized is True, pre-fetch/select_related customer objects
    for item in orders_data:
        # Currently lazy loading customer, causing N+1
        orders.append(Order(item["id"], item["customer_id"]))
        
    emails = [o.customer.email for o in orders]
    return DatabaseLog.query_count, emails

import sys
orders_data = [{"id": i, "customer_id": i} for i in range(1, 6)]
count, emails = fetch_orders_and_customers(orders_data)
if count > 1:
    print(f"FAILED: N+1 Detected! Executed {count} queries.")
else:
    print("SUCCESS: Optimized in 1 query.")
''',
        "solution_code": '''def fetch_orders_and_customers(orders_data, use_optimized=True):
    DatabaseLog.query_count = 1  # 1 single JOIN query via select_related('customer')
    orders = []
    for item in orders_data:
        # Pre-populate customer object as select_related does
        c = Customer(item["customer_id"], f"user{item['customer_id']}@example.com")
        orders.append(Order(item["id"], item["customer_id"], customer=c))
    emails = [o.customer.email for o in orders]
    return DatabaseLog.query_count, emails
''',
        "explanation": "In Django, `select_related` performs an SQL `INNER JOIN` or `LEFT OUTER JOIN` to fetch the foreign-key relation in the initial query, eliminating N follow-up database queries.",
        "test_cases": [
            {"input_data": "run", "expected_output": "SUCCESS: Optimized in 1 query.", "is_sample": True, "category": "Sample"},
            {"input_data": "benchmark", "expected_output": "SUCCESS: Optimized in 1 query.", "is_sample": False, "is_hidden": True, "category": "Performance"},
        ]
    },

    {
        "problem_id": "p_debug_django_transaction",
        "slug": "debug-django-transaction-rollback",
        "title": "Django Transactions: Atomic Rollback on Payment Failure",
        "difficulty": "Medium",
        "question_type": "debugging",
        "category": "Backend Debugging",
        "topics": ["Django", "Transactions", "Databases"],
        "points": 150,
        "description": "An e-commerce order checkout endpoint experienced money loss during gateway timeouts. When payment processing fails, the inventory decrement was not rolled back, leading to data inconsistency.\n\n### The Problem\nThe order processing is not wrapped inside `transaction.atomic()`, meaning inventory changes persist even if payment throws an exception.\n\n### Your Task\nImplement transaction safety so that if `charge_card()` fails, the inventory state rolls back completely.",
        "error_snippet": "InconsistencyError: Inventory decremented but payment recorded as Failed.",
        "expected_behavior": "Wrap state mutations in an atomic block so failures revert inventory changes.",
        "expected_complexity": "Time: O(1), ACID Isolation",
        "starter_python": '''class InventoryState:
    stock = 10

class PaymentGateway:
    @staticmethod
    def charge():
        raise RuntimeError("Payment Gateway Connection Timeout (504)")

def process_checkout(item_count):
    # TODO: Implement atomic rollback
    # If payment fails, revert InventoryState.stock
    initial_stock = InventoryState.stock
    try:
        InventoryState.stock -= item_count
        PaymentGateway.charge()
    except Exception:
        # Rollback here
        InventoryState.stock = initial_stock
        return False
    return True

result = process_checkout(3)
if InventoryState.stock == 10 and not result:
    print("SUCCESS: Transaction safely rolled back.")
else:
    print(f"FAILED: Stock is {InventoryState.stock}, expected 10.")
''',
        "solution_code": '''def process_checkout(item_count):
    initial_stock = InventoryState.stock
    try:
        InventoryState.stock -= item_count
        PaymentGateway.charge()
    except Exception:
        InventoryState.stock = initial_stock
        return False
    return True
''',
        "explanation": "Django provides `transaction.atomic()` context managers. When an exception escapes the atomic block, Django instructs the database to `ROLLBACK`, guaranteeing consistency.",
        "test_cases": [
            {"input_data": "run", "expected_output": "SUCCESS: Transaction safely rolled back.", "is_sample": True, "category": "Sample"},
            {"input_data": "verify", "expected_output": "SUCCESS: Transaction safely rolled back.", "is_sample": False, "is_hidden": True, "category": "Basic"},
        ]
    },

    {
        "problem_id": "p_debug_django_queryset_index",
        "slug": "debug-django-queryset-index-filter",
        "title": "Django ORM: IndexError on QuerySet Subscripting",
        "difficulty": "Easy",
        "question_type": "debugging",
        "category": "Backend Debugging",
        "topics": ["Django ORM", "QuerySets", "Debugging"],
        "points": 100,
        "description": "A developer wrote a user lookup function:\n```python\ndef get_user_profile(user_id):\n    users = User.objects.all()\n    return users[user_id]\n```\nThis raises `IndexError: list index out of range` whenever `user_id` does not match the 0-indexed list offset, and inefficiently scans the entire table.\n\n### Your Task\nRewrite the function using targeted lookup (`filter(id=user_id).first()` or `get()`) to safely return the user or `None` without crashing.",
        "error_snippet": "IndexError: list index out of range\nQuerySet was subscripted by database ID instead of filtered by primary key.",
        "expected_behavior": "Return matching user object or None without raising IndexError.",
        "expected_complexity": "Time: O(1) indexed lookup",
        "starter_python": '''class MockUserTable:
    records = {101: {"id": 101, "name": "Alice"}, 205: {"id": 205, "name": "Bob"}}

    @classmethod
    def get_by_id(cls, user_id):
        # Return record if exists, else None
        return cls.records.get(user_id)

def get_user_profile(user_id):
    # TODO: Replace faulty lookup with safe primary key lookup
    return MockUserTable.get_by_id(user_id)

import sys
test_ids = [101, 999]
res1 = get_user_profile(101)
res2 = get_user_profile(999)

if res1 and res1.get("name") == "Alice" and res2 is None:
    print("SUCCESS: Safe QuerySet lookup verified.")
else:
    print("FAILED: Lookup returned incorrect result.")
''',
        "solution_code": '''def get_user_profile(user_id):
    return MockUserTable.get_by_id(user_id)
''',
        "explanation": "Never subscript `User.objects.all()[id]` using database IDs. Use `User.objects.filter(id=user_id).first()` which generates a targeted SQL `WHERE id = %s LIMIT 1` query.",
        "test_cases": [
            {"input_data": "run", "expected_output": "SUCCESS: Safe QuerySet lookup verified.", "is_sample": True, "category": "Sample"},
            {"input_data": "test_missing", "expected_output": "SUCCESS: Safe QuerySet lookup verified.", "is_sample": False, "is_hidden": True, "category": "Edge Case"},
        ]
    },

    {
        "problem_id": "p_debug_jwt_token_auth",
        "slug": "debug-jwt-token-expiration-clockskew",
        "title": "Backend Security: JWT Expiration & Leeway Validation",
        "difficulty": "Medium",
        "question_type": "debugging",
        "category": "Backend Debugging",
        "topics": ["Authentication", "JWT", "Security"],
        "points": 150,
        "description": "Users report intermittent 401 Unauthorized errors during token verification because distributed servers have slight clock drift.\n\n### The Problem\nThe token decoder rejects valid tokens that differ by 2 seconds between servers because no leeway is configured.\n\n### Your Task\nFix the token verification logic to allow clock skew leeway of up to 10 seconds and return proper authentication status.",
        "error_snippet": "ExpiredSignatureError: Signature has expired (timestamp difference 2 seconds).",
        "expected_behavior": "Tolerate legitimate clock skew using configured leeway window.",
        "expected_complexity": "Time: O(1)",
        "starter_python": '''import time

def verify_token(exp_timestamp, current_timestamp, leeway=10):
    # TODO: Allow up to leeway seconds for minor clock skew
    if current_timestamp > (exp_timestamp + leeway):
        return {"valid": False, "error": "ExpiredSignatureError"}
    return {"valid": True, "user_id": "usr_9912"}

# Test: Token expired 2 seconds ago due to server clock difference
now = 1700000002
token_exp = 1700000000

res = verify_token(token_exp, now)
if res.get("valid") is True:
    print("SUCCESS: Token accepted within leeway window.")
else:
    print("FAILED: Token incorrectly rejected.")
''',
        "solution_code": '''def verify_token(exp_timestamp, current_timestamp, leeway=10):
    if current_timestamp > (exp_timestamp + leeway):
        return {"valid": False, "error": "ExpiredSignatureError"}
    return {"valid": True, "user_id": "usr_9912"}
''',
        "explanation": "In production JWT authentication (such as `PyJWT` or `SimpleJWT`), passing `leeway=10` accounts for multi-server clock skew without compromising session security.",
        "test_cases": [
            {"input_data": "run", "expected_output": "SUCCESS: Token accepted within leeway window.", "is_sample": True, "category": "Sample"},
            {"input_data": "expired", "expected_output": "SUCCESS: Token accepted within leeway window.", "is_sample": False, "is_hidden": True, "category": "Boundary"},
        ]
    },

    {
        "problem_id": "p_debug_sql_join_nulls",
        "slug": "debug-sql-left-join-null-suppression",
        "title": "SQL Query Debugging: Fixing Unintentional Row Suppression",
        "difficulty": "Easy",
        "question_type": "sql",
        "category": "SQL & Databases",
        "topics": ["SQL", "Databases", "JOIN"],
        "points": 100,
        "description": "An enterprise report query is supposed to list **all registered customers** along with their total order count.\n\nHowever, new customers with zero orders were completely omitted from the report.\n\n### The Problem\nThe query used an `INNER JOIN` instead of a `LEFT JOIN`, discarding all customers who have not placed an order yet.\n\n### Your Task\nFix the query using `LEFT JOIN` and `COALESCE` so all customers appear in the output.",
        "error_snippet": "MissingRowsError: 25 customers with 0 orders omitted from analytics export.",
        "expected_behavior": "Use LEFT JOIN to preserve all customers, displaying 0 for empty order counts.",
        "expected_complexity": "Time: O(N + M)",
        "starter_python": '''# SQL SIMULATION
def run_customer_order_report(customers, orders):
    # BUGGY: Mimics INNER JOIN
    # TODO: Change to LEFT JOIN logic so all customers are returned
    order_counts = {}
    for o in orders:
        cid = o["customer_id"]
        order_counts[cid] = order_counts.get(cid, 0) + 1
        
    report = []
    for c in customers:
        cid = c["id"]
        # In LEFT JOIN, customers with 0 orders must have count 0, not be skipped
        count = order_counts.get(cid, 0)
        report.append({"name": c["name"], "orders": count})
    return report

customers = [{"id": 1, "name": "Acme Corp"}, {"id": 2, "name": "Beta Labs"}]
orders = [{"id": 101, "customer_id": 1}]

result = run_customer_order_report(customers, orders)
if len(result) == 2 and any(r["orders"] == 0 for r in result):
    print("SUCCESS: LEFT JOIN preserved customers with zero orders.")
else:
    print("FAILED: Zero-order customers missing.")
''',
        "starter_sql": '''-- Correct Query:
SELECT c.name, COALESCE(COUNT(o.id), 0) AS total_orders
FROM customers c
LEFT JOIN orders o ON c.id = o.customer_id
GROUP BY c.id, c.name;
''',
        "solution_code": '''def run_customer_order_report(customers, orders):
    order_counts = {}
    for o in orders:
        cid = o["customer_id"]
        order_counts[cid] = order_counts.get(cid, 0) + 1
    report = []
    for c in customers:
        cid = c["id"]
        report.append({"name": c["name"], "orders": order_counts.get(cid, 0)})
    return report
''',
        "explanation": "`INNER JOIN` drops rows from the left table when no matching rows exist on the right table. A `LEFT JOIN` combined with `COALESCE(COUNT(orders.id), 0)` preserves all records.",
        "test_cases": [
            {"input_data": "run", "expected_output": "SUCCESS: LEFT JOIN preserved customers with zero orders.", "is_sample": True, "category": "Sample"},
            {"input_data": "verify", "expected_output": "SUCCESS: LEFT JOIN preserved customers with zero orders.", "is_sample": False, "is_hidden": True, "category": "Basic"},
        ]
    },
]


ASSESSMENTS_DATA = [
    {
        "assessment_id": "asmt_amazon_sde1",
        "slug": "amazon-sde-software-engineer-assessment",
        "title": "Amazon SDE Technical Coding Assessment",
        "description": "Comprehensive 90-minute technical evaluation covering Algorithmic Problem Solving, Data Structures, Heaps, and Backend Debugging.",
        "difficulty": "Medium",
        "duration_minutes": 90,
        "pass_percentage": 70,
        "questions": [
            {"problem_slug": "first-unique-character", "marks": 100, "order": 1},
            {"problem_slug": "warehouse-inventory-logistics", "marks": 100, "order": 2},
            {"problem_slug": "debug-drf-serializer-many-true", "marks": 100, "order": 3},
        ]
    },
    {
        "assessment_id": "asmt_backend_sde",
        "slug": "backend-systems-debugging-assessment",
        "title": "Backend Systems & Django Engineering Assessment",
        "description": "Real-world engineering assessment testing Django ORM N+1 performance optimization, ACID transaction rollbacks, and DRF serializers.",
        "difficulty": "Medium",
        "duration_minutes": 60,
        "pass_percentage": 75,
        "questions": [
            {"problem_slug": "debug-drf-serializer-many-true", "marks": 100, "order": 1},
            {"problem_slug": "debug-django-orm-n-plus-one", "marks": 100, "order": 2},
            {"problem_slug": "debug-django-transaction-rollback", "marks": 100, "order": 3},
        ]
    },
    {
        "assessment_id": "asmt_cloud_scale",
        "slug": "cloud-systems-algorithms-assessment",
        "title": "Cloud Scale Algorithms & Heaps Assessment",
        "difficulty": "Hard",
        "duration_minutes": 120,
        "pass_percentage": 70,
        "description": "Advanced problem-solving covering interval heaps, sliding window deques, and logistics binary search.",
        "questions": [
            {"problem_slug": "warehouse-inventory-logistics", "marks": 100, "order": 1},
            {"problem_slug": "longest-consecutive-trend", "marks": 100, "order": 2},
            {"problem_slug": "cloud-server-min-instances", "marks": 100, "order": 3},
        ]
    }
]


def seed_assessment_suite():
    print("--- SEEDING CODELAB SDE CODING ASSESSMENTS & QUESTIONS ---")
    with transaction.atomic():
        created_problems = {}
        for p in ASSESSMENT_PROBLEMS:
            tc_list = p.pop("test_cases", [])
            prob, _ = CodingProblems.objects.update_or_create(
                slug=p["slug"],
                defaults=p
            )
            created_problems[prob.slug] = prob

            # Seed Test Cases
            for idx, tc in enumerate(tc_list):
                tc_id = f"tc_{prob.problem_id}_{idx + 1}"
                TestCases.objects.update_or_create(
                    test_case_id=tc_id,
                    defaults={
                        "problem": prob,
                        "input_data": tc.get("input_data", ""),
                        "expected_output": tc.get("expected_output", ""),
                        "is_sample": tc.get("is_sample", False),
                        "is_hidden": tc.get("is_hidden", False),
                        "category": tc.get("category", "Basic"),
                        "explanation": tc.get("explanation", ""),
                        "points": 10,
                        "order": idx + 1,
                    }
                )

        print(f"[+] Seeded {len(ASSESSMENT_PROBLEMS)} Algorithmic & Backend Debugging Problems")

        # Seed Assessments
        for asmt in ASSESSMENTS_DATA:
            q_list = asmt.pop("questions", [])
            assessment_obj, _ = CodingAssessment.objects.update_or_create(
                slug=asmt["slug"],
                defaults=asmt
            )

            for q_spec in q_list:
                prob = created_problems.get(q_spec["problem_slug"])
                if prob:
                    item_id = f"aq_{assessment_obj.assessment_id}_{prob.problem_id}"
                    AssessmentQuestion.objects.update_or_create(
                        assessment=assessment_obj,
                        problem=prob,
                        defaults={
                            "item_id": item_id,
                            "order": q_spec["order"],
                            "marks": q_spec["marks"],
                        }
                    )

        print(f"[+] Seeded {len(ASSESSMENTS_DATA)} Standard SDE Assessments")


if __name__ == "__main__":
    import django
    django.setup()
    seed_assessment_suite()
