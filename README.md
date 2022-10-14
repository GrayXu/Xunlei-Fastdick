env: xunlei-fastdick + systemctl on ubuntu22

Bugs:
- [x] 上下行正常同时加速
  - 原代码up & down的逻辑混着处理了，某一个down的话，俩都得重开。跟error 500进一步延长等待时间。
  - do sth: 直接分了俩文件跑，理论上session_id不能同时持有两个。但实测可能是单向的提速认一个session_id，也好像可以用不同的session_id收发心跳。。但还是拿redis做跨process share，renew or relogin都先update共享的session_id再save context；keepalive用共享的share_id <details><summary></summary>好丑，想改成private repo了</details>

- [ ] error 500 timeout
  - 强制10分钟一次keepalive心跳包很容易error 500，基本要一直重复到直到513 channel挂了后relogin + reupgrade。而upgrade自己有时也会500，也需要等待。而第一次keepalive发送失败就会产生降级，让整体等待时间很长。这些timeout问题都集中出现在上行提速上。<details><summary></summary>类似的问题也出现在官方的客户端上，客服反馈是后端有问题，过一周修，但实际上也没修好。迅雷的上行提速真的很多bug。。。</details>
  - do sth: 让error 500和1001一分钟后就重发

[old readme](https://github.com/GrayXu/Xunlei-Fastdick/blob/master/README.old.md)