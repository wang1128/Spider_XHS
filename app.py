# app.py
import os
import sqlite3
import random
import threading
import uuid
import re
from collections import defaultdict
from flask import Flask, request, jsonify
from loguru import logger
from pathlib import Path
from apis.pc_apis import XHS_Apis
from xhs_utils.common_utils import init
from xhs_utils.data_util import handle_note_info, download_note, save_to_xlsx
import time
import sys

# 初始化Flask应用
app = Flask(__name__)

# 配置日志系统
log_dir = Path("logs")
log_dir.mkdir(parents=True, exist_ok=True)

logger.remove()
logger.add(
    sys.stderr,
    level="DEBUG",
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
)
logger.add(
    log_dir / "xhs_spider.log",
    rotation="500 MB",
    retention="30 days",
    encoding="utf-8",
    level="DEBUG",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
)

# 初始化全局配置
cookies_str, base_path = init()

# 任务状态存储
task_status = defaultdict(dict)


class FlaskDataSpider:
    def __init__(self):
        self.xhs_apis = XHS_Apis()
        self.liked_regex = re.compile(r"^(\d+\.?\d*)([万万千]?)")

    def _get_db_connection(self):
        """获取线程安全的数据库连接"""
        return sqlite3.connect('downloaded_notes.db', check_same_thread=False)

    def _parse_liked_count(self, liked_str):
        """解析中文格式的点赞数"""
        try:
            cleaned = liked_str.replace(',', '').strip()
            match = self.liked_regex.match(cleaned)
            if not match:
                return 0

            num_part, unit = match.groups()
            num = float(num_part)

            unit_multiplier = {
                '万': 10000,
                '千': 1000,
                '': 1
            }
            return int(num * unit_multiplier.get(unit, 1))
        except Exception as e:
            logger.warning(f"点赞数解析失败: {liked_str} -> {str(e)}")
            return 0

    def spider_note(self, note_url: str, proxies=None):
        """处理单个笔记爬取"""
        conn = self._get_db_connection()
        try:
            c = conn.cursor()
            c.execute("SELECT note_info FROM downloaded_notes WHERE url=?", (note_url,))
            if c.fetchone():
                logger.info(f'笔记 {note_url} 已存在')
                return False, '笔记已存在', None

            success, msg, note_info = self.xhs_apis.get_note_info(note_url, cookies_str, proxies)
            if success:
                note_info = note_info['data']['items'][0]
                note_info['url'] = note_url
                processed_info = handle_note_info(note_info)
                c.execute("INSERT INTO downloaded_notes VALUES (?,?)",
                          (note_url, str(processed_info)))
                conn.commit()
                return True, '成功', processed_info
            return False, msg, None
        except Exception as e:
            logger.error(f"爬取失败: {str(e)}")
            return False, str(e), None
        finally:
            conn.close()

    def spider_user_notes(self, task_id, user_url, save_choice, min_likes, proxies=None):
        """处理用户所有笔记"""
        try:
            task_status[task_id] = {"status": "processing", "progress": 0}

            # 获取用户笔记
            success, msg, notes = self.xhs_apis.get_user_all_notes(user_url, cookies_str, proxies)
            if not success:
                task_status[task_id] = {"status": "failed", "message": msg}
                return

            # 过滤笔记
            filtered = []
            for note in notes:
                liked_str = note.get('interact_info', {}).get('liked_count', '0')
                liked_count = self._parse_liked_count(liked_str)
                if liked_count > min_likes:
                    filtered.append(note)

            task_status[task_id]["total"] = len(filtered)
            logger.info(f'用户 {user_url} 有效笔记: {len(filtered)}条')

            # 分批处理
            batch_size = 5
            for i in range(0, len(filtered), batch_size):
                batch = filtered[i:i + batch_size]
                for note in batch:
                    note_url = f"https://www.xiaohongshu.com/explore/{note['note_id']}?xsec_token={note['xsec_token']}"
                    self.spider_note(note_url, proxies)
                    time.sleep(random.randint(1, 3))

                # 更新进度
                progress = min(i + batch_size, len(filtered))
                task_status[task_id]["progress"] = round(progress / len(filtered) * 100, 1)

            # 最终状态
            task_status[task_id].update({
                "status": "completed",
                "message": f"完成 {len(filtered)}条笔记下载",
                "downloaded": len(filtered)
            })
        except Exception as e:
            logger.error(f"用户处理异常: {str(e)}")
            task_status[task_id] = {"status": "failed", "message": str(e)}

    def spider_search_notes(self, task_id, query, require_num, save_choice, sort, note_type, min_likes, proxies=None):
        """处理搜索笔记"""
        try:
            task_status[task_id] = {"status": "processing", "progress": 0}

            # 执行搜索
            success, msg, notes = self.xhs_apis.search_some_note(
                query, require_num, cookies_str, sort, note_type, proxies
            )
            if not success:
                task_status[task_id] = {"status": "failed", "message": msg}
                return

            # 过滤笔记
            filtered = []
            for n in notes:
                if n.get('model_type') != 'note':
                    continue
                liked_str = n.get('note_card', {}).get('interact_info', {}).get('liked_count', '0')
                liked_count = self._parse_liked_count(liked_str)
                if liked_count > min_likes:
                    filtered.append(n)

            task_status[task_id]["total"] = len(filtered)
            logger.info(f'搜索 {query} 有效笔记: {len(filtered)}条')

            # 分批处理
            batch_size = 5
            for i in range(0, len(filtered), batch_size):
                batch = filtered[i:i + batch_size]
                for note in batch:
                    note_url = f"https://www.xiaohongshu.com/explore/{note['id']}?xsec_token={note['xsec_token']}"
                    self.spider_note(note_url, proxies)
                    time.sleep(random.randint(1, 3))

                # 更新进度
                progress = min(i + batch_size, len(filtered))
                task_status[task_id]["progress"] = round(progress / len(filtered) * 100, 1)

            # 最终状态
            task_status[task_id].update({
                "status": "completed",
                "message": f"完成 {len(filtered)}条搜索下载",
                "downloaded": len(filtered)
            })
        except Exception as e:
            logger.error(f"搜索处理异常: {str(e)}")
            task_status[task_id] = {"status": "failed", "message": str(e)}


