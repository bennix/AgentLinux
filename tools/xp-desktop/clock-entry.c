#include <gtk/gtk.h>
#include <ifaddrs.h>
#include <net/if.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <gio/gdesktopappinfo.h>

static gboolean launch_entry(const char *desktop)
{
    GDesktopAppInfo *app = g_desktop_app_info_new(desktop);
    if (!app)
        return FALSE;
    GError *error = NULL;
    gboolean ok = g_app_info_launch(G_APP_INFO(app), NULL, NULL, &error);
    if (error) {
        g_warning("%s: %s", desktop, error->message);
        g_error_free(error);
    }
    g_object_unref(app);
    return ok;
}

static gboolean clock_pressed(GtkWidget *window, GdkEventButton *event, gpointer data)
{
    return event->type == GDK_2BUTTON_PRESS && event->button == 1
        && launch_entry("agentlinux-xp-datetime.desktop");
}

static void menu_launch(GtkMenuItem *item, gpointer desktop)
{
    launch_entry(desktop);
}

static gboolean chinese_menu;

static gboolean is_network_icon(GtkWidget *widget)
{
    g_autofree gchar *name = NULL;
    g_object_get(widget, "icon-name", &name, NULL);
    return g_strcmp0(name, "network-idle") == 0 || g_strcmp0(name, "network-offline") == 0;
}

static gboolean network_tooltip(GtkWidget *widget, gint x, gint y, gboolean keyboard,
                                GtkTooltip *tooltip, gpointer unused)
{
    if (!is_network_icon(widget)) return FALSE;
    g_autoptr(GString) text = g_string_new(chinese_menu ? "网络连接" : "Network Connections");
    struct ifaddrs *interfaces = NULL;
    if (getifaddrs(&interfaces) == 0) {
        for (struct ifaddrs *it = interfaces; it; it = it->ifa_next) {
            if (!it->ifa_addr || !(it->ifa_flags & IFF_UP) || it->ifa_flags & IFF_LOOPBACK) continue;
            int family = it->ifa_addr->sa_family;
            const void *address;
            if (family == AF_INET)
                address = &((struct sockaddr_in *)it->ifa_addr)->sin_addr;
            else if (family == AF_INET6)
                address = &((struct sockaddr_in6 *)it->ifa_addr)->sin6_addr;
            else
                continue;
            char buffer[INET6_ADDRSTRLEN];
            if (inet_ntop(family, address, buffer, sizeof(buffer)))
                g_string_append_printf(text, "\n%s   %s", it->ifa_name, buffer);
        }
        freeifaddrs(interfaces);
    }
    gtk_tooltip_set_text(tooltip, text->str);
    return TRUE;
}

/* WinTC updates this property on UPower source and battery changes. */
static void show_external_power(GtkWidget *widget, GParamSpec *pspec, gpointer unused)
{
    g_autofree gchar *icon = NULL;
    g_object_get(widget, "icon-name", &icon, NULL);
    if (!icon || !g_str_has_prefix(icon, "battery-")) return;

    g_autoptr(GDir) supplies = g_dir_open("/sys/class/power_supply", 0, NULL);
    if (!supplies) return;
    const gchar *name;
    while ((name = g_dir_read_name(supplies))) {
        g_autofree gchar *dir = g_build_filename("/sys/class/power_supply", name, NULL);
        g_autofree gchar *online_path = g_build_filename(dir, "online", NULL);
        g_autofree gchar *online = NULL;
        if (!g_file_get_contents(online_path, &online, NULL, NULL) ||
            !g_str_equal(g_strstrip(online), "1")) continue;
        g_autofree gchar *scope_path = g_build_filename(dir, "scope", NULL);
        g_autofree gchar *scope = NULL;
        if (g_file_get_contents(scope_path, &scope, NULL, NULL) &&
            g_str_equal(g_strstrip(scope), "Device")) continue;
        g_autofree gchar *type_path = g_build_filename(dir, "type", NULL);
        g_autofree gchar *type = NULL;
        if (!g_file_get_contents(type_path, &type, NULL, NULL)) continue;
        g_strstrip(type);
        if (g_str_equal(type, "Mains") || g_str_has_prefix(type, "USB") ||
            g_str_equal(type, "Wireless")) {
            g_object_set(widget, "icon-name", "ac-adapter", NULL);
            return;
        }
    }
}

