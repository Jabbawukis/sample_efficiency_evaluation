from abc import ABC, abstractmethod
from typing import Union
from more_itertools import windowed

import spacy
from datasets import DatasetDict, Dataset, IterableDatasetDict, IterableDataset
from tqdm import tqdm
from spacy.lang.en import English

from utility import utility
from utility.utility import word_in_sentence


class FactMatcherBase(ABC):
    """
    FactMatcherBase
    """

    def __init__(self, **kwargs):
        """
        Initialize FactMatcherBase class.
        """

        bear_data_path = kwargs.get("bear_data_path")

        self.entity_relation_info_dict: dict = utility.extract_entity_information(
            bear_data_path=kwargs.get("bear_facts_path", f"{bear_data_path}/BEAR"),
            bear_relation_info_path=kwargs.get("bear_relation_info_path", f"{bear_data_path}/relation_info.json"),
        )

        self.save_file_content = kwargs.get("save_file_content", False)

        self.nlp = English()

        self.tokenizer = self.nlp.tokenizer

        self.nlp.add_pipe("sentencizer")

    def convert_relation_info_dict_to_json(self, file_path: str) -> None:
        """
        Convert relation info dictionary to json file.

        :param file_path: Path to save the json file.
        :return:
        """
        utility.save_json_dict(self.entity_relation_info_dict, file_path)

    @abstractmethod
    def create_fact_statistics(
        self,
        file_contents: Union[DatasetDict, Dataset, IterableDatasetDict, IterableDataset],
        text_key: str = "text",
    ) -> None:
        """
        Create fact statistics
        """


