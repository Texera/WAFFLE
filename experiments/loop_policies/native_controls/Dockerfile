FROM waffle-rapidminer:10.1.0
COPY RunNative.java /runner/
RUN javac -cp 'lib/*' RunNative.java
ENTRYPOINT ["java","-Djava.awt.headless=true","-cp",".:lib/*","RunNative"]
