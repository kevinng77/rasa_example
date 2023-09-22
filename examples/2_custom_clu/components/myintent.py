from __future__ import annotations
import numpy as np
import logging

from typing import Any, Text, List, Dict, Tuple, Type
import torch
from rasa.engine.graph import ExecutionContext, GraphComponent
from rasa.engine.recipes.default_recipe import DefaultV1Recipe
from rasa.engine.storage.resource import Resource
from rasa.engine.storage.storage import ModelStorage
from rasa.nlu.featurizers.dense_featurizer.dense_featurizer import DenseFeaturizer
from rasa.nlu.tokenizers.tokenizer import Token, Tokenizer
from rasa.shared.nlu.training_data.training_data import TrainingData
from rasa.shared.nlu.training_data.message import Message
from rasa.nlu.constants import (
    DENSE_FEATURIZABLE_ATTRIBUTES,
    SEQUENCE_FEATURES,
    SENTENCE_FEATURES,
    NO_LENGTH_RESTRICTION,
    NUMBER_OF_SUB_TOKENS,
    TOKENS_NAMES,
)
from rasa.shared.nlu.constants import TEXT, ACTION_TEXT

logger = logging.getLogger(__name__)

MAX_SEQUENCE_LENGTHS = {
    "bert": 512,
    "gpt": 512,
    "gpt2": 512,
    "xlnet": NO_LENGTH_RESTRICTION,
    "distilbert": 512,
    "roberta": 512,
    "camembert": 512,
}


