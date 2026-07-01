/* ItayPhone home bar — an always-on-top Wayland layer-shell strip that sits at
 * the bottom of the phone frame and floats OVER everything (incl. Android apps).
 * Swipe up (mouse-drag or touch) => "home": close the foreground Android app so
 * the ItayPhone launcher underneath re-appears.
 *
 * Geometry is env-overridable so it fits both the dev monitor (phone frame) and
 * a real fullscreen phone display:
 *   HB_LEFT  (px from left, default 60)      HB_BOTTOM (px from bottom, def 320)
 *   HB_W     (bar width, default 360)        HB_H      (bar height, default 30)
 *   HB_FULL=1  -> stretch full width, sit on the very bottom (real phone)
 *
 * Build: gcc itayhome.c -o itayhome $(pkg-config --cflags --libs gtk+-3.0 gtk-layer-shell-0) -lm
 */
#include <gtk/gtk.h>
#include <gtk-layer-shell.h>
#include <stdlib.h>
#include <math.h>

static double press_y = -1;

static void run_home(void) {
    system("/home/itay/itayhome-action.sh >/dev/null 2>&1 &");
}

static gboolean on_press(GtkWidget *w, GdkEventButton *e, gpointer d) {
    press_y = e->y_root;
    return TRUE;
}
static gboolean on_release(GtkWidget *w, GdkEventButton *e, gpointer d) {
    if (press_y >= 0 && (press_y - e->y_root) > 22.0) run_home();
    press_y = -1;
    return TRUE;
}
static gboolean on_touch(GtkWidget *w, GdkEvent *ev, gpointer d) {
    GdkEventTouch *t = (GdkEventTouch *) ev;
    if (ev->type == GDK_TOUCH_BEGIN) { press_y = t->y_root; return TRUE; }
    if (ev->type == GDK_TOUCH_END || ev->type == GDK_TOUCH_CANCEL) {
        if (press_y >= 0 && (press_y - t->y_root) > 22.0) run_home();
        press_y = -1;
        return TRUE;
    }
    return FALSE;
}

static gboolean on_draw(GtkWidget *w, cairo_t *cr, gpointer d) {
    int width  = gtk_widget_get_allocated_width(w);
    int height = gtk_widget_get_allocated_height(w);
    /* faint bar strip (also guarantees the input region covers the whole bar) */
    cairo_set_source_rgba(cr, 0.0, 0.0, 0.0, 0.16);
    cairo_paint(cr);
    /* the iOS-style home pill, centred near the bottom */
    double pw = width * 0.36, ph = 5.0;
    double px = (width - pw) / 2.0, py = height - ph - 6.0, r = ph / 2.0;
    cairo_set_source_rgba(cr, 0.92, 0.94, 0.98, 0.85);
    cairo_new_sub_path(cr);
    cairo_arc(cr, px + r,      py + r, r,   M_PI/2.0, 3.0*M_PI/2.0);
    cairo_arc(cr, px + pw - r, py + r, r, 3.0*M_PI/2.0,     M_PI/2.0);
    cairo_close_path(cr);
    cairo_fill(cr);
    return FALSE;
}

int main(int argc, char **argv) {
    gtk_init(&argc, &argv);

    int mleft = 60, mbottom = 320, bar_w = 360, bar_h = 30, full = 0;
    char *e;
    if ((e = getenv("HB_LEFT")))   mleft   = atoi(e);
    if ((e = getenv("HB_BOTTOM"))) mbottom = atoi(e);
    if ((e = getenv("HB_W")))      bar_w   = atoi(e);
    if ((e = getenv("HB_H")))      bar_h   = atoi(e);
    if ((e = getenv("HB_FULL")))   full    = atoi(e);

    GtkWidget *win = gtk_window_new(GTK_WINDOW_TOPLEVEL);
    gtk_widget_set_app_paintable(win, TRUE);
    GdkVisual *vis = gdk_screen_get_rgba_visual(gtk_widget_get_screen(win));
    if (vis) gtk_widget_set_visual(win, vis);

    gtk_layer_init_for_window(GTK_WINDOW(win));
    gtk_layer_set_layer(GTK_WINDOW(win), GTK_LAYER_SHELL_LAYER_OVERLAY);
    gtk_layer_set_namespace(GTK_WINDOW(win), "itayhome");
    gtk_layer_set_keyboard_mode(GTK_WINDOW(win), GTK_LAYER_SHELL_KEYBOARD_MODE_NONE);
    gtk_layer_set_anchor(GTK_WINDOW(win), GTK_LAYER_SHELL_EDGE_BOTTOM, TRUE);
    if (full) {
        gtk_layer_set_anchor(GTK_WINDOW(win), GTK_LAYER_SHELL_EDGE_LEFT, TRUE);
        gtk_layer_set_anchor(GTK_WINDOW(win), GTK_LAYER_SHELL_EDGE_RIGHT, TRUE);
        bar_w = 0; /* let it stretch */
    } else {
        gtk_layer_set_anchor(GTK_WINDOW(win), GTK_LAYER_SHELL_EDGE_LEFT, TRUE);
        gtk_layer_set_margin(GTK_WINDOW(win), GTK_LAYER_SHELL_EDGE_LEFT, mleft);
    }
    gtk_layer_set_margin(GTK_WINDOW(win), GTK_LAYER_SHELL_EDGE_BOTTOM, mbottom);

    gtk_widget_set_size_request(win, bar_w, bar_h);
    gtk_widget_add_events(win, GDK_BUTTON_PRESS_MASK | GDK_BUTTON_RELEASE_MASK | GDK_TOUCH_MASK);
    g_signal_connect(win, "button-press-event",   G_CALLBACK(on_press),   NULL);
    g_signal_connect(win, "button-release-event", G_CALLBACK(on_release), NULL);
    g_signal_connect(win, "touch-event",          G_CALLBACK(on_touch),   NULL);
    g_signal_connect(win, "draw",                 G_CALLBACK(on_draw),    NULL);

    gtk_widget_show_all(win);
    gtk_main();
    return 0;
}
