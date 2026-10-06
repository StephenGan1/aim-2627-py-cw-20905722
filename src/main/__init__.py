# -*- coding: utf-8 -*-
"""AIM 2627 Python Coursework —— 哨兵 Sentry 控制模块（学生骨架）。

你的全部作业都在本文件里：按题面（题面.pdf）各题的规范补全每个标有 TODO 的函数。
- 骨架已提供：Facing / SentryState 枚举、SentryGrid 的构造与只读属性、
  渲染函数 render_frame（demo 用，不进测试）。
- 你要实现：Q1-Q6 与 Bonus 的全部 TODO，以及 SentryGrid 的
  四个方法（current_pos 的 setter、move_forward、turn_left、turn_right）。
- 未实现的函数 raise NotImplementedError：可见测试会自动 skip，
  CI 一开始就是绿的；实现一个，对应测试亮一个。
- `python main.py`（或 PYTHONPATH=src python -m main）可看 ASCII 演示。
"""
import json
from enum import Enum


# ---------------------------------------------------------------------------
# 仿真世界基础（已提供，勿改）
# ---------------------------------------------------------------------------
class Facing(Enum):
    """朝向枚举。世界坐标 (x, y)：x 向右增长，y 向上增长（数学系）。"""

    UP = (0, 1)
    DOWN = (0, -1)
    LEFT = (-1, 0)
    RIGHT = (1, 0)

    @property
    def delta(self):
        """该朝向的单位位移向量 (dx, dy)。"""
        return self.value[0], self.value[1]


# ---------------------------------------------------------------------------
# Q1 机器人自检（题面 Q1·自检状态计算与报告生成）
# ---------------------------------------------------------------------------
def hp_ratio(hp, max_hp):
    """TODO(Q1)：血量百分比，返回 0-100 的 int；计算与边界规则见题面 Q1 规范。"""
    ratio = int(hp / max_hp * 100)
    ratio = max(0, min(100, ratio))
    return ratio


def status_report(name, robot_type, hp, max_hp, battery):
    """TODO(Q1)：一行自检报告字符串；档位判定与逐字符格式见题面 Q1 规范。"""
    hp_pct = hp_ratio(hp, max_hp)

    if battery < 20:
        level = "LOW"
    elif battery < 60:
        level = "WARNING"
    else:
        level = "OK"

    return f"{name:<10}|{robot_type:^10}|HP {hp_pct:>3}%|BAT {battery:>3}%|{level}"


# ---------------------------------------------------------------------------
# Q2 战斗日志分析（题面 Q2·多源日志解析与统计）
# ---------------------------------------------------------------------------
def analyze_damage_log(lines):
    """TODO(Q2)：解析混合格式伤害日志，返回固定契约的统计 dict；
    行格式、去重与统计口径见题面 Q2 规范。"""
    total = 0
    by_armor = {
        "front": 0,
        "left": 0,
        "right": 0
    }

    seen_ids = []
    event_count = 0

    armor_map = {
        "F": "front",
        "L": "left",
        "R": "right"
    }

    for raw_line in lines:
        if not isinstance(raw_line, str):
            continue

        line = raw_line.strip()

        if not line or line.startswith("#"):
            continue

        # JSON 日志
        if line.startswith("{"):
            try:
                data = json.loads(line)
            except (json.JSONDecodeError, TypeError):
                continue

            if not isinstance(data, dict):
                continue

            armor = data.get("armor")
            damage = data.get("damage")

            if armor not in by_armor:
                continue

            if type(damage) is not int or damage <= 0:
                continue

            if "id" in data:
                event_id = data["id"]

                if event_id in seen_ids:
                    continue

                seen_ids.append(event_id)

            by_armor[armor] += damage
            total += damage
            event_count += 1
            continue

        # 传感器日志，例如 F:32,L:5,R:12
        parts = line.split(",")
        damages = []
        valid = True

        for part in parts:
            part = part.strip()

            if ":" not in part:
                valid = False
                break

            key, value = part.split(":", 1)

            key = key.strip()
            value = value.strip()

            if key not in armor_map:
                valid = False
                break

            if not value.isdigit():
                valid = False
                break

            damage = int(value)

            if damage <= 0:
                valid = False
                break

            damages.append((armor_map[key], damage))

        if not valid or not damages:
            continue

        for armor, damage in damages:
            by_armor[armor] += damage
            total += damage
            event_count += 1

    if event_count == 0:
        most_hit = None
        avg = 0.0
    else:
        most_hit = max(by_armor, key=by_armor.get)
        avg = round(total / event_count, 2)

    return {
        "total": total,
        "by_armor": by_armor,
        "most_hit": most_hit,
        "avg": avg
    }

