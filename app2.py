# app.py
import logging
import os
import sqlite3
import random
import threading
import uuid
import re
import time
import sys
from collections import defaultdict
from flask import Flask, request, jsonify
from loguru import logger
from pathlib import Path
from apis.pc_apis import XHS_Apis
from xhs_utils.common_utils import init
from xhs_utils.data_util import handle_note_info, download_note, save_to_xlsx

# 初始化Flask应用
app = Flask(__name__)

# ================== 日志配置 ==================
log_dir = Path("logs")
log_dir.mkdir(parents=True, exist_ok=True)

logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
           "<level>{level: <8}</level> | "
           "<cyan>{module}.{function}:{line}</cyan> - "
           "<level>{message}</level>",
    level="DEBUG"
)
logger.add(
    log_dir / "xhs_spider_{time:YYYY-MM-DD}.log",
    rotation="00:00",
    retention="30 days",
    encoding="utf-8",
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {module}.{function}:{line} - {message}"
)

# ================== 全局初始化 ==================
cookies_str, base_path = init()
task_status = defaultdict(dict)


# ================== 核心爬虫类 ==================
class FlaskDataSpider:
    def __init__(self):
        self.xhs_apis = XHS_Apis()
        self.liked_regex = re.compile(r"^(\d+\.?\d*)([万万千]?)")
        self.lock = threading.Lock()
        self.last_request = 0
        self.request_interval = random.randint(15, 25)  # 随机间隔15-25秒

        logger.info("爬虫实例初始化完成 | 请求间隔: {}秒", self.request_interval)

    # ================ 工具方法 ================
    def _get_db_connection(self):
        """获取数据库连接"""
        conn = sqlite3.connect('downloaded_notes.db', check_same_thread=False)
        conn.execute("PRAGMA busy_timeout = 5000")
        return conn

    def _rate_limit(self):
        """请求频率控制"""
        with self.lock:
            elapsed = time.time() - self.last_request
            if elapsed < self.request_interval:
                wait_time = self.request_interval - elapsed
                logger.debug("频率控制 | 需要等待: {:.2f}s", wait_time)
                time.sleep(wait_time)
            self.last_request = time.time()
            logger.debug("频率控制 | 最新请求时间: {}", time.strftime("%H:%M:%S", time.localtime(self.last_request)))

    def _parse_liked_count(self, liked_str):
        """解析点赞数"""
        try:
            cleaned = liked_str.replace(',', '').strip()
            match = self.liked_regex.match(cleaned)
            if not match:
                logger.warning("点赞数解析失败 | 原始内容: {}", liked_str)
                return 0

            num_part, unit = match.groups()
            num = float(num_part)
            multiplier = {'万': 10000, '千': 1000}.get(unit, 1)
            result = int(num * multiplier)
            logger.debug("点赞数解析成功 | 原始: {} → 转换: {}", liked_str, result)
            return result
        except Exception as e:
            logger.error("点赞数解析异常 | 错误: {}", str(e))
            return 0

    # ================ 核心功能 ================
    def spider_search_notes(self, task_id, query, require_num, save_choice, sort, note_type, min_likes):
        """搜索笔记爬取主逻辑"""
        task_start = time.time()
        try:
            logger.info("【搜索任务启动】ID: {} | 关键词: {} | 数量: {} | 类型: {}",
                        task_id, query, require_num, note_type)

            # 初始化任务状态
            task_status[task_id] = {
                "status": "processing",
                "progress": 0,
                "total": 0,
                "success": 0,
                "failed": 0,
                "details": [],
                "current_url": None,
                "query": query,
                "start_time": time.strftime("%Y-%m-%d %H:%M:%S")
            }

            # 创建存储目录
            media_dir = os.path.join(base_path['media'], f"search_{query}")
            excel_dir = os.path.join(base_path['excel'], f"search_{query}")
            os.makedirs(media_dir, exist_ok=True)
            os.makedirs(excel_dir, exist_ok=True)
            logger.debug("存储目录创建完成 | 媒体: {} | Excel: {}", media_dir, excel_dir)

            # 执行搜索
            logger.info("正在执行搜索 | 关键词: {}...", query)
            success, msg, notes = self.xhs_apis.search_some_note(
                query, require_num, cookies_str, sort, note_type
            )
            if not success:
                logger.error("搜索失败 | 原因: {}", msg)
                task_status[task_id].update({"status": "failed", "message": msg})
                return

            # 过滤笔记
            original_count = len(notes)
            filtered = []
            for idx, note in enumerate(notes):
                if note.get('model_type') != 'note':
                    continue
                liked_str = note.get('note_card', {}).get('interact_info', {}).get('liked_count', '0')
                liked_count = self._parse_liked_count(liked_str)
                if liked_count > min_likes:
                    filtered.append(note)

            logger.info("笔记过滤完成 | 原始数量: {} | 有效数量: {} | 最低点赞: {}",
                        original_count, len(filtered), min_likes)
            task_status[task_id]["total"] = len(filtered)

            # 处理笔记
            note_list = []
            for idx, note in enumerate(filtered, 1):
                note_url = None
                try:
                    self._rate_limit()  # 频率控制

                    # 构建笔记URL
                    note_id = note['id']
                    xsec_token = note['xsec_token']
                    note_url = f"https://www.xiaohongshu.com/explore/{note_id}?xsec_token={xsec_token}"
                    task_status[task_id]["current_url"] = note_url

                    logger.debug("正在处理笔记 {}/{} | URL: {}", idx, len(filtered), note_url)

                    # 处理单个笔记
                    success, msg, note_info = self.spider_note(note_url, media_dir)
                    if success:
                        note_list.append(note_info)
                        task_status[task_id]["success"] += 1
                        logger.debug("笔记处理成功 | URL: {}", note_url)
                    else:
                        task_status[task_id]["failed"] += 1
                        logger.warning("笔记处理失败 | URL: {} | 原因: {}", note_url, msg)

                    # 记录详情
                    task_status[task_id]["details"].append({
                        "url": note_url,
                        "status": "success" if success else "failed",
                        "message": msg,
                        "timestamp": time.strftime("%H:%M:%S")
                    })

                    # 更新进度
                    progress = round((idx / len(filtered)) * 100, 1)
                    task_status[task_id]["progress"] = progress

                    # 定期日志
                    if idx % 5 == 0 or idx == len(filtered):
                        logger.info("处理进度 | {}/{} ({:.1f}%) | 成功率: {:.1f}%",
                                    idx, len(filtered), progress,
                                    (task_status[task_id]["success"] / idx) * 100)

                except Exception as e:
                    logger.error("笔记处理异常 | URL: {} | 错误: {}", note_url, str(e), exc_info=True)
                    task_status[task_id]["failed"] += 1
                    task_status[task_id]["details"].append({
                        "url": note_url,
                        "status": "failed",
                        "message": str(e),
                        "timestamp": time.strftime("%H:%M:%S")
                    })

            # 保存Excel
            if save_choice in ['all', 'excel'] and note_list:
                excel_path = os.path.join(excel_dir, f"search_{query}.xlsx")
                logger.info("正在生成Excel文件 | 路径: {}", excel_path)
                save_to_xlsx(note_list, excel_path)
                task_status[task_id]["excel_path"] = excel_path
                logger.success("Excel文件已保存 | 文件: {}", excel_path)

            # 更新最终状态
            total_time = time.time() - task_start
            task_status[task_id].update({
                "status": "completed",
                "message": f"完成 {len(filtered)}条搜索（成功{task_status[task_id]['success']}条）",
                "current_url": None,
                "total_time": f"{total_time:.1f}s",
                "avg_time": f"{total_time / len(filtered):.1f}s/条"
            })
            logger.success("任务完成 | ID: {} | 总耗时: {} | 平均速度: {}",
                           task_id,
                           task_status[task_id]["total_time"],
                           task_status[task_id]["avg_time"])

        except Exception as e:
            logger.critical("搜索任务异常 | ID: {} | 错误: {}", task_id, str(e), exc_info=True)
            task_status[task_id].update({
                "status": "failed",
                "message": str(e),
                "current_url": None
            })

    def spider_note(self, note_url: str, save_path: str):
        """单笔记处理核心方法"""
        conn = self._get_db_connection()
        try:
            logger.debug("开始处理笔记 | URL: {}", note_url)

            # 检查重复
            c = conn.cursor()
            c.execute("SELECT note_info FROM downloaded_notes WHERE url=?", (note_url,))
            if c.fetchone():
                logger.warning("跳过重复笔记 | URL: {}", note_url)
                return True, '笔记已存在', None

            # 获取数据
            logger.debug("正在获取笔记详情 | URL: {}", note_url)
            success, msg, note_info = self.xhs_apis.get_note_info(note_url, cookies_str)
            if not success:
                logger.error("API请求失败 | URL: {} | 原因: {}", note_url, msg)
                return False, msg, None

            # 处理数据
            raw_data = note_info['data']['items'][0]
            processed_info = handle_note_info(raw_data)
            processed_info['url'] = note_url
            logger.debug("数据处理完成 | 类型: {} | 媒体数: {}",
                         processed_info['note_type'],
                         len(processed_info['media']))

            # 存储到数据库
            logger.debug("正在写入数据库 | URL: {}", note_url)
            c.execute("INSERT INTO downloaded_notes VALUES (?,?)",
                      (note_url, str(processed_info)))
            conn.commit()
            logger.debug("数据库写入成功 | URL: {}", note_url)

            # 保存媒体文件
            logger.debug("正在保存媒体文件 | 路径: {}", save_path)
            download_note(processed_info, save_path)
            logger.success("媒体保存完成 | 路径: {} | 文件数: {}",
                           save_path, len(processed_info['media']))

            return True, '成功', processed_info

        except Exception as e:
            conn.rollback()
            logger.error("笔记处理失败 | URL: {} | 错误: {}", note_url, str(e), exc_info=True)
            return False, str(e), None

        finally:
            conn.close()
            logger.debug("数据库连接已关闭 | URL: {}", note_url)


