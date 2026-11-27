"""
Career Learning Roadmaps API for SkilTrix
Reproduces exactly the 7 career roadmaps and progress management from the SkilTrix Android App
(FrontendFragment, BackendFragment, FullStackFragment, PythonFullStackFragment,
 JavaFragment, AndroidFragment, CyberSecurityFragment, RoadmapStage, ProgressManager).
"""

import re
from django.utils.text import slugify
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from django.db import transaction
from .models import LearningRoadmap, LearningRoadmapProgress


# ==============================================================================
# 7 EXACT ROADMAP DEFINITIONS (FROM ANDROID SOURCE)
# ==============================================================================

OFFICIAL_ROADMAPS = [
    {
        "key": "frontend_roadmap",
        "title": "Frontend Web Roadmap",
        "category": "Web Development",
        "badge": "INFOGRAPHICS TIMELINE",
        "description": "Winding 3D visual journey to master HTML, CSS, JavaScript, React, Next.js, and Web Performance.",
        "icon": "code",
        "accent_color": "#F59E0B",
        "estimated_weeks": "12-16 Weeks",
        "stages": [
            {
                "stage_number": 1,
                "badge_text": "STEP 01",
                "title": "HTML5 & Modern CSS3",
                "description": "Semantic HTML, Flexbox, Grid, Responsive Design & Tailwind",
                "color": "#F59E0B",
                "difficulty": "Beginner",
                "estimated_hours": "15 Hours",
                "tutorial_link": "/tutorials/html",
                "practice_link": "/compilers/html-compiler",
                "topics": [
                    "Semantic Elements & Accessibility",
                    "Flexbox & CSS Grid Systems",
                    "Responsive Media Queries",
                    "Tailwind CSS & Utility Frameworks",
                ],
            },
            {
                "stage_number": 2,
                "badge_text": "STEP 02",
                "title": "JavaScript ES6+",
                "description": "DOM Manipulation, Async/Await, Promises & Fetch API",
                "color": "#10B981",
                "difficulty": "Beginner",
                "estimated_hours": "25 Hours",
                "tutorial_link": "/tutorials/javascript",
                "practice_link": "/compilers/javascript-compiler",
                "topics": [
                    "ES6+ Arrow Functions & Destructuring",
                    "DOM Events & Event Bubbling",
                    "Promises, Async / Await Syntax",
                    "Fetch API & LocalStorage Persistence",
                ],
            },
            {
                "stage_number": 3,
                "badge_text": "STEP 03",
                "title": "React & Component State",
                "description": "JSX, Hooks (useState, useEffect), Props & Context",
                "color": "#06B6D4",
                "difficulty": "Intermediate",
                "estimated_hours": "30 Hours",
                "tutorial_link": "/tutorials/react",
                "practice_link": "/codelab",
                "topics": [
                    "JSX & Component Driven Architecture",
                    "useState, useEffect & Custom Hooks",
                    "Context API & State Management",
                    "React Router Navigation",
                ],
            },
            {
                "stage_number": 4,
                "badge_text": "STEP 04",
                "title": "TypeScript & State Management",
                "description": "Type Safety, Redux Toolkit & Zustand",
                "color": "#3B82F6",
                "difficulty": "Intermediate",
                "estimated_hours": "20 Hours",
                "tutorial_link": "/tutorials/typescript",
                "practice_link": "/compilers/typescript-compiler",
                "topics": [
                    "TypeScript Interfaces, Types & Generics",
                    "Redux Toolkit / RTK Query",
                    "Zustand & Lightweight State",
                    "Formik / React Hook Form",
                ],
            },
            {
                "stage_number": 5,
                "badge_text": "STEP 05",
                "title": "Next.js & SSR/SSG",
                "description": "App Router, Server Components, SEO & API Routes",
                "color": "#8B5CF6",
                "difficulty": "Advanced",
                "estimated_hours": "25 Hours",
                "tutorial_link": "/tutorials/nextjs",
                "practice_link": "/codelab",
                "topics": [
                    "Next.js App Router Architecture",
                    "Server Side Rendering (SSR) & SSG",
                    "API Routes & Server Actions",
                    "SEO Optimization & Performance",
                ],
            },
            {
                "stage_number": 6,
                "badge_text": "STEP 06",
                "title": "Web Testing & Deployment",
                "description": "Jest, Playwright, Vercel CI/CD & Lighthouse",
                "color": "#EC4899",
                "difficulty": "Advanced",
                "estimated_hours": "15 Hours",
                "tutorial_link": "/tutorials/git",
                "practice_link": "/codelab",
                "topics": [
                    "Jest & React Testing Library",
                    "Playwright / Cypress E2E Testing",
                    "Lighthouse Performance & Core Web Vitals",
                    "Vercel & Netlify Deployment",
                ],
            },
        ],
    },
    {
        "key": "backend_roadmap",
        "title": "Backend Engineering Roadmap",
        "category": "Backend Development",
        "badge": "INFOGRAPHICS TIMELINE",
        "description": "Winding 3D learning path for building scalable APIs, databases, microservices, and cloud systems.",
        "icon": "server",
        "accent_color": "#10B981",
        "estimated_weeks": "14-18 Weeks",
        "stages": [
            {
                "stage_number": 1,
                "badge_text": "STEP 01",
                "title": "Core Language & Data Structures",
                "description": "Select Language (Node/Java/Go/Python) & Data Structures",
                "color": "#F59E0B",
                "difficulty": "Beginner",
                "estimated_hours": "30 Hours",
                "tutorial_link": "/tutorials/python",
                "practice_link": "/practice",
                "topics": [
                    "Language Fundamentals & Syntax",
                    "OOP & Design Patterns",
                    "Arrays, HashMaps, Trees & Algorithms",
                    "Memory & Thread Concurrency",
                ],
            },
            {
                "stage_number": 2,
                "badge_text": "STEP 02",
                "title": "Databases & ORMs",
                "description": "Relational SQL, NoSQL & Query Optimization",
                "color": "#10B981",
                "difficulty": "Beginner",
                "estimated_hours": "25 Hours",
                "tutorial_link": "/tutorials/sql",
                "practice_link": "/sql-practice",
                "topics": [
                    "PostgreSQL & Complex SQL Queries",
                    "MongoDB & Redis Key-Value Caching",
                    "Database Indexing & Transactions",
                    "ORMs: Hibernate / Prisma / SQLAlchemy",
                ],
            },
            {
                "stage_number": 3,
                "badge_text": "STEP 03",
                "title": "API Design & Security",
                "description": "REST, GraphQL, OAuth2 & JWT Authentication",
                "color": "#06B6D4",
                "difficulty": "Intermediate",
                "estimated_hours": "25 Hours",
                "tutorial_link": "/tutorials/node",
                "practice_link": "/codelab",
                "topics": [
                    "RESTful Principles & OpenAPI Standards",
                    "GraphQL Schemas & Queries",
                    "JWT Tokens & Session Management",
                    "Rate Limiting & CORS Gateways",
                ],
            },
            {
                "stage_number": 4,
                "badge_text": "STEP 04",
                "title": "Caching & Message Queues",
                "description": "Redis Caching, RabbitMQ & Kafka Event Streaming",
                "color": "#3B82F6",
                "difficulty": "Intermediate",
                "estimated_hours": "20 Hours",
                "tutorial_link": "/tutorials/redis",
                "practice_link": "/codelab",
                "topics": [
                    "Redis In-Memory Caching Strategies",
                    "RabbitMQ Message Queuing",
                    "Apache Kafka Event Streams",
                    "Monolith to Microservices Pattern",
                ],
            },
            {
                "stage_number": 5,
                "badge_text": "STEP 05",
                "title": "Docker, Kubernetes & Cloud",
                "description": "Containerization, AWS Services & Orchestration",
                "color": "#8B5CF6",
                "difficulty": "Advanced",
                "estimated_hours": "25 Hours",
                "tutorial_link": "/tutorials/docker",
                "practice_link": "/codelab",
                "topics": [
                    "Docker Containers & Compose",
                    "Kubernetes Cluster Management",
                    "AWS EC2, S3, RDS & Lambda",
                    "GitHub Actions CI/CD Pipelines",
                ],
            },
            {
                "stage_number": 6,
                "badge_text": "STEP 06",
                "title": "System Design & Observability",
                "description": "Scalability, Sharding & Prometheus Monitoring",
                "color": "#EC4899",
                "difficulty": "Advanced",
                "estimated_hours": "30 Hours",
                "tutorial_link": "/tutorials/system-design",
                "practice_link": "/practice",
                "topics": [
                    "High-Availability System Architecture",
                    "Database Sharding & Load Balancing",
                    "Prometheus & Grafana Monitoring",
                    "OWASP Security Hardening",
                ],
            },
        ],
    },
    {
        "key": "fullstack_roadmap",
        "title": "Full Stack Engineering Roadmap",
        "category": "Full Stack Development",
        "badge": "INFOGRAPHICS TIMELINE",
        "description": "Complete end-to-end 3D roadmap covering Frontend, Backend, Databases, DevOps, and Full-Stack App Deployment.",
        "icon": "layers",
        "accent_color": "#06B6D4",
        "estimated_weeks": "18-24 Weeks",
        "stages": [
            {
                "stage_number": 1,
                "badge_text": "STEP 01",
                "title": "Frontend Fundamentals",
                "description": "HTML5, CSS3, JavaScript ES6+ & Tailwind",
                "color": "#F59E0B",
                "difficulty": "Beginner",
                "estimated_hours": "25 Hours",
                "tutorial_link": "/tutorials/html",
                "practice_link": "/compilers/html-compiler",
                "topics": [
                    "HTML5 Semantics & Responsive Layouts",
                    "CSS Grid, Flexbox & Tailwind CSS",
                    "JavaScript DOM & ES6+ Syntax",
                    "Async/Await & Fetch API",
                ],
            },
            {
                "stage_number": 2,
                "badge_text": "STEP 02",
                "title": "React & Single Page Apps",
                "description": "Components, State, Hooks & React Router",
                "color": "#10B981",
                "difficulty": "Beginner",
                "estimated_hours": "30 Hours",
                "tutorial_link": "/tutorials/react",
                "practice_link": "/codelab",
                "topics": [
                    "React Components & Props",
                    "useState, useEffect & Custom Hooks",
                    "Context API & State Management",
                    "SPA Client Routing",
                ],
            },
            {
                "stage_number": 3,
                "badge_text": "STEP 03",
                "title": "Node.js & Express Backend",
                "description": "RESTful APIs, Express Middleware & Routing",
                "color": "#06B6D4",
                "difficulty": "Intermediate",
                "estimated_hours": "25 Hours",
                "tutorial_link": "/tutorials/node",
                "practice_link": "/codelab",
                "topics": [
                    "Node.js Runtime & NPM Modules",
                    "Express Server Setup & Middleware",
                    "RESTful Endpoints & Controller Pattern",
                    "Error Handling & Logging",
                ],
            },
            {
                "stage_number": 4,
                "badge_text": "STEP 04",
                "title": "Databases & Authentication",
                "description": "PostgreSQL, MongoDB, JWT & OAuth2",
                "color": "#3B82F6",
                "difficulty": "Intermediate",
                "estimated_hours": "20 Hours",
                "tutorial_link": "/tutorials/sql",
                "practice_link": "/sql-practice",
                "topics": [
                    "Relational SQL (PostgreSQL) & ORMs",
                    "NoSQL Document Stores (MongoDB)",
                    "JWT Token Authentication",
                    "Bcrypt Password Hashing",
                ],
            },
            {
                "stage_number": 5,
                "badge_text": "STEP 05",
                "title": "DevOps, Docker & Cloud",
                "description": "Containerization, CI/CD Pipelines & AWS",
                "color": "#8B5CF6",
                "difficulty": "Advanced",
                "estimated_hours": "25 Hours",
                "tutorial_link": "/tutorials/docker",
                "practice_link": "/codelab",
                "topics": [
                    "Dockerization of App Services",
                    "Docker Compose Multi-Container Setup",
                    "GitHub Actions Deployment CI/CD",
                    "AWS EC2, S3 & Nginx Reverse Proxy",
                ],
            },
            {
                "stage_number": 6,
                "badge_text": "STEP 06",
                "title": "Full-Stack Production App",
                "description": "Monorepo, Next.js, Microservices & Capstone Project",
                "color": "#EC4899",
                "difficulty": "Advanced",
                "estimated_hours": "35 Hours",
                "tutorial_link": "/tutorials/nextjs",
                "practice_link": "/codelab",
                "topics": [
                    "Next.js Full Stack App Architecture",
                    "Real-Time WebSockets / Socket.io",
                    "Stripe Payment Gateway Integration",
                    "Production Monitoring & Release",
                ],
            },
        ],
    },
    {
        "key": "python_fullstack_roadmap",
        "title": "Python Full Stack Roadmap",
        "category": "Full Stack Development",
        "badge": "INFOGRAPHICS TIMELINE",
        "description": "Serpentine 3D roadmap covering Python core, Django, FastAPI, PostgreSQL, React frontend, and Cloud deployment.",
        "icon": "terminal",
        "accent_color": "#3B82F6",
        "estimated_weeks": "16-20 Weeks",
        "stages": [
            {
                "stage_number": 1,
                "badge_text": "STEP 01",
                "title": "Python Language & OOP",
                "description": "Data Types, Functions, OOP, Decorators & Virtual Environments",
                "color": "#F59E0B",
                "difficulty": "Beginner",
                "estimated_hours": "25 Hours",
                "tutorial_link": "/tutorials/python",
                "practice_link": "/compilers/python-compiler",
                "topics": [
                    "Python Syntax, Data Structures & Comprehensions",
                    "OOP: Classes, Inheritance & Dunder Methods",
                    "Decorators, Generators & Context Managers",
                    "Virtual Environments & Pip Package Manager",
                ],
            },
            {
                "stage_number": 2,
                "badge_text": "STEP 02",
                "title": "Django Web Framework",
                "description": "MVT Pattern, ORM Models, Views, Templates & Admin",
                "color": "#10B981",
                "difficulty": "Beginner",
                "estimated_hours": "30 Hours",
                "tutorial_link": "/django-tutorials",
                "practice_link": "/codelab",
                "topics": [
                    "Django MVT Architecture & Project Setup",
                    "Django ORM Models & Migrations",
                    "Views, URLs & Template Engine",
                    "Django Admin Panel & User Authentication",
                ],
            },
            {
                "stage_number": 3,
                "badge_text": "STEP 03",
                "title": "Django REST Framework & FastAPI",
                "description": "REST Endpoints, Serializers, Pydantic & Async",
                "color": "#06B6D4",
                "difficulty": "Intermediate",
                "estimated_hours": "25 Hours",
                "tutorial_link": "/tutorials/fastapi",
                "practice_link": "/codelab",
                "topics": [
                    "Django REST Framework (DRF) Serializers",
                    "JWT Authentication & Permissions",
                    "FastAPI Async Endpoints & Pydantic",
                    "Swagger / OpenAPI Documentation",
                ],
            },
            {
                "stage_number": 4,
                "badge_text": "STEP 04",
                "title": "Databases & Celery Queues",
                "description": "PostgreSQL, Redis, Celery & Asynchronous Tasks",
                "color": "#3B82F6",
                "difficulty": "Intermediate",
                "estimated_hours": "20 Hours",
                "tutorial_link": "/tutorials/postgresql",
                "practice_link": "/sql-practice",
                "topics": [
                    "PostgreSQL Relational DB Configuration",
                    "Redis Caching & Session Storage",
                    "Celery Asynchronous Task Queues",
                    "Celery Beat Scheduled Background Jobs",
                ],
            },
            {
                "stage_number": 5,
                "badge_text": "STEP 05",
                "title": "Frontend Integration with React",
                "description": "React SPA, Axios Integration & JWT Auth Handling",
                "color": "#8B5CF6",
                "difficulty": "Advanced",
                "estimated_hours": "25 Hours",
                "tutorial_link": "/tutorials/react",
                "practice_link": "/codelab",
                "topics": [
                    "React Components & State Management",
                    "Axios HTTP Request Interceptors",
                    "JWT Token Storage & Refresh Flows",
                    "Tailwind CSS UI Styling",
                ],
            },
            {
                "stage_number": 6,
                "badge_text": "STEP 06",
                "title": "Docker & Cloud Deployment",
                "description": "Gunicorn, Nginx, Docker Compose, AWS & CI/CD",
                "color": "#EC4899",
                "difficulty": "Advanced",
                "estimated_hours": "20 Hours",
                "tutorial_link": "/tutorials/docker",
                "practice_link": "/codelab",
                "topics": [
                    "Dockerization of Django & React",
                    "Nginx Reverse Proxy & Gunicorn WSGI",
                    "AWS EC2 & S3 Media File Uploads",
                    "GitHub Actions Production Deployment",
                ],
            },
        ],
    },
    {
        "key": "java_roadmap",
        "title": "Java Developer Roadmap",
        "category": "Enterprise Development",
        "badge": "INFOGRAPHICS TIMELINE",
        "description": "3D winding infographic path from Java SE Core, Collections, Multithreading to Spring Boot Enterprise Microservices.",
        "icon": "coffee",
        "accent_color": "#F59E0B",
        "estimated_weeks": "16-20 Weeks",
        "stages": [
            {
                "stage_number": 1,
                "badge_text": "STEP 01",
                "title": "Java SE Core & OOP",
                "description": "Syntax, Data Types, Control Flow, OOP & Exception Handling",
                "color": "#F59E0B",
                "difficulty": "Beginner",
                "estimated_hours": "30 Hours",
                "tutorial_link": "/tutorials/java",
                "practice_link": "/compilers/java-compiler",
                "topics": [
                    "Java Virtual Machine (JVM) & JDK Setup",
                    "OOP: Classes, Interfaces & Polymorphism",
                    "Exception Handling & Custom Exceptions",
                    "Generics, Enums & Memory Management",
                ],
            },
            {
                "stage_number": 2,
                "badge_text": "STEP 02",
                "title": "Collections & Streams API",
                "description": "List, Set, Map, Lambda Expressions & Functional Streams",
                "color": "#10B981",
                "difficulty": "Beginner",
                "estimated_hours": "25 Hours",
                "tutorial_link": "/tutorials/java",
                "practice_link": "/compilers/java-compiler",
                "topics": [
                    "ArrayList, LinkedList, HashSet & HashMap",
                    "Java 8 Lambda Expressions & Functional Interfaces",
                    "Stream API Filtering, Mapping & Reduction",
                    "Optional Class & Null Handling",
                ],
            },
            {
                "stage_number": 3,
                "badge_text": "STEP 03",
                "title": "Concurrency & Multithreading",
                "description": "Threads, ExecutorService, Concurrent Collections & Locks",
                "color": "#06B6D4",
                "difficulty": "Intermediate",
                "estimated_hours": "25 Hours",
                "tutorial_link": "/tutorials/java",
                "practice_link": "/compilers/java-compiler",
                "topics": [
                    "Thread Creation, Runnable & Lifecycle",
                    "Synchronization & Reentrant Locks",
                    "ExecutorService Thread Pools & Futures",
                    "CompletableFuture Concurrent Programming",
                ],
            },
            {
                "stage_number": 4,
                "badge_text": "STEP 04",
                "title": "Spring Framework & Spring Boot",
                "description": "Dependency Injection, Spring MVC & REST APIs",
                "color": "#3B82F6",
                "difficulty": "Intermediate",
                "estimated_hours": "30 Hours",
                "tutorial_link": "/tutorials/spring-boot",
                "practice_link": "/codelab",
                "topics": [
                    "Spring Inversion of Control (IoC) & Beans",
                    "Spring Boot Auto-Configuration",
                    "Spring MVC Controller REST Endpoints",
                    "Jackson JSON Serialization",
                ],
            },
            {
                "stage_number": 5,
                "badge_text": "STEP 05",
                "title": "Spring Data JPA & Security",
                "description": "Hibernate ORM, PostgreSQL & Spring Security JWT",
                "color": "#8B5CF6",
                "difficulty": "Advanced",
                "estimated_hours": "25 Hours",
                "tutorial_link": "/tutorials/spring-boot",
                "practice_link": "/codelab",
                "topics": [
                    "Spring Data JPA & Hibernate Entities",
                    "PostgreSQL Database Relationships",
                    "Spring Security Authentication & Filters",
                    "JWT Token Role-Based Security",
                ],
            },
            {
                "stage_number": 6,
                "badge_text": "STEP 06",
                "title": "Spring Cloud & Microservices",
                "description": "Eureka, API Gateway, Docker & JUnit Testing",
                "color": "#EC4899",
                "difficulty": "Advanced",
                "estimated_hours": "30 Hours",
                "tutorial_link": "/tutorials/system-design",
                "practice_link": "/codelab",
                "topics": [
                    "Spring Cloud Eureka Service Discovery",
                    "Spring Cloud API Gateway & Resilience4j",
                    "Dockerizing Spring Boot Services",
                    "Unit Testing with JUnit 5 & Mockito",
                ],
            },
        ],
    },
    {
        "key": "android_roadmap",
        "title": "Android Development Roadmap",
        "category": "Mobile Development",
        "badge": "INFOGRAPHICS TIMELINE",
        "description": "Continuous 3D serpentine roadmap from beginner to production-ready Android developer. Tap any milestone to view details and track progress.",
        "icon": "smartphone",
        "accent_color": "#10B981",
        "estimated_weeks": "14-18 Weeks",
        "stages": [
            {
                "stage_number": 1,
                "badge_text": "STEP 01",
                "title": "Android Foundations",
                "description": "Install Android Studio, SDK, Gradle, Emulator & First App",
                "color": "#F59E0B",
                "difficulty": "Beginner",
                "estimated_hours": "15 Hours",
                "tutorial_link": "/tutorials/kotlin",
                "practice_link": "/compilers/kotlin-compiler",
                "topics": [
                    "Android Studio Setup & SDK Manager",
                    "Gradle Build System & Dependencies",
                    "Project Directory Structure",
                    "Emulator Setup & Running First App",
                ],
            },
            {
                "stage_number": 2,
                "badge_text": "STEP 02",
                "title": "Kotlin Fundamentals",
                "description": "Variables, OOP, Null Safety, Lambdas & Extensions",
                "color": "#10B981",
                "difficulty": "Beginner",
                "estimated_hours": "25 Hours",
                "tutorial_link": "/tutorials/kotlin",
                "practice_link": "/compilers/kotlin-compiler",
                "topics": [
                    "Control Flow, Functions & Type System",
                    "OOP: Classes, Inheritance & Interfaces",
                    "Null Safety & Smart Casting",
                    "Lambdas, High-Order Functions & Collections",
                ],
            },
            {
                "stage_number": 3,
                "badge_text": "STEP 03",
                "title": "Android UI & Views",
                "description": "XML Layouts, ConstraintLayout, RecyclerView & Navigation",
                "color": "#06B6D4",
                "difficulty": "Intermediate",
                "estimated_hours": "25 Hours",
                "tutorial_link": "/tutorials/kotlin",
                "practice_link": "/codelab",
                "topics": [
                    "XML Layouts & ConstraintLayout Basics",
                    "Activities, Fragments & Lifecycle",
                    "RecyclerView, ViewHolders & Adapters",
                    "Navigation Component & SafeArgs",
                ],
            },
            {
                "stage_number": 4,
                "badge_text": "STEP 04",
                "title": "Jetpack Compose UI",
                "description": "Composables, State, Material 3 & Animations",
                "color": "#3B82F6",
                "difficulty": "Intermediate",
                "estimated_hours": "30 Hours",
                "tutorial_link": "/tutorials/kotlin",
                "practice_link": "/codelab",
                "topics": [
                    "Composables & Declarative UI Syntax",
                    "Remember, MutableState & State Hoisting",
                    "LazyColumn, LazyRow & Grid Layouts",
                    "Material Design 3 Theming & Animations",
                ],
            },
            {
                "stage_number": 5,
                "badge_text": "STEP 05",
                "title": "Coroutines & Flow",
                "description": "Asynchronous Programming, StateFlow & REST APIs",
                "color": "#8B5CF6",
                "difficulty": "Advanced",
                "estimated_hours": "25 Hours",
                "tutorial_link": "/tutorials/kotlin",
                "practice_link": "/codelab",
                "topics": [
                    "Kotlin Coroutines & Dispatchers",
                    "StateFlow & SharedFlow Reactive Streams",
                    "Retrofit REST APIs & OkHttp Interceptors",
                    "JSON Deserialization with Moshi / Gson",
                ],
            },
            {
                "stage_number": 6,
                "badge_text": "STEP 06",
                "title": "Architecture & Room",
                "description": "MVVM / Clean Architecture, Room Database & Hilt DI",
                "color": "#EC4899",
                "difficulty": "Advanced",
                "estimated_hours": "30 Hours",
                "tutorial_link": "/tutorials/system-design",
                "practice_link": "/codelab",
                "topics": [
                    "ViewModel & Repository Pattern",
                    "Room Database & DataStore Local Persistence",
                    "Dependency Injection with Hilt",
                    "Unit Testing with JUnit & Mockito",
                ],
            },
        ],
    },
    {
        "key": "cyber_security_roadmap",
        "title": "Cyber Security Specialist Roadmap",
        "category": "Cyber Security",
        "badge": "INFOGRAPHICS TIMELINE",
        "description": "3D visual learning journey covering Networking, Ethical Hacking, Web App Security, Cryptography, and Incident Response.",
        "icon": "shield",
        "accent_color": "#8B5CF6",
        "estimated_weeks": "16-22 Weeks",
        "stages": [
            {
                "stage_number": 1,
                "badge_text": "STEP 01",
                "title": "Computer Networking & OS",
                "description": "TCP/IP, OSI Model, Subnetting, Linux CLI & Bash",
                "color": "#F59E0B",
                "difficulty": "Beginner",
                "estimated_hours": "25 Hours",
                "tutorial_link": "/tutorials/linux",
                "practice_link": "/practice",
                "topics": [
                    "TCP/IP, UDP & OSI 7-Layer Protocol Stack",
                    "IP Addressing, Subnetting & DNS Protocols",
                    "Linux Terminal Commands & File Permissions",
                    "Bash Shell Scripting Automation",
                ],
            },
            {
                "stage_number": 2,
                "badge_text": "STEP 02",
                "title": "Cyber Security Fundamentals",
                "description": "CIA Triad, Risk Management, Security Policies & Threat Models",
                "color": "#10B981",
                "difficulty": "Beginner",
                "estimated_hours": "20 Hours",
                "tutorial_link": "/tutorials/cybersecurity",
                "practice_link": "/practice",
                "topics": [
                    "Confidentiality, Integrity & Availability (CIA)",
                    "Threat Modeling & Attack Surfaces",
                    "Security Frameworks (NIST & ISO 27001)",
                    "Access Controls & Multi-Factor Auth (MFA)",
                ],
            },
            {
                "stage_number": 3,
                "badge_text": "STEP 03",
                "title": "Ethical Hacking & Recon",
                "description": "Information Gathering, Nmap, Wireshark & Scanning",
                "color": "#06B6D4",
                "difficulty": "Intermediate",
                "estimated_hours": "30 Hours",
                "tutorial_link": "/tutorials/cybersecurity",
                "practice_link": "/practice",
                "topics": [
                    "OSINT Reconnaissance & Social Engineering",
                    "Nmap Network Port Scanning",
                    "Wireshark Packet Analysis & Sniffing",
                    "Vulnerability Assessment Tools (OpenVAS / Nessus)",
                ],
            },
            {
                "stage_number": 4,
                "badge_text": "STEP 04",
                "title": "Web Application Security",
                "description": "OWASP Top 10, Burp Suite, SQLi & XSS Attacks",
                "color": "#3B82F6",
                "difficulty": "Intermediate",
                "estimated_hours": "30 Hours",
                "tutorial_link": "/tutorials/cybersecurity",
                "practice_link": "/practice",
                "topics": [
                    "OWASP Top 10 Vulnerabilities",
                    "SQL Injection (SQLi) & Remediation",
                    "Cross-Site Scripting (XSS) & CSRF",
                    "Burp Suite Interception Proxy",
                ],
            },
            {
                "stage_number": 5,
                "badge_text": "STEP 05",
                "title": "Cryptography & PKI",
                "description": "Symmetric/Asymmetric Encryption, Hashing & SSL/TLS",
                "color": "#8B5CF6",
                "difficulty": "Advanced",
                "estimated_hours": "25 Hours",
                "tutorial_link": "/tutorials/cybersecurity",
                "practice_link": "/practice",
                "topics": [
                    "AES, RSA & Elliptic Curve Cryptography",
                    "SHA-256 Hashing & Password Salting",
                    "Public Key Infrastructure (PKI) & Certificates",
                    "TLS/SSL Handshake & Secure Communications",
                ],
            },
            {
                "stage_number": 6,
                "badge_text": "STEP 06",
                "title": "Incident Response & Forensics",
                "description": "SIEM Monitoring, Malware Analysis & SOC Analyst Capstone",
                "color": "#EC4899",
                "difficulty": "Advanced",
                "estimated_hours": "30 Hours",
                "tutorial_link": "/tutorials/cybersecurity",
                "practice_link": "/practice",
                "topics": [
                    "SIEM Log Analysis (Splunk / Elastic SOC)",
                    "Memory Forensics & Incident Response",
                    "Basic Reverse Engineering & Malware Analysis",
                    "Penetration Testing Report Writing",
                ],
            },
        ],
    },
]


