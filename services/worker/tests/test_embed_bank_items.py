from app.jobs import embed_bank_items


def test_embed_bank_items_persists_each_item_in_bounded_batch(monkeypatch):
    rows = [{"id": "a", "prompt": "A"}, {"id": "b", "prompt": "B"}]
    selects, updates = [], []
    monkeypatch.setattr(embed_bank_items.db, "select", lambda table, params: selects.append((table, params)) or rows)
    monkeypatch.setattr(embed_bank_items.db, "update", lambda *args: updates.append(args) or [{}])
    monkeypatch.setattr(embed_bank_items, "embed", lambda text: [0.1] * 1024)

    result = embed_bank_items.run(institution_id="inst")

    assert result == {"attempted": 2, "embedded": 2, "failed": 0, "remaining": False}
    assert selects[0][1]["origin"] == "eq.bank"
    assert selects[0][1]["retired_at"] == "is.null"
    assert len(updates) == 2
    assert all(update[2]["embedded_at"] for update in updates)


def test_embed_bank_items_continues_after_an_item_failure(monkeypatch):
    monkeypatch.setattr(embed_bank_items.db, "select", lambda *args: [
        {"id": "bad", "prompt": "bad"}, {"id": "good", "prompt": "good"},
    ])
    updated = []
    monkeypatch.setattr(embed_bank_items.db, "update", lambda *args: updated.append(args) or [{}])
    monkeypatch.setattr(embed_bank_items, "embed", lambda text: (_ for _ in ()).throw(ValueError("bad"))
                        if text == "bad" else [0.1] * 1024)
    result = embed_bank_items.run()
    assert result["failed"] == 1
    assert result["embedded"] == 1
    assert updated[0][1]["id"] == "eq.good"
