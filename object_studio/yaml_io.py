from pathlib import Path
import yaml
from .models import Project, ObjectDefinition, ObjectSize, ObjectFlags

class FlowList(list):
    """Custom list type to force flow style (inline array) in YAML dumps."""
    pass

def flow_list_rep(dumper, data):
    return dumper.represent_sequence('tag:yaml.org,2002:seq', data, flow_style=True)

yaml.add_representer(FlowList, flow_list_rep)

def load_project(path: Path) -> Project:
    project = Project()
    if not path.exists():
        return project
        
    with open(path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f) or {}
        
    for obj_data in data.get("objects", []):
        size_data = obj_data.get("size", {})
        flags_data = obj_data.get("flags", {})
        
        obj = ObjectDefinition(
            id=obj_data.get("id", ""),
            code=obj_data.get("code", 0),
            size=ObjectSize(
                width=size_data.get("width", 1),
                height=size_data.get("height", 1)
            ),
            flags=ObjectFlags(
                blocking=flags_data.get("blocking", False),
                interactive=flags_data.get("interactive", False)
            ),
            tiles=obj_data.get("tiles", [])
        )
        project.objects.append(obj)
        
    return project

def save_project(path: Path, project: Project) -> bool:
    # Sort objects by code for consistency
    project.objects.sort(key=lambda o: o.code)
    
    out_objects = []
    for obj in project.objects:
        out_objects.append({
            "object": obj.id,  # world_builder używa 'object' albo 'id' (zgodnie z pydantic aliasem) - tutaj specyfikacja mówi `id` ale zmienimy na id.
            # Zgodnie z object-studio.md:
            "id": obj.id,
            "code": obj.code,
            "size": {
                "width": obj.size.width,
                "height": obj.size.height
            },
            "flags": {
                "blocking": obj.flags.blocking,
                "interactive": obj.flags.interactive
            },
            "tiles": FlowList(obj.tiles)
        })
        
    data = {"objects": out_objects}
    
    try:
        with open(path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, sort_keys=False, indent=2, allow_unicode=True)
        return True
    except Exception:
        return False

def validate_project(project: Project) -> list[str]:
    errors = []
    ids = set()
    codes = set()
    
    for obj in project.objects:
        if not obj.id:
            errors.append(f"Obiekt z kodem {obj.code} nie ma ID.")
        if obj.id in ids:
            errors.append(f"Zduplikowane ID: {obj.id}")
        ids.add(obj.id)
        
        if obj.code in codes:
            errors.append(f"Zduplikowany code: {obj.code} dla ID: {obj.id}")
        codes.add(obj.code)
        
        if obj.size.width <= 0 or obj.size.height <= 0:
            errors.append(f"Nieprawidłowy rozmiar dla ID: {obj.id}")
            
        if len(obj.tiles) == 0:
            errors.append(f"Pusty obiekt (brak kafelków): {obj.id}")
            
        expected_len = obj.size.width * obj.size.height
        if len(obj.tiles) != expected_len:
            errors.append(f"Zła liczba kafelków w {obj.id}. Oczekiwano {expected_len}, jest {len(obj.tiles)}")
            
        for t in obj.tiles:
            if t < 0 or t > 255:
                errors.append(f"Nieprawidłowy index kafelka ({t}) w obiekcie {obj.id}")
                
    return errors
