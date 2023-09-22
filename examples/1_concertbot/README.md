# Concertbot

## What’s inside this example?

This example contains some training data and the main files needed to build an
assistant on your local machine. The `concertbot` consists of the following files:

- **data/stories.md** contains training stories for the Core model
- **actions/actions.py** contains some custom actions
- **config.yml** contains the model configuration
- **domain.yml** contains the domain of the assistant
- **endpoints.yml** contains the webhook configuration for the custom actions

## 快速开始

```
pip install rasa
```

执行代码，训练模型。 run（官方示例中，仅仅对 rasa core 进行了训练，而没有训练 NLU，导致 intent 识别不出来）
```
rasa train
```

启动 server，可以通过 REST API 进行交互
```
rasa run actions&
rasa run -m models --endpoints endpoints.yml --enable-api
```

发送请求到 POST http://localhost:5005/webhooks/rest/webhook, body 是 
```
{
  "sender": "test_user",  
  "message": "Find me some good concerts"
}
```

你可以执行下面这串代码，测试一下 rest api 是否正常运行。
```
curl -X POST http://localhost:5005/webhooks/rest/webhook \
-H "Content-Type: application/json" \
-d '{  "sender": "change_to_your_name",   "message": "Find me some good venues"}' 
```

除了 rest api 外，可以通过命令行进行终端交互：
```
rasa run actions&  # 在后台启动
rasa shell
```

多次运行 `rasa run action` 导致 5055 端口占用，报错时，运行：
```
sudo kill -9 `lsof -t -i:5055`
```
