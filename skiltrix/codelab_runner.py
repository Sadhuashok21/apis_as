import os
import sys
import uuid
import time
import shutil
import zipfile
import subprocess
from pathlib import Path
from pathlib import PureWindowsPath
from typing import Dict, Any, Tuple, Optional
from django.conf import settings

WORKSPACE_BASE_DIR = Path(settings.MEDIA_ROOT) / "codelab_workspaces"
WORKSPACE_BASE_DIR.mkdir(parents=True, exist_ok=True)

# Allowed execution timeouts and size limits
MAX_EXECUTION_TIMEOUT_SECONDS = 15.0
MAX_OUTPUT_LENGTH = 100_000  # 100 KB max stdout/stderr buffer


def get_project_workspace_dir(project_id: str) -> Path:
    """Resolve an owned project's storage from its database owner, never its title."""
    from .codelab_models import CodeProject

    project = CodeProject.objects.select_related("user").filter(project_id=project_id).first()
    if project is None:
        raise ValueError("Workspace project does not exist.")
    safe_id = "".join(c for c in project.project_id if c.isalnum() or c in ("-", "_"))
    owner_id = "".join(c for c in project.user.user_id if c.isalnum() or c in ("-", "_"))
    root = (WORKSPACE_BASE_DIR / "users").resolve()
    project_dir = (root / owner_id / safe_id).resolve()
    if root not in project_dir.parents:
        raise ValueError("Invalid workspace storage path.")

    # Existing project ownership comes from CodeProject.user. Copy legacy data
    # into its isolated location once, preserving the original for backup/review.
    legacy = WORKSPACE_BASE_DIR / safe_id
    if not project_dir.exists() and legacy.is_dir() and not legacy.is_symlink():
        project_dir.parent.mkdir(parents=True, exist_ok=True)
        project_dir.mkdir(parents=True, exist_ok=True)
        for source in legacy.rglob("*"):
            if source.is_symlink():
                continue
            relative = source.relative_to(legacy)
            target = project_dir / relative
            if source.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            elif source.is_file():
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
    project_dir.mkdir(parents=True, exist_ok=True)
    return project_dir


def resolve_workspace_path(workspace_dir: Path, relative_path: str) -> Path:
    """Resolve a user path and reject traversal and symlink escapes."""
    safe_rel = sanitize_relative_path(relative_path)
    root = workspace_dir.resolve()
    target = (root / safe_rel).resolve()
    if target != root and root not in target.parents:
        raise ValueError("Workspace path escapes the project directory.")
    return target


def sanitize_relative_path(rel_path: str) -> str:
    """Ensure path has no directory traversal characters."""
    raw_path = (rel_path or "").strip().replace("\\", "/")
    parts = raw_path.split("/")
    if (
        raw_path.startswith("/")
        or PureWindowsPath(raw_path).is_absolute()
        or any(part == ".." for part in parts)
    ):
        raise ValueError(f"Illegal path traversal attempt: {rel_path}")
    normalized = os.path.normpath(raw_path)
    if normalized in ("", "."):
        raise ValueError("A file path is required.")
    return normalized.replace("\\", "/")


def sync_db_files_to_workspace(project) -> Path:
    """Sync all ProjectFile records to disk workspace."""
    workspace_dir = get_project_workspace_dir(project.project_id)
    files = project.files.all()

    for pfile in files:
        safe_rel = sanitize_relative_path(pfile.path)
        target_path = resolve_workspace_path(workspace_dir, safe_rel)
        if pfile.is_directory:
            target_path.mkdir(parents=True, exist_ok=True)
        else:
            # Never write or overwrite binary SQLite databases as text
            if safe_rel.endswith((".sqlite3", ".sqlite", ".db")) or "sqlite" in safe_rel:
                continue

            target_path.parent.mkdir(parents=True, exist_ok=True)
            temp_path = target_path.with_name(f".{target_path.name}.{uuid.uuid4().hex}.tmp")
            temp_path.write_text(pfile.content, encoding="utf-8", errors="replace")
            os.replace(temp_path, target_path)

    return workspace_dir