static void name_tray_icon(GtkWidget *widget, GParamSpec *pspec, gpointer data)
{
    g_autofree gchar *icon = NULL;
    const gchar *name = NULL;
    g_object_get(widget, "icon-name", &icon, NULL);
    if (!icon) return;
    if (g_str_has_prefix(icon, "audio-volume-"))
        name = chinese_menu ? "音量" : "Volume";
    else if (g_str_has_prefix(icon, "battery-"))
        name = chinese_menu ? "电池" : "Battery";
    else if (g_str_equal(icon, "ac-adapter"))
        name = chinese_menu ? "外接电源" : "AC power";
    else if (is_network_icon(widget))
        name = chinese_menu ? "网络连接" : "Network Connections";
    if (name) atk_object_set_name(gtk_widget_get_accessible(widget), name);
}

static gboolean tray_event(GtkWidget *widget, GdkEvent *event, gpointer data)
{
    if (event->type != GDK_BUTTON_PRESS)
        return FALSE;
    g_autofree gchar *icon = NULL;
    g_object_get(widget, "icon-name", &icon, NULL);
    if (icon && g_str_has_prefix(icon, "audio-volume-") && event->button.button == 3)
        return launch_entry("agentlinux-xp-audio.desktop");
    if (icon && (g_str_has_prefix(icon, "battery-") || g_str_equal(icon, "ac-adapter"))) {
        if (event->button.button == 1) {
            g_autofree gchar *script = g_build_filename(g_get_home_dir(), ".local", "share",
                "agentlinux-xp", "power-properties.py", NULL);
            gchar *args[] = {"/usr/bin/python3", script, "--meter", NULL};
            return g_spawn_async(NULL, args, NULL, G_SPAWN_DEFAULT, NULL, NULL, NULL, NULL);
        }
        if (event->button.button == 3)
            return launch_entry("agentlinux-xp-power.desktop");
        return FALSE;
    }
    if (!is_network_icon(widget))
        return FALSE;
    if (event->button.button == 1)
        return launch_entry("agentlinux-xp-wifi.desktop");
    if (event->button.button != 3)
        return FALSE;
    GtkWidget *menu = gtk_menu_new();
    const char *entries[] = {"agentlinux-xp-wifi.desktop", "agentlinux-xp-connections.desktop",
                             "nm-connection-editor.desktop", "agentlinux-system-network.desktop"};
    for (guint i = 0; i < G_N_ELEMENTS(entries); i++) {
        GDesktopAppInfo *app = g_desktop_app_info_new(entries[i]);
        if (!app)
            continue;
        GtkWidget *item = gtk_menu_item_new_with_label(g_app_info_get_display_name(G_APP_INFO(app)));
        g_signal_connect(item, "activate", G_CALLBACK(menu_launch), (gpointer)entries[i]);
        gtk_menu_shell_append(GTK_MENU_SHELL(menu), item);
        g_object_unref(app);
    }
    g_signal_connect_swapped(menu, "selection-done", G_CALLBACK(gtk_widget_destroy), menu);
    gtk_widget_show_all(menu);
    gtk_menu_popup_at_pointer(GTK_MENU(menu), event);
    return TRUE;
}

static GVariant *ime_call(const char *method, GVariant *args)
{
    g_autoptr(GDBusConnection) bus = g_bus_get_sync(G_BUS_TYPE_SESSION, NULL, NULL);
    if (!bus) return NULL;
    return g_dbus_connection_call_sync(bus, "org.fcitx.Fcitx5", "/controller",
        "org.fcitx.Fcitx.Controller1", method, args, NULL, G_DBUS_CALL_FLAGS_NO_AUTO_START,
        400, NULL, NULL);
}

static gboolean apply_ime(gpointer id)
{
    g_autoptr(GVariant) result = ime_call("SetCurrentIM", g_variant_new("(s)", (const char *)id));
    return G_SOURCE_REMOVE;
}

static void choose_ime(GtkMenuItem *entry, gpointer unused)
{
    /* Let the popup release its grab and the editor regain its input context. */
    GtkWidget *menu = gtk_widget_get_parent(GTK_WIDGET(entry));
    GdkWindow *editor = g_object_get_data(G_OBJECT(menu), "input-target");
    if (editor && !gdk_window_is_destroyed(editor))
        gdk_window_focus(editor, gtk_get_current_event_time());
    const char *id = g_object_get_data(G_OBJECT(entry), "ime-id");
    g_timeout_add_full(G_PRIORITY_DEFAULT, 150, apply_ime, g_strdup(id), g_free);
}

static void restart_ime(GtkMenuItem *entry, gpointer unused)
{
    g_autoptr(GVariant) reply = ime_call("Restart", NULL);
}

