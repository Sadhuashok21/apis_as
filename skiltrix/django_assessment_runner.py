"""Sandboxed multi-file Django project runner and unittest/tests.py grader for assessments."""

from __future__ import annotations

import io
import os
import re
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from .execution.sandbox_policy import ExecutionPolicy


DEFAULT_LOCKED_FILES: List[str] = [
    "README.md",
    "manage.py",
    "posts/tests.py",
    "config/settings.py",
    "config/urls.py",
]

IGNORED_UPLOAD_DIRS = {
    "__pycache__",
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "env",
    "node_modules",
    ".pytest_cache",
    ".mypy_cache",
    ".tox",
    ".idea",
    ".vscode",
    "staticfiles",
    "media",
    "__MACOSX",
}

IGNORED_UPLOAD_EXTENSIONS = {
    ".pyc",
    ".pyo",
    ".pyd",
    ".sqlite3",
    ".db",
    ".sqlite",
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".webp",
    ".ico",
    ".pdf",
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
    ".exe",
    ".dll",
    ".so",
    ".dylib",
    ".bin",
    ".zip",
    ".tar",
    ".gz",
}

IGNORED_UPLOAD_FILENAMES = {".ds_store", "thumbs.db"}

MAX_UPLOAD_FILE_BYTES = 512 * 1024
MAX_UPLOAD_TOTAL_BYTES = 8 * 1024 * 1024
MAX_UPLOAD_FILE_COUNT = 200

