# 🪟 ShortsForge 윈도우 설치 완전 가이드

---

## 이 외부 도구가 뭐고 왜 필요한가?

### FFmpeg — 영상 인코딩 엔진
- moviepy(파이썬 영상 편집 라이브러리)가 **내부적으로** FFmpeg를 호출합니다
- 직접 쓸 일은 없지만, **없으면 영상 파일(MP4) 생성 자체가 불가능**합니다
- 영상계의 "프린터 드라이버" 같은 것입니다

### ImageMagick — 이미지/텍스트 렌더링 엔진
- moviepy의 TextClip(텍스트 오버레이)이 **내부적으로** ImageMagick을 호출합니다
- **없으면 영상 위에 한글 텍스트를 올릴 수 없습니다**
- 영상계의 "폰트 렌더러" 같은 것입니다

> 둘 다 한번 설치하면 끝이고, 직접 실행할 일은 없습니다.
> moviepy가 알아서 백그라운드에서 호출합니다.

---

## 1단계. FFmpeg 설치 (윈도우)

### 방법 A: winget으로 설치 (가장 쉬움, 윈도우 10/11)

```
winget install ffmpeg
```

터미널(PowerShell 또는 CMD)에서 위 명령어 한 줄이면 끝입니다.
설치 후 터미널을 **새로 열고** 확인:

```
ffmpeg -version
```

### 방법 B: 직접 다운로드 (winget 안 되는 경우)

1. https://www.gyan.dev/ffmpeg/builds/ 접속

2. **"release builds"** 섹션에서 **"ffmpeg-release-essentials.zip"** 다운로드
   (full 버전도 상관없지만 essentials가 가벼움)

3. 압축 해제 → 예: `C:\ffmpeg\` 에 배치
   (폴더 안에 bin, doc, presets 등이 보여야 함)

4. **환경변수 PATH에 bin 폴더 추가:**

   ```
   [윈도우 키] → "환경 변수" 검색 → "시스템 환경 변수 편집" 클릭
   → "환경 변수" 버튼 클릭
   → "시스템 변수"에서 "Path" 선택 → "편집"
   → "새로 만들기" → C:\ffmpeg\bin 입력
   → 확인 → 확인 → 확인
   ```

5. **CMD/PowerShell을 새로 열고** 확인:

   ```
   ffmpeg -version
   ```

   `ffmpeg version 7.x ...` 같은 출력이 나오면 성공!

---

## 2단계. ImageMagick 설치 (윈도우)

1. https://imagemagick.org/script/download.php 접속

2. **Windows** 섹션에서 최신 버전 다운로드
   예: `ImageMagick-7.x.x-x-Q16-HDRI-x64-dll.exe`

3. 설치 진행 시 **반드시 아래 두 항목 체크:**

   ```
   ☑ Add application directory to your system path
   ☑ Install legacy utilities (e.g. convert)   ← 이거 중요!!
   ```

   > "Install legacy utilities" 를 안 체크하면 moviepy가 못 찾습니다!

4. 설치 완료 후 **CMD/PowerShell을 새로 열고** 확인:

   ```
   magick -version
   ```

   `Version: ImageMagick 7.x.x ...` 출력되면 성공!

5. **moviepy에 경로 알려주기** (자동으로 못 찾는 경우에만):

   CMD에서:
   ```
   where magick
   ```
   
   출력된 경로(예: `C:\Program Files\ImageMagick-7.1.1-Q16-HDRI\magick.exe`)를
   환경변수로 설정:

   ```
   [윈도우 키] → "환경 변수" 검색
   → "시스템 변수" → "새로 만들기"
   → 변수 이름: IMAGEMAGICK_BINARY
   → 변수 값:   C:\Program Files\ImageMagick-7.1.1-Q16-HDRI\magick.exe
   → 확인
   ```

---

## 3단계. 설치 확인 (한번에 테스트)

CMD 또는 PowerShell을 **새로 열고:**

```
python --version
ffmpeg -version
magick -version
```

세 개 다 버전이 출력되면 준비 완료입니다.

---

## 4단계. ShortsForge 실행

```powershell
# 압축 해제 후 폴더 진입
cd shortsforge

# 가상환경 생성 + 활성화
python -m venv venv
venv\Scripts\activate

# 패키지 설치
pip install -r requirements.txt

# API 키 설정
copy config\.env.example config\.env
# config\.env 파일을 메모장으로 열어서 API 키 입력

# 환경 점검
python test_all.py env

# 단계별 테스트
python test_all.py script
python test_all.py tts
python test_all.py media
python test_all.py video

# 실전 실행
python main.py create "해외출장 시 와이파이 절약 꿀팁 3가지"
```

---

## 자주 묻는 질문

### Q. winget이 안 됩니다
윈도우 10 1709 이전 버전이면 winget이 없습니다.
Microsoft Store에서 "앱 설치 관리자"를 설치하거나, 방법 B(직접 다운로드)를 사용하세요.

### Q. ffmpeg을 설치했는데 "명령을 찾을 수 없습니다"
→ 터미널을 **새로 열어야** 환경변수가 적용됩니다.
→ 그래도 안 되면 PATH에 bin 폴더 경로가 정확한지 확인하세요.

### Q. ImageMagick 설치했는데 moviepy에서 에러남
→ "Install legacy utilities" 체크 안 하고 설치한 경우가 대부분입니다.
→ ImageMagick 제거 후 다시 설치하면서 해당 옵션 체크하세요.

### Q. 설치 후 재부팅 필요한가요?
→ 보통 필요 없지만, 환경변수 적용이 안 되면 재부팅하세요.

### Q. 이 두 프로그램 용량이 얼마나 되나요?
→ FFmpeg: 약 80~130MB
→ ImageMagick: 약 30~50MB
→ 둘 다 가벼운 편입니다.
