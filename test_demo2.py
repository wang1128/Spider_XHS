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
    # 构建请求参数
    payload = {
        "user_url": user_url,
        "save_choice": save_choice,
        "min_likes": min_likes
    }

    try:
        # 提交任务
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

    # 轮询状态
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            status_res = requests.get(
                f"http://localhost:{server_port}{task_info['status_url']}",
                timeout=5
            )
            status = status_res.json()

            # 打印实时状态
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

    # 打印最终结果
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
    """参数化的搜索测试"""
    # 构建请求参数
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
    print(f"任务ID: {task_info['task_id']}")

    # 轮询状态
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            status_res = requests.get(
                f"http://localhost:{server_port}{task_info['status_url']}",
                timeout=5
            )
            status = status_res.json()

            # 打印实时状态
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

    # 打印最终结果
    print("\n\n=== 最终状态 ===")
    print(json.dumps(status, indent=2, ensure_ascii=False))
    return status


if __name__ == "__main__":
    # 示例测试用例
    #            :param query 搜索的关键词
    #             :param cookies_str 你的cookies
    #             :param page 搜索的页数
    #             :param sort 排序方式 general:综合排序, time_descending:时间排序, popularity_descending:热度排序
    #             :param note_type 笔记类型 0:全部, 1:视频, 2:图文
    #             返回搜索的结果
    user_test_params = {
        "user_url": "https://www.xiaohongshu.com/user/profile/56567b99b8c8b46b10592003?xsec_token=ABz4Rtqy2RzGNNtDm0Xt-QjxFSUML9uKgioMyY11yaXMM%3D&xsec_source=pc_search",
        "min_likes": 100,
        "timeout": 600
        # ,  # 延长超时时间
        # "note_type": 1
    }

    """
        指定数量搜索笔记，设置排序方式和笔记类型和笔记数量
        :param query 搜索的关键词
        :param require_num 搜索的数量
        :param cookies_str 你的cookies
        :param sort 排序方式 general:综合排序, time_descending:时间排序, popularity_descending:热度排序
        :param note_type 笔记类型 0:全部, 1:视频, 2:图文
        返回搜索的结果
    """

    search_test_params = {
        "query": "公务员考试",
        "require_num": 30,
        "min_likes": 200,
        "sort": "general"  # 测试热门排序
    }

    # 执行测试
    print("\n" + "=" * 50)
    test_user_crawler_with_status(**user_test_params)

    # print("\n" + "=" * 50)
    # test_search_with_status(**search_test_params)