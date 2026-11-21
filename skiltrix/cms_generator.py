import os
import re
import json
import shutil
from pathlib import Path
from django.conf import settings
from django.utils.text import slugify


def get_skiltrix_generated_root() -> Path:
    """
    Returns the absolute path to `skiltrix/src/generated-courses`.
    Ensures the directory exists.
    """
    base_dir = Path(settings.BASE_DIR).parent  # c:\Users\ssimu\OneDrive\Desktop\web\main
    target_dir = base_dir / "skiltrix" / "src" / "generated-courses"
    target_dir.mkdir(parents=True, exist_ok=True)
    return target_dir.resolve()


def sanitize_rel_path(path_str: str) -> str:
    """
    Sanitizes a relative path ensuring it cannot escape using .. or invalid characters.
    """
    cleaned = path_str.strip("/\\ ")
    parts = [slugify(p) for p in re.split(r"[/\\]+", cleaned) if p and p != "." and p != ".."]
    return "/".join(parts)


def html_to_jsx(html: str) -> str:
    """
    Converts standard HTML snippet into valid React JSX:
    - class="..." -> className="..."
    - for="..." -> htmlFor="..."
    - self-closing void elements (img, br, hr, input)
    - inline styles style="..." -> style={{ ... }}
    """
    if not html:
        return ""

    jsx = html
    # class to className
    jsx = re.sub(r'\bclass=(["\'])', r'className=\1', jsx)
    jsx = re.sub(r'\bfor=(["\'])', r'htmlFor=\1', jsx)
    jsx = re.sub(r'\btabindex=(["\'])', r'tabIndex=\1', jsx)
    jsx = re.sub(r'\bautocomplete=(["\'])', r'autoComplete=\1', jsx)
    jsx = re.sub(r'\bcolspan=(["\'])', r'colSpan=\1', jsx)
    jsx = re.sub(r'\browspan=(["\'])', r'rowSpan=\1', jsx)

    # self-close void tags: <img ...>, <br>, <hr>, <input ...>
    for tag in ['img', 'br', 'hr', 'input']:
        pattern = rf'<({tag}\b[^>]*?)(?<!/)>'
        jsx = re.sub(pattern, r'<\1 />', jsx, flags=re.IGNORECASE)

    # inline style attribute to React style object (simple key-value mapping)
    def style_replacer(match):
        raw_styles = match.group(1)
        pairs = [p.strip() for p in raw_styles.split(';') if p.strip()]
        style_entries = []
        for pair in pairs:
            if ':' in pair:
                k, v = pair.split(':', 1)
                k = k.strip()
                v = v.strip().replace('"', '\\"')
                # convert kebab-case to camelCase
                camel_k = re.sub(r'-([a-z])', lambda m: m.group(1).upper(), k)
                style_entries.append(f'"{camel_k}": "{v}"')
        return "style={{" + ", ".join(style_entries) + "}}"

    jsx = re.sub(r'style="([^"]*)"', style_replacer, jsx)

    return jsx


