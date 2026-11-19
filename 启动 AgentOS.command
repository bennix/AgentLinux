#!/bin/bash
set -eu
cd "$(dirname "$0")"
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
exec qemu-system-x86_64 -name AgentOS -machine q35 -accel tcg,thread=multi -cpu max -smp 4 -m 6144 -boot order=d -cdrom "$PWD/ZenMux-Kylin-24.04.5-amd64.iso" -display cocoa -nic user,model=virtio-net-pci "$@"
