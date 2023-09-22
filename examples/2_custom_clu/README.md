# 自定义 NLU 中的 featurizer 和额外 NLU 引擎

这个案例展示了

1. 如何使用 pytorch 上的模型，作为我们的 embedding 工具。
2. 如何添加一个情感分析引擎（这在 RASA 中是没有的）。

通过这个展示，我们能够延申到以下功能：

1. 参考这个代码，我们能够实现使用 paddle, onnx 等模型作为我们的 Feature/Embedding 工具。
2. 当 RASA 默认的训练效果不好时，你应该意识到 RASA 的自带 Featurizer 存在很大问题：他不能够被训练！
3. RASA 默认使用 CLS 位置的 feature 作为 sentence embedding 进行分类，而其他位置的 feature 作为 sequence embedding 进行 NER 等任务。**大部分的 Transformer 使用了 SUB-TOKEN 的分词方式，而 RASA 默认的 NER 方式时将 subtoken 对应的 embedding 结合，作为完成 token 的 embedding。**
4. 猜测：在 featurizer 中，没有输出任何完整 token 信息，估计在 NER 环节使用的 token 信息，是从 Tokenizer 传过去的，因此如果 Featurizer 输出 feature 维度和 Tokenizer 对应不上，就会报错。
5.  RASA 不支持 GPU，但是通过自定义 Component（下文会介绍到），我们能够在 GPU 机器上训练好权重，然后把他放在 RASA 中直接用，这将大大减少模型训练时间。
6. 我们能够在 RASA NLU 的基本功能（Intent，NER）上，添加上任意的 NLU 处理结果，比如添加额外的细腻度情感分析结果、添加额外的实体链接、实体纠错、信息抽取结果。

## 快速开始

```sh
pip install rasa==3.4.4
```

本样例主要展示 NLU 相关自定义功能，因此我们仅训练 NLU 模型！如果同时训练了 core 模型，那么在测试环节中，你很大可能是看不到下文中对应结果的。

```sh
rasa train nlu  # 训练模型
```

然后执行：

```sh
rasa shell
```

在对话框中，输入任意字符查看 NLU 结果。其中 sentiment 等字段是我们自定义添加上去的。

## Config.py 中的 Pipeline 讲解

Pipeline 由多个 GraphComponent 组成，，当用户发出消息后，消息会 **依次** 经过 Pipeline 的每一个 GraphComponent 处理，以完成 NLU。比如一下是一个经典的 Pipeline 写法：

```yml
pipeline:
  - name: "WhitespaceTokenizer"  
  - name: "CountVectorsFeaturizer"
  - name: "DIETClassifier"
    epochs: 100
```

以上面的 Pipeline 为例，rasa 进行 nlu 的时候，会从上到下进行每一个 GraphComponent。

如果用伪代码来表示这个流程，就是：

```python
# 毕竟是伪代码，因此逻辑不会很严谨
message = parse_user_input
# message 为数据结构，在 `rasa.shared.nlu.training_data.message` 可查看。
for GraphComponent in pipeline.name:
    message = GraphComponent.process(message)
```

每个 Component 可以在 `rasa.rasa.nlu` 文件夹下面找到，如 `WhitespaceTokenizer` 对应 `rasa.rasa.nlu.tokenizer.whitespace_tokenizer.WhitespaceTokenizer`。

### 自定义  GraphComponent (for NLU)

使用自定义 NLU GraphComponent 需要以下几个步骤：

1. 写一个 `.py` 文件，里面定义好你要的 `GraphComponent`。本案例中的自定义 GraphComponent 都写在 Component 文件夹下面了。

2. 在 Pipeline 中引用对应的  `GraphComponent`

#### 1. 定义 Custom GraphComponent

在 `rasa.data.test_classes` 中，我们能够看到一些官方提供的 `GraphComponent` 自定义方法和模板。如 `nlu_component_skeleton.py`。从下面的代码中可以看出，GraphComponent 主要的入口就是 `create`, `train`, `process`, `process_training_data` 四个方法。

```python
@DefaultV1Recipe.register(
    [DefaultV1Recipe.ComponentType.INTENT_CLASSIFIER], is_trainable=True
)
class CustomNLUComponent(GraphComponent):
    @classmethod
    def create(
        cls,
        config: Dict[Text, Any],
        model_storage: ModelStorage,
        resource: Resource,
        execution_context: ExecutionContext,
    ) -> GraphComponent:
        # TODO: Implement this
        ...

    def train(self, training_data: TrainingData) -> Resource:
        # TODO: Implement this if your component requires training
        ...

    def process_training_data(self, training_data: TrainingData) -> TrainingData:
        # TODO: Implement this if your component augments the training data with
        #       tokens or message features which are used by other components
        #       during training.
        ...

        return training_data

    def process(self, messages: List[Message]) -> List[Message]:
        # TODO: This is the method which Rasa Open Source will call during inference.
        ...
        return messages
```

