# Apply consolidated economy to AWS panne_demo (first remote apply).
# Does NOT touch local leaction_db / does NOT touch DB panne.
FROM 253137917703.dkr.ecr.us-east-2.amazonaws.com/panne/backend@sha256:7f04f955a29461b85a9676e53d33a26e23d602329bb078273b518d84bcfd6829
USER root
RUN mkdir -p /opt/panne/scripts /opt/panne/backend
# Scripts expect ROOT/backend on sys.path
COPY populate_demo_economy.py /opt/panne/scripts/populate_demo_economy.py
COPY normalize_flour_package_prices.py /opt/panne/scripts/normalize_flour_package_prices.py
COPY apply_entry.py /opt/panne/apply_entry.py
# Point scripts ROOT to /opt/panne and reuse installed app package
RUN ln -sfn /app /opt/panne/backend \
 && chown -R panne:panne /opt/panne
USER 10001:10001
WORKDIR /opt/panne
ENTRYPOINT ["python", "-u", "/opt/panne/apply_entry.py"]
