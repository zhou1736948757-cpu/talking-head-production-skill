import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
from production import candidates, chinese_cues, digest, fingerprint, import_transcript, make_edit, questions, script_text, script_escape, export_hypit
from hypit_backend import HypitBackend


class ProductionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.media = Path(self.tmp.name) / "source.mp4"
        self.media.write_bytes(b"non-private-test-content")
        self.transcript = import_transcript({"words": [
            {"id": "a", "text": "不要", "start": 1, "end": 2},
            {"id": "b", "text": "删除。", "start": 4, "end": 5},
            {"id": "c", "text": "限定。", "start": 7, "end": 8}]}, self.media)
        self.request = {"mode": "produce", "pace": "用户自述：自然慢讲", "pause_policy": "保留呼吸与语义停顿", "must_keep": ["a"]}
        self.probe = patch("production.probe", return_value={"duration": 10, "width": 360, "height": 640, "has_audio": True})
        self.probe.start()

    def tearDown(self):
        self.probe.stop(); self.tmp.cleanup()

    def edit(self, request=None):
        return make_edit(self.media, self.transcript, request or self.request)

    def test_no_default_strategy(self):
        with self.assertRaisesRegex(ValueError, "待用户回答"):
            self.edit({"mode": "produce"})
        self.assertEqual(len(questions({"mode": "plan"})), 3)

    def test_known_answers_not_reasked(self):
        self.assertEqual(questions(self.request), [])
        self.assertEqual(len(questions({"mode": "plan", "pace": "标准"})), 2)

    def test_analysis_no_renderer(self):
        with patch("production.subprocess.run", side_effect=AssertionError("render called")):
            self.assertEqual(questions({"mode": "analysis"}), [])
            with self.assertRaisesRegex(ValueError, "纯分析"):
                self.edit({"mode": "analysis"})

    def test_breath_candidates_are_kept(self):
        gaps = candidates(self.transcript)
        self.assertEqual(len(gaps), 2)
        self.assertTrue(all(g["decision"] == "keep" for g in gaps))
        self.assertEqual(self.edit()["output_frames"], 300)

    def test_cut_rebases_all_later_anchors(self):
        req = {**self.request, "cuts": [{"start": 2, "end": 4, "action": "delete", "reason": "审听确认可去的长空白", "approved": True}]}
        edit = self.edit(req)
        self.assertEqual(edit["output_frames"], 240)
        self.assertEqual(edit["tokens"][1]["start"], 2)
        self.assertEqual(edit["tokens"][2]["start"], 5)
        body = script_text(edit, [{"id": "proof", "first": "b", "last": "c"}])
        self.assertIn("@{proof}@{proof-enter!}", body)
        self.assertEqual(edit["time_map"][1]["source_start_frame"], 120)
        self.assertEqual(edit["time_map"][1]["output_start_frame"], 60)

    def test_deletion_requires_review(self):
        req = {**self.request, "cuts": [{"start": 2, "end": 4, "action": "delete", "reason": "候选"}]}
        with self.assertRaisesRegex(ValueError, "approved"):
            self.edit(req)

    def test_word_cannot_be_cut_in_half(self):
        req = {**self.request, "cuts": [{"start": 4.5, "end": 6, "action": "delete", "reason": "测试", "approved": True}]}
        with self.assertRaisesRegex(ValueError, "截断词"):
            self.edit(req)

    def test_protected_pause_is_not_deleted(self):
        req = {**self.request, "protected_ranges": [{"start": 2.5, "end": 3}], "cuts": [{"start": 2, "end": 4, "action": "delete", "reason": "测试", "approved": True}]}
        with self.assertRaisesRegex(ValueError, "必须保留的片段"):
            self.edit(req)

    def test_required_negation_stays(self):
        req = {**self.request, "cuts": [{"start": 0, "end": 3, "action": "delete", "reason": "测试", "approved": True}]}
        with self.assertRaisesRegex(ValueError, "必须保留"):
            self.edit(req)

    def test_changed_media_invalidates_cache(self):
        old = self.transcript["cache_key"]
        self.media.write_bytes(b"replacement")
        with self.assertRaisesRegex(ValueError, "指纹"):
            self.edit()
        new = import_transcript({"words": self.transcript["tokens"]}, self.media)
        self.assertNotEqual(new["cache_key"], old)

    def test_track_and_language_in_cache(self):
        payload = {"words": self.transcript["tokens"]}
        a = import_transcript(payload, self.media, 0, "zh")
        b = import_transcript(payload, self.media, 1, "zh")
        c = import_transcript(payload, self.media, 0, "en")
        self.assertEqual(len({a["cache_key"], b["cache_key"], c["cache_key"]}), 3)

    def test_missing_timing_never_estimated(self):
        with self.assertRaisesRegex(ValueError, "禁止估填"):
            import_transcript({"words": [{"text": "未知", "start": 1}]}, self.media)

    def test_chinese_breaks_by_characters_and_punctuation(self):
        cues = chinese_cues(self.transcript["tokens"], max_chars=5)
        self.assertEqual([[w["id"] for w in cue] for cue in cues], [["a"], ["b"], ["c"]])
        self.assertIn(" || ", script_text(self.edit(), []))

    def test_style_changes_do_not_change_material_key(self):
        edit = self.edit(); changed = copy.deepcopy(edit)
        changed["request"]["style"] = {"accent": "#000000"}
        self.assertEqual(edit["edit_key"], changed["edit_key"])

    def test_local_backend_rejects_remote_endpoint(self):
        profile = Path(self.tmp.name) / "profile.json"
        profile.write_text(json.dumps({"credentials": {}, "endpoints": {"x": {"use": "@hypit/provider-hypihub"}}}))
        with self.assertRaisesRegex(ValueError, "无凭据"):
            HypitBackend().invoke(Path(self.tmp.name), "build", profile)

    def test_transcript_markup_stays_literal(self):
        self.assertEqual(script_escape("@{proof}a|b"), r"\@\{proof\}a\|b")

    def test_audio_track_mismatch_rejected(self):
        with self.assertRaisesRegex(ValueError, "音轨"):
            self.edit({**self.request, "audio_track": 1})

    def test_stale_roughcut_cannot_be_exported(self):
        root = Path(self.tmp.name)
        rough = root / "rough.mp4"; rough.write_bytes(b"old cut")
        font = root / "font.ttf"; font.write_bytes(b"font fixture")
        Path(str(rough)+".provenance.json").write_text(json.dumps({"edit_key": "old edit", "media_sha256": fingerprint(rough)}))
        with self.assertRaisesRegex(ValueError, "不是当前 edit"):
            export_hypit(self.edit(), rough, root / "project", font)

    def test_script_change_cannot_bypass_alignment_with_reuse(self):
        root = Path(self.tmp.name)
        (root / "assets").mkdir()
        media = root / "assets/roughcut.mp4"; media.write_bytes(b"current cut")
        (root / "timing.json").write_text(json.dumps({"value": {"media_sha256": fingerprint(media)}}))
        (root / "anchors.json").write_text(json.dumps({"script_digest": digest("原话")}))
        (root / "production.svml").write_text('<script id="story"><speech>改话</speech></script>')
        profile = root / "profile.json"; profile.write_text(json.dumps({"credentials": {}, "endpoints": {}}))
        with self.assertRaisesRegex(ValueError, "Script 已变化"):
            HypitBackend(run="reuse.svrun").invoke(root, "build", profile)


if __name__ == "__main__":
    unittest.main()
