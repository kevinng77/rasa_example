import logging
from typing import Any, Text, Dict, List, Type, Tuple

import joblib
from scipy.sparse import hstack, vstack, csr_matrix
from sklearn.linear_model import LogisticRegression

from rasa.engine.storage.resource import Resource
from rasa.engine.storage.storage import ModelStorage
from rasa.engine.recipes.default_recipe import DefaultV1Recipe
from rasa.engine.graph import ExecutionContext, GraphComponent
from rasa.nlu.classifiers import LABEL_RANKING_LENGTH
from rasa.nlu.featurizers.featurizer import Featurizer
from rasa.shared.nlu.training_data.training_data import TrainingData
from rasa.shared.nlu.training_data.message import Message
from rasa.shared.nlu.constants import TEXT, INTENT
from rasa.utils.tensorflow.constants import RANKING_LENGTH

logger = logging.getLogger(__name__)


@DefaultV1Recipe.register(
    DefaultV1Recipe.ComponentType.INTENT_CLASSIFIER, is_trainable=False
)
class SentimentClassifier(GraphComponent):
    """Intent classifier using the Logistic Regression."""

    @classmethod
    def required_components(cls) -> List[Type]:
        """Components that should be included in the pipeline before this component."""
        return []

    @staticmethod
    def required_packages() -> List[Text]:
        """Any extra python dependencies required for this component to run."""
        return []

    @staticmethod
    def get_default_config() -> Dict[Text, Any]:
        """The component's default config (see parent class for full docstring)."""
        return {
            "max_iter": 100,
            "solver": "lbfgs",
            "tol": 1e-4,
            "random_state": 42,
            RANKING_LENGTH: LABEL_RANKING_LENGTH,
        }

    def __init__(
        self,
        config: Dict[Text, Any],
        name: Text,
        model_storage: ModelStorage,
        resource: Resource,
    ) -> None:
        """Construct a new classifier."""
        self.name = name
        self.config = {**self.get_default_config(), **config}
        self.clf = "your sentiment model, it can be Bert of SKlearn model."

        # We need to use these later when saving the trained component.
        self._model_storage = model_storage
        self._resource = resource

    @classmethod
    def create(
        cls,
        config: Dict[Text, Any],
        model_storage: ModelStorage,
        resource: Resource,
        execution_context: ExecutionContext,
    ) -> "LogisticRegressionClassifier":
        """Creates a new untrained component (see parent class for full docstring)."""
        return cls(config, execution_context.node_name, model_storage, resource)

    def process(self, messages: List[Message]) -> List[Message]:
        """Return the most likely intent and its probability for a message."""

        for idx, message in enumerate(messages):
            sentiment, score = "Positive", 0.666  # this should come from your model
            message.set("sentiment", sentiment, add_to_output=True)
            message.set("sentiment_confidence", score, add_to_output=True)
        return messages

    def persist(self) -> None:
        """Persist this model into the passed directory."""
        with self._model_storage.write_to(self._resource) as model_dir:
            path = model_dir / f"{self._resource.name}.joblib"
            joblib.dump(self.clf, path)
            logger.debug(f"Saved intent classifier to '{path}'.")

    @classmethod
    def load(
        cls,
        config: Dict[Text, Any],
        model_storage: ModelStorage,
        resource: Resource,
        execution_context: ExecutionContext,
        **kwargs: Any,
    ):
        """Loads trained component (see parent class for full docstring)."""
        try:
            with model_storage.read_from(resource) as model_dir:
                classifier = joblib.load(model_dir / f"{resource.name}.joblib")
                component = cls(
                    config, execution_context.node_name, model_storage, resource
                )
                component.clf = classifier
                return component
        except ValueError:
            logger.debug(
                f"Failed to load {cls.__class__.__name__} from model storage. Resource "
                f"'{resource.name}' doesn't exist."
            )
            return cls.create(config, model_storage, resource, execution_context)

    @classmethod
    def validate_config(cls, config: Dict[Text, Any]) -> None:
        """Validates that the component is configured properly."""
        pass
