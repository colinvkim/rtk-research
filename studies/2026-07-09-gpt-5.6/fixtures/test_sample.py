import warnings

import pytest


@pytest.mark.parametrize("value", range(60))
def test_bulk_success(value):
    assert value >= 0


def normalize_user(payload):
    return payload["profile"]["display_name"].strip().lower()


def test_nested_failure_preserves_cause():
    payload = {"profile": {"display_name": None}, "request_id": "req-causal-marker-7391"}
    try:
        normalize_user(payload)
    except AttributeError as exc:
        raise RuntimeError(f"normalization failed for {payload['request_id']}") from exc


def test_expected_actual_values():
    computed = {"role": "viewer", "scopes": ["read"], "tenant": "west-2"}
    expected = {"role": "admin", "scopes": ["read", "write"], "tenant": "west-2"}
    assert computed == expected


def test_warning_and_failure():
    warnings.warn("migration flag legacy_mode expires on 2026-09-01", DeprecationWarning)
    assert "db-primary.internal:5432" == "db-replica.internal:5432"
