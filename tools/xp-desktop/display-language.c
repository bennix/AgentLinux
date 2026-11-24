#include <gtk/gtk.h>
#include <gtk/gtkx.h>
#include <gio/gdesktopappinfo.h>
#include <wintc/registry.h>
#include <string.h>
#include <stdio.h>

static const char *translation(const char *text)
{
    static const char *labels[][2] = {
        {"Display Properties","显示属性"}, {"Themes","主题"}, {"Desktop","桌面"},
        {"Screen Saver","屏幕保护程序"}, {"Appearance","外观"}, {"Settings","设置"},
        {"Save As","另存为"}, {"Delete","删除"}, {"Browse...","浏览…"},
        {"Center","居中"}, {"Tile","平铺"}, {"Stretch","拉伸"},
        {"Apply","应用"}, {"Cancel","取消"}, {"OK","确定"}, {"Theme:","主题："},
        {"Sample:","示例："}, {"Background:","背景："}, {"Position:","位置："},
        {"Color:","颜色："}, {"Screen saver","屏幕保护程序"}, {"Preview","预览"},
        {"Wait:","等待："}, {"minutes","分钟"}, {"Monitor power","显示器电源"},
        {"Power","电源"}, {"Display:","显示器："}, {"Screen resolution","屏幕分辨率"},
        {"Color quality","颜色质量"}, {"Less","低"}, {"More","高"}, {"Advanced","高级"},
        {"Effects...","效果…"}, {"Windows and buttons:","窗口和按钮："},
        {"Color scheme:","配色方案："}, {"Font size:","字号："},
        {"Customize Desktop...","自定义桌面…"}, {"Troubleshoot...","疑难解答…"},
        {"On resume, display Welcome screen","恢复时显示欢迎屏幕"},
        {"To adjust monitor power settings and save energy, click Power.","点击“电源”可调整显示器电源设置以节约能源。"},
        {"A theme is a background plus a set of sounds, icons, and other elements to help you personalize your computer with one click.","主题包括背景、声音、图标等元素，可一次更改桌面外观。"}
    };
    for (size_t i = 0; text && i < G_N_ELEMENTS(labels); i++)
        if (strcmp(text, labels[i][0]) == 0) return labels[i][1];
    return NULL;
}

static gboolean chinese;

static void update_preview(GSettings *settings, const char *key, GtkImage *image)
{
    g_autofree char *path = g_settings_get_string(settings, "picture-filename");
    g_autoptr(GdkPixbuf) pixbuf = gdk_pixbuf_new_from_file_at_scale(path, 320, 164, TRUE, NULL);
    gtk_image_set_from_pixbuf(image, pixbuf);
}

static const char *theme_fields[][2] = {
    {"org.mate.background", "picture-filename"}, {"org.mate.background", "picture-options"},
    {"org.mate.background", "primary-color"}, {"org.mate.background", "secondary-color"},
    {"org.mate.background", "color-shading-type"}, {"org.mate.interface", "font-name"},
    {"org.mate.interface", "icon-theme"}, {"org.mate.interface", "gtk-theme"}
};

static void remove_theme(GtkButton *button, gpointer data)
{
    const char *path = g_object_get_data(G_OBJECT(button), "theme-file");
    if (!path) return;
    GtkWindow *parent = GTK_WINDOW(gtk_widget_get_toplevel(GTK_WIDGET(button)));
    g_autofree char *name = g_filename_display_basename(path);
    GtkWidget *dialog = gtk_message_dialog_new(parent, GTK_DIALOG_MODAL, GTK_MESSAGE_QUESTION,
        GTK_BUTTONS_NONE, chinese ? "将主题文件“%s”移到回收站？" : "Move the theme file “%s” to the Trash?", name);
    gtk_dialog_add_buttons(GTK_DIALOG(dialog), chinese ? "取消" : "Cancel", GTK_RESPONSE_CANCEL,
        chinese ? "移到回收站" : "Move to Trash", GTK_RESPONSE_ACCEPT, NULL);
    gtk_dialog_set_default_response(GTK_DIALOG(dialog), GTK_RESPONSE_CANCEL);
    int response = gtk_dialog_run(GTK_DIALOG(dialog));
    gtk_widget_destroy(dialog);
    if (response != GTK_RESPONSE_ACCEPT) return;
    g_autoptr(GFile) file = g_file_new_for_path(path);
    g_autoptr(GError) error = NULL;
    if (!g_file_trash(file, NULL, &error)) {
        dialog = gtk_message_dialog_new(parent, GTK_DIALOG_MODAL, GTK_MESSAGE_ERROR,
            GTK_BUTTONS_CLOSE, "%s", error->message);
        gtk_dialog_run(GTK_DIALOG(dialog));
        gtk_widget_destroy(dialog);
        return;
    }
    gtk_widget_set_sensitive(GTK_WIDGET(button), FALSE);
    g_object_set_data(G_OBJECT(button), "theme-file", NULL);
}

static void theme_file(GtkButton *button, gpointer mode)
{
    gboolean save = GPOINTER_TO_INT(mode);
    GtkWindow *parent = GTK_WINDOW(gtk_widget_get_toplevel(GTK_WIDGET(button)));
    GtkWidget *dialog = gtk_file_chooser_dialog_new(
        save ? (chinese ? "保存桌面主题" : "Save desktop theme") :
               (chinese ? "打开桌面主题" : "Open desktop theme"),
        parent, save ? GTK_FILE_CHOOSER_ACTION_SAVE : GTK_FILE_CHOOSER_ACTION_OPEN,
        chinese ? "取消" : "Cancel", GTK_RESPONSE_CANCEL,
        save ? (chinese ? "保存" : "Save") : (chinese ? "打开" : "Open"), GTK_RESPONSE_ACCEPT, NULL);
    GtkFileChooser *chooser = GTK_FILE_CHOOSER(dialog);
    GtkFileFilter *filter = gtk_file_filter_new();
    gtk_file_filter_add_pattern(filter, "*.agenttheme");
    gtk_file_filter_set_name(filter, chinese ? "AgentLinux 桌面主题" : "AgentLinux desktop themes");
    gtk_file_chooser_add_filter(chooser, filter);
    if (save) {
        gtk_file_chooser_set_do_overwrite_confirmation(chooser, TRUE);
        gtk_file_chooser_set_current_name(chooser, chinese ? "我的主题.agenttheme" : "My Theme.agenttheme");
    }
    if (gtk_dialog_run(GTK_DIALOG(dialog)) == GTK_RESPONSE_ACCEPT) {
        g_autofree char *path = gtk_file_chooser_get_filename(chooser);
        g_autoptr(GKeyFile) file = g_key_file_new();
        g_autoptr(GError) error = NULL;
        g_auto(GStrv) values = g_new0(char *, G_N_ELEMENTS(theme_fields) + 1);
        if (!save) g_key_file_load_from_file(file, path, G_KEY_FILE_NONE, &error);
        for (guint i = 0; !error && i < G_N_ELEMENTS(theme_fields); i++) {
            const char *schema = theme_fields[i][0], *key = theme_fields[i][1];
            g_autoptr(GSettings) settings = g_settings_new(schema);
            if (save) {
                g_autofree char *value = g_settings_get_string(settings, key);
                g_key_file_set_string(file, schema, key, value);
            } else {
                values[i] = g_key_file_get_string(file, schema, key, &error);
                if (!error) {
                    GSettingsSchemaSource *source = g_settings_schema_source_get_default();
                    g_autoptr(GSettingsSchema) spec = g_settings_schema_source_lookup(source, schema, TRUE);
                    g_autoptr(GSettingsSchemaKey) field = g_settings_schema_get_key(spec, key);
                    g_autoptr(GVariant) value = g_variant_ref_sink(g_variant_new_string(values[i]));
                    if (!g_settings_schema_key_range_check(field, value) || !g_settings_is_writable(settings, key))
                        g_set_error_literal(&error, G_IO_ERROR, G_IO_ERROR_INVALID_DATA, key);
                }
            }
        }
        if (save) g_key_file_save_to_file(file, path, &error);
        else if (!error) {
            for (guint i = 0; i < G_N_ELEMENTS(theme_fields); i++) {
                g_autoptr(GSettings) settings = g_settings_new(theme_fields[i][0]);
                g_settings_set_string(settings, theme_fields[i][1], values[i]);
            }
            g_settings_sync();
        }
        GtkWidget *remove = g_object_get_data(G_OBJECT(button), "remove-theme");
        if (!error && remove) {
            gboolean managed = g_str_has_suffix(path, ".agenttheme");
            g_object_set_data_full(G_OBJECT(remove), "theme-file", managed ? g_strdup(path) : NULL, g_free);
            gtk_widget_set_sensitive(remove, managed);
            gtk_widget_set_tooltip_text(remove, managed ? path : NULL);
        }
        if (error) {
            GtkWidget *message = gtk_message_dialog_new(GTK_WINDOW(dialog), GTK_DIALOG_MODAL,
                GTK_MESSAGE_ERROR, GTK_BUTTONS_CLOSE, "%s", error->message);
            gtk_dialog_run(GTK_DIALOG(message));
            gtk_widget_destroy(message);
        }
    }
    gtk_widget_destroy(dialog);
}

