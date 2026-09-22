"""Focused regression tests for issues #26, #46, #47, and #49."""

import ast
import datetime
from pathlib import Path

COMPONENT = Path(__file__).parents[1] / "custom_components" / "epg"


def _tree(filename: str) -> ast.Module:
    return ast.parse((COMPONENT / filename).read_text())


def _function(filename: str, name: str):
    return next(
        node
        for node in ast.walk(_tree(filename))
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name
    )


def test_open_epg_requests_send_user_agent():
    for filename, function_name in (
        ("config_flow.py", "fetch_channel_list"),
        ("sensor.py", "_async_update_data"),
    ):
        function = _function(filename, function_name)
        requests = [
            node
            for node in ast.walk(function)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "session"
            and node.func.attr == "get"
        ]
        assert len(requests) == 1
        assert any(keyword.arg == "headers" for keyword in requests[0].keywords)


def test_selected_channels_has_safe_default():
    source = (COMPONENT / "__init__.py").read_text()
    assert 'entry.options.get("selected_channels", [])' in source
    assert 'entry.options["selected_channels"]' not in source


def test_programme_date_is_an_iso_string():
    function = _function("sensor.py", "_format_programme")
    module = ast.Module(body=[function], type_ignores=[])
    namespace = {"datetime": datetime, "timedelta": datetime.timedelta}
    exec(compile(ast.fix_missing_locations(module), "sensor.py", "exec"), namespace)
    result = namespace["_format_programme"](
        {"title": "News", "start": "12:30", "end": "13:00"}, "today", "One"
    )
    assert result["date"] == datetime.date.today().isoformat()
    assert isinstance(result["date"], str)


def test_current_programme_attributes_are_exposed():
    function = _function("sensor.py", "extra_state_attributes")
    assigned_keys = {
        node.slice.value
        for node in ast.walk(function)
        if isinstance(node, ast.Subscript)
        and isinstance(node.ctx, ast.Store)
        and isinstance(node.value, ast.Name)
        and node.value.id == "ret"
        and isinstance(node.slice, ast.Constant)
    }
    assert {"title", "start_time", "end_time"} <= assigned_keys


def test_first_refresh_runs_as_a_background_task():
    function = _function("sensor.py", "_initialize_coordinator")
    calls = [node for node in ast.walk(function) if isinstance(node, ast.Call)]
    assert any(
        isinstance(call.func, ast.Attribute)
        and call.func.attr == "async_create_background_task"
        for call in calls
    )
    assert not any(
        isinstance(node, ast.Await)
        and isinstance(node.value, ast.Call)
        and isinstance(node.value.func, ast.Attribute)
        and node.value.func.attr == "async_config_entry_first_refresh"
        for node in ast.walk(function)
    )


def test_non_generated_entities_do_not_wait_for_coordinator_data():
    function = _function("sensor.py", "_create_entities")
    source = ast.unparse(function)
    assert "config_options.get('selected_channels', [])" in source
    assert "channel.id if channel else channel_id" in source
