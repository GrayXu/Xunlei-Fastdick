# Deprecated!

这个repo本身是为了压榨上下行同时提速时的额外上行提速效果，现在这个bug已经被修复，所以这个repo和原repo没有什么效果区别了。

---

env: xunlei-fastdick + systemctl on ubuntu22

note: 所有修改都overfit上行提速经常error 500的问题。如果没这问题就用原版。

Bugs:
- [x] 上下行正常同时加速
  - 原代码up & down的逻辑混着处理了，某一个down的话，俩都得重开。跟error 500进一步延长等待时间。
  - edit 
    - 分了俩文件跑，理论上session_id不能同时持有两个。但实测可能是单向的提速认一个session_id，也好像可以用不同的session_id收发心跳。但还是拿redis做跨process share，renew or relogin都先update共享的session_id再同步地save context；keepalive用共享的share_id

- [x] error 500 long timeout
  - 强制10分钟一次keepalive心跳包很容易error 500，基本要一直重复到直到513 channel挂了后relogin + reupgrade。而upgrade自己有时也会500，需要再等待。而第一次keepalive发送失败就会产生降级，让整体等待时间很长。这些timeout问题都集中出现在上行提速上。<details><summary></summary>类似的问题也出现在官方的客户端上，客服反馈是后端有问题，过一周修，但实际上也没修好。迅雷的上行提速真的很多bug。。。</details>
  - edit:
    -  让error 500和1001半分钟后就重发
    -  keepalive出现error 500就不重发keepalive，直接re-upgrade

[old readme](https://github.com/GrayXu/Xunlei-Fastdick/blob/master/README.old.md)