static void populate_input_menu(GtkWidget *menu, GtkWidget *button)
{
    GList *children = gtk_container_get_children(GTK_CONTAINER(menu));
    for (GList *item = children; item; item = item->next)
        gtk_widget_destroy(item->data);
    g_list_free(children);
    G_GNUC_BEGIN_IGNORE_DEPRECATIONS
    GdkWindow *editor = gdk_screen_get_active_window(gtk_widget_get_screen(GTK_WIDGET(button)));
    G_GNUC_END_IGNORE_DEPRECATIONS
    g_object_set_data_full(G_OBJECT(menu), "input-target", editor, g_object_unref);
    g_autoptr(GVariant) group = ime_call("CurrentInputMethodGroup", NULL);
    if (group) {
        const char *name;
        g_variant_get(group, "(&s)", &name);
        g_autoptr(GVariant) info = ime_call("InputMethodGroupInfo", g_variant_new("(s)", name));
        if (info) {
            g_autoptr(GVariant) methods = g_variant_get_child_value(info, 1);
            g_autoptr(GVariant) current = ime_call("CurrentInputMethod", NULL);
            const char *current_id = NULL;
            if (current) g_variant_get(current, "(&s)", &current_id);
            GVariantIter iter;
            const char *id, *layout;
            g_variant_iter_init(&iter, methods);
            while (g_variant_iter_loop(&iter, "(&s&s)", &id, &layout)) {
                const char *label = id;
                if (g_str_equal(id, "keyboard-us")) label = chinese_menu ? "英语（美国）" : "English (US)";
                else if (g_str_equal(id, "myime")) label = "MyIME";
                else if (g_str_equal(id, "pinyin")) label = chinese_menu ? "拼音" : "Pinyin";
                GtkWidget *item = gtk_check_menu_item_new_with_label(label);
                gtk_check_menu_item_set_draw_as_radio(GTK_CHECK_MENU_ITEM(item), TRUE);
                gtk_check_menu_item_set_active(GTK_CHECK_MENU_ITEM(item), g_strcmp0(id, current_id) == 0);
                g_object_set_data_full(G_OBJECT(item), "ime-id", g_strdup(id), g_free);
                g_signal_connect(item, "activate", G_CALLBACK(choose_ime), NULL);
                gtk_menu_shell_append(GTK_MENU_SHELL(menu), item);
                gtk_widget_show(item);
            }
        }
    }
    GtkWidget *settings = gtk_menu_item_new_with_label(chinese_menu ? "输入法设置…" : "Input settings…");
    g_signal_connect(settings, "activate", G_CALLBACK(menu_launch), "myime-settings.desktop");
    gtk_menu_shell_append(GTK_MENU_SHELL(menu), settings);
    GtkWidget *restart = gtk_menu_item_new_with_label(chinese_menu ? "重启输入法" : "Restart input method");
    g_autoptr(GVariant) capability = ime_call("CanRestart", NULL);
    gboolean can_restart = FALSE;
    if (capability) g_variant_get(capability, "(b)", &can_restart);
    gtk_widget_set_sensitive(restart, can_restart);
    g_signal_connect(restart, "activate", G_CALLBACK(restart_ime), NULL);
    gtk_menu_shell_append(GTK_MENU_SHELL(menu), restart);
    gtk_widget_show(settings);
    gtk_widget_show(restart);
}

static gboolean wrap_clock(gpointer data)
{
    GtkWidget *clock = data;
    GtkWidget *parent = gtk_widget_get_parent(clock);
    if (GTK_IS_BOX(parent)) {
        gint position = 0;
        gtk_container_child_get(GTK_CONTAINER(parent), clock, "position", &position, NULL);
        GtkWidget *hit = gtk_event_box_new();
        gtk_event_box_set_visible_window(GTK_EVENT_BOX(hit), FALSE);
        gtk_container_remove(GTK_CONTAINER(parent), clock);
        gtk_container_add(GTK_CONTAINER(hit), clock);
        gtk_box_pack_end(GTK_BOX(parent), hit, FALSE, FALSE, 0);
        gtk_box_reorder_child(GTK_BOX(parent), hit, position);
        gtk_widget_add_events(hit, GDK_BUTTON_PRESS_MASK);
        g_signal_connect(hit, "button-press-event", G_CALLBACK(clock_pressed), NULL);
        GtkWidget *input = gtk_menu_button_new();
        gtk_button_set_image(GTK_BUTTON(input), gtk_image_new_from_icon_name("input-keyboard", GTK_ICON_SIZE_MENU));
        gtk_button_set_always_show_image(GTK_BUTTON(input), TRUE);
        gtk_menu_button_set_direction(GTK_MENU_BUTTON(input), GTK_ARROW_UP);
        gtk_button_set_relief(GTK_BUTTON(input), GTK_RELIEF_NONE);
        gtk_widget_set_focus_on_click(input, FALSE);
        const char *label = chinese_menu ? "切换输入法" : "Switch input method";
        gtk_widget_set_tooltip_text(input, label);
        atk_object_set_name(gtk_widget_get_accessible(input), label);
        GtkWidget *menu = gtk_menu_new();
        gtk_menu_button_set_popup(GTK_MENU_BUTTON(input), menu);
        g_signal_connect(menu, "show", G_CALLBACK(populate_input_menu), input);
        gtk_box_pack_end(GTK_BOX(parent), input, FALSE, FALSE, 0);
        gtk_widget_show_all(input);
        gtk_widget_show_all(hit);
    }
    return G_SOURCE_REMOVE;
}