# 初始化爬虫实例
spider = FlaskDataSpider()


@app.route('/api/crawl_note', methods=['POST'])
def crawl_single_note():
    """单个笔记爬取接口"""
    data = request.json
    task_id = str(uuid.uuid4())

    def task_wrapper():
        try:
            success, msg, _ = spider.spider_note(data['note_url'], data.get('proxies'))
            if success:
                task_status[task_id] = {"status": "completed", "message": "笔记下载成功"}
            else:
                task_status[task_id] = {"status": "failed", "message": msg}
        except Exception as e:
            task_status[task_id] = {"status": "failed", "message": str(e)}

    thread = threading.Thread(target=task_wrapper)
    thread.start()

    return jsonify({
        "task_id": task_id,
        "status_url": f"/api/tasks/{task_id}",
        "message": "任务已接受"
    })


@app.route('/api/crawl_user', methods=['POST'])
def crawl_user_notes():
    """用户笔记爬取接口"""
    data = request.json
    task_id = str(uuid.uuid4())

    thread = threading.Thread(
        target=spider.spider_user_notes,
        args=(task_id, data['user_url'], data['save_choice'],
              data['min_likes'], data.get('proxies'))
    )
    thread.start()

    return jsonify({
        "task_id": task_id,
        "status_url": f"/api/tasks/{task_id}",
        "message": "任务已接受"
    })


@app.route('/api/crawl_search', methods=['POST'])
def crawl_search_notes():
    """搜索笔记爬取接口"""
    data = request.json
    task_id = str(uuid.uuid4())

    thread = threading.Thread(
        target=spider.spider_search_notes,
        args=(task_id, data['query'], data['require_num'], data['save_choice'],
              data.get('sort', 'general'), data.get('note_type', 0),
              data['min_likes'], data.get('proxies'))
    )
    thread.start()

    return jsonify({
        "task_id": task_id,
        "status_url": f"/api/tasks/{task_id}",
        "message": "任务已接受"
    })


@app.route('/api/tasks/<task_id>', methods=['GET'])
def get_task_status(task_id):
    """任务状态查询接口"""
    status = task_status.get(task_id, {"status": "not_found"})
    return jsonify(status)


if __name__ == '__main__':
    # 初始化数据库
    with app.app_context():
        conn = sqlite3.connect('downloaded_notes.db')
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS downloaded_notes
                    (url TEXT PRIMARY KEY, note_info TEXT)''')
        conn.commit()
        conn.close()

    # 启动服务（端口设为8080）
    app.run(host='0.0.0.0', port=8080, threaded=True)