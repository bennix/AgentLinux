#define _GNU_SOURCE
#include <dlfcn.h>
#include <gio/gio.h>
#include <gtk/gtk.h>
#include <wintc/exec/action.h>

/* Desktop entries may specify an absolute Icon path. WinTC passes both forms
 * to the theme loader, which only understands icon names. */
GdkPixbuf *gtk_icon_theme_load_icon(GtkIconTheme *theme, const gchar *name, gint size,
                                    GtkIconLookupFlags flags, GError **error)
{
    if (name && g_path_is_absolute(name) && size > 0 &&
        g_strcmp0(g_get_prgname(), "wintc-taskband") == 0)
        return gdk_pixbuf_new_from_file_at_scale(name, size, size, TRUE, error);

    typedef GdkPixbuf *(*LoadIcon)(GtkIconTheme *, const gchar *, gint, GtkIconLookupFlags, GError **);
    LoadIcon original = (LoadIcon)dlsym(RTLD_NEXT, "gtk_icon_theme_load_icon");
    return original(theme, name, size, flags, error);
}

gboolean wintc_launch_action(WinTCAction action, GError **error)
{
    const char *script = NULL;
    switch (action) {
    case WINTC_ACTION_MYDOCS: {
        g_autofree char *launcher = g_build_filename(g_get_home_dir(), ".local", "share",
                                                     "agentlinux-xp", "explorer-launch.sh", NULL);
        char *argv[] = { launcher, "--my-documents", NULL };
        return g_spawn_async(NULL, argv, NULL, G_SPAWN_DEFAULT, NULL, NULL, NULL, error);
    }
    case WINTC_ACTION_SEARCH:    script = "search-files.py"; break;
    case WINTC_ACTION_CONNECTTO: script = "connections.py"; break;
    case WINTC_ACTION_MIMEMGMT: script = "default-programs.py"; break;
    case WINTC_ACTION_HELP: {
        char *argv[] = { "/usr/bin/yelp", "help-list:", NULL };
        return g_spawn_async(NULL, argv, NULL, G_SPAWN_DEFAULT, NULL, NULL, NULL, error);
    }
    default: break;
    }
    if (script) {
        g_autofree char *path = g_build_filename(g_get_home_dir(), ".local", "share",
                                                "agentlinux-xp", script, NULL);
        char *argv[] = { path, NULL };
        return g_spawn_async(NULL, argv, NULL, G_SPAWN_DEFAULT, NULL, NULL, NULL, error);
    }
    typedef gboolean (*Launch)(WinTCAction, GError **);
    Launch original = (Launch)dlsym(RTLD_NEXT, "wintc_launch_action");
    if (original)
        return original(action, error);
    g_set_error_literal(error, G_IO_ERROR, G_IO_ERROR_NOT_SUPPORTED, "Start menu action unavailable");
    return FALSE;
}
