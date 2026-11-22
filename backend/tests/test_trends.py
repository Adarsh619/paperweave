from app.tools.graph_query import growth, rising_methods


def test_growth_compares_last_two_complete_years_with_the_two_before():
    years, counts = [2021, 2022, 2023, 2024, 2025, 2026], [100, 100, 150, 250, 50, 10]
    # this_year=2026 is partial and ignored: (150+250) vs (100+100) -> +100%
    assert growth(years, counts, this_year=2025) == (150 + 250 - 200) / 200
    assert growth(years, counts, this_year=2026) == (250 + 50 - (100 + 150)) / 250


def test_growth_needs_four_complete_years():
    assert growth([2024, 2025], [10, 20], this_year=2026) is None
    assert growth([2021, 2022, 2023, 2024], [0, 0, 5, 5], this_year=2025) is None  # no prior volume


def test_rising_methods_ranks_by_share_change_and_needs_support():
    periods = {"recent": 100, "earlier": 50}
    rows = [
        {"period": "recent", "method": "Diffusion", "papers": 30},
        {"period": "earlier", "method": "Diffusion", "papers": 5},   # 10% -> 30%
        {"period": "recent", "method": "GAN", "papers": 5},
        {"period": "earlier", "method": "GAN", "papers": 20},        # 40% -> 5%
        {"period": "recent", "method": "Rare", "papers": 2},         # below support
    ]
    out = rising_methods(periods, rows)
    assert [m["method"] for m in out] == ["Diffusion", "GAN"]
    assert round(out[0]["change"], 2) == 0.20 and round(out[1]["change"], 2) == -0.35
    assert rising_methods({"recent": 10}, rows) == []  # no earlier period, no comparison


def test_resolve_scope_prefers_exact_field_over_topic_substring(monkeypatch):
    from app import stores
    from app.tools import graph_query
    rows = [{"topic": "Machine learning for physics", "field": "Physics"},
            {"topic": "Quantum computing", "field": "Physics"}]
    monkeypatch.setattr(stores, "read", lambda *a, **k: rows)
    assert graph_query.resolve_scope("Physics") == ("Physics", None)
    assert graph_query.resolve_scope("what is trending in quantum computing?") == (None, "Quantum computing")


def test_topic_phrase_reads_the_topic_from_the_question():
    from app.agent.nodes import _topic_phrase
    assert _topic_phrase("What are the most cited papers on hallucination since 2023?") == "hallucination"
    assert _topic_phrase("Most cited papers about graph neural networks?") == "graph neural networks"
    assert _topic_phrase("Which papers are most cited in the corpus?") is None