def generate_course_page_files(
    course_slug: str,
    page_slug_hierarchy: list[str],
    page_title: str,
    course_title: str,
    html_content: str,
    blocks_data: list[dict] = None,
    custom_css: str = "",
    custom_js: str = "",
    breadcrumbs: list[dict] = None,
    prev_page: dict = None,
    next_page: dict = None,
    video_data: dict = None,
) -> dict:
    """
    Generates index.tsx, index.css, and index.js files for a published educational course page.
    Validates filesystem boundaries to prevent path traversal.
    """
    root_dir = get_skiltrix_generated_root()

    clean_course_slug = slugify(course_slug)
    clean_parts = [slugify(p) for p in page_slug_hierarchy if p]
    if not clean_parts:
        clean_parts = ["index"]

    target_rel_dir = Path(clean_course_slug).joinpath(*clean_parts)
    target_abs_dir = (root_dir / target_rel_dir).resolve()

    # Enforce path containment
    if not str(target_abs_dir).startswith(str(root_dir)):
        raise ValueError("Invalid target path: directory traversal attempt rejected.")

    target_abs_dir.mkdir(parents=True, exist_ok=True)

    # Paths
    tsx_file = target_abs_dir / "index.tsx"
    css_file = target_abs_dir / "index.css"
    js_file = target_abs_dir / "index.js"

    # Compute relative import path to components
    # e.g. depth 2 -> ../../../components/cms
    depth = len(clean_parts) + 1  # course_slug + each sub-part
    rel_prefix = "../" * (depth + 1) + "components"

    # 1. Write CSS file
    scoped_css = f"""/* Page-Specific Styles for: {page_title} */
.generated-page-container {{
  max-width: 1000px;
  margin: 0 auto;
  padding: 1.5rem 1rem 4rem;
  color: var(--text-color, #f8fafc);
}}

.generated-content h1, .generated-content h2, .generated-content h3 {{
  color: #ffffff;
  font-weight: 700;
  margin-top: 2rem;
  margin-bottom: 0.75rem;
}}

.generated-content p {{
  line-height: 1.75;
  margin-bottom: 1.25rem;
  color: #cbd5e1;
}}

.generated-content table {{
  width: 100%;
  border-collapse: collapse;
  margin: 1.5rem 0;
  overflow-x: auto;
  display: block;
}}

.generated-content table th, .generated-content table td {{
  border: 1px solid #334155;
  padding: 10px 14px;
  text-align: left;
}}

.generated-content table th {{
  background: #1e293b;
  color: #f1f5f9;
  font-weight: 600;
}}

.generated-content blockquote {{
  border-left: 4px solid #6366f1;
  padding-left: 1rem;
  margin: 1.5rem 0;
  color: #94a3b8;
  font-style: italic;
}}

{custom_css.strip()}
"""
    css_file.write_text(scoped_css, encoding="utf-8")

    # 2. Write JS file (if provided)
    if custom_js and custom_js.strip():
        js_file.write_text(custom_js.strip(), encoding="utf-8")
    else:
        js_file.write_text("// Page client utilities\nexport default {};\n", encoding="utf-8")

    # 3. Construct TSX React component
    jsx_content = html_to_jsx(html_content)

    # Breadcrumbs representation
    breadcrumbs_list = breadcrumbs or [
        {"label": "Courses", "to": "/courses"},
        {"label": course_title or clean_course_slug.replace("-", " ").title(), "to": f"/courses/{clean_course_slug}"},
        {"label": page_title},
    ]
    breadcrumbs_json = json.dumps(breadcrumbs_list)

    prev_json = json.dumps(prev_page) if prev_page else "undefined"
    next_json = json.dumps(next_page) if next_page else "undefined"

    video_block_jsx = ""
    # Only render top video banner if explicitly requested as a hero banner;
    # inline videos embedded in html_content render directly at their custom positions.
    if video_data and video_data.get("url") and video_data.get("is_hero_banner"):
        v_url = video_data.get("url", "").replace('"', '\\"')
        v_thumb = video_data.get("thumbnail", "").replace('"', '\\"')
        v_title = video_data.get("title", "Lecture Video").replace('"', '\\"')
        v_target = video_data.get("target", "_blank")
        video_block_jsx = f"""
        <div className="my-6">
          <YouTubeCard
            videoUrl="{v_url}"
            thumbnail="{v_thumb}"
            title="{v_title}"
            openInNewTab={{{'true' if v_target == '_blank' else 'false'}}}
          />
        </div>
        """

    safe_component_name = "".join(w.capitalize() for w in re.split(r"[\W_]+", f"{clean_course_slug}_{clean_parts[-1]}") if w) + "Page"

    tsx_content = f"""// AUTO-GENERATED COURSE PAGE: {page_title}
// Generated by Skiltrix WordPress-like Dynamic CMS Engine
// Do NOT edit directly; update from Skiltrix Admin Panel.

import React from 'react';
import CoursePageShell from '{rel_prefix}/cms/CoursePageShell';
import YouTubeCard from '{rel_prefix}/cms/YouTubeCard';
import './index.css';

export default function {safe_component_name}() {{
  return (
    <CoursePageShell
      title="{page_title.replace('"', '\\"')}"
      courseSlug="{clean_course_slug}"
      breadcrumbs={{{breadcrumbs_json}}}
      prevPage={{{prev_json}}}
      nextPage={{{next_json}}}
    >
      <div className="generated-page-container">
        {video_block_jsx}
        <div className="generated-content" dangerouslySetInnerHTML={{{{ __html: `{jsx_content.replace('`', '\\`').replace('$', '\\$')}` }}}} />
      </div>
    </CoursePageShell>
  );
}}
"""
    tsx_file.write_text(tsx_content, encoding="utf-8")

    base_dir = Path(settings.BASE_DIR).parent
    return {
        "file_path": str(tsx_file.relative_to(base_dir)),
        "css_path": str(css_file.relative_to(base_dir)),
        "js_path": str(js_file.relative_to(base_dir)),
        "abs_dir": str(target_abs_dir),
    }


def delete_course_page_files(file_path: str):
    """
    Safely removes the directory containing generated files for a deleted page.
    """
    root_dir = get_skiltrix_generated_root()
    if not file_path:
        return

    base_dir = Path(settings.BASE_DIR).parent
    full_path = (base_dir / file_path).resolve()

    if str(full_path).startswith(str(root_dir)) and full_path.exists():
        page_dir = full_path.parent
        if page_dir.is_dir() and page_dir != root_dir:
            shutil.rmtree(page_dir, ignore_errors=True)


def update_cms_manifest():
    """
    Compiles all published CmsPage records into skiltrix/src/generated-courses/manifest.json.
    """
    from .cms_models import CmsPage, CmsCourse

    root_dir = get_skiltrix_generated_root()
    manifest_file = root_dir / "manifest.json"

    published_pages = CmsPage.objects.filter(status="published").select_related("course", "parent", "prev_page", "next_page")

    manifest = {}
    for p in published_pages:
        clean_url = p.url_path.strip("/")
        manifest[clean_url] = {
            "pageId": p.page_id,
            "courseId": p.course.course_id,
            "courseSlug": p.course.slug,
            "courseTitle": p.course.title,
            "title": p.title,
            "slug": p.slug,
            "urlPath": p.url_path,
            "filePath": p.file_path,
            "order": p.page_order,
            "parentId": p.parent.page_id if p.parent else None,
            "prev": {
                "title": p.prev_page.title,
                "path": p.prev_page.url_path,
            } if p.prev_page else None,
            "next": {
                "title": p.next_page.title,
                "path": p.next_page.url_path,
            } if p.next_page else None,
            "seo": {
                "title": p.seo_title or f"{p.title} - {p.course.title}",
                "description": p.seo_description,
            },
            "video": {
                "title": p.video_title,
                "url": p.video_url,
                "thumbnail": p.video_thumbnail,
                "target": p.video_target,
            } if p.video_url else None,
        }

    manifest_file.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest
