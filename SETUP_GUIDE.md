# 🧪 ShortsForge 설치 & 테스트 완전 가이드

> 이 문서를 위에서 아래로 순서대로 따라하면 됩니다.

---

## 📦 STEP 0. 사전 준비물

시작 전 아래 3가지가 필요합니다.

### 0-1. Python 3.10 이상

```bash
python --version
# Python 3.10+ 이어야 합니다
```

없으면:
- Mac: `brew install python`
- Windows: https://python.org 에서 다운로드 (설치 시 "Add to PATH" 체크!)
- Ubuntu: `sudo apt install python3 python3-pip`

### 0-2. FFmpeg

moviepy가 내부적으로 사용합니다. **없으면 영상 생성 불가.**

```bash
ffmpeg -version
```

없으면:
- Mac: `brew install ffmpeg`
- Windows: https://www.gyan.dev/ffmpeg/builds/ 에서 "release full" 다운 → 압축 해제 → bin 폴더를 환경변수 PATH에 추가
- Ubuntu: `sudo apt install ffmpeg`

### 0-3. API 키 2개

| API | 용도 | 무료 여부 | 발급 링크 |
|-----|------|----------|----------|
| **Gemini API** | 스크립트 생성 | ✅ 무료 (하루 15회) | https://aistudio.google.com/apikey |
| **Pexels API** | 스톡 영상 | ✅ 무료 (월 200회) | https://www.pexels.com/api/new/ |

**Gemini API 키 발급 방법:**
1. https://aistudio.google.com/apikey 접속
2. Google 계정 로그인
3. "Create API Key" 클릭
4. 키 복사 (AIza... 로 시작하는 문자열)

**Pexels API 키 발급 방법:**
1. https://www.pexels.com/api/new/ 접속
2. 회원가입 또는 로그인
3. 이름/URL 입력 후 "Generate API Key"
4. 키 복사

---

## 🛠 STEP 1. 프로젝트 설치

```bash
# 1) 압축 해제
unzip shortsforge.zip
cd shortsforge

# 2) 가상환경 생성 (권장)
python -m venv venv

# 가상환경 활성화
# Mac/Linux:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# 3) 패키지 설치
pip install -r requirements.txt
```

**설치 문제가 생기면:**

```bash
# moviepy 설치 실패 시
pip install moviepy==1.0.3

# Mac에서 edge-tts 설치 오류 시
pip install --upgrade pip
pip install edge-tts

# Windows에서 mutagen 오류 시
pip install mutagen --no-cache-dir
```

---

## 🔑 STEP 2. API 키 설정

```bash
# .env 파일 생성
cp config/.env.example config/.env
```

**config/.env 파일을 편집기로 열고 키 입력:**

```
GEMINI_API_KEY=AIzaSy여기에_발급받은_키_붙여넣기
PEXELS_API_KEY=여기에_발급받은_키_붙여넣기
```

> ⚠️ 키 앞뒤에 따옴표나 공백이 없어야 합니다!

---

## 🔤 STEP 3. 한글 폰트 설치

텍스트 오버레이에 사용할 폰트입니다.

1. https://fonts.google.com/noto/specimen/Noto+Sans+KR 접속
2. 우측 상단 "Download family" 클릭
3. 압축 해제 후 `NotoSansKR-Bold.ttf` 파일을 찾아서
4. `shortsforge/assets/fonts/` 폴더에 복사

```bash
# 확인
ls assets/fonts/
# NotoSansKR-Bold.ttf 가 보여야 합니다
```

> 💡 폰트 없이도 테스트 가능하지만, 텍스트가 깨질 수 있습니다.

---

## ✅ STEP 4. 환경 점검 (필수!)

```bash
python test_all.py env
```

**정상 출력 예시:**
```
🔍 [0단계] 환경 점검
=================================================

📌 Python 버전: 3.12.0
   ✅ OK

📌 필수 패키지 확인:
   ✅ PyYAML
   ✅ python-dotenv
   ✅ google-generativeai
   ✅ edge-tts
   ✅ mutagen
   ✅ requests
   ✅ moviepy

📌 FFmpeg 확인:
   ✅ ffmpeg version 6.1 ...

📌 API 키 확인:
   ✅ GEMINI_API_KEY: AIzaSyBx...1234
   ✅ PEXELS_API_KEY: abc12345...6789

🎉 모든 환경 점검 통과!
```

**❌ 오류가 나면** 해당 항목을 해결한 후 다시 실행하세요.

---

## 🧪 STEP 5. 단계별 테스트

**각 단계를 하나씩 테스트합니다.** 한 단계가 성공해야 다음으로 넘어갈 수 있습니다.

