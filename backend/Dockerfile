# ---- build: instala as dependências num venv isolado ----
FROM python:3.14-slim AS build
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
RUN python -m venv /venv
COPY requirements.txt .
RUN /venv/bin/pip install -r requirements.txt

# ---- runtime: só o venv + o código, rodando sem root ----
FROM python:3.14-slim
ENV PATH="/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TODO_DATABASE=/data/todo.db
RUN useradd --uid 10001 --no-create-home app \
    && mkdir /data && chown app /data
COPY --from=build /venv /venv
WORKDIR /app
COPY --chown=app . .
USER app
VOLUME /data
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