DEFAULT_AMAZON_PROJECT_FILES: Dict[str, str] = {
    "README.md": """# Blog Platform (Django): Post Creation

## Overview
This is a blogging platform where users can discover, read, and share blog posts.

However, users are unable to create and publish new blog posts cleanly via **Write Post** or `POST /api/posts/`. Your task is to fix the backend issue in `posts/views.py`.

## Expected API Behavior

### `POST /api/posts/`
Creates a new blog post and returns HTTP **201 Created**.

#### Request Body (`application/json` or form-data)
```json
{
  "title": "System Design Caching",
  "content": "Write-through vs write-behind cache patterns.",
  "author_email": "sde@amazon.test"
}
```

#### Responses
- **201 Created**: `{"status": true, "post": {"id", "title", "slug", "content", "author_email"}}`
- **400 Bad Request**: when `title` or `content` is blank/missing -> `{"status": false, "error": "..."}`
- **Unique Slugs**: duplicate titles must auto-generate a unique slug (e.g. `distributed-locks-2`) instead of failing with `IntegrityError`.

### `GET /api/posts/`
Returns HTTP **200 OK** with `{"status": true, "posts": [...]}`.
""",
    "manage.py": """#!/usr/bin/env python
import os
import sys


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
""",
    "config/__init__.py": "",
    "config/settings.py": """from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = "skiltrix-assessment-sandbox-key"
DEBUG = True
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "posts",
]

MIDDLEWARE = [
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "config.urls"
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
""",
    "config/urls.py": """from django.urls import include, path
from posts import views as post_views

urlpatterns = [
    path("", post_views.blog_home, name="blog-home"),
    path("api/", include("posts.urls")),
]
""",
    "posts/__init__.py": "",
    "posts/models.py": """from django.db import models
from django.utils.text import slugify


class Post(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    content = models.TextField()
    author_email = models.EmailField(blank=True, default="")
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-id"]
""",
    "posts/urls.py": """from django.urls import path
from . import views

urlpatterns = [
    path("posts/", views.posts_collection, name="posts-collection"),
]
""",
    "posts/views.py": """import json
from django.http import HttpResponse, JsonResponse
from django.utils.text import slugify
from .models import Post


def blog_home(request):
    html = '''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>BlogPlatform — Discover Stories</title>
  <style>
    body { margin: 0; font-family: system-ui, sans-serif; background: #0b0f19; color: #e2e8f0; }
    header { display: flex; justify-content: space-between; align-items: center; padding: 14px 24px; background: #111827; border-bottom: 1px solid #1f2937; }
    .brand { font-weight: 800; color: #a78bfa; font-size: 18px; }
    .btn { background: #7c3aed; color: #fff; border: 0; padding: 8px 14px; border-radius: 8px; font-weight: 600; cursor: pointer; }
    .wrap { max-width: 820px; margin: 24px auto; padding: 0 20px; }
    .card { background: #111827; border: 1px solid #1f2937; border-radius: 12px; padding: 16px; margin-bottom: 12px; }
    input, textarea { width: 100%; box-sizing: border-box; background: #0b0f19; border: 1px solid #334155; color: #fff; padding: 9px 11px; border-radius: 8px; margin-bottom: 10px; }
    .status { font-size: 13px; margin-top: 8px; }
  </style>
</head>
<body>
  <header>
    <div class="brand">BlogPlatform</div>
    <button class="btn" onclick="document.getElementById('composer').scrollIntoView()">+ Write</button>
  </header>
  <div class="wrap">
    <h2>Discover Stories</h2>
    <div id="composer" class="card">
      <h3 style="margin-top:0">Write a New Post</h3>
      <input id="title" placeholder="Post title (e.g. Distributed Caching)" />
      <textarea id="content" rows="3" placeholder="Write your story content..."></textarea>
      <input id="author_email" placeholder="Author email (e.g. john@example.com)" />
      <button class="btn" onclick="createPost()">Publish Post</button>
      <div id="feedback" class="status"></div>
    </div>
    <div id="posts">Loading posts...</div>
  </div>
  <script>
    async function loadPosts() {
      const res = await fetch('api/posts/');
      const data = await res.json();
      const box = document.getElementById('posts');
      if (!data.posts || data.posts.length === 0) {
        box.innerHTML = '<div class="card">No posts yet. Click Publish Post above to reproduce or test the fix.</div>';
        return;
      }
      box.innerHTML = data.posts.map(p =>
        `<div class="card"><strong>${p.title}</strong> <small style="color:#94a3b8">/${p.slug}</small><p style="margin:6px 0 0;color:#cbd5e1">${p.content}</p></div>`
      ).join('');
    }
    async function createPost() {
      const fb = document.getElementById('feedback');
      fb.textContent = 'Submitting POST api/posts/...';
      try {
        const res = await fetch('api/posts/', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            title: document.getElementById('title').value,
            content: document.getElementById('content').value,
            author_email: document.getElementById('author_email').value
          })
        });
        const txt = await res.text();
        fb.style.color = res.status === 201 ? '#34d399' : '#f87171';
        fb.textContent = `HTTP ${res.status}: ${txt.slice(0, 180)}`;
        if (res.ok) loadPosts();
      } catch (e) {
        fb.style.color = '#f87171';
        fb.textContent = 'Request failed: ' + e;
      }
    }
    loadPosts();
  </script>
</body>
</html>'''
    return HttpResponse(html)


def posts_collection(request):
    if request.method == "GET":
        rows = list(Post.objects.values("id", "title", "slug", "content", "author_email", "is_published"))
        return JsonResponse({"status": True, "posts": rows}, status=200)

    if request.method == "POST":
        # BUG 1: Only reads request.POST; JSON payloads (application/json) get empty title/content.
        title = request.POST.get("title", "")
        content = request.POST.get("content", "")
        author_email = request.POST.get("author_email", "")

        # BUG 2: Missing validation — blank title/content should return 400 Bad Request with {"status": False, "error": ...}.
        # BUG 3: Duplicate titles collide on Post.slug unique constraint instead of generating a unique suffix!
        post = Post.objects.create(
            title=title,
            slug=slugify(title),
            content=content,
            author_email=author_email,
        )

        # BUG 4: Returns 200 instead of 201 Created!
        return JsonResponse(
            {
                "status": True,
                "post": {
                    "id": post.id,
                    "title": post.title,
                    "slug": post.slug,
                    "content": post.content,
                    "author_email": post.author_email,
                },
            },
            status=200,
        )

    return JsonResponse({"status": False, "error": "Method not allowed"}, status=405)
""",
    "posts/tests.py": """import json
from django.test import TestCase


class PostUploadEndpointTests(TestCase):
    def test_upload_post_json_returns_201(self):
        payload = {
            "title": "System Design Caching",
            "content": "Write-through vs write-behind cache patterns.",
            "author_email": "sde@amazon.test",
        }
        res = self.client.post(
            "/api/posts/",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertTrue(data.get("status"))
        self.assertEqual(data["post"]["title"], payload["title"])
        self.assertEqual(data["post"]["slug"], "system-design-caching")

    def test_blank_title_returns_400(self):
        res = self.client.post(
            "/api/posts/",
            data=json.dumps({"title": "   ", "content": "Valid body"}),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 400)
        self.assertFalse(res.json().get("status"))
""",
}

