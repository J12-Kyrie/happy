from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import List

from PySide6.QtCore import QPointF, QTimer, Qt
from PySide6.QtGui import QColor, QPainter, QPaintEvent
from PySide6.QtWidgets import QWidget


@dataclass
class Snowflake:
    position: QPointF
    radius: float
    velocity_y: float
    drift: float
    opacity: float


class SnowEffect(QWidget):
    def __init__(self, parent=None, flake_count: int = 70) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.flake_count = flake_count
        self.flakes: List[Snowflake] = []
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_flakes)
        self.timer.start(40)

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self._init_flakes()

    def _init_flakes(self) -> None:
        self.flakes = []
        width = max(1, self.width())
        height = max(1, self.height())
        for _ in range(self.flake_count):
            self.flakes.append(
                Snowflake(
                    position=QPointF(random.uniform(0, width), random.uniform(0, height)),
                    radius=random.uniform(1.5, 4.5),
                    velocity_y=random.uniform(0.6, 1.8),
                    drift=random.uniform(-0.5, 0.5),
                    opacity=random.uniform(0.25, 0.65),
                )
            )

    def _update_flakes(self) -> None:
        if not self.flakes:
            self._init_flakes()
        width = self.width()
        height = self.height()
        for flake in self.flakes:
            x = flake.position.x() + flake.drift
            y = flake.position.y() + flake.velocity_y
            if y > height:
                y = -flake.radius
                x = random.uniform(0, width)
            if x > width:
                x = 0
            if x < 0:
                x = width
            flake.position = QPointF(x, y)
        self.update()

    def pause(self) -> None:
        self.timer.stop()

    def resume(self) -> None:
        if not self.timer.isActive():
            self.timer.start(40)

    def paintEvent(self, event: QPaintEvent) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        for flake in self.flakes:
            color = QColor(255, 255, 255)
            color.setAlphaF(flake.opacity)
            painter.setBrush(color)
            painter.drawEllipse(flake.position, flake.radius, flake.radius)


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: float
    color: QColor
    trail: List[QPointF] = field(default_factory=list)


@dataclass
class RocketParticle:
    x: float
    y: float
    target_y: float
    vx: float
    vy: float
    color: QColor
    burst_config: dict = field(default_factory=dict)
    trail: List[QPointF] = field(default_factory=list)