def _resolve_authenticated_user(request):
    """Return authenticated Django user only (no header spoofing)."""
    user = getattr(request, "user", None)
    if user and getattr(user, "is_authenticated", False):
        return user
    return None


def _roadmap_to_dict(rm_obj: LearningRoadmap) -> dict:
    stages = rm_obj.stages if isinstance(rm_obj.stages, list) else []
    return {
        "key": rm_obj.key,
        "title": rm_obj.title,
        "category": rm_obj.category,
        "badge": rm_obj.badge,
        "description": rm_obj.description,
        "icon": rm_obj.icon,
        "accent_color": rm_obj.accent_color,
        "estimated_weeks": rm_obj.estimated_weeks,
        "order": rm_obj.order,
        "is_active": rm_obj.is_active,
        "stages": stages,
    }


def _normalize_stages(raw_stages) -> list:
    if not isinstance(raw_stages, list):
        return []
    cleaned = []
    for idx, st in enumerate(raw_stages, start=1):
        if not isinstance(st, dict):
            continue
        title = str(st.get("title") or "").strip()
        if not title:
            continue
        try:
            stage_number = int(st.get("stage_number") or idx)
        except (TypeError, ValueError):
            stage_number = idx
        diff = str(st.get("difficulty") or "Beginner").strip()
        if diff not in ("Beginner", "Intermediate", "Advanced"):
            diff = "Beginner"
        raw_topics = st.get("topics")
        topics = (
            [str(t).strip() for t in raw_topics if str(t).strip()]
            if isinstance(raw_topics, list)
            else []
        )
        cleaned.append(
            {
                "stage_number": stage_number,
                "badge_text": str(st.get("badge_text") or f"STEP {stage_number:02d}").strip(),
                "title": title,
                "description": str(st.get("description") or "").strip(),
                "color": str(st.get("color") or "#3B82F6").strip(),
                "difficulty": diff,
                "estimated_hours": str(st.get("estimated_hours") or "15 Hours").strip(),
                "tutorial_link": str(st.get("tutorial_link") or "/tutorials").strip(),
                "practice_link": str(st.get("practice_link") or "/codelab").strip(),
                "topics": topics,
            }
        )
    cleaned.sort(key=lambda s: s["stage_number"])
    return cleaned


