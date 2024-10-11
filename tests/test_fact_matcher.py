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
                },
                "Armenia": {
                    "aliases": ["Republic of Armenia", "🇦🇲", "ARM", "AM"],
                    "obj_label": "Nikol Pashinyan",
                },
                "Free State of Fiume": {
                    "aliases": [],
                    "obj_label": "Gabriele D'Annunzio",
                },
                "Nepal": {
                    "aliases": [
                        "NPL",
                        "Federal Democratic Republic of Nepal",
                        "NEP",
                        "NP",
                        "🇳🇵",
                    ],
                    "obj_label": "Khadga Prasad Sharma Oli",
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

    def test_extract_entity_information(self):
        with patch.object(utility, "load_json_dict", return_value=self.test_relation_info_dict) as mock_load_json_dict, \
             patch.object(FactMatcherSimpleHeuristic, "initialize_index", return_value=(self.writer_mocked, self.indexer_mocked)):

            fact_matcher = FactMatcherSimpleHeuristic(
                bear_relation_info_path=f"{self.test_resources_abs_path}/relation_info.json",
                bear_data_path=f"{self.test_resources_abs_path}/BEAR",
            )

            self.assertEqual(fact_matcher.bear_relation_info_dict, self.test_relation_info_dict)
            self.assertEqual(fact_matcher.entity_relation_info_dict, self.test_entity_relation_info_dict)
            mock_load_json_dict.assert_called_once_with(f"{self.test_resources_abs_path}/relation_info.json")

    def test_search_index(self):
        with patch.object(utility, "load_json_dict", return_value=self.test_relation_info_dict):
            patch.object(FactMatcherSimpleHeuristic, "extract_entity_information", return_value=self.test_entity_relation_info_dict)

            fact_matcher = FactMatcherSimpleHeuristic(
                bear_relation_info_path=f"{self.test_resources_abs_path}/relation_info.json",
                bear_data_path=f"{self.test_resources_abs_path}/BEAR",
                file_index_dir=self.test_index_dir,
            )

            fact_matcher.index_file("Boeing is a company")
            fact_matcher.index_file("Boeing 747 is a plane")
            fact_matcher.commit_index()
            results = fact_matcher.search_index("Boeing")
            self.assertEqual(len(results), 2)
            self.assertEqual(results,
                             [{'path': '/ddda5959a6a4f994ee6a55c0e60b6137ea776e79846fc5a35d58ef0840005905',
                               'title': 'ddda5959a6a4f994ee6a55c0e60b6137ea776e79846fc5a35d58ef0840005905',
                               'content': 'Boeing is a company'},
                              {'path': '/1b4c34a604c95618ceb558da613bd8655d0a6a21ccaf0480dc150eff44d30047',
                               'title': '1b4c34a604c95618ceb558da613bd8655d0a6a21ccaf0480dc150eff44d30047',
                               'content': 'Boeing 747 is a plane'}])

    def test_search_index_sub_query(self):
        with patch.object(utility, "load_json_dict", return_value=self.test_relation_info_dict):
            patch.object(FactMatcherSimpleHeuristic, "extract_entity_information", return_value=self.test_entity_relation_info_dict)

            fact_matcher = FactMatcherSimpleHeuristic(
                bear_relation_info_path=f"{self.test_resources_abs_path}/relation_info.json",
                bear_data_path=f"{self.test_resources_abs_path}/BEAR",
                file_index_dir=self.test_index_dir,
            )

            fact_matcher.index_file("Boeing is a company")
            fact_matcher.index_file("Boeing 747 is a plane")
            fact_matcher.commit_index()
            results = fact_matcher.search_index("Boeing", sub_query="747")
            self.assertEqual(len(results), 1)
            self.assertEqual(results,
                             [{'path': '/1b4c34a604c95618ceb558da613bd8655d0a6a21ccaf0480dc150eff44d30047',
                               'title': '1b4c34a604c95618ceb558da613bd8655d0a6a21ccaf0480dc150eff44d30047',
                               'content': 'Boeing 747 is a plane'}])
