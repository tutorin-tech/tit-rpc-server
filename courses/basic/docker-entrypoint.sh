#!/bin/bash

set -x

USER_PASSWORD=$(tr -dc 'a-zA-Z0-9' </dev/urandom | head -c 32)

PORT=${PORT:=2222}

set +x

sed -i 's/#PasswordAuthentication yes/PasswordAuthentication no/g' /etc/ssh/sshd_config

sed -i "s/#Port 22/Port ${PORT}/g" /etc/ssh/sshd_config

passwd student << EOF
${USER_PASSWORD}
${USER_PASSWORD}
EOF

passwd tutor << EOF
${USER_PASSWORD}
${USER_PASSWORD}
EOF

>&2 echo "Running sshd"
/usr/sbin/sshd -D

