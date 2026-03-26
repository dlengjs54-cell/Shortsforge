FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    imagemagick \
    fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

RUN if [ -f /etc/ImageMagick-6/policy.xml ]; then \
    sed -i 's/<policy domain="path" rights="none" pattern="@\*"/<policy domain="path" rights="read|write" pattern="@*"/' /etc/ImageMagick-6/policy.xml; \
    sed -i '/<policy domain="coder" rights="none"/d' /etc/ImageMagick-6/policy.xml; \
    sed -i '/<policy domain="delegate" rights="none"/d' /etc/ImageMagick-6/policy.xml; \
    fi

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p assets/fonts && \
    ln -sf /usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc assets/fonts/NotoSansKR-Bold.ttf || true

RUN mkdir -p output

EXPOSE 5000

CMD ["python", "run_cloud.py"]

