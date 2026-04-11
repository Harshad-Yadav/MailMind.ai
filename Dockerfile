FROM node:20-bookworm-slim AS ui-builder
WORKDIR /app/ui
COPY ui/package.json ui/package-lock.json* ./
RUN npm install
COPY ui/ ./
RUN npm run build

FROM python:3.11-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend ./backend
COPY server ./server
COPY training ./training
COPY tasks ./tasks
COPY graders ./graders
COPY dataset ./dataset
COPY models ./models
COPY docker ./docker
COPY openenv.yaml ./openenv.yaml
COPY pyproject.toml ./pyproject.toml
COPY uv.lock ./uv.lock
COPY train.py ./train.py
COPY inference.py ./inference.py
COPY baseline.py ./baseline.py
COPY predict_email.py ./predict_email.py
COPY README.md ./README.md
COPY --from=ui-builder /app/ui/dist ./ui/dist

RUN useradd -m -u 1000 user
RUN chown -R user:user /app
USER user

EXPOSE 7860
CMD ["sh", "-c", "python -m training.data_generator && uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-7860}"]
