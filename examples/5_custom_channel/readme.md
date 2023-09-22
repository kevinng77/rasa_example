# 自定义 channel

自定义 channel 可以用于修改和用户交互的方式，或进行一些输出预处理等。

以下仓库展示了：

+ 自定义一个 channel，用户可以通过访问我们自定义的 Url 来进行交互。

功能拓展：

+ 这个功能可以用来进行一些内容监控和管理，比如对输出内容监管，保存输出内容等等。
+ 自定义消息队列管理方式。
+ 该功能也可以用来间接的储存一些用户对话信息，包括：用户输入，机器人输出，模型预测的 NLU 结果等等。但是还是需要修改到 rasa 源码。如果要保存模型输出，可以参考更优雅的方式：自定义 trackerStrore。

## 快速开始

```sh
pip install rasa==3.4.4
```

老操作了，在终端 A 输入：

```sh
rasa train
rasa run actions &
rasa run --enable-api
```

打开一个新的终端 B 输入：

```sh
curl -X POST http://localhost:5005/webhooks/rest/mywebhook \
-H "Content-Type: application/json" \
-d '{  "sender": "change_to_your_name",   "message": "Find me some good venues"}' 
```

你会在终端 A 中看到：

```sh
This is a custom webhook made by me.
>>> you could see the following information: sender_id change_to_your_name,
 text Find me some good venues
>>> the custom channel is used for custom front-end interaction, if you want to save
middleware information, please use custom trackerstore, see next example
```

我们主要将 channel 自定义在了 `mychannel` 中，并在 `RestInput.blueprint()` 中修改了 app 的 router。