DEFAULT_AMAZON_HIDDEN_TEST_FILES: Dict[str, str] = {
    "posts/tests_hidden.py": """import json
from django.test import TestCase
from posts.models import Post


class PostUploadHiddenGradingTests(TestCase):
    def test_duplicate_title_generates_unique_slug(self):
        payload = {"title": "Distributed Locks", "content": "Redis Redlock notes"}
        r1 = self.client.post("/api/posts/", data=json.dumps(payload), content_type="application/json")
        r2 = self.client.post("/api/posts/", data=json.dumps(payload), content_type="application/json")
        self.assertEqual(r1.status_code, 201)
        self.assertEqual(r2.status_code, 201)
        self.assertNotEqual(r1.json()["post"]["slug"], r2.json()["post"]["slug"])
        self.assertEqual(Post.objects.count(), 2)

    def test_missing_content_returns_400(self):
        res = self.client.post(
            "/api/posts/",
            data=json.dumps({"title": "Empty Body", "content": ""}),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 400)
        self.assertEqual(Post.objects.count(), 0)

    def test_get_posts_lists_uploaded_posts(self):
        self.client.post(
            "/api/posts/",
            data=json.dumps({"title": "DynamoDB Partition Keys", "content": "High cardinality keys"}),
            content_type="application/json",
        )
        res = self.client.get("/api/posts/")
        self.assertEqual(res.status_code, 200)
        posts = res.json().get("posts", [])
        self.assertEqual(len(posts), 1)
        self.assertEqual(posts[0]["title"], "DynamoDB Partition Keys")
"""
}

DEFAULT_DJANGO_PROJECT_TEMPLATE: Dict[str, Any] = {
    "project_files": DEFAULT_AMAZON_PROJECT_FILES,
    "hidden_test_files": DEFAULT_AMAZON_HIDDEN_TEST_FILES,
}


def sanitize_rel_file_path(raw_path: str) -> Optional[str]:
    """Validate and normalize a relative workspace file path."""
    if not raw_path or not isinstance(raw_path, str):
        return None
    norm = raw_path.replace("\\", "/").strip().lstrip("/")
    if not norm or ".." in norm.split("/") or norm.startswith("~"):
        return None
    if ":" in norm.split("/")[0]:
        return None
    if any(seg in IGNORED_UPLOAD_DIRS for seg in norm.split("/")):
        return None
    lower = norm.lower()
    if lower.split("/")[-1] in IGNORED_UPLOAD_FILENAMES:
        return None
    if any(lower.endswith(ext) for ext in IGNORED_UPLOAD_EXTENSIONS):
        return None
    return norm