static void show_current_theme(GtkWidget *widget, gpointer data)
{
    if (!GTK_IS_COMBO_BOX(widget)) {
        if (GTK_IS_CONTAINER(widget))
            gtk_container_foreach(GTK_CONTAINER(widget), show_current_theme, data);
        return;
    }
    GtkComboBox *combo = GTK_COMBO_BOX(widget);
    if (gtk_combo_box_get_model(combo)) return;
    const char *theme = g_getenv("GTK_THEME");
    g_autofree char *configured = NULL;
    if (!theme || !*theme) {
        g_object_get(gtk_widget_get_settings(widget), "gtk-theme-name", &configured, NULL);
        theme = configured;
    }
    if (!theme || !*theme) return;
    GtkListStore *store = gtk_list_store_new(1, G_TYPE_STRING);
    GtkTreeIter current;
    gtk_list_store_insert_with_values(store, &current, -1, 0, theme, -1);
    gtk_combo_box_set_model(combo, GTK_TREE_MODEL(store));
    GtkCellRenderer *caption = gtk_cell_renderer_text_new();
    gtk_cell_layout_pack_start(GTK_CELL_LAYOUT(combo), caption, TRUE);
    gtk_cell_layout_add_attribute(GTK_CELL_LAYOUT(combo), caption, "text", 0);
    gtk_combo_box_set_active_iter(combo, &current);
    gtk_widget_show(widget);
    GtkWidget *row = gtk_widget_get_parent(widget);
    g_autoptr(GList) children = gtk_container_get_children(GTK_CONTAINER(row));
    GtkWidget *buttons = g_list_nth_data(children, 1);
    if (GTK_IS_BOX(buttons)) {
        g_autoptr(GList) actions = gtk_container_get_children(GTK_CONTAINER(buttons));
        GtkWidget *save = g_list_nth_data(actions, 0);
        if (GTK_IS_BUTTON(save)) {
            gtk_widget_set_sensitive(save, TRUE);
            g_signal_connect(save, "clicked", G_CALLBACK(theme_file), GINT_TO_POINTER(1));
        }
        GtkWidget *open = gtk_button_new_with_label(chinese ? "打开…" : "Open…");
        gtk_box_pack_start(GTK_BOX(buttons), open, FALSE, FALSE, 0);
        g_signal_connect(open, "clicked", G_CALLBACK(theme_file), NULL);
        GtkWidget *remove = g_list_nth_data(actions, 1);
        if (GTK_IS_BUTTON(remove) && GTK_IS_BUTTON(save)) {
            gtk_widget_set_sensitive(remove, FALSE);
            g_signal_connect(remove, "clicked", G_CALLBACK(remove_theme), NULL);
            g_object_set_data(G_OBJECT(save), "remove-theme", remove);
            g_object_set_data(G_OBJECT(open), "remove-theme", remove);
        }
        gtk_widget_show(open);
    }
    g_object_unref(store);
}

static gboolean add_preview(gpointer data)
{
    GtkWidget *box = gtk_widget_get_parent(GTK_WIDGET(data));
    if (!GTK_IS_BOX(box) || g_object_get_data(G_OBJECT(box), "agentlinux-preview"))
        return G_SOURCE_REMOVE;
    gtk_container_foreach(GTK_CONTAINER(box), show_current_theme, NULL);
    GtkWidget *image = gtk_image_new();
    GSettings *settings = g_settings_new("org.mate.background");
    gtk_box_pack_start(GTK_BOX(box), image, TRUE, TRUE, 0);
    g_object_set_data(G_OBJECT(box), "agentlinux-preview", image);
    g_object_set_data_full(G_OBJECT(image), "background-settings", settings, g_object_unref);
    g_signal_connect_object(settings, "changed::picture-filename", G_CALLBACK(update_preview), image, 0);
    update_preview(settings, NULL, GTK_IMAGE(image));
    gtk_widget_show(image);
    return G_SOURCE_REMOVE;
}

static void style_caption(GtkCellLayout *layout, GtkCellRenderer *cell, GtkTreeModel *model,
                          GtkTreeIter *iter, gpointer data)
{
    g_autofree char *name = NULL;
    gtk_tree_model_get(model, iter, 1, &name, -1);
    const char *localized = translation(name);
    g_object_set(cell, "text", localized ? localized : name, NULL);
}

static const char *wallpaper_styles[] = {"centered", "wallpaper", "stretched"};

static void wallpaper_changed(GtkWidget *widget, gpointer window)
{
    g_object_set_data(window, "agentlinux-position", GINT_TO_POINTER(gtk_combo_box_get_active(GTK_COMBO_BOX(widget)) + 1));
}

static void row_changed(GtkListBox *box, GtkListBoxRow *row, gpointer window)
{
    if (row) g_object_set_data(window, "agentlinux-wallpaper-edited", GINT_TO_POINTER(1));
}

static void apply_wallpaper(GSimpleAction *action, GVariant *parameter, gpointer window)
{
    gboolean edited = g_object_steal_data(window, "agentlinux-wallpaper-edited") != NULL;
    int position = GPOINTER_TO_INT(g_object_steal_data(window, "agentlinux-position")) - 1;
    if (!edited && position < 0) return;
    g_autoptr(GSettings) background = g_settings_new("org.mate.background");
    if (edited) {
        WinTCRegistry *registry = wintc_registry_new();
        g_autofree char *path = NULL;
        if (wintc_registry_get_key_value(registry, "HKCU\\Control Panel\\Desktop", "Wallpaper",
                                         WINTC_REG_SZ, &path, NULL) && path && g_file_test(path, G_FILE_TEST_IS_REGULAR))
            g_settings_set_string(background, "picture-filename", path);
        g_object_unref(registry);
    }
    if (position >= 0 && (guint) position < G_N_ELEMENTS(wallpaper_styles))
        g_settings_set_string(background, "picture-options", wallpaper_styles[position]);
    g_settings_sync();
}

