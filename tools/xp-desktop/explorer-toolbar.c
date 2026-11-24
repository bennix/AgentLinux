#include <gtk/gtk.h>

static const struct { const char *english, *chinese; } labels[] = {
    {"Back", "后退"}, {"Forward", "前进"}, {"Up", "向上"},
    {"Search", "搜索"}, {"Folders", "文件夹"}, {"Views", "视图"},
};

static void translate_task_label(GtkLabel *label)
{
    const gchar *name = gtk_buildable_get_name(GTK_BUILDABLE(label));
    if (g_strcmp0(name, "label-heading") && g_strcmp0(name, "label-item-label"))
        return;
    static const struct { const char *english, *chinese; } tasks[] = {
        {"Folder Tasks", "文件夹任务"}, {"Extract all files", "全部解压"},
        {"File and Folder Tasks", "文件和文件夹任务"}, {"Other Places", "其他位置"},
        {"System Tasks", "系统任务"}, {"Details", "详细信息"},
        {"Make a new folder", "创建新文件夹"}, {"Share this folder", "共享此文件夹"},
        {"Publish this folder to the Web", "将此文件夹发布到 Web"},
        {"View system information", "查看系统信息"}, {"Add or remove programs", "添加或删除程序"},
        {"Change a setting", "更改设置"}, {"My Computer", "我的电脑"},
        {"My Documents", "我的文档"}, {"My Network Places", "网上邻居"},
        {"Control Panel", "控制面板"}, {"Shared Documents", "共享文档"},
    };
    for (guint i = 0; i < G_N_ELEMENTS(tasks); i++) {
        if (g_strcmp0(gtk_label_get_text(label), tasks[i].english) == 0) {
            gtk_label_set_text(label, tasks[i].chinese);
            return;
        }
    }
}

/* Keep the editable namespace address intact for navigation and copying. */
static gboolean draw_address(GtkWidget *widget, cairo_t *cr, gpointer data)
{
    GtkEntry *entry = GTK_ENTRY(widget);
    if (gtk_widget_has_focus(widget) ||
        g_ascii_strcasecmp(gtk_entry_get_text(entry),
                           "::{170f6110-d099-4fca-9307-fc1dc43eb71b}") != 0)
        return FALSE;
    GtkStyleContext *style = gtk_widget_get_style_context(widget);
    gint width = gtk_widget_get_allocated_width(widget);
    gint height = gtk_widget_get_allocated_height(widget);
    gtk_render_background(style, cr, 0, 0, width, height);
    gtk_render_frame(style, cr, 0, 0, width, height);
    PangoLayout *layout = gtk_widget_create_pango_layout(widget, "我的电脑");
    gint x, y;
    gtk_entry_get_layout_offsets(entry, &x, &y);
    gtk_render_layout(style, cr, MAX(x, 3), y, layout);
    g_object_unref(layout);
    return TRUE;
}

static gboolean open_system_task(GtkLinkButton *link, gpointer desktop_id)
{
    gchar *argv[] = {"gtk-launch", desktop_id, NULL};
    GError *error = NULL;
    if (!g_spawn_async(NULL, argv, NULL, G_SPAWN_SEARCH_PATH, NULL, NULL, NULL, &error)) {
        g_warning("Could not launch system task: %s", error->message);
        g_error_free(error);
    }
    return TRUE;
}

static gboolean open_user_directory(GtkLinkButton *link, gpointer directory)
{
    const gchar *path = g_get_user_special_dir(GPOINTER_TO_INT(directory));
    if (path && g_file_test(path, G_FILE_TEST_IS_DIR)) {
        g_autofree gchar *launcher = g_build_filename(g_get_user_data_dir(),
            "agentlinux-xp", "explorer-launch.sh", NULL);
        gchar *argv[] = {launcher, (gchar *)path, NULL};
        GError *error = NULL;
        if (!g_spawn_async(NULL, argv, NULL, G_SPAWN_DEFAULT, NULL, NULL, NULL, &error)) {
            g_warning("Could not open folder: %s", error->message);
            g_error_free(error);
        }
    }
    return TRUE;
}

