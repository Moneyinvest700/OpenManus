FROM python:3.12-slim-bookworm
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends git curl libatomic1 && rm -rf /var/lib/apt/lists/* && pip install --no-cache-dir uv
COPY . /app/
RUN uv pip install --system -r requirements.txt && playwright install --with-deps chromium
RUN useradd -m -u 10001 manus && chown -R manus:manus /app /home/manus
ENV PYTHONUNBUFFERED=1 HOME=/home/manus
RUN uvx browser-use install && chown -R manus:manus /home/manus
USER manus
CMD ["python", "web.py"]
