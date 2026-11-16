from app.core.static import static_version


def test_static_version_is_independent_of_root_and_file_creation_order(tmp_path):
    first, second = tmp_path / "first", tmp_path / "second"
    first.mkdir()
    second.mkdir()
    for root, order in ((first, ["a.js", "b.js"]), (second, ["b.js", "a.js"])):
        for name in order:
            (root / name).write_text(f"export const name = '{name}';")
    assert static_version(first) == static_version(second)


def test_changing_a_nested_dependency_versions_all_asset_urls(tmp_path):
    nested = tmp_path / "js" / "admin"
    nested.mkdir(parents=True)
    (tmp_path / "js" / "entry.js").write_text("import './admin/actions.js';")
    dependency = nested / "actions.js"
    dependency.write_text("export const action = 1;")
    before = static_version(tmp_path)
    dependency.write_text("export const action = 2;")
    assert static_version(tmp_path) != before
