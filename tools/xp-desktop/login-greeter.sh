#!/bin/sh
set -eu
assets=/usr/local/share/agentlinux-xp/greeter
prefix=/uk/oddmatics/wintc/logonui
G_RESOURCE_OVERLAYS="$prefix=$assets/branding"
# LightDM starts the welcome screen before a user session supplies its locale.
greeter_locale=$(
    explicit_locale=${LC_ALL:-${LC_MESSAGES:-}}
    if [ -r /etc/default/locale ]; then
        . /etc/default/locale
    fi
    printf '%s' "${explicit_locale:-${LC_ALL:-${LC_MESSAGES:-${LANG:-}}}}"
)
case "$greeter_locale" in
    zh_CN*|zh:*) G_RESOURCE_OVERLAYS="$prefix=$assets/zh:$G_RESOURCE_OVERLAYS" ;;
esac
export G_RESOURCE_OVERLAYS
exec /usr/local/libexec/agentlinux-logonui
