"""
ShortsForge 웹 대시보드
Flask 기반, 기존 CLI 모듈을 내부에서 호출
"""

import sys
import json
from pathlib import Path
from flask import Flask, request, jsonify, render_template, send_file

# 프로젝트 루트 설정
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import core.env_setup  # noqa: F401
from core.config_loader import Config
from web.tasks import TaskManager

# ── Flask 앱 ──
app = Flask(__name__, template_folder="templates")
config = Config()
tasks = TaskManager(config)


# ═══════════════════════════════════════════
# 페이지 라우트
# ═══════════════════════════════════════════

@app.route("/")
def index():
    return render_template("index.html")


# ═══════════════════════════════════════════
# API: 프로젝트 관리
# ═══════════════════════════════════════════

@app.route("/api/projects", methods=["GET"])
def api_list_projects():
    """전체 프로젝트 목록"""
    projects = tasks.get_projects()
    return jsonify({"projects": projects})


@app.route("/api/projects/<project_id>", methods=["GET"])
def api_project_detail(project_id):
    """프로젝트 상세"""
    try:
        detail = tasks.get_project_detail(project_id)
        return jsonify(detail)
    except FileNotFoundError:
        return jsonify({"error": "프로젝트를 찾을 수 없습니다"}), 404


@app.route("/api/projects/<project_id>", methods=["DELETE"])
def api_delete_project(project_id):
    """프로젝트 삭제"""
    try:
        tasks.delete_project(project_id)
        return jsonify({"success": True})
    except FileNotFoundError:
        return jsonify({"error": "프로젝트를 찾을 수 없습니다"}), 404


# ═══════════════════════════════════════════
# API: 영상 생성
# ═══════════════════════════════════════════

@app.route("/api/create", methods=["POST"])
def api_create():
    """단일 프로젝트 생성"""
    data = request.json
    topic = data.get("topic", "").strip()
    if not topic:
        return jsonify({"error": "주제를 입력하세요"}), 400

    task = tasks.create_project(topic)
    return jsonify({"task": task})


@app.route("/api/batch", methods=["POST"])
def api_batch():
    """일괄 생성"""
    data = request.json
    topics = data.get("topics", [])
    if isinstance(topics, str):
        topics = [t.strip() for t in topics.split("\n") if t.strip()]

    if not topics:
        return jsonify({"error": "주제를 하나 이상 입력하세요"}), 400

    created = tasks.create_batch(topics)
    return jsonify({"tasks": created, "count": len(created)})


@app.route("/api/resume/<project_id>", methods=["POST"])
def api_resume(project_id):
    """실패한 프로젝트 재실행"""
    data = request.json or {}
    from_stage = data.get("from_stage")

    try:
        task = tasks.resume_project(project_id, from_stage=from_stage)
        return jsonify({"task": task})
    except FileNotFoundError:
        return jsonify({"error": "프로젝트를 찾을 수 없습니다"}), 404


# ═══════════════════════════════════════════
# API: 스크립트 편집
# ═══════════════════════════════════════════

@app.route("/api/projects/<project_id>/script", methods=["GET"])
def api_get_script(project_id):
    """스크립트 조회"""
    try:
        project = tasks.pm.load(project_id)
        if not project.script_path.exists():
            return jsonify({"error": "스크립트가 아직 생성되지 않았습니다"}), 404
        with open(project.script_path, "r", encoding="utf-8") as f:
            script = json.load(f)
        return jsonify({"script": script})
    except FileNotFoundError:
        return jsonify({"error": "프로젝트를 찾을 수 없습니다"}), 404


@app.route("/api/projects/<project_id>/script", methods=["PUT"])
def api_update_script(project_id):
    """스크립트 수정 후 저장"""
    try:
        project = tasks.pm.load(project_id)
        data = request.json
        script = data.get("script", {})

        with open(project.script_path, "w", encoding="utf-8") as f:
            json.dump(script, f, ensure_ascii=False, indent=2)

        return jsonify({"success": True})
    except FileNotFoundError:
        return jsonify({"error": "프로젝트를 찾을 수 없습니다"}), 404


# ═══════════════════════════════════════════
# API: 파일 다운로드
# ═══════════════════════════════════════════

