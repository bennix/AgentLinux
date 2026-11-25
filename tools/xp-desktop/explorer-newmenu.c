#define _GNU_SOURCE
#include <dlfcn.h>
#include <gio/gio.h>

static gboolean chinese_ui(void)
{
    return g_str_has_prefix(g_get_language_names()[0], "zh");
}

/* Operation in the installed shell's file and folder tasks menu (amfsvw.ui). */
enum { CREATE_FOLDER = 80 };

gboolean wintc_sh_new_menu_create_file(const gchar *path, gint operation,
                                       guint *hash, GError **error)
{
    if (operation != CREATE_FOLDER || !chinese_ui()) {
        typedef gboolean (*CreateFile)(const gchar *, gint, guint *, GError **);
        CreateFile original = (CreateFile)dlsym(RTLD_NEXT, "wintc_sh_new_menu_create_file");
        if (original) return original(path, operation, hash, error);
        g_set_error_literal(error, G_IO_ERROR, G_IO_ERROR_NOT_SUPPORTED, "Shell operation unavailable");
        return FALSE;
    }
    for (guint i = 0; i < 100; i++) {
        g_autofree gchar *name = i ? g_strdup_printf("新建文件夹 (%u)", i) : g_strdup("新建文件夹");
        g_autofree gchar *filename = g_build_filename(path, name, NULL);
        g_autoptr(GFile) file = g_file_new_for_path(filename);
        GError *cause = NULL;
        if (g_file_make_directory(file, NULL, &cause)) {
            if (hash) *hash = g_str_hash(filename);
            return TRUE;
        }
        if (!g_error_matches(cause, G_IO_ERROR, G_IO_ERROR_EXISTS)) {
            g_propagate_error(error, cause);
            return FALSE;
        }
        g_error_free(cause);
    }
    g_set_error_literal(error, G_IO_ERROR, G_IO_ERROR_EXISTS, "已存在同名文件夹");
    return FALSE;
}

#include <wintc/shellext.h>

static WinTCShextActivateItemFunc native_panel;

static gboolean open_panel(WinTCShextHost *host, WinTCShextViewItem *item,
                           WinTCShextPathInfo *path, GError **error)
{
    gchar *argv[] = {"gtk-launch", "agentlinux-xp-control", NULL};
    if (g_spawn_async(NULL, argv, NULL, G_SPAWN_SEARCH_PATH, NULL, NULL, NULL, NULL))
        return TRUE;
    return native_panel(host, item, path, error);
}

gboolean wintc_shext_host_add_toplevel_item(WinTCShextHost *host,
    const gchar *category, const gchar *id, WinTCShextViewItem *item,
    WinTCShextActivateItemFunc activate, GError **error)
{
    typedef gboolean (*RegisterItem)(WinTCShextHost *, const gchar *, const gchar *,
        WinTCShextViewItem *, WinTCShextActivateItemFunc, GError **);
    RegisterItem original = (RegisterItem)dlsym(RTLD_NEXT, "wintc_shext_host_add_toplevel_item");
    if (!original) {
        g_set_error_literal(error, G_IO_ERROR, G_IO_ERROR_NOT_SUPPORTED, "无法注册系统项目");
        return FALSE;
    }
    if (chinese_ui() && g_strcmp0(id, "/") == 0 && g_strcmp0(item->display_name, "Local Disk (/)") == 0) {
        /* The drive monitor owns and frees this heap-allocated label. */
        g_free(item->display_name);
        item->display_name = g_strdup("本地磁盘 (/)");
    } else if (id && g_ascii_strcasecmp(id, "::{38f0b859-bfe8-49fe-88db-024d9c450147}") == 0 &&
               g_strcmp0(item->display_name, "Control Panel") == 0) {
        /* The built-in Control Panel item and its label are static. */
        if (chinese_ui()) item->display_name = "控制面板";
        native_panel = activate;
        activate = open_panel;
    }
    return original(host, category, id, item, activate, error);
}

