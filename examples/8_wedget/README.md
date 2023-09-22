# Web UI 案例

1. 支持通过 js 的方式，简单的在网页上嵌入对话系统 UI。
2. 支持自动 session 管理。多用户交流

## 快速上手

1. 在 credentials 中添加设置:

```
socketio:
  user_message_evt: user_uttered
  bot_message_evt: bot_uttered
  session_persistence: true
```

```
rasa train
rasa run actions &
rasa run --enable-api --cors '*'
```

在任意 HTML 文件中添加（记得修改你的 websocket 为 `http://<ip>:<port>/socket.io`）:
```
<div id="rasa-chat-widget" data-websocket-url="http://40.76.242.139:5005/socket.io"></div>
<script src="https://unpkg.com/@rasahq/rasa-chat" type="application/javascript"></script>
```

或者 

```
    <script>!(function () {
        let e = document.createElement("script"),
          t = document.head || document.getElementsByTagName("head")[0];
        (e.src =
          "https://cdn.jsdelivr.net/npm/rasa-webchat@1.x.x/lib/index.js"),
          // Replace 1.x.x with the version that you want
          (e.async = !0),
          (e.onload = () => {
            window.WebChat.default(
              {
                customData: { language: "en" },
                socketUrl: "http://40.76.242.139:5005",
                socketPath: "/socket.io/",
                // add other props here
              },
              null
            );
          }),
          t.insertBefore(e, t.firstChild);
      })();
      </script>
```

打开改 HTML 页面就能看到对话系统了。