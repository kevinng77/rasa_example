# 高并发速度测试

修改 `run_test.py` 中的 URL 为你的 rasa restapi url.

```
URL = "http://40.76.242.139:5005/webhooks/rest/webhook"
```

运行 `python run_test.py` 就行。其中 `n = 100 ` 表示 在 1 秒钟内，我们对 rasa 服务器发起 `n=100` 次并发的访问。