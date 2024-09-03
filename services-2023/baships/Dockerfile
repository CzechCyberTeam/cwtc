FROM ubuntu:24.04
RUN apt update && apt install -y cron socat xxd
RUN echo "* * * * * root find /opt/baships/data -mmin +10 -delete" >> /etc/crontab
COPY service /opt/baships
WORKDIR /opt/baships
COPY start.sh .
SHELL ["/bin/bash", "-c"]
ENTRYPOINT cron && socat TCP-LISTEN:9999,reuseaddr,fork,cool-write,keepalive,keepcnt=1,keepidle=3,keepintvl=3 EXEC:./handle.sh,nofork,cool-write
