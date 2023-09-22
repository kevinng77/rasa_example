# RASA K8S

## K8S 环境

```
kubectl create namespace rasa
```

需要添加对应的 helm chart 源

```sh
helm repo add rasa https://helm.rasa.com
```

## 启动 RASA Action

### 制作 Actions Image

将 actionss 文件放在 `actions/actions.py` 中，执行：

```sh
docker build ./action_docker -t kevinng77/myaction:latest
```

修改你想保存的 image 名称，格式如下：

```sh
docker build ./action_docker -t <account_username>/<repository_name>:<custom_image_tag>
```

保存后，上传到 docker 的某个 registry。本案例使用 dockerhub

```
docker push kevinng77/myaction
```

### 修改 values.yml

主要修改 `action_values.yml` 其中的 image 路径:

```yml
image:
  # -- Action Server image name to use (relative to `registry`)
  name: kevinng77/myaction

  # -- Action Server image tag to use
  tag: "latest"
```

把 `kevinng77/myaction` 改成你 dockerhub 对应的镜像 ID 就行。

其他配置可以参考 [rasa chart](https://github.com/RasaHQ/helm-charts/tree/main/charts) ，其中你可能会考虑：

+ 调整 auto scaling 方案。
+ Service 方案采用 ClusterIP，因为我们会将 RASA server 和 Action server 部署在同一个集群中。如果要分开部署，可以设置其他服务方式。

### 安装 action server service

参考官方提供的 helm，一键安装即可，我们将 action server 部署 release_name 为 `rasa-action-server` ：

```sh
helm install --namespace rasa \
  --values action_values.yml rasa-action-server rasa/rasa-action-server
```

更新的话使用：

```sh
helm upgrade --namespace rasa  --reuse-values  \
  --values action_values.yml rasa-action-server rasa/rasa-action-server
```

## 启动 RASA

### 制作 RASA Image

默认的 RASA image 当中，时没有 spacy等包的，如果你的 rasa 架构使用了 torch，paddle，spacy 等依赖，可以自行打包：

```dockerfile
# rasa_docker/Dockerfile
FROM rasa/rasa:3.4.4
WORKDIR /app
USER root

RUN pip install spacy
RUN python -m spacy download zh_core_web_trf

# By best practices, don't run the code with root user
USER 1001
```

构建镜像并推送到 dockerhub：

```sh
docker build ./rasa_docker -t kevinng77/rasa:3.4.4
docker push kevinng77/rasa:3.4.4
```

### 上传 model

将本地上用 `rasa train` 训练出来的模型推到 github 上（也可以时其他你可以通过 wget 下载到的地方），比如该案例中，将模型推到了： `https://github.com/kevinng77/rasa_model/zh_model.tar.gz`

### 修改 values.yml

修改 rasa_values.yml, 完整文件可以参考 rasa_values.yml 文件。比较值得注意的是：

1. rasa server 和 action server 的通信，通过 helm 配置方式为：

```yml
## Settings for Rasa Action Server
## See: https://github.com/RasaHQ/helm-charts/tree/main/charts/rasa-action-server
rasa-action-server:
  # -- Install Rasa Action Server
  install: false

  external:
    # -- Determine if external URL is used
    enabled: true
    # -- External URL to Rasa Action Server
    url: "http://rasa-action-server/webhook"
```

其中 URL 用的 `http://rasa-action-server/webhook` 表示 action server 在同 K8S 集群上的 resource name: `rasa-action-server` 运行。因此通过 ClusterIP 的方式就能访问到。

2. 我们设置让 rasa server（同名的 pod） 不要分布在同一个 label 中，设置 pod label 为 `app: rasa-server`，而后配置：

```yml
podLabels:
  app: rasa-server
affinity: 
  podAntiAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:
    - labelSelector:
        matchExpressions:
        - key: app
          operator: In
          values:
          - rasa-server
      topologyKey: "kubernetes.io/hostname"
```

其中的 topologyKey 可以通过 `kubectl get node --show-labels` 查看。

3. 配置模型路径和 credentials，支持 restAPI 以及 socketio 通信。

```yml
applicationSettings:
	# 该路径应该是一个下载路径，对应 https://github.com/kevinng77/rasa_model/zh_model.tar.gz
	# 上的内容
  initialModel: "https://github.com/kevinng77/rasa_model/blob/master/zh_model.tar.gz?raw=true"
  credentials:
    # 
    enabled: true
    additionalChannelCredentials:
      rest: {}
      socketio:
        user_message_evt: user_uttered
        bot_message_evt: bot_uttered
        session_persistence: true
        # 其它 credentials 配置
```

4. 修改 Image source 为你推送到 dockerhub 的镜像

```yml
image:
  name: rasa
  tag: "3.4.4"
  # -- Override default registry + image.name for Rasa Open Source
  repository: "kevinng77/rasa"
```

5. 针对 AZURE 进行特殊服务配置

```yml
service:
  type: LoadBalancer
  port: 5005
  # Azure 专用 LoadBalancer 申请域名方法
  annotations: {
    service.beta.kubernetes.io/azure-dns-label-name: acrasa
  }
```

### 安装 rasa 服务

```sh
helm install \
    --namespace rasa \
    --values rasa_values.yml \
    myrasa \
    rasa/rasa
```

更新 helm 用：

```sh
helm upgrade -f rasa_values.yml --reuse-values  \
    --namespace rasa \
        myrasa rasa/rasa
```

## 访问 rasa

可以通过 LoadBalancer 对应的 IP 地址进行方案。其中我们基于 Azure 配置，可以直接访问 IP:

```sh
http://acrasa.eastasia.cloudapp.azure.com/
```

前端通过 restAPI 发送请求，或者通过 RASA 提供的 chat Widget，具体查看 RASA 官网:

```html
<div id="rasa-chat-widget" data-websocket-url="http://your_ip:5005/socket.io"></div>
<script src="https://unpkg.com/@rasahq/rasa-chat" type="application/javascript"></script>
```

## 集群性能测试

通过 gevent 和 requests 在 python 上模拟了一下高峰访问：

| 1秒内访问数量/耗时（秒） | 1       | 10      | 50        | 100     |
| ------------------------ | ------- | ------- | --------- | ------- |
| 1 node                   | 0.5-0.7 | 2.5-3.4 | 12.5-14.2 | 27-29   |
| 2 node                   | 0.5-0.7 | 0.5-1.4 | 3.9-6     | 8-11.2  |
| 4 node                   | 0.5-0.7 | 0.5-0.8 | 1.1-3.5   | 2.3-5.8 |
| 10 node                  | 0.5-0.7 | 0.5-0.7 | 0.5-3     | 0.5-3   |

node 配置：2核 8G内存。NLU 模型：SPACE ZH(400M)

总结：单台机器配置不能太低，否则轮询策略对耗时影响大。建议 4 核 16+GB 内存节点。NLU 部分对模型进行推理优化后，2 - 3 台 4 核 16+GB 内存节点就能应付好每秒钟 100 次的请求了。