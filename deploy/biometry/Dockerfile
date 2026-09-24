FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /srv/biometry

COPY app/requirements.txt ./requirements.txt
# NumPy 2.4+ wheels require x86-64-v2; this VM exposes only x86-64-v1.
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir --no-deps numpy==2.3.5 \
    && groupadd --system biometry \
    && useradd --system --gid biometry --home-dir /srv/biometry biometry

COPY app/app ./app
COPY app/frontend ./frontend
COPY app/models ./models

RUN chown -R biometry:biometry /srv/biometry
USER biometry

EXPOSE 8100
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8100", "--workers", "1"]