static void find_address(GtkWidget *widget, gpointer data)
{
    GtkWidget **result = data;
    if (*result) return;
    if (GTK_IS_ENTRY(widget)) {
        GtkWidget *combo = gtk_widget_get_ancestor(widget, GTK_TYPE_COMBO_BOX);
        if (combo && !g_strcmp0(gtk_buildable_get_name(GTK_BUILDABLE(combo)), "combo-address"))
            *result = widget;
    } else if (GTK_IS_CONTAINER(widget)) {
        gtk_container_foreach(GTK_CONTAINER(widget), find_address, data);
    }
}

static void launch_sharing(const gchar *path)
{
    g_autofree gchar *launcher = g_build_filename(g_get_user_data_dir(), "agentlinux-xp", "network-places.py", NULL);
    gchar *argv[] = {launcher, "--share", (gchar *)path, NULL};
    g_spawn_async(NULL, argv, NULL, G_SPAWN_DEFAULT, NULL, NULL, NULL, NULL);
}

static void share_address(GtkMenuItem *item, gchar *path)
{
    launch_sharing(path);
}

static gboolean open_network_address(GtkWidget *entry, GdkEventKey *event, gpointer data)
{
    if (event->keyval != GDK_KEY_Return && event->keyval != GDK_KEY_KP_Enter) return FALSE;
    g_autofree gchar *buffer = g_strdup(gtk_entry_get_text(GTK_ENTRY(entry)));
    gchar *text = g_strstrip(buffer);
    gsize length = strlen(text);
    if (length >= 2 && text[0] == '"' && text[length - 1] == '"') {
        text[length - 1] = '\0';
        text++;
    }
    if (!g_str_has_prefix(text, "\\\\") && g_ascii_strncasecmp(text, "smb://", 6)) return FALSE;
    g_autofree gchar *launcher = g_build_filename(g_get_user_data_dir(), "agentlinux-xp", "network-places.py", NULL);
    gchar *argv[] = {launcher, "--connect", (gchar *)text, NULL};
    g_autoptr(GError) error = NULL;
    if (!g_spawn_async(NULL, argv, NULL, G_SPAWN_DEFAULT, NULL, NULL, NULL, &error)) {
        GtkWidget *notice = gtk_message_dialog_new(GTK_WINDOW(gtk_widget_get_toplevel(entry)),
            GTK_DIALOG_DESTROY_WITH_PARENT, GTK_MESSAGE_ERROR, GTK_BUTTONS_CLOSE, "%s", error->message);
        gtk_dialog_run(GTK_DIALOG(notice));
        gtk_widget_destroy(notice);
    }
    return TRUE;
}

static void populate_address_menu(GtkEntry *entry, GtkWidget *menu, gpointer data)
{
    const gchar *text = gtk_entry_get_text(entry);
    g_autoptr(GFile) location = g_file_new_for_commandline_arg(text);
    g_autofree gchar *path = g_file_get_path(location);
    if ((!g_path_is_absolute(text) && !g_str_has_prefix(text, "file://")) ||
        !path || !g_file_test(path, G_FILE_TEST_IS_DIR)) return;
    gboolean chinese = g_str_has_prefix(g_get_language_names()[0], "zh");
    GtkWidget *item = gtk_menu_item_new_with_label(chinese ? "共享此文件夹…" : "Share this folder…");
    g_object_set_data_full(G_OBJECT(item), "xp-share-path", g_strdup(path), g_free);
    g_signal_connect(item, "activate", G_CALLBACK(share_address),
                     g_object_get_data(G_OBJECT(item), "xp-share-path"));
    gtk_menu_shell_append(GTK_MENU_SHELL(menu), item);
    gtk_widget_show(item);
}

static gboolean share_directory(GtkLinkButton *link, gpointer data)
{
    GtkWidget *address = NULL;
    find_address(gtk_widget_get_toplevel(GTK_WIDGET(link)), &address);
    const gchar *path = address ? gtk_entry_get_text(GTK_ENTRY(address)) : NULL;
    launch_sharing(path ? path : "");
    return TRUE;
}