### 5-1. 스크립트 생성 테스트

```bash
python test_all.py script
```

**확인 포인트:**
- ✅ Gemini API 호출 성공
- ✅ `output/_test/script.json` 생성됨
- ✅ title, hook, body(3개), cta 모두 포함
- ✅ visual_keyword가 영문으로 포함됨
- ✅ 글자 수 400~500자 범위

**실패 시 체크리스트:**
- `GEMINI_API_KEY` 올바른지 확인
- 인터넷 연결 확인
- `API 키 할당량 초과` → 몇 분 후 재시도

**생성된 script.json 직접 확인:**
```bash
cat output/_test/script.json
```

### 5-2. TTS 음성 합성 테스트

```bash
python test_all.py tts
```

**확인 포인트:**
- ✅ `output/_test/audio.mp3` 생성됨
- ✅ `output/_test/audio_meta.json` 생성됨
- ✅ 오디오 길이 40~55초 범위
- ✅ MP3 파일을 재생하면 한국어 나레이션이 들림

**오디오 재생 확인:**
```bash
# Mac
open output/_test/audio.mp3

# Windows
start output/_test/audio.mp3

# Linux
xdg-open output/_test/audio.mp3
```

**실패 시 체크리스트:**
- `edge-tts` 패키지 설치 확인
- 인터넷 연결 확인 (Edge TTS는 MS 서버 사용)

### 5-3. 미디어(스톡영상) 수집 테스트

```bash
python test_all.py media
```

**확인 포인트:**
- ✅ `output/_test/media/` 폴더에 MP4 파일 3~5개
- ✅ `output/_test/media_manifest.json` 생성됨
- ✅ 각 클립이 세로형(9:16)이면 최적

**다운로드된 클립 확인:**
```bash
ls -la output/_test/media/
```

**실패 시 체크리스트:**
- `PEXELS_API_KEY` 확인
- Pexels API가 없으면 → `config/default.yaml`에서 `media.provider: "local"` 로 변경
- 로컬 모드는 `assets/local_clips/` 에 MP4 파일을 직접 넣어야 함

### 5-4. 영상 조립 테스트

```bash
python test_all.py video
```

> ⏱ 이 단계는 1~3분 소요됩니다.

**확인 포인트:**
- ✅ `output/_test/final.mp4` 생성됨
- ✅ 해상도 1080x1920 (세로)
- ✅ 길이 60초 이하
- ✅ 나레이션 + 배경 영상 + 텍스트 오버레이 확인

**영상 재생:**
```bash
# Mac
open output/_test/final.mp4

# Windows
start output/_test/final.mp4
```

**실패 시 체크리스트:**
- `FFmpeg` 설치 확인: `ffmpeg -version`
- 이전 단계(script, tts, media) 모두 완료됐는지 확인
- 메모리 부족 → 다른 프로그램 종료 후 재시도
- 폰트 오류 → `config/default.yaml`에서 `style.font_path` 확인

---

## 🚀 STEP 6. 전체 파이프라인 테스트

단계별 테스트가 모두 성공했으면, 실제 CLI로 처음부터 끝까지 실행합니다.

```bash
# 테스트 결과 정리
python test_all.py clean

# 실전 실행!
python main.py create "해외박람회 부스 예약 실전 노하우"
```

**정상 실행 흐름:**
```
✅ 프로젝트 생성: 20260326_해외박람회_부스_예약_실전_노하우

🎬 파이프라인 시작: 20260326_해외박람회_부스_예약_실전_노하우
   주제: 해외박람회 부스 예약 실전 노하우

── [SCRIPT] 시작 ──
   🤖 Gemini (gemini-2.0-flash) 스크립트 생성 중...
   📝 제목: 박람회 부스, 이렇게 잡으세요!
   📝 스크립트 저장: script.json (312자, 약 36.7초)
   ✅ 완료 (3.2초)

── [TTS] 시작 ──
   🔊 Edge TTS 합성 중... (voice: ko-KR-SunHiNeural)
   🔊 오디오 생성: audio.mp3 (42.3초)
   📊 타임스탬프: audio_meta.json (5개 구간)
   ✅ 완료 (5.1초)

── [MEDIA] 시작 ──
   🔍 Pexels 검색: 'exhibition booth'
   ⬇️  다운로드: clip_hook.mp4
   ...
   🎞  미디어 수집 완료: 5개 클립
   ✅ 완료 (25.4초)

── [VIDEO] 시작 ──
   🎬 영상 조립 시작...
   📹 [hook] 3.2초 - 부스 배정에서 탈락한 적...
   ...
   💾 인코딩: final.mp4
   📐 해상도: 1080x1920, 길이: 42.3초
   ✅ 완료 (87.2초)

🎉 완료! 영상: output/20260326_해외박람회_부스_예약_실전_노하우/final.mp4
```

