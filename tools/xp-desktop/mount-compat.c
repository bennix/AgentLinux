/* GLib 2.84 renamed these existing GUnixMountEntry functions.
 * Only preload this library in WinTC processes on Ubuntu 24.04. */
#include <stdint.h>
typedef struct _GUnixMountEntry GUnixMountEntry;
extern GUnixMountEntry *g_unix_mount_at(const char *, uint64_t *);
extern void g_unix_mount_free(GUnixMountEntry *);
extern const char *g_unix_mount_get_device_path(GUnixMountEntry *);
extern const char *g_unix_mount_get_fs_type(GUnixMountEntry *);

GUnixMountEntry *g_unix_mount_entry_at(const char *path, uint64_t *time_read)
{
    return g_unix_mount_at(path, time_read);
}
void g_unix_mount_entry_free(GUnixMountEntry *entry)
{
    g_unix_mount_free(entry);
}
const char *g_unix_mount_entry_get_device_path(GUnixMountEntry *entry)
{
    return g_unix_mount_get_device_path(entry);
}
const char *g_unix_mount_entry_get_fs_type(GUnixMountEntry *entry)
{
    return g_unix_mount_get_fs_type(entry);
}
