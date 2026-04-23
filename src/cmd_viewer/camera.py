from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass(slots=True)
class Camera:
    zoom: float = 1.0
    pan_x: float = 0.0
    pan_y: float = 0.0
    _rotation: np.ndarray = field(default_factory=lambda: _default_rotation(), repr=False)

    def reset(self) -> None:
        self.zoom = 1.0
        self.pan_x = 0.0
        self.pan_y = 0.0
        self._rotation = _default_rotation()

    def rotate(
        self,
        delta_yaw: float = 0.0,
        delta_pitch: float = 0.0,
        delta_roll: float = 0.0,
    ) -> None:
        if delta_yaw:
            self._rotation = self._rotation @ _rotation_y(delta_yaw)
        if delta_pitch:
            self._rotation = self._rotation @ _rotation_x(delta_pitch)
        if delta_roll:
            self._rotation = self._rotation @ _rotation_z(delta_roll)
        self._rotation = _orthonormalize(self._rotation)

    def change_zoom(self, scale: float) -> None:
        self.zoom = float(np.clip(self.zoom * scale, 0.2, 32.0))

    def translate(self, delta_x: float = 0.0, delta_y: float = 0.0) -> None:
        self.pan_x += delta_x
        self.pan_y += delta_y

    def rotation_matrix(self) -> np.ndarray:
        return self._rotation

    def transform(
        self,
        positions: np.ndarray,
        center: np.ndarray | None = None,
    ) -> np.ndarray:
        if center is None:
            center = positions.mean(axis=0, keepdims=True)
        centered = positions - center
        return centered @ self.rotation_matrix()

    def transform_vectors(self, vectors: np.ndarray) -> np.ndarray:
        return vectors @ self.rotation_matrix()


def _rotation_x(angle: float) -> np.ndarray:
    cos_angle = np.cos(angle)
    sin_angle = np.sin(angle)
    return np.array(
        [
            [1.0, 0.0, 0.0],
            [0.0, cos_angle, -sin_angle],
            [0.0, sin_angle, cos_angle],
        ]
    )


def _rotation_y(angle: float) -> np.ndarray:
    cos_angle = np.cos(angle)
    sin_angle = np.sin(angle)
    return np.array(
        [
            [cos_angle, 0.0, sin_angle],
            [0.0, 1.0, 0.0],
            [-sin_angle, 0.0, cos_angle],
        ]
    )


def _rotation_z(angle: float) -> np.ndarray:
    cos_angle = np.cos(angle)
    sin_angle = np.sin(angle)
    return np.array(
        [
            [cos_angle, -sin_angle, 0.0],
            [sin_angle, cos_angle, 0.0],
            [0.0, 0.0, 1.0],
        ]
    )


def _default_rotation() -> np.ndarray:
    return _rotation_y(0.55) @ _rotation_x(-0.35)


def _orthonormalize(matrix: np.ndarray) -> np.ndarray:
    u, _, vh = np.linalg.svd(matrix)
    rotation = u @ vh
    if np.linalg.det(rotation) < 0:
        u[:, -1] *= -1.0
        rotation = u @ vh
    return rotation
