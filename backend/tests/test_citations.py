from app.agent.citations import validate

KNOWN = {"2005.11401", "2404.16130", "2407.01219"}


def test_valid_citations_are_kept_in_order():
    text, cited = validate("GraphRAG [2404.16130] builds on RAG [2005.11401].", KNOWN)
    assert text == "GraphRAG [2404.16130] builds on RAG [2005.11401]."
    assert cited == ["2404.16130", "2005.11401"]


def test_garbled_id_is_repaired():
    text, cited = validate("Best practices [2-407.01219].", KNOWN)
    assert text == "Best practices [2407.01219]."
    assert cited == ["2407.01219"]


def test_unknown_ids_are_removed():
    text, cited = validate("A made-up claim [2401.99999]. Real one [2005.11401].", KNOWN)
    assert "2401.99999" not in text
    assert text == "A made-up claim. Real one [2005.11401]."
    assert cited == ["2005.11401"]


def test_grouped_and_prefixed_citations():
    text, cited = validate("Both [arXiv:2005.11401, 2404.16130, 2101.00000].", KNOWN)
    assert text == "Both [2005.11401, 2404.16130]."
    assert cited == ["2005.11401", "2404.16130"]


def test_placeholder_and_markdown_links_untouched_or_removed():
    text, _ = validate("See [the paper](https://arxiv.org/abs/2005.11401) [arxiv_id]", KNOWN)
    assert text == "See [the paper](https://arxiv.org/abs/2005.11401)"


def test_table_cells_keep_citations():
    text, cited = validate("| GraphRAG | [2404.16130] | graphs |", KNOWN)
    assert "[2404.16130]" in text
    assert cited == ["2404.16130"]
