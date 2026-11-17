FROM python:3.12.3-slim-bookworm
# Exact reported versions only; never silently substitute dependencies.
RUN python -m pip install --no-cache-dir --only-binary=:all: numpy==2.5.4 pandas==3.1.1
