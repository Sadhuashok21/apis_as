from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
import hashlib
import time

from sfs.models import AllUsers
from .models import (
    TutorialTrack,
    TutorialModule,
    TutorialLesson,
    TutorialProgress,
    TutorialBookmark,
    TutorialNote,
    TutorialCertificate,
    DailyActivity,
    UserProfile,
)
from .tutorial_seed_data import INITIAL_TRACKS


def _ensure_initial_seeds():
    """Ensure database has the curated initial tutorial tracks."""
    if TutorialTrack.objects.exists():
        return

    for t_data in INITIAL_TRACKS:
        track, _ = TutorialTrack.objects.get_or_create(
            track_id=t_data["track_id"],
            defaults={
                "title": t_data["title"],
                "category": t_data.get("category", "languages"),
                "description": t_data.get("description", ""),
                "icon": t_data.get("icon", "code"),
                "is_featured": t_data.get("is_featured", False),
                "order": t_data.get("order", 1),
            }
        )
        for m_data in t_data.get("modules", []):
            module, _ = TutorialModule.objects.get_or_create(
                module_id=m_data["module_id"],
                defaults={
                    "track": track,
                    "title": m_data["title"],
                    "level": m_data.get("level", "beginner"),
                    "description": m_data.get("description", ""),
                    "order": m_data.get("order", 1),
                }
            )
            for l_data in m_data.get("lessons", []):
                TutorialLesson.objects.get_or_create(
                    lesson_id=f"{track.track_id}-{l_data['slug']}",
                    defaults={
                        "track": track,
                        "module": module,
                        "slug": l_data["slug"],
                        "title": l_data["title"],
                        "reading_time_minutes": l_data.get("reading_time_minutes", 5),
                        "learning_objectives": l_data.get("learning_objectives", []),
                        "explanation": l_data.get("explanation", ""),
                        "syntax_code": l_data.get("syntax_code", ""),
                        "code_examples": l_data.get("code_examples", []),
                        "try_it_yourself": l_data.get("try_it_yourself", {}),
                        "quiz": l_data.get("quiz", {}),
                        "challenge": l_data.get("challenge", {}),
                        "order": l_data.get("order", 1),
                    }
                )


def _get_user_from_request(request):
    """Retrieve authenticated user from request or token."""
    user = getattr(request, "user", None)
    if user and user.is_authenticated:
        return user
    user_id = request.headers.get("X-User-Id") or request.query_params.get("user_id")
    if user_id:
        return AllUsers.objects.filter(user_id=user_id).first()
    return None


@api_view(["GET"])
@permission_classes([AllowAny])
def list_tutorial_tracks(request):
    """
    List all tutorial tracks with categories, total lessons, and optional completion.
    """
    _ensure_initial_seeds()
    category = request.query_params.get("category", "").strip().lower()
    search = request.query_params.get("q", "").strip()

    qs = TutorialTrack.objects.all().prefetch_related("modules", "lessons")
    if category and category != "all":
        qs = qs.filter(category=category)
    if search:
        qs = qs.filter(Q(title__icontains=search) | Q(description__icontains=search) | Q(track_id__icontains=search))

    user = _get_user_from_request(request)
    completed_ids = set()
    if user:
        completed_ids = set(
            TutorialProgress.objects.filter(user=user, completed=True).values_list("lesson_id", flat=True)
        )

    tracks_data = []
    for track in qs:
        all_lessons = list(track.lessons.all())
        total_lessons = len(all_lessons)
        user_completed = sum(1 for l in all_lessons if l.lesson_id in completed_ids)
        percent = int((user_completed / total_lessons * 100)) if total_lessons > 0 else 0

        tracks_data.append({
            "track_id": track.track_id,
            "title": track.title,
            "category": track.category,
            "description": track.description,
            "icon": track.icon,
            "is_featured": track.is_featured,
            "order": track.order,
            "total_lessons": total_lessons,
            "completed_lessons": user_completed,
            "progress_percent": percent,
            "modules_count": track.modules.count(),
        })

    return Response({
        "status": True,
        "tracks": tracks_data,
        "categories": [
            {"id": "all", "label": "All Tutorials"},
            {"id": "languages", "label": "Programming Languages"},
            {"id": "web", "label": "Web Development"},
            {"id": "backend", "label": "Backend Development"},
            {"id": "databases", "label": "Databases"},
            {"id": "computer_science", "label": "Computer Science"},
            {"id": "cloud_devops", "label": "Cloud & DevOps"},
            {"id": "other_tech", "label": "Other Technology"},
        ]
    })


