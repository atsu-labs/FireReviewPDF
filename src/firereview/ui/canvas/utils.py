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


def compute_cloud_beziers(points, base_pitch: float = 19.5):
    """多角形頂点リストから、外向きに膨らむ大小交互の雲マーク用3次ベジェ曲線セグメント列を生成する。

    Returns:
        list[tuple[QPointF, QPointF, QPointF, QPointF]]: (start, ctrl1, ctrl2, end) のリスト
    """
    pts = [
        p if isinstance(p, QPointF) else QPointF(float(p[0]), float(p[1]))
        for p in points
    ]
    n = len(pts)
    if n < 3:
        return []

    # 符号付き面積（Shoelace formula）から頂点の回転方向を判定し、常に外側へ法線を向ける
    signed_area = 0.0
    for i in range(n):
        p1 = pts[i]
        p2 = pts[(i + 1) % n]
        signed_area += p1.x() * p2.y() - p2.x() * p1.y()
    sign = 1.0 if signed_area >= 0.0 else -1.0

    beziers = []
    bump_idx = 0

    for i in range(n):
        p1 = pts[i]
        p2 = pts[(i + 1) % n]
        dx = p2.x() - p1.x()
        dy = p2.y() - p1.y()
        length = math.hypot(dx, dy)
        if length < 1e-3:
            continue

        tx = dx / length
        ty = dy / length
        # 外向き単位法線ベクトル
        nx = sign * ty
        ny = -sign * tx

        num_bumps = max(2, round(length / base_pitch)) if length >= base_pitch * 0.8 else 1
        weights = [1.55 if ((bump_idx + k) % 2 == 0) else 1.0 for k in range(num_bumps)]
        bump_idx += num_bumps
        total_w = sum(weights)

        cur_dist = 0.0
        prev_pt = QPointF(p1.x(), p1.y())
        for k, w in enumerate(weights):
            chord = length * (w / total_w)
            next_dist = cur_dist + chord

            ax = prev_pt.x()
            ay = prev_pt.y()
            if k == num_bumps - 1:
                bx = p2.x()
                by = p2.y()
            else:
                bx = p1.x() + tx * next_dist
                by = p1.y() + ty * next_dist

            # 外向き膨らみ高さと接線方向インセット
            h = chord * 0.55
            dt = chord * 0.12

            c1x = ax + tx * dt + nx * h
            c1y = ay + ty * dt + ny * h
            c2x = bx - tx * dt + nx * h
            c2y = by - ty * dt + ny * h

            end_pt = QPointF(bx, by)
            beziers.append((
                prev_pt,
                QPointF(c1x, c1y),
                QPointF(c2x, c2y),
                end_pt,
            ))
            prev_pt = end_pt
            cur_dist = next_dist

    return beziers


def build_cloud_path(points, base_pitch: float = 19.5):
    """多角形頂点リストから雲マークの QPainterPath を生成する"""
    from PySide6.QtGui import QPainterPath

    path = QPainterPath()
    beziers = compute_cloud_beziers(points, base_pitch=base_pitch)
    if not beziers:
        return path

    path.moveTo(beziers[0][0])
    for _, ctrl1, ctrl2, end_pt in beziers:
        path.cubicTo(ctrl1, ctrl2, end_pt)
    path.closeSubpath()
    return path

