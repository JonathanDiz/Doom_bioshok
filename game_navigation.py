import asyncio
import heapq
import numpy as np
from collections import defaultdict
from typing import List, Tuple, Dict, Set
from concurrent.futures import ThreadPoolExecutor

class GamePathFinder:
    def __init__(self, game):
        self.game = game
        self.map_data = np.array(game.map.mini_map, dtype=np.bool_)
        self.world_map = game.map.world_map  # Corregir typo
        self.tile_size = game.map.tile_size
        
        # Optimización: Precalcular posiciones walkables
        self.walkable_nodes = self._precompute_walkable()
        self.nav_mesh = self._build_nav_mesh()
        
        # Sistema de caché optimizado
        self.path_cache: Dict[Tuple[Tuple, Tuple], List[Tuple]] = {}
        self.executor = ThreadPoolExecutor(max_workers=2)
        self.loop = asyncio.get_event_loop()

        # Estadísticas de rendimiento
        self.cache_hits = 0
        self.cache_misses = 0

    def _precompute_walkable(self) -> Set[Tuple[int, int]]:
        """Precalcula nodos transitables usando NumPy"""
        y, x = np.where(self.map_data == 0)
        return set(zip(x.tolist(), y.tolist()))

    def _build_nav_mesh(self) -> Dict[Tuple, List[Tuple]]:
        """Construye la malla de navegación vectorizada"""
        directions = [(-1,0), (0,-1), (1,0), (0,1), (-1,-1), (1,-1), (1,1), (-1,1)]
        mesh = defaultdict(list)
        
        for (x, y) in self.walkable_nodes:
            neighbors = [
                (x + dx, y + dy) 
                for dx, dy in directions 
                if (x + dx, y + dy) in self.walkable_nodes
            ]
            if neighbors:
                mesh[(x, y)] = neighbors
        return mesh

    async def find_path_async(self, start: Tuple[int, int], goal: Tuple[int, int]) -> List[Tuple[int, int]]:
        """Versión asíncrona con caché inteligente"""
        cache_key = (start, goal)
        
        # Verificar caché primero
        if cache_key in self.path_cache:
            self.cache_hits += 1
            return self.path_cache[cache_key]
        
        self.cache_misses += 1
        path = await self.loop.run_in_executor(
            self.executor,
            self._optimized_a_star,
            start,
            goal
        )
        
        # Almacenar en caché si el camino es válido
        if path and path[-1] == goal:
            self.path_cache[cache_key] = path
            
        return path

    def _optimized_a_star(self, start: Tuple[int, int], goal: Tuple[int, int]) -> List[Tuple[int, int]]:
        """A* optimizado con cola de prioridad mejorada"""
        if start == goal or start not in self.nav_mesh:
            return []

        # Heap optimizado
        frontier = []
        heapq.heappush(frontier, (0, 0, start))
        came_from = {}
        cost_so_far = {start: 0}
        found_goal = False
        
        while frontier:
            _, current = heapq.heappop(frontier)[1]
            
            if current == goal:
                found_goal = True
                break
                
            for neighbor in self.nav_mesh.get(current, []):
                new_cost = cost_so_far[current] + 1
                if neighbor not in cost_so_far or new_cost < cost_so_far[neighbor]:
                    cost_so_far[neighbor] = new_cost
                    priority = new_cost + self._octile_heuristic(goal, neighbor)
                    heapq.heappush(frontier, (priority, id(neighbor), neighbor))
                    came_from[neighbor] = current
        
        return self._reconstruct_path(came_from, start, goal) if found_goal else []

    def _octile_heuristic(self, a: Tuple[int, int], b: Tuple[int, int]) -> float:
        """Heurística octil optimizada"""
        dx = abs(a[0] - b[0])
        dy = abs(a[1] - b[1])
        return (dx + dy) - 0.5858 * min(dx, dy)

    def _reconstruct_path(self, came_from: Dict, start: Tuple, goal: Tuple) -> List[Tuple]:
        """Reconstrucción de camino con pre-asignación de memoria"""
        path = []
        current = goal
        while current != start:
            path.append(current)
            current = came_from.get(current)
            if current is None:
                return []
        path.reverse()
        return self._smooth_path(path)

    def _smooth_path(self, path: List[Tuple]) -> List[Tuple]:
        """Suavizado optimizado con visión directa vectorizada"""
        if len(path) < 3:
            return path
        
        smoothed = [path[0]]
        last_valid = path[0]
        
        for i in range(1, len(path)-1):
            if not self._has_line_of_sight(last_valid, path[i+1]):
                smoothed.append(path[i])
                last_valid = path[i]
        
        smoothed.append(path[-1])
        return smoothed

    def _has_line_of_sight(self, start: Tuple, end: Tuple) -> bool:
        """Bresenham optimizado con salida temprana"""
        x0, y0 = start
        x1, y1 = end
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        
        while (x0 != x1) or (y0 != y1):
            if (x0, y0) in self.world_map:
                return False
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
                if x0 == x1 and y0 == y1:
                    break
            if e2 <= dx:
                err += dx
                y0 += sy
        return True

    def get_next_step(self, start: Tuple, goal: Tuple) -> Tuple:
        """Obtención del siguiente paso con caché L1"""
        if start == goal:
            return start
            
        path = self.path_cache.get((start, goal), [])
        if not path:
            path = self._optimized_a_star(start, goal)
            if path:
                self.path_cache[(start, goal)] = path
        return path[0] if path else start

    async def dynamic_obstacle_update(self, force=False):
        """Actualización dinámica optimizada con pooling"""
        if force or self.game.object_handler.has_dynamic_obstacles:
            await self.loop.run_in_executor(
                self.executor,
                self._partial_navmesh_update
            )
            self.path_cache.clear()

    def _partial_navmesh_update(self):
        """Actualización parcial de la malla de navegación"""
        changed_nodes = self._detect_changes()
        for node in changed_nodes:
            if node in self.nav_mesh:
                self.nav_mesh[node] = [
                    (node[0]+dx, node[1]+dy)
                    for dx, dy in [(-1,0), (0,-1), (1,0), (0,1)]
                    if (node[0]+dx, node[1]+dy) in self.walkable_nodes
                ]

    def _detect_changes(self) -> Set[Tuple]:
        """Detección de cambios en el mapa usando máscaras NumPy"""
        current_map = np.array(self.game.map.mini_map, dtype=np.bool_)
        diff = np.logical_xor(self.map_data, current_map)
        changed = set(zip(*np.where(diff)))
        self.map_data = current_map
        return changed

    def get_performance_stats(self) -> Dict:
        """Estadísticas de rendimiento para debug"""
        return {
            'cache_hits': self.cache_hits,
            'cache_misses': self.cache_misses,
            'cache_ratio': self.cache_hits / (self.cache_hits + self.cache_misses) if (self.cache_hits + self.cache_misses) > 0 else 0,
            'navmesh_size': len(self.nav_mesh),
            'walkable_nodes': len(self.walkable_nodes)
        }