static void troubleshoot_display(GtkButton *button, gpointer data)
{
    GtkWindow *parent = GTK_WINDOW(gtk_widget_get_toplevel(GTK_WIDGET(button)));
    GtkWidget *dialog = gtk_dialog_new_with_buttons(chinese ? "显示疑难解答" : "Display troubleshooting",
        parent, GTK_DIALOG_MODAL | GTK_DIALOG_DESTROY_WITH_PARENT,
        chinese ? "关闭" : "Close", GTK_RESPONSE_CLOSE, NULL);
    GtkWidget *box = gtk_dialog_get_content_area(GTK_DIALOG(dialog));
    gtk_container_set_border_width(GTK_CONTAINER(box), 10);
    gtk_box_set_spacing(GTK_BOX(box), 8);
    GtkWidget *help = gtk_label_new(chinese ?
        "星号 (*) 表示当前刷新率，加号 (+) 表示首选模式。可在“高级”中调整显示设置。" :
        "An asterisk (*) marks the active refresh rate. A plus (+) marks the preferred mode. Use Advanced to change display settings.");
    gtk_label_set_line_wrap(GTK_LABEL(help), TRUE);
    gtk_box_pack_start(GTK_BOX(box), help, FALSE, FALSE, 0);
    GtkWidget *scroll = gtk_scrolled_window_new(NULL, NULL);
    GtkWidget *report = gtk_text_view_new();
    gtk_text_view_set_editable(GTK_TEXT_VIEW(report), FALSE);
    gtk_text_view_set_monospace(GTK_TEXT_VIEW(report), TRUE);
    gtk_container_add(GTK_CONTAINER(scroll), report);
    gtk_box_pack_start(GTK_BOX(box), scroll, TRUE, TRUE, 0);
    g_autoptr(GError) error = NULL;
    g_autoptr(GSubprocess) command = g_subprocess_new(G_SUBPROCESS_FLAGS_STDOUT_PIPE |
        G_SUBPROCESS_FLAGS_STDERR_MERGE, &error, "/usr/bin/xrandr", "--current", NULL);
    g_autofree char *output = NULL;
    if (command) g_subprocess_communicate_utf8(command, NULL, NULL, &output, NULL, &error);
    gtk_text_buffer_set_text(gtk_text_view_get_buffer(GTK_TEXT_VIEW(report)),
                             error ? error->message : output, -1);
    gtk_window_set_default_size(GTK_WINDOW(dialog), 550, 330);
    gtk_widget_show_all(dialog);
    gtk_dialog_run(GTK_DIALOG(dialog));
    gtk_widget_destroy(dialog);
}

static void open_settings_app(GtkButton *button, GDesktopAppInfo *app)
{
    g_autoptr(GError) error = NULL;
    if (g_app_info_launch(G_APP_INFO(app), NULL, NULL, &error)) return;
    GtkWidget *notice = gtk_message_dialog_new(GTK_WINDOW(gtk_widget_get_toplevel(GTK_WIDGET(button))),
        GTK_DIALOG_MODAL | GTK_DIALOG_DESTROY_WITH_PARENT, GTK_MESSAGE_ERROR, GTK_BUTTONS_CLOSE,
        "%s", error->message);
    gtk_dialog_run(GTK_DIALOG(notice));
    gtk_widget_destroy(notice);
}

static const char *screensaver_program = "/usr/lib/ukui-screensaver/ukui-screensaver-default";

static void preview_screensaver(GtkButton *button, gpointer data)
{
    GtkWidget *parent = gtk_widget_get_toplevel(GTK_WIDGET(button));
    GtkWidget *dialog = gtk_dialog_new_with_buttons(chinese ? "屏幕保护程序预览" : "Screen Saver Preview",
        GTK_WINDOW(parent), GTK_DIALOG_MODAL | GTK_DIALOG_DESTROY_WITH_PARENT,
        chinese ? "关闭" : "Close", GTK_RESPONSE_CLOSE, NULL);
    GtkWidget *close = gtk_dialog_get_widget_for_response(GTK_DIALOG(dialog), GTK_RESPONSE_CLOSE);
    g_autoptr(GtkAccelGroup) shortcuts = gtk_accel_group_new();
    gtk_window_add_accel_group(GTK_WINDOW(dialog), shortcuts);
    gtk_widget_add_accelerator(close, "clicked", shortcuts, GDK_KEY_Escape, 0, GTK_ACCEL_VISIBLE);
    GtkWidget *socket = gtk_socket_new();
    gtk_widget_set_can_focus(socket, FALSE);
    gtk_window_set_focus(GTK_WINDOW(dialog), close);
    gtk_window_set_default_size(GTK_WINDOW(dialog), 600, 390);
    gtk_box_pack_start(GTK_BOX(gtk_dialog_get_content_area(GTK_DIALOG(dialog))), socket, TRUE, TRUE, 0);
    gtk_widget_show_all(dialog);
    g_autofree char *id = g_strdup_printf("%lu", (unsigned long)gtk_socket_get_id(GTK_SOCKET(socket)));
    g_autoptr(GError) error = NULL;
    g_autoptr(GSubprocess) child = g_subprocess_new(G_SUBPROCESS_FLAGS_NONE, &error, screensaver_program,
                                                    "--window-id", id, NULL);
    if (!child) {
        GtkWidget *message = gtk_label_new(error->message);
        gtk_box_pack_start(GTK_BOX(gtk_dialog_get_content_area(GTK_DIALOG(dialog))), message, FALSE, FALSE, 0);
        gtk_widget_show(message);
    }
    gtk_dialog_run(GTK_DIALOG(dialog));
    if (child) {
        g_subprocess_force_exit(child);
        g_subprocess_wait(child, NULL, NULL);
    }
    gtk_widget_destroy(dialog);
}

static void stage_wait(GtkSpinButton *spin, GSettings *settings)
{
    g_settings_set_int(settings, "idle-delay", gtk_spin_button_get_value_as_int(spin));
}

static void release_saver(gpointer settings, GClosure *closure)
{
    g_object_unref(settings);
}

static void commit_saver(GSimpleAction *action, GVariant *parameter, GSettings *settings)
{
    const char *chosen = g_object_get_data(G_OBJECT(settings), "chosen-background");
    if (chosen) {
        g_autoptr(GError) error = NULL;
        g_autofree char *folder = g_build_filename(g_get_user_data_dir(), "agentlinux-xp",
                                                    "selected-saver-background", NULL);
        g_autofree char *path = g_build_filename(folder, "background.png", NULL);
        g_autoptr(GdkPixbuf) image = gdk_pixbuf_new_from_file_at_scale(chosen, 2560, 2560, TRUE, &error);
        g_autofree char *png = NULL;
        gsize size = 0;
        if (image && g_mkdir_with_parents(folder, 0700) < 0)
            g_set_error_literal(&error, G_FILE_ERROR, G_FILE_ERROR_FAILED, g_strerror(errno));
        if (!error && gdk_pixbuf_save_to_buffer(image, &png, &size, "png", &error, NULL))
            g_file_set_contents(path, png, size, &error);
        if (!error) {
            g_autoptr(GSettings) renderer = g_settings_new("org.ukui.screensaver-default");
            if (!g_settings_set_string(renderer, "background-path", folder))
                g_set_error_literal(&error, G_IO_ERROR, G_IO_ERROR_PERMISSION_DENIED,
                                    chinese ? "无法保存屏保背景目录" : "Cannot save screen saver background folder");
        }
        if (error) {
            GtkWidget *notice = gtk_message_dialog_new(NULL, GTK_DIALOG_MODAL, GTK_MESSAGE_ERROR,
                                                       GTK_BUTTONS_CLOSE, "%s", error->message);
            gtk_dialog_run(GTK_DIALOG(notice));
            gtk_widget_destroy(notice);
        } else {
            g_settings_set_string(settings, "background", chosen);
            g_object_set_data(G_OBJECT(settings), "chosen-background", NULL);
        }
    }
    g_settings_apply(settings);
    g_settings_sync();
}

static GSettings *saver_settings(GtkWidget *window)
{
    GSettings *settings = g_object_get_data(G_OBJECT(window), "agentlinux-saver");
    if (settings) return settings;
    settings = g_settings_new("org.ukui.screensaver");
    g_settings_delay(settings);
    g_object_set_data_full(G_OBJECT(window), "agentlinux-saver", settings, g_object_unref);
    const char *names[] = {"apply", "ok"};
    for (size_t i = 0; i < G_N_ELEMENTS(names); i++) {
        GAction *action = g_action_map_lookup_action(G_ACTION_MAP(window), names[i]);
        if (action) g_signal_connect_data(action, "activate", G_CALLBACK(commit_saver),
            g_object_ref(settings), release_saver, 0);
    }
    return settings;
}

static void apply_effects(GSimpleAction *action, GVariant *parameter, GSettings *settings)
{
    g_settings_apply(settings);
    g_settings_sync();
}

static GSettings *page_settings(GtkWidget *window, const char *schema)
{
    GSettings *settings = g_object_get_data(G_OBJECT(window), schema);
    if (!settings) {
        settings = g_settings_new(schema);
        g_settings_delay(settings);
        g_object_set_data_full(G_OBJECT(window), schema, settings, g_object_unref);
        const char *names[] = {"apply", "ok"};
        for (guint i = 0; i < G_N_ELEMENTS(names); i++) {
            GAction *action = g_action_map_lookup_action(G_ACTION_MAP(window), names[i]);
            if (action) g_signal_connect_data(action, "activate", G_CALLBACK(apply_effects),
                                              g_object_ref(settings), release_saver, 0);
        }
    }
    return settings;
}

