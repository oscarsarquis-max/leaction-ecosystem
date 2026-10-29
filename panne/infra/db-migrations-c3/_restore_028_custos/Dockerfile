# One-shot restore image: local panne_demo dump â†’ AWS panne_demo
FROM public.ecr.aws/docker/library/postgres:17-alpine
RUN apk add --no-cache python3 py3-pip \
 && pip3 install --break-system-packages --quiet "boto3>=1.35" "psycopg[binary]>=3.2" "sqlalchemy>=2.0"
COPY panne_demo_custos.dump /dump/panne_demo_custos.dump
COPY restore_entry.py /restore_entry.py
USER postgres
ENTRYPOINT ["python3", "-u", "/restore_entry.py"]

