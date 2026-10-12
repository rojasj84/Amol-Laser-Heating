"""Mouse editing of camera ROIs, independent of Tk widgets and fitting."""
from dataclasses import dataclass

from matplotlib.backend_bases import MouseButton
from matplotlib.patches import Rectangle
import numpy as np

from laser_heating.models import RegionOfInterest


@dataclass(frozen=True)
class _Drag:
    side: str
    handle: str
    origin: tuple[float, float]
    roi: RegionOfInterest


class ROIDragController:
    """Pick handles in screen pixels; edit integer, exclusive image bounds.

    The callback receives preview changes. Applying them to analysis remains
    the editor's responsibility. Each drag starts from an immutable snapshot,
    preventing accumulated rounding errors or a jump when picking near an edge.
    """

    HIT_RADIUS = 9
    COLORS = {"left": "limegreen", "right": "tomato"}

    def __init__(self, axes, width, height, on_change, on_hover):
        self.axes = axes
        self.canvas = axes.figure.canvas
        self.width, self.height = width, height
        self.on_change, self.on_hover = on_change, on_hover
        self.rois = {}
        self.active_side = "left"
        self._drag = None
        self._hover = None
        self.rectangles = {}
        self.handles = {}
        for side, color in self.COLORS.items():
            rectangle = Rectangle((0, 0), 1, 1, linewidth=2, edgecolor=color,
                                  facecolor="none", linestyle="--", zorder=3)
            axes.add_patch(rectangle)
            self.rectangles[side] = rectangle
            self.handles[side], = axes.plot([], [], linestyle="none", marker="s",
                                            markersize=7, markeredgecolor=color,
                                            markerfacecolor="white", zorder=4)
        self._connections = [
            self.canvas.mpl_connect("button_press_event", self._press),
            self.canvas.mpl_connect("motion_notify_event", self._motion),
            self.canvas.mpl_connect("button_release_event", self._release),
            self.canvas.mpl_connect("figure_leave_event", self._leave),
        ]

    @staticmethod
    def _positions(roi):
        x0, x1, y0, y1 = roi.x_start, roi.x_end, roi.y_start, roi.y_end
        xm, ym = (x0+x1)/2, (y0+y1)/2
        return {"top_left": (x0, y0), "top_right": (x1, y0),
                "bottom_right": (x1, y1), "bottom_left": (x0, y1),
                "top": (xm, y0), "right": (x1, ym),
                "bottom": (xm, y1), "left": (x0, ym)}

    def set_rois(self, rois):
        for roi in rois.values():
            roi.validate(self.width, self.height)
        self.rois = dict(rois)
        self._draw()

    def select_side(self, side):
        if side not in self.COLORS:
            raise ValueError(f"Unknown ROI side {side!r}")
        self.active_side = side
        self._draw()

    def _draw(self):
        for side, rectangle in self.rectangles.items():
            roi = self.rois.get(side)
            rectangle.set_visible(roi is not None)
            self.handles[side].set_visible(roi is not None)
            if roi is None:
                continue
            rectangle.set_bounds(roi.x_start, roi.y_start,
                                 roi.x_end-roi.x_start, roi.y_end-roi.y_start)
            rectangle.set_linewidth(2.8 if side == self.active_side else 1.8)
            rectangle.set_zorder(5 if side == self.active_side else 3)
            points = tuple(self._positions(roi).values())
            self.handles[side].set_data(*zip(*points))
            self.handles[side].set_zorder(6 if side == self.active_side else 4)
        self.canvas.draw_idle()

    def _point(self, event):
        if event.x is None or event.y is None:
            return None
        point = self.axes.transData.inverted().transform((event.x, event.y))
        return tuple(point) if np.all(np.isfinite(point)) else None

    def _hit_test(self, event):
        if event.inaxes is not self.axes:
            return None
        sides = sorted(self.rois, key=lambda side: side != self.active_side)
        # Handles take precedence over edges or an overlapping rectangle's body.
        closest, distance = None, self.HIT_RADIUS**2
        for side in sides:
            for handle, point in self._positions(self.rois[side]).items():
                screen = self.axes.transData.transform(point)
                candidate = float(np.sum((screen-(event.x, event.y))**2))
                if candidate < distance:
                    closest, distance = (side, handle), candidate
        if closest is not None:
            return closest
        for side in sides:
            roi = self.rois[side]
            a = self.axes.transData.transform((roi.x_start, roi.y_start))
            b = self.axes.transData.transform((roi.x_end, roi.y_end))
            xmin, xmax = sorted((a[0], b[0]))
            ymin, ymax = sorted((a[1], b[1]))
            edges = []
            if xmin <= event.x <= xmax:
                edges += [(abs(event.y-a[1]), "top"), (abs(event.y-b[1]), "bottom")]
            if ymin <= event.y <= ymax:
                edges += [(abs(event.x-a[0]), "left"), (abs(event.x-b[0]), "right")]
            for candidate, handle in edges:
                if candidate**2 < distance:
                    closest, distance = (side, handle), candidate**2
        if closest is not None:
            return closest
        point = self._point(event)
        if point is not None:
            x, y = point
            for side in sides:
                roi = self.rois[side]
                if roi.x_start < x < roi.x_end and roi.y_start < y < roi.y_end:
                    return side, "move"
        return None

    def _set_hover(self, target):
        if target != self._hover:
            self._hover = target
            self.on_hover(*(target if target is not None else (None, None)))

    def _press(self, event):
        if event.button != MouseButton.LEFT:
            return
        target, point = self._hit_test(event), self._point(event)
        if target is None or point is None:
            return
        side, handle = target
        self.select_side(side)
        self._drag = _Drag(side, handle, point, self.rois[side])
        self._set_hover(target)

    def _motion(self, event):
        if self._drag is None:
            self._set_hover(self._hit_test(event))
            return
        point = self._point(event)
        if point is None:
            return
        drag = self._drag
        dx, dy = (int(round(value-origin)) for value, origin in zip(point, drag.origin))
        roi = drag.roi
        x0, x1, y0, y1 = roi.x_start, roi.x_end, roi.y_start, roi.y_end
        if drag.handle == "move":
            dx = max(-x0, min(dx, self.width-x1))
            dy = max(-y0, min(dy, self.height-y1))
            x0, x1, y0, y1 = x0+dx, x1+dx, y0+dy, y1+dy
        else:
            if "left" in drag.handle:
                x0 = max(0, min(x0+dx, x1-1))
            if "right" in drag.handle:
                x1 = min(self.width, max(x1+dx, x0+1))
            if "top" in drag.handle:
                y0 = max(0, min(y0+dy, y1-1))
            if "bottom" in drag.handle:
                y1 = min(self.height, max(y1+dy, y0+1))
        updated = RegionOfInterest(x0, x1, y0, y1)
        if updated != self.rois.get(drag.side):
            self.rois[drag.side] = updated
            self._draw()
            self.on_change(drag.side, updated)

    def _release(self, event):
        if event.button in (None, MouseButton.LEFT):
            self._drag = None
            self._set_hover(self._hit_test(event))

    def _leave(self, event):
        if self._drag is None:
            self._set_hover(None)

    def disconnect(self):
        for connection in self._connections:
            self.canvas.mpl_disconnect(connection)
        self._connections.clear()
        self._drag = None
        self._set_hover(None)