# ================== Flask路由 ==================
@app.route('/api/crawl_search', methods=['POST'])
def crawl_search():
    """搜索接口"""
    data = request.json
    task_id = str(uuid.uuid4())

    def thread_task():
        # 初始化线程内日志
        logger.configure(handlers=[
            {
                "sink": sys.stderr,
                "format": "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | {level} | {message}",
                "level": "DEBUG"
            },
            {
                "sink": log_dir / "xhs_spider.log",
                "rotation": "500 MB",
                "retention": "30 days",
                "level": "DEBUG"
            }
        ])

        with app.app_context():  # 保持上下文
            spider.spider_search_notes(
                task_id,
                data['query'],
                data['require_num'],
                data.get('save_choice', 'all'),
                data.get('sort', 'general'),
                data.get('note_type', 0),
                data.get('min_likes', 100)
            )

    threading.Thread(target=thread_task).start()
    return jsonify({"task_id": task_id})


@app.route('/api/tasks/<task_id>', methods=['GET'])
def get_task_status(task_id):
    """任务状态查询"""
    status = task_status.get(task_id, {"status": "not_found"})
    logger.debug("状态查询 | ID: {} | 状态: {}", task_id, status.get('status'))
    return jsonify(status)


# ================== 启动服务 ==================
if __name__ == '__main__':
    # 禁用Flask默认日志
    app.logger.disabled = True
    logging.getLogger('werkzeug').disabled = True
    # 初始化数据库
    with app.app_context():
        try:
            conn = sqlite3.connect('downloaded_notes.db')
            conn.execute('''CREATE TABLE IF NOT EXISTS downloaded_notes
                          (url TEXT PRIMARY KEY, 
                           note_info TEXT,
                           create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
            conn.commit()
            logger.success("数据库初始化完成 | 路径: downloaded_notes.db")
        except Exception as e:
            logger.critical("数据库初始化失败 | 错误: {}", str(e))
            sys.exit(1)
        finally:
            conn.close()

    # 启动服务
    logger.info("服务启动 | 端口: 8080 | 媒体存储路径: {}", base_path['media'])
    app.run(host='0.0.0.0', port=8080, threaded=True)