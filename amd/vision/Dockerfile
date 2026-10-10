# CPU-only vision/OCR service: no torch and no TORCH_VARIANT build argument.
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 VISION_HOST=0.0.0.0 VISION_PORT=8084
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt \
 && pip uninstall -y opencv-python \
 && pip install --force-reinstall --no-deps opencv-python-headless==4.11.0.86 \
 && useradd --create-home --uid 10001 app
COPY --chown=app:app app.py config.py textaxes.py annotate.py ./
COPY --chown=app:app readers/ readers/
COPY --chown=app:app config/ config/
USER app
EXPOSE 8084
HEALTHCHECK --interval=10s --timeout=5s --start-period=10s --retries=3 CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:'+os.environ.get('VISION_PORT','8084')+'/health',timeout=4)"
CMD ["python", "app.py"]
