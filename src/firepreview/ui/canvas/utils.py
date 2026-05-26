import math
from PySide6.QtCore import QPointF

def point_to_segment_distance(pt, s1, s2):
    dx = s2.x() - s1.x()
    dy = s2.y() - s1.y()
    l2 = dx*dx + dy*dy
    if l2 == 0:
        return math.sqrt((pt.x() - s1.x())**2 + (pt.y() - s1.y())**2), s1
    t = ((pt.x() - s1.x()) * dx + (pt.y() - s1.y()) * dy) / l2
    t = max(0.0, min(1.0, t))
    projection = QPointF(s1.x() + t * dx, s1.y() + t * dy)
    dist = math.sqrt((pt.x() - projection.x())**2 + (pt.y() - projection.y())**2)
    return dist, projection

def apply_angle_snap(start: QPointF, pos: QPointF) -> QPointF:
    """Shiftキー押下時に水平・垂直・45度スナップを適用する"""
    dx = pos.x() - start.x()
    dy = pos.y() - start.y()
    distance = math.sqrt(dx * dx + dy * dy)
    if distance < 0.001:
        return pos
    angle_deg = math.degrees(math.atan2(dy, dx))
    snapped_deg = round(angle_deg / 45.0) * 45.0
    snapped_rad = math.radians(snapped_deg)
    return QPointF(start.x() + distance * math.cos(snapped_rad),
                   start.y() + distance * math.sin(snapped_rad))
