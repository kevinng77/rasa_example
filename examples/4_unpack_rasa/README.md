# rasa 入口测试

这个案例展示了

1. 在 python library 环境中不安装 rasa 的情况下，运行完整的 rasa 服务。


通过这个展示，我们能够延申到以下功能：

1. 拆解 rasa 源文件，以及各个包。
2. 根据入口，快速自定义各种需求。

## 快速开始

### 安装环境

官方提供了 poetry 的环境管理方案，可以直接 `poetry install` 来安装对应依赖。如果没有 poetry 的话，就：

```sh
pip install -r requirements.txt
```

安装好之后检查一下 rasa 是否安装：`pip list|grep rasa`，这里我们可能会需要 rasa-sdk 这个包，这个包也是[开源](https://github.com/RasaHQ/rasa-sdk) 的。

### 

主函数在 `rasa/__main__.py` 中，因此我们以模块的方式运行它就行了。这也是 poetry 中触发 rasa 的方法。至于如何用 rasa 直接开启服务，可以查看 poetry python 包管理工具。

```
python -m rasa train
```

```
python -m rasa run actions &
nohup python -m rasa run --enable-api > server.log &
```

命令还执行

```
curl -X POST http://localhost:5005/webhooks/rest/webhook \
-H "Content-Type: application/json" \
-d '{  "sender": "change_to_your_name",   "message": "Find me some good venues"}' 
```

查看返回结果，有正常的 200 和文字结果说明成功。

```
[{"recipient_id":"change_to_your_name","text":"here are some venues I found"},{"recipient_id":"change_to_your_name","text":"Big Arena, Rock Cellar"}]%  
```

关闭所有 rasa 后台进程

```
ps -ef|grep rasa|awk '{print $2}'|xargs kill -9 
```



