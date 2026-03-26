# 🎬 ShortsForge

유튜브 쇼츠 자동 생성 도구 — 해외출장/박람회/기업연수 실전 꿀팁 콘텐츠

## 빠른 시작

### 1. 설치

```bash
cd shortsforge
pip install -r requirements.txt
```

### 2. API 키 설정

```bash
cp config/.env.example config/.env
# config/.env 파일을 열어서 API 키 입력:
#   GEMINI_API_KEY=...
#   PEXELS_API_KEY=...
```

### 3. 폰트 준비

`assets/fonts/` 에 `NotoSansKR-Bold.ttf` 배치
(Google Fonts에서 무료 다운로드: https://fonts.google.com/noto/specimen/Noto+Sans+KR)

### 4. 실행

```bash
# 쇼츠 1편 생성
python main.py create "해외출장 시 와이파이 절약 꿀팁 3가지"

# 실패 시 재실행
python main.py resume 20260326_해외출장_시_와이파이_절약_꿀팁_3가지 --from tts

# 프로젝트 목록
python main.py list

# 주제 일괄 생성
python main.py batch topics.txt

# 설정 확인
python main.py config show
```

## 프로젝트 구조

```
shortsforge/
├── main.py              # CLI 진입점
├── config/
│   ├── default.yaml     # 전체 설정
│   └── .env             # API 키 (gitignore)
├── core/                # 프레임워크
│   ├── config_loader.py
│   ├── project_manager.py
│   └── pipeline.py
├── modules/             # 교체 가능한 기능 모듈
│   ├── script_gen/      # AI 스크립트 생성
│   ├── tts/             # 음성 합성
│   ├── media_source/    # 스톡 영상 수집
│   └── video_build/     # 영상 조립
├── assets/              # 리소스
│   ├── fonts/
│   └── bgm/
└── output/              # 생성된 프로젝트
```

## 파이프라인

```
주제 입력 → [스크립트 생성] → [TTS 음성] → [미디어 수집] → [영상 조립] → final.mp4
                Gemini        Edge TTS      Pexels API     moviepy
```

## 설정 변경

`config/default.yaml` 에서 AI 모델, TTS 엔진, 영상 스타일 등 모든 설정 변경 가능.
코드 수정 없이 provider 값만 교체하면 공급사 전환됩니다.

## topics.txt 예시

```
해외출장 시 와이파이 절약 꿀팁 3가지
해외박람회 부스 예약 실전 노하우
기업연수 예산 아끼는 항공권 예약법
출장 짐 싸기 프로처럼 하는 법
해외출장 환전 최적 타이밍 꿀팁
```
