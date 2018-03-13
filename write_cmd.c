#include <X11/extensions/XTest.h>
#include <X11/keysym.h>
#include <X11/Xlib.h>

#include <stdio.h>
#include <assert.h>
#include <time.h>

#define TYPE_KEYCODE(kc) do { \
    XTestFakeKeyEvent(display, kc, True, CurrentTime); \
    XTestFakeKeyEvent(display, kc, False, CurrentTime); \
    XFlush(display); } while (0)

#define TYPE_KEYSYM(ch) do { \
    XTestFakeKeyEvent(display, XKeysymToKeycode(display, (ch)), True, CurrentTime); \
    XTestFakeKeyEvent(display, XKeysymToKeycode(display, (ch)), False, CurrentTime); \
    XFlush(display); } while (0)
#define DELAY_NS 100

#define KEYPRESS(kc) do { \
            XTestFakeKeyEvent(display, (kc), True, CurrentTime); \
            XFlush(display); } while (0)

#define KEYRELEASE(kc) do { \
            XTestFakeKeyEvent(display, (kc), False, CurrentTime); \
            XFlush(display); } while (0)

Display *display;
struct timespec ts = { .tv_sec = DELAY_NS / 1000000000, .tv_nsec = DELAY_NS };

void write_string(char *cmd) {
    for (; *cmd; cmd++) {
        TYPE_KEYSYM(*cmd);
        nanosleep(&ts, NULL);
    }
    TYPE_KEYSYM(XK_Return);
}

void write_keycodes(unsigned int *cmd, int len) {
    unsigned int press_stack[1024] = { 0 };
    int top = 0;
    for (int i = 0; i < len; i++) {
        if (top > 0 && press_stack[top-1] == cmd[i]) {
            printf("KEYRELEASE: %d.\n", cmd[i]);
            KEYRELEASE(cmd[i]);
            press_stack[top--] = 0; 
        } else {
            printf("KEYPRESS: %d.\n", cmd[i]);
            KEYPRESS(cmd[i]);
            press_stack[top++] = cmd[i];
        }
        nanosleep(&ts, NULL);
    }
    if (top > 0) {
        printf("KEYRELEASE: %d.\n", press_stack[top-1]);
        KEYRELEASE(press_stack[top-1]);
    }
}

int main(int argc, char **argv) {
    display = XOpenDisplay(NULL);
    assert(display != NULL);
    XFlush(display);

    int len = 0;
    if (argc == 1) {
        unsigned int keycodes[1024];
        for (int i = 0; i < 1024; i++) {
            if (scanf("%u", keycodes + i) == EOF)
                break;
            len++;
        }
        write_keycodes(keycodes, len);
        XFlush(display);
        nanosleep(&ts, NULL);
        goto cleanup_and_quit;
    } else {
        for (int i = 1; i < argc; i++) {
            write_string(argv[i]);
            XFlush(display);
            nanosleep(&ts, NULL);
        }
        goto cleanup_and_quit;
    }

cleanup_and_quit: 
    XCloseDisplay(display);
    return 0;
}
