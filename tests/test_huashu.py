import copy
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).parents[1]/"scripts"))
from huashu_backend import prepare,validate_edit,attach,inspect,render,locate
from production import read,write,fingerprint


class HuashuTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.edit={"edit_key":"cut-v1","fps":30,"request":{"mode":"produce","pace":"自然","pause_policy":"保留气口","must_keep":[]},
                   "tokens":[{"id":"a","text":"再","start":17,"end":17.4},{"id":"b","text":"解释。","start":18,"end":20}]}
        self.motion={"purpose":"解释当前观点","clips":[{"id":"proof","grammar":"t2_keynote_ui","theme":"paper","first":"a","last":"b","size":[640,360],"frame":[.05,.1,.95,.4],
            "cues":[{"token":"a","kind":"card","text":"具体证据"},{"token":"b","kind":"card","text":"说明含义"}]}]}

    def tearDown(self):self.tmp.cleanup()

    def test_semantic_cues_use_edited_not_source_time(self):
        result=prepare(self.edit,self.motion,self.root)
        clip=result["clips"][0]
        self.assertEqual(clip["edit_start_frame"],510)
        self.assertEqual([c["at"] for c in clip["spec"]["cues"]],[0,1])
        self.assertEqual(clip["spec"]["duration"],3)

    def test_changed_speech_or_cut_invalidates_project(self):
        project=prepare(self.edit,self.motion,self.root)
        changed=copy.deepcopy(self.edit);changed["tokens"][0]["start"]=16
        with self.assertRaisesRegex(ValueError,"锚点已变"):validate_edit(project,changed)

    def test_missing_preferences_do_not_prepare(self):
        self.edit["request"]={"mode":"produce"}
        with self.assertRaisesRegex(ValueError,"偏好未答完"):prepare(self.edit,self.motion,self.root)
        self.assertFalse((self.root/"motion-project.json").exists())

    def test_analysis_does_not_prepare(self):
        self.edit["request"]["mode"]="analysis"
        with self.assertRaisesRegex(ValueError,"只分析"):prepare(self.edit,self.motion,self.root)

    def test_plan_does_not_render(self):
        self.edit["request"]["mode"]="plan";prepare(self.edit,self.motion,self.root)
        with patch("huashu_backend.subprocess.run",side_effect=AssertionError("render called")):
            with self.assertRaisesRegex(ValueError,"方案不渲染"):render(self.root,self.edit,"unused","unused","unused","unused")

    def test_analysis_request_cannot_run_existing_production_project(self):
        prepare(self.edit,self.motion,self.root)
        self.edit["request"]["mode"]="analysis"
        with patch("huashu_backend.subprocess.run",side_effect=AssertionError("render called")):
            with self.assertRaisesRegex(ValueError,"只分析"):render(self.root,self.edit,"unused","unused","unused","unused")

    def test_plan_request_cannot_run_existing_production_project(self):
        prepare(self.edit,self.motion,self.root)
        self.edit["request"]["mode"]="plan"
        with patch("huashu_backend.subprocess.run",side_effect=AssertionError("render called")):
            with self.assertRaisesRegex(ValueError,"方案不渲染"):render(self.root,self.edit,"unused","unused","unused","unused")

    def test_reference_seconds_are_not_accepted(self):
        self.motion["clips"][0]["cues"][0]["at"]=21
        with self.assertRaisesRegex(ValueError,"不接受原秒数"):prepare(self.edit,self.motion,self.root)

    def test_unknown_grammar_not_executed(self):
        self.motion["clips"][0]["grammar"]="../../anything"
        with self.assertRaisesRegex(ValueError,"受支持"):prepare(self.edit,self.motion,self.root)

    def test_whiteboard_pen_is_explicit_and_hidden_option_survives(self):
        clip=self.motion["clips"][0];clip["grammar"]="y3_whiteboard"
        for cue in clip["cues"]:cue["kind"]="point"
        with self.assertRaisesRegex(ValueError,"白板须明确"):prepare(self.edit,self.motion,self.root)
        clip["pen"]="hidden"
        self.assertEqual(prepare(self.edit,self.motion,self.root)["clips"][0]["spec"]["koubo_pen"],"hidden")

    def test_remote_image_not_downloaded(self):
        self.motion["clips"][0]["cues"][0]["image"]="https://example.com/private.png"
        with self.assertRaisesRegex(ValueError,"不联网"):prepare(self.edit,self.motion,self.root)

    def test_long_clip_requires_new_shots(self):
        self.edit["tokens"][1]["end"]=30
        with self.assertRaisesRegex(ValueError,"8 秒"):prepare(self.edit,self.motion,self.root)

    def test_number_requires_settle_anchor_and_preroll(self):
        self.motion["clips"][0]["cues"][0].update({"kind":"number","data":{"value":3}})
        with self.assertRaisesRegex(ValueError,"落定"):prepare(self.edit,self.motion,self.root)

    def test_attach_preserves_existing_scene_and_checks_media(self):
        prepare(self.edit,self.motion,self.root)
        media=self.root/"motion.mp4";media.write_bytes(b"synthetic fixture")
        write(self.root/"rendered-scenes.json",[{"id":"proof","media":str(media),"media_sha256":fingerprint(media),"first":"a","last":"b","frame":[.05,.1,.95,.4],"cache_hit":False}])
        existing=[{"id":"kept","first":"a","last":"b","label":"原有画面"}]
        result=attach(self.root,self.edit,existing,self.root/"scenes.json")
        self.assertEqual(result[0],existing[0]);self.assertEqual(result[1]["first"],"a")
        media.write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError,"文件已变化"):attach(self.root,self.edit,[],self.root/"new.json")

    def test_attach_does_not_overwrite_id(self):
        prepare(self.edit,self.motion,self.root)
        write(self.root/"rendered-scenes.json",[{"id":"proof"}])
        with self.assertRaisesRegex(ValueError,"ID 冲突"):attach(self.root,self.edit,[{"id":"proof"}],self.root/"new.json")

    def test_alternative_clips_require_explicit_selection(self):
        alternative=copy.deepcopy(self.motion["clips"][0]);alternative["id"]="alternative"
        self.motion["clips"].append(alternative);prepare(self.edit,self.motion,self.root)
        media=self.root/"motion.mp4";media.write_bytes(b"synthetic fixture")
        rendered=[{"id":c["id"],"first":"a","last":"b","frame":c["frame"],"media":str(media),"media_sha256":fingerprint(media)} for c in self.motion["clips"]]
        write(self.root/"rendered-scenes.json",rendered)
        with self.assertRaisesRegex(ValueError,"重叠"):attach(self.root,self.edit,[],self.root/"new.json")
        self.assertEqual([s["id"] for s in attach(self.root,self.edit,[],self.root/"new.json",["alternative"])],["alternative"])
        with self.assertRaisesRegex(ValueError,"不存在"):attach(self.root,self.edit,[],self.root/"new.json",["missing"])

    def test_missing_dependency_is_actionable(self):
        with self.assertRaisesRegex(ValueError,"提供 --root"):locate(self.root/"missing")

    def test_modified_engine_requires_review(self):
        prepare(self.edit,self.motion,self.root)
        with patch("huashu_backend.inspect",return_value={"engine_fingerprint":"new"}):
            with self.assertRaisesRegex(ValueError,"已审阅指纹不符"):render(self.root,self.edit,"unused","unused","unused","old")


if __name__=="__main__":unittest.main()