def compute_locked_files(project_files: Optional[Dict[str, str]]) -> List[str]:
    """Return read-only paths for any Django assessment project (built-in or uploaded)."""
    if not isinstance(project_files, dict) or not project_files:
        return []

    norm_paths = [
        str(k).replace("\\", "/").lstrip("/")
        for k in project_files.keys()
        if str(k).replace("\\", "/").strip("/")
    ]
    settings_dirs = {
        path.rsplit("/", 1)[0]
        for path in norm_paths
        if path.endswith("/settings.py")
    }
    default_set = set(DEFAULT_LOCKED_FILES)
    locked: List[str] = []
    for path in norm_paths:
        filename = path.rsplit("/", 1)[-1]
        lower_name = filename.lower()
        is_root_meta = lower_name in ("manage.py", "readme.md") and "/" not in path
        is_test_file = filename == "tests.py" or (filename.startswith("test_") and filename.endswith(".py")) or "/tests/" in path
        is_settings = filename == "settings.py"
        is_root_urls = path.endswith("/urls.py") and path.rsplit("/", 1)[0] in settings_dirs
        if path in default_set or is_root_meta or is_test_file or is_settings or is_root_urls:
            locked.append(path)
    return locked


def _is_hidden_test_path(rel_path: str) -> bool:
    lower = rel_path.lower()
    filename = lower.rsplit("/", 1)[-1]
    return (
        filename.startswith("tests_hidden")
        or filename.startswith("hidden_test")
        or "/hidden_tests/" in f"/{lower}"
    )


def _strip_project_wrapper(raw_map: Dict[str, str]) -> Dict[str, str]:
    """Strip a single outer folder (or outer folder above manage.py) from uploaded paths."""
    if not raw_map or "manage.py" in raw_map:
        return raw_map

    manage_candidates = sorted(
        [p for p in raw_map.keys() if p.endswith("/manage.py")],
        key=lambda p: p.count("/"),
    )
    prefix = ""
    if manage_candidates:
        prefix = manage_candidates[0].rsplit("/", 1)[0] + "/"
    else:
        first_parts = {p.split("/", 1)[0] for p in raw_map.keys() if "/" in p}
        has_root_file = any("/" not in p for p in raw_map.keys())
        if len(first_parts) == 1 and not has_root_file:
            prefix = next(iter(first_parts)) + "/"

    if not prefix:
        return raw_map

    stripped: Dict[str, str] = {}
    for path, content in raw_map.items():
        if path.startswith(prefix):
            rel = path[len(prefix):]
            if rel:
                stripped[rel] = content
    return stripped or raw_map


def parse_django_archive_bytes(raw_bytes: bytes) -> Dict[str, Any]:
    """Extract a local Django project .zip upload into project_files and hidden_test_files."""
    if not raw_bytes:
        raise ValueError("Uploaded archive is empty.")
    try:
        zf = zipfile.ZipFile(io.BytesIO(raw_bytes))
    except zipfile.BadZipFile as exc:
        raise ValueError("Invalid .zip archive. Please upload a valid Django project .zip file.") from exc

    raw_files: Dict[str, str] = {}
    skipped: List[str] = []
    total_bytes = 0

    with zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            clean = sanitize_rel_file_path(info.filename)
            if not clean:
                skipped.append(info.filename)
                continue
            if info.file_size > MAX_UPLOAD_FILE_BYTES:
                skipped.append(f"{clean} (exceeds 512 KB)")
                continue
            if len(raw_files) >= MAX_UPLOAD_FILE_COUNT:
                skipped.append(f"{clean} (file limit {MAX_UPLOAD_FILE_COUNT} reached)")
                continue
            total_bytes += info.file_size
            if total_bytes > MAX_UPLOAD_TOTAL_BYTES:
                raise ValueError("Uploaded Django project exceeds the 8 MB source size limit.")
            raw_content = zf.read(info)
            if b"\x00" in raw_content:
                skipped.append(f"{clean} (binary)")
                continue
            raw_files[clean] = raw_content.decode("utf-8", errors="replace")

    normalized = _strip_project_wrapper(raw_files)
    project_files: Dict[str, str] = {}
    hidden_test_files: Dict[str, str] = {}

    for rel_path, content in sorted(normalized.items()):
        if _is_hidden_test_path(rel_path):
            hidden_test_files[rel_path] = content
        else:
            project_files[rel_path] = content

    if not project_files:
        raise ValueError("No readable source files were found in the uploaded Django project.")

    def _count_test_methods(file_map: Dict[str, str]) -> int:
        return sum(
            len(re.findall(r"^\s*def\s+test_", src or "", re.MULTILINE))
            for path, src in file_map.items()
            if path.endswith(".py")
        )

    readme = project_files.get("README.md") or project_files.get("readme.md") or ""
    locked = compute_locked_files(project_files)

    return {
        "project_files": project_files,
        "hidden_test_files": hidden_test_files,
        "locked_files": locked,
        "readme": readme,
        "skipped_files": skipped[:25],
        "stats": {
            "file_count": len(project_files),
            "hidden_file_count": len(hidden_test_files),
            "has_manage_py": "manage.py" in project_files,
            "public_test_count": _count_test_methods(project_files),
            "hidden_test_count": _count_test_methods(hidden_test_files),
        },
    }