# ---------------------------------------------------------------------------
# Q3 SentryGrid（题面 Q3·载体物理规则）
# ---------------------------------------------------------------------------


class SentryGrid:
    """哨兵仿真载体（构造与只读属性已提供；四个 TODO 方法由你实现）。"""

    def __init__(self, width, height, obstacles, enemy_pos,
                 start_pos=(0, 0), facing=Facing.UP, fuel=100):
        self._width = int(width)
        self._height = int(height)
        if self._width <= 0 or self._height <= 0:
            raise ValueError("地图尺寸必须为正")
        # 障碍坐标存入 set，查询 O(1)——已有实现，勿改。
        self._obstacles = set()
        for ob in obstacles:
            x, y = ob
            self._obstacles.add((int(x), int(y)))
        if not isinstance(enemy_pos, (tuple, list)) or len(enemy_pos) != 2:
            raise TypeError("enemy_pos 需要长度为 2 的 tuple/list")
        self._enemy_pos = self._clamp_cell(enemy_pos)
        if self._enemy_pos in self._obstacles:
            raise ValueError("enemy_pos 不能位于障碍物上")
        if not isinstance(facing, Facing):
            facing = Facing.UP
        self._facing = facing
        self._fuel = int(fuel)
        self._collision_count = 0
        self._pos = self._clamp_cell(start_pos)
        if self._pos in self._obstacles:
            raise ValueError("start_pos 不能位于障碍物上")

    def _clamp_cell(self, cell):
        """已提供：元素转 int 并夹回地图范围（供 __init__ 使用）。"""
        x = int(cell[0])
        y = int(cell[1])
        x = max(0, min(self._width - 1, x))
        y = max(0, min(self._height - 1, y))
        return (x, y)

    # -- 只读属性（已提供，勿改） ------------------------------------------
    @property
    def width(self):
        return self._width

    @property
    def height(self):
        return self._height

    @property
    def enemy_pos(self):
        return self._enemy_pos

    @property
    def facing(self):
        return self._facing

    @property
    def fuel(self):
        return self._fuel

    @property
    def collision_count(self):
        return self._collision_count

    @property
    def obstacles(self):
        """障碍集合的只读视图（内部 set 引用，不要修改它）。"""
        return self._obstacles

    @property
    def found_enemy(self):
        return self._pos == self._enemy_pos

    def is_blocked(self, x, y):
        """已提供：坐标是否为障碍或越界（O(1)）。"""
        return ((x, y) in self._obstacles
                or not (0 <= x < self._width and 0 <= y < self._height))

    # -- 你要实现的部分 ------------------------------------------------------
    @property
    def current_pos(self):
        """当前位置 (x, y) 的 tuple。"""
        return self._pos

    @current_pos.setter
    def current_pos(self, value):
        if not isinstance(value, (tuple, list)) or len(value) != 2:
            raise TypeError("current_pos 需要长度为 2 的 tuple/list")

        self._pos = self._clamp_cell(value)

    def move_forward(self):
        if self._fuel <= 0:
            return self._pos

        self._fuel -= 1

        dx, dy = self._facing.delta
        new_x = self._pos[0] + dx
        new_y = self._pos[1] + dy

        if self.is_blocked(new_x, new_y):
            self._collision_count += 1
            return self._pos

        self._pos = (new_x, new_y)
        return self._pos

    def turn_left(self):
        left_turn = {
            Facing.UP: Facing.LEFT,
            Facing.LEFT: Facing.DOWN,
            Facing.DOWN: Facing.RIGHT,
            Facing.RIGHT: Facing.UP
        }

        self._facing = left_turn[self._facing]
        return self._facing

    def turn_right(self):
        right_turn = {
            Facing.UP: Facing.RIGHT,
            Facing.RIGHT: Facing.DOWN,
            Facing.DOWN: Facing.LEFT,
            Facing.LEFT: Facing.UP
        }

        self._facing = right_turn[self._facing]
        return self._facing


