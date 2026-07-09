#!/bin/sh
set -eu

SOURCE_DIR="/opt/incident_platform_seed"
TARGET_DIR="/opt/splunk/etc/apps/incident_platform"

if [ -d "$SOURCE_DIR" ]; then
  sudo rm -rf "$TARGET_DIR"
  sudo mkdir -p "$TARGET_DIR"
  sudo cp -R "$SOURCE_DIR"/. "$TARGET_DIR"/
  sudo chown -R splunk:splunk "$TARGET_DIR"
fi

exec /sbin/entrypoint.sh "$@"