static void enable_system_task(GtkWidget *label)
{
    if (g_strcmp0(gtk_buildable_get_name(GTK_BUILDABLE(label)), "label-item-label"))
        return;
    GtkWidget *link = gtk_widget_get_ancestor(label, GTK_TYPE_LINK_BUTTON);
    if (!link || gtk_widget_get_sensitive(link)) return;
    if (!g_strcmp0(gtk_label_get_text(GTK_LABEL(label)), "Share this folder")) {
        g_signal_connect(link, "activate-link", G_CALLBACK(share_directory), NULL);
        gtk_widget_set_sensitive(link, TRUE);
        return;
    }
    static const struct { const gchar *label; GUserDirectory directory; } places[] = {
        {"My Documents", G_USER_DIRECTORY_DOCUMENTS},
        {"Shared Documents", G_USER_DIRECTORY_PUBLIC_SHARE},
    };
    for (guint i = 0; i < G_N_ELEMENTS(places); i++) {
        if (g_strcmp0(gtk_label_get_text(GTK_LABEL(label)), places[i].label)) continue;
        const gchar *path = g_get_user_special_dir(places[i].directory);
        if (path && g_file_test(path, G_FILE_TEST_IS_DIR)) {
            g_signal_connect(link, "activate-link", G_CALLBACK(open_user_directory),
                             GINT_TO_POINTER(places[i].directory));
            gtk_widget_set_sensitive(link, TRUE);
        }
        return;
    }
    static const struct { const gchar *label, *desktop; } tasks[] = {
        {"My Network Places", "agentlinux-xp-places"},
        {"View system information", "agentlinux-xp-system"},
        {"Add or remove programs", "agentlinux-xp-programs"},
        {"Change a setting", "agentlinux-xp-control"},
        {"Control Panel", "agentlinux-xp-control"},
    };
    for (guint i = 0; i < G_N_ELEMENTS(tasks); i++) {
        if (!g_strcmp0(gtk_label_get_text(GTK_LABEL(label)), tasks[i].label)) {
            g_signal_connect(link, "activate-link", G_CALLBACK(open_system_task), (gpointer)tasks[i].desktop);
            gtk_widget_set_sensitive(link, TRUE);
            return;
        }
    }
}

static void open_explorer_setting(GtkMenuItem *item, gpointer data)
{
    const char *option = data;
    g_autofree char *script = g_build_filename(g_get_user_data_dir(), "agentlinux-xp",
        option ? "network-places.py" : "control-panel.py", NULL);
    char *args[] = {"/usr/bin/python3", script, option ? (char *)option : "--folder-options", NULL};
    g_autoptr(GError) error = NULL;
    if (!g_spawn_async(NULL, args, NULL, G_SPAWN_DEFAULT, NULL, NULL, NULL, &error))
        g_warning("%s", error->message);
}

static void show_agentlinux_about(GtkMenuItem *item, gpointer unused)
{
    GtkWidget *menu = gtk_widget_get_parent(GTK_WIDGET(item));
    GtkWidget *owner = gtk_menu_get_attach_widget(GTK_MENU(menu));
    GtkWidget *window = owner ? gtk_widget_get_toplevel(owner) : NULL;
    g_autofree char *emblem = g_build_filename(g_get_user_data_dir(), "agentlinux-xp", "college-emblem.png", NULL);
    g_autoptr(GdkPixbuf) logo = gdk_pixbuf_new_from_file_at_scale(emblem, 96, 96, TRUE, NULL);
    g_autofree char *release = g_get_os_info(G_OS_INFO_KEY_PRETTY_NAME);
    gtk_show_about_dialog(GTK_IS_WINDOW(window) ? GTK_WINDOW(window) : NULL,
        "program-name", "AgentLinux", "title", g_str_has_prefix(g_get_language_names()[0], "zh")
            ? "关于 AgentLinux" : "About AgentLinux", "logo", logo, "comments", release, NULL);
}

