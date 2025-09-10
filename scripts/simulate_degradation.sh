#!/usr/bin/env bash
set -euo pipefail
MODE=${1:-linux}
CMD=${2:-start}
IFACE=${IFACE:-eth0}

if [[ "$MODE" == "linux" ]]; then
  if [[ "$CMD" == "start" ]]; then
    sudo tc qdisc add dev "$IFACE" root netem delay 100ms loss 5%
    echo "netem degradation started on $IFACE"
  else
    sudo tc qdisc del dev "$IFACE" root || true
    echo "netem degradation stopped on $IFACE"
  fi
else
  # macOS/app-degrade: toggle flag file
  FLAG="$(dirname "$0")/../app/.degrade.flag"
  if [[ "$CMD" == "start" ]]; then
    touch "$FLAG" && echo "app degrade flag enabled ($FLAG)"
  else
    rm -f "$FLAG" && echo "app degrade flag disabled"
  fi
fi
