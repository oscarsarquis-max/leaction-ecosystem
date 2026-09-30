# Imagem reproduzível do backend Spider (sandbox). Usuário não root. Sem secrets.
FROM eclipse-temurin:21-jre-alpine
RUN apk add --no-cache wget \
  && addgroup -S spider && adduser -S spider -G spider
WORKDIR /app
COPY target/spider-0.1.0-SNAPSHOT.jar /app/app.jar
USER spider
EXPOSE 8080
ENV JAVA_OPTS="-XX:MaxRAMPercentage=75"
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
  CMD wget -qO- http://127.0.0.1:8080/actuator/health/liveness || exit 1
ENTRYPOINT ["sh", "-c", "exec java $JAVA_OPTS -jar /app/app.jar"]
