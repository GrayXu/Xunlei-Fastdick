env: xunlei-fastdick + systemctl on ubuntu22

Bugs:
- [x] 上下行正常同时加速
  - 原代码up & down的逻辑混着处理了，某一个down的话，俩都得重开。跟error 500进一步延长等待时间。
  - 直接分了俩文件跑，理论上session_id不能同时持有两个。但实测可能是单向的提速认一个session_id，也成功用不同的session_id收发心跳。<details><summary></summary>
当然也可以改share session_id，就是原po的代码有点混乱，就没改了。。</details>

- [ ] error 500 timeout
  - 10分钟一次keepalive包很容易error 500，基本要一直重复到直到513 channel挂了后relogin + reupgrade。而upgrade有时也会500，也需要等待。而第一次keepalive发送失败就会产生降级，让整体等待时间很长。
    - error 500感觉是迅雷的服务器胡填的error code。。感觉藏了什么验证。。

[old readme](https://github.com/GrayXu/Xunlei-Fastdick/blob/master/README.old.md)