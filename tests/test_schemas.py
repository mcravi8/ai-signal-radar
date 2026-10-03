import copy
import json
import unittest
from pathlib import Path

from pipeline.export_public import PUBLIC_SCHEMA_FILES, PublicDataError, validate_schema


ROOT = Path(__file__).resolve().parents[1]


class PublicSchemaTests(unittest.TestCase):
    def test_every_public_dataset_has_a_schema_and_validates(self):
        public_files = {path.name for path in (ROOT / "data/public").glob("*.json")}
        self.assertEqual(public_files, set(PUBLIC_SCHEMA_FILES))
        for dataset_name, schema_name in PUBLIC_SCHEMA_FILES.items():
            with self.subTest(dataset=dataset_name):
                payload = json.loads((ROOT / "data/public" / dataset_name).read_text(encoding="utf-8"))
                validate_schema(payload, ROOT / "schemas" / schema_name)

    def test_missing_required_section_is_rejected_for_every_dataset(self):
        for dataset_name, schema_name in PUBLIC_SCHEMA_FILES.items():
            with self.subTest(dataset=dataset_name):
                payload = json.loads((ROOT / "data/public" / dataset_name).read_text(encoding="utf-8"))
                invalid = copy.deepcopy(payload)
                invalid.pop(next(iter(invalid)))
                with self.assertRaises(PublicDataError):
                    validate_schema(invalid, ROOT / "schemas" / schema_name)

    def test_nested_research_contract_is_enforced(self):
        payload = json.loads((ROOT / "data/public/research.json").read_text(encoding="utf-8"))
        invalid = copy.deepcopy(payload)
        invalid["evidence"][0].pop("publisher_id")
        with self.assertRaisesRegex(PublicDataError, "publisher_id"):
            validate_schema(invalid, ROOT / "schemas" / PUBLIC_SCHEMA_FILES["research.json"])


if __name__ == "__main__":
    unittest.main()
