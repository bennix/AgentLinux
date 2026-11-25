#define _GNU_SOURCE
#include <dlfcn.h>
#include <gio/gio.h>

gboolean wintc_launch_command(const gchar *command, GError **error)
{
    g_autofree gchar *buffer = g_strdup(command);
    gchar *address = g_strstrip(buffer);
    gsize length = strlen(address);
    if (length >= 2 && address[0] == '"' && address[length - 1] == '"') {
        address[length - 1] = '\0';
        address++;
    }
    if (g_regex_match_simple(
            "^(?:rundll32(?:\\.exe)?[ \\t]+printui\\.dll,PrintUIEntry|printui(?:\\.exe)?)[ \\t]+/il$",
            address, G_REGEX_CASELESS, 0)) {
        g_autofree gchar *wizard = g_build_filename(g_get_home_dir(), ".local", "share",
                                                    "agentlinux-xp", "add-printer.py", NULL);
        gchar *argv[] = {wizard, NULL};
        return g_spawn_async(NULL, argv, NULL, G_SPAWN_DEFAULT, NULL, NULL, NULL, error);
    }
    gboolean unc = g_str_has_prefix(address, "\\\\") || g_str_has_prefix(address, "//");
    if (!unc && g_ascii_strncasecmp(address, "smb://", 6)) {
        typedef gboolean (*LaunchCommand)(const gchar *, GError **);
        LaunchCommand launch = (LaunchCommand)dlsym(RTLD_NEXT, "wintc_launch_command");
        if (launch) {
            const gchar *start = command;
            while (g_ascii_isspace(*start)) start++;
            gsize len = strcspn(start, " \t\r\n");
            g_autofree gchar *lower = g_ascii_strdown(start, len);
            if (strncmp(start, lower, len) && !strchr(lower, '/')) {
                g_autofree gchar *alias = g_build_filename(g_get_home_dir(), ".local", "bin", lower, NULL);
                g_autofree gchar *target = g_file_read_link(alias, NULL);
                g_autofree gchar *dispatcher = g_build_filename(g_get_home_dir(), ".local", "share",
                                                               "agentlinux-xp", "control-command.sh", NULL);
                g_autofree gchar *directory = g_path_get_dirname(alias);
                g_autofree gchar *resolved = target ? g_canonicalize_filename(target, directory) : NULL;
                if (!g_strcmp0(resolved, dispatcher)) {
                    g_autofree gchar *quoted = g_shell_quote(alias);
                    g_autofree gchar *normalized = g_strconcat(quoted, start + len, NULL);
                    return g_spawn_command_line_async(normalized, error);
                }
            }
            return launch(command, error);
        }
        g_set_error_literal(error, G_IO_ERROR, G_IO_ERROR_FAILED, "Run service unavailable");
        return FALSE;
    }
    g_autofree gchar *uri = NULL;
    if (unc) {
        g_autofree gchar *path = g_strdup(address + 2);
        g_strdelimit(path, "\\", '/');
        g_autofree gchar *escaped = g_uri_escape_string(path, "/:[]", FALSE);
        uri = g_strconcat("smb://", escaped, NULL);
    } else {
        uri = g_strdup(address);
    }
    g_autoptr(GUri) parsed = g_uri_parse(uri, G_URI_FLAGS_HAS_PASSWORD, error);
    if (!parsed) return FALSE;
    if (!g_uri_get_host(parsed) || !*g_uri_get_host(parsed) || g_uri_get_password(parsed)) {
        g_set_error_literal(error, G_IO_ERROR, G_IO_ERROR_INVALID_ARGUMENT,
            g_str_has_prefix(g_get_language_names()[0], "zh") ?
            "请输入服务器和共享名，并在连接窗口中登录。" :
            "Enter the server and share name, then sign in when prompted.");
        return FALSE;
    }
    g_autofree gchar *launcher = g_build_filename(g_get_user_data_dir(), "agentlinux-xp",
                                               "network-places.py", NULL);
    gchar *argv[] = {launcher, "--connect", uri, NULL};
    return g_spawn_async(NULL, argv, NULL, G_SPAWN_DEFAULT, NULL, NULL, NULL, error);
}
