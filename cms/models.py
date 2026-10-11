from django.db import models
from django.utils import timezone


class Category(models.Model):
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True)
    description = models.TextField(blank=True)
    meta_title = models.CharField(max_length=255, blank=True)
    meta_description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Tag(models.Model):
    name = models.CharField(max_length=60)
    slug = models.SlugField(max_length=80, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Author(models.Model):
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True)
    bio = models.TextField(blank=True)
    profile_image = models.CharField(max_length=500, blank=True, help_text="Image URL or static path")
    role = models.CharField(max_length=120, default="Software Engineer", blank=True)
    email = models.EmailField(blank=True)
    twitter_url = models.URLField(blank=True)
    linkedin_url = models.URLField(blank=True)
    github_url = models.URLField(blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class BlogPost(models.Model):
    STATUS_CHOICES = (
        ("draft", "Draft"),
        ("published", "Published"),
        ("scheduled", "Scheduled"),
    )

    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    excerpt = models.TextField(blank=True, help_text="Short teaser paragraph for previews & search")
    content = models.TextField(help_text="Full markdown or formatted article content")
    featured_image = models.CharField(max_length=500, blank=True, help_text="Image URL or asset path")
    author = models.ForeignKey(Author, on_delete=models.SET_NULL, null=True, blank=True, related_name="posts")
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name="posts")
    tags = models.ManyToManyField(Tag, blank=True, related_name="posts")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    published_at = models.DateTimeField(null=True, blank=True)
    reading_time = models.PositiveIntegerField(default=5, help_text="Estimated reading time in minutes")
    meta_title = models.CharField(max_length=255, blank=True)
    meta_description = models.TextField(blank=True)
    canonical_url = models.URLField(blank=True)
    views_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-published_at", "-created_at"]
        verbose_name = "Blog Post"
        verbose_name_plural = "Blog Posts"

    def __str__(self):
        return self.title

    def is_public(self):
        if self.status != "published":
            return False
        if self.published_at and self.published_at > timezone.now():
            return False
        return True


class Tutorial(models.Model):
    CATEGORY_CHOICES = (
        ("java", "Java"),
        ("python", "Python"),
        ("django", "Django"),
        ("react", "React"),
        ("javascript", "JavaScript"),
        ("typescript", "TypeScript"),
        ("linux", "Linux"),
        ("dsa", "DSA"),
        ("aiml", "AI/ML"),
        ("android", "Android"),
        ("aws", "AWS"),
        ("databases", "Databases"),
    )

    DIFFICULTY_CHOICES = (
        ("beginner", "Beginner"),
        ("intermediate", "Intermediate"),
        ("advanced", "Advanced"),
    )

    STATUS_CHOICES = (
        ("draft", "Draft"),
        ("published", "Published"),
    )

    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255)
    category = models.CharField(max_length=40, choices=CATEGORY_CHOICES)
    introduction = models.TextField(blank=True)
    content = models.TextField(help_text="Complete tutorial documentation, instructions & deep dive")
    code_examples = models.TextField(blank=True, help_text="Key code snippets and runnable examples")
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES, default="beginner")
    author = models.ForeignKey(Author, on_delete=models.SET_NULL, null=True, blank=True, related_name="tutorials")
    published_date = models.DateTimeField(null=True, blank=True)
    updated_date = models.DateTimeField(auto_now=True)
    estimated_reading_time = models.PositiveIntegerField(default=8, help_text="Minutes")
    related_tutorials = models.ManyToManyField("self", symmetrical=False, blank=True)
    meta_title = models.CharField(max_length=255, blank=True)
    meta_description = models.TextField(blank=True)
    canonical_url = models.URLField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="published")
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = (("category", "slug"),)
        ordering = ["category", "order", "-published_date"]
        verbose_name = "Tutorial"
        verbose_name_plural = "Tutorials"

    def __str__(self):
        return f"[{self.get_category_display()}] {self.title}"


class Resource(models.Model):
    RESOURCE_TYPE_CHOICES = (
        ("cheatsheet", "Cheat Sheet"),
        ("guide", "Programming Guide"),
        ("interview_prep", "Interview Resource"),
        ("dsa_guide", "DSA Resource"),
        ("dev_tools", "Developer Tool"),
        ("roadmap", "Learning Roadmap"),
        ("download", "Download"),
        ("documentation", "Documentation"),
    )

    STATUS_CHOICES = (
        ("draft", "Draft"),
        ("published", "Published"),
    )

    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    resource_type = models.CharField(max_length=40, choices=RESOURCE_TYPE_CHOICES)
    description = models.TextField()
    content = models.TextField(blank=True, help_text="Markdown or rich reference content")
    badge_text = models.CharField(max_length=50, blank=True)
    download_url = models.CharField(max_length=500, blank=True)
    external_url = models.CharField(max_length=500, blank=True)
    tags = models.ManyToManyField(Tag, blank=True, related_name="resources")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="published")
    featured = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order", "-created_at"]
        verbose_name = "Resource"
        verbose_name_plural = "Resources"

    def __str__(self):
        return f"[{self.get_resource_type_display()}] {self.title}"


