from study_mcp.db import repository


def list_materials_tool() -> dict[str, object]:
    """
    List all study materials currently stored in the vector database.

    Returns a list of materials with their material_id and source name.
    """
    materials = repository.list_materials()
    return {
        'materials': materials,
        'total': len(materials),
    }
