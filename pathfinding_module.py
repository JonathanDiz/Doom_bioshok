import asyncio
import heapq
from collections import defaultdict
from typing import List, Tuple, Dict

import concurrent

class PathFinder:
    def __init__(self, game):
        self.game = game
        self.walkable_cache = {}
        self.cached_paths: Dict[Tuple, List] = {}
        self.loop = asyncio.get_event_loop()
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)
        
        # Direcciones de movimiento (8 direcciones)
        self.directions = [
            (-1, 0), (0, -1), (1, 0), (0, 1),
            (-1, -1), (1, -1), (1, 1), (-1, 1)
        ]
        
        self.build_navigation_mesh()

    def build_navigation_mesh(self):
        """Precalcula la malla de navegación al iniciar el nivel"""
        self.nav_mesh = defaultdict(list)
        world_map = self.game.map.world_map
        
        for y in range(len(self.game.map.mini_map)):
            for x in range(len(self.game.map.mini_map[0])):
                if not world_map.get((x, y), False):
                    self.nav_mesh[(x, y)] = [
                        (x+dx, y+dy) for dx, dy in self.directions
                        if not world_map.get((x+dx, y+dy), False)
                    ]

    async def find_path_async(self, start: Tuple[int, int], goal: Tuple[int, int]) -> List[Tuple[int, int]]:
        """Pathfinding asíncrono con A* optimizado"""
        return await self.loop.run_in_executor(
            self.executor,
            self.a_star_search,
            start,
            goal
        )

    def a_star_search(self, start: Tuple[int, int], goal: Tuple[int, int]) -> List[Tuple[int, int]]:
        """Algoritmo A* con prioridad para movimiento natural"""
        if start == goal:
            return []

        frontier = []
        heapq.heappush(frontier, (0, start))
        came_from: Dict[Tuple, Tuple] = {}
        cost_so_far: Dict[Tuple, float] = {start: 0}
        
        while frontier:
            current = heapq.heappop(frontier)[1]
            
            if current == goal:
                break
            
            for neighbor in self.nav_mesh.get(current, []):
                new_cost = cost_so_far[current] + self.heuristic(current, neighbor)
                if neighbor not in cost_so_far or new_cost < cost_so_far[neighbor]:
                    cost_so_far[neighbor] = new_cost
                    priority = new_cost + self.heuristic(goal, neighbor)
                    heapq.heappush(frontier, (priority, neighbor))
                    came_from[neighbor] = current
        
        return self.reconstruct_path(came_from, start, goal)

    def heuristic(self, a: Tuple[int, int], b: Tuple[int, int]) -> float:
        """Distancia octil para movimiento diagonal"""
        dx = abs(a[0] - b[0])
        dy = abs(a[1] - b[1])
        return (dx + dy) + (1 - 2 * 1) * min(dx, dy)

    def reconstruct_path(self, came_from: Dict[Tuple, Tuple], 
                        start: Tuple[int, int], 
                        goal: Tuple[int, int]) -> List[Tuple[int, int]]:
        """Reconstruye el camino óptimo"""
        path = []
        current = goal
        
        while current != start:
            path.append(current)
            current = came_from.get(current, start)
            if current == start:
                break
        
        path.reverse()
        return self.smooth_path(path)

    def smooth_path(self, path: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
        """Suaviza el camino eliminando nodos redundantes"""
        if len(path) < 3:
            return path
        
        smoothed = [path[0]]
        for node in path[1:-1]:
            last = smoothed[-1]
            if not self.line_of_sight(last, node):
                smoothed.append(node)
        smoothed.append(path[-1])
        
        return smoothed

    def line_of_sight(self, start: Tuple[int, int], end: Tuple[int, int]) -> bool:
        """Algoritmo Bresenham para visión directa"""
        x0, y0 = start
        x1, y1 = end
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        
        while x0 != x1 or y0 != y1:
            if self.game.map.world_map.get((x0, y0), False):
                return False
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy
        
        return True

    def get_next_step(self, start: Tuple[int, int], goal: Tuple[int, int]) -> Tuple[int, int]:
        """Obtiene el siguiente paso óptimo con cache"""
        if (start, goal) in self.cached_paths:
            return self.cached_paths[(start, goal)][0] if self.cached_paths[(start, goal)] else start
        
        path = self.a_star_search(start, goal)
        self.cached_paths[(start, goal)] = path
        return path[0] if path else start

    async def dynamic_obstacle_update(self):
        """Actualiza dinámicamente los obstáculos en segundo plano"""
        while True:
            await asyncio.sleep(1)
            self.build_navigation_mesh()
            self.cached_paths.clear()