def sync_workspace_files_to_db(project) -> None:
    """
    Sync all files from physical workspace directory back into ProjectFile DB records.
    Indexes files created or modified by terminal commands, manage.py startapp, or scripts.
    """
    from .codelab_models import ProjectFile
    import uuid

    workspace_dir = get_project_workspace_dir(project.project_id)
    if not workspace_dir.exists():
        return

    ignored_dirs = {".venv", "venv", "env", "__pycache__", ".git", ".idea", ".vscode"}
    existing_files = {pfile.path: pfile for pfile in project.files.all()}

    for root, dirs, files in os.walk(workspace_dir):
        dirs[:] = [d for d in dirs if d not in ignored_dirs and not (Path(root) / d).is_symlink()]
        rel_root = Path(root).relative_to(workspace_dir)

        if rel_root != Path("."):
            dir_path = rel_root.as_posix()
            if dir_path not in existing_files:
                ProjectFile.objects.create(
                    file_id=f"file_{uuid.uuid4().hex[:12]}",
                    project=project,
                    path=dir_path,
                    name=rel_root.name,
                    is_directory=True,
                    content="",
                    size_bytes=0,
                )

        for f in files:
            if (
                f.endswith((".pyc", ".sqlite3", ".sqlite", ".db"))
                or f in ("db.sqlite3", "django_server.log", "php_server.log")
            ):
                continue
            file_path = (rel_root / f).as_posix() if rel_root != Path(".") else f
            abs_path = Path(root) / f
            if abs_path.is_symlink():
                continue

            try:
                content = abs_path.read_text(encoding="utf-8", errors="replace")
                size_bytes = len(content.encode("utf-8"))
            except Exception:
                content = ""
                size_bytes = 0

            if file_path in existing_files:
                pfile = existing_files[file_path]
                if pfile.content != content:
                    pfile.content = content
                    pfile.size_bytes = size_bytes
                    pfile.save(update_fields=["content", "size_bytes", "updated_at"])
            else:
                ProjectFile.objects.create(
                    file_id=f"file_{uuid.uuid4().hex[:12]}",
                    project=project,
                    path=file_path,
                    name=f,
                    is_directory=False,
                    content=content,
                    size_bytes=size_bytes,
                )


def export_project_as_zip(project) -> Path:
    """Create a ZIP archive of the project workspace."""
    workspace_dir = sync_db_files_to_workspace(project)
    zip_path = workspace_dir / "exports" / f"{uuid.uuid4().hex}.zip"
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for root, dirs, files in os.walk(workspace_dir):
            dirs[:] = [directory for directory in dirs if not (Path(root) / directory).is_symlink()]
            for file in files:
                abs_path = Path(root) / file
                if abs_path.is_symlink() or "exports" in abs_path.relative_to(workspace_dir).parts:
                    continue
                arc_name = abs_path.relative_to(workspace_dir)
                zip_file.write(abs_path, arc_name)

    return zip_path


