# Hardened OpenJDK Sandbox Image
FROM eclipse-temurin:21-jdk-alpine

RUN addgroup -g 10001 runner && \
    adduser -u 10001 -G runner -s /bin/sh -D runner

WORKDIR /workspace
RUN chown runner:runner /workspace && \
    chmod 750 /workspace

USER runner:runner
ENTRYPOINT ["/bin/sh", "-c"]