因此自定义的 `GraphComponent` 中，必须覆盖重写以上四个方法。我们根据  `rasa.rasa.nlu`  中的文件进行修改，尝试使用 pytorch 的模型来计算模型的 embedding。大致方法是继承 `rasa.nlu.featurizers.dense_featurizer.dense_featurizer` 中的 `DenseFeaturizer` 抽象类，

```python
@DefaultV1Recipe.register(
    DefaultV1Recipe.ComponentType.MESSAGE_FEATURIZER, is_trainable=False
)
class LanguageModelFeaturizer(DenseFeaturizer, GraphComponent):
	#...
```

具体查看该文件夹下的 `components/myintent.py`。比较值得注意的点是：**默认情况下，所有的 Featurizer 都是不能被 train 的**，包括 RASA 自带的 TF transformers。而我们知道，Transformer 系列小模型在不微调的情况下，效果是不怎么好的。因此我们可以考虑，

1. 将 Featurizer 和 Intent Classifier 合并成一个 Compoent，而后统一在 RASA 中训练。
2. 或者选个领域预训练+微调好的 embedding transformer
3. 其他骚操作

#### 2. Pipeline 中引用自定义模块

我们将原先的词袋模型替换为我们自定义的模型 `components.myintent.LanguageModelFeaturizer`， 并使用 huggingface 上的权重`kevinng77/TinyBERT_4L_312D_SIMCSE_finetune`，这便是自定义模型的好处之一：这是一个在个人GPU 上蒸馏好的模型，速度比标准 bert 快20+倍，且在 NLI 数据集上的精度（较 SIMCSE）保留了 98%。我们能够进一步对他进行量化、检索、推理部署等，以进一步提高预测速度。

```python
pipeline:
  - name: "WhitespaceTokenizer"
  - name: components.myintent.LanguageModelFeaturizer
    model_name: kevinng77/TinyBERT_4L_312D_SIMCSE_finetune 
  - name: "DIETClassifier"
    epochs: 100
```

#### 3. 我们添加额外的情感分析模块，从用户回答中提取更多信息

根据 `rasa.nlu` 下的代码，大致可以猜测到，整个 Pipeline 的 NLU 过程中，所有的结果都会被记录在 `Message` 上。

因此如果我们想要添加额外的 nlu 信息，如实体间关系、细腻度情感分析。那么，我们就可以自定义 `Component` 模块，而后通过 `process()` 函数，将 NLU 处理的结果添加到 `Message` 中就行。`Message` 中有 `data` 字典，可以用来储存其他特征信息。

比如说，我想要在 intent 分析和 NER 分析的基础上，加上一层情感分析：

```yml
pipeline:
  - name: "WhitespaceTokenizer"
  - name: components.myintent.LanguageModelFeaturizer
    model_name: distilbert
  - name: components.sentiment_classifier.SentimentClassifier
  - name: "DIETClassifier"
    epochs: 50
```

在 `components.sentiment_classifier.SentimentClassifier` 中，我们提供以下方法（具体可查看文件夹中代码）：

```python
@DefaultV1Recipe.register(
    DefaultV1Recipe.ComponentType.INTENT_CLASSIFIER, is_trainable=False
)
class SentimentClassifier(GraphComponent):
    """Intent classifier using the Logistic Regression."""
    
    # ...
    
	def process(self, messages: List[Message]) -> List[Message]:
        """Return the most likely intent and its probability for a message."""

        for idx, message in enumerate(messages):
            sentiment, score = "Positive", 0.666  # this should come from your model
            message.set("sentiment", sentiment, add_to_output=True)
            message.set("sentiment_confidence", score, add_to_output=True)
        return messages
```

那么在输出结果中，我们就能看到 `Message.data` 中，多了情感分析的结果，执行以下语句进行测试 ：

```
rasa train nlu
rasa shell
```

输入 `hello world`，系统回复内容中，就会多出来 `sentiment` 和 `sentiment_confidence` 两个字段了：

```sh
NLU model loaded. Type a message and press enter to parse it.
Next message:
hello world
{
  "text": "hello world",
  "intent": {
    "name": "greet",
    "confidence": 0.4089217782020569
  },
  "entities": [],
  "text_tokens": [
    [
      0,
      5
    ],
   # ...
  ],
  "sentiment": "Positive",
  "sentiment_confidence": 0.666,
  "intent_ranking": [
    {
      "name": "greet",
      "confidence": 0.4089217782020569
    },
	#...
  ]
}
```





