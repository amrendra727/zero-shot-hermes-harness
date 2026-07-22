from src.graph.agent import agentic_ai
from src.graph.edges import after_transform


def test_graph_compiles_without_env():
    # compiled at import; nodes present
    assert agentic_ai is not None
    node_names = set(agentic_ai.get_graph().nodes)
    assert {"transform_text", "error_handler", "finalize"} <= node_names


def test_error_edge_routes_to_handler():
    assert after_transform({"error": "boom"}) == "error_handler"
    assert after_transform({"error": None}) == "finalize"


def test_transform_node_surfaces_error_on_exception():
    """Baseline transform is deterministic; exceptions surface as error payloads."""
    from src.graph.nodes import transform_text

    out = transform_text({"input_text": "hi", "instruction": "upper"})
    assert isinstance(out, dict)
    assert out.get("error") is None
    assert out.get("output_text") == "HI"
