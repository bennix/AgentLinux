#!/bin/sh
assets="$HOME/.local/share/agentlinux-xp"
. "$assets/session-env.sh"
case ":$PATH:" in
    *":$HOME/.local/bin:"*) ;;
    *) export PATH="$HOME/.local/bin:$PATH" ;;
esac
export LD_PRELOAD="$assets/run-network.so${LD_PRELOAD:+:$LD_PRELOAD}"
exec /usr/bin/run "$@"
