"""
ShortsForge 단계별 테스트 스크립트

각 모듈을 독립적으로 테스트합니다.
전체 파이프라인 실행 전에 이 스크립트로 환경을 점검하세요.

사용법:
    python test_all.py              전체 테스트
    python test_all.py env          환경 점검만
    python test_all.py script       스크립트 생성만
    python test_all.py tts          TTS만
    python test_all.py media        미디어 수집만
    python test_all.py video        영상 조립만 (이전 단계 결과 필요)
"""

import os
import sys
import json
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# 윈도우 ImageMagick 자동 감지
import core.env_setup  # noqa: F401

TEST_DIR = PROJECT_ROOT / "output" / "_test"
TEST_TOPIC = "해외출장 시 와이파이 절약 꿀팁 3가지"


# ═══════════════════════════════════════════
# 0. 환경 점검
# ═══════════════════════════════════════════

def test_environment():
    """Python 버전, 패키지, API 키, 폰트 점검"""
    print("\n" + "=" * 60)
    print("🔍 [0단계] 환경 점검")
    print("=" * 60)
    
    errors = []
    warnings = []

    # ── Python 버전 ──
    v = sys.version_info
    print(f"\n📌 Python 버전: {v.major}.{v.minor}.{v.micro}")
    if v.major < 3 or v.minor < 10:
        errors.append("Python 3.10 이상이 필요합니다")
    else:
        print("   ✅ OK")

    # ── 필수 패키지 ──
    print("\n📌 필수 패키지 확인:")
    packages = {
        "yaml": "PyYAML",
        "dotenv": "python-dotenv",
        "google.generativeai": "google-generativeai",
        "edge_tts": "edge-tts",
        "mutagen": "mutagen",
        "requests": "requests",
        "moviepy.editor": "moviepy",
    }
    
    for module, pip_name in packages.items():
        try:
            __import__(module)
            print(f"   ✅ {pip_name}")
        except ImportError:
            errors.append(f"{pip_name} 미설치 → pip install {pip_name}")
            print(f"   ❌ {pip_name} — pip install {pip_name}")

    # ── FFmpeg ──
    print("\n📌 FFmpeg 확인:")
    if shutil.which("ffmpeg"):
        import subprocess
        result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True)
        version_line = result.stdout.split("\n")[0] if result.stdout else "unknown"
        print(f"   ✅ {version_line[:60]}")
    else:
        errors.append("FFmpeg 미설치 → moviepy 영상 조립에 필수")
        print("   ❌ FFmpeg 없음")
        print("      설치법:")
        print("      - Windows: winget install ffmpeg (또는 WINDOWS_SETUP.md 참고)")
        print("      - Mac:     brew install ffmpeg")
        print("      - Ubuntu:  sudo apt install ffmpeg")

    # ── ImageMagick ──
    print("\n📌 ImageMagick 확인:")
    magick_cmd = shutil.which("magick") or shutil.which("convert")
    if magick_cmd:
        import subprocess
        try:
            result = subprocess.run([magick_cmd, "-version"], capture_output=True, text=True)
            version_line = result.stdout.split("\n")[0] if result.stdout else "unknown"
            print(f"   ✅ {version_line[:60]}")
        except Exception:
            print(f"   ✅ 경로 발견: {magick_cmd}")
    elif os.getenv("IMAGEMAGICK_BINARY"):
        print(f"   ✅ 환경변수 설정됨: {os.getenv('IMAGEMAGICK_BINARY')}")
    else:
        warnings.append("ImageMagick 미설치 → 텍스트 오버레이에 필요 (WINDOWS_SETUP.md 참고)")
        print("   ⚠️  ImageMagick 없음 (텍스트 오버레이에 필요)")
        print("      설치법:")
        print("      - Windows: WINDOWS_SETUP.md 2단계 참고")
        print("      - Mac:     brew install imagemagick")
        print("      - Ubuntu:  sudo apt install imagemagick")

    # ── 설정 파일 ──
    print("\n📌 설정 파일 확인:")
    config_yaml = PROJECT_ROOT / "config" / "default.yaml"
    env_file = PROJECT_ROOT / "config" / ".env"
    
    if config_yaml.exists():
        print(f"   ✅ {config_yaml}")
    else:
        errors.append(f"설정 파일 없음: {config_yaml}")

    if env_file.exists():
        print(f"   ✅ {env_file}")
    else:
        warnings.append(f".env 파일 없음 → cp config/.env.example config/.env 후 API 키 입력")
        print(f"   ⚠️  {env_file} 없음 (API 키 파일)")

    # ── API 키 ──
    print("\n📌 API 키 확인:")
    if env_file.exists():
        from dotenv import load_dotenv
        import os
        load_dotenv(env_file)
        
        gemini_key = os.getenv("GEMINI_API_KEY", "")
        pexels_key = os.getenv("PEXELS_API_KEY", "")
        
        if gemini_key and gemini_key != "your_gemini_api_key_here":
            print(f"   ✅ GEMINI_API_KEY: {gemini_key[:8]}...{gemini_key[-4:]}")
        else:
            errors.append("GEMINI_API_KEY 미설정")
            print("   ❌ GEMINI_API_KEY 없음")
            print("      발급: https://aistudio.google.com/apikey")

        if pexels_key and pexels_key != "your_pexels_api_key_here":
            print(f"   ✅ PEXELS_API_KEY: {pexels_key[:8]}...{pexels_key[-4:]}")
        else:
            warnings.append("PEXELS_API_KEY 미설정 (미디어 수집 불가, 로컬 폴백 사용)")
            print("   ⚠️  PEXELS_API_KEY 없음 (선택사항)")
            print("      발급: https://www.pexels.com/api/new/")
    else:
        errors.append("config/.env 파일 생성 필요")

    # ── 폰트 ──
    print("\n📌 폰트 확인:")
    font_path = PROJECT_ROOT / "assets" / "fonts" / "NotoSansKR-Bold.ttf"
    if font_path.exists():
        size_mb = font_path.stat().st_size / (1024 * 1024)
        print(f"   ✅ {font_path.name} ({size_mb:.1f}MB)")
    else:
        warnings.append("NotoSansKR-Bold.ttf 없음 → 텍스트 오버레이에 기본 폰트 사용")
        print(f"   ⚠️  {font_path} 없음")
        print("      다운로드: https://fonts.google.com/noto/specimen/Noto+Sans+KR")
        print("      → assets/fonts/NotoSansKR-Bold.ttf 에 배치")

    # ── Config 로드 테스트 ──
    print("\n📌 Config 로드 테스트:")
    try:
        from core.config_loader import Config
        config = Config()
        issues = config.validate()
        if issues:
            for issue in issues:
                warnings.append(issue)
                print(f"   ⚠️  {issue}")
        else:
            print("   ✅ 설정 검증 통과")
    except Exception as e:
        errors.append(f"Config 로드 실패: {e}")
        print(f"   ❌ {e}")

    # ── 결과 요약 ──
    print("\n" + "─" * 60)
    if errors:
        print(f"\n❌ 오류 {len(errors)}건 (반드시 해결 필요):")
        for e in errors:
            print(f"   • {e}")
    if warnings:
        print(f"\n⚠️  경고 {len(warnings)}건 (선택적):")
        for w in warnings:
            print(f"   • {w}")
    if not errors and not warnings:
        print("\n🎉 모든 환경 점검 통과! 테스트를 진행하세요.")
    elif not errors:
        print("\n✅ 필수 환경 OK. 경고 항목은 선택적으로 해결하세요.")
    
    return len(errors) == 0


