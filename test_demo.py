import requests
import random
import time

def test_search_crawler():
    """测试搜索爬虫服务（对应原示例1）"""
    # 搜索参数设置
    search_queries = [
        ("公考网课对比测评", "网页3/6关于网课选择的核心需求"),
        ("考公作息时间表", "网页1/6提到的精细化时间管理"),
        ("事业单位备考攻略", "网页3/5涉及的拓展考试类型"),
        ("考公心理调适方法", "网页7/4提及的备考心态问题")
    ]

    for query, description in search_queries:
        print(f"\n{'#' * 30}\n开始处理搜索词：{query}\n描述：{description}")

        # 生成动态参数
        payload = {
            "query": query,
            "require_num": 30,
            "save_choice": "all",
            "sort": "general",
            "note_type": 0,
            "min_likes": random.randint(80, 150)
        }

        # 发送API请求（端口改为8080）
        response = requests.post(
            "http://localhost:8080/api/crawl_search",  # 修改端口
            json=payload
        )

        print(f"响应状态：{response.status_code}")
        print(f"响应内容：{response.json()}")

        time.sleep(3)

def test_user_crawler():
    """测试用户爬虫服务（对应原示例2）"""
    users = [
        (
            "https://www.xiaohongshu.com/user/profile/55c2b8c267bc652c03886000?xsec_token=AB82gDEutzUWqwyBkA1Rg0Sph506Df__h1eVIbI-owaGU=&xsec_source=pc_feed",
            "示例用户主页（设置高点赞阈值）",
            1000
        )
    ]

    for user_url, description, min_likes in users:
        print(f"\n{'#' * 30}\n开始处理用户：{user_url}\n描述：{description}")

        payload = {
            "user_url": user_url,
            "save_choice": "all",
            "min_likes": min_likes
        }

        response = requests.post(
            "http://localhost:8080/api/crawl_user",  # 确保端口一致
            json=payload
        )

        print(f"响应状态：{response.status_code}")
        print(f"响应内容：{response.json()}")

        time.sleep(5)


def test_user_crawler_with_status():
    """带状态跟踪的用户爬虫测试"""
    try:
        # 提交任务到8080端口
        response = requests.post(
            "http://localhost:8080/api/crawl_user",
            json={
                "user_url": "https://www.xiaohongshu.com/user/profile/55c2b8c267bc652c03886000?xsec_token=AB82gDEutzUWqwyBkA1Rg0Sph506Df__h1eVIbI-owaGU=&xsec_source=pc_feed",
                "save_choice": "all",
                "min_likes": 100
            },
            timeout=10
        )
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"❌ 请求失败: {str(e)}")
        if hasattr(e, 'response'):
            print(f"服务器响应: {e.response.text}")
        return

    task_info = response.json()
    print("任务提交响应:", task_info)

    # 状态轮询
    start_time = time.time()
    timeout = 300  # 5分钟超时

    while time.time() - start_time < timeout:
        try:
            status_res = requests.get(f"http://localhost:8080{task_info['status_url']}", timeout=5)
            status = status_res.json()

            if status["status"] == "completed":
                print(f"\n✅ 完成! 下载数量: {status.get('downloaded', 0)}")
                break
            elif status["status"] == "failed":
                print(f"\n❌ 失败! 错误: {status.get('message', '未知错误')}")
                break

            print(f"\r当前进度: {status.get('progress', 0)}%", end="")
            time.sleep(2)
        except requests.exceptions.RequestException as e:
            print(f"\n⚠️ 状态查询异常: {str(e)}")
            time.sleep(5)
    else:
        print("\n⌛ 任务超时")

if __name__ == "__main__":
    # print("=== 测试搜索爬虫 ===")
    # test_search_crawler()

    print("\n=== 测试用户爬虫 ===")
    # test_user_crawler()

    # print("=== 测试用户爬虫（带状态跟踪）===")
    test_user_crawler_with_status()

    print("\n=== 测试完成 ===")