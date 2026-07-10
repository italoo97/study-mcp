from study_mcp.db import repository


def delete_material_tool(material_id: str) -> dict[str, str | int]:
    """
    Delete all chunks of a material from the vector store.

    Args:
        material_id: The material to delete.

    Returns:
        dict with material_id and chunks_deleted.
    """
    deleted = repository.delete_material(material_id)
    return {'material_id': material_id, 'chunks_deleted': deleted}


def get_material_overview_tool(
    material_id: str, num_chunks: int = 5
) -> dict[str, object]:
    """
    Return the first chunks of a material so the client can understand
    what it's about before summarizing or quizzing on it.

    Args:
        material_id: The material to inspect.
        num_chunks: How many leading chunks to return (default 5).

    Returns:
        dict with material_id, source, total_chunks and chunks (the
        first num_chunks texts, in order).
    """
    chunks = repository.get_chunks_by_material(material_id)
    if not chunks:
        return {'error': f'No chunks found for material_id {material_id}'}

    return {
        'material_id': material_id,
        'source': chunks[0]['source'],
        'total_chunks': len(chunks),
        'chunks': [c['text'] for c in chunks[:num_chunks]],
    }


def generate_quiz_context_tool(
    material_id: str, num_topics: int = 5
) -> dict[str, object]:
    """
    Return a spread of chunks from a material for the calling LLM to
    write quiz questions from. This tool does NOT generate a quiz -
    it returns context; the client model writes the questions.

    Args:
        material_id: The material to sample from.
        num_topics: How many chunks to sample, spread across the
            material (default 5).

    Returns:
        dict with material_id, source and a list of sampled chunk
        texts spanning the material.
    """
    chunks = repository.get_chunks_by_material(material_id)
    if not chunks:
        return {'error': f'No chunks found for material_id {material_id}'}

    if len(chunks) <= num_topics:
        sampled = chunks
    else:
        # ponytail: evenly-spaced index sampling, not topic-aware -
        # good enough since chunks are already sequential by content.
        # Ceiling: could sample near-duplicate topics on repetitive
        # material. Upgrade path: cluster chunk embeddings instead.
        step = len(chunks) / num_topics
        indices = sorted({int(i * step) for i in range(num_topics)})
        sampled = [chunks[i] for i in indices]

    return {
        'material_id': material_id,
        'source': sampled[0]['source'],
        'chunks': [c['text'] for c in sampled],
    }


def study_stats_tool() -> dict[str, object]:
    """
    Return study statistics: total materials, total chunks and chunks
    per material.

    Returns:
        dict with total_materials, total_chunks and
        chunks_per_material (a list of {material_id, source, chunks}).
    """
    materials = repository.list_materials()
    per_material = []
    total_chunks = 0

    for material in materials:
        chunks = repository.get_chunks_by_material(material['material_id'])
        total_chunks += len(chunks)
        per_material.append({
            'material_id': material['material_id'],
            'source': material['source'],
            'chunks': len(chunks),
        })

    return {
        'total_materials': len(materials),
        'total_chunks': total_chunks,
        'chunks_per_material': per_material,
    }
