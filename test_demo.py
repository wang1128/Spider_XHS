import requests
import time
import json


def test_user_crawler_with_status(
        user_url: str,
        save_choice: str = "all",
        min_likes: int = 100,
        timeout: int = 300,
        server_port: int = 8080
):
    """参数化的用户爬虫测试"""
    payload = {
        "user_url": user_url,
        "save_choice": save_choice,
        "min_likes": min_likes
    }

    try:
        response = requests.post(
            f"http://localhost:{server_port}/api/crawl_user",
            json=payload,
            timeout=10
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
                timeout=5
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

            time.sleep(2)
        except requests.exceptions.RequestException as e:
            print(f"\n⚠️ 状态查询异常: {str(e)}")
            time.sleep(5)
    # else:
    #     print("\n⌛ 任务超时")
    #     return None

    print("\n\n=== 最终状态 ===")
    print(json.dumps(status, indent=2, ensure_ascii=False))
    return status


def test_search_with_status(
        query: str,
        require_num: int = 20,
        save_choice: str = "all",
        min_likes: int = 100,
        sort: str = "general",
        note_type: int = 0,
        timeout: int = 300,
        server_port: int = 8080
):
    """参数化的搜索测试（支持笔记类型）"""
    if note_type not in [0, 1, 2]:
        raise ValueError("无效笔记类型：0-全部 1-视频 2-图文")

    payload = {
        "query": query,
        "require_num": require_num,
        "save_choice": save_choice,
        "min_likes": min_likes,
        "sort": sort,
        "note_type": note_type
    }

    try:
        response = requests.post(
            f"http://localhost:{server_port}/api/crawl_search",
            json=payload,
            timeout=10
        )
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"❌ 请求失败: {str(e)}")
        if hasattr(e, 'response'):
            print(f"服务器响应: {e.response.text}")
        return None

    task_info = response.json()
    print(f"\n=== 搜索测试启动 ===")
    print(f"搜索词: {query}")
    print(f"笔记类型: {['全部', '视频', '图文'][note_type]}")
    print(f"任务ID: {task_info['task_id']}")

    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            status_res = requests.get(
                f"http://localhost:{server_port}{task_info['status_url']}",
                timeout=5
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

            time.sleep(2)
        except requests.exceptions.RequestException as e:
            print(f"\n⚠️ 状态查询异常: {str(e)}")
            time.sleep(5)
    # else:
    #     print("\n⌛ 任务超时")
    #     return None

    print("\n\n=== 最终状态 ===")
    print(json.dumps(status, indent=2, ensure_ascii=False))

    # 验证笔记类型
    if status["status"] == "completed":
        actual_types = set()
        for item in status.get("details", []):
            if item.get("type"):
                actual_types.add(item["type"])
        print(f"\n验证结果: 实际获取的笔记类型 - {', '.join(actual_types) or '无'}")

    return status


if __name__ == "__main__":
    # 用户测试示例
    user_test_params = {
        "user_url": "https://www.xiaohongshu.com/user/profile/63fec5ff000000002a008e2c",
        "min_likes": 1000,
        "timeout": 600
    }

    # 读取关键词文件
    search_test_cases = []
    keyword_file = "关键词2.txt"  # 文件路径可修改

    try:
        with open(keyword_file, "r", encoding="utf-8") as f:
            for line in f:
                # 清洗和验证关键词
                keyword = line.strip()
                if keyword:  # 忽略空行
                    search_test_cases.append({
                        "query": keyword,
                        "require_num": 50,
                        "min_likes": 200,
                        "note_type": 0,
                        "desc": f"关键词: {keyword}"
                    })
        print(f"成功加载 {len(search_test_cases)} 个关键词")
    except Exception as e:
        print(f"文件读取失败: {str(e)}")
        exit()

    # 执行测试套件
    print("\n" + "=" * 50)
    # test_user_crawler_with_status(**user_test_params)  # 可选用户测试

    import random
    import time

    for index, case in enumerate(search_test_cases, 1):
        print(f"\n{'=' * 50}\n正在处理第 {index}/{len(search_test_cases)} 个关键词: {case['query']}")

        # 执行搜索测试
        test_search_with_status(
            query=case["query"],
            require_num=case["require_num"],
            min_likes=case["min_likes"],
            note_type=case["note_type"]
        )

        # 随机等待
        # if index != len(search_test_cases):  # 最后一个不需要等待
        #     wait_time = random.randint(60, 80)  # 1-3分钟
        #     print(f"\n🕒 任务 {index} 完成，开始休息 {wait_time} 秒...")
        #     time.sleep(wait_time)