#!/usr/bin/env python3
"""Build pwnghost bootable SD card image. No final copy needed."""
import os, subprocess, tempfile, time

OUT = '/tmp/pwnghost.img'
SZ = 2048

def sh(cmd, **kw):
    print(f"  {cmd.split()[0]}...")
    subprocess.run(cmd, shell=True, check=kw.get('check', True))

print("=== PwnGhost image builder ===")
sh("apt-get update -qq && apt-get install -y -qq parted e2fsprogs dosfstools kpartx curl 2>&1 | tail -1", check=False)

# Create image directly on host volume
sh(f"dd if=/dev/zero of={OUT} bs=1M count={SZ} status=none")
sh(f"parted -s {OUT} mklabel msdos")
sh(f"parted -s {OUT} mkpart primary fat32 1MiB 256MiB")
sh(f"parted -s {OUT} mkpart primary ext4 256MiB 100%")
sh(f"parted -s {OUT} set 1 boot on")

# Loop + mount
sh(f"losetup -D")
loop = subprocess.run(f"losetup -f --show {OUT}", shell=True, capture_output=True, text=True).stdout.strip()
sh(f"kpartx -av {loop}", check=False)
time.sleep(0.5)
dev = loop.replace('/dev/', '')
b = f"/dev/mapper/{dev}p1"
r = f"/dev/mapper/{dev}p2"

# Format
sh(f"mkfs.vfat -F32 {b} -n PWNBOOT")
sh(f"mkfs.ext4 -F {r} -L PWNROOT")

# Mount
mnt = tempfile.mkdtemp()
boot_mnt = tempfile.mkdtemp()
sh(f"mount {r} {mnt}")
sh(f"mount {b} {boot_mnt}")

# Boot files
sh("curl -sL https://github.com/raspberrypi/firmware/archive/refs/heads/master.tar.gz -o /tmp/fw.tar.gz")
sh("mkdir -p /tmp/fw && tar xzf /tmp/fw.tar.gz -C /tmp/fw", check=False)
# Also put boot files in root's /boot so it boots from both
subprocess.run(f"cp /tmp/fw/firmware-master/boot/kernel*.img {boot_mnt}/", shell=True, check=False)
subprocess.run(f"cp /tmp/fw/firmware-master/boot/*.dtb {boot_mnt}/", shell=True, check=False)
subprocess.run(f"cp /tmp/fw/firmware-master/boot/start*.elf {boot_mnt}/", shell=True, check=False)
subprocess.run(f"cp /tmp/fw/firmware-master/boot/fixup*.dat {boot_mnt}/", shell=True, check=False)
with open(f"{boot_mnt}/config.txt", 'w') as f:
    f.write("arm_64bit=1\nkernel=kernel8.img\ndevice_tree=bcm2710-rpi-zero-2-w.dtb\ngpu_mem=16\n")
with open(f"{boot_mnt}/cmdline.txt", 'w') as f:
    f.write("console=serial0,115200 console=tty1 root=/dev/mmcblk0p2 rootfstype=ext4 fsck.repair=yes rootwait quiet\n")

# Mirror boot into root's /boot
sh(f"mkdir -p {mnt}/boot && cp -r {boot_mnt}/* {mnt}/boot/")

# Rootfs from pre-exported tar
sh("tar xzf /src/rootfs.tar.gz -C /mnt 2>/dev/null || true")

# pi user
subprocess.run("grep -q ^pi: /mnt/etc/passwd || echo 'pi:x:1000:1000:PI,,,:/home/pi:/bin/bash' >> /mnt/etc/passwd", shell=True)
subprocess.run("echo 'pi:$6$r9nVw1Rs$3i7F9WJ9F7G6L6v5V5c5C5x5Z5a5A5s5S5d5F5g5H5j5K5l5Z5x5C5v5B5n5M5:19860:0:99999:7:::' >> /mnt/etc/shadow", shell=True)
subprocess.run("echo 'pi ALL=ALL NOPASSWD:ALL' >> /mnt/etc/sudoers", shell=True)

# Service
os.makedirs("/mnt/etc/systemd/system/multi-user.target.wants", exist_ok=True)
subprocess.run("ln -sf /etc/systemd/system/pwnghost.service /mnt/etc/systemd/system/multi-user.target.wants/pwnghost.service", shell=True)

# Done - sync and detach
sh("sync")
time.sleep(1)
sh(f"umount {boot_mnt} {mnt}", check=False)
sh(f"kpartx -d {loop}", check=False)
sh("losetup -D", check=False)
sh("cp /tmp/pwnghost.img /src/pwnghost.img")
print("=== DONE: /src/pwnghost.img ===")