static gboolean on_map(GSignalInvocationHint *hint, guint count,
                       const GValue *values, gpointer data)
{
    GtkWidget *widget = g_value_get_object(values);
    if (GTK_IS_MENU_ITEM(widget)) {
        GtkWidget *menu = gtk_menu_item_get_submenu(GTK_MENU_ITEM(widget));
        if (GTK_IS_MENU(menu) && !g_object_get_data(G_OBJECT(menu), "xp-folder-options")) {
            g_autoptr(GList) children = gtk_container_get_children(GTK_CONTAINER(menu));
            for (GList *it = children; it; it = it->next) {
                if (!GTK_IS_MENU_ITEM(it->data)) continue;
                const char *label = gtk_menu_item_get_label(GTK_MENU_ITEM(it->data));
                if (!g_strcmp0(label, "About Windows") || !g_strcmp0(label, "关于 Windows")) {
                    gtk_actionable_set_action_name(GTK_ACTIONABLE(it->data), NULL);
                    gtk_widget_set_sensitive(it->data, TRUE);
                    gtk_menu_item_set_label(it->data, g_str_has_prefix(g_get_language_names()[0], "zh")
                        ? "关于 AgentLinux" : "About AgentLinux");
                    g_signal_connect(it->data, "activate", G_CALLBACK(show_agentlinux_about), NULL);
                    continue;
                }
                if (!g_strcmp0(gtk_menu_item_get_label(it->data), "Is this copy of Windows legal?") ||
                    !g_strcmp0(gtk_menu_item_get_label(it->data), "此 Windows 副本是否合法？")) {
                    gtk_widget_set_no_show_all(it->data, TRUE);
                    gtk_widget_hide(it->data);
                }
                if (!g_strcmp0(label, "Map Network Drive...") || !g_strcmp0(label, "映射网络驱动器…")) {
                    gtk_widget_set_sensitive(it->data, TRUE);
                    g_signal_connect(it->data, "activate", G_CALLBACK(open_explorer_setting), "--map-share");
                    continue;
                }
                if (!g_strcmp0(label, "Disconnect Network Drive...") || !g_strcmp0(label, "断开网络驱动器…")) {
                    gtk_widget_set_sensitive(it->data, TRUE);
                    g_signal_connect(it->data, "activate", G_CALLBACK(open_explorer_setting), "--connected");
                    continue;
                }
                if (g_strcmp0(label, "Folder Options...") && g_strcmp0(label, "文件夹选项…")) continue;
                g_signal_connect(it->data, "activate", G_CALLBACK(open_explorer_setting), NULL);
                GtkWidget *add = gtk_menu_item_new_with_label(g_str_has_prefix(g_get_language_names()[0], "zh")
                    ? "添加网络位置…" : "Add a Network Place…");
                gtk_menu_shell_append(GTK_MENU_SHELL(menu), add);
                g_signal_connect(add, "activate", G_CALLBACK(open_explorer_setting), "--add-place");
                gtk_widget_show(add);
                g_object_set_data(G_OBJECT(menu), "xp-folder-options", GINT_TO_POINTER(1));
                break;
            }
        }
    }
    if (GTK_IS_LABEL(widget)) enable_system_task(widget);
    if (GTK_IS_ENTRY(widget) && !g_object_get_data(G_OBJECT(widget), "xp-address-renderer")) {
        GtkWidget *combo = gtk_widget_get_ancestor(widget, GTK_TYPE_COMBO_BOX);
        if (combo && g_strcmp0(gtk_buildable_get_name(GTK_BUILDABLE(combo)), "combo-address") == 0) {
            g_signal_connect(widget, "key-press-event", G_CALLBACK(open_network_address), NULL);
            g_signal_connect(widget, "populate-popup", G_CALLBACK(populate_address_menu), NULL);
            if (g_str_has_prefix(g_get_language_names()[0], "zh"))
                g_signal_connect(widget, "draw", G_CALLBACK(draw_address), NULL);
            g_object_set_data(G_OBJECT(widget), "xp-address-renderer", GINT_TO_POINTER(1));
        }
    }
    if (!g_str_has_prefix(g_get_language_names()[0], "zh")) return TRUE;
    if (GTK_IS_LABEL(widget))
        translate_task_label(GTK_LABEL(widget));
    if (GTK_IS_TOOL_BUTTON(widget)) {
        GtkToolButton *button = GTK_TOOL_BUTTON(widget);
        for (guint i = 0; i < G_N_ELEMENTS(labels); i++) {
            if (g_strcmp0(gtk_tool_button_get_label(button), labels[i].english) == 0) {
                gtk_tool_button_set_label(button, labels[i].chinese);
                gtk_widget_set_tooltip_text(widget, labels[i].chinese);
                break;
            }
        }
    }
    return TRUE;
}

G_MODULE_EXPORT void gtk_module_init(gint *argc, gchar ***argv)
{
    gpointer klass = g_type_class_ref(GTK_TYPE_WIDGET);
    g_signal_add_emission_hook(g_signal_lookup("map", GTK_TYPE_WIDGET),
                               0, on_map, NULL, NULL);
    g_type_class_unref(klass);
}
