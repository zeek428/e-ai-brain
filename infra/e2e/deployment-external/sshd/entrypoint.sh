#!/bin/sh
set -eu

: "${E2E_SSH_AUTHORIZED_KEY:?E2E_SSH_AUTHORIZED_KEY is required}"
printf '%s\n' "$E2E_SSH_AUTHORIZED_KEY" > /home/e2e/.ssh/authorized_keys
chown e2e:e2e /home/e2e/.ssh/authorized_keys
chmod 600 /home/e2e/.ssh/authorized_keys
ssh-keygen -A >/dev/null 2>&1
exec /usr/sbin/sshd -D -e
