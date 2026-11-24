/* Passive X11 grabs for the XP desktop shortcuts. */
#include <X11/Xlib.h>
#include <X11/keysym.h>
#include <X11/XKBlib.h>
#include <signal.h>
#include <stdio.h>
#include <unistd.h>

static int unavailable;
static int grab_error(Display *display, XErrorEvent *event)
{
    (void)display;
    unavailable = event->error_code;
    return 0;
}

/* Both session startup and XDG autostart can reach this helper. */
static int claim_shortcuts(Display *display, Window root)
{
    char name[64];
    snprintf(name, sizeof(name), "_AGENTLINUX_XP_SHORTCUTS_S%d", DefaultScreen(display));
    Atom selection = XInternAtom(display, name, False);
    XGrabServer(display);
    int available = XGetSelectionOwner(display, selection) == None;
    if (available) {
        Window owner = XCreateSimpleWindow(display, root, 0, 0, 1, 1, 0, 0, 0);
        XSetSelectionOwner(display, selection, owner, CurrentTime);
    }
    XUngrabServer(display);
    XSync(display, False);
    return available;
}

int main(void)
{
    Display *display = XOpenDisplay(NULL);
    if (!display) return 1;
    Window root = DefaultRootWindow(display);
    unsigned int numlock = XkbKeysymToModifiers(display, XK_Num_Lock);
    unsigned int super = XkbKeysymToModifiers(display, XK_Super_L);
    if (!super) return 1;
    if (!claim_shortcuts(display, root)) {
        XCloseDisplay(display);
        return 0;
    }
    unsigned int locks[] = {0, LockMask, numlock, LockMask | numlock};
    struct shortcut {
        KeySym symbol;
        unsigned int modifiers;
        const char *entry;
        KeyCode key;
    } shortcuts[] = {
        {XK_Escape, ControlMask, NULL, 0},
        {XK_r, super, "agentlinux-xp-run", 0},
        {XK_Escape, ControlMask | ShiftMask, "agentlinux-xp-taskmgr", 0},
        {XK_e, super, "agentlinux-xp-computer", 0},
        {XK_Pause, super, "agentlinux-xp-system", 0},
    };
    XSetErrorHandler(grab_error);
    for (size_t i = 0; i < sizeof(shortcuts) / sizeof(shortcuts[0]); i++) {
        struct shortcut *binding = &shortcuts[i];
        binding->key = XKeysymToKeycode(display, binding->symbol);
        if (!binding->key)
            continue;
        unavailable = 0;
        for (size_t j = 0; j < sizeof(locks) / sizeof(locks[0]); j++)
            XGrabKey(display, binding->key, binding->modifiers | locks[j], root,
                     False, GrabModeAsync, GrabModeAsync);
        XSync(display, False);
        if (unavailable)
            fprintf(stderr, "Shortcut %s unavailable (X11 error %d)\n",
                    XKeysymToString(binding->symbol), unavailable);
    }
    signal(SIGCHLD, SIG_IGN);
    for (;;) {
        XEvent event;
        XNextEvent(display, &event);
        if (event.type != KeyPress)
            continue;
        for (size_t i = 0; i < sizeof(shortcuts) / sizeof(shortcuts[0]); i++) {
            if (event.xkey.keycode != shortcuts[i].key ||
                (event.xkey.state & (0xffu & ~(LockMask | numlock))) != shortcuts[i].modifiers)
                continue;
            if (fork() == 0) {
                close(ConnectionNumber(display));
                if (shortcuts[i].entry)
                    execl("/usr/bin/gtk-launch", "gtk-launch", shortcuts[i].entry, (char *)NULL);
                else
                    execl("/usr/bin/wintc-taskband", "wintc-taskband", "--start", (char *)NULL);
                _exit(127);
            }
            break;
        }
    }
}
