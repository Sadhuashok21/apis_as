# Hardened GCC Sandbox Image
FROM gcc:13-bookworm

RUN groupadd -g 10001 runner && \
    useradd -u 10001 -g runner -m -s /bin/bash runner

WORKDIR /workspace
RUN chown runner:runner /workspace && \
    chmod 750 /workspace

USER runner:runner
ENTRYPOINT ["/bin/bash", "-c"]
