import pytest

from st_vtt.patch import PatchError, apply_patch, get_pointer


def test_set_nested_creates_intermediates():
    d = {}
    apply_patch(d, "/moves/pips/x", 2)
    assert d == {"moves": {"pips": {"x": 2}}}


def test_list_append_and_index():
    d = {"items": []}
    apply_patch(d, "/items/-", {"n": 1})
    apply_patch(d, "/items/-", {"n": 2})
    apply_patch(d, "/items/0/n", 9)
    assert [i["n"] for i in d["items"]] == [9, 2]
    apply_patch(d, "/items/0", op="remove")
    assert d["items"] == [{"n": 2}]
    with pytest.raises(PatchError):
        apply_patch(d, "/items/5", 1)


def test_escapes_and_get():
    d = {"a/b": {"~": 1}}
    assert get_pointer(d, "/a~1b/~0") == 1


def test_remove_missing_key():
    with pytest.raises(PatchError):
        apply_patch({"a": 1}, "/b", op="remove")


def test_bad_pointer():
    with pytest.raises(PatchError):
        apply_patch({}, "a/b", 1)


def test_list_ops_idempotent():
    d = {}
    apply_patch(d, "/moves/taken", "a", "list_add")
    apply_patch(d, "/moves/taken", "a", "list_add")
    apply_patch(d, "/moves/taken", "b", "list_add")
    assert d["moves"]["taken"] == ["a", "b"]
    apply_patch(d, "/moves/taken", "a", "list_remove")
    apply_patch(d, "/moves/taken", "zzz", "list_remove")
    assert d["moves"]["taken"] == ["b"]
    with pytest.raises(PatchError):
        apply_patch({"x": 1}, "/x", "a", "list_add")


def test_text_patch_merges_concurrent_edits():
    from diff_match_patch import diff_match_patch

    dmp = diff_match_patch()
    base = "The mill burned.\nOld Mab is missing."
    a = "The mill burned last night.\nOld Mab is missing."
    b = "The mill burned.\nOld Mab is missing. Bryn went looking."
    doc = {"notes": base}
    pa = dmp.patch_toText(dmp.patch_make(base, a))
    pb = dmp.patch_toText(dmp.patch_make(base, b))
    apply_patch(doc, "/notes", op="text_patch", patch=pa)
    merged = apply_patch(doc, "/notes", op="text_patch", patch=pb)
    assert merged == "The mill burned last night.\nOld Mab is missing. Bryn went looking."
    assert doc["notes"] == merged
    # patching a missing field starts from ""
    d2 = {}
    apply_patch(d2, "/notes", op="text_patch", patch=dmp.patch_toText(dmp.patch_make("", "hi")))
    assert d2["notes"] == "hi"
    with pytest.raises(PatchError):
        apply_patch({"n": 3}, "/n", op="text_patch", patch=pa)