# ---------------------------------------------------------------------------
# Q4 贪心导航（题面 Q4·单步贪心导航策略）
# ---------------------------------------------------------------------------
def next_step_toward(pos, target, obstacles, current_facing=Facing.UP):
    """TODO(Q4)：返回下一步应朝向的 Facing；
    候选判定、优先级与回退规则见题面 Q4 规范。"""

    x, y = pos
    tx, ty = target

    if pos == target:
        return current_facing

    dx = tx - x
    dy = ty - y

    candidates = []

    if dx > 0:
        candidates.append((abs(dx), Facing.RIGHT))
    elif dx < 0:
        candidates.append((abs(dx), Facing.LEFT))

    if dy > 0:
        candidates.append((abs(dy), Facing.UP))
    elif dy < 0:
        candidates.append((abs(dy), Facing.DOWN))

    candidates.sort(key=lambda item: item[0], reverse=True)

    for _, direction in candidates:
        step_x, step_y = direction.delta
        next_pos = (x + step_x, y + step_y)

        if next_pos not in obstacles:
            return direction

    return current_facing


# ---------------------------------------------------------------------------
# Q5 哨兵决策机（题面 Q5·裁判系统决策规则表）
# ---------------------------------------------------------------------------
class SentryState(Enum):
    """哨兵状态机（已提供，勿改）。"""

    PATROL = "PATROL"
    SUSPECT = "SUSPECT"
    ENGAGE = "ENGAGE"
    RETREAT = "RETREAT"
    RETURN = "RETURN"


def decide(sensor, state, hp, heat):
    """TODO(Q5)：纯函数决策，返回 (action: str, new_state: SentryState)；
    sensor 字段契约、R1-R7 规则表与非法输入处理见题面 Q5 规范。"""

    required = {"enemy_frames", "enemy_dist", "robot_type", "max_hp"}

    if not isinstance(sensor, dict) or not required.issubset(sensor):
        raise ValueError("sensor 缺少必要字段")

    if not isinstance(state, SentryState):
        raise ValueError("state 非法")

    frames = sensor["enemy_frames"]

    if isinstance(frames, (tuple, list)):
        if len(frames) == 0 or len(frames) > 6:
            raise ValueError("enemy_frames 长度非法")
        frames = tuple(bool(x) for x in frames)
    else:
        frames = (bool(frames),)

    robot_type = sensor["robot_type"]
    if robot_type not in ("INFANTRY", "HERO"):
        robot_type = "INFANTRY"

    enemy_dist = sensor["enemy_dist"]
    if type(enemy_dist) is not int or enemy_dist < 0:
        enemy_dist = float("inf")

    try:
        max_hp = int(sensor["max_hp"])
    except (TypeError, ValueError):
        max_hp = 1

    if max_hp <= 0:
        max_hp = 1

    try:
        hp_value = int(hp)
    except (TypeError, ValueError):
        hp_value = 0

    hp_pct = int(hp_value / max_hp * 100)
    hp_pct = max(0, min(100, hp_pct))

    visible = frames[-1]

    # R1：血量低，优先撤退
    if hp_pct <= 30:
        return ("RETREAT", SentryState.RETREAT)

    # R2：撤退状态恢复后返航
    if state is SentryState.RETREAT:
        return ("RETURN", SentryState.RETURN)

    # R3：RETURN 只保持一帧
    if state is SentryState.RETURN:
        return ("MOVE_BASE", SentryState.PATROL)

    # R4 / R5：正在交火
    if state is SentryState.ENGAGE:
        if visible:
            if enemy_dist <= 3:
                return ("SHOOT", SentryState.ENGAGE)

            if robot_type == "HERO":
                return ("MOVE_RIGHT", SentryState.ENGAGE)

            return ("MOVE_LEFT", SentryState.ENGAGE)

        # 刚刚才丢失目标
        if len(frames) >= 2 and frames[-2]:
            return ("HOLD_FIRE", SentryState.ENGAGE)

        # 连续看不到
        return ("SCAN", SentryState.SUSPECT)

    # R6：巡逻/怀疑状态发现敌人
    if visible:
        confirmed = (
            len(frames) >= 2
            and frames[-1]
            and frames[-2]
        )

        if confirmed:
            if enemy_dist <= 3:
                return ("SHOOT", SentryState.ENGAGE)

            if robot_type == "HERO":
                return ("MOVE_RIGHT", SentryState.ENGAGE)

            return ("MOVE_LEFT", SentryState.ENGAGE)

        return ("SCAN", SentryState.SUSPECT)

    # R7：默认行为
    if state is SentryState.PATROL:
        return ("PATROL_MOVE", SentryState.PATROL)

    return ("SCAN", SentryState.SUSPECT)


