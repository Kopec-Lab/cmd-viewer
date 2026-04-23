from __future__ import annotations

import curses

import numpy as np

from cmd_viewer.camera import Camera
from cmd_viewer.colors import visual_for_atom
from cmd_viewer.representations import FramePayload


SHADE_RAMP = " .:-=+*#%@"


class TerminalRenderer:
    def __init__(self, color_mode: str) -> None:
        self.color_mode = color_mode

    def init_colors(self) -> None:
        if not curses.has_colors():
            return
        curses.start_color()
        curses.use_default_colors()
        color_pairs = {
            1: curses.COLOR_CYAN,
            2: curses.COLOR_YELLOW,
            3: curses.COLOR_MAGENTA,
            4: curses.COLOR_BLUE,
            5: curses.COLOR_GREEN,
            6: curses.COLOR_WHITE,
            7: curses.COLOR_CYAN,
            8: curses.COLOR_RED,
            9: curses.COLOR_MAGENTA,
            10: curses.COLOR_GREEN,
            11: curses.COLOR_YELLOW,
            12: curses.COLOR_CYAN,
            13: curses.COLOR_BLUE,
            14: curses.COLOR_WHITE,
        }
        for pair_id, fg in color_pairs.items():
            curses.init_pair(pair_id, fg, -1)

    def draw(
        self,
        screen: "curses.window",
        camera: Camera,
        payload: FramePayload,
        header_lines: list[str],
        footer_lines: list[str],
        show_box: bool,
    ) -> None:
        screen.erase()
        total_height, total_width = screen.getmaxyx()
        view_top = len(header_lines)
        view_height = max(total_height - len(header_lines) - len(footer_lines), 1)
        view_width = max(total_width, 1)

        transformed_points = camera.transform(payload.point_positions, center=payload.center)
        transformed_line_starts = camera.transform(payload.line_starts, center=payload.center)
        transformed_line_ends = camera.transform(payload.line_ends, center=payload.center)
        transformed_box = None
        if show_box and payload.box_corners is not None:
            transformed_box = camera.transform(payload.box_corners, center=payload.center)

        max_extent = float(np.abs(transformed_points[:, :2]).max()) if len(transformed_points) else 1.0
        if len(transformed_line_starts):
            max_extent = max(max_extent, float(np.abs(transformed_line_starts[:, :2]).max()))
            max_extent = max(max_extent, float(np.abs(transformed_line_ends[:, :2]).max()))
        if transformed_box is not None and len(transformed_box):
            max_extent = max(max_extent, float(np.abs(transformed_box[:, :2]).max()))
        max_extent = max(max_extent, 1e-6)
        scale = min(view_width, view_height) * 0.45 * camera.zoom / max_extent

        depth_buffer = np.full((view_height, view_width), -np.inf, dtype=float)
        char_buffer = np.full((view_height, view_width), " ", dtype="<U1")
        color_buffer = np.zeros((view_height, view_width), dtype=int)

        z_min = float(transformed_points[:, 2].min()) if len(transformed_points) else 0.0
        z_max = float(transformed_points[:, 2].max()) if len(transformed_points) else 1.0
        if len(transformed_line_starts):
            z_min = min(z_min, float(transformed_line_starts[:, 2].min()))
            z_min = min(z_min, float(transformed_line_ends[:, 2].min()))
            z_max = max(z_max, float(transformed_line_starts[:, 2].max()))
            z_max = max(z_max, float(transformed_line_ends[:, 2].max()))
        if transformed_box is not None and len(transformed_box):
            z_min = min(z_min, float(transformed_box[:, 2].min()))
            z_max = max(z_max, float(transformed_box[:, 2].max()))
        z_span = max(z_max - z_min, 1e-6)

        if transformed_box is not None:
            self._draw_box(
                transformed_box=transformed_box,
                scale=scale,
                depth_buffer=depth_buffer,
                char_buffer=char_buffer,
                color_buffer=color_buffer,
                width=view_width,
                height=view_height,
                camera=camera,
            )

        self._draw_lines(
            transformed_line_starts=transformed_line_starts,
            transformed_line_ends=transformed_line_ends,
            line_chars=payload.line_chars,
            line_color_ids=payload.line_color_ids,
            scale=scale,
            depth_buffer=depth_buffer,
            char_buffer=char_buffer,
            color_buffer=color_buffer,
            width=view_width,
            height=view_height,
            camera=camera,
        )

        for index, point in enumerate(transformed_points):
            x, y = self._project_point(point, scale, view_width, view_height, camera)
            if x < 0 or x >= view_width or y < 0 or y >= view_height:
                continue
            depth = float(point[2])
            if depth < depth_buffer[y, x]:
                continue
            shade_index = int((depth - z_min) / z_span * (len(SHADE_RAMP) - 1))
            visual = visual_for_atom(
                self.color_mode,
                payload.point_resnames[index],
                payload.point_elements[index],
                payload.point_resids[index],
            )
            point_char = (
                payload.point_chars[index]
                if payload.point_chars is not None
                else (visual.char if self.color_mode in {"class", "resid"} else SHADE_RAMP[shade_index])
            )
            self._draw_point_marker(
                x=x,
                y=y,
                depth=depth,
                char=point_char,
                color_id=visual.color_id,
                footprint=visual.footprint,
                depth_buffer=depth_buffer,
                char_buffer=char_buffer,
                color_buffer=color_buffer,
            )

        if len(payload.overlay_positions):
            transformed_overlays = camera.transform(payload.overlay_positions, center=payload.center)
            for index, point in enumerate(transformed_overlays):
                x, y = self._project_point(point, scale, view_width, view_height, camera)
                self._draw_point_marker(
                    x=x,
                    y=y,
                    depth=float(point[2]),
                    char=payload.overlay_chars[index],
                    color_id=payload.overlay_color_ids[index],
                    footprint=0,
                    depth_buffer=depth_buffer,
                    char_buffer=char_buffer,
                    color_buffer=color_buffer,
                )

        for row_index, line in enumerate(header_lines):
            self._safe_addstr(screen, row_index, 0, line[:view_width])

        for y in range(view_height):
            for x in range(view_width):
                char = char_buffer[y, x]
                if char == " ":
                    continue
                color_id = color_buffer[y, x]
                attr = curses.color_pair(color_id) if color_id else curses.A_NORMAL
                self._safe_addstr(screen, view_top + y, x, char, attr)

        self._draw_axes_overlay(
            screen=screen,
            camera=camera,
            top=view_top,
            width=view_width,
            height=view_height,
        )

        footer_top = view_top + view_height
        for offset, line in enumerate(footer_lines):
            self._safe_addstr(screen, footer_top + offset, 0, line[:view_width])

        screen.refresh()

    def _draw_lines(
        self,
        transformed_line_starts: np.ndarray,
        transformed_line_ends: np.ndarray,
        line_chars: list[str],
        line_color_ids: list[int],
        scale: float,
        depth_buffer: np.ndarray,
        char_buffer: np.ndarray,
        color_buffer: np.ndarray,
        width: int,
        height: int,
        camera: Camera,
    ) -> None:
        for index, start in enumerate(transformed_line_starts):
            end = transformed_line_ends[index]
            start_x, start_y = self._project_point(start, scale, width, height, camera)
            end_x, end_y = self._project_point(end, scale, width, height, camera)
            projected_start = (start_x, start_y, float(start[2]))
            projected_end = (end_x, end_y, float(end[2]))
            line_char = line_chars[index]
            if line_char == "auto":
                line_char = self._cartoon_line_char(start_x, start_y, end_x, end_y)
            elif line_char == "helix":
                line_char = "@" if abs(end_x - start_x) + abs(end_y - start_y) > 1 else "o"
            elif line_char == "sheet":
                line_char = self._sheet_line_char(start_x, start_y, end_x, end_y)
            self._raster_line(
                start=projected_start,
                end=projected_end,
                depth_buffer=depth_buffer,
                char_buffer=char_buffer,
                color_buffer=color_buffer,
                char=line_char,
                color_id=line_color_ids[index],
            )

    def _draw_box(
        self,
        transformed_box: np.ndarray,
        scale: float,
        depth_buffer: np.ndarray,
        char_buffer: np.ndarray,
        color_buffer: np.ndarray,
        width: int,
        height: int,
        camera: Camera,
    ) -> None:
        projected = []
        for point in transformed_box:
            x, y = self._project_point(point, scale, width, height, camera)
            projected.append(
                (
                    x,
                    y,
                    float(point[2]),
                )
            )

        edges = (
            (0, 1), (0, 2), (0, 4),
            (1, 3), (1, 5),
            (2, 3), (2, 6),
            (3, 7),
            (4, 5), (4, 6),
            (5, 7),
            (6, 7),
        )
        for start, end in edges:
            self._raster_line(
                start=projected[start],
                end=projected[end],
                depth_buffer=depth_buffer,
                char_buffer=char_buffer,
                color_buffer=color_buffer,
                char=":",
                color_id=6,
            )
        for x, y, depth in projected:
            if 0 <= x < width and 0 <= y < height and depth >= depth_buffer[y, x]:
                char_buffer[y, x] = "+"
                color_buffer[y, x] = 6
                depth_buffer[y, x] = depth

    def _draw_axes_overlay(
        self,
        screen: "curses.window",
        camera: Camera,
        top: int,
        width: int,
        height: int,
    ) -> None:
        origin_x = min(width - 5, width - 1)
        origin_y = min(top + 4, top + height - 1)
        if origin_x < 2 or origin_y < top:
            return

        axis_vectors = camera.transform_vectors(
            np.array(
                [
                    [1.0, 0.0, 0.0],
                    [0.0, 1.0, 0.0],
                    [0.0, 0.0, 1.0],
                ]
            )
        )
        labels = (("x", 8), ("y", 5), ("z", 7))
        self._safe_addstr(screen, origin_y, origin_x, "+")
        for index, (label, color_id) in enumerate(labels):
            dx = int(round(axis_vectors[index, 0] * 3.0))
            dy = int(round(axis_vectors[index, 1] * 2.0))
            tip_x = origin_x + dx
            tip_y = origin_y + dy
            self._draw_screen_line(
                screen=screen,
                start=(origin_x, origin_y),
                end=(tip_x, tip_y),
                char=".",
                color_id=color_id,
                skip_start=True,
            )
            if top <= tip_y < top + height and 0 <= tip_x < width:
                self._safe_addstr(screen, tip_y, tip_x, label, curses.color_pair(color_id))

    @staticmethod
    def _safe_addstr(
        screen: "curses.window",
        y: int,
        x: int,
        text: str,
        attr: int = 0,
    ) -> None:
        try:
            screen.addstr(y, x, text, attr)
        except curses.error:
            return

    @staticmethod
    def _line_points(start: tuple[int, int], end: tuple[int, int]) -> list[tuple[int, int]]:
        x0, y0 = start
        x1, y1 = end
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        error = dx + dy
        points: list[tuple[int, int]] = []
        while True:
            points.append((x0, y0))
            if x0 == x1 and y0 == y1:
                break
            twice_error = 2 * error
            if twice_error >= dy:
                error += dy
                x0 += sx
            if twice_error <= dx:
                error += dx
                y0 += sy
        return points

    def _raster_line(
        self,
        start: tuple[int, int, float],
        end: tuple[int, int, float],
        depth_buffer: np.ndarray,
        char_buffer: np.ndarray,
        color_buffer: np.ndarray,
        char: str,
        color_id: int,
    ) -> None:
        points = self._line_points((start[0], start[1]), (end[0], end[1]))
        if not points:
            return
        start_depth = start[2]
        end_depth = end[2]
        height, width = depth_buffer.shape
        denominator = max(len(points) - 1, 1)
        for index, (x, y) in enumerate(points):
            if x < 0 or x >= width or y < 0 or y >= height:
                continue
            depth = start_depth + (end_depth - start_depth) * (index / denominator)
            if depth < depth_buffer[y, x]:
                continue
            char_buffer[y, x] = char
            color_buffer[y, x] = color_id
            depth_buffer[y, x] = depth

    def _draw_point_marker(
        self,
        x: int,
        y: int,
        depth: float,
        char: str,
        color_id: int,
        footprint: int,
        depth_buffer: np.ndarray,
        char_buffer: np.ndarray,
        color_buffer: np.ndarray,
    ) -> None:
        self._plot_marker_cell(x, y, depth, char, color_id, depth_buffer, char_buffer, color_buffer)
        if footprint <= 0:
            return
        for offset_x, offset_y in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            self._plot_marker_cell(
                x + offset_x,
                y + offset_y,
                depth,
                char,
                color_id,
                depth_buffer,
                char_buffer,
                color_buffer,
            )

    @staticmethod
    def _plot_marker_cell(
        x: int,
        y: int,
        depth: float,
        char: str,
        color_id: int,
        depth_buffer: np.ndarray,
        char_buffer: np.ndarray,
        color_buffer: np.ndarray,
    ) -> None:
        height, width = depth_buffer.shape
        if x < 0 or x >= width or y < 0 or y >= height:
            return
        if depth < depth_buffer[y, x]:
            return
        char_buffer[y, x] = char
        color_buffer[y, x] = color_id
        depth_buffer[y, x] = depth

    def _draw_screen_line(
        self,
        screen: "curses.window",
        start: tuple[int, int],
        end: tuple[int, int],
        char: str,
        color_id: int,
        skip_start: bool = False,
    ) -> None:
        points = self._line_points(start, end)
        if skip_start and points:
            points = points[1:]
        attr = curses.color_pair(color_id) if color_id else curses.A_NORMAL
        for x, y in points:
            self._safe_addstr(screen, y, x, char, attr)

    @staticmethod
    def _project_point(
        point: np.ndarray,
        scale: float,
        width: int,
        height: int,
        camera: Camera,
    ) -> tuple[int, int]:
        x = int(round(point[0] * scale + (width - 1) / 2 + camera.pan_x))
        y = int(round(point[1] * scale + (height - 1) / 2 + camera.pan_y))
        return x, y

    @staticmethod
    def _cartoon_line_char(start_x: int, start_y: int, end_x: int, end_y: int) -> str:
        dx = end_x - start_x
        dy = end_y - start_y
        abs_dx = abs(dx)
        abs_dy = abs(dy)
        if abs_dx >= abs_dy * 2:
            return "="
        if abs_dy >= abs_dx * 2:
            return "|"
        if dx == 0 or dy == 0:
            return "+" if dx == 0 and dy == 0 else ("=" if abs_dx >= abs_dy else "|")
        return "/" if (dx > 0) ^ (dy > 0) else "\\"

    @staticmethod
    def _sheet_line_char(start_x: int, start_y: int, end_x: int, end_y: int) -> str:
        dx = end_x - start_x
        dy = end_y - start_y
        abs_dx = abs(dx)
        abs_dy = abs(dy)
        if abs_dx >= abs_dy * 1.5:
            return ">" if dx >= 0 else "<"
        if abs_dy >= abs_dx * 1.5:
            return "v" if dy >= 0 else "^"
        return ">" if dx >= 0 else "<"
