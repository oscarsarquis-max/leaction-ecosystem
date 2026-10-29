FROM flyway/flyway:11.10.1
USER root
RUN apt-get update \
  && apt-get install -y --no-install-recommends wget gnupg ca-certificates \
  && wget -qO- https://www.postgresql.org/media/keys/ACCC4CF8.asc | gpg --dearmor -o /usr/share/keyrings/pgdg.gpg \
  && echo "deb [signed-by=/usr/share/keyrings/pgdg.gpg] http://apt.postgresql.org/pub/repos/apt jammy-pgdg main" > /etc/apt/sources.list.d/pgdg.list \
  && apt-get update \
  && apt-get install -y --no-install-recommends postgresql-client-17 \
  && rm -rf /var/lib/apt/lists/*
COPY ops/image-copy-017/migrations /opt/af-migrations
COPY ops/image-copy-017/rehearse-copy-worker-017.sh /opt/rehearse-copy-worker-017.sh
RUN sed -i 's/\r$//' /opt/rehearse-copy-worker-017.sh && chmod +x /opt/rehearse-copy-worker-017.sh
ENTRYPOINT ["/opt/rehearse-copy-worker-017.sh"]