static const struct { const char *id, *en, *zh; } desktop_items[] = {
    {"agentlinux-xp-explorer", "Windows Explorer", "资源管理器"},
    {"agentlinux-xp-control", "Control Panel", "控制面板"},
    {"agentlinux-xp-places", "My Network Places", "网上邻居"},
    {"agentlinux-xp-wifi", "Wireless Network", "无线网络"}
};

static const struct { const char *marker, *en, *zh; } standard_icons[] = {
    {"computer.hidden", "My Computer", "我的电脑"},
    {"home.hidden", "Home Folder", "主目录"},
    {"trash.hidden", "Recycle Bin", "回收站"}
};

static gchar *standard_icon_marker(guint index)
{
    return g_build_filename(g_get_user_config_dir(), "agentlinux-xp", "desktop-icons",
                            standard_icons[index].marker, NULL);
}

static gchar *shortcut_path(guint index, gboolean hidden)
{
    g_autofree char *name = g_strdup_printf("%s.desktop", desktop_items[index].id);
    if (hidden)
        return g_build_filename(g_get_user_config_dir(), "agentlinux-xp", "hidden-shortcuts", name, NULL);
    return g_build_filename(g_get_user_special_dir(G_USER_DIRECTORY_DESKTOP), name, NULL);
}

static gchar *stored_shortcut(guint index)
{
    gchar *path = shortcut_path(index, TRUE);
    if (g_file_test(path, G_FILE_TEST_EXISTS)) return path;
    g_autofree char *name = g_strdup_printf(".%s.desktop", desktop_items[index].id);
    gchar *legacy = g_build_filename(g_get_user_special_dir(G_USER_DIRECTORY_DESKTOP), name, NULL);
    if (g_file_test(legacy, G_FILE_TEST_EXISTS)) {
        g_free(path);
        return legacy;
    }
    g_free(legacy);
    return path;
}

static void apply_desktop_items(GSimpleAction *action, GVariant *parameter, GHashTable *changes)
{
    GHashTableIter iter;
    gpointer key, value;
    g_hash_table_iter_init(&iter, changes);
    while (g_hash_table_iter_next(&iter, &key, &value)) {
        guint index = GPOINTER_TO_UINT(key);
        gboolean visible = GPOINTER_TO_INT(value);
        if (index >= G_N_ELEMENTS(desktop_items)) {
            g_autofree char *marker = standard_icon_marker(index - G_N_ELEMENTS(desktop_items));
            g_autoptr(GFile) file = g_file_new_for_path(marker);
            g_autoptr(GError) error = NULL;
            if (visible) {
                if (!g_file_delete(file, NULL, &error) && g_error_matches(error, G_IO_ERROR, G_IO_ERROR_NOT_FOUND))
                    g_clear_error(&error);
            } else {
                g_autofree char *dir = g_path_get_dirname(marker);
                if (g_mkdir_with_parents(dir, 0700) < 0)
                    g_set_error_literal(&error, G_FILE_ERROR, g_file_error_from_errno(errno), g_strerror(errno));
                else
                    g_file_set_contents(marker, "", 0, &error);
            }
            if (error) {
                GtkWidget *notice = gtk_message_dialog_new(NULL, GTK_DIALOG_MODAL, GTK_MESSAGE_ERROR,
                    GTK_BUTTONS_CLOSE, "%s", error->message);
                gtk_dialog_run(GTK_DIALOG(notice));
                gtk_widget_destroy(notice);
            } else g_hash_table_iter_remove(&iter);
            continue;
        }
        g_autofree char *from = visible ? stored_shortcut(index) : shortcut_path(index, FALSE);
        g_autofree char *to = shortcut_path(index, !visible);
        g_autoptr(GFile) src = g_file_new_for_path(from);
        g_autoptr(GFile) dest = g_file_new_for_path(to);
        if (g_file_query_exists(src, NULL)) {
            g_autoptr(GError) error = NULL;
            g_autofree char *parent = g_path_get_dirname(to);
            if (g_mkdir_with_parents(parent, 0700) < 0)
                g_set_error_literal(&error, G_FILE_ERROR, g_file_error_from_errno(errno), g_strerror(errno));
            if (error || !g_file_move(src, dest, G_FILE_COPY_NONE, NULL, NULL, NULL, &error)) {
                GtkWidget *notice = gtk_message_dialog_new(NULL, GTK_DIALOG_MODAL, GTK_MESSAGE_ERROR,
                                                           GTK_BUTTONS_CLOSE, "%s", error->message);
                gtk_dialog_run(GTK_DIALOG(notice));
                gtk_widget_destroy(notice);
                continue;
            }
        }
        g_hash_table_iter_remove(&iter);
    }
}

static void customize_desktop(GtkButton *button, gpointer unused)
{
    GtkWidget *window = gtk_widget_get_toplevel(GTK_WIDGET(button));
    GHashTable *changes = g_object_get_data(G_OBJECT(window), "xp-shortcut-changes");
    if (!changes) {
        changes = g_hash_table_new(g_direct_hash, g_direct_equal);
        g_object_set_data_full(G_OBJECT(window), "xp-shortcut-changes", changes, (GDestroyNotify)g_hash_table_unref);
        const char *names[] = {"apply", "ok"};
        for (guint i = 0; i < G_N_ELEMENTS(names); i++) {
            GAction *action = g_action_map_lookup_action(G_ACTION_MAP(window), names[i]);
            if (action) g_signal_connect(action, "activate", G_CALLBACK(apply_desktop_items), changes);
        }
    }
    GtkWidget *dialog = gtk_dialog_new_with_buttons(chinese ? "桌面快捷方式" : "Desktop Shortcuts",
        GTK_WINDOW(window), GTK_DIALOG_MODAL | GTK_DIALOG_DESTROY_WITH_PARENT,
        chinese ? "取消" : "Cancel", GTK_RESPONSE_CANCEL, chinese ? "确定" : "OK", GTK_RESPONSE_OK, NULL);
    GtkWidget *box = gtk_dialog_get_content_area(GTK_DIALOG(dialog));
    gtk_container_set_border_width(GTK_CONTAINER(box), 12);
    GtkWidget *checks[G_N_ELEMENTS(desktop_items)];
    for (guint i = 0; i < G_N_ELEMENTS(desktop_items); i++) {
        g_autofree char *shown = shortcut_path(i, FALSE);
        g_autofree char *hidden = stored_shortcut(i);
        gboolean exists = g_file_test(shown, G_FILE_TEST_EXISTS);
        gpointer pending;
        gboolean staged = g_hash_table_lookup_extended(changes, GUINT_TO_POINTER(i), NULL, &pending);
        checks[i] = gtk_check_button_new_with_label(chinese ? desktop_items[i].zh : desktop_items[i].en);
        gtk_toggle_button_set_active(GTK_TOGGLE_BUTTON(checks[i]), staged ? GPOINTER_TO_INT(pending) : exists);
        gtk_widget_set_sensitive(checks[i], exists || g_file_test(hidden, G_FILE_TEST_EXISTS));
        gtk_container_add(GTK_CONTAINER(box), checks[i]);
    }
    GtkWidget *standard[G_N_ELEMENTS(standard_icons)];
    for (guint i = 0; i < G_N_ELEMENTS(standard_icons); i++) {
        g_autofree char *marker = standard_icon_marker(i);
        gpointer pending;
        gpointer key = GUINT_TO_POINTER(G_N_ELEMENTS(desktop_items) + i);
        gboolean staged = g_hash_table_lookup_extended(changes, key, NULL, &pending);
        standard[i] = gtk_check_button_new_with_label(chinese ? standard_icons[i].zh : standard_icons[i].en);
        gtk_toggle_button_set_active(GTK_TOGGLE_BUTTON(standard[i]),
            staged ? GPOINTER_TO_INT(pending) : !g_file_test(marker, G_FILE_TEST_EXISTS));
        gtk_container_add(GTK_CONTAINER(box), standard[i]);
    }
    gtk_widget_show_all(dialog);
    if (gtk_dialog_run(GTK_DIALOG(dialog)) == GTK_RESPONSE_OK) {
        for (guint i = 0; i < G_N_ELEMENTS(standard_icons); i++) {
            gpointer key = GUINT_TO_POINTER(G_N_ELEMENTS(desktop_items) + i);
            g_autofree char *marker = standard_icon_marker(i);
            gboolean active = gtk_toggle_button_get_active(GTK_TOGGLE_BUTTON(standard[i]));
            if (active == !g_file_test(marker, G_FILE_TEST_EXISTS)) g_hash_table_remove(changes, key);
            else g_hash_table_insert(changes, key, GINT_TO_POINTER(active));
        }
        for (guint i = 0; i < G_N_ELEMENTS(desktop_items); i++) {
            g_autofree char *shown = shortcut_path(i, FALSE);
            gboolean active = gtk_toggle_button_get_active(GTK_TOGGLE_BUTTON(checks[i]));
            if (active == g_file_test(shown, G_FILE_TEST_EXISTS))
                g_hash_table_remove(changes, GUINT_TO_POINTER(i));
            else
                g_hash_table_insert(changes, GUINT_TO_POINTER(i), GINT_TO_POINTER(active));
        }
        GAction *apply = g_action_map_lookup_action(G_ACTION_MAP(window), "apply");
        if (g_hash_table_size(changes) && G_IS_SIMPLE_ACTION(apply))
            g_simple_action_set_enabled(G_SIMPLE_ACTION(apply), TRUE);
    }
    gtk_widget_destroy(dialog);
}

