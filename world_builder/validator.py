import sys
from .model import GameWorld
from typing import Set, Dict, List

class ValidationError(Exception):
    pass

class WorldValidator:
    def __init__(self, world: GameWorld):
        self.world = world
        self.warnings = []
        
        # Lookups
        self.region_ids: Set[str] = set()
        self.screen_ids: Set[str] = set()
        self.object_ids: Set[str] = set()
        self.object_codes: Set[int] = set()
        
        self.objects_by_id = {}
        
    def validate(self):
        self._check_duplicates()
        self._check_region_dirs()
        self._check_references()
        self._check_bounds()
        self._check_reachability()
        self._check_overlaps()
        
    def _check_duplicates(self):
        for obj in self.world.objects:
            if obj.id in self.object_ids:
                raise ValidationError(f"Duplicate object id: {obj.id}")
            if obj.code in self.object_codes:
                raise ValidationError(f"Duplicate object code: {obj.code}")
            
            expected_tiles = obj.size.width * obj.size.height
            if len(obj.tiles) != expected_tiles:
                raise ValidationError(f"Object '{obj.id}' has {len(obj.tiles)} tiles, expected {expected_tiles} (W:{obj.size.width} * H:{obj.size.height})")
                
            self.object_ids.add(obj.id)
            self.object_codes.add(obj.code)
            self.objects_by_id[obj.id] = obj
            
        for region in self.world.regions:
            if region.id in self.region_ids:
                raise ValidationError(f"Duplicate region id: {region.id}")
            self.region_ids.add(region.id)
            
            for screen in region.screens:
                if screen.id in self.screen_ids:
                    raise ValidationError(f"Duplicate screen id: {screen.id}")
                self.screen_ids.add(screen.id)
                
    def _check_region_dirs(self):
        for region in self.world.regions:
            if getattr(region, '_dir_name', '') and region._dir_name != region.id:
                raise ValidationError(f"Region id '{region.id}' does not match directory '{region._dir_name}'")
                
    def _check_references(self):
        # Start region and screen
        start_region = self.world.world.start_region
        start_screen = self.world.world.start_screen
        
        if start_region not in self.region_ids:
            raise ValidationError(f"start_region '{start_region}' not found")
            
        start_region_obj = next((r for r in self.world.regions if r.id == start_region), None)
        if start_region_obj:
            screen_exists = any(s.id == start_screen for s in start_region_obj.screens)
            if not screen_exists:
                raise ValidationError(f"start_screen '{start_screen}' not found in region '{start_region}'")
                
        # Screens exits and objects
        for region in self.world.regions:
            if region.start_screen and not any(s.id == region.start_screen for s in region.screens):
                raise ValidationError(f"Region '{region.id}' start_screen '{region.start_screen}' not found")
                
            for screen in region.screens:
                for direction in ['north', 'south', 'east', 'west']:
                    target = getattr(screen.exits, direction)
                    if target is not None and target not in self.screen_ids:
                        raise ValidationError(f"Screen '{screen.id}' has invalid {direction} exit '{target}'")
                        
                for inst in screen.objects:
                    if inst.object not in self.object_ids:
                        raise ValidationError(f"Screen '{screen.id}' uses unknown object '{inst.object}'")
                        
    def _check_bounds(self):
        # Start position
        pos = self.world.world.start_position
        if not (0 <= pos.x <= 39 and 0 <= pos.y <= 9):
            raise ValidationError(f"start_position ({pos.x}, {pos.y}) is out of bounds")
            
        # Object footprints
        for region in self.world.regions:
            for screen in region.screens:
                for inst in screen.objects:
                    obj_def = self.objects_by_id[inst.object]
                    right = inst.x + obj_def.size.width
                    bottom = inst.y + obj_def.size.height
                    # Bounds are up to 40 and 10 (exclusive max)
                    if right > 40 or bottom > 10:
                        raise ValidationError(f"Object '{inst.object}' on screen '{screen.id}' footprint out of bounds (Right: {right}, Bottom: {bottom})")

    def _check_reachability(self):
        # Build graph
        graph = {s_id: [] for s_id in self.screen_ids}
        for region in self.world.regions:
            for screen in region.screens:
                for direction in ['north', 'south', 'east', 'west']:
                    target = getattr(screen.exits, direction)
                    if target:
                        graph[screen.id].append(target)
                        
        start_screen = self.world.world.start_screen
        visited = set()
        
        def dfs(node):
            if node not in visited:
                visited.add(node)
                for neighbor in graph.get(node, []):
                    dfs(neighbor)
                    
        if start_screen in graph:
            dfs(start_screen)
            
        unreachable = self.screen_ids - visited
        if unreachable:
            self.warnings.append(f"Unreachable screens: {', '.join(unreachable)}")
            
    def _check_overlaps(self):
        for region in self.world.regions:
            for screen in region.screens:
                grid = {}
                for inst in screen.objects:
                    obj_def = self.objects_by_id[inst.object]
                    if not obj_def.flags.blocking:
                        continue
                        
                    for x in range(inst.x, inst.x + obj_def.size.width):
                        for y in range(inst.y, inst.y + obj_def.size.height):
                            if (x, y) in grid:
                                self.warnings.append(f"Overlapping blocking objects on screen '{screen.id}' at ({x}, {y})")
                            grid[(x, y)] = True
