# syntax=docker/dockerfile:1.7
# Runtime only. The fat JAR is built on the host/CI (npm + mvnw package).
# No Maven, no npm, no settings.xml, and no source tree in this image.
FROM eclipse-temurin:21-jre-jammy
RUN useradd --system --uid 10001 --create-home actionfinance
WORKDIR /app
COPY --chown=actionfinance:actionfinance ops/image-staging/actionfinance-backend.jar app.jar
USER 10001
EXPOSE 8091
ENV SPRING_PROFILES_ACTIVE=production
ENTRYPOINT ["java", "-jar", "/app/app.jar"]
