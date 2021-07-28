FROM ubuntu:focal

COPY id_rsa.pub /

RUN apt-get update && apt-get install -y \
    bash \
    openssh-server \
 \
 && ssh-keygen -A \
 \
 && adduser --shell=/bin/bash --disabled-password student \
 && adduser --shell=/bin/bash --disabled-password tutor \
 \
 && cd /home/student \
 && mkdir .ssh \
 && cp /id_rsa.pub .ssh/authorized_keys \
 && chown -R student:student .ssh \
 \
 && cd /home/tutor \
 && mkdir .ssh \
 && cp /id_rsa.pub .ssh/authorized_keys \
 && chown -R tutor:tutor .ssh \
 \
 && mkdir /run/sshd \
 \
 && rm -rf /var/cache/apk/* \
 && rm     /id_rsa.pub

COPY docker-entrypoint.sh /entrypoint.sh

COPY etc/motd /etc

COPY etc/skel/.bashrc /home/student

COPY etc/skel/.profile /home/student

COPY etc/skel/.bashrc /home/tutor

COPY etc/skel/.profile /home/tutor

ENTRYPOINT ["/entrypoint.sh"]