const gchar *wintc_ishext_view_get_display_name(WinTCIShextView *view)
{
    typedef const gchar *(*DisplayName)(WinTCIShextView *);
    DisplayName original = (DisplayName)dlsym(RTLD_NEXT, "wintc_ishext_view_get_display_name");
    const gchar *name = original ? original(view) : NULL;
    const gboolean chinese = chinese_ui();
    if (!g_strcmp0(G_OBJECT_TYPE_NAME(view), "WinTCShViewDesktop")) return chinese ? "桌面" : name;
    WinTCShextPathInfo path = {0};
    wintc_ishext_view_get_path(view, &path);
    if (path.base_path) {
        if (!g_ascii_strcasecmp(path.base_path, "::{170f6110-d099-4fca-9307-fc1dc43eb71b}"))
            name = chinese ? "我的电脑" : name;
        else if (!g_ascii_strcasecmp(path.base_path, "::{38f0b859-bfe8-49fe-88db-024d9c450147}"))
            name = chinese ? "控制面板" : name;
        else if (!g_strcmp0(path.base_path, "file:///") || !g_strcmp0(path.base_path, "/"))
            name = chinese ? "本地磁盘 (/)" : name;
        else if (g_str_has_prefix(path.base_path, "file://")) {
            static const struct { GUserDirectory directory; const gchar *zh; const gchar *en; } places[] = {
                {G_USER_DIRECTORY_DESKTOP, "桌面", "Desktop"}, {G_USER_DIRECTORY_DOCUMENTS, "我的文档", "My Documents"}, {G_USER_DIRECTORY_PUBLIC_SHARE, "共享文档", "Shared Documents"},
                {G_USER_DIRECTORY_PICTURES, "图片收藏", "My Pictures"}, {G_USER_DIRECTORY_MUSIC, "我的音乐", "My Music"},
            };
            g_autofree gchar *local = g_filename_from_uri(path.base_path, NULL, NULL);
            for (guint i = 0; local && i < G_N_ELEMENTS(places); i++) {
                const gchar *dir = g_get_user_special_dir(places[i].directory);
                if (!g_strcmp0(local, dir) && g_strcmp0(dir, g_get_home_dir())) {
                    name = chinese ? places[i].zh : places[i].en;
                    break;
                }
            }
        }
    }
    wintc_shext_path_info_free_data(&path);
    return name;
}

static GSettings *folder_settings(void)
{
    static GSettings *settings;
    if (!settings) settings = g_settings_new("org.ukui.peony.settings");
    return settings;
}

gint wintc_shext_view_item_compare_by_fs_order(const WinTCShextViewItem *first,
                                               const WinTCShextViewItem *second)
{
    if (first->is_leaf != second->is_leaf && g_settings_get_boolean(folder_settings(), "folder-first"))
        return first->is_leaf ? 1 : -1;
    return wintc_shext_view_item_compare_by_name(first, second);
}

static void refresh_folder_visibility(GSettings *settings, const gchar *key, WinTCIShextView *view)
{
    wintc_ishext_view_refresh_items(view);
}

void _wintc_ishext_view_items_added(WinTCIShextView *view, WinTCShextViewItemsUpdate *update)
{
    typedef void (*ItemsAdded)(WinTCIShextView *, WinTCShextViewItemsUpdate *);
    ItemsAdded original = (ItemsAdded)dlsym(RTLD_NEXT, "_wintc_ishext_view_items_added");
    if (!original) return;
    if (g_strcmp0(G_OBJECT_TYPE_NAME(view), "WinTCShViewFS") != 0) {
        original(view, update);
        return;
    }
    GSettings *settings = g_object_get_data(G_OBJECT(view), "xp-folder-visibility");
    if (!settings) {
        settings = g_object_ref(folder_settings());
        g_object_set_data_full(G_OBJECT(view), "xp-folder-visibility", settings, g_object_unref);
        g_signal_connect_object(settings, "changed::show-file-extension",
                                G_CALLBACK(refresh_folder_visibility), view, 0);
        g_signal_connect_object(settings, "changed::folder-first",
                                G_CALLBACK(refresh_folder_visibility), view, 0);
        g_signal_connect_object(settings, "changed::show-hidden-file",
                                G_CALLBACK(refresh_folder_visibility), view, 0);
    }
    gboolean show_hidden = g_settings_get_boolean(settings, "show-hidden-file");
    gboolean show_extension = g_settings_get_boolean(settings, "show-file-extension");
    if (show_hidden && show_extension) {
        original(view, update);
        return;
    }
    WinTCShextViewItemsUpdate visible = *update;
    visible.data = NULL;
    g_autoptr(GPtrArray) copies = g_ptr_array_new_with_free_func(g_free);
    g_autoptr(GPtrArray) labels = g_ptr_array_new_with_free_func(g_free);
    for (GList *entry = update->data; entry; entry = entry->next) {
        WinTCShextViewItem *item = entry->data;
        const char *name = item->display_name;
        if (!show_hidden && name[0] == '.') continue;
        const char *dot = strrchr(name, '.');
        if (!show_extension && item->is_leaf && dot && dot != name && dot[1]) {
            /* Deliver the caption to the view while keeping its filesystem item intact. */
            WinTCShextViewItem *caption = g_new(WinTCShextViewItem, 1);
            *caption = *item;
            caption->display_name = g_strndup(name, dot - name);
            g_ptr_array_add(labels, caption->display_name);
            g_ptr_array_add(copies, caption);
            item = caption;
        }
        visible.data = g_list_prepend(visible.data, item);
    }
    visible.data = g_list_reverse(visible.data);
    original(view, &visible);
    g_list_free(visible.data);
}

void wintc_shext_host_remove_toplevel_item(WinTCShextHost *host, const gchar *category,
                                          const gchar *id)
{
    /* A remote mount can disappear without ever supplying a local path.
       There is no registered string key to remove in that case. */
    if (!category || !id) return;
    typedef void (*RemoveItem)(WinTCShextHost *, const gchar *, const gchar *);
    RemoveItem original = (RemoveItem)dlsym(RTLD_NEXT, "wintc_shext_host_remove_toplevel_item");
    if (original) original(host, category, id);
}