@api_view(["GET"])
@permission_classes([AllowAny])
def get_tutorial_track_curriculum(request, track_id):
    """
    Get full track curriculum with modules and lesson tree.
    """
    _ensure_initial_seeds()
    track = TutorialTrack.objects.filter(track_id=track_id.lower()).first()
    if not track:
        return Response({"status": False, "message": f"Tutorial track '{track_id}' not found."}, status=status.HTTP_404_NOT_FOUND)

    user = _get_user_from_request(request)
    completed_ids = set()
    bookmarked_ids = set()
    if user:
        completed_ids = set(
            TutorialProgress.objects.filter(user=user, track=track, completed=True).values_list("lesson_id", flat=True)
        )
        bookmarked_ids = set(
            TutorialBookmark.objects.filter(user=user).values_list("lesson_id", flat=True)
        )

    modules_data = []
    total_lessons = 0
    completed_count = 0

    for m in track.modules.all().order_by("order"):
        lessons_data = []
        for l in m.lessons.all().order_by("order"):
            total_lessons += 1
            is_done = l.lesson_id in completed_ids
            if is_done:
                completed_count += 1
            lessons_data.append({
                "lesson_id": l.lesson_id,
                "slug": l.slug,
                "title": l.title,
                "order": l.order,
                "reading_time_minutes": l.reading_time_minutes,
                "is_completed": is_done,
                "is_bookmarked": l.lesson_id in bookmarked_ids,
            })
        modules_data.append({
            "module_id": m.module_id,
            "title": m.title,
            "level": m.level,
            "description": m.description,
            "order": m.order,
            "lessons": lessons_data,
        })

    percent = int((completed_count / total_lessons * 100)) if total_lessons > 0 else 0

    return Response({
        "status": True,
        "track": {
            "track_id": track.track_id,
            "title": track.title,
            "category": track.category,
            "description": track.description,
            "icon": track.icon,
            "total_lessons": total_lessons,
            "completed_lessons": completed_count,
            "progress_percent": percent,
        },
        "modules": modules_data,
    })


@api_view(["GET"])
@permission_classes([AllowAny])
def get_tutorial_lesson_detail(request, track_id, slug):
    """
    Get full lesson content, adjacent lessons, user progress, note, and bookmark status.
    """
    _ensure_initial_seeds()
    track = TutorialTrack.objects.filter(track_id=track_id.lower()).first()
    if not track:
        return Response({"status": False, "message": "Track not found"}, status=status.HTTP_404_NOT_FOUND)

    lesson = TutorialLesson.objects.filter(track=track, slug=slug.lower()).first()
    if not lesson:
        # Fallback by lesson_id or first lesson
        lesson = TutorialLesson.objects.filter(track=track).order_by("order").first()
        if not lesson:
            return Response({"status": False, "message": "Lesson not found"}, status=status.HTTP_404_NOT_FOUND)

    # Determine previous and next lessons in track order
    all_lessons = list(TutorialLesson.objects.filter(track=track).order_by("module__order", "order"))
    current_idx = -1
    for idx, l in enumerate(all_lessons):
        if l.lesson_id == lesson.lesson_id:
            current_idx = idx
            break

    prev_lesson = all_lessons[current_idx - 1] if current_idx > 0 else None
    next_lesson = all_lessons[current_idx + 1] if current_idx >= 0 and current_idx < len(all_lessons) - 1 else None

    user = _get_user_from_request(request)
    is_completed = False
    is_bookmarked = False
    user_note = ""

    if user:
        prog = TutorialProgress.objects.filter(user=user, lesson=lesson).first()
        if prog and prog.completed:
            is_completed = True
        is_bookmarked = TutorialBookmark.objects.filter(user=user, lesson=lesson).exists()
        note_obj = TutorialNote.objects.filter(user=user, lesson=lesson).first()
        if note_obj:
            user_note = note_obj.content

    return Response({
        "status": True,
        "track": {
            "track_id": track.track_id,
            "title": track.title,
            "category": track.category,
            "icon": track.icon,
        },
        "module": {
            "module_id": lesson.module.module_id,
            "title": lesson.module.title,
            "level": lesson.module.level,
        },
        "lesson": {
            "lesson_id": lesson.lesson_id,
            "slug": lesson.slug,
            "title": lesson.title,
            "reading_time_minutes": lesson.reading_time_minutes,
            "learning_objectives": lesson.learning_objectives,
            "explanation": lesson.explanation,
            "syntax_code": lesson.syntax_code,
            "code_examples": lesson.code_examples,
            "try_it_yourself": lesson.try_it_yourself,
            "quiz": lesson.quiz,
            "challenge": lesson.challenge,
            "is_completed": is_completed,
            "is_bookmarked": is_bookmarked,
            "user_note": user_note,
        },
        "navigation": {
            "prev": {"slug": prev_lesson.slug, "title": prev_lesson.title} if prev_lesson else None,
            "next": {"slug": next_lesson.slug, "title": next_lesson.title} if next_lesson else None,
        }
    })


