# 📱 핸드폰으로 ShortsForge 클라우드 배포 가이드

> PC 없이 핸드폰 브라우저만으로 전체 세팅 가능합니다.
> 한번만 세팅하면, 이후 매일 자동으로 영상이 만들어집니다.

---

## 전체 흐름 (약 20분)

```
GitHub에 코드 올리기 → Railway 연결 → API 키 입력 → 끝!
```

---

## STEP 1. GitHub에 코드 올리기 (5분)

### 1-1. GitHub 계정 만들기 (이미 있으면 건너뛰기)

1. 핸드폰 브라우저에서 https://github.com 접속
2. "Sign up" → 이메일, 비밀번호 입력 → 가입 완료

### 1-2. 새 저장소(Repository) 만들기

1. GitHub 로그인 후 https://github.com/new 접속
2. 아래처럼 입력:
   - **Repository name**: `shortsforge`
   - **Description**: 유튜브 쇼츠 자동 생성
   - **Public** 선택 (Private도 가능하지만 Railway 무료 연결에 Public이 편함)
   - ☑ "Add a README file" 체크
3. **"Create repository"** 클릭

### 1-3. 파일 업로드

1. 만들어진 저장소 페이지에서 **"Add file"** → **"Upload files"** 클릭
2. shortsforge.zip을 풀어서 나온 파일들을 **전부 드래그앤드롭**

   > 📱 핸드폰에서 파일 선택이 어려우면:
   > - PC에서 한번만 이 업로드 단계를 해도 됩니다
   > - 또는 GitHub 앱(GitHub Mobile)을 설치하면 더 편합니다

3. 아래로 스크롤 → **"Commit changes"** 클릭
4. 업로드 완료되면 파일 목록에 `main.py`, `Dockerfile`, `config/` 등이 보여야 합니다

> ⚠️ 중요: 폴더 구조가 `shortsforge/main.py`가 아니라
> **루트에 바로** `main.py`, `Dockerfile` 등이 있어야 합니다.
> zip 풀면 shortsforge 폴더 안의 **내용물**을 올리세요.

---

## STEP 2. Railway 가입 + 배포 (10분)

### 2-1. Railway 가입

1. 핸드폰 브라우저에서 https://railway.app 접속
2. **"Login"** → **"Login with GitHub"** 클릭
3. GitHub 계정으로 로그인 (권한 허용)

> Railway 무료 플랜: 매달 $5 크레딧 무료 제공
> 쇼츠 하루 1편 기준으로 충분합니다.
> 처음 가입 시 신용카드 등록하면 $5가 부여됩니다.
> (등록 안 해도 Trial로 사용 가능하지만 500시간 제한)

### 2-2. 새 프로젝트 만들기

1. Railway 대시보드에서 **"New Project"** 클릭
2. **"Deploy from GitHub Repo"** 선택
3. `shortsforge` 저장소 선택
4. Railway가 자동으로 Dockerfile을 감지하고 빌드를 시작합니다

> 빌드에 3~5분 걸립니다. 기다리세요.

### 2-3. 환경변수(API 키) 설정

빌드가 진행되는 동안 API 키를 설정합니다.

1. Railway 프로젝트 페이지에서 **서비스(shortsforge)** 클릭
2. **"Variables"** 탭 클릭
3. 아래 3개를 하나씩 추가:

```
GEMINI_API_KEY = (발급받은 Gemini API 키)
PEXELS_API_KEY = (발급받은 Pexels API 키)
PORT = 5000
```

**추가 방법**: "New Variable" 클릭 → 이름과 값 입력 → Add

> API 키 발급이 아직이면:
> - Gemini: https://aistudio.google.com/apikey (Google 로그인 → Create API Key)
> - Pexels: https://www.pexels.com/api/new/ (가입 → Generate API Key)
> 둘 다 핸드폰 브라우저에서 가능합니다.

### 2-4. 도메인 설정 (접속 주소 만들기)

1. 같은 서비스 페이지에서 **"Settings"** 탭
2. **"Networking"** 섹션에서 **"Generate Domain"** 클릭
3. `shortsforge-xxxxx.up.railway.app` 같은 주소가 생성됩니다