# ═══════════════════════════════════════════
# 1. 스크립트 생성 테스트
# ═══════════════════════════════════════════

def test_script():
    """Gemini API로 스크립트 생성 테스트"""
    print("\n" + "=" * 60)
    print("📝 [1단계] 스크립트 생성 테스트")
    print(f"   주제: {TEST_TOPIC}")
    print("=" * 60)

    TEST_DIR.mkdir(parents=True, exist_ok=True)

    from core.config_loader import Config
    from modules.script_gen import create_provider

    config = Config()
    provider = create_provider(config)

    print("\n⏳ Gemini API 호출 중...")
    script_data = provider.generate(TEST_TOPIC)
    
    output_path = TEST_DIR / "script.json"
    provider.save(script_data, output_path)

    # 결과 출력
    print(f"\n{'─' * 40}")
    print(f"제목: {script_data['title']}")
    print(f"훅:   {script_data['hook']}")
    for item in script_data["body"]:
        print(f"  {item['order']}. {item['text']}")
        print(f"     🔍 visual_keyword: {item.get('visual_keyword', 'N/A')}")
    print(f"CTA:  {script_data['cta']}")
    print(f"해시: {', '.join(script_data.get('hashtags', []))}")
    
    meta = script_data.get("_meta", {})
    print(f"\n📊 {meta.get('total_chars', '?')}자 / 약 {meta.get('estimated_duration_sec', '?')}초")
    print(f"✅ 저장: {output_path}")
    return True


