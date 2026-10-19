import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
from reuse_build import reuse


class ReuseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.project = Path(self.temp.name)
        self.build = "bld_TEST1234567890"
        self.timing = {"words": [{"text": "不要", "start": 1, "end": 2}], "media_sha256": "fixture"}
        (self.project/"timing.json").write_text(json.dumps({"kind": "inline", "value": self.timing}))
        self.result = self.project/".hypit/results/2026-10-19"/self.build
        self.result.mkdir(parents=True)
        (self.result/"timing-value.json").write_text(json.dumps({"format": "hypit.result-value@1", "value": self.timing, "resources": []}))
        (self.result/"result.json").write_text(json.dumps({"outputs": {
            "timing.timing": {"value": {"kind": "value", "path": "timing-value.json"}},
            "prepared.media": {"value": {"kind": "value", "path": "unused.json"}}}}))
        self.source = self.project/"render.svrun"
        self.source.write_text('<?svml using="@hypit/markup/run@1"?><svrun version="1"><author source="./production.svml"/><target output="final.video"/><value id="reuse-1234567890-0" type="@koubo/reviewed-alignment@1#Timing" from="./timing.json"/></svrun>')
        self.dest = self.project/"reuse.svrun"

    def tearDown(self):
        self.temp.cleanup()

    def test_unrelated_candidate_and_unique_ids(self):
        reuse(self.project,self.build,self.source,self.dest,["prepared.media"])
        self.assertIn('id="reuse-1234567890-0-next"',self.dest.read_text())
        self.assertIn('id="reuse-1234567890-0"',self.dest.read_text())

    def test_changed_speech_refuses_stale_reuse(self):
        (self.project/"timing.json").write_text(json.dumps({"value": {"words": [{"text": "可以"}]}}))
        with self.assertRaisesRegex(ValueError,"已改变"):
            reuse(self.project,self.build,self.source,self.dest,["prepared.media"])
        self.assertFalse(self.dest.exists())

    def test_saved_alignment_chain_retains_evidence_check(self):
        chained="bld_SECOND"
        folder=self.result.parent/chained;folder.mkdir()
        (folder/"result.json").write_text(json.dumps({"outputs":{
            "alignment.alignment":{"value":{"kind":"build-output","build":self.build,"output":"alignment.alignment"}},
            "prepared.media":{"value":{"kind":"build-output","build":self.build,"output":"prepared.media"}}}}))
        reuse(self.project,chained,self.source,self.dest,["prepared.media"])
        self.assertIn('build="bld_SECOND"',self.dest.read_text())


if __name__ == "__main__":
    unittest.main()
