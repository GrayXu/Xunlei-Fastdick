#!/usr/bin/env bash

## netlimit.sh 用法：
## ./netlimit.sh <限速值，单位 KB/s> 如 ./netlimit.sh 12800
## 脚本依赖于以下软件包，请自行安装好：curl openssl

## 限速上限，可以依靠其他脚本测得限速上限，然后以参数 1 传入
upload_limits="$1"

## 爱快用户名
ik_username="**********"

## 爱快密码
ik_password="**********"

## 登陆爱快网址，形如： http://192.168.1.1:10000
url_ikuai="http://192.168.2.1"

## 这个 body 是设置“智能流控”模式的提交 body ，请先通过浏览器开发工具在爱快的“流控分流->智能流控”这里抓取你爱快系统的 body ，修改为你的 parent/interface/download/id 等
data_raw="{
    \"func_name\":\"layer7_intell\",
    \"action\":\"set_iface\",
    \"param\":
        {
            \"parent\":\"wan1\",
            \"interface\":\"wan1\",
            \"upload\":\"$upload_limits\",
            \"download\":22000,
            \"qos_switch\":1,
            \"comment\":\"\",
            \"id\":17262097
        }}"·

# echo $data_raw

## 登陆
ik_login() {
local ik_username="$1"
local ik_password="$2"
local passwd=$(echo -n "$ik_password" | openssl md5 -hex | awk '{print $2}')
local pass=$(echo -n "salt_11${ik_password}" | base64)
local cookie=$(curl $url_ikuai/Action/login -Ssi --data "{\"username\":\"$ik_username\",\"passwd\":\"$passwd\",\"pass\":\"$pass\",\"remember_password\":\"true\"}" | awk '/Set-Cookie:/{print $2}' 2>/dev/null)
[[ $cookie ]] && echo $cookie
}

## 获取 cookie
login_cookie=$(ik_login "$ik_username" "$ik_password")

# echo $login_cookie

## 设置限速
if [[ $login_cookie ]]; then
echo -n "success 设置爱快限速为 $upload_limits KB/s ，结果："
curl $url_ikuai/Action/call --header "Cookie: $login_cookie" --data-raw "$data_raw"
else
echo "fail 未能成功登陆爱快"
fi