# ═══════════════════════════════════════════
# 2. TTS 테스트
# ═══════════════════════════════════════════

def test_tts():
    """Edge TTS 음성 합성 테스트"""
    print("\n" + "=" * 60)
    print("🔊 [2단계] TTS 음성 합성 테스트")
    print("=" * 60)

    script_path = TEST_DIR / "script.json"
    if not script_path.exists():
        print("⚠️  script.json 없음 → 샘플 스크립트로 테스트합니다")
        _create_sample_script(script_path)

    from core.config_loader import Config
    from modules.tts import create_provider

    config = Config()
    provider = create_provider(config)

    audio_path = TEST_DIR / "audio.mp3"
    meta_path = TEST_DIR / "audio_meta.json"

    print("\n⏳ Edge TTS 합성 중...")
    provider.synthesize_from_script(script_path, audio_path, meta_path)

    # 결과 확인
    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)

    print(f"\n{'─' * 40}")
    print(f"총 길이: {meta['total_duration_sec']}초")
    for seg in meta["segments"]:
        print(f"  {seg['label']:10s} {seg['start']:5.1f}~{seg['end']:5.1f}초  {seg['text'][:25]}...")
    
    size_kb = audio_path.stat().st_size / 1024
    print(f"\n📊 파일 크기: {size_kb:.0f}KB")
    print(f"✅ 저장: {audio_path}")

    if meta["total_duration_sec"] > 60:
        print(f"⚠️  경고: {meta['total_duration_sec']}초 → 60초 초과! 스크립트 축소 필요")
    
    return True


# ═══════════════════════════════════════════
# 3. 미디어 수집 테스트
# ═══════════════════════════════════════════

def test_media():
    """Pexels API 스톡 영상 수집 테스트"""
    print("\n" + "=" * 60)
    print("🎞  [3단계] 미디어 수집 테스트")
    print("=" * 60)

    script_path = TEST_DIR / "script.json"
    if not script_path.exists():
        print("⚠️  script.json 없음 → 샘플 스크립트로 테스트합니다")
        _create_sample_script(script_path)

    media_dir = TEST_DIR / "media"
    manifest_path = TEST_DIR / "media_manifest.json"

    from core.config_loader import Config
    from modules.media_source import create_provider

    config = Config()
    
    try:
        provider = create_provider(config)
    except ValueError as e:
        if "API 키" in str(e):
            print(f"\n⚠️  {e}")
            print("   PEXELS_API_KEY가 없으면 미디어 수집을 건너뜁니다.")
            print("   config/.env에 PEXELS_API_KEY를 추가하거나,")
            print("   config/default.yaml에서 media.provider를 'local'로 변경하세요.")
            return False
        raise

    print("\n⏳ 스톡 영상 검색 + 다운로드 중...")
    provider.collect_for_script(script_path, media_dir, manifest_path)

    # 결과 확인
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    clips = manifest.get("clips", [])
    print(f"\n{'─' * 40}")
    for clip in clips:
        file_path = media_dir / clip["file"]
        size_mb = file_path.stat().st_size / (1024 * 1024) if file_path.exists() else 0
        print(f"  📹 {clip['file']:20s} [{clip['keyword']:25s}] {size_mb:.1f}MB")

    print(f"\n✅ {len(clips)}개 클립 다운로드 완료")
    return True


# ═══════════════════════════════════════════
# 4. 영상 조립 테스트
# ═══════════════════════════════════════════