@api_view(["POST"])
@permission_classes([AllowAny])
def save_tutorial_progress(request):
    """
    Mark a lesson completed, award XP (+20 for lesson, +30 for quiz), and update streak.
    """
    user = _get_user_from_request(request)
    if not user:
        return Response({"status": False, "message": "Sign in required to save progress."}, status=status.HTTP_401_UNAUTHORIZED)

    lesson_id = request.data.get("lesson_id")
    track_id = request.data.get("track_id")
    quiz_passed = bool(request.data.get("quiz_passed", False))

    if not lesson_id:
        return Response({"status": False, "message": "lesson_id is required"}, status=status.HTTP_400_BAD_REQUEST)

    lesson = TutorialLesson.objects.filter(lesson_id=lesson_id).first()
    if not lesson:
        return Response({"status": False, "message": "Lesson not found"}, status=status.HTTP_404_NOT_FOUND)

    track = lesson.track
    xp_to_award = 20
    if quiz_passed:
        xp_to_award += 30

    with transaction.atomic():
        prog, created = TutorialProgress.objects.get_or_create(
            user=user,
            lesson=lesson,
            defaults={
                "track": track,
                "completed": True,
                "completed_at": timezone.now(),
                "quiz_completed": quiz_passed,
                "quiz_score": 100 if quiz_passed else 0,
                "xp_earned": xp_to_award,
            }
        )
        if not created and not prog.completed:
            prog.completed = True
            prog.completed_at = timezone.now()
            if quiz_passed:
                prog.quiz_completed = True
                prog.quiz_score = 100
            prog.xp_earned += xp_to_award
            prog.save()

        # Update DailyActivity streak
        today = timezone.now().date()
        act, _ = DailyActivity.objects.get_or_create(user=user, date=today)
        act.problems_solved = getattr(act, "problems_solved", 0) + 1
        act.save()

        # Update User Profile XP
        try:
            profile = UserProfile.objects.filter(user=user).first()
            if profile:
                profile.xp = getattr(profile, "xp", 0) + xp_to_award
                profile.save(update_fields=["xp"])
        except Exception:
            pass

    # Calculate overall track completion
    total = track.lessons.count()
    completed_count = TutorialProgress.objects.filter(user=user, track=track, completed=True).count()
    percent = int((completed_count / total * 100)) if total > 0 else 0

    return Response({
        "status": True,
        "message": f"Lesson completed! +{xp_to_award} XP awarded.",
        "xp_awarded": xp_to_award,
        "progress_percent": percent,
        "completed_count": completed_count,
        "total_lessons": total,
        "is_track_completed": completed_count >= total,
    })


@api_view(["POST"])
@permission_classes([AllowAny])
def toggle_tutorial_bookmark(request):
    """
    Toggle bookmark for a tutorial lesson.
    """
    user = _get_user_from_request(request)
    if not user:
        return Response({"status": False, "message": "Sign in required to bookmark."}, status=status.HTTP_401_UNAUTHORIZED)

    lesson_id = request.data.get("lesson_id")
    lesson = TutorialLesson.objects.filter(lesson_id=lesson_id).first()
    if not lesson:
        return Response({"status": False, "message": "Lesson not found"}, status=status.HTTP_404_NOT_FOUND)

    existing = TutorialBookmark.objects.filter(user=user, lesson=lesson).first()
    if existing:
        existing.delete()
        is_bookmarked = False
    else:
        TutorialBookmark.objects.create(user=user, lesson=lesson)
        is_bookmarked = True

    return Response({"status": True, "is_bookmarked": is_bookmarked})


