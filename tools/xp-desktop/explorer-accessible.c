#include <gtk/gtk-a11y.h>
#include "../public/lstvwctl.h"

typedef struct {
    AtkObject parent;
    GWeakRef view;
    GtkTreeRowReference *row;
    gchar *label;
} FileItem;
typedef AtkObjectClass FileItemClass;

static void file_actions(AtkActionIface *iface);
G_DEFINE_TYPE_WITH_CODE(FileItem, file_item, ATK_TYPE_OBJECT,
                        G_IMPLEMENT_INTERFACE(ATK_TYPE_ACTION, file_actions))

static WinTCCtlListView *current_view(FileItem *item)
{
    WinTCCtlListView *view = g_weak_ref_get(&item->view);
    if (view && wintc_ctl_list_view_get_model(view) != gtk_tree_row_reference_get_model(item->row))
        g_clear_object(&view);
    return view;
}

static const gchar *file_name(AtkObject *object)
{
    FileItem *item = (FileItem *)object;
    g_autoptr(WinTCCtlListView) view = current_view(item);
    g_autoptr(GtkTreePath) path = gtk_tree_row_reference_get_path(item->row);
    GtkTreeIter iter;
    g_clear_pointer(&item->label, g_free);
    if (view && path) {
        GtkTreeModel *model = wintc_ctl_list_view_get_model(view);
        gint col = wintc_ctl_list_view_get_text_column(view);
        if (col >= 0 && gtk_tree_model_get_iter(model, &iter, path))
            gtk_tree_model_get(model, &iter, col, &item->label, -1);
    }
    return item->label;
}

static gboolean file_action(AtkAction *action, gint index)
{
    FileItem *item = (FileItem *)action;
    g_autoptr(WinTCCtlListView) view = current_view(item);
    g_autoptr(GtkTreePath) path = gtk_tree_row_reference_get_path(item->row);
    if (!view || !path || index < 0 || index > 1) return FALSE;
    wintc_ctl_list_view_unselect_all(view);
    wintc_ctl_list_view_select_path(view, path);
    if (index == 1) g_signal_emit_by_name(view, "item-activated", path);
    return TRUE;
}

static gint action_count(AtkAction *action) { return 2; }
static const gchar *action_name(AtkAction *action, gint index)
{
    const gchar *names[] = {"select", "open"};
    return index >= 0 && index < 2 ? names[index] : NULL;
}
static void file_actions(AtkActionIface *iface)
{
    iface->get_n_actions = action_count;
    iface->get_name = action_name;
    iface->do_action = file_action;
}

static void file_finalize(GObject *object)
{
    FileItem *item = (FileItem *)object;
    g_clear_pointer(&item->row, gtk_tree_row_reference_free);
    g_weak_ref_clear(&item->view);
    g_free(item->label);
    G_OBJECT_CLASS(file_item_parent_class)->finalize(object);
}
static void file_item_class_init(FileItemClass *klass)
{
    G_OBJECT_CLASS(klass)->finalize = file_finalize;
    ATK_OBJECT_CLASS(klass)->get_name = file_name;
}
static void file_item_init(FileItem *item)
{
    g_weak_ref_init(&item->view, NULL);
    atk_object_set_role(ATK_OBJECT(item), ATK_ROLE_LIST_ITEM);
}

typedef GtkWidgetAccessible FileList;
typedef GtkWidgetAccessibleClass FileListClass;
G_DEFINE_TYPE(FileList, file_list, GTK_TYPE_WIDGET_ACCESSIBLE)

static gint file_count(AtkObject *object)
{
    GtkWidget *view = gtk_accessible_get_widget(GTK_ACCESSIBLE(object));
    GtkTreeModel *model = view ? wintc_ctl_list_view_get_model(WINTC_CTL_LIST_VIEW(view)) : NULL;
    return model ? gtk_tree_model_iter_n_children(model, NULL) : 0;
}

static AtkObject *file_child(AtkObject *parent, gint index)
{
    if (index < 0 || index >= file_count(parent)) return NULL;
    GtkWidget *view = gtk_accessible_get_widget(GTK_ACCESSIBLE(parent));
    GtkTreeModel *model = wintc_ctl_list_view_get_model(WINTC_CTL_LIST_VIEW(view));
    g_autoptr(GtkTreePath) path = gtk_tree_path_new_from_indices(index, -1);
    FileItem *item = g_object_new(file_item_get_type(), NULL);
    item->row = gtk_tree_row_reference_new(model, path);
    g_weak_ref_set(&item->view, view);
    atk_object_set_parent(ATK_OBJECT(item), parent);
    return ATK_OBJECT(item);
}
static void file_list_class_init(FileListClass *klass)
{
    ATK_OBJECT_CLASS(klass)->get_n_children = file_count;
    ATK_OBJECT_CLASS(klass)->ref_child = file_child;
}
static void file_list_init(FileList *list) {}