def get_default_starter_files(project_type: str, language: str) -> list:
    """Generate default files based on project type and language."""
    files = []

    if project_type == "django":
        files.append({
            "path": "manage.py",
            "name": "manage.py",
            "is_directory": False,
            "content": """#!/usr/bin/env python
import os
import sys

def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable?"
        ) from exc
    execute_from_command_line(sys.argv)

if __name__ == '__main__':
    main()
"""
        })
        files.append({
            "path": "requirements.txt",
            "name": "requirements.txt",
            "is_directory": False,
            "content": """Django>=4.2,<5.2
asgiref>=3.7.0
sqlparse>=0.4.4
"""
        })
        files.append({
            "path": ".gitignore",
            "name": ".gitignore",
            "is_directory": False,
            "content": """*.pyc
__pycache__/
db.sqlite3
media/
.venv/
*.log
.DS_Store
"""
        })
        files.append({
            "path": "config/__init__.py",
            "name": "__init__.py",
            "is_directory": False,
            "content": ""
        })
        files.append({
            "path": "config/settings.py",
            "name": "settings.py",
            "is_directory": False,
            "content": """import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = 'codelab-insecure-django-secret-key-for-learning'
DEBUG = True
ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'myapp.apps.MyappConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

_configured_db = os.environ.get('CODELAB_DJANGO_DATABASE')
_db_file = f'{_configured_db}.sqlite3' if _configured_db else 'default_db.sqlite3'
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'databases' / _db_file,
    }
}

AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']

MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
"""
        })
        files.append({
            "path": "config/urls.py",
            "name": "urls.py",
            "is_directory": False,
            "content": """from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('myapp.urls')),
]
"""
        })
        files.append({
            "path": "config/asgi.py",
            "name": "asgi.py",
            "is_directory": False,
            "content": """import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
application = get_asgi_application()
"""
        })
        files.append({
            "path": "config/wsgi.py",
            "name": "wsgi.py",
            "is_directory": False,
            "content": """import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
application = get_wsgi_application()
"""
        })
        files.append({
            "path": "myapp/__init__.py",
            "name": "__init__.py",
            "is_directory": False,
            "content": ""
        })
        files.append({
            "path": "myapp/apps.py",
            "name": "apps.py",
            "is_directory": False,
            "content": """from django.apps import AppConfig

class MyappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'myapp'
"""
        })
        files.append({
            "path": "myapp/admin.py",
            "name": "admin.py",
            "is_directory": False,
            "content": """from django.contrib import admin
from .models import Task

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'completed', 'created_at')
"""
        })
        files.append({
            "path": "myapp/models.py",
            "name": "models.py",
            "is_directory": False,
            "content": """from django.db import models

class Task(models.Model):
    title = models.CharField(max_length=200)
    completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
"""
        })
        files.append({
            "path": "myapp/views.py",
            "name": "views.py",
            "is_directory": False,
            "content": """from django.shortcuts import render
from django.http import JsonResponse
from .models import Task

def home(request):
    tasks = Task.objects.all()
    context = {
        'title': 'SkilTrix Django Development Suite',
        'tasks': tasks,
    }
    return render(request, 'myapp/index.html', context)

def tasks_api(request):
    return JsonResponse({
        'status': 'success',
        'message': 'Welcome to your Django API!',
        'version': '1.0.0'
    })
"""
        })
        files.append({
            "path": "myapp/urls.py",
            "name": "urls.py",
            "is_directory": False,
            "content": """from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('api/tasks/', views.tasks_api, name='tasks_api'),
]
"""
        })
        files.append({
            "path": "myapp/tests.py",
            "name": "tests.py",
            "is_directory": False,
            "content": """from django.test import TestCase
from .models import Task

class TaskModelTest(TestCase):
    def test_create_task(self):
        task = Task.objects.create(title="Learn Django on SkilTrix")
        self.assertEqual(task.title, "Learn Django on SkilTrix")
        self.assertFalse(task.completed)
"""
        })
        files.append({
            "path": "myapp/migrations/__init__.py",
            "name": "__init__.py",
            "is_directory": False,
            "content": ""
        })
        files.append({
            "path": "templates/base.html",
            "name": "base.html",
            "is_directory": False,
            "content": """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}Django App - SkilTrix{% endblock %}</title>
    <link rel="stylesheet" href="/static/css/style.css">
</head>
<body>
    <header class="header">
        <div class="logo">⚡ SkilTrix Django IDE</div>
    </header>
    <main class="container">
        {% block content %}{% endblock %}
    </main>
</body>
</html>
"""
        })
        files.append({
            "path": "templates/myapp/index.html",
            "name": "index.html",
            "is_directory": False,
            "content": """{% extends 'base.html' %}

{% block title %}{{ title }}{% endblock %}

{% block content %}
<div class="card">
    <h1 style="color: #6366f1;">🚀 {{ title }}</h1>
    <p>Your Django development environment is active and running cleanly.</p>
    <ul>
        <li>Modify <code>myapp/views.py</code> or <code>myapp/models.py</code> to add features.</li>
        <li>Visit <code>/api/tasks/</code> for JSON response.</li>
    </ul>
</div>
{% endblock %}
"""
        })
        files.append({
            "path": "static/css/style.css",
            "name": "style.css",
            "is_directory": False,
            "content": """body {
    margin: 0;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background: #0f172a;
    color: #f8fafc;
}
.header {
    padding: 16px 32px;
    background: #1e293b;
    border-bottom: 1px solid #334155;
    font-weight: bold;
}
.container {
    max-width: 800px;
    margin: 40px auto;
    padding: 0 20px;
}
.card {
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 12px;
    padding: 32px;
}
"""
        })
        files.append({
            "path": "media/.keep",
            "name": ".keep",
            "is_directory": False,
            "content": ""
        })

    elif project_type == "php":
        files.append({
            "path": "index.php",
            "name": "index.php",
            "is_directory": False,
            "content": """<?php
require_once __DIR__ . '/config.php';
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SkilTrix PHP App</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <div class="container">
        <header class="header">
            <span class="badge">🐘 PHP <?php echo phpversion(); ?></span>
            <h1>SkilTrix PHP CodeLab</h1>
            <p class="subtitle">Full-stack multi-file PHP development environment</p>
        </header>

        <div class="grid">
            <div class="card">
                <h3>⚡ Server Status</h3>
                <p>Status: <strong style="color: #4ade80;">Active &amp; Running</strong></p>
                <p>Time: <?php echo date('Y-m-d H:i:s'); ?></p>
                <p>Memory: <?php echo round(memory_get_usage() / 1024 / 1024, 2); ?> MB</p>
            </div>

            <div class="card">
                <h3>🚀 Fast Navigation</h3>
                <ul class="nav-links">
                    <li><a href="form.php">📝 Interactive Form Demo (POST/GET)</a></li>
                    <li><a href="api.php">⚡ JSON REST API Endpoint</a></li>
                    <li><a href="db_test.php">🗄️ SQLite PDO Database Demo</a></li>
                </ul>
            </div>
        </div>

        <footer class="footer">
            <p>CodeLab PHP Workspace &bull; Persistent Project Files</p>
        </footer>
    </div>
</body>
</html>
"""
        })
        files.append({
            "path": "config.php",
            "name": "config.php",
            "is_directory": False,
            "content": """<?php
if (session_status() === PHP_SESSION_NONE) {
    session_start();
}

define('APP_NAME', 'SkilTrix PHP CodeLab');
define('APP_VERSION', '1.0.0');

// SQLite PDO Database Helper
function getDatabase() {
    $dbPath = __DIR__ . '/app.db';
    $pdo = new PDO("sqlite:" . $dbPath);
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
    return $pdo;
}
"""
        })
        files.append({
            "path": "api.php",
            "name": "api.php",
            "is_directory": False,
            "content": """<?php
header('Content-Type: application/json; charset=utf-8');
require_once __DIR__ . '/config.php';

$response = [
    'status' => 'success',
    'message' => 'Welcome to your SkilTrix PHP API!',
    'php_version' => phpversion(),
    'timestamp' => date('c'),
    'items' => [
        ['id' => 1, 'name' => 'PHP Syntax & Types', 'category' => 'Basics'],
        ['id' => 2, 'name' => 'PDO & Prepared Statements', 'category' => 'Database'],
        ['id' => 3, 'name' => 'Sessions & Authentication', 'category' => 'Security']
    ]
];

echo json_encode($response, JSON_PRETTY_PRINT);
"""
        })
        files.append({
            "path": "form.php",
            "name": "form.php",
            "is_directory": False,
            "content": """<?php
require_once __DIR__ . '/config.php';

$message = '';
$messageType = '';

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $username = trim($_POST['username'] ?? '');
    $email = trim($_POST['email'] ?? '');

    if (!empty($username) && !empty($email)) {
        $_SESSION['last_submission'] = [
            'username' => htmlspecialchars($username),
            'email' => htmlspecialchars($email),
            'time' => date('H:i:s')
        ];
        $message = "Success! Received submission for " . htmlspecialchars($username) . " (" . htmlspecialchars($email) . ")";
        $messageType = "success";
    } else {
        $message = "Please fill in all required fields.";
        $messageType = "error";
    }
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>PHP Form Submission - SkilTrix</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <div class="container">
        <p><a href="index.php">&larr; Back to Dashboard</a></p>
        <div class="card">
            <h2>📝 PHP Form Submission Demo</h2>
            <p>Test standard HTTP POST form processing, input sanitization, and session storage.</p>

            <?php if (!empty($message)): ?>
                <div class="alert alert-<?php echo $messageType; ?>">
                    <?php echo $message; ?>
                </div>
            <?php endif; ?>

            <form method="POST" action="form.php" class="form">
                <div class="form-group">
                    <label for="username">Username:</label>
                    <input type="text" id="username" name="username" placeholder="e.g. alex_coder" required>
                </div>
                <div class="form-group">
                    <label for="email">Email Address:</label>
                    <input type="email" id="email" name="email" placeholder="alex@example.com" required>
                </div>
                <button type="submit" class="btn">Submit via POST</button>
            </form>

            <?php if (isset($_SESSION['last_submission'])): ?>
                <div style="margin-top: 20px; font-size: 13px; color: #94a3b8;">
                    <strong>Last Session Submission:</strong> <?php echo $_SESSION['last_submission']['username']; ?> at <?php echo $_SESSION['last_submission']['time']; ?>
                </div>
            <?php endif; ?>
        </div>
    </div>
</body>
</html>
"""
        })
        files.append({
            "path": "db_test.php",
            "name": "db_test.php",
            "is_directory": False,
            "content": """<?php
require_once __DIR__ . '/config.php';

try {
    $db = getDatabase();
    // Create notes table if not exists
    $db->exec("CREATE TABLE IF NOT EXISTS notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )");

    // Auto-seed if empty
    $count = $db->query("SELECT COUNT(*) FROM notes")->fetchColumn();
    if ($count == 0) {
        $db->exec("INSERT INTO notes (title) VALUES ('Welcome to SkilTrix PHP SQLite!')");
        $db->exec("INSERT INTO notes (title) VALUES ('PDO prepared statements tutorial')");
    }

    $notes = $db->query("SELECT * FROM notes ORDER BY id DESC")->fetchAll(PDO::FETCH_ASSOC);
    $statusMsg = "Connected to SQLite successfully. " . count($notes) . " records found.";
} catch (Exception $e) {
    $statusMsg = "Database Error: " . $e->getMessage();
    $notes = [];
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>PHP SQLite Database - SkilTrix</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <div class="container">
        <p><a href="index.php">&larr; Back to Dashboard</a></p>
        <div class="card">
            <h2>🗄️ SQLite PDO Database Demo</h2>
            <p class="status-msg"><?php echo htmlspecialchars($statusMsg); ?></p>

            <table class="table">
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Note Title</th>
                        <th>Created At</th>
                    </tr>
                </thead>
                <tbody>
                    <?php foreach ($notes as $note): ?>
                        <tr>
                            <td><?php echo $note['id']; ?></td>
                            <td><?php echo htmlspecialchars($note['title']); ?></td>
                            <td><?php echo $note['created_at']; ?></td>
                        </tr>
                    <?php endforeach; ?>
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>
"""
        })
        files.append({
            "path": "style.css",
            "name": "style.css",
            "is_directory": False,
            "content": """body {
    background: #0f172a;
    color: #e2e8f0;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    margin: 0;
    padding: 24px;
}
.container {
    max-width: 800px;
    margin: 0 auto;
}
.header {
    text-align: center;
    margin-bottom: 24px;
}
.badge {
    background: #4338ca;
    color: #c7d2fe;
    padding: 4px 10px;
    border-radius: 6px;
    font-size: 12px;
    font-weight: 600;
}
.grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
}
.card {
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 10px;
    padding: 20px;
}
.nav-links {
    list-style: none;
    padding: 0;
    margin: 0;
}
.nav-links li {
    margin-bottom: 10px;
}
.nav-links a, p a {
    color: #818cf8;
    text-decoration: none;
    font-weight: 500;
}
.nav-links a:hover, p a:hover {
    text-decoration: underline;
}
.form-group {
    margin-bottom: 14px;
}
.form-group label {
    display: block;
    margin-bottom: 6px;
    font-size: 13px;
    color: #94a3b8;
}
.form-group input {
    width: 100%;
    box-sizing: border-box;
    background: #0f172a;
    border: 1px solid #334155;
    color: white;
    padding: 8px 12px;
    border-radius: 6px;
    font-size: 14px;
}
.btn {
    background: #6366f1;
    color: white;
    border: none;
    padding: 8px 16px;
    border-radius: 6px;
    cursor: pointer;
    font-weight: 600;
}
.btn:hover {
    background: #4f46e5;
}
.alert {
    padding: 10px 14px;
    border-radius: 6px;
    margin-bottom: 14px;
    font-size: 13px;
}
.alert-success {
    background: rgba(34, 197, 94, 0.2);
    border: 1px solid rgba(34, 197, 94, 0.4);
    color: #4ade80;
}
.alert-error {
    background: rgba(239, 68, 68, 0.2);
    border: 1px solid rgba(239, 68, 68, 0.4);
    color: #f87171;
}
.table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 14px;
}
.table th, .table td {
    padding: 10px;
    border-bottom: 1px solid #334155;
    text-align: left;
    font-size: 13px;
}
.footer {
    text-align: center;
    margin-top: 30px;
    font-size: 12px;
    color: #64748b;
}
"""
        })

    elif project_type == "sql":
        files.append({
            "path": "schema.sql",
            "name": "schema.sql",
            "is_directory": False,
            "content": """-- SkilTrix SQL Playground Initial Schema
CREATE TABLE IF NOT EXISTS departments (
    dept_id INTEGER PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    location VARCHAR(100)
);

CREATE TABLE IF NOT EXISTS employees (
    emp_id INTEGER PRIMARY KEY,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    dept_id INTEGER,
    salary DECIMAL(10, 2),
    hire_date DATE,
    FOREIGN KEY (dept_id) REFERENCES departments(dept_id)
);
"""
        })
        files.append({
            "path": "seed.sql",
            "name": "seed.sql",
            "is_directory": False,
            "content": """-- Insert initial sample seed data
INSERT INTO departments (dept_id, name, location) VALUES
(1, 'Engineering', 'San Francisco'),
(2, 'Product Management', 'New York'),
(3, 'Design', 'London');

INSERT INTO employees (emp_id, first_name, last_name, dept_id, salary, hire_date) VALUES
(101, 'Alex', 'Rivera', 1, 95000.00, '2023-01-15'),
(102, 'Maya', 'Patel', 1, 110000.00, '2022-06-01'),
(103, 'Liam', 'Chen', 2, 88000.00, '2023-03-20'),
(104, 'Sophia', 'Kim', 3, 82000.00, '2023-09-10');
"""
        })
        files.append({
            "path": "queries.sql",
            "name": "queries.sql",
            "is_directory": False,
            "content": """-- Practice queries
-- 1. List all employees with their department name
SELECT e.emp_id, e.first_name, e.last_name, d.name AS department, e.salary
FROM employees e
JOIN departments d ON e.dept_id = d.dept_id
ORDER BY e.salary DESC;
"""
        })

    elif project_type == "react":
        files.append({
            "path": "package.json",
            "name": "package.json",
            "is_directory": False,
            "content": """{
  "name": "codelab-react-app",
  "private": true,
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build"
  },
  "dependencies": {
    "react": "^19.0.0",
    "react-dom": "^19.0.0"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^6.0.0",
    "vite": "^8.0.5"
  }
}
"""
        })
        files.append({
            "path": "index.html",
            "name": "index.html",
            "is_directory": False,
            "content": """<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>SkilTrix React Project</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
"""
        })
        files.append({
            "path": "src/App.jsx",
            "name": "App.jsx",
            "is_directory": False,
            "content": """import React, { useState } from 'react';

export default function App() {
  const [count, setCount] = useState(0);

  return (
    <div style={{ fontFamily: 'system-ui, sans-serif', padding: '40px', background: '#090d16', color: '#f1f5f9', minHeight: '100vh' }}>
      <h1 style={{ color: '#6366f1' }}>⚛️ Welcome to React CodeLab!</h1>
      <p>Edit <code>src/App.jsx</code> to watch instant updates.</p>
      <button 
        onClick={() => setCount(c => c + 1)}
        style={{ background: '#4f46e5', color: '#fff', border: 'none', padding: '10px 20px', borderRadius: '8px', fontSize: '16px', cursor: 'pointer' }}
      >
        Count is: {count}
      </button>
    </div>
  );
}
"""
        })
        files.append({
            "path": "src/main.jsx",
            "name": "main.jsx",
            "is_directory": False,
            "content": """import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App.jsx';

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
"""
        })

    else:
        # Single-file program defaults
        lang_lower = language.lower()
        if "py" in lang_lower:
            files.append({
                "path": "main.py",
                "name": "main.py",
                "is_directory": False,
                "content": """# SkilTrix CodeLab - Python Workspace
import sys

def main():
    print("🚀 Python Execution Environment Active!")
    print(f"Python Version: {sys.version.split()[0]}")

if __name__ == '__main__':
    main()
"""
            })
        elif "java" in lang_lower:
            files.append({
                "path": "Solution.java",
                "name": "Solution.java",
                "is_directory": False,
                "content": """// SkilTrix CodeLab - Java Workspace
public class Solution {
    public static void main(String[] args) {
        System.out.println("☕ Java Execution Environment Active!");
        System.out.println("Java Version: " + System.getProperty("java.version"));
    }
}
"""
            })
        elif "js" in lang_lower or "javascript" in lang_lower:
            files.append({
                "path": "index.js",
                "name": "index.js",
                "is_directory": False,
                "content": """// SkilTrix CodeLab - JavaScript/Node.js Workspace
console.log("⚡ Node.js Execution Environment Active!");
console.log(`Node Version: ${process.version}`);
"""
            })
        elif "ts" in lang_lower or "typescript" in lang_lower:
            files.append({
                "path": "index.ts",
                "name": "index.ts",
                "is_directory": False,
                "content": """// SkilTrix CodeLab - TypeScript Workspace
interface Developer {
    name: string;
    skills: string[];
}

const dev: Developer = {
    name: "SkilTrix Engineer",
    skills: ["TypeScript", "Python", "React"]
};

console.log("📘 TypeScript Environment Active!", dev);
"""
            })
        elif "cpp" in lang_lower or "c++" in lang_lower:
            files.append({
                "path": "main.cpp",
                "name": "main.cpp",
                "is_directory": False,
                "content": """#include <iostream>

int main() {
    std::cout << "⚙️ C++ Execution Environment Active!" << std::endl;
    return 0;
}
"""
            })
        elif "c" == lang_lower:
            files.append({
                "path": "main.c",
                "name": "main.c",
                "is_directory": False,
                "content": """#include <stdio.h>

int main() {
    printf("⚙️ C Execution Environment Active!\\n");
    return 0;
}
"""
            })
        else:
            files.append({
                "path": "main.txt",
                "name": "main.txt",
                "is_directory": False,
                "content": "Welcome to your SkilTrix CodeLab project!\n"
            })

    return files


def run_code_in_sandbox(
    language: str,
    code: str,
    stdin: str = "",
    workspace_dir: Optional[Path] = None,
    entry_filename: Optional[str] = None
) -> Dict[str, Any]:
    """
    Executes code in a secure sandboxed environment.
    Delegates to the modular SkilTrix CodeLab execution worker engine.
    """
    from .execution import execute_code_job

    return execute_code_job(
        language=language,
        code=code,
        stdin=stdin,
        workspace_dir=workspace_dir,
        entry_file=entry_filename,
    )