class FireworksOverlay(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.particles: List[Particle] = []
        self.rockets: List[RocketParticle] = []
        self.active = False
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.setInterval(16)

    def trigger(
        self,
        base_color: QColor,
        center: QPointF | None = None,
        simultaneous: bool = False,
        bursts: int | None = None,
        particle_count: int | None = None,
        launch_from_bottom: bool = True,
    ) -> None:
        self.active = True
        self.particles = []
        self.rockets = []
        width = self.width()
        height = self.height()

        if center is None:
            center_x = width / 2
            center_y = height / 2
        else:
            center_x = max(0.0, min(width, center.x()))
            center_y = max(0.0, min(height, center.y()))

        total_bursts = bursts if bursts is not None else (6 if simultaneous else 4)

        if launch_from_bottom:
            for _ in range(total_bursts):
                hue_shift = random.randint(-20, 20)
                color = QColor(base_color)
                h, s, v, a = color.getHsv()
                color.setHsv((h + hue_shift) % 360, min(255, s + 30), v, a)

                start_x = center_x + random.uniform(-width * 0.15, width * 0.15)
                start_y = height + 10
                target_y = center_y + random.uniform(-height * 0.1, height * 0.1)

                launch_speed = random.uniform(12.0, 16.0)
                default_count = 80 if simultaneous else 160
                count = particle_count if particle_count is not None else default_count

                self.rockets.append(
                    RocketParticle(
                        x=start_x,
                        y=start_y,
                        target_y=target_y,
                        vx=random.uniform(-0.5, 0.5),
                        vy=-launch_speed,
                        color=color,
                        burst_config={
                            "count": count,
                            "simultaneous": simultaneous,
                        },
                        trail=[QPointF(start_x, start_y)],
                    )
                )
        else:
            base_radius = max(220.0, min(width, height) * 0.35)
            for _ in range(total_bursts):
                hue_shift = random.randint(-20, 20)
                color = QColor(base_color)
                h, s, v, a = color.getHsv()
                color.setHsv((h + hue_shift) % 360, min(255, s + 30), v, a)
                default_count = 80 if simultaneous else 160
                count = particle_count if particle_count is not None else default_count
                for i in range(count):
                    angle = (math.pi * 2 / count) * i
                    speed = random.uniform(18.0, 26.0) if simultaneous else random.uniform(12.0, 18.0)
                    vx = math.cos(angle) * speed
                    vy = math.sin(angle) * speed
                    origin_x = center_x + math.cos(angle) * random.uniform(0, base_radius) * 0.28
                    origin_y = center_y + math.sin(angle) * random.uniform(0, base_radius) * 0.28
                    origin_x += random.uniform(-20, 20)
                    origin_y += random.uniform(-20, 20)
                    self.particles.append(
                        Particle(
                            x=origin_x,
                            y=origin_y,
                            vx=vx,
                            vy=vy,
                            life=random.uniform(0.55, 0.85),
                            color=color,
                            trail=[QPointF(origin_x, origin_y)],
                        )
                    )

        self.timer.start()
        self.show()
        self.raise_()
        self.update()

    def _tick(self) -> None:
        alive_rockets: List[RocketParticle] = []
        for rocket in self.rockets:
            rocket.x += rocket.vx
            rocket.y += rocket.vy
            rocket.vy += 0.08

            rocket.trail.append(QPointF(rocket.x, rocket.y))
            if len(rocket.trail) > 10:
                rocket.trail.pop(0)

            if rocket.y <= rocket.target_y:
                self._explode_rocket(rocket)
            else:
                alive_rockets.append(rocket)

        self.rockets = alive_rockets

        gravity = 0.24
        damping = 0.86
        dt = 0.016
        alive_particles: List[Particle] = []
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.vy += gravity
            p.vx *= damping
            p.vy *= damping
            p.life -= dt
            p.trail.append(QPointF(p.x, p.y))
            if len(p.trail) > 8:
                p.trail.pop(0)
            if p.life > 0:
                alive_particles.append(p)
        self.particles = alive_particles

        if not self.particles and not self.rockets:
            self.timer.stop()
            self.active = False
            self.hide()

        self.update()

    def _explode_rocket(self, rocket: RocketParticle) -> None:
        count = rocket.burst_config.get("count", 80)
        simultaneous = rocket.burst_config.get("simultaneous", False)

        explosion_type = random.choice(["sphere", "ring", "spiral"])

        if explosion_type == "sphere":
            for i in range(count):
                angle = (math.pi * 2 / count) * i
                speed = random.uniform(18.0, 28.0) if simultaneous else random.uniform(14.0, 20.0)
                vx = math.cos(angle) * speed
                vy = math.sin(angle) * speed

                self.particles.append(
                    Particle(
                        x=rocket.x,
                        y=rocket.y,
                        vx=vx,
                        vy=vy,
                        life=random.uniform(0.6, 0.9),
                        color=rocket.color,
                        trail=[QPointF(rocket.x, rocket.y)],
                    )
                )
        elif explosion_type == "ring":
            for i in range(count):
                angle = (math.pi * 2 / count) * i
                speed = random.uniform(16.0, 22.0)
                vx = math.cos(angle) * speed
                vy = math.sin(angle) * speed

                self.particles.append(
                    Particle(
                        x=rocket.x,
                        y=rocket.y,
                        vx=vx,
                        vy=vy,
                        life=random.uniform(0.6, 0.9),
                        color=rocket.color,
                        trail=[QPointF(rocket.x, rocket.y)],
                    )
                )
        elif explosion_type == "spiral":
            for i in range(count):
                angle = (math.pi * 4 / count) * i
                radius_factor = (i / count) * 0.5 + 0.5
                speed = random.uniform(14.0, 20.0) * radius_factor
                vx = math.cos(angle) * speed
                vy = math.sin(angle) * speed

                self.particles.append(
                    Particle(
                        x=rocket.x,
                        y=rocket.y,
                        vx=vx,
                        vy=vy,
                        life=random.uniform(0.6, 0.9),
                        color=rocket.color,
                        trail=[QPointF(rocket.x, rocket.y)],
                    )
                )

    def paintEvent(self, event: QPaintEvent) -> None:  # type: ignore[override]
        if not self.active:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)

        for rocket in self.rockets:
            trail = rocket.trail if rocket.trail else [QPointF(rocket.x, rocket.y)]
            trail_length = len(trail)
            for index, point in enumerate(reversed(trail)):
                ratio = (index + 1) / trail_length
                alpha = 0.9 * (ratio ** 0.7)
                color = QColor(rocket.color)
                color.setAlphaF(alpha)
                radius = 2.0 + 1.2 * ratio
                painter.setBrush(color)
                painter.drawEllipse(point, radius, radius)

        for particle in self.particles:
            trail = particle.trail if particle.trail else [QPointF(particle.x, particle.y)]
            trail_length = len(trail)
            for index, point in enumerate(reversed(trail)):
                ratio = (index + 1) / trail_length
                alpha = max(0.0, min(1.0, particle.life + 0.35)) * (ratio ** 1.0)
                color = QColor(particle.color)
                color.setAlphaF(alpha)
                radius = 0.8 + 1.4 * ratio
                painter.setBrush(color)
                painter.drawEllipse(point, radius, radius)

