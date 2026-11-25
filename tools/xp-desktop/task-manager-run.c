#include <gtk/gtk.h>
#include <gio/gdesktopappinfo.h>

static void launch_run(GSimpleAction *action, GVariant *parameter, gpointer data)
{
    (void)action;
    (void)parameter;
    (void)data;
    GDesktopAppInfo *app = g_desktop_app_info_new("agentlinux-xp-run.desktop");
    if (app) {
        GAppLaunchContext *context = g_app_launch_context_new();
        g_app_launch_context_setenv(context, "AGENTLINUX_NEW_TASK", "1");
        g_app_info_launch(G_APP_INFO(app), NULL, context, NULL);
        g_object_unref(context);
        g_object_unref(app);
    }
}

static gboolean window_mapped(GSignalInvocationHint *hint, guint count,
                              const GValue *values, gpointer data)
{
    (void)hint;
    (void)count;
    (void)data;
    GtkWidget *widget = g_value_get_object(values);
    if (g_str_equal(G_OBJECT_TYPE_NAME(widget), "WinTCTaskmgrWindow") &&
        !g_action_map_lookup_action(G_ACTION_MAP(widget), "new-task")) {
        GSimpleAction *action = g_simple_action_new("new-task", NULL);
        g_signal_connect(action, "activate", G_CALLBACK(launch_run), NULL);
        g_action_map_add_action(G_ACTION_MAP(widget), G_ACTION(action));
        g_object_unref(action);
    }
    return TRUE;
}

void gtk_module_init(gint *argc, gchar ***argv)
{
    (void)argc;
    (void)argv;
    gpointer widget_class = g_type_class_ref(GTK_TYPE_WIDGET);
    g_signal_add_emission_hook(g_signal_lookup("map", GTK_TYPE_WIDGET), 0, window_mapped, NULL, NULL);
    g_type_class_unref(widget_class);
}