# ---------------------------------------------------------------------------
# Q6 巡逻任务（题面 Q6·巡逻契约与验收阈值）
# ---------------------------------------------------------------------------
def run_patrol(grid, max_steps=500):
    """TODO(Q6)：sense → decide → act 主循环；
    循环结构、终止条件、脱困自由度与统计返回契约见题面 Q6 规范。"""
    from collections import deque

    steps = 0
    visited = {grid.current_pos}
    escape_path = []

    def manhattan(a, b):
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    def find_escape_path(start, target):
        queue = deque([start])
        parent = {start: (None, None)}

        directions = (
            Facing.UP,
            Facing.DOWN,
            Facing.LEFT,
            Facing.RIGHT
        )

        while queue:
            current = queue.popleft()

            if current == target:
                break

            for direction in directions:
                dx, dy = direction.delta
                nxt = (current[0] + dx, current[1] + dy)

                if grid.is_blocked(*nxt):
                    continue

                if nxt in parent:
                    continue

                parent[nxt] = (current, direction)
                queue.append(nxt)

        if target not in parent:
            return []

        path = []
        current = target

        while current != start:
            previous, direction = parent[current]
            path.append(direction)
            current = previous

        path.reverse()
        return path

    def face_direction(direction):
        order = {
            Facing.UP: 0,
            Facing.RIGHT: 1,
            Facing.DOWN: 2,
            Facing.LEFT: 3
        }

        difference = (
            order[direction] - order[grid.facing]
        ) % 4

        if difference == 1:
            grid.turn_right()
        elif difference == 2:
            grid.turn_right()
            grid.turn_right()
        elif difference == 3:
            grid.turn_left()

    while (
        steps < max_steps
        and grid.fuel > 0
        and not grid.found_enemy
    ):
        position = grid.current_pos

        if escape_path:
            direction = escape_path.pop(0)

        else:
            direction = next_step_toward(
                position,
                grid.enemy_pos,
                grid.obstacles,
                grid.facing
            )

            dx, dy = direction.delta
            next_pos = (
                position[0] + dx,
                position[1] + dy
            )

            current_distance = manhattan(
                position,
                grid.enemy_pos
            )

            next_distance = manhattan(
                next_pos,
                grid.enemy_pos
            )

            greedy_ok = (
                not grid.is_blocked(*next_pos)
                and next_distance < current_distance
            )

            if not greedy_ok:
                escape_path = find_escape_path(
                    position,
                    grid.enemy_pos
                )

                if not escape_path:
                    break

                direction = escape_path.pop(0)

        face_direction(direction)
        grid.move_forward()

        steps += 1
        visited.add(grid.current_pos)

    success = grid.found_enemy

    return {
        "steps": steps,
        "collisions": grid.collision_count,
        "visited_count": len(visited),
        "found_enemy": success,
        "success": success
    }


def report_to_json(stats):
    """TODO(Q6)：把 stats 序列化为确定性的 JSON 字符串，见题面 Q6 规范。"""
    return json.dumps(
        stats,
        sort_keys=True,
        separators=(",", ":")
    )


# ---------------------------------------------------------------------------
# Bonus：BFS 全局最短路（题面 Bonus·BFS 语义与排行榜）
# ---------------------------------------------------------------------------
def bfs_path_length(start, target, obstacles):
    """TODO(Bonus)：BFS 全局最短路步数；返回语义与边界职责见题面 Bonus 规范。"""
    from collections import deque

    if start == target:
        return 0

    obstacles = set(obstacles)

    if target in obstacles:
        return -1

    queue = deque([(start, 0)])
    visited = {start}

    while queue:
        current, distance = queue.popleft()

        x, y = current

        neighbors = [
            (x + 1, y),
            (x - 1, y),
            (x, y + 1),
            (x, y - 1)
        ]

        for nxt in neighbors:
            if nxt in obstacles:
                continue

            if nxt in visited:
                continue

            if nxt == target:
                return distance + 1

            visited.add(nxt)
            queue.append((nxt, distance + 1))

    return -1
# ---------------------------------------------------------------------------
# 渲染（已提供，demo 专用，不进测试）
# ---------------------------------------------------------------------------


def render_frame(grid, trail=()):
    """ASCII 渲染一帧战场；trail 为走过的格子集合。返回 list[str]。"""
    trail = set(trail)
    rows = []
    for y in range(grid.height - 1, -1, -1):
        row = []
        for x in range(grid.width):
            if (x, y) == grid.current_pos:
                row.append("◉")
            elif (x, y) == grid.enemy_pos:
                row.append("▲")
            elif (x, y) in grid.obstacles:
                row.append("█")
            elif (x, y) in trail:
                row.append("·")
            else:
                row.append(".")
        rows.append("".join(row))
    return rows
