#include <X11/XKBlib.h>
#include <stdio.h>
#include <string.h>

int main(int argc, char **argv)
{
    const unsigned mask = XkbStickyKeysMask | XkbSlowKeysMask |
                          XkbBounceKeysMask | XkbMouseKeysMask;
    Display *display = XOpenDisplay(NULL);
    if (!display) return 1;
    if (argc == 2) {
        unsigned value;
        char extra;
        if (sscanf(argv[1], "%u%c", &value, &extra) != 1 || (value & ~mask))
            return 2;
        if (!XkbChangeEnabledControls(display, XkbUseCoreKbd, mask, value))
            return 1;
    } else if (argc != 1) return 2;

    XkbDescPtr keyboard = XkbAllocKeyboard();
    if (!keyboard) return 1;
    keyboard->device_spec = XkbUseCoreKbd;
    if (XkbGetControls(display, XkbControlsEnabledMask, keyboard) != Success)
        return 1;
    printf("%u\n", keyboard->ctrls->enabled_ctrls & mask);
    XkbFreeKeyboard(keyboard, 0, True);
    XCloseDisplay(display);
    return 0;
}