def test_video():
    """moviepy 영상 조립 테스트"""
    print("\n" + "=" * 60)
    print("🎬 [4단계] 영상 조립 테스트")
    print("=" * 60)

    # 필요 파일 확인
    required = {
        "script.json": TEST_DIR / "script.json",
        "audio.mp3": TEST_DIR / "audio.mp3",
        "audio_meta.json": TEST_DIR / "audio_meta.json",
        "media_manifest.json": TEST_DIR / "media_manifest.json",
    }
    
    missing = [name for name, path in required.items() if not path.exists()]
    if missing:
        print(f"\n❌ 이전 단계 결과 파일 없음: {', '.join(missing)}")
        print("   먼저 이전 단계 테스트를 실행하세요:")
        print("   python test_all.py script && python test_all.py tts && python test_all.py media")
        return False

    media_dir = TEST_DIR / "media"
    if not list(media_dir.glob("*.mp4")):
        print("\n⚠️  media 폴더에 mp4 파일 없음 → 색상 배경으로 대체됩니다")

    from core.config_loader import Config
    from core.project_manager import Project
    from modules.video_build import compose

    config = Config()
    project = Project(TEST_DIR)
    
    # manifest가 없으면 임시 생성
    if not project.manifest_path.exists():
        manifest = {
            "id": "_test",
            "topic": TEST_TOPIC,
            "status": {"script": "done", "tts": "done", "media": "done", "video": "pending"},
        }
        with open(project.manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)

    print("\n⏳ 영상 조립 중... (1~3분 소요)")
    compose(project=project, config=config)

    # 결과 확인
    final_path = TEST_DIR / "final.mp4"
    if final_path.exists():
        size_mb = final_path.stat().st_size / (1024 * 1024)
        print(f"\n{'─' * 40}")
        print(f"📊 파일 크기: {size_mb:.1f}MB")
        print(f"✅ 영상 생성 완료: {final_path}")
        print(f"\n💡 영상 확인: 파일을 더블클릭하거나 VLC에서 열어보세요")
        return True
    else:
        print("\n❌ final.mp4 생성 실패")
        return False


# ═══════════════════════════════════════════
# 유틸리티
# ═══════════════════════════════════════════

def _create_sample_script(output_path: Path):
    """테스트용 샘플 스크립트 생성 (API 호출 없이)"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sample = {
        "title": "해외출장 와이파이 꿀팁 3가지",
        "hook": "해외에서 데이터 요금 폭탄 맞으셨죠?",
        "body": [
            {
                "order": 1,
                "text": "첫째, 출발 전 통신사 로밍 요금제를 꼭 비교하세요. 하루 만원 이하 요금제가 많습니다",
                "visual_keyword": "airport wifi smartphone",
            },
            {
                "order": 2,
                "text": "둘째, 현지 유심보다 이심이 더 편합니다. 공항에서 바로 개통되니까요",
                "visual_keyword": "sim card travel",
            },
            {
                "order": 3,
                "text": "셋째, 호텔 와이파이만 믿지 마세요. 포켓 와이파이 하나면 어디서든 안심입니다",
                "visual_keyword": "portable wifi device",
            },
        ],
        "cta": "더 많은 해외출장 꿀팁이 궁금하시면 리키항공에 문의하세요",
        "hashtags": ["#해외출장", "#와이파이", "#출장꿀팁", "#리키항공", "#로밍"],
        "_meta": {"total_chars": 245, "estimated_duration_sec": 28.8},
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(sample, f, ensure_ascii=False, indent=2)
    print(f"   📝 샘플 스크립트 생성: {output_path}")


def clean_test():
    """테스트 폴더 정리"""
    if TEST_DIR.exists():
        shutil.rmtree(TEST_DIR)
        print(f"🗑  테스트 폴더 삭제: {TEST_DIR}")


# ═══════════════════════════════════════════
# 메인
# ═══════════════════════════════════════════

def main():
    target = sys.argv[1] if len(sys.argv) > 1 else "all"

    tests = {
        "env": test_environment,
        "script": test_script,
        "tts": test_tts,
        "media": test_media,
        "video": test_video,
        "clean": clean_test,
    }

    if target == "all":
        print("🚀 ShortsForge 전체 테스트")
        print("=" * 60)

        if not test_environment():
            print("\n❌ 환경 점검 실패. 위 오류를 해결한 후 다시 시도하세요.")
            return

        for name in ["script", "tts", "media", "video"]:
            try:
                success = tests[name]()
                if not success:
                    print(f"\n⚠️  {name} 단계에서 중단. 이후 단계를 건너뜁니다.")
                    break
            except Exception as e:
                print(f"\n❌ {name} 테스트 실패: {e}")
                import traceback
                traceback.print_exc()
                break

        print("\n" + "=" * 60)
        print("테스트 완료. output/_test/ 폴더에서 결과를 확인하세요.")
        print("정리: python test_all.py clean")

    elif target in tests:
        try:
            tests[target]()
        except Exception as e:
            print(f"\n❌ 오류: {e}")
            import traceback
            traceback.print_exc()
    else:
        print(f"사용법: python test_all.py [env|script|tts|media|video|clean|all]")


if __name__ == "__main__":
    main()
