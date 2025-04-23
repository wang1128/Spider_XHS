import requests
import time
import json

TIME_OUT = 3000
MIN_LIKE = 500


def test_user_crawler_with_status(
        user_url: str,
        save_choice: str = "all",
        min_likes: int = MIN_LIKE,  # 固定参数
        timeout: int = 60000,  # 固定参数
        server_port: int = 8080
):
    """用户爬虫测试（参数已固定）"""
    payload = {
        "user_url": user_url,
        "save_choice": save_choice,
        "min_likes": min_likes
    }

    try:
        response = requests.post(
            f"http://localhost:{server_port}/api/crawl_user",
            json=payload,
            timeout=30
        )
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"❌ 请求失败: {str(e)}")
        if hasattr(e, 'response'):
            print(f"服务器响应: {e.response.text}")
        return None

    task_info = response.json()
    print(f"\n=== 用户爬虫测试启动 ===")
    print(f"用户URL: {user_url}")
    print(f"任务ID: {task_info['task_id']}")

    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            status_res = requests.get(
                f"http://localhost:{server_port}{task_info['status_url']}",
                timeout=10
            )
            status = status_res.json()

            status_msg = (
                f"\r[进度 {status.get('progress', 0)}%] "
                f"成功: {status.get('success', 0)} "
                f"失败: {status.get('failed', 0)} "
                f"当前处理: {status.get('current_url', '无')}"
            )
            print(status_msg.ljust(100), end="")

            if status["status"] in ["completed", "failed"]:
                break

            time.sleep(5)
        except requests.exceptions.RequestException as e:
            print(f"\n⚠️ 状态查询异常: {str(e)}")
            time.sleep(5)

    print("\n\n=== 最终状态 ===")
    print(json.dumps(status, indent=2, ensure_ascii=False))
    return status


if __name__ == "__main__":
    # ==============================
    # 读取用户URL列表
    # ==============================
    user_urls = []
    try:
        with open("crawl_user.txt", "r", encoding="utf-8") as f:
            for line in f:
                url = line.strip()
                if url.startswith("http"):
                    user_urls.append(url)
                elif url:  # 忽略空行但打印非URL内容
                    print(f"⚠️ 忽略无效行: {line.strip()}")

        print(f"成功加载 {len(user_urls)} 个用户URL")
        if not user_urls:
            print("❌ 文件中没有有效URL")
            exit()
    except Exception as e:
        print(f"❌ 文件读取失败: {str(e)}")
        exit()

    # ==============================
    # 执行所有用户爬虫任务
    # ==============================
    for idx, url in enumerate(user_urls, 1):
        print(f"\n{'=' * 50}")
        print(f"处理进度: {idx}/{len(user_urls)}")

        # 调用爬虫函数（参数已固化在函数定义中）
        test_user_crawler_with_status(user_url=url)
        print('完成')

        # 在这里加 转换 wav，识别，和输出 pdf 的逻辑


        # 添加间隔（可选）
        if idx != len(user_urls):
            print("\n等待5秒...")
            time.sleep(5)
