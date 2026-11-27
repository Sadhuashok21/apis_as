import json
import tempfile
from pathlib import Path
from unittest.mock import patch
from django.test import TestCase
from rest_framework.test import APIClient

from apis.cdn_utils import get_st_image_url
from sfs.models import AllUsers
from skiltrix.cms_generator import jsx_to_html
from skiltrix.cms_models import CmsCourse, CmsPage
from skiltrix.models import Courses


class CmsAndCatalogCourseImageTests(TestCase):
    def setUp(self):
        self.client_api = APIClient()
        self.user = AllUsers.objects.create(
            user_id="usr_course_img_test",
            username="courseimgtester",
            name="Course",
            lastname="Tester",
            email="courseimg@skiltrix.org",
            user_type="admin",
            platform="web",
            platform_name="skiltrix",
            type="admin",
            ip="127.0.0.1",
            status="approved",
        )

    def test_get_st_image_url_preserves_media_and_cdn_urls(self):
        self.assertEqual(
            get_st_image_url("cyber.png"),
            "https://cdn.ascentracoresolutions.com/st/images/cyber.png",
        )
        self.assertEqual(
            get_st_image_url("/media/st/images/cyber.png"),
            "/media/st/images/cyber.png",
        )
        self.assertEqual(
            get_st_image_url("https://cdn.ascentracoresolutions.com/st/images/cyber.png"),
            "https://cdn.ascentracoresolutions.com/st/images/cyber.png",
        )

    def test_cms_course_create_update_list_and_navigation_image(self):
        create_res = self.client.post(
            "/api/admin/cms/courses/",
            data=json.dumps({
                "title": "Cyber Security",
                "slug": "cyber-security",
                "category": "Programming",
                "image": "cyber-cover.png",
                "status": "published",
            }),
            content_type="application/json",
        )
        self.assertEqual(create_res.status_code, 200)
        created_data = create_res.json()
        self.assertTrue(created_data["status"])
        course_id = created_data["course"]["course_id"]
        self.assertEqual(created_data["course"]["image"], "cyber-cover.png")
        self.assertEqual(
            created_data["course"]["image_url"],
            "https://cdn.ascentracoresolutions.com/st/images/cyber-cover.png",
        )

        # Update course cover image via PUT
        updated_url = "/media/st/images/cyber-updated.webp"
        update_res = self.client.put(
            f"/api/admin/cms/courses/{course_id}/",
            data=json.dumps({"image": updated_url}),
            content_type="application/json",
        )
        self.assertEqual(update_res.status_code, 200)
        self.assertEqual(update_res.json()["course"]["image"], updated_url)
        self.assertEqual(update_res.json()["course"]["image_url"], updated_url)

        # Public CMS courses list returns image & image_url
        public_res = self.client.get("/api/cms/courses/")
        self.assertEqual(public_res.status_code, 200)
        courses = public_res.json()["courses"]
        matched = next(c for c in courses if c["course_id"] == course_id)
        self.assertEqual(matched["image"], updated_url)
        self.assertEqual(matched["image_url"], updated_url)

        # Navigation overview also returns course image
        nav_res = self.client.get("/api/cms/navigation/cyber-security/")
        self.assertEqual(nav_res.status_code, 200)
        self.assertEqual(nav_res.json()["course"]["image"], updated_url)
        self.assertEqual(nav_res.json()["course"]["image_url"], updated_url)

    def test_catalog_course_patch_preserves_long_cdn_image_url(self):
        course = Courses.objects.create(
            course_id="crs_img_test",
            name="Cyber Defense",
            image="initial.png",
            type="beginner",
            is_paid=False,
            price=0,
            user=self.user,
            status="active",
        )
        long_cdn_url = "https://cdn.ascentracoresolutions.com/st/images/very-long-course-cover-filename-123456.webp"
        self.client_api.force_authenticate(user=self.user)
        res = self.client_api.patch(
            f"/apps/skiltrix/api/courses/{course.course_id}/",
            data={"image": long_cdn_url},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        course.refresh_from_db()
        self.assertEqual(course.image, long_cdn_url)
        self.assertEqual(res.json()["image_url"], long_cdn_url)

    def test_publish_cms_page_avoids_duplicate_course_or_page_breadcrumbs(self):
        course = CmsCourse.objects.create(
            course_id="crs_crumb_test",
            title="Cyber Security",
            slug="cyber-security-crumb",
            status="published",
        )
        parent_page = CmsPage.objects.create(
            page_id="pg_parent_1",
            course=course,
            title="Module 1",
            slug="module-1",
            url_path="/courses/cyber-security-crumb/module-1/",
            file_path="skiltrix/src/generated-courses/cyber-security-crumb/module-1/index.tsx",
            css_path="skiltrix/src/generated-courses/cyber-security-crumb/module-1/index.css",
            status="published",
        )
        leaf_page = CmsPage.objects.create(
            page_id="pg_leaf_1",
            course=course,
            parent=parent_page,
            title="Untitled Page",
            slug="untitled-page",
            url_path="/courses/cyber-security-crumb/module-1/untitled-page/",
            file_path="skiltrix/src/generated-courses/cyber-security-crumb/module-1/untitled-page/index.tsx",
            css_path="skiltrix/src/generated-courses/cyber-security-crumb/module-1/untitled-page/index.css",
            status="draft",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_root = Path(tmpdir)
            with patch("skiltrix.cms_generator.get_skiltrix_generated_root", return_value=tmp_root), \
                 patch("skiltrix.cms_views.get_skiltrix_generated_root", return_value=tmp_root), \
                 patch("skiltrix.cms_generator.settings.BASE_DIR", str(tmp_root / "apis")):
                res = self.client.post(
                    f"/api/admin/cms/pages/{leaf_page.page_id}/publish/",
                    data=json.dumps({"html_content": "<p>Hello</p>"}),
                    content_type="application/json",
                )
                self.assertEqual(res.status_code, 200)
                generated_tsx = (tmp_root / "cyber-security-crumb" / "module-1" / "untitled-page" / "index.tsx").read_text(encoding="utf-8")
                self.assertIn('courseTitle="Cyber Security"', generated_tsx)
                self.assertIn(
                    'breadcrumbs={[{"label": "Module 1", "to": "/courses/cyber-security-crumb/module-1"}]}',
                    generated_tsx,
                )
                self.assertNotIn('"label": "Courses"', generated_tsx)
                self.assertNotIn('"label": "Untitled Page"', generated_tsx)

                # Renaming page slug from untitled-page updates DB slug and url_path cleanly
                update_res = self.client.put(
                    f"/api/admin/cms/pages/{leaf_page.page_id}/",
                    data=json.dumps({
                        "title": "Network Firewalls",
                        "slug": "network-firewalls",
                        "parent_id": parent_page.page_id,
                    }),
                    content_type="application/json",
                )
                self.assertEqual(update_res.status_code, 200)
                leaf_page.refresh_from_db()
                self.assertEqual(leaf_page.slug, "network-firewalls")
                self.assertEqual(
                    leaf_page.url_path,
                    "/courses/cyber-security-crumb/module-1/network-firewalls/",
                )

                # Explicit prev/next navigation links persist and can be cleared cleanly
                pub_with_prev = self.client.post(
                    f"/api/admin/cms/pages/{leaf_page.page_id}/publish/",
                    data=json.dumps({
                        "html_content": "<p>Updated</p>",
                        "prev_page_id": parent_page.page_id,
                        "next_page_id": "",
                    }),
                    content_type="application/json",
                )
                self.assertEqual(pub_with_prev.status_code, 200)
                leaf_page.refresh_from_db()
                self.assertEqual(leaf_page.prev_page_id, parent_page.id)
                self.assertIsNone(leaf_page.next_page_id)

                pub_cleared = self.client.post(
                    f"/api/admin/cms/pages/{leaf_page.page_id}/publish/",
                    data=json.dumps({
                        "html_content": "<p>Updated</p>",
                        "prev_page_id": None,
                        "next_page_id": None,
                    }),
                    content_type="application/json",
                )
                self.assertEqual(pub_cleared.status_code, 200)
                leaf_page.refresh_from_db()
                self.assertIsNone(leaf_page.prev_page_id)

                # Code blocks and inline-styled HTML keep valid HTML attributes inside dangerouslySetInnerHTML
                code_html = (
                    '<div class="cms-code-block" data-lang="bash" '
                    'style="background: #0f172a; border-radius: 10px;">'
                    '<div class="code-body" style="display: flex;">'
                    '<pre><code class="language-bash">cd "ashok"</code></pre>'
                    '</div></div>'
                )
                pub_code = self.client.post(
                    f"/api/admin/cms/pages/{leaf_page.page_id}/publish/",
                    data=json.dumps({"html_content": code_html}),
                    content_type="application/json",
                )
                self.assertEqual(pub_code.status_code, 200)
                code_tsx = (
                    tmp_root / "cyber-security-crumb" / "module-1" / "network-firewalls" / "index.tsx"
                ).read_text(encoding="utf-8")
                self.assertIn('class="cms-code-block"', code_tsx)
                self.assertIn('style="background: #0f172a; border-radius: 10px;"', code_tsx)
                self.assertNotIn("className=", code_tsx.split("__html:", 1)[1])

                # Legacy JSX-mangled stored HTML restores to valid HTML attributes cleanly
                repaired = jsx_to_html(
                    '<div className="cms-code-block" style={{"backgroundColor": "#0f172a", "borderRadius": "10px"}}>hi</div>'
                )
                self.assertIn('class="cms-code-block"', repaired)
                self.assertIn('background-color: #0f172a; border-radius: 10px;', repaired)
