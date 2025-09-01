
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user

# Expect the host app to provide: db, models.Progress, models.Event
# We will import these within register_perspective_routes to avoid global coupling.

APP_ROOT = Path(__file__).parent
PERSPECTIVES_DIR = APP_ROOT / "content" / "perspectives"

def _load_all_perspectives() -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    if not PERSPECTIVES_DIR.exists():
        PERSPECTIVES_DIR.mkdir(parents=True, exist_ok=True)
        return items
    for f in PERSPECTIVES_DIR.glob("*.json"):
        try:
            with f.open(encoding="utf-8") as fp:
                data = json.load(fp)
            # Minimal schema guardrails
            data.setdefault("slug", f.stem)
            data.setdefault("title", f.stem.replace("-", " ").title())
            data.setdefault("summary", "")
            try:
                data["order"] = int(data.get("order", 9999))
            except Exception:
                data["order"] = 9999
            data.setdefault("lessons", [])
            items.append(data)
        except Exception as e:
            # Skip malformed files but don't crash the app
            print(f"[perspectives] Skipping {f.name}: {e}")
            continue
    items.sort(key=lambda x: (x.get("order", 9999), x.get("title", "")))
    return items

def _load_perspective(slug: str) -> Optional[Dict[str, Any]]:
    path = PERSPECTIVES_DIR / f"{slug}.json"
    if path.exists():
        with path.open(encoding="utf-8") as fp:
            return json.load(fp)
    # fallback: scan all if filename mismatch
    for data in _load_all_perspectives():
        if data.get("slug") == slug:
            return data
    return None

def _get_lesson(data: Dict[str, Any], lesson_id: str) -> Optional[Dict[str, Any]]:
    for lesson in data.get("lessons", []):
        if str(lesson.get("id")) == str(lesson_id):
            return lesson
    return None

def _compute_progress(db, Progress, user_id: int, perspective_slug: str, total_lessons: int) -> int:
    if total_lessons <= 0:
        return 0
    count = (
        db.session.query(Progress)
        .filter_by(user_id=user_id, perspective_slug=perspective_slug, status="completed")
        .count()
    )
    pct = round(100 * min(count, total_lessons) / total_lessons)
    return pct

def _log_event(db, Event, user_id: int, etype: str, slug: Optional[str], lesson_id: Optional[str], meta: Optional[Dict[str, Any]] = None):
    try:
        ev = Event(user_id=user_id, type=etype, perspective_slug=slug, lesson_id=lesson_id, meta=meta or {}, created_at=datetime.utcnow())
        db.session.add(ev)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"[perspectives] Failed to log event {etype}: {e}")

def register_perspective_routes(app, db):
    # Import models late to avoid circulars
    from models import Progress, Event

    bp = Blueprint("perspectives_bp", __name__)

    @bp.route("/dashboard")
    @login_required
    def dashboard():
        raw = _load_all_perspectives()
        perspectives = []
        for p in raw:
            total = len(p.get("lessons", []))
            progress = _compute_progress(db, Progress, current_user.id, p["slug"], total)
            perspectives.append({
                "slug": p["slug"],
                "title": p.get("title", ""),
                "summary": p.get("summary", ""),
                "progress": progress,
            })
        # streak may be from app context; fall back to 0
        try:
            streak = app.jinja_env.globals.get("streak", 0)
        except Exception:
            streak = 0
        return render_template("dashboard.html", perspectives=perspectives, user=current_user, streak=streak)

    @bp.route("/perspectives/<slug>")
    @login_required
    def perspective_detail(slug):
        data = _load_perspective(slug)
        if not data:
            flash("Perspective not found.", "warning")
            return redirect(url_for("perspectives_bp.dashboard"))
        lessons = data.get("lessons", [])
        # Fetch completed lessons for the user
        completed_ids = {
            row.lesson_id
            for row in db.session.query(Progress.lesson_id)
                .filter_by(user_id=current_user.id, perspective_slug=slug, status="completed")
                .all()
        }
        return render_template("perspective.html", perspective=data, lessons=lessons, completed_ids=completed_ids)

    @bp.route("/lesson/<slug>/<lesson_id>", methods=["GET", "POST"])
    @login_required
    def lesson(slug, lesson_id):
        perspective = _load_perspective(slug)
        if not perspective:
            flash("Perspective not found.", "warning")
            return redirect(url_for("perspectives_bp.dashboard"))
        lesson = _get_lesson(perspective, lesson_id)
        if not lesson:
            flash("Lesson not found.", "warning")
            return redirect(url_for("perspectives_bp.perspective_detail", slug=slug))

        # Ensure a Progress row exists
        prog = db.session.query(Progress).filter_by(user_id=current_user.id, perspective_slug=slug, lesson_id=str(lesson_id)).first()
        if not prog:
            prog = Progress(user_id=current_user.id, perspective_slug=slug, lesson_id=str(lesson_id), status="started", score=0, updated_at=datetime.utcnow())
            db.session.add(prog)
            db.session.commit()

        if request.method == "POST":
            action = request.form.get("action", "")
            if action in ("submit_quiz", "quick_check"):
                try:
                    qidx = int(request.form.get("qidx", 0))
                    choice_idx = int(request.form.get("answer", request.form.get("choice_idx", -1)))
                    quick_checks = lesson.get("quick_checks", [])
                    if 0 <= qidx < len(quick_checks):
                        qc = quick_checks[qidx]
                        correct = (choice_idx == int(qc.get("answer_index", -1)))
                        _log_event(db, Event, current_user.id, "quiz_attempted", slug, str(lesson_id), {"qidx": qidx, "correct": correct})
                        # simple scoring: first correct answer marks completion
                        if correct and (prog.status != "completed"):
                            prog.status = "completed"
                            prog.score = max(prog.score or 0, 100)
                            prog.updated_at = datetime.utcnow()
                            db.session.commit()
                        flash("Correct!" if correct else "Try again—check the feedback.", "success" if correct else "warning")
                except Exception as e:
                    db.session.rollback()
                    flash("Could not grade this question.", "danger")
                    print(f"[perspectives] quiz grade error: {e}")

            elif action in ("submit_minigame", "minigame"):
                mg = lesson.get("minigame")
                if mg:
                    if mg.get("type") == "choice":
                        picked = request.form.get("picked_option")
                        correct = (picked == mg.get("correct_option"))
                        _log_event(db, Event, current_user.id, "minigame_played", slug, str(lesson_id), {"game": "choice", "picked": picked, "correct": correct})
                        flash("Mini-game: nice!" if correct else "Mini-game: close—check the explanation.", "info")
                    elif mg.get("type") == "slider":
                        value = request.form.get("slider_value")
                        _log_event(db, Event, current_user.id, "minigame_played", slug, str(lesson_id), {"game": "slider", "value": value})
                        flash("Thanks for your rating.", "info")

            return redirect(url_for("perspectives_bp.lesson", slug=slug, lesson_id=lesson_id))

        _log_event(db, Event, current_user.id, "lesson_started", slug, str(lesson_id), {})
        return render_template("lesson.html",
                               perspective=perspective,
                               lesson=lesson,
                               quick_checks=lesson.get("quick_checks", []),
                               minigame=lesson.get("minigame"))

    # Register the blueprint last
    app.register_blueprint(bp)
    # Expose helpers if the app wants them
    app.jinja_env.globals["load_all_perspectives"] = _load_all_perspectives
    app.jinja_env.globals["load_perspective"] = _load_perspective
    app.jinja_env.globals["PERSPECTIVES_DIR"] = str(PERSPECTIVES_DIR)