static void edit_effects(GtkButton *button, gpointer data)
{
    GtkWidget *window = gtk_widget_get_toplevel(GTK_WIDGET(button));
    GSettings *settings = page_settings(window, "org.mate.interface");
    GtkWidget *dialog = gtk_dialog_new_with_buttons(chinese ? "效果" : "Effects", GTK_WINDOW(window),
        GTK_DIALOG_MODAL | GTK_DIALOG_DESTROY_WITH_PARENT, chinese ? "取消" : "Cancel", GTK_RESPONSE_CANCEL,
        chinese ? "确定" : "OK", GTK_RESPONSE_OK, NULL);
    GtkWidget *check = gtk_check_button_new_with_label(chinese ? "启用界面动画" : "Enable interface animations");
    gtk_toggle_button_set_active(GTK_TOGGLE_BUTTON(check), g_settings_get_boolean(settings, "gtk-enable-animations"));
    gtk_widget_set_sensitive(check, g_settings_is_writable(settings, "gtk-enable-animations"));
    GtkWidget *content = gtk_dialog_get_content_area(GTK_DIALOG(dialog));
    gtk_container_set_border_width(GTK_CONTAINER(content), 12);
    gtk_container_add(GTK_CONTAINER(content), check);
    gtk_widget_show_all(dialog);
    if (gtk_dialog_run(GTK_DIALOG(dialog)) == GTK_RESPONSE_OK)
        g_settings_set_boolean(settings, "gtk-enable-animations", gtk_toggle_button_get_active(GTK_TOGGLE_BUTTON(check)));
    gtk_widget_destroy(dialog);
}

static void choose_saver_background(GtkButton *button, GSettings *settings)
{
    GtkWindow *parent = GTK_WINDOW(gtk_widget_get_toplevel(GTK_WIDGET(button)));
    GtkWidget *dialog = gtk_file_chooser_dialog_new(chinese ? "屏保背景" : "Screen saver background",
        parent, GTK_FILE_CHOOSER_ACTION_OPEN, chinese ? "取消" : "Cancel", GTK_RESPONSE_CANCEL,
        chinese ? "选择" : "Select", GTK_RESPONSE_ACCEPT, NULL);
    GtkFileChooser *chooser = GTK_FILE_CHOOSER(dialog);
    GtkFileFilter *images = gtk_file_filter_new();
    gtk_file_filter_set_name(images, chinese ? "图片" : "Images");
    gtk_file_filter_add_pixbuf_formats(images);
    gtk_file_chooser_add_filter(chooser, images);
    g_autofree char *current = g_settings_get_string(settings, "background");
    const char *pending = g_object_get_data(G_OBJECT(settings), "chosen-background");
    if (g_file_test(pending ? pending : current, G_FILE_TEST_IS_REGULAR))
        gtk_file_chooser_set_filename(chooser, pending ? pending : current);
    if (gtk_dialog_run(GTK_DIALOG(dialog)) == GTK_RESPONSE_ACCEPT) {
        g_autofree char *filename = gtk_file_chooser_get_filename(chooser);
        if (filename) g_object_set_data_full(G_OBJECT(settings), "chosen-background", g_strdup(filename), g_free);
    }
    gtk_widget_destroy(dialog);
}

static void stage_saver_choice(GtkComboBox *combo, GSettings *settings)
{
    g_settings_set_boolean(settings, "idle-activation-enabled", gtk_combo_box_get_active(combo) == 1);
}

static void setup_saver_choice(GtkComboBox *combo, GSettings *settings)
{
    g_autoptr(GtkListStore) choices = gtk_list_store_new(1, G_TYPE_STRING);
    gtk_list_store_insert_with_values(choices, NULL, -1, 0, chinese ? "（无）" : "(None)", -1);
    gtk_list_store_insert_with_values(choices, NULL, -1, 0,
        chinese ? "当前系统屏幕保护程序" : "Current system screen saver", -1);
    gtk_combo_box_set_model(combo, GTK_TREE_MODEL(choices));
    GtkCellRenderer *caption = gtk_cell_renderer_text_new();
    gtk_cell_layout_pack_start(GTK_CELL_LAYOUT(combo), caption, TRUE);
    gtk_cell_layout_add_attribute(GTK_CELL_LAYOUT(combo), caption, "text", 0);
    gtk_combo_box_set_active(combo, g_settings_get_boolean(settings, "idle-activation-enabled") ? 1 : 0);
    g_settings_bind_writable(settings, "idle-activation-enabled", combo, "sensitive", FALSE);
    g_signal_connect_object(combo, "changed", G_CALLBACK(stage_saver_choice), settings, 0);
}

static void show_current_value(GtkComboBox *combo, const char *text)
{
    g_autoptr(GtkListStore) model = gtk_list_store_new(1, G_TYPE_STRING);
    gtk_list_store_insert_with_values(model, NULL, -1, 0, text, -1);
    gtk_combo_box_set_model(combo, GTK_TREE_MODEL(model));
    GtkCellRenderer *caption = gtk_cell_renderer_text_new();
    gtk_cell_layout_pack_start(GTK_CELL_LAYOUT(combo), caption, TRUE);
    gtk_cell_layout_add_attribute(GTK_CELL_LAYOUT(combo), caption, "text", 0);
    gtk_combo_box_set_active(combo, 0);
    gtk_widget_set_sensitive(GTK_WIDGET(combo), FALSE);
}

static void show_color_depth(GtkComboBox *combo)
{
    GdkScreen *screen = gtk_widget_get_screen(GTK_WIDGET(combo));
    int bits = gdk_visual_get_depth(gdk_screen_get_system_visual(screen));
    g_autofree char *text = g_strdup_printf(chinese ? "%d 位" : "%d-bit", bits);
    show_current_value(combo, text);
}

static void change_font_size(GtkComboBox *combo, GSettings *settings)
{
    GtkTreeIter iter;
    if (!gtk_combo_box_get_active_iter(combo, &iter)) return;
    int points;
    gtk_tree_model_get(gtk_combo_box_get_model(combo), &iter, 1, &points, -1);
    if (!points) {
        g_settings_set_string(settings, "font-name", g_object_get_data(G_OBJECT(combo), "xp-original-font"));
        return;
    }
    g_autofree char *name = g_settings_get_string(settings, "font-name");
    g_autoptr(PangoFontDescription) font = pango_font_description_from_string(name);
    pango_font_description_set_size(font, points * PANGO_SCALE);
    g_autofree char *updated = pango_font_description_to_string(font);
    g_settings_set_string(settings, "font-name", updated);
}

