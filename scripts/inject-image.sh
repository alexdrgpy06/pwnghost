#!/usr/bin/env bash
# Inject pwnghost into an existing RPiOS lite image.
# Usage: bash scripts/inject-image.sh </path/to/raspios-lite.img> [output.img]
set -euo pipefail
SRC_IMG="${1:-raspios-lite.img}"
OUT="${2:-pwnghost.img}"

cp "$SRC_IMG" "$OUT"

# Mount + inject pwnghost
docker run --rm --privileged -v "$(pwd):/src" debian:bookworm-slim bash -c "
apt-get update -qq && apt-get install -y -qq kpartx 2>&1 | tail -1
losetup -D; losetup -f /src/$OUT
LOOP=\$(losetup -l | grep $OUT | head -1 | awk '{print \$1}')
kpartx -av \$LOOP >/dev/null
# PiOS: root is partition 2
mount /dev/mapper/loop\${LOOP: -1}p2 /mnt

# Extract pwnghost rootfs (has binary + service)
docker export \$(docker create pwnghost-rootfs) | tar xf - -C /mnt 2>/dev/null || true

# Enable service
ln -sf /etc/systemd/system/pwnghost.service /mnt/etc/systemd/system/multi-user.target.wants/ 2>/dev/null || true

umount /mnt; kpartx -d \$LOOP 2>/dev/null; losetup -D
sync
echo 'INJECTED: /src/$OUT'
" 2>&1 | grep -E "(INJECTED|Processing|read error)" || true
ls -lh "$OUT"
