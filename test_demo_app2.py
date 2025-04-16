import os
import json
import threading
import time
import random
import uuid
from collections import defaultdict
from app import FlaskDataSpider  # 替换为实际模块路径

# 初始化爬虫实例（与主程序共享配置）
spider = FlaskDataSpider()
task_status = defaultdict(dict)  # 与主程序共享任务状态存储


def test_search_with_status(
        query: str,
        require_num: int = 20,
        save_choice: str = "all",
        min_likes: int = 100,
        sort: str = "general",
        note_type: int = 0,
        timeout: int = 300
):
    """直接调用搜索爬虫逻辑"""
    task_id = str(uuid.uuid4())

    # 启动爬虫线程
    threading.Thread(
        target=spider.spider_search_notes,
        args=(task_id, query, require_num, save_choice, sort, note_type, min_likes)
    ).start()

    print(f"\n=== 搜索测试启动 ===")
    print(f"搜索词: {query}")
    print(f"任务ID: {task_id}")

    start_time = time.time()
    last_progress = 0

    while time.time() - start_time < timeout:
        status = task_status.get(task_id, {})

        # 进度更新时才刷新显示
        if status.get("progress", 0) != last_progress:
            status_msg = (
                f"[进度 {status.get('progress', 0)}%] "
                f"成功: {status.get('success', 0)} "
                f"失败: {status.get('failed', 0)} "
                f"当前处理: {status.get('current_url', '无')}"
            )
            print("\r" + status_msg.ljust(100), end="")
            last_progress = status.get("progress", 0)

        if status.get("status") in ["completed", "failed"]:
            break

        time.sleep(2)

    # 最终状态处理
    final_status = task_status.get(task_id, {"status": "unknown"})
    print("\n\n=== 最终状态 ===")
    print(json.dumps(final_status, indent=2, ensure_ascii=False))

    # 结果验证
    if final_status.get("status") == "completed":
        actual_types = set()
        for item in final_status.get("details", []):
            if item.get("type"):
                actual_types.add(item["type"])
        print(f"实际获取的笔记类型: {', '.join(actual_types) or '无'}")

    return final_status


def load_keywords(filename: str) -> list:
    """加载关键词文件"""
    search_cases = []

    try:
        with open(filename, "r", encoding="utf-8") as f:
            for line_number, line in enumerate(f, 1):
                raw_keyword = line.strip()

                # 关键词清洗
                keyword = raw_keyword.replace('\u3000', ' ')  # 替换全角空格
                keyword = ' '.join(keyword.split())  # 合并连续空格

                if not keyword:
                    continue

                # 构建测试用例
                search_cases.append({
                    "query": keyword,
                    "require_num": 50,
                    "min_likes": 1000,
                    "note_type": 0,
                    "desc": f"第{line_number}行: {keyword}"
                })

        print(f"成功加载 {len(search_cases)} 个有效关键词")
        return search_cases

    except Exception as e:
        print(f"文件读取失败: {str(e)}")
        exit(1)


if __name__ == "__main__":
    # 参数配置
    keyword_file = "关键词.txt"  # 可修改路径
    total_timeout = 24 * 3600  # 总超时时间24小时

    # 加载关键词
    print("=" * 60)
    print(f"正在加载关键词文件: {os.path.abspath(keyword_file)}")
    search_test_cases = load_keywords(keyword_file)

    # 执行测试套件
    print("\n" + "=" * 60)
    print(f"开始执行 {len(search_test_cases)} 个搜索测试用例")
    print("=" * 60)

    start_timestamp = time.time()
    success_count = 0
    failed_count = 0

    for case_index, test_case in enumerate(search_test_cases, 1):
        case_start = time.time()
        print(f"\n▶️ 正在执行第 {case_index}/{len(search_test_cases)} 个用例")
        print(f"📝 用例描述: {test_case['desc']}")
        print(f"🔍 搜索词: {test_case['query']}")
        print(f"⏳ 开始时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(case_start))}")

        # 执行测试
        result = test_search_with_status(
            query=test_case["query"],
            require_num=test_case["require_num"],
            min_likes=test_case["min_likes"],
            note_type=test_case["note_type"]
        )

        # 统计结果
        if result.get("status") == "completed":
            success_count += 1
        else:
            failed_count += 1

        # 计算剩余时间
        elapsed_time = time.time() - start_timestamp
        avg_time = elapsed_time / case_index
        remaining = avg_time * (len(search_test_cases) - case_index)
        print(f"\n🕒 本用例耗时: {time.time() - case_start:.1f}秒 | 预计剩余时间: {remaining / 60:.1f}分钟")

        # 非最后一个任务时等待
        if case_index < len(search_test_cases):
            wait_seconds = random.randint(60, 80)
            print(f"\n⏸️ 任务间隔等待: {wait_seconds}秒")
            time.sleep(wait_seconds)

    # 最终报告
    print("\n" + "=" * 60)
    print(f"测试套件执行完成 (总耗时: {(time.time() - start_timestamp) / 60:.1f}分钟)")
    print(f"✅ 成功: {success_count} 个")
    print(f"❌ 失败: {failed_count} 个")
    print("=" * 60)