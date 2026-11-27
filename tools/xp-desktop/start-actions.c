#define _GNU_SOURCE
#include <dlfcn.h>
#include <garcon/garcon.h>
#include <gio/gio.h>
#include <gtk/gtk.h>
#include <wintc/exec/action.h>

/* WinTC seeds its frequently used list from all.menu, including hidden helpers. */
GList *garcon_menu_get_elements(GarconMenu *menu)
{
    typedef GList *(*GetElements)(GarconMenu *);
    GetElements original = (GetElements)dlsym(RTLD_NEXT, "garcon_menu_get_elements");
    GList *elements = original(menu);
    if (g_strcmp0(g_get_prgname(), "wintc-taskband") != 0)
        return elements;

    for (GList *item = elements, *next; item; item = next) {
        next = item->next;
        if (!garcon_menu_element_get_visible(item->data))
            elements = g_list_delete_link(elements, item);
    }
    return elements;
}

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
    case WINTC_ACTION_MYPICS:
    case WINTC_ACTION_MYMUSIC: {
        GUserDirectory kind = action == WINTC_ACTION_MYPICS ? G_USER_DIRECTORY_PICTURES
                                                            : G_USER_DIRECTORY_MUSIC;
        const char *folder = g_get_user_special_dir(kind);
        if (!folder) break;
        g_autofree char *launcher = g_build_filename(g_get_home_dir(), ".local", "share",
                                                     "agentlinux-xp", "explorer-launch.sh", NULL);
        char *argv[] = { launcher, (char *)folder, NULL };
        return g_spawn_async(NULL, argv, NULL, G_SPAWN_DEFAULT, NULL, NULL, NULL, error);
    }
    case WINTC_ACTION_SEARCH:    script = "search-files.py"; break;
    case WINTC_ACTION_CONTROL:   script = "control-panel.py"; break;
    case WINTC_ACTION_CONNECTTO: script = "connections.py"; break;
    case WINTC_ACTION_MIMEMGMT: script = "default-programs.py"; break;
    case WINTC_ACTION_HELP: script = "help-center.py"; break;
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
