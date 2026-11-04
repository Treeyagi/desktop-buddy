// Desktop Buddy window reporter, loaded into KWin by desktop-awareness/windows.py.
// On Wayland apps can't see each other's windows, but KWin can: this sends the
// buddy a JSON snapshot of the real windows (bottom to top) whenever anything
// changes. It only reads; it never moves or changes a window.
const SERVICE = "org.desktopbuddy.Windows";
const PATH = "/Windows";
const IFACE = "org.desktopbuddy.Windows";

function onCurrentDesktop(w) {
    if (w.onAllDesktops) return true;
    const cur = workspace.currentDesktop;
    for (let i = 0; i < w.desktops.length; i++) {
        if (w.desktops[i] === cur) return true;
    }
    return false;
}

function snapshot() {
    const order = workspace.stackingOrder;
    const out = [];
    for (let i = 0; i < order.length; i++) {
        const w = order[i];
        if (!(w.normalWindow || w.dialog)) continue;
        // skip the buddy's own see-through overlays (KWin lists them like windows)
        const cls = String(w.resourceClass);
        if (w.caption === "Desktop Buddy overlay" || (w.caption === "" && cls.indexOf("python") === 0)) continue;
        const g = w.frameGeometry;
        out.push({
            id: String(w.internalId),
            title: String(w.caption),
            app: String(w.resourceClass),
            x: g.x, y: g.y, w: g.width, h: g.height,
            minimized: !!w.minimized,
            fullscreen: !!w.fullScreen,
            active: w === workspace.activeWindow,
            output: w.output ? String(w.output.name) : "",
            here: onCurrentDesktop(w),
            z: i,
        });
    }
    callDBus(SERVICE, PATH, IFACE, "Update", JSON.stringify(out));
}

function watch(w) {
    w.frameGeometryChanged.connect(snapshot);
    w.captionChanged.connect(snapshot);
    w.minimizedChanged.connect(snapshot);
    w.fullScreenChanged.connect(snapshot);
    w.outputChanged.connect(snapshot);
}

workspace.windowList().forEach(watch);
workspace.windowAdded.connect(function (w) { watch(w); snapshot(); });
workspace.windowRemoved.connect(snapshot);
workspace.windowActivated.connect(snapshot);
workspace.currentDesktopChanged.connect(snapshot);
if (workspace.stackingOrderChanged) workspace.stackingOrderChanged.connect(snapshot);  // not in every KWin
snapshot();

// The mouse cursor, for his squirrel moments: at most about 15 updates a second.
let lastCursor = 0;
if (workspace.cursorPosChanged) {
    workspace.cursorPosChanged.connect(function () {
        const now = Date.now();
        if (now - lastCursor < 66) return;
        lastCursor = now;
        const p = workspace.cursorPos;
        callDBus(SERVICE, PATH, IFACE, "Cursor", p.x, p.y);
    });
}
