from gevent import monkey
import gevent
import requests
import time
monkey.patch_socket()

n = 100  # 并发数量 在1秒内发送
texts = [
       "Find me some good concerts",
       "Show me concerts",
       "search concerts",
       "Find me some good venues",
       "Show me venues",
       "search venues",]

URL = "http://40.76.242.139:5005/webhooks/rest/webhook"

import random

def worker(i):
    time1 = time.time()
    idx = random.randint(0, len(texts)-1)
    resp = requests.post(URL,json={
  "sender": f"{i}",  
  "message": texts[idx]
})
    if resp.status_code == 200:
        print(f"user {i} : {texts[idx]}")
        print(f"{' '.join([x['text'] for x in resp.json()])}")
        print(f'User {i} request end; time cost: {time.time() - time1:.2f}s')
        print(">>>" * 10)
    else:
        print(f"User {i} code error {resp.status_code}")
               
def run():
    """开始运行"""
    workers = [gevent.spawn_later(i/n, worker, i) for i in range(n)]   # 其实和上面的代码就这里不一样
    gevent.joinall(workers)  # 等所有请求结束后退出，类似线程的join
    print('Done!')


if __name__ == "__main__":
    run()
    