@app.route("/api/projects/<project_id>/video", methods=["GET"])
def api_download_video(project_id):
    """최종 영상 다운로드"""
    try:
        project = tasks.pm.load(project_id)
        if not project.final_video_path.exists():
            return jsonify({"error": "영상이 아직 생성되지 않았습니다"}), 404
        return send_file(
            project.final_video_path,
            as_attachment=True,
            download_name=f"{project_id}.mp4",
        )
    except FileNotFoundError:
        return jsonify({"error": "프로젝트를 찾을 수 없습니다"}), 404


@app.route("/api/projects/<project_id>/audio", methods=["GET"])
def api_download_audio(project_id):
    """오디오 미리듣기"""
    try:
        project = tasks.pm.load(project_id)
        if not project.audio_path.exists():
            return jsonify({"error": "오디오가 없습니다"}), 404
        return send_file(project.audio_path, mimetype="audio/mpeg")
    except FileNotFoundError:
        return jsonify({"error": "프로젝트를 찾을 수 없습니다"}), 404


# ═══════════════════════════════════════════
# API: 작업 상태
# ═══════════════════════════════════════════

@app.route("/api/tasks", methods=["GET"])
def api_tasks():
    """실행 중인 작업 목록"""
    return jsonify({"tasks": tasks.get_all_tasks()})


@app.route("/api/config", methods=["GET"])
def api_config():
    """현재 설정"""
    return jsonify(config.dump())


# ═══════════════════════════════════════════
# API: 주제 뱅크 & 스케줄러
# ═══════════════════════════════════════════

_topic_gen = None

def get_topic_gen():
    global _topic_gen
    if _topic_gen is None:
        from modules.topic_gen import TopicGenerator
        _topic_gen = TopicGenerator(config)
    return _topic_gen


@app.route("/api/topics/bank", methods=["GET"])
def api_topic_bank():
    """주제 뱅크 현황"""
    tg = get_topic_gen()
    summary = tg.get_bank_summary()
    pending = tg.get_pending_topics()
    return jsonify({"summary": summary, "pending": pending})


@app.route("/api/topics/generate", methods=["POST"])
def api_generate_topics():
    """주제 N개 새로 생성"""
    data = request.json or {}
    count = data.get("count", 5)
    tg = get_topic_gen()
    topics = tg.generate_daily(count=count)
    return jsonify({"topics": topics, "count": len(topics)})


@app.route("/api/topics/add", methods=["POST"])
def api_add_topic():
    """수동 주제 추가"""
    data = request.json or {}
    topic = data.get("topic", "").strip()
    if not topic:
        return jsonify({"error": "주제를 입력하세요"}), 400
    tg = get_topic_gen()
    tg.add_manual_topic(topic, category=data.get("category", "해외출장"))
    return jsonify({"success": True})


@app.route("/api/topics/skip", methods=["POST"])
def api_skip_topic():
    """주제 건너뛰기"""
    data = request.json or {}
    topic = data.get("topic", "").strip()
    if not topic:
        return jsonify({"error": "주제를 입력하세요"}), 400
    tg = get_topic_gen()
    tg.mark_skipped(topic)
    return jsonify({"success": True})


@app.route("/api/topics/create-next", methods=["POST"])
def api_create_from_next():
    """대기 주제 중 다음 N개로 영상 바로 생성"""
    data = request.json or {}
    count = data.get("count", 1)
    tg = get_topic_gen()
    next_topics = tg.get_next_topics(count=count)

    created = []
    for t in next_topics:
        task = tasks.create_project(t["topic"])
        tg.mark_used(t["topic"])
        created.append(task)

    return jsonify({"tasks": created, "count": len(created)})


@app.route("/api/scheduler/status", methods=["GET"])
def api_scheduler_status():
    """스케줄러 상태"""
    sched_config = config.get("scheduler", default={})
    tg = get_topic_gen()
    summary = tg.get_bank_summary()
    return jsonify({
        "run_time": sched_config.get("run_time", "06:00"),
        "daily_count": sched_config.get("daily_count", 1),
        "enabled": sched_config.get("enabled", True),
        "topic_bank": summary,
    })


# ═══════════════════════════════════════════
# 서버 실행
# ═══════════════════════════════════════════

if __name__ == "__main__":
    import webbrowser
    port = 5000
    print(f"""
╔══════════════════════════════════════════╗
║     🎬 ShortsForge 웹 대시보드           ║
║                                          ║
║     http://localhost:{port}               ║
║                                          ║
║     종료: Ctrl+C                         ║
╚══════════════════════════════════════════╝
    """)
    webbrowser.open(f"http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)
