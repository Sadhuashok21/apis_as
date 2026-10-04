# Hardened PHP Sandbox Image
FROM php:8.3-cli-alpine

RUN addgroup -g 10001 runner && \
    adduser -u 10001 -G runner -s /bin/sh -D runner

WORKDIR /workspace
RUN chown runner:runner /workspace && \
    chmod 750 /workspace

USER runner:runner
ENTRYPOINT ["php"]
