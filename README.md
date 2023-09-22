

## Updates

3/10 - 更新 [2_custom_clu](./examples/2_custom_clu/)：如何自定义 RASA 里面的 NLU 模块，基本上根据这个 example，我们可以使用任意的模型（torch, paddle等）来进行意图识别（基于此，我们能够实现对 rasa 推理速度和精度的大幅度提升）；或者实现 RASA 中不存在的功能，比如情感分析等；同时我们也意识到，RASA 自带的 transformer embedding 模型是不能 train的，并且其基于 Transformer Embedding 的特征提取方法也是可以优化的。

3/12 - 更新 [3-custmo_clu_advanced](./examples/3-custom_clu_advanced/) ：RASA NLU REST API。完结 RASA NLU 部分探索，作简要知识点总结。

3/15 - 更新 [1_concertbot](./examples/1_concertbot/): 添加 rest-api 调用方法在 1-concertbot example 中。

3/20 - 更新 [4_unpack_rasa](./examples/4_unpack_rasa/) ：rasa 入口以及开源框架拆解，完成 不安装 rasa python 包的情况下，运行 rasa 所有功能案例。

3/20 - 更新 [5_custom_channel](./examples/5_custom_channel/) ：rasa custom channel output，见 example 5

3/20 - 更新 [6_redis_store](./examples/6_redis_store/)：rasa TrackerStore 使用 redis 配置；这个支持我们对高并发支持以及保存中间变量。

3/21 - 更新 [7_async_test](./examples/7_async_test/)：测试了2 核 16 GB 内存虚拟机，在 1 秒钟内为100名用户进行服务时。平均耗时约 4 秒钟。

3/21 - 更新 [8_widget](./examples/8_wedget/): 通过 rasa 官方的 widget 和 socket-io 实现了客户端 session 方案。

3/23 - 更新 [9_k8s_rasa](./examples/9_k8s_rasa/): RASA K8S 部署。

## TODO

- [x] 添加自定义 intent 和其他 NLU 模块（3/10）
- [x] 尝试使用自定义的 Transformer 模型，而非直接使用官方提供的预训练模型。(自定义模型有利于更好的控制模型推理速度。)
- [x] NLU REST API 测试，NLU 整理模块完结
- [x] RASA 包管理架构梳理，rasa 手动安装，库依赖手动管理案例添加。
- [x] 梳理 客户端 Ression 设计方案(通过官方提供的 widget 和 websocket 实现)，添加 redis 缓存管理案例。
- [x] 添加 k8s helm 开启服务示例。
- [x] 梳理 Redis 储存方案，添加 Redis Tracker 储存方案。
- [ ] 调查数据隐私问题。
- [ ] Policy 考察，rule 和 story example 探索。
- [ ] 添加自定义 rasa core 案例。


## Resource

1. [blog_Conversational-AI-with-Rasa](http://qiniu.s1nh.org/blog_Conversational-AI-with-Rasa.pdf)
2. 
