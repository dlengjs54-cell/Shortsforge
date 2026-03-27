FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    imagemagick \
    fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

RUN POLICY_PATH=$(find /etc -type f -name policy.xml | grep ImageMagick | head -n 1) && \
    echo "Using policy file: $POLICY_PATH" && \
    cp "$POLICY_PATH" "${POLICY_PATH}.bak" && \
    sed -i 's#<policy domain="path" rights="none" pattern="@\*"/>#<policy domain="path" rights="read|write" pattern="@*"/>#g' "$POLICY_PATH"

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p assets/fonts && \
    ln -sf /usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc assets/fonts/NotoSansKR-Bold.ttf || true

RUN mkdir -p output

CMD ["python", "run_cloud.py"]
