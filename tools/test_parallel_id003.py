"""Fast shard protocol tests in the locked Meep environment."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"simulations"/"meep"))
import robust_coupler_v003 as c


class ShardTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        self.specs=c.search_specs()
        for i,spec in enumerate(self.specs):
            rows=[dict(zip(("resolution","length_um","gap_um","width_bias_um",
                           "wavelength_um"),key),objective_error=0.1+i*0.01)
                  for key in spec]
            c.write_json(self.root/f"id003-search-{i}"/"shard.json",
                dict(stage="search",index=i,provenance=c.provenance(),rows=rows))

    def tearDown(self):
        self.temp.cleanup()

    def test_complete_and_deterministic(self):
        rows=c.read_shards(self.root,"search",self.specs)
        self.assertEqual(sum(map(len,rows)),36)
        winners=c.choose(rows)
        self.assertEqual(winners,{"nominal":(2.,0.2),"robust":(2.,0.2)})
        self.assertEqual(len(c.validation_specs(winners)),18)
        self.assertEqual(len(c.validation_specs({"nominal":(2.,0.2),"robust":(6.,0.35)})),36)

    def mutate(self,fn):
        path=self.root/"id003-search-0"/"shard.json"
        data=json.loads(path.read_text())
        fn(data)
        c.write_json(path,data)

    def test_missing_shard(self):
        (self.root/"id003-search-0"/"shard.json").unlink()
        with self.assertRaises(ValueError):
            c.read_shards(self.root,"search",self.specs)

    def test_wrong_scenario(self):
        self.mutate(lambda d:d["rows"][0].update(width_bias_um=0.03))
        with self.assertRaises(ValueError):
            c.read_shards(self.root,"search",self.specs)

    def test_wrong_provenance(self):
        self.mutate(lambda d:d["provenance"].update(run_id="wrong"))
        with self.assertRaises(ValueError):
            c.read_shards(self.root,"search",self.specs)

    def test_duplicate_row(self):
        self.mutate(lambda d:d["rows"].append(d["rows"][0]))
        with self.assertRaises(ValueError):
            c.read_shards(self.root,"search",self.specs)

    def test_unexpected_shard(self):
        c.write_json(self.root/"id003-search-99"/"shard.json",{})
        with self.assertRaises(ValueError):
            c.read_shards(self.root,"search",self.specs)


if __name__=="__main__":
    unittest.main()
