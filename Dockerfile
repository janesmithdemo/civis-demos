FROM civisanalytics/datascience-python:8.4 AS builder

WORKDIR /build
COPY pyproject.toml ./
COPY survey_demo ./survey_demo
RUN pip install --no-cache-dir --prefix=/install .

FROM civisanalytics/datascience-python:8.4

WORKDIR /app
COPY --from=builder /install /usr/local
COPY config ./config
COPY scripts ./scripts
COPY survey_demo ./survey_demo