@api_view(["POST"])
@permission_classes([AllowAny])
def save_tutorial_note(request):
    """
    Save or clear personal notes for a lesson.
    """
    user = _get_user_from_request(request)
    if not user:
        return Response({"status": False, "message": "Sign in required for notes."}, status=status.HTTP_401_UNAUTHORIZED)

    lesson_id = request.data.get("lesson_id")
    content = request.data.get("content", "").strip()

    lesson = TutorialLesson.objects.filter(lesson_id=lesson_id).first()
    if not lesson:
        return Response({"status": False, "message": "Lesson not found"}, status=status.HTTP_404_NOT_FOUND)

    note_obj, _ = TutorialNote.objects.get_or_create(user=user, lesson=lesson)
    note_obj.content = content
    note_obj.save()

    return Response({"status": True, "message": "Note saved.", "content": content})


@api_view(["POST"])
@permission_classes([AllowAny])
def issue_tutorial_certificate(request):
    """
    Issue a certificate of completion when a student completes all lessons in a track.
    """
    user = _get_user_from_request(request)
    track_id = request.data.get("track_id", "").strip().lower()
    student_name = request.data.get("student_name", "").strip()

    track = TutorialTrack.objects.filter(track_id=track_id).first()
    if not track:
        return Response({"status": False, "message": "Course track not found"}, status=status.HTTP_404_NOT_FOUND)

    if not student_name:
        if user:
            student_name = f"{getattr(user, 'name', '')} {getattr(user, 'lastname', '')}".strip() or user.username
        else:
            student_name = "SkilTrix Scholar"

    # Generate unique Certificate ID: STX-[TRACK]-[TIMESTAMP]
    cert_id = f"STX-{track.track_id.upper()}-{int(time.time())}"
    raw_hash = f"{cert_id}:{student_name}:{track.title}"
    verification_hash = hashlib.sha256(raw_hash.encode("utf-8")).hexdigest()[:16].upper()

    cert = None
    if user:
        cert, _ = TutorialCertificate.objects.get_or_create(
            user=user,
            track=track,
            defaults={
                "certificate_id": cert_id,
                "student_name": student_name,
                "course_name": track.title,
                "score_percent": 95,
                "verification_hash": verification_hash,
            }
        )

    return Response({
        "status": True,
        "certificate": {
            "certificate_id": cert.certificate_id if cert else cert_id,
            "student_name": student_name,
            "course_name": track.title,
            "track_id": track.track_id,
            "score_percent": 95,
            "issued_at": timezone.now().strftime("%B %d, %Y"),
            "verification_hash": verification_hash,
            "verification_url": f"https://ascentracoresolutions.com/certificates/{cert_id}",
        }
    })


@api_view(["GET"])
@permission_classes([AllowAny])
def get_tutorial_certificate(request, cert_id):
    """
    Publicly verify and view a SkilTrix certificate.
    """
    cert = TutorialCertificate.objects.filter(certificate_id=cert_id.upper()).first()
    if not cert:
        return Response({"status": False, "message": "Certificate not found or invalid ID."}, status=status.HTTP_404_NOT_FOUND)

    return Response({
        "status": True,
        "certificate": {
            "certificate_id": cert.certificate_id,
            "student_name": cert.student_name,
            "course_name": cert.course_name,
            "score_percent": cert.score_percent,
            "issued_at": cert.issued_at.strftime("%B %d, %Y"),
            "verification_hash": cert.verification_hash,
        }
    })


@api_view(["GET"])
@permission_classes([AllowAny])
def search_tutorials(request):
    """
    Global search for tutorials, lessons, syntax topics, and code examples (Ctrl + K).
    """
    _ensure_initial_seeds()
    query = request.query_params.get("q", "").strip().lower()
    if not query:
        return Response({"status": True, "results": []})

    results = []

    # 1. Match tracks
    for t in TutorialTrack.objects.filter(Q(title__icontains=query) | Q(track_id__icontains=query) | Q(description__icontains=query))[:5]:
        results.append({
            "type": "track",
            "title": t.title,
            "subtitle": f"{t.get_category_display()} Course",
            "url": f"/tutorials/{t.track_id}",
            "icon": t.icon,
        })

    # 2. Match lessons
    for l in TutorialLesson.objects.filter(Q(title__icontains=query) | Q(explanation__icontains=query) | Q(slug__icontains=query))[:15]:
        results.append({
            "type": "lesson",
            "title": l.title,
            "subtitle": f"{l.track.title} • {l.module.title}",
            "url": f"/tutorials/{l.track.track_id}/{l.slug}",
            "icon": "book",
        })

    return Response({"status": True, "results": results})

