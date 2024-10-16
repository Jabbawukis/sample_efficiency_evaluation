import logging
import os
import unittest
import shutil
from unittest.mock import patch, MagicMock

from sample_efficiency_evaluation.fact_matcher import FactMatcherSimpleHeuristic
from utility import utility


class FactMatcherTest(unittest.TestCase):

    def setUp(self) -> None:
        self.test_relation_info_dict = {
            "P6": {"domains": ["Political", "Biographical", "Historical"]},
            "P19": {"domains": ["Biographical"]},
        }
        self.test_entity_relation_info_dict = {
            "P6": {
                "Abu Dhabi": {
                    "aliases": ["Abū Dhabi", "Abudhabi"],
                    "obj_label": "Khalifa bin Zayed Al Nahyan",
                    "occurrences": 0,
                },
                "Armenia": {
                    "aliases": ["Republic of Armenia", "🇦🇲", "ARM", "AM"],
                    "obj_label": "Nikol Pashinyan",
                    "occurrences": 0,
                },
                "Free State of Fiume": {"aliases": [], "obj_label": "Gabriele D'Annunzio", "occurrences": 0},
                "Gülcemal Sultan": {"aliases": [], "obj_label": "Albania", "occurrences": 0},
                "Nepal": {
                    "aliases": ["NPL", "Federal Democratic Republic of Nepal", "NEP", "NP", "🇳🇵"],
                    "obj_label": "Khadga Prasad Sharma Oli",
                    "occurrences": 0,
                },
            }
        }
        self.maxDiff = None
        self.test_resources_abs_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "test_resources"))
        self.indexer_mocked = MagicMock()
        self.writer_mocked = MagicMock()
        self.test_index_dir = f"{self.test_resources_abs_path}/test_index_dir"
        if os.path.exists(self.test_index_dir):
            shutil.rmtree(self.test_index_dir)

    def test_extract_entity_information_good(self):
        with (
            patch.object(utility, "load_json_dict", return_value=self.test_relation_info_dict) as mock_load_json_dict,
            patch.object(logging, "error") as mock_error,
            patch.object(
                FactMatcherSimpleHeuristic, "_initialize_index", return_value=(self.writer_mocked, self.indexer_mocked)
            ),
        ):

            fact_matcher = FactMatcherSimpleHeuristic(
                bear_relation_info_path=f"{self.test_resources_abs_path}/relation_info.json",
                bear_facts_path=f"{self.test_resources_abs_path}/BEAR",
            )

            self.assertEqual(fact_matcher.entity_relation_info_dict, self.test_entity_relation_info_dict)
            mock_error.assert_called_once()
            mock_load_json_dict.assert_called_once_with(f"{self.test_resources_abs_path}/relation_info.json")

    def test_extract_entity_information_good2(self):
        with (
            patch.object(utility, "load_json_dict", return_value=self.test_relation_info_dict) as mock_load_json_dict,
            patch.object(logging, "error") as mock_error,
            patch.object(
                FactMatcherSimpleHeuristic, "_initialize_index", return_value=(self.writer_mocked, self.indexer_mocked)
            ),
        ):

            fact_matcher = FactMatcherSimpleHeuristic(bear_data_path=f"{self.test_resources_abs_path}")

            self.assertEqual(fact_matcher.entity_relation_info_dict, self.test_entity_relation_info_dict)
            mock_error.assert_called_once()
            mock_load_json_dict.assert_called_once_with(f"{self.test_resources_abs_path}/relation_info.json")

    def test_index_dataset_1(self):
        with (
            patch.object(utility, "load_json_dict", return_value=self.test_relation_info_dict),
            patch.object(
                FactMatcherSimpleHeuristic, "_initialize_index", return_value=(self.writer_mocked, self.indexer_mocked)
            ),
            patch.object(
                FactMatcherSimpleHeuristic,
                "_extract_entity_information",
                return_value=self.test_entity_relation_info_dict,
            ),
            patch.object(
                FactMatcherSimpleHeuristic,
                "index_file",
            ) as mock_index_file,
            patch.object(
                FactMatcherSimpleHeuristic,
                "commit_index",
            ) as mock_commit_index,
        ):

            fact_matcher = FactMatcherSimpleHeuristic(
                bear_data_path=f"{self.test_resources_abs_path}",
                file_index_dir=self.test_index_dir,
            )

            fact_matcher.index_dataset(
                [
                    {"text": "Boeing is a company. Boeing 747 is a plane."},
                    {"text": "Boeing 747 is a plane"},
                ],
                text_key="text",
                split_contents_into_sentences=False,
            )

            mock_index_file.assert_any_call("Boeing is a company. Boeing 747 is a plane.")
            mock_index_file.assert_any_call("Boeing 747 is a plane")
            self.assertEqual(mock_index_file.call_count, 2)

    def test_index_dataset_2(self):
        with (
            patch.object(utility, "load_json_dict", return_value=self.test_relation_info_dict),
            patch.object(
                FactMatcherSimpleHeuristic,
                "_extract_entity_information",
                return_value=self.test_entity_relation_info_dict,
            ),
            patch.object(
                FactMatcherSimpleHeuristic, "_initialize_index", return_value=(self.writer_mocked, self.indexer_mocked)
            ),
            patch.object(
                FactMatcherSimpleHeuristic,
                "index_file",
            ) as mock_index_file,
            patch.object(
                FactMatcherSimpleHeuristic,
                "commit_index",
            ) as mock_commit_index,
        ):

            fact_matcher = FactMatcherSimpleHeuristic(
                bear_data_path=f"{self.test_resources_abs_path}",
                file_index_dir=self.test_index_dir,
            )

            fact_matcher.index_dataset(
                [
                    {"text": "Boeing is a company. Boeing 747 is a plane."},
                    {"text": "Boeing 747 is a cool plane."},
                ],
                text_key="text",
                split_contents_into_sentences=True,
            )

            mock_index_file.assert_any_call("Boeing is a company.")
            mock_index_file.assert_any_call("Boeing 747 is a plane.")
            mock_index_file.assert_any_call("Boeing 747 is a cool plane.")
            self.assertEqual(mock_index_file.call_count, 3)

    def test_search_index(self):
        with (
            patch.object(utility, "load_json_dict", return_value=self.test_relation_info_dict),
            patch.object(
                FactMatcherSimpleHeuristic,
                "_extract_entity_information",
                return_value=self.test_entity_relation_info_dict,
            ),
        ):

            fact_matcher = FactMatcherSimpleHeuristic(
                bear_data_path=f"{self.test_resources_abs_path}",
                file_index_dir=self.test_index_dir,
            )

            fact_matcher.index_file("Boeing is a company")
            fact_matcher.index_file("Boeing 747 is a plane")
            fact_matcher.commit_index()
            results = fact_matcher.search_index("Boeing")
            self.assertEqual(len(results), 2)
            self.assertEqual(
                results,
                [
                    {
                        "path": "/ddda5959a6a4f994ee6a55c0e60b6137ea776e79846fc5a35d58ef0840005905",
                        "title": "ddda5959a6a4f994ee6a55c0e60b6137ea776e79846fc5a35d58ef0840005905",
                        "text": "Boeing is a company",
                    },
                    {
                        "path": "/1b4c34a604c95618ceb558da613bd8655d0a6a21ccaf0480dc150eff44d30047",
                        "title": "1b4c34a604c95618ceb558da613bd8655d0a6a21ccaf0480dc150eff44d30047",
                        "text": "Boeing 747 is a plane",
                    },
                ],
            )

    def test_search_index_sub_query_1(self):
        with (
            patch.object(utility, "load_json_dict", return_value=self.test_relation_info_dict),
            patch.object(
                FactMatcherSimpleHeuristic,
                "_extract_entity_information",
                return_value=self.test_entity_relation_info_dict,
            ),
        ):

            fact_matcher = FactMatcherSimpleHeuristic(
                bear_data_path=f"{self.test_resources_abs_path}",
                file_index_dir=self.test_index_dir,
            )

            fact_matcher.index_file("Boeing is a company")
            fact_matcher.index_file("Boeing 747 is a plane")
            fact_matcher.commit_index()
            results = fact_matcher.search_index("Boeing", sub_query="747")
            self.assertEqual(len(results), 1)
            self.assertEqual(
                results,
                [
                    {
                        "path": "/1b4c34a604c95618ceb558da613bd8655d0a6a21ccaf0480dc150eff44d30047",
                        "title": "1b4c34a604c95618ceb558da613bd8655d0a6a21ccaf0480dc150eff44d30047",
                        "text": "Boeing 747 is a plane",
                    }
                ],
            )

    def test_search_index_sub_query_2(self):
        with (
            patch.object(utility, "load_json_dict", return_value=self.test_relation_info_dict),
            patch.object(
                FactMatcherSimpleHeuristic,
                "_extract_entity_information",
                return_value=self.test_entity_relation_info_dict,
            ),
        ):

            fact_matcher = FactMatcherSimpleHeuristic(
                bear_data_path=f"{self.test_resources_abs_path}",
                file_index_dir=self.test_index_dir,
            )

            fact_matcher.index_file("Angela Merkel is the chancellor of Germany")
            fact_matcher.index_file("Boeing 747 is a plane")
            fact_matcher.commit_index()
            results = fact_matcher.search_index("Angela Merkel", sub_query="chancellor Germany")
            self.assertEqual(len(results), 1)
            self.assertEqual(
                results,
                [
                    {
                        "path": "/4640d50a3d19c3d61223ee8bee3f4615164524b78bbf06bb2f7c70a6e4ccc6d4",
                        "title": "4640d50a3d19c3d61223ee8bee3f4615164524b78bbf06bb2f7c70a6e4ccc6d4",
                        "text": "Angela Merkel is the chancellor of Germany",
                    }
                ],
            )