class CaseStudy(models.Model):
    STATUS_CHOICES = (
        ("draft", "Draft"),
        ("published", "Published"),
    )

    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    project_name = models.CharField(max_length=120, help_text="e.g. SkilTrix, SFS Blueprints, SonicOra, Transport Hub")
    client_or_type = models.CharField(max_length=120, default="Internal SaaS Product")
    summary = models.TextField()
    background = models.TextField()
    problem = models.TextField()
    solution = models.TextField()
    technology_used = models.JSONField(default=list, help_text="List of technologies: ['Django', 'React', 'Docker']")
    architecture = models.TextField()
    development_process = models.TextField()
    challenges = models.TextField()
    results = models.TextField()
    lessons_learned = models.TextField()
    cover_image = models.CharField(max_length=500, blank=True)
    live_url = models.CharField(max_length=500, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="published")
    featured = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order", "-created_at"]
        verbose_name = "Case Study"
        verbose_name_plural = "Case Studies"

    def __str__(self):
        return f"{self.project_name}: {self.title}"


class Product(models.Model):
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True)
    tagline = models.CharField(max_length=255, blank=True)
    description = models.TextField()
    features = models.JSONField(default=list, help_text="List of key feature bullets")
    screenshots = models.JSONField(default=list, help_text="List of screenshot image URLs")
    technologies = models.JSONField(default=list, help_text="Tech stack list")
    status = models.CharField(max_length=40, default="Production")
    website_url = models.CharField(max_length=500, blank=True)
    app_url = models.CharField(max_length=500, blank=True)
    documentation_url = models.CharField(max_length=500, blank=True)
    github_url = models.CharField(max_length=500, blank=True)
    featured = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order", "name"]
        verbose_name = "Product"
        verbose_name_plural = "Products"

    def __str__(self):
        return self.name


class Service(models.Model):
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True)
    short_description = models.TextField()
    full_description = models.TextField()
    icon_name = models.CharField(max_length=50, default="code")
    benefits = models.JSONField(default=list, help_text="List of benefits")
    deliverables = models.JSONField(default=list, help_text="Key deliverables")
    technologies = models.JSONField(default=list, help_text="Stack tags")
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order", "name"]
        verbose_name = "Service"
        verbose_name_plural = "Services"

    def __str__(self):
        return self.name


class FAQ(models.Model):
    CATEGORY_CHOICES = (
        ("general", "General"),
        ("services", "Services & Engineering"),
        ("products", "Products & Platforms"),
        ("support", "Support & Hiring"),
    )

    question = models.CharField(max_length=300)
    answer = models.TextField()
    category = models.CharField(max_length=40, choices=CATEGORY_CHOICES, default="general")
    order = models.PositiveIntegerField(default=0)
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ["category", "order"]
        verbose_name = "FAQ"
        verbose_name_plural = "FAQs"

    def __str__(self):
        return self.question


class SiteSetting(models.Model):
    site_name = models.CharField(max_length=120, default="Ascentracore Solutions")
    tagline = models.CharField(max_length=255, default="Software Development, Developer Tools & Engineering Platforms")
    hero_heading = models.CharField(max_length=255, default="Engineering Scalable Systems, Developer Tools & High-Value Learning Platforms")
    hero_subheading = models.TextField(default="Ascentracore Solutions builds high-performance web systems, cloud infrastructure, compiler toolchains, and interactive technical education resources.")
    contact_email = models.EmailField(default="contact@ascentracoresolutions.com")
    contact_phone = models.CharField(max_length=50, default="+916305096514")
    address = models.CharField(max_length=255, default="India")
    meta_title = models.CharField(max_length=255, default="Ascentracore Solutions | Software Engineering & Tech Resources")
    meta_description = models.TextField(default="Official website of Ascentracore Solutions: Custom software development, cloud infrastructure, SkilTrix coding platform, developer resources, and in-depth engineering tutorials.")

    def __str__(self):
        return self.site_name

    class Meta:
        verbose_name = "Site Setting"
        verbose_name_plural = "Site Settings"