static void show_font_sizes(GtkComboBox *combo, GSettings *settings)
{
    g_autofree char *name = g_settings_get_string(settings, "font-name");
    g_autoptr(PangoFontDescription) font = pango_font_description_from_string(name);
    g_autoptr(GtkListStore) model = gtk_list_store_new(2, G_TYPE_STRING, G_TYPE_INT);
    const int sizes[] = {9, 10, 11, 12, 14, 16, 18, 20, 24};
    int active = -1;
    for (guint i = 0; i < G_N_ELEMENTS(sizes); i++) {
        g_autofree char *label = g_strdup_printf("%d pt", sizes[i]);
        gtk_list_store_insert_with_values(model, NULL, -1, 0, label, 1, sizes[i], -1);
        if (!pango_font_description_get_size_is_absolute(font) &&
            pango_font_description_get_size(font) == sizes[i] * PANGO_SCALE) active = i;
    }
    if (active < 0) {
        active = 0;
        g_object_set_data_full(G_OBJECT(combo), "xp-original-font", g_strdup(name), g_free);
        gtk_list_store_insert_with_values(model, NULL, 0, 0, name, 1, 0, -1);
    }
    gtk_combo_box_set_model(combo, GTK_TREE_MODEL(model));
    GtkCellRenderer *cell = gtk_cell_renderer_text_new();
    gtk_cell_layout_pack_start(GTK_CELL_LAYOUT(combo), cell, TRUE);
    gtk_cell_layout_add_attribute(GTK_CELL_LAYOUT(combo), cell, "text", 0);
    gtk_combo_box_set_active(combo, active);
    g_settings_bind_writable(settings, "font-name", combo, "sensitive", FALSE);
    g_signal_connect_object(combo, "changed", G_CALLBACK(change_font_size), settings, 0);
}

static void show_appearance_value(GtkComboBox *combo)
{
    GtkWidget *widget = GTK_WIDGET(combo);
    GList *children = gtk_container_get_children(GTK_CONTAINER(gtk_widget_get_parent(widget)));
    int field = 0;
    for (GList *item = children; item && item->data != widget; item = item->next)
        if (GTK_IS_COMBO_BOX(item->data)) field++;
    g_list_free(children);
    if (field == 2) {
        show_font_sizes(combo, page_settings(gtk_widget_get_toplevel(widget), "org.mate.interface"));
        return;
    }
    g_autofree char *configured = NULL;
    g_object_get(gtk_widget_get_settings(widget), "gtk-theme-name",
                 &configured, NULL);
    const char *value = configured;
    if (g_getenv("GTK_THEME")) value = g_getenv("GTK_THEME");
    if (field == 1 && g_strcmp0(value, "Windows XP style (Blue)") == 0)
        value = chinese ? "默认（蓝色）" : "Default (blue)";
    if (value) show_current_value(combo, value);
}

static void update_display_label(GdkScreen *screen, GtkWidget *widget)
{
    GdkDisplay *display = gdk_screen_get_display(screen);
    GdkMonitor *monitor = gdk_display_get_monitor_at_window(display, gtk_widget_get_window(widget));
    if (!monitor) return;
    if (g_object_get_data(G_OBJECT(widget), "xp-resolution")) {
        GdkRectangle area;
        gdk_monitor_get_geometry(monitor, &area);
        int scale = gdk_monitor_get_scale_factor(monitor);
        g_autofree char *text = g_strdup_printf(chinese ? "%d × %d 像素" : "%d × %d pixels",
                                                area.width * scale, area.height * scale);
        gtk_label_set_text(GTK_LABEL(widget), text);
    } else {
        const char *model = gdk_monitor_get_model(monitor);
        gtk_label_set_text(GTK_LABEL(widget), model ? model : (chinese ? "显示器" : "Monitor"));
    }
}

typedef struct {
    char *output;
    GPtrArray *modes;
    int current;
    gboolean pending;
} DisplayModes;

static void free_modes(gpointer data)
{
    DisplayModes *m = data;
    g_free(m->output);
    g_ptr_array_unref(m->modes);
    g_free(m);
}

static gint mode_order(gconstpointer a, gconstpointer b)
{
    int aw, ah, bw, bh;
    sscanf(*(char *const *)a, "%dx%d", &aw, &ah);
    sscanf(*(char *const *)b, "%dx%d", &bw, &bh);
    return aw == bw ? ah - bh : aw - bw;
}

static gboolean set_mode(DisplayModes *m, int index, GError **error)
{
    gchar *args[] = {"xrandr", "--output", m->output, "--mode", m->modes->pdata[index], NULL};
    gint status;
    return g_spawn_sync(NULL, args, NULL, G_SPAWN_SEARCH_PATH, NULL, NULL, NULL, NULL, &status, error)
        && g_spawn_check_wait_status(status, error);
}

static gboolean expire_mode(gpointer dialog)
{
    gtk_dialog_response(GTK_DIALOG(dialog), GTK_RESPONSE_CANCEL);
    return G_SOURCE_REMOVE;
}

static void apply_mode(GSimpleAction *action, GVariant *parameter, GtkRange *range)
{
    DisplayModes *m = g_object_get_data(G_OBJECT(range), "xp-modes");
    int requested = (int)gtk_range_get_value(range);
    if (!m->pending || requested == m->current) return;
    m->pending = FALSE;
    g_autoptr(GError) error = NULL;
    GtkWindow *parent = GTK_WINDOW(gtk_widget_get_toplevel(GTK_WIDGET(range)));
    if (set_mode(m, requested, &error)) {
        GtkWidget *dialog = gtk_message_dialog_new(parent, GTK_DIALOG_MODAL, GTK_MESSAGE_QUESTION,
            GTK_BUTTONS_NONE, "%s", chinese ? "保留此分辨率？15 秒后将自动还原。" :
            "Keep this resolution? The previous mode will return in 15 seconds.");
        gtk_dialog_add_buttons(GTK_DIALOG(dialog), chinese ? "还原" : "Revert", GTK_RESPONSE_CANCEL,
            chinese ? "保留" : "Keep", GTK_RESPONSE_ACCEPT, NULL);
        GSource *timer = g_timeout_source_new_seconds(15);
        g_source_set_callback(timer, expire_mode, dialog, NULL);
        g_source_attach(timer, NULL);
        int response = gtk_dialog_run(GTK_DIALOG(dialog));
        g_source_destroy(timer);
        g_source_unref(timer);
        gtk_widget_destroy(dialog);
        if (response == GTK_RESPONSE_ACCEPT) {
            m->current = requested;
            g_autofree char *helper = g_build_filename(g_get_home_dir(), ".local", "share",
                "agentlinux-xp", "display-mode.py", NULL);
            g_autoptr(GSubprocess) save = g_subprocess_new(G_SUBPROCESS_FLAGS_NONE, &error,
                "/usr/bin/python3", helper, m->output, m->modes->pdata[requested], NULL);
            if (save) g_subprocess_wait_check(save, NULL, &error);
        } else if (!set_mode(m, m->current, &error)) {
            m->current = requested;
        }
    }
    gtk_range_set_value(range, m->current);
    m->pending = FALSE;
    if (error) {
        GtkWidget *notice = gtk_message_dialog_new(parent, GTK_DIALOG_MODAL, GTK_MESSAGE_ERROR,
            GTK_BUTTONS_CLOSE, "%s", error->message);
        gtk_dialog_run(GTK_DIALOG(notice));
        gtk_widget_destroy(notice);
    }
}

static gchar *format_mode(GtkScale *scale, gdouble value, DisplayModes *m)
{
    return g_strdup(g_ptr_array_index(m->modes, (guint)value));
}

static void select_mode(GtkRange *range, DisplayModes *m)
{
    m->pending = (int)gtk_range_get_value(range) != m->current;
    if (m->pending) {
        GtkWidget *window = gtk_widget_get_toplevel(GTK_WIDGET(range));
        GAction *apply = g_action_map_lookup_action(G_ACTION_MAP(window), "apply");
        if (G_IS_SIMPLE_ACTION(apply)) g_simple_action_set_enabled(G_SIMPLE_ACTION(apply), TRUE);
    }
}

