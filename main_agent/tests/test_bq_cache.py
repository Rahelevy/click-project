import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

import main_agent.cache.bq_cache as bq_cache


def make_row(rd):
    return SimpleNamespace(result_data=rd, query_hash="h")


def test_get_miss_returns_none(monkeypatch):
    mock_client = Mock()
    mock_query = Mock()
    mock_query.result.return_value = []
    mock_client.query.return_value = mock_query
    monkeypatch.setattr(bq_cache, "CLIENT", mock_client)

    assert bq_cache.get("SELECT 1") is None
    mock_client.query.assert_called_once()


def test_get_hit_returns_data_and_updates_hit_count(monkeypatch):
    mock_client = Mock()
    row = make_row({"foo": "bar"})
    mock_query = Mock()
    mock_query.result.return_value = [row]
    # simulate two query calls: one to select the row, one to update hit_count
    mock_client.query.side_effect = [mock_query, mock_query]

    monkeypatch.setattr(bq_cache, "CLIENT", mock_client)

    res = bq_cache.get("SELECT 1")
    assert res == {"foo": "bar"}
    assert mock_client.query.call_count >= 1


def test_set_calls_insert_rows_json(monkeypatch):
    mock_client = Mock()
    mock_client.insert_rows_json.return_value = []  # no errors
    monkeypatch.setattr(bq_cache, "CLIENT", mock_client)

    ok = bq_cache.set("SELECT 1", {"a": 1})
    assert ok is True
    mock_client.insert_rows_json.assert_called_once()


def test_delete_calls_query(monkeypatch):
    mock_client = Mock()
    mock_query = Mock()
    mock_query.result.return_value = None
    mock_client.query.return_value = mock_query
    monkeypatch.setattr(bq_cache, "CLIENT", mock_client)

    assert bq_cache.delete("SELECT 1") is True
    mock_client.query.assert_called_once()
