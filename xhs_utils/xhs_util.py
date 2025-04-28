import os
import json
import math
import random
import execjs
from xhs_utils.cookie_util import trans_cookies

import execjs

# 确保 execjs 使用 Node.js 运行时
execjs.runtime_names = ['Node']  # 显式指定运行时
b = execjs.get().name
print(f"当前 JS 环境: {b}")  # 调试输出

# 获取当前文件的绝对路径
current_file_path = os.path.abspath(__file__)
# 计算项目根目录（假设当前文件在项目根目录下的某个子目录中）
project_root = os.path.dirname(os.path.dirname(current_file_path))
# static 目录的绝对路径（与 xhs_utils 平行）
static_dir = os.path.join(project_root, "static")

# 加载 JS 文件（兼容 Windows 和 macOS）
try:
    # 1. 加载 xhs_xs_xsc_56.js
    js_path = os.path.join(static_dir, "xhs_xs_xsc_56.js")
    with open(js_path, "r", encoding="utf-8") as f:
        js_code = f.read()
    js = execjs.compile(js_code)
    a = execjs.get().name
    print(execjs.get().name)

    # 2. 加载 xhs_xray.js
    xray_js_path = os.path.join(static_dir, "xhs_xray.js")
    with open(xray_js_path, "r", encoding="utf-8") as f:
        xray_js_code = f.read()
    xray_js = execjs.compile(xray_js_code)
except Exception as e:
    raise Exception(f"加载 JS 文件失败，请检查路径: {e}")


def generate_x_b3_traceid(len=16):
    x_b3_traceid = ""
    for t in range(len):
        x_b3_traceid += "abcdef0123456789"[math.floor(16 * random.random())]
    return x_b3_traceid

def generate_xs_xs_common(a1, api, data=''):
    ret = js.call('get_request_headers_params', api, data, a1)
    xs, xt, xs_common = ret['xs'], ret['xt'], ret['xs_common']
    return xs, xt, xs_common

def generate_xs(a1, api, data=''):
    ret = js.call('get_xs', api, data, a1)
    xs, xt = ret['X-s'], ret['X-t']
    return xs, xt

def generate_xray_traceid():
    return xray_js.call('traceId')
def get_common_headers():
    return {
        "authority": "www.xiaohongshu.com",
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "accept-language": "zh-CN,zh;q=0.9",
        "cache-control": "no-cache",
        "pragma": "no-cache",
        "referer": "https://www.xiaohongshu.com/",
        "sec-ch-ua": "\"Chromium\";v=\"122\", \"Not(A:Brand\";v=\"24\", \"Google Chrome\";v=\"122\"",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "\"Windows\"",
        "sec-fetch-dest": "document",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "same-origin",
        "sec-fetch-user": "?1",
        "upgrade-insecure-requests": "1",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }
def get_request_headers_template():
    return {
        "authority": "edith.xiaohongshu.com",
        "accept": "application/json, text/plain, */*",
        "accept-language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
        "cache-control": "no-cache",
        "content-type": "application/json;charset=UTF-8",
        "origin": "https://www.xiaohongshu.com",
        "pragma": "no-cache",
        "referer": "https://www.xiaohongshu.com/",
        "sec-ch-ua": "\"Not A(Brand\";v=\"99\", \"Microsoft Edge\";v=\"121\", \"Chromium\";v=\"121\"",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "\"Windows\"",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-site",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0",
        "x-b3-traceid": "",
        "x-s": "",
        "x-s-common": "",
        "x-t": "",
        "x-xray-traceid": generate_xray_traceid()
    }

def generate_headers(a1, api, data=''):
    xs, xt, xs_common = generate_xs_xs_common(a1, api, data)
    x_b3_traceid = generate_x_b3_traceid()
    headers = get_request_headers_template()
    headers['x-s'] = xs
    headers['x-t'] = str(xt)
    headers['x-s-common'] = xs_common
    headers['x-b3-traceid'] = x_b3_traceid
    if data:
        data = json.dumps(data, separators=(',', ':'), ensure_ascii=False)
    return headers, data

def generate_request_params(cookies_str, api, data=''):
    cookies = trans_cookies(cookies_str)
    a1 = cookies['a1']
    headers, data = generate_headers(a1, api, data)
    return headers, cookies, data

def splice_str(api, params):
    url = api + '?'
    for key, value in params.items():
        if value is None:
            value = ''
        url += key + '=' + value + '&'
    return url[:-1]

