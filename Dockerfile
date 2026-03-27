FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    imagemagick \
    fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

RUN echo '<policymap><policy domain="Undefined" rights="all"/></policymap>' > /etc/ImageMagick-6/policy.xml

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p assets/fonts && \
    ln -sf /usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc assets/fonts/NotoSansKR-Bold.ttf || true

RUN mkdir -p output

EXPOSE 5000

CMD ["python", "run_cloud.py"]