> 이 주소가 당신만의 ShortsForge 접속 주소입니다!
> 핸드폰 홈화면에 바로가기를 추가해두세요.

### 2-5. 배포 확인

1. **"Deployments"** 탭에서 배포 상태 확인
2. 초록색 ✅ "Success"가 뜨면 완료!
3. 위에서 만든 도메인 주소로 접속
4. ShortsForge 대시보드가 나타나면 성공! 🎉

---

## STEP 3. 첫 테스트 (2분)

1. 핸드폰 브라우저에서 당신의 Railway 주소 접속
   예: `https://shortsforge-xxxxx.up.railway.app`

2. **"주제 뱅크"** 탭 클릭

3. **"🤖 AI 주제 5개 생성"** 버튼 클릭
   → AI가 자동으로 쇼츠 주제 5개를 만들어줍니다

4. 마음에 드는 주제 옆 **"▶ 생성"** 클릭
   → 영상 자동 생성 시작 (2~3분 소요)

5. 프로젝트 카드가 ✅ 완료로 바뀌면
   → **"⬇ 영상"** 버튼으로 핸드폰에 다운로드

6. 다운로드된 MP4를 유튜브 앱에서 바로 업로드!

---

## STEP 4. 매일 자동 생성 설정 확인

배포하면 스케줄러가 자동으로 함께 실행됩니다.

**기본 설정:** 매일 아침 6시에 영상 1편 자동 생성

변경하려면 GitHub에서 `config/default.yaml` 파일을 편집:

```yaml
scheduler:
  enabled: true
  run_time: "06:00"     # 원하는 시간으로 변경
  daily_count: 1        # 하루 편수 (무료 플랜은 1편 권장)
```

> GitHub에서 파일 수정하면 Railway가 자동으로 재배포합니다.

---

## 매일 하는 일 (1분)

```
아침에 핸드폰으로 대시보드 접속
→ 오늘 자동 생성된 영상 확인
→ ⬇ 다운로드
→ 유튜브 앱에서 업로드
→ 끝!
```

---

## 비용 정리

| 항목 | 비용 |
|------|------|
| Railway 서버 | 무료 ($5/월 크레딧) |
| Gemini API | 무료 (하루 15회) |
| Pexels API | 무료 (월 200회) |
| Edge TTS | 무료 |
| **합계** | **₩0** |

> 하루 1편 기준으로 모든 무료 한도 안에 들어옵니다.
> 하루 2편 이상은 Gemini/Pexels 무료 한도를 넘을 수 있습니다.

---

## 문제 해결

### "배포 실패" (Build Failed)
→ Railway "Deployments" 탭에서 로그 확인
→ 대부분 파일 구조 문제: `Dockerfile`이 루트에 있는지 확인

### "접속이 안 됨"
→ Railway "Settings" → Networking에서 도메인이 생성되었는지 확인
→ "Deployments"에서 배포가 Success인지 확인

### "API 키 오류"
→ Railway "Variables"에서 키가 정확히 입력되었는지 확인
→ 키 앞뒤에 공백이나 따옴표가 없어야 함

### "영상이 안 만들어짐"
→ 대시보드에서 프로젝트 클릭 → 실행 로그 확인
→ 대부분 Pexels API 키 문제 → media provider를 "local"로 변경

### "무료 크레딧이 부족"
→ Railway 무료 크레딧은 매달 초기화됩니다
→ 하루 1편만 생성하면 충분합니다
→ 크레딧이 부족하면 그 달은 일시 정지됨 (데이터 삭제 안됨)

### Railway 대신 다른 무료 서비스를 쓰고 싶으면
이 프로젝트는 Docker 기반이라 아래 서비스에도 동일하게 배포 가능:
- **Render** (https://render.com) — "New Web Service" → GitHub 연결
- **Fly.io** (https://fly.io) — `fly launch` 명령어
- **Koyeb** (https://koyeb.com) — GitHub 연결 배포

모두 Dockerfile을 자동 감지합니다.
