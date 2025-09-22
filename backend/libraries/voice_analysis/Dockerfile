# 최적화된 Multi-stage build (캐시 효율성 개선)
# Stage 1: Build dependencies
FROM python:3.11-slim as builder

WORKDIR /app

# 시스템 의존성 설치 (빌드용) - 캐시 최적화
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# requirements 파일들을 먼저 복사 (변경이 적은 파일)
COPY requirements-base.txt requirements-ml.txt ./

# 기본 의존성 설치
RUN pip install --no-cache-dir --user -r requirements-base.txt

# ML 의존성 설치
RUN pip install --no-cache-dir --user -r requirements-ml.txt

# PyTorch CPU 버전 설치 (더 작은 CPU 전용 버전)
RUN pip install --no-cache-dir --user \
    --index-url https://download.pytorch.org/whl/cpu \
    --timeout 300 \
    torch==2.1.0+cpu torchaudio==2.1.0+cpu

# Stage 2: Production image
FROM python:3.11-slim

WORKDIR /app

# 필수 시스템 패키지만 설치 (한 번의 RUN으로 레이어 최소화)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ffmpeg \
    libsndfile1 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* && \
    pip cache purge

# 빌더 스테이지에서 설치된 Python 패키지 복사
COPY --from=builder /root/.local /root/.local

# PATH 환경변수 설정
ENV PATH=/root/.local/bin:$PATH

# 환경변수 설정 (레이어 최소화를 위해 먼저 설정)
ENV PYTHONPATH=/app \
    PORT=8080 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# 필요한 파일만 선택적으로 복사
COPY main.py ./
COPY analysis ./analysis/
COPY utils ./utils/
COPY serviceAccountKey.json ./

# Python 캐시 정리
RUN find . -type f -name "*.pyc" -delete && \
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true && \
    rm -rf /root/.cache /tmp/* /var/tmp/*

EXPOSE 8080

CMD ["python", "main.py"]