export GTK_THEME='Windows XP style (Blue)'
export QT_STYLE_OVERRIDE=gtk2
case "$(cat "$HOME/.config/agentlinux-xp/language" 2>/dev/null)" in
    en_US.UTF-8) LANG=en_US.UTF-8; LANGUAGE=en_US:en ;;
    zh_CN.UTF-8) LANG=zh_CN.UTF-8; LANGUAGE=zh_CN:zh ;;
    *)
        # LightDM can pass LANGUAGE=en even when the installed locale is Chinese.
        case "${LC_ALL:-${LC_MESSAGES:-${LANG:-}}}:${LANGUAGE:-}" in
            zh_CN*:en) export LANGUAGE=zh_CN:zh ;;
        esac
        return 0 ;;
esac
unset LC_ALL LC_MESSAGES
export LANG LANGUAGE