static void configure_resolution(GtkWidget *widget)
{
    g_autofree char *output = NULL;
    gint status;
    gtk_widget_set_sensitive(widget, FALSE);
    if (!g_spawn_command_line_sync("xrandr --current", &output, NULL, &status, NULL) || status) return;
    g_auto(GStrv) lines = g_strsplit(output, "\n", -1);
    GdkDisplay *display = gtk_widget_get_display(widget);
    GdkMonitor *monitor = gdk_display_get_monitor_at_window(display, gtk_widget_get_window(widget));
    const char *name = monitor ? gdk_monitor_get_model(monitor) : NULL;
    int start = -1, primary = -1;
    for (int i = 0; lines[i]; i++) {
        char *connected = strstr(lines[i], " connected ");
        if (!connected) continue;
        if (name && strlen(name) == (gsize)(connected - lines[i]) && g_str_has_prefix(lines[i], name)) {
            start = i;
            break;
        }
        if (strstr(connected, " primary ")) primary = i;
        if (start < 0 || primary >= 0) start = primary >= 0 ? primary : i;
    }
    if (start < 0) return;
    DisplayModes *m = g_new0(DisplayModes, 1);
    m->output = g_strndup(lines[start], strchr(lines[start], ' ') - lines[start]);
    m->modes = g_ptr_array_new_with_free_func(g_free);
    g_object_set_data_full(G_OBJECT(widget), "xp-modes", m, free_modes);
    char *active = NULL;
    for (int i = start + 1; lines[i] && g_ascii_isspace(lines[i][0]); i++) {
        char mode[64], extra;
        int width, height;
        if (sscanf(lines[i], "%63s", mode) != 1 || sscanf(mode, "%dx%d%c", &width, &height, &extra) != 2) continue;
        char *copy = g_strdup(mode);
        g_ptr_array_add(m->modes, copy);
        if (strchr(lines[i], '*')) active = copy;
    }
    if (!active || m->modes->len < 2) return;
    g_ptr_array_sort(m->modes, mode_order);
    guint current;
    g_ptr_array_find(m->modes, active, &current);
    m->current = current;
    gtk_range_set_range(GTK_RANGE(widget), 0, m->modes->len - 1);
    gtk_range_set_increments(GTK_RANGE(widget), 1, 1);
    gtk_scale_set_digits(GTK_SCALE(widget), 0);
    gtk_range_set_value(GTK_RANGE(widget), current);
    g_signal_connect(widget, "format-value", G_CALLBACK(format_mode), m);
    g_signal_connect(widget, "value-changed", G_CALLBACK(select_mode), m);
    GtkWidget *window = gtk_widget_get_toplevel(widget);
    GAction *apply = g_action_map_lookup_action(G_ACTION_MAP(window), "apply");
    if (apply) g_signal_connect_object(apply, "activate", G_CALLBACK(apply_mode), widget, 0);
    gtk_widget_set_can_focus(widget, TRUE);
    gtk_widget_set_sensitive(widget, TRUE);
}

static void select_display_page(GSimpleAction *action, GVariant *value, GtkNotebook *book)
{
    int page = g_variant_get_int32(value);
    if (page >= 0 && page < gtk_notebook_get_n_pages(book)) {
        gtk_notebook_set_current_page(book, page);
        gtk_window_present(GTK_WINDOW(gtk_widget_get_toplevel(GTK_WIDGET(book))));
    }
}

