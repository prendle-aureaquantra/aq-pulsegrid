FROM eclipse-temurin:17-jdk-jammy

ARG SPARK_VERSION=3.5.4
ARG HADOOP_VERSION=3

ENV SPARK_HOME=/opt/spark \
    PATH="${SPARK_HOME}/bin:${PATH}" \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip python3-venv curl unzip \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL "https://archive.apache.org/dist/spark/spark-${SPARK_VERSION}/spark-${SPARK_VERSION}-bin-hadoop${HADOOP_VERSION}.tgz" \
    | tar -xz -C /opt \
    && mv "/opt/spark-${SPARK_VERSION}-bin-hadoop${HADOOP_VERSION}" "${SPARK_HOME}"

WORKDIR /workspace/aq-pulsegrid
COPY pyproject.toml README.md ./
COPY pulsegrid ./pulsegrid
COPY generate_city.py ./

RUN pip3 install --no-cache-dir -e ".[dev]"

CMD ["bash"]
