#!/bin/sh
# Mount the repository so an archive can be read as an ordinary directory tree.
#
# A Borg repository holds nothing recognisable on disk — encrypted, deduplicated
# chunks, root-only. This is how you look inside without extracting anything.
#
#   sudo ./browse.sh                 # mount at /mnt/borg and list the archives
#   sudo ./browse.sh --umount        # unmount when finished
#
# Needs FUSE, which the Debian borg package does not pull in:
#   sudo apt install python3-llfuse
set -eu

MP="${MOUNTPOINT:-/mnt/borg}"

[ "$(id -u)" -eq 0 ] || { echo "run as root — borgmatic reads root-only credentials" >&2; exit 2; }

if [ "${1:-}" = "--umount" ] || [ "${1:-}" = "-u" ]; then
  umount "$MP" && echo "unmounted $MP"
  exit 0
fi

mountpoint -q "$MP" && { echo "already mounted at $MP"; exit 0; }
mkdir -p "$MP"

# grep -v exits 1 when it filters everything away, so test the mount itself
# rather than the pipeline.
borgmatic mount --mount-point "$MP" 2>&1 | grep -v '^[a-z-]*:' || true
if ! mountpoint -q "$MP"; then
  echo "mount failed. If it said 'no FUSE support': sudo apt install python3-llfuse" >&2
  exit 1
fi

echo "mounted at $MP"
echo
echo "archives:"
ls -1 "$MP" | sed 's/^/  /'
echo
echo "Each is the filesystem as it was. Database dumps are under <archive>/borgmatic/."
echo "Unmount when finished:  sudo $0 --umount"