@api_view(["GET"])
@permission_classes([AllowAny])
def list_career_roadmaps(request):
    """
    Returns summary preview list of active career roadmaps.
    Full roadmap details require user authentication.
    """
    user = _resolve_authenticated_user(request)
    category = request.query_params.get("category", "").strip().lower()
    search = request.query_params.get("q", "").strip().lower()

    user_progress_map = {}
    if user:
        progress_entries = LearningRoadmapProgress.objects.filter(
            user=user, completed=True
        ).values("roadmap_key", "stage_number")
        for entry in progress_entries:
            key = entry["roadmap_key"]
            user_progress_map.setdefault(key, set()).add(entry["stage_number"])

    roadmaps_qs = LearningRoadmap.objects.filter(is_active=True).order_by("order", "id")
    roadmaps_data = []
    for rm_obj in roadmaps_qs:
        rm = _roadmap_to_dict(rm_obj)
        if category and category != "all" and rm["category"].lower() != category:
            continue

        if search:
            match_title = search in rm["title"].lower()
            match_desc = search in rm["description"].lower()
            match_key = search in rm["key"].lower()
            match_topic = any(
                search in str(topic).lower()
                for st in rm["stages"]
                for topic in (st.get("topics") or [])
            )
            if not (match_title or match_desc or match_key or match_topic):
                continue

        stages_total = len(rm["stages"])
        completed_stage_numbers = user_progress_map.get(rm["key"], set())
        completed_count = len(completed_stage_numbers)
        percent = int((completed_count / stages_total) * 100) if stages_total > 0 else 0

        current_stage = 1
        for st in rm["stages"]:
            if st.get("stage_number") not in completed_stage_numbers:
                current_stage = st.get("stage_number", 1)
                break
        else:
            current_stage = max(stages_total, 1)

        roadmaps_data.append({
            "key": rm["key"],
            "title": rm["title"],
            "category": rm["category"],
            "badge": rm["badge"],
            "description": rm["description"],
            "icon": rm["icon"],
            "accent_color": rm["accent_color"],
            "estimated_weeks": rm["estimated_weeks"] or "12-16 Weeks",
            "total_stages": stages_total,
            "completed_stages": completed_count,
            "progress_percent": percent,
            "current_stage": current_stage,
            "stages_summary": [
                {
                    "stage_number": s.get("stage_number", idx + 1),
                    "title": s.get("title", ""),
                    "completed": s.get("stage_number") in completed_stage_numbers,
                }
                for idx, s in enumerate(rm["stages"][:4])
            ],
        })

    return Response({
        "status": True,
        "requires_auth": user is None,
        "count": len(roadmaps_data),
        "roadmaps": roadmaps_data,
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_career_roadmap_detail(request, roadmap_key):
    """
    Returns full details of a specific roadmap with all stages, subtopics,
    and completion status. Strictly requires an authenticated user.
    """
    user = _resolve_authenticated_user(request)
    if not user:
        return Response(
            {
                "status": False,
                "requires_auth": True,
                "message": "Authentication required to access the full roadmap.",
            },
            status=status.HTTP_401_UNAUTHORIZED,
        )

    rm_obj = LearningRoadmap.objects.filter(key=roadmap_key, is_active=True).first()
    if not rm_obj:
        return Response(
            {"status": False, "message": f"Roadmap '{roadmap_key}' not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    roadmap = _roadmap_to_dict(rm_obj)
    completed_stages = {}
    entries = LearningRoadmapProgress.objects.filter(
        user=user, roadmap_key=roadmap_key
    ).values("stage_number", "completed", "completed_subtopics")
    for ent in entries:
        completed_stages[ent["stage_number"]] = {
            "completed": ent["completed"],
            "completed_subtopics": ent["completed_subtopics"] or [],
        }

    stages_with_status = []
    completed_count = 0
    for st in roadmap["stages"]:
        st_num = st.get("stage_number")
        st_prog = completed_stages.get(st_num, {})
        is_completed = st_prog.get("completed", False)
        subtopics_done = st_prog.get("completed_subtopics", [])
        if is_completed:
            completed_count += 1

        stages_with_status.append({
            **st,
            "completed": is_completed,
            "completed_subtopics": subtopics_done,
        })

    total_stages = len(stages_with_status)
    percent = int((completed_count / total_stages) * 100) if total_stages > 0 else 0

    return Response({
        "status": True,
        "roadmap": {
            **roadmap,
            "stages": stages_with_status,
            "total_stages": total_stages,
            "completed_stages": completed_count,
            "progress_percent": percent,
        },
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def toggle_career_stage_progress(request, roadmap_key, stage_number):
    """Toggle or explicitly set completion status for a stage and roadmap key."""
    rm_obj = LearningRoadmap.objects.filter(key=roadmap_key, is_active=True).first()
    if not rm_obj:
        return Response(
            {"status": False, "message": f"Roadmap '{roadmap_key}' not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    try:
        stage_num = int(stage_number)
    except (ValueError, TypeError):
        return Response(
            {"status": False, "message": "Invalid stage number."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user = _resolve_authenticated_user(request)
    if not user:
        return Response(
            {"status": False, "message": "User authentication required."},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    explicit_state = request.data.get("completed")
    subtopics = request.data.get("completed_subtopics")

    with transaction.atomic():
        progress_obj, created = LearningRoadmapProgress.objects.get_or_create(
            user=user,
            roadmap_key=roadmap_key,
            stage_number=stage_num,
            defaults={"completed": True, "completed_subtopics": subtopics or []},
        )
        if not created:
            if explicit_state is not None:
                progress_obj.completed = bool(explicit_state)
            else:
                progress_obj.completed = not progress_obj.completed
            if subtopics is not None:
                progress_obj.completed_subtopics = list(subtopics)
            progress_obj.save()

    completed_count = LearningRoadmapProgress.objects.filter(
        user=user, roadmap_key=roadmap_key, completed=True
    ).count()
    total_stages = len(rm_obj.stages or [])
    percent = int((completed_count / total_stages) * 100) if total_stages > 0 else 0

    return Response({
        "status": True,
        "stage_number": stage_num,
        "completed": progress_obj.completed,
        "completed_subtopics": progress_obj.completed_subtopics,
        "total_stages": total_stages,
        "completed_stages": completed_count,
        "progress_percent": percent,
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def reset_career_roadmap_progress(request, roadmap_key):
    """Reset all stage progress for a given roadmap key."""
    user = _resolve_authenticated_user(request)
    if not user:
        return Response(
            {"status": False, "message": "User authentication required."},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    deleted_count, _ = LearningRoadmapProgress.objects.filter(
        user=user, roadmap_key=roadmap_key
    ).delete()

    return Response({
        "status": True,
        "message": f"Progress for '{roadmap_key}' has been reset.",
        "deleted_count": deleted_count,
        "completed_stages": 0,
        "progress_percent": 0,
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def sync_career_roadmaps_progress(request):
    """Batch synchronizes local roadmap progress with the authenticated user account."""
    user = _resolve_authenticated_user(request)
    if not user:
        return Response(
            {"status": False, "message": "User authentication required."},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    progress_payload = request.data.get("progress", {})
    if not isinstance(progress_payload, dict):
        return Response(
            {"status": False, "message": "Invalid progress payload structure."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    synced_items = 0
    with transaction.atomic():
        for roadmap_key, stages_list in progress_payload.items():
            if not isinstance(stages_list, list):
                continue
            for stage_num in stages_list:
                try:
                    s_int = int(stage_num)
                    LearningRoadmapProgress.objects.update_or_create(
                        user=user,
                        roadmap_key=roadmap_key,
                        stage_number=s_int,
                        defaults={"completed": True},
                    )
                    synced_items += 1
                except (ValueError, TypeError):
                    continue

    return Response({
        "status": True,
        "message": f"Successfully synced {synced_items} completed stages.",
        "synced_count": synced_items,
    })


# ==============================================================================
# ADMIN ROADMAP MANAGEMENT ENDPOINTS (CREATE, UPDATE, DELETE)
# ==============================================================================

def _admin_serialize_roadmap(rm_obj: LearningRoadmap) -> dict:
    stages = rm_obj.stages if isinstance(rm_obj.stages, list) else []
    return {
        "key": rm_obj.key,
        "title": rm_obj.title,
        "category": rm_obj.category,
        "badge": rm_obj.badge,
        "description": rm_obj.description,
        "icon": rm_obj.icon,
        "accent_color": rm_obj.accent_color,
        "estimated_weeks": rm_obj.estimated_weeks,
        "order": rm_obj.order,
        "is_active": rm_obj.is_active,
        "stages": stages,
        "total_stages": len(stages),
        "created_at": rm_obj.created_at.isoformat() if rm_obj.created_at else None,
        "updated_at": rm_obj.updated_at.isoformat() if rm_obj.updated_at else None,
    }


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated, IsAdminUser])
def admin_career_roadmaps(request):
    if request.method == "GET":
        qs = LearningRoadmap.objects.all().order_by("order", "id")
        return Response({
            "status": True,
            "roadmaps": [_admin_serialize_roadmap(r) for r in qs],
        })

    title = str(request.data.get("title") or "").strip()
    if not title:
        return Response({"detail": "Roadmap title is required."}, status=status.HTTP_400_BAD_REQUEST)

    raw_key = str(request.data.get("key") or "").strip()
    clean_key = re.sub(r"[^a-z0-9_]+", "_", slugify(raw_key or title).replace("-", "_")).strip("_")
    if not clean_key:
        clean_key = f"roadmap_{LearningRoadmap.objects.count() + 1}"
    if LearningRoadmap.objects.filter(key=clean_key).exists():
        return Response({"detail": f"A roadmap with key '{clean_key}' already exists."}, status=status.HTTP_400_BAD_REQUEST)

    stages = _normalize_stages(request.data.get("stages") or [])
    max_order = LearningRoadmap.objects.count() + 1
    rm_obj = LearningRoadmap.objects.create(
        key=clean_key,
        title=title,
        category=str(request.data.get("category") or "Web Development").strip(),
        badge=str(request.data.get("badge") or "INFOGRAPHICS TIMELINE").strip(),
        description=str(request.data.get("description") or "").strip(),
        icon=str(request.data.get("icon") or "code").strip(),
        accent_color=str(request.data.get("accent_color") or "#3B82F6").strip(),
        estimated_weeks=str(request.data.get("estimated_weeks") or "12-16 Weeks").strip(),
        order=int(request.data.get("order") if request.data.get("order") is not None else max_order),
        is_active=bool(request.data.get("is_active", True)),
        stages=stages,
    )
    return Response(_admin_serialize_roadmap(rm_obj), status=status.HTTP_201_CREATED)


@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated, IsAdminUser])
def admin_career_roadmap_detail(request, roadmap_key):
    rm_obj = LearningRoadmap.objects.filter(key=roadmap_key).first()
    if not rm_obj:
        return Response({"detail": f"Roadmap '{roadmap_key}' not found."}, status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        return Response(_admin_serialize_roadmap(rm_obj))

    if request.method == "DELETE":
        LearningRoadmapProgress.objects.filter(roadmap_key=rm_obj.key).delete()
        rm_obj.delete()
        return Response({"deleted": True}, status=status.HTTP_204_NO_CONTENT)

    for field in ("title", "category", "badge", "description", "icon", "accent_color", "estimated_weeks"):
        if field in request.data:
            setattr(rm_obj, field, str(request.data.get(field) or "").strip())
    if "order" in request.data and request.data["order"] is not None:
        rm_obj.order = int(request.data["order"])
    if "is_active" in request.data:
        rm_obj.is_active = bool(request.data["is_active"])
    if "stages" in request.data:
        rm_obj.stages = _normalize_stages(request.data.get("stages"))
    rm_obj.save()
    return Response(_admin_serialize_roadmap(rm_obj))