static void localize_program_folder(GtkLabel *label)
{
    static const struct { const char *en, *zh; } folders[] = {
        {"Accessories", "附件"}, {"Accessibility", "辅助工具"},
        {"Communications", "通讯"}, {"Entertainment", "娱乐"},
        {"System Tools", "系统工具"}, {"Games", "游戏"}, {"Startup", "启动"},
        {"Qt Developer Tools", "Qt 开发工具"}, {"WinTC Developer", "WinTC 开发工具"}
    };
    GtkWidget *item = gtk_widget_get_ancestor(GTK_WIDGET(label), GTK_TYPE_MENU_ITEM);
    if (!item || !gtk_menu_item_get_submenu(GTK_MENU_ITEM(item))) return;
    const char *text = gtk_label_get_text(label);
    for (guint i = 0; i < G_N_ELEMENTS(folders); i++) {
        if (g_strcmp0(text, folders[i].en) == 0) {
            gtk_label_set_text(label, folders[i].zh);
            return;
        }
    }
}

static gboolean widget_mapped(GSignalInvocationHint *hint, guint count,
                              const GValue *values, gpointer data)
{
    GtkWidget *widget = g_value_get_object(values);
    if (GTK_IS_SCALE(widget) &&
        gtk_style_context_has_class(gtk_widget_get_style_context(gtk_widget_get_toplevel(widget)), "wintc-volmgmt")) {
        atk_object_set_name(gtk_widget_get_accessible(widget), chinese_menu ? "设备音量" : "Device volume");
    }
    if (chinese_menu && GTK_IS_LABEL(widget)) {
        GtkWidget *popup = gtk_widget_get_toplevel(widget);
        if (gtk_style_context_has_class(gtk_widget_get_style_context(popup), "wintc-volmgmt")) {
            const gchar *label = gtk_label_get_text(GTK_LABEL(widget));
            if (g_strcmp0(label, "Mute") == 0) gtk_label_set_text(GTK_LABEL(widget), "静音");
            else if (g_strcmp0(label, "Volume") == 0) gtk_label_set_text(GTK_LABEL(widget), "音量");
        } else localize_program_folder(GTK_LABEL(widget));
    }
    if (g_strcmp0(G_OBJECT_TYPE_NAME(widget), "WinTCNotifAreaIcon") == 0
        && !g_object_get_data(G_OBJECT(widget), "agentlinux-network-entry")) {
        g_signal_connect(widget, "notify::icon-name", G_CALLBACK(show_external_power), NULL);
        g_signal_connect(widget, "notify::icon-name", G_CALLBACK(name_tray_icon), NULL);
        show_external_power(widget, NULL, NULL);
        name_tray_icon(widget, NULL, NULL);
        if (is_network_icon(widget)) {
            gtk_widget_set_has_tooltip(widget, TRUE);
            g_signal_connect(widget, "query-tooltip", G_CALLBACK(network_tooltip), NULL);
        }
        g_signal_connect(widget, "event", G_CALLBACK(tray_event), NULL);
        g_object_set_data(G_OBJECT(widget), "agentlinux-network-entry", GINT_TO_POINTER(1));
    }
    if (GTK_IS_LABEL(widget) && gtk_style_context_has_class(gtk_widget_get_style_context(widget), "clock")
        && !g_object_get_data(G_OBJECT(widget), "agentlinux-clock-entry")) {
        g_idle_add_full(G_PRIORITY_DEFAULT_IDLE, wrap_clock, g_object_ref(widget), g_object_unref);
        g_object_set_data(G_OBJECT(widget), "agentlinux-clock-entry", GINT_TO_POINTER(1));
    }
    return TRUE;
}

G_MODULE_EXPORT void gtk_module_init(gint *argc, gchar ***argv)
{
    if (g_strcmp0(g_get_prgname(), "wintc-taskband") == 0) {
        const char *language = g_get_language_names()[0];
        chinese_menu = g_str_has_prefix(language, "zh_CN") || g_str_equal(language, "zh");
        gpointer klass = g_type_class_ref(GTK_TYPE_WIDGET);
        g_signal_add_emission_hook(g_signal_lookup("map", GTK_TYPE_WIDGET), 0, widget_mapped, NULL, NULL);
        g_type_class_unref(klass);
    }
}