static gboolean on_map(GSignalInvocationHint *hint, guint count, const GValue *values, gpointer data)
{
    GtkWidget *widget = g_value_get_object(values);
    if (!g_object_get_data(G_OBJECT(widget), "agentlinux-observed")) {
        GtkWidget *window = gtk_widget_get_toplevel(widget);
        const char *id = gtk_buildable_get_name(GTK_BUILDABLE(widget));
        if (GTK_IS_NOTEBOOK(widget) && g_strcmp0(id, "main-notebook") == 0) {
            GtkApplication *app = gtk_window_get_application(GTK_WINDOW(window));
            g_autoptr(GSimpleAction) select = g_simple_action_new("select-page", G_VARIANT_TYPE_INT32);
            g_signal_connect_object(select, "activate", G_CALLBACK(select_display_page), widget, 0);
            g_action_map_add_action(G_ACTION_MAP(app), G_ACTION(select));
            const char *requested = g_getenv("AGENTLINUX_DISPLAY_PAGE");
            if (requested && requested[0] >= '0' && requested[0] <= '4' && !requested[1])
                gtk_notebook_set_current_page(GTK_NOTEBOOK(widget), requested[0] - '0');
        }
        if (GTK_IS_SCALE(widget) && GTK_IS_APPLICATION_WINDOW(window)) {
            GtkWidget *book = gtk_widget_get_ancestor(widget, GTK_TYPE_NOTEBOOK);
            if (book && gtk_widget_is_ancestor(widget, gtk_notebook_get_nth_page(GTK_NOTEBOOK(book), 4)))
                configure_resolution(widget);
        }
        if (GTK_IS_BUTTON(widget) && g_strcmp0(gtk_button_get_label(GTK_BUTTON(widget)), "Customize Desktop...") == 0) {
            gtk_widget_set_sensitive(widget, TRUE);
            g_signal_connect(widget, "clicked", G_CALLBACK(customize_desktop), NULL);
        }
        if (GTK_IS_BUTTON(widget) && g_strcmp0(gtk_button_get_label(GTK_BUTTON(widget)), "Effects...") == 0) {
            gtk_widget_set_sensitive(widget, TRUE);
            g_signal_connect(widget, "clicked", G_CALLBACK(edit_effects), NULL);
        }
        if (GTK_IS_BUTTON(widget) && g_strcmp0(gtk_button_get_label(GTK_BUTTON(widget)), "Troubleshoot...") == 0) {
            gtk_widget_set_sensitive(widget, TRUE);
            g_signal_connect(widget, "clicked", G_CALLBACK(troubleshoot_display), NULL);
        }
        if (GTK_IS_BUTTON(widget) && GTK_IS_APPLICATION_WINDOW(window) &&
            g_strcmp0(gtk_button_get_label(GTK_BUTTON(widget)), "Settings") == 0) {
            GSettings *settings = saver_settings(window);
            if (g_settings_is_writable(settings, "background")) {
                g_settings_bind(settings, "idle-activation-enabled", widget,
                                "sensitive", G_SETTINGS_BIND_GET | G_SETTINGS_BIND_NO_SENSITIVITY);
                g_signal_connect_object(widget, "clicked", G_CALLBACK(choose_saver_background), settings, 0);
            }
        }
        if (GTK_IS_BUTTON(widget) && g_strcmp0(gtk_button_get_label(GTK_BUTTON(widget)), "Preview") == 0
            && g_file_test(screensaver_program, G_FILE_TEST_IS_EXECUTABLE)) {
            g_settings_bind(saver_settings(window), "idle-activation-enabled", widget,
                            "sensitive", G_SETTINGS_BIND_GET | G_SETTINGS_BIND_NO_SENSITIVITY);
            g_signal_connect(widget, "clicked", G_CALLBACK(preview_screensaver), NULL);
        }
        if (GTK_IS_BUTTON(widget) && (g_strcmp0(gtk_button_get_label(GTK_BUTTON(widget)), "Power") == 0 ||
                                      g_strcmp0(gtk_button_get_label(GTK_BUTTON(widget)), "Advanced") == 0)) {
            gboolean power = g_str_equal(gtk_button_get_label(GTK_BUTTON(widget)), "Power");
            GtkWidget *book = gtk_widget_get_ancestor(widget, GTK_TYPE_NOTEBOOK);
            gboolean appearance = book && gtk_widget_is_ancestor(widget, gtk_notebook_get_nth_page(GTK_NOTEBOOK(book), 3));
            GDesktopAppInfo *app = g_desktop_app_info_new(power ? "agentlinux-xp-power.desktop" :
                                              appearance ? "xfce-ui-settings.desktop" : "xfce-display-settings.desktop");
            if (app) {
                g_object_set_data_full(G_OBJECT(widget), "agentlinux-settings-app", app, g_object_unref);
                g_signal_connect(widget, "clicked", G_CALLBACK(open_settings_app), app);
                gtk_widget_set_sensitive(widget, TRUE);
            }
        }
        if (GTK_IS_CHECK_BUTTON(widget) && GTK_IS_APPLICATION_WINDOW(window) &&
            g_strcmp0(gtk_button_get_label(GTK_BUTTON(widget)), "On resume, display Welcome screen") == 0) {
            gtk_widget_set_can_focus(widget, TRUE);
            GSettings *settings = saver_settings(window);
            g_settings_bind(settings, "lock-enabled", widget, "active", G_SETTINGS_BIND_DEFAULT);
            g_settings_bind_writable(settings, "lock-enabled", widget, "sensitive", FALSE);
        }
        if (GTK_IS_COMBO_BOX(widget) && GTK_IS_APPLICATION_WINDOW(window)) {
            GtkWidget *notebook = gtk_widget_get_ancestor(widget, GTK_TYPE_NOTEBOOK);
            if (notebook && gtk_widget_is_ancestor(widget, gtk_notebook_get_nth_page(GTK_NOTEBOOK(notebook), 2)))
                setup_saver_choice(GTK_COMBO_BOX(widget), saver_settings(window));
            else if (notebook && gtk_widget_is_ancestor(widget, gtk_notebook_get_nth_page(GTK_NOTEBOOK(notebook), 3)))
                show_appearance_value(GTK_COMBO_BOX(widget));
            else if (notebook && gtk_widget_is_ancestor(widget, gtk_notebook_get_nth_page(GTK_NOTEBOOK(notebook), 4)))
                show_color_depth(GTK_COMBO_BOX(widget));
        }
        if (GTK_IS_LABEL(widget)) {
            const char *label = gtk_label_get_text(GTK_LABEL(widget));
            gboolean resolution = g_strcmp0(label, "blam! pixels") == 0;
            if (resolution || g_strcmp0(label, "(not implemented)") == 0) {
                GtkWidget *book = gtk_widget_get_ancestor(widget, GTK_TYPE_NOTEBOOK);
                if (book && gtk_widget_is_ancestor(widget, gtk_notebook_get_nth_page(GTK_NOTEBOOK(book), 4))) {
                    g_object_set_data(G_OBJECT(widget), "xp-resolution", GINT_TO_POINTER(resolution));
                    GdkScreen *screen = gtk_widget_get_screen(widget);
                    update_display_label(screen, widget);
                    g_signal_connect_object(screen, "monitors-changed", G_CALLBACK(update_display_label), widget, 0);
                }
            }
        }
        if (GTK_IS_SPIN_BUTTON(widget) && GTK_IS_APPLICATION_WINDOW(window)) {
            GSettings *settings = saver_settings(window);
            int minutes = g_settings_get_int(settings, "idle-delay");
            GtkSpinButton *spin = GTK_SPIN_BUTTON(widget);
            gtk_spin_button_set_range(spin, MIN(1, minutes), MAX(9999, minutes));
            gtk_spin_button_set_increments(spin, 1, 10);
            gtk_spin_button_set_value(spin, minutes);
            gtk_widget_set_sensitive(widget, g_settings_is_writable(settings, "idle-delay"));
            gtk_widget_set_can_focus(widget, TRUE);
            g_signal_connect_object(spin, "value-changed", G_CALLBACK(stage_wait), settings, 0);

        }
        if (GTK_IS_LIST_BOX(widget) && g_strcmp0(id, "listbox-wallpapers") == 0)
            g_signal_connect_object(widget, "row-selected", G_CALLBACK(row_changed), window, 0);
        if (GTK_IS_COMBO_BOX(widget) && g_strcmp0(id, "combo-style") == 0) {
            g_autoptr(GSettings) background = g_settings_new("org.mate.background");
            g_autofree char *style = g_settings_get_string(background, "picture-options");
            for (guint i = 0; i < G_N_ELEMENTS(wallpaper_styles); i++)
                if (g_str_equal(style, wallpaper_styles[i]))
                    gtk_combo_box_set_active(GTK_COMBO_BOX(widget), i);
            g_signal_connect_object(widget, "changed", G_CALLBACK(wallpaper_changed), window, 0);
        }
        if (GTK_IS_APPLICATION_WINDOW(widget)) {
            const char *names[] = {"apply", "ok"};
            for (size_t i = 0; i < G_N_ELEMENTS(names); i++) {
                GAction *action = g_action_map_lookup_action(G_ACTION_MAP(widget), names[i]);
                if (action) g_signal_connect_after(action, "activate", G_CALLBACK(apply_wallpaper), widget);
            }
        }
        g_object_set_data(G_OBJECT(widget), "agentlinux-observed", GINT_TO_POINTER(1));
    }
    if (chinese && GTK_IS_COMBO_BOX(widget) &&
        g_strcmp0(gtk_buildable_get_name(GTK_BUILDABLE(widget)), "combo-style") == 0) {
        GList *cells = gtk_cell_layout_get_cells(GTK_CELL_LAYOUT(widget));
        for (GList *item = cells; item; item = item->next)
            if (GTK_IS_CELL_RENDERER_TEXT(item->data))
                gtk_cell_layout_set_cell_data_func(GTK_CELL_LAYOUT(widget), item->data, style_caption, NULL, NULL);
        g_list_free(cells);
    } else if (chinese && GTK_IS_WINDOW(widget)) {
        const char *title = translation(gtk_window_get_title(GTK_WINDOW(widget)));
        if (title) gtk_window_set_title(GTK_WINDOW(widget), title);
    } else if (GTK_IS_LABEL(widget)) {
        const char *text = gtk_label_get_text(GTK_LABEL(widget));
        GtkWidget *list = gtk_widget_get_ancestor(widget, GTK_TYPE_LIST_BOX);
        if (list && g_strcmp0(gtk_buildable_get_name(GTK_BUILDABLE(list)), "listbox-wallpapers") == 0) {
            static const struct { const char *file, *zh, *en; } themes[] = {
                {"AgentLinux.jpg", "AgentLinux · 规划、执行与验证", "AgentLinux · Plan / Act / Verify"},
                {"AgentLinux-Nodes.jpg", "AgentLinux · 智能体网络", "AgentLinux · Agent Network"},
                {"AgentLinux-Studio.jpg", "AgentLinux · 推理工作室", "AgentLinux · Reasoning Studio"},
                {"college-bliss.svg", "学院 · 经典草原", "College · Bliss"}
            };
            for (guint i = 0; i < G_N_ELEMENTS(themes); i++) {
                if (g_str_equal(text, themes[i].file)) {
                    gtk_label_set_text(GTK_LABEL(widget), chinese ? themes[i].zh : themes[i].en);
                    gtk_widget_set_tooltip_text(widget, themes[i].file);
                    return TRUE;
                }
            }
        }
        if (g_strcmp0(text, "Sample:") == 0)
            g_idle_add_full(G_PRIORITY_DEFAULT_IDLE, add_preview, g_object_ref(widget), g_object_unref);
        const char *label = chinese ? translation(text) : NULL;
        if (label) gtk_label_set_text(GTK_LABEL(widget), label);
    }
    return TRUE;
}

void gtk_module_init(gint *argc, gchar ***argv)
{
    if (g_strcmp0(g_get_prgname(), "desk.cpl") != 0) return;
    g_autoptr(GSettings) background = g_settings_new("org.mate.background");
    g_autofree char *current = g_settings_get_string(background, "picture-filename");
    if (current && g_file_test(current, G_FILE_TEST_IS_REGULAR)) {
        const char *key = "HKCU\\Control Panel\\Desktop";
        WinTCRegistry *registry = wintc_registry_new();
        g_autofree char *saved = NULL;
        wintc_registry_get_key_value(registry, key, "Wallpaper", WINTC_REG_SZ, &saved, NULL);
        if (g_strcmp0(saved, current) != 0)
            wintc_registry_set_key_value(registry, key, "Wallpaper", WINTC_REG_SZ, &current, TRUE, NULL);
        g_object_unref(registry);
    }
    chinese = g_str_has_prefix(g_get_language_names()[0], "zh");
    gpointer klass = g_type_class_ref(GTK_TYPE_WIDGET);
    g_signal_add_emission_hook(g_signal_lookup("map", GTK_TYPE_WIDGET), 0, on_map, NULL, NULL);
    g_type_class_unref(klass);
}