---

## 🔄 STEP 7. 유용한 명령어 모음

```bash
# 📋 프로젝트 목록 확인
python main.py list

# 🔁 실패한 프로젝트 재실행 (TTS부터)
python main.py resume 20260326_해외박람회_부스_예약_실전_노하우 --from tts

# 📝 스크립트만 별도 테스트
python main.py run-stage script --topic "기업연수 예산 절약법"

# 📦 여러 주제 일괄 생성
# 먼저 topics.txt 파일 생성:
cat > topics.txt << EOF
해외출장 시 와이파이 절약 꿀팁 3가지
해외박람회 부스 예약 실전 노하우
기업연수 예산 아끼는 항공권 예약법
출장 짐 싸기 프로처럼 하는 법
해외출장 환전 최적 타이밍 꿀팁
EOF

python main.py batch topics.txt

# ⚙️ 설정 확인
python main.py config show
python main.py config validate
```

---

## ⚠️ 자주 발생하는 문제 & 해결법

### 문제 1: `ModuleNotFoundError: No module named 'xxx'`
```bash
# 가상환경 활성화 확인
source venv/bin/activate  # Mac/Linux
venv\Scripts\activate     # Windows

# 패키지 재설치
pip install -r requirements.txt
```

### 문제 2: `FileNotFoundError: ImageMagick` (moviepy)
moviepy의 TextClip은 ImageMagick이 필요할 수 있습니다.
```bash
# Mac
brew install imagemagick

# Ubuntu
sudo apt install imagemagick

# Windows
# https://imagemagick.org/script/download.php 에서 설치
# 설치 시 "Install legacy utilities (convert)" 체크
```

설치 후 moviepy 설정:
```python
# 자동으로 찾지 못하면 환경변수 설정
# Mac/Linux: export IMAGEMAGICK_BINARY=/usr/local/bin/convert
# Windows:   set IMAGEMAGICK_BINARY=C:\Program Files\ImageMagick\magick.exe
```

### 문제 3: `오디오가 60초를 넘음`
`config/default.yaml` 에서 스크립트 길이 제한:
```yaml
script:
  max_chars: 400  # 500 → 400으로 줄이기
```
또는 `output/{프로젝트}/script.json`을 직접 편집 후:
```bash
python main.py resume {프로젝트ID} --from tts
```

### 문제 4: `텍스트가 깨져서 보임`
한글 폰트 미설치:
1. NotoSansKR-Bold.ttf 다운로드
2. `assets/fonts/` 에 배치
3. `config/default.yaml`에서 경로 확인:
```yaml
style:
  font_path: "./assets/fonts/NotoSansKR-Bold.ttf"
```

### 문제 5: `Pexels API 결과 없음 / 키 오류`
Pexels 없이도 작동하도록 전환:
```yaml
# config/default.yaml
media:
  provider: "local"  # pexels → local
```
그리고 `assets/local_clips/` 폴더에 MP4 파일을 직접 넣으세요.

### 문제 6: `Windows에서 경로 오류`
백슬래시 문제:
```yaml
# config/default.yaml — Windows에서도 슬래시 사용
style:
  font_path: "./assets/fonts/NotoSansKR-Bold.ttf"  # ✅
  # font_path: ".\\assets\\fonts\\NotoSansKR-Bold.ttf"  # ❌
```

### 문제 7: `영상이 검은 화면만 나옴`
미디어 클립이 없어서 색상 배경으로 대체된 경우:
- `output/{프로젝트}/media/` 에 MP4 파일이 있는지 확인
- 없으면 미디어 수집 재실행: `python main.py resume {ID} --from media`

---

## 📁 생성되는 파일 구조

하나의 쇼츠 생성 후 폴더 내용:

```
output/20260326_해외출장_와이파이_절약_꿀팁/
├── manifest.json          # 프로젝트 상태 (자동 관리)
├── script.json            # AI 생성 스크립트
├── audio.mp3              # TTS 나레이션 음성
├── audio_meta.json        # 구간별 타임스탬프
├── media_manifest.json    # 다운로드된 클립 목록
├── media/                 # 스톡 영상 클립들
│   ├── clip_hook.mp4
│   ├── clip_01.mp4
│   ├── clip_02.mp4
│   ├── clip_03.mp4
│   └── clip_cta.mp4
└── final.mp4              # ⭐ 최종 완성 영상
```

> 💡 `script.json`을 수동 편집 후 `--from tts` 로 재실행하면
> AI 대본을 수정해서 영상을 다시 만들 수 있습니다.
