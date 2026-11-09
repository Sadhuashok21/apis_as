import os
import sys
import django
from pathlib import Path

# Setup Django environment
sys.path.append(r'C:\Users\ssimu\OneDrive\Desktop\web\main\apis')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'apis.settings')
django.setup()

from skiltrix.cms_models import CmsCourse, CmsPage
from skiltrix.cms_generator import generate_course_page_files, update_cms_manifest

def run_e2e_verification():
    print("=== STARTING CMS END-TO-END VERIFICATION ===")

    # 1. Create or get C Programming course
    course, created = CmsCourse.objects.get_or_create(
        slug="c-programming",
        defaults={
            "title": "C Programming Masterclass",
            "description": "Comprehensive course on C programming from variables to pointers.",
            "category": "Systems Programming",
            "status": "published",
            "order": 1
        }
    )
    print(f"[OK] Course ready: {course.title} (ID: {course.course_id}, slug: {course.slug})")

    # 2. Create or get "Variables in C" page
    page, p_created = CmsPage.objects.get_or_create(
        course=course,
        slug="variables",
        defaults={
            "title": "Variables in C Programming",
            "page_order": 1,
            "status": "draft",
            "url_path": "/courses/c-programming/variables/"
        }
    )
    print(f"[OK] Page metadata ready: {page.title} (ID: {page.page_id})")

    # 3. Prepare educational content elements (Code Block, Video, Topics, Callouts, Table)
    educational_html = """
    <h2>1. Understanding Variables in C</h2>
    <p>A variable is simply a named location in memory used to hold a value that can be modified during the execution of a program. In C, every variable must have a declared data type before it can be used.</p>

    <!-- Information Callout -->
    <div class="cms-callout-info" style="margin: 20px 0; padding: 16px; border-radius: 10px; background: rgba(59, 130, 246, 0.1); border-left: 4px solid #3b82f6; color: #93c5fd;">
        <strong>Quick Rule:</strong> Variable names in C can contain letters, digits, and underscores, but must begin with a letter or underscore. C is case-sensitive!
    </div>

    <!-- YouTube Video Card -->
    <div class="cms-youtube-card" style="margin: 28px 0; border-radius: 12px; overflow: hidden; background: #070b13; border: 1px solid #1e293b; box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.5);">
        <a href="https://www.youtube.com/watch?v=7_uM3v0a2Ew" target="_blank" rel="noopener noreferrer" style="display: block; position: relative; text-decoration: none;">
            <div style="position: relative; padding-top: 56.25%; width: 100%; background: #020617;">
                <img src="/yt_img.jpg" alt="C Variables Explained in 10 Minutes" style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; object-fit: cover;" />
                <div style="position: absolute; top: 0; left: 0; right: 0; bottom: 0; display: flex; align-items: center; justify-content: center;">
                    <div style="width: 64px; height: 64px; border-radius: 50%; background: rgba(220, 38, 38, 0.9); display: flex; align-items: center; justify-content: center; box-shadow: 0 0 20px rgba(220, 38, 38, 0.6);">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="white"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
                    </div>
                </div>
            </div>
            <div style="padding: 14px 18px; background: #0b1120; border-top: 1px solid #1e293b; display: flex; justify-content: space-between; align-items: center;">
                <span style="color: #f1f5f9; font-weight: 600; font-size: 14px;">Watch: C Variables Explained Step-by-Step</span>
                <span style="color: #818cf8; font-size: 12px; font-weight: 600;">Open on YouTube &rarr;</span>
            </div>
        </a>
    </div>

    <!-- Code Block with Copy Icon -->
    <h3>C Variable Declaration Example</h3>
    <div class="cms-code-block" style="margin: 20px 0; border-radius: 10px; overflow: hidden; border: 1px solid #1e293b; background: #0d1117;">
        <div style="display: flex; justify-content: space-between; align-items: center; padding: 10px 16px; background: #161b22; border-bottom: 1px solid #1e293b; font-size: 12px; color: #94a3b8; font-family: monospace;">
            <span style="font-weight: 600; color: #f1f5f9;">variables_example.c</span>
            <span style="background: rgba(99, 102, 241, 0.15); color: #818cf8; padding: 2px 8px; border-radius: 4px; font-size: 11px;">C</span>
        </div>
        <pre style="margin: 0; padding: 16px; overflow-x: auto; font-family: monospace; font-size: 13.5px; line-height: 1.6; color: #f8fafc; background: #090d13;"><code>#include &lt;stdio.h&gt;

int main() {
    int age = 21;
    float gpa = 3.85;
    char grade = 'A';
    double salary = 85000.50;

    printf("Age: %d\\n", age);
    printf("GPA: %.2f\\n", gpa);
    printf("Grade: %c\\n", grade);
    printf("Salary: $%.2f\\n", salary);

    return 0;
}</code></pre>
    </div>

    <!-- Comparison Table -->
    <h3>Fundamental C Data Types & Memory Sizes</h3>
    <table style="width: 100%; border-collapse: collapse; margin: 20px 0; font-size: 14px;">
        <thead>
            <tr style="background: #1e293b; color: #f1f5f9;">
                <th style="padding: 10px 14px; border: 1px solid #334155; text-align: left;">Type</th>
                <th style="padding: 10px 14px; border: 1px solid #334155; text-align: left;">Size in Bytes</th>
                <th style="padding: 10px 14px; border: 1px solid #334155; text-align: left;">Format Specifier</th>
                <th style="padding: 10px 14px; border: 1px solid #334155; text-align: left;">Typical Range</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td style="padding: 8px 14px; border: 1px solid #334155; font-family: monospace; color: #818cf8;">int</td>
                <td style="padding: 8px 14px; border: 1px solid #334155;">4 bytes</td>
                <td style="padding: 8px 14px; border: 1px solid #334155; font-family: monospace;">%d or %i</td>
                <td style="padding: 8px 14px; border: 1px solid #334155;">-2,147,483,648 to 2,147,483,647</td>
            </tr>
            <tr>
                <td style="padding: 8px 14px; border: 1px solid #334155; font-family: monospace; color: #818cf8;">float</td>
                <td style="padding: 8px 14px; border: 1px solid #334155;">4 bytes</td>
                <td style="padding: 8px 14px; border: 1px solid #334155; font-family: monospace;">%f</td>
                <td style="padding: 8px 14px; border: 1px solid #334155;">1.2E-38 to 3.4E+38</td>
            </tr>
            <tr>
                <td style="padding: 8px 14px; border: 1px solid #334155; font-family: monospace; color: #818cf8;">char</td>
                <td style="padding: 8px 14px; border: 1px solid #334155;">1 byte</td>
                <td style="padding: 8px 14px; border: 1px solid #334155; font-family: monospace;">%c</td>
                <td style="padding: 8px 14px; border: 1px solid #334155;">-128 to 127 or 0 to 255</td>
            </tr>
            <tr>
                <td style="padding: 8px 14px; border: 1px solid #334155; font-family: monospace; color: #818cf8;">double</td>
                <td style="padding: 8px 14px; border: 1px solid #334155;">8 bytes</td>
                <td style="padding: 8px 14px; border: 1px solid #334155; font-family: monospace;">%lf</td>
                <td style="padding: 8px 14px; border: 1px solid #334155;">2.3E-308 to 1.7E+308</td>
            </tr>
        </tbody>
    </table>

    <!-- 32 Variable Topics Cards Grid -->
    <h3>Explore All Variable Subtopics</h3>
    <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 12px; margin: 20px 0;">
        <a href="/courses/c-programming/variables/integer/" style="display: block; padding: 12px; border-radius: 8px; background: #0f172a; border: 1px solid #1e293b; text-decoration: none; color: inherit;">
            <div style="font-size: 11px; font-weight: 700; color: #818cf8; margin-bottom: 4px;">#1 TOPIC</div>
            <div style="font-weight: 600; font-size: 13px; color: #f1f5f9; margin-bottom: 4px;">Integer Variables</div>
            <div style="font-size: 11px; color: #94a3b8;">Signed and unsigned 32-bit whole numbers.</div>
        </a>
        <a href="/courses/c-programming/variables/float/" style="display: block; padding: 12px; border-radius: 8px; background: #0f172a; border: 1px solid #1e293b; text-decoration: none; color: inherit;">
            <div style="font-size: 11px; font-weight: 700; color: #818cf8; margin-bottom: 4px;">#2 TOPIC</div>
            <div style="font-weight: 600; font-size: 13px; color: #f1f5f9; margin-bottom: 4px;">Floating Point Variables</div>
            <div style="font-size: 11px; color: #94a3b8;">Single-precision decimal numbers.</div>
        </a>
        <a href="/courses/c-programming/variables/char/" style="display: block; padding: 12px; border-radius: 8px; background: #0f172a; border: 1px solid #1e293b; text-decoration: none; color: inherit;">
            <div style="font-size: 11px; font-weight: 700; color: #818cf8; margin-bottom: 4px;">#3 TOPIC</div>
            <div style="font-weight: 600; font-size: 13px; color: #f1f5f9; margin-bottom: 4px;">Character Variables</div>
            <div style="font-size: 11px; color: #94a3b8;">ASCII character storage and byte codes.</div>
        </a>
        <a href="/courses/c-programming/variables/double/" style="display: block; padding: 12px; border-radius: 8px; background: #0f172a; border: 1px solid #1e293b; text-decoration: none; color: inherit;">
            <div style="font-size: 11px; font-weight: 700; color: #818cf8; margin-bottom: 4px;">#4 TOPIC</div>
            <div style="font-weight: 600; font-size: 13px; color: #f1f5f9; margin-bottom: 4px;">Double Precision Variables</div>
            <div style="font-size: 11px; color: #94a3b8;">64-bit IEEE-754 precision math.</div>
        </a>
    </div>
    """

    custom_css = """
    .cms-callout-info {
        transition: transform 0.2s ease;
    }
    .cms-callout-info:hover {
        transform: translateX(4px);
    }
    """

    # 4. Generate physical files into skiltrix/src/generated-courses/c-programming/variables/
    gen_result = generate_course_page_files(
        course_slug=course.slug,
        page_slug_hierarchy=["variables"],
        page_title=page.title,
        course_title=course.title,
        html_content=educational_html,
        custom_css=custom_css,
        custom_js="// Variables Page Script\nconsole.log('C Variables Page Initialized');\n",
        breadcrumbs=[
            {"label": "Courses", "to": "/courses"},
            {"label": "C Programming", "to": "/courses/c-programming/"},
            {"label": "Variables in C"}
        ],
        prev_page={"title": "Introduction to C", "url": "/courses/c-programming/intro/"},
        next_page={"title": "Data Types in C", "url": "/courses/c-programming/data-types/"},
        video_data={
            "url": "https://www.youtube.com/watch?v=7_uM3v0a2Ew",
            "thumbnail": "/yt_img.jpg",
            "title": "C Variables Explained",
            "target": "_blank"
        }
    )

    print(f"[OK] Physical files generated successfully:")
    print(f"     TSX file: {gen_result['file_path']}")
    print(f"     CSS file: {gen_result['css_path']}")
    print(f"     JS file:  {gen_result['js_path']}")

    # 5. Save ONLY metadata in MySQL (ZERO body HTML!)
    page.file_path = gen_result["file_path"]
    page.css_path = gen_result["css_path"]
    page.js_path = gen_result["js_path"]
    page.status = "published"
    page.video_url = "https://www.youtube.com/watch?v=7_uM3v0a2Ew"
    page.video_thumbnail = "/yt_img.jpg"
    page.video_title = "C Variables Explained"
    page.save()

    print("[OK] Page metadata saved in MySQL table st_cms_pages.")

    # 6. Update manifest.json
    manifest_path = update_cms_manifest()
    print(f"[OK] Manifest updated: {manifest_path}")

    # 7. Verify generated files exist on disk
    base_dir = Path(r"C:\Users\ssimu\OneDrive\Desktop\web\main")
    tsx_disk = base_dir / gen_result['file_path']
    css_disk = base_dir / gen_result['css_path']
    js_disk = base_dir / gen_result['js_path']

    assert tsx_disk.exists(), f"TSX file missing: {tsx_disk}"
    assert css_disk.exists(), f"CSS file missing: {css_disk}"
    assert js_disk.exists(), f"JS file missing: {js_disk}"
    print(f"[OK] Verified physical disk presence: {tsx_disk.stat().st_size} bytes TSX")

    # 8. Verify NO educational HTML in database
    # Check model fields of CmsPage to verify no body content field exists
    page_fields = [f.name for f in CmsPage._meta.get_fields()]
    assert "content" not in page_fields and "html_content" not in page_fields and "body" not in page_fields, (
        f"Database contains content field! Fields: {page_fields}"
    )
    print(f"[OK] Database schema verified: ZERO educational body HTML stored in database! Metadata only: {page_fields}")

    print("\n=== E2E VERIFICATION COMPLETED WITH 100% SUCCESS ===")

if __name__ == '__main__':
    run_e2e_verification()