def _detect_settings_module(workspace: Path) -> str:
    manage_py = workspace / "manage.py"
    if manage_py.exists():
        text = manage_py.read_text(encoding="utf-8", errors="ignore")
        match = re.search(r"""DJANGO_SETTINGS_MODULE["']?\s*,\s*["']([^"']+)["']""", text)
        if match:
            return match.group(1)
    for settings_file in workspace.rglob("settings.py"):
        rel = settings_file.relative_to(workspace).with_suffix("")
        return ".".join(rel.parts)
    return "config.settings"


def _parse_django_test_output(output: str, hidden_names: set[str]) -> List[Dict[str, Any]]:
    """Parse `manage.py test -v 2` test case lines into uniform judge verdicts."""
    pattern = re.compile(
        r"^(test_[A-Za-z0-9_]+)\s+\(([^)]+)\)\s+.*?\.\.\.\s+(ok|FAIL|ERROR|skipped.*)$",
        re.MULTILINE,
    )
    results: List[Dict[str, Any]] = []
    for idx, match in enumerate(pattern.finditer(output), start=1):
        test_name = match.group(1)
        dotted_cls = match.group(2)
        verdict = match.group(3).strip()
        is_hidden = any(h in dotted_cls for h in hidden_names) or "tests_hidden" in dotted_cls
        passed = verdict == "ok"
        status_label = "Accepted" if passed else ("Runtime Error" if verdict == "ERROR" else "Wrong Answer")
        results.append(
            {
                "case_number": idx,
                "name": f"{dotted_cls.split('.')[-1]}.{test_name}",
                "input": test_name,
                "is_hidden": is_hidden,
                "passed": passed,
                "status": status_label,
                "execution_time_ms": 0.0,
                "memory_kb": 0.0,
            }
        )
    return results


def evaluate_django_project_problem(
    *,
    problem: Any,
    candidate_files: Optional[Dict[str, str]],
    max_marks: float = 100.0,
    include_hidden: bool = False,
) -> Dict[str, Any]:
    """Run `manage.py test -v 2` inside an ephemeral workspace directory."""
    starter_files = dict(getattr(problem, "project_files", None) or {})
    hidden_files = dict(getattr(problem, "hidden_test_files", None) or {})
    hidden_keys = {sanitize_rel_file_path(k) for k in hidden_files.keys()}
    hidden_keys.discard(None)

    merged_files: Dict[str, str] = {}
    for raw_k, raw_v in starter_files.items():
        clean_k = sanitize_rel_file_path(raw_k)
        if clean_k:
            merged_files[clean_k] = str(raw_v or "")

    if isinstance(candidate_files, dict):
        for raw_k, raw_v in candidate_files.items():
            clean_k = sanitize_rel_file_path(raw_k)
            if clean_k and clean_k not in hidden_keys:
                merged_files[clean_k] = str(raw_v or "")

    if include_hidden:
        for raw_k, raw_v in hidden_files.items():
            clean_k = sanitize_rel_file_path(raw_k)
            if clean_k:
                merged_files[clean_k] = str(raw_v or "")

    if "manage.py" not in merged_files:
        raise ValueError("This Django assessment problem has no manage.py configured.")

    hidden_module_markers = {
        Path(k).stem for k in hidden_keys if k and k.endswith(".py")
    }

    with tempfile.TemporaryDirectory(prefix="skiltrix_django_eval_") as tmp_dir:
        workspace = Path(tmp_dir)
        for rel_path, content in merged_files.items():
            target = (workspace / rel_path).resolve()
            if not str(target).startswith(str(workspace.resolve())):
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")

        settings_mod = _detect_settings_module(workspace)
        env = ExecutionPolicy.sanitize_environment(
            {
                "PYTHONUNBUFFERED": "1",
                "DJANGO_SETTINGS_MODULE": settings_mod,
            }
        )
        env["PYTHONPATH"] = f"{str(workspace)}{os.pathsep}{env.get('PYTHONPATH', '')}".strip(os.pathsep)

        start = time.time()
        try:
            proc = subprocess.run(
                [sys.executable, "manage.py", "test", "--noinput", "-v", "2"],
                cwd=workspace,
                env=env,
                capture_output=True,
                text=True,
                timeout=25.0,
            )
            elapsed_ms = round((time.time() - start) * 1000.0, 2)
            stdout = proc.stdout or ""
            stderr = proc.stderr or ""
            combined = f"{stdout}\n{stderr}".strip()
            timed_out = False
        except subprocess.TimeoutExpired as exc:
            elapsed_ms = round((time.time() - start) * 1000.0, 2)
            stdout = exc.stdout.decode("utf-8", errors="ignore") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
            stderr = "Django test runner timed out after 25s."
            combined = f"{stdout}\n{stderr}".strip()
            proc = None
            timed_out = True

    parsed_cases = _parse_django_test_output(combined, hidden_module_markers)
    if not parsed_cases and not timed_out:
        summary_match = re.search(r"Ran\s+(\d+)\s+test", combined)
        total_reported = int(summary_match.group(1)) if summary_match else 0
        passed_all = bool(proc and proc.returncode == 0 and total_reported > 0)
        if total_reported > 0:
            parsed_cases = [
                {
                    "case_number": i,
                    "name": f"Test Case #{i}",
                    "input": f"Django test #{i}",
                    "is_hidden": False,
                    "passed": passed_all,
                    "status": "Accepted" if passed_all else "Wrong Answer",
                    "execution_time_ms": round(elapsed_ms / total_reported, 2),
                    "memory_kb": 0.0,
                }
                for i in range(1, total_reported + 1)
            ]

    total_cases = len(parsed_cases)
    passed_cases = sum(1 for c in parsed_cases if c["passed"])
    failed_cases = total_cases - passed_cases

    if timed_out:
        overall_status = "Time Limit Exceeded"
        score = 0.0
    elif total_cases == 0:
        overall_status = "Runtime Error"
        score = 0.0
    elif passed_cases == total_cases:
        overall_status = "Accepted"
        score = round(float(max_marks), 2)
    elif passed_cases > 0:
        overall_status = "Partial Accepted"
        score = round((passed_cases / total_cases) * float(max_marks), 2)
    else:
        overall_status = "Wrong Answer"
        score = 0.0

    per_case_ms = round(elapsed_ms / max(total_cases, 1), 2)
    for case in parsed_cases:
        case["execution_time_ms"] = per_case_ms

    return {
        "status": overall_status,
        "mode": "sample_tests",
        "language": "django",
        "passed": overall_status == "Accepted",
        "passed_count": passed_cases,
        "total_count": total_cases,
        "total_test_cases": total_cases,
        "passed_test_cases": passed_cases,
        "failed_test_cases": failed_cases,
        "score": score,
        "max_score": round(float(max_marks), 2),
        "execution_time_ms": elapsed_ms,
        "memory_used_kb": 24576.0,
        "memory_kb": 24576.0,
        "backend_used": "django_test_runner",
        "compile_output": "",
        "error_message": combined if overall_status != "Accepted" else "",
        "stdout": combined,
        "stderr": stderr if overall_status != "Accepted" else "",
        "test_case_results": parsed_cases,
    }
