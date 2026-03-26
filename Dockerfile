FROM python:3.11-slim

# FFmpeg + ImageMagick + 한글 폰트 설치
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    imagemagick \
    fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

# ImageMagick 정책 수정 (moviepy 호환)
RUN sed -i 's/rights="none" pattern="@\*"/rights="read|write" pattern="@*"/' /etc/ImageMagick-6/policy.xml || true

WORKDIR /app

# 패키지 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 소스 복사
COPY . .

# 한글 폰트 심링크 (NotoSansCJK → assets/fonts)
RUN mkdir -p assets/fonts && \
    ln -sf /usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc assets/fonts/NotoSansKR-Bold.ttf || true

# output 폴더 생성
RUN mkdir -p output

# 포트 노출
EXPOSE 5000

# 웹 대시보드 + 스케줄러 동시 실행
CMD ["python", "run_cloud.py"]
