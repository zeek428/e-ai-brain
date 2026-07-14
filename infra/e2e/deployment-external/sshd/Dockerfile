FROM alpine:3.20

RUN apk add --no-cache openssh-server \
  && adduser -D -s /bin/sh e2e \
  && passwd -d e2e \
  && mkdir -p /run/sshd /home/e2e/.ssh \
  && chown -R e2e:e2e /home/e2e/.ssh \
  && chmod 700 /home/e2e/.ssh

COPY entrypoint.sh /entrypoint.sh
RUN chmod 755 /entrypoint.sh

EXPOSE 22
ENTRYPOINT ["/entrypoint.sh"]
