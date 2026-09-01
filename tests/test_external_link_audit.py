from scripts.audit_external_links import extract_links


def test_extract_links_records_source_and_trims_sentence_punctuation(tmp_path):
    document = tmp_path / "sample.md"
    document.write_text(
        "See [paper](https://example.org/paper).\n"
        "Again https://example.org/paper, and https://example.org/code!\n",
        encoding="utf-8",
    )

    inventory = extract_links([document])

    assert set(inventory) == {
        "https://example.org/paper",
        "https://example.org/code",
    }
    assert [entry["line"] for entry in inventory["https://example.org/paper"]] == [1, 2]