@DefaultV1Recipe.register(
    DefaultV1Recipe.ComponentType.MESSAGE_FEATURIZER, is_trainable=False
)
class LanguageModelFeaturizer(DenseFeaturizer, GraphComponent):
    """A featurizer that uses transformer-based language models.

    This component loads a pre-trained language model
    from the Transformers library (https://github.com/huggingface/transformers)
    including BERT, GPT, GPT-2, xlnet, distilbert, and roberta.
    It also tokenizes and featurizes the featurizable dense attributes of
    each message.
    """

    @classmethod
    def required_components(cls) -> List[Type]:
        """Components that should be included in the pipeline before this component."""
        return [Tokenizer]

    def __init__(
        self, config: Dict[Text, Any], execution_context: ExecutionContext
    ) -> None:
        """Initializes the featurizer with the model in the config."""
        super(LanguageModelFeaturizer, self).__init__(
            execution_context.node_name, config
        )
        self._load_model_metadata()
        self._load_model_instance()

    @staticmethod
    def get_default_config() -> Dict[Text, Any]:
        """Returns LanguageModelFeaturizer's default config."""
        return {
            **DenseFeaturizer.get_default_config(),
            "model_name": "bert",
            "cache_dir": None,
        }

    @classmethod
    def validate_config(cls, config: Dict[Text, Any]) -> None:
        """Validates the configuration."""
        pass

    @classmethod
    def create(
        cls,
        config: Dict[Text, Any],
        model_storage: ModelStorage,
        resource: Resource,
        execution_context: ExecutionContext,
    ) -> LanguageModelFeaturizer:
        """Creates a LanguageModelFeaturizer.

        Loads the model specified in the config.
        """
        return cls(config, execution_context)

    @staticmethod
    def required_packages() -> List[Text]:
        """Returns the extra python dependencies required."""
        return ["transformers"]

    def _load_model_metadata(self) -> None:
        """Loads the metadata for the specified model and set them as properties.

        This includes the model name, model weights, cache directory and the
        maximum sequence length the model can handle.
        """

        self.model_name = self._config["model_name"]
        self.cache_dir = self._config["cache_dir"]

        self.max_model_sequence_length = 512

    def _load_model_instance(self) -> None:
        from transformers import AutoTokenizer, AutoModel

        logger.debug(f"Loading Tokenizer and Model for {self.model_name}")

        self.tokenizer = AutoTokenizer.from_pretrained(
            self.model_name, cache_dir=self.cache_dir
        )
        self.model = AutoModel.from_pretrained( 
            self.model_name, cache_dir=self.cache_dir
        )
        self.model.eval()
        self.pad_token_id = self.tokenizer.unk_token_id

    def _get_docs_for_batch(
        self,
        batch_examples: List[Message],
        attribute: Text,
        inference_mode: bool = False,
    ) -> List[Dict[Text, Any]]:
        """Computes language model docs for all examples in the batch.

        Args:
            batch_examples: Batch of message objects for which language model docs
            need to be computed.
            attribute: Property of message to be processed, one of ``TEXT`` or
            ``RESPONSE``.
            inference_mode: Whether the call is during inference or during training.


        Returns:
            List of language model docs for each message in batch.
        """
        # TODO update

        input_text = [example.get('text') for example in batch_examples]
        inputs = self.tokenizer(input_text, return_tensors='pt', padding=True, truncation=True)
        with torch.no_grad():
            outputs = self.model(**inputs).last_hidden_state    
        #  print(outputs.shape) # [29, 9, 312])
        batch_sentence_features = outputs[:,0,:].numpy()
        batch_sequence_features = outputs[:,1:,:].numpy()

        # A doc consists of
        # {'sequence_features': ..., 'sentence_features': ...}
        batch_docs = []
        for index in range(len(batch_examples)):
            doc = {
                SEQUENCE_FEATURES: batch_sequence_features[index],
                SENTENCE_FEATURES: np.reshape(batch_sentence_features[index], (1, -1)),
            }
            batch_docs.append(doc)

        return batch_docs

    def process_training_data(self, training_data: TrainingData) -> TrainingData:
        """Computes tokens and dense features for each message in training data.

        Args:
            training_data: NLU training data to be tokenized and featurized
            config: NLU pipeline config consisting of all components.
        """
        batch_size = 64

        for attribute in DENSE_FEATURIZABLE_ATTRIBUTES:

            non_empty_examples = list(
                filter(lambda x: x.get(attribute), training_data.training_examples)
            )

            batch_start_index = 0

            while batch_start_index < len(non_empty_examples):

                batch_end_index = min(
                    batch_start_index + batch_size, len(non_empty_examples)
                )
                # Collect batch examples
                batch_messages = non_empty_examples[batch_start_index:batch_end_index]

                # Construct a doc with relevant features
                # extracted(tokens, dense_features)
                batch_docs = self._get_docs_for_batch(batch_messages, attribute)

                for index, ex in enumerate(batch_messages):
                    self._set_lm_features(batch_docs[index], ex, attribute)
                batch_start_index += batch_size

        return training_data

    def process(self, messages: List[Message]) -> List[Message]:
        """Processes messages by computing tokens and dense features."""
        for message in messages:
            self._process_message(message)
        return messages

    def _process_message(self, message: Message) -> Message:
        """Processes a message by computing tokens and dense features."""
        # processing featurizers operates only on TEXT and ACTION_TEXT attributes,
        # because all other attributes are labels which are featurized during
        # training and their features are stored by the model itself.
        for attribute in {TEXT, ACTION_TEXT}:
            if message.get(attribute):
                self._set_lm_features(
                    self._get_docs_for_batch(
                        [message], attribute=attribute, inference_mode=True
                    )[0],
                    message,
                    attribute,
                )
        return message

    def _set_lm_features(
        self, doc: Dict[Text, Any], message: Message, attribute: Text = TEXT
    ) -> None:
        """Adds the precomputed word vectors to the messages features."""
        sequence_features = doc[SEQUENCE_FEATURES]
        sentence_features = doc[SENTENCE_FEATURES]

        self.add_features_to_message(
            sequence=sequence_features,  # CLS 之后的 feature shape [len_seq, hidden_size]
            sentence=sentence_features,  # CLS 对应 shape(1, -1)
            attribute=attribute,
            message=message,
        )
