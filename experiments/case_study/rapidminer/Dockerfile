FROM maven:3.9-eclipse-temurin-11@sha256:7bb84a451705605a47d24eb844d4d9ab03e33e131a507db76aafe25db3907f64
WORKDIR /runner
COPY pom.xml .
RUN mvn -B -ntp org.apache.maven.plugins:maven-dependency-plugin:3.8.1:copy-dependencies -DoutputDirectory=/runner/lib \
    && echo '2b6c10110cd7a6bed54337dba4d78ac0a1fa0dc8b08f238d6870f2b662c3a4ff  lib/rapidminer-studio-core-10.1.0.jar' | sha256sum -c -
COPY RunProcess.java .
RUN javac -cp 'lib/*' RunProcess.java
ENTRYPOINT ["java", "-Djava.awt.headless=true", "-cp", ".:lib/*", "RunProcess"]