class FactMatcherSimple(FactMatcherBase):
    """
    FactMatcherSimple is a class that uses a simple search by string heuristic to search for entities in the dataset.

    kwargs:
        - bear_data_path [str]: Path to bear data directory.
            This is the main directory where all the bear data is stored. It should contain the relation_info.json file
            and the BEAR facts directory.

        - bear_relation_info_path [Optional[str]]: Path to the BEAR relation info file.
            This file contains the relation information for the BEAR data. If not provided, it will be set to
            {bear_data_path}/relation_info.json.

        - bear_facts_path [Optional[str]]: Path to the BEAR facts directory.
            This is the directory where all the BEAR fact files (.jsonl) are stored. If not provided, it will be set to
            {bear_data_path}/BEAR. Note that the dataset provides a BEAR and a BEAR-big directory, with the latter
            containing more facts.

        - save_file_content [Optional[bool]]: If True, the content of the file where the entity is found will be saved
            in the relation dictionary. The default is False.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.relation_mapping_dict = self._create_mapped_relations()
        self.relation_sentence_dict = {}

    def _create_mapped_relations(self) -> dict:
        mapped_relations = {}
        for relation_id, relation_info in self.entity_relation_info_dict.items():
            for entity_id, entity_info in relation_info.items():
                try:
                    mapped_relations[entity_info["subj_label"].lower()]["relations"].add((relation_id, entity_id))
                except KeyError:
                    mapped_relations[entity_info["subj_label"].lower()] = {"relations": {(relation_id, entity_id)}}
                for alias in entity_info["subj_aliases"]:
                    try:
                        mapped_relations[alias.lower()]["relations"].add((relation_id, entity_id))
                    except KeyError:
                        mapped_relations[alias.lower()] = {"relations": {(relation_id, entity_id)}}
        return mapped_relations

    def _add_occurrences(self, ngram: str, sentence: str) -> None:
        for relation_subj_tuple in self.relation_mapping_dict[ngram]["relations"]:

            relation_id = relation_subj_tuple[0]
            subj_id = relation_subj_tuple[1]

            obj_label = self.entity_relation_info_dict[relation_id][subj_id]["obj_label"]
            obj_aliases = self.entity_relation_info_dict[relation_id][subj_id]["obj_aliases"]

            if word_in_sentence(obj_label, sentence):
                try:
                    if sentence in self.relation_sentence_dict[subj_id][relation_id]:
                        continue
                    self.relation_sentence_dict[subj_id][relation_id].update([sentence])
                except KeyError:
                    self.relation_sentence_dict[subj_id] = {relation_id: {sentence}}
                self.entity_relation_info_dict[relation_id][subj_id]["occurrences"] = len(
                    self.relation_sentence_dict[subj_id][relation_id]
                )
                if self.save_file_content:
                    self.entity_relation_info_dict[relation_id][subj_id]["sentences"].update([sentence])
                continue
            for alias in obj_aliases:
                if word_in_sentence(alias, sentence):
                    try:
                        if sentence in self.relation_sentence_dict[subj_id][relation_id]:
                            break
                        self.relation_sentence_dict[subj_id][relation_id].update([sentence])
                    except KeyError:
                        self.relation_sentence_dict[subj_id] = {relation_id: {sentence}}
                    self.entity_relation_info_dict[relation_id][subj_id]["occurrences"] = len(
                        self.relation_sentence_dict[subj_id][relation_id]
                    )
                    if self.save_file_content:
                        self.entity_relation_info_dict[relation_id][subj_id]["sentences"].update([sentence])

    def _process_file_content(self, file_content: str) -> None:
        """
        Process file content.

        :param file_content: File content to process.
        :return:
        """
        content = utility.clean_string(file_content)
        split_doc = self.nlp(content)
        sentences = [sent.text for sent in split_doc.sents]
        for sentence in sentences:
            tokens = [token.orth_ for token in self.tokenizer(sentence.lower())]
            for ngram_size in range(1, len(tokens) + 1):
                for ngram in windowed(tokens, ngram_size):
                    ngram = " ".join(ngram)
                    if ngram not in self.relation_mapping_dict:
                        continue
                    self._add_occurrences(ngram, sentence)

    def create_fact_statistics(
        self, file_contents: Union[DatasetDict, Dataset, IterableDatasetDict, IterableDataset], text_key: str = "text"
    ) -> None:
        """
        Create fact statistics with multiprocessing .

        This method will iterate over documents and extract sentences.
        It will search for entities in the sentence.
        The occurrences will be updated in the relation dictionary.
        :param text_key: Key to extract text from file content.
        :param file_contents: List of dictionaries containing the file contents.
        :return:
        """
        for file_content in tqdm(file_contents, desc="Processing dataset"):
            self._process_file_content(file_content[text_key])


class FactMatcherEntityLinking(FactMatcherBase):
    """
    FactMatcherEntityLinking is a class that uses the entity linker model to search for entities in the dataset.

    kwargs:
    - bear_data_path [str]: Path to bear data directory.
        This is the main directory where all the bear data is stored. It should contain the relation_info.json file
        and the BEAR facts directory.

    - bear_relation_info_path [Optional[str]]: Path to the BEAR relation info file.
        This file contains the relation information for the BEAR data. If not provided, it will be set to
        {bear_data_path}/relation_info.json.

    - bear_facts_path [Optional[str]]: Path to the BEAR facts directory.
        This is the directory where all the BEAR fact files (.jsonl) are stored. If not provided, it will be set to
        {bear_data_path}/BEAR. Note that the dataset provides a BEAR and a BEAR-big directory, with the latter
        containing more facts.

    - save_file_content [Optional[bool]]: If True, the content of the file where the entity is found will be saved
        in the relation dictionary. The default is False.

    - require_gpu [Optional[bool]]: If True, it will require a GPU for the spacy entity linker.
        The default is False.

    - gpu_id [Optional[int]]: GPU ID to use for the spacy entity linker.
        The default is 0.

    - entity_linker_model [str]: Entity linker model to use.
        The default is "en_core_web_md", which is a medium-sized model optimized for cpu.
        Refer to https://spacy.io/models/en for more information.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        if kwargs.get("require_gpu", False):
            spacy.require_gpu(kwargs.get("gpu_id", 0))
        else:
            spacy.prefer_gpu(kwargs.get("gpu_id", 0))

        self.entity_linker = spacy.load(kwargs.get("entity_linker_model", "en_core_web_md"))

        self.entity_linker.add_pipe("entityLinker", last=True)

    def _get_entity_ids(self, content: str) -> set:
        """
        Get entity IDs from content.

        :param content: Content to extract entity IDs from.
        :return: Entity IDs
        """
        return self.entity_linker(content)._.linkedEntities

    def _add_occurrences(self, entity_ids: list[str], sentence: str) -> None:
        for entity_id in entity_ids:
            for _, relations in self.entity_relation_info_dict.items():
                try:
                    if relations[entity_id]["obj_id"] in entity_ids:
                        relations[entity_id]["occurrences"] += 1
                        if self.save_file_content:
                            relations[entity_id]["sentences"].update([sentence])
                except KeyError:
                    continue

    def create_fact_statistics(
        self, file_contents: Union[DatasetDict, Dataset, IterableDatasetDict, IterableDataset], text_key: str = "text"
    ) -> None:
        """
        Create fact statistics

        This method will iterate over documents and extract sentences. The entity linker model is used to search for
        entities in the sentence. The occurrences will be updated in the relation dictionary.
        :param text_key: Key to extract text from file content.
        Since the dataset is a list of dictionaries, we need to
        specify the key to extract the file content.
        That would be the case if we pass a huggingface dataset.
        :param file_contents: List of dictionaries containing the file contents
        :return:
        """
        for file_content in tqdm(file_contents, desc="Processing dataset"):
            content = utility.clean_string(file_content[text_key])
            split_doc = self.nlp(content)
            sentences = [sent.text for sent in split_doc.sents]
            for sentence in sentences:
                all_linked_entities = self._get_entity_ids(sentence)
                entity_ids = [f"Q{str(linked_entity.get_id())}" for linked_entity in all_linked_entities]
                self._add_occurrences(entity_ids, sentence)
