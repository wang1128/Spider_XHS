import os
import sqlite3
import random
from loguru import logger
from apis.pc_apis import XHS_Apis
from xhs_utils.common_utils import init
from xhs_utils.data_util import handle_note_info, download_note, save_to_xlsx
import time
import sys

# 初始化数据库连接
conn = sqlite3.connect('downloaded_notes.db')
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS downloaded_notes
             (url TEXT PRIMARY KEY, note_info TEXT)''')
conn.commit()


class Data_Spider():
    def __init__(self):
        self.xhs_apis = XHS_Apis()

    def spider_note(self, note_url: str, cookies_str: str, proxies=None):
        c.execute("SELECT note_info FROM downloaded_notes WHERE url =?", (note_url,))
        result = c.fetchone()
        if result:
            logger.info(f'笔记 {note_url} 已经下载过，详细信息如下：')
            logger.info(result[0])
            return False, '笔记已下载', None

        note_info = None
        try:
            success, msg, note_info = self.xhs_apis.get_note_info(note_url, cookies_str, proxies)
            if success:
                note_info = note_info['data']['items'][0]
                note_info['url'] = note_url
                note_info = handle_note_info(note_info)
                c.execute("INSERT INTO downloaded_notes VALUES (?,?)", (note_url, str(note_info)))
                conn.commit()
        except Exception as e:
            success = False
            msg = e
        logger.info(f'爬取笔记信息 {note_url}: {success}, msg: {msg}, note_info: {note_info}')
        return success, msg, note_info

    def spider_some_note(self, notes: list, cookies_str: str, base_path: dict, save_choice: str, excel_name: str = '',
                         proxies=None):
        if (save_choice == 'all' or save_choice == 'excel') and excel_name == '':
            raise ValueError('excel_name 不能为空')
        note_list = []
        for note_url in notes:
            sleep_time = random.randint(2, 3)
            time.sleep(sleep_time)
            logger.info(f"休眠 {sleep_time} 秒模拟真人操作")
            success, msg, note_info = self.spider_note(note_url, cookies_str, proxies)
            if note_info is not None and success:
                note_list.append(note_info)
        for note_info in note_list:
            if save_choice == 'all' or save_choice == 'media':
                download_note(note_info, base_path['media'])
        # if save_choice == 'all' or save_choice == 'excel':
        #     file_path = os.path.abspath(os.path.join(base_path['excel'], f'{excel_name}.xlsx'))
        #     save_to_xlsx(note_list, file_path)

    def spider_user_all_note(self, user_url: str, cookies_str: str, base_path: dict, save_choice: str,
                             excel_name: str = '', proxies=None, min_likes=10):
        note_list = []
        try:
            # 用户目录处理
            user_id = user_url.split('/')[-1].split('?')[0]
            user_media_dir = os.path.join(base_path['media'], f"user_{user_id}")
            os.makedirs(user_media_dir, exist_ok=True)
            user_excel_dir = os.path.join(base_path['excel'], f"user_{user_id}")
            os.makedirs(user_excel_dir, exist_ok=True)
            base_path_user = {'media': user_media_dir, 'excel': user_excel_dir}

            # 获取用户笔记
            success, msg, all_note_info = self.xhs_apis.get_user_all_notes(user_url, cookies_str, proxies)
            if success:
                filtered_notes = []
                for note in all_note_info:
                    try:
                        # 调试日志
                        logger.debug(f"\n{'=' * 30}\n处理用户笔记ID: {note.get('note_id', 'unknown')}")

                        # 获取点赞数
                        interact_info = note.get('interact_info', {})
                        liked_count_str = interact_info.get('liked_count', '0')

                        # 转换处理
                        try:
                            liked_count = int(liked_count_str)
                        except ValueError:
                            logger.warning(f"无效点赞数值: {liked_count_str}, 笔记ID: {note.get('note_id')}")
                            liked_count = 0

                        logger.debug(f"用户笔记点赞数: {liked_count} (阈值: {min_likes})")

                        if liked_count > min_likes:
                            filtered_notes.append(note)
                            logger.debug("✅ 保留用户笔记")
                        else:
                            logger.debug("❌ 过滤用户笔记")
                    except Exception as e:
                        logger.error(f"处理用户笔记异常: {str(e)}")
                        continue

                all_note_info = filtered_notes
                logger.info(f'用户 {user_url} 有效作品数量（点赞>{min_likes}）: {len(all_note_info)}')

                # 生成笔记URL
                for simple_note_info in all_note_info:
                    note_url = f"https://www.xiaohongshu.com/explore/{simple_note_info['note_id']}?xsec_token={simple_note_info['xsec_token']}"
                    note_list.append(note_url)

            # 调用下载
            if save_choice in ['all', 'excel']:
                excel_name = user_id
            self.spider_some_note(note_list, cookies_str, base_path_user, save_choice, excel_name, proxies)

            # 随机休眠
            sleep_time = random.randint(2, 10)
            logger.info(f"用户主页下载完成，休眠 {sleep_time} 秒")
            time.sleep(sleep_time)

        except Exception as e:
            logger.error(f"用户主页处理异常: {str(e)}")
        return note_list, success, msg

    def spider_some_search_note(self, query: str, require_num: int, cookies_str: str, base_path: dict, save_choice: str,
                                sort="general", note_type=0, excel_name: str = '', proxies=None, min_likes=10):
        note_list = []
        try:
            # 搜索目录处理
            search_media_dir = os.path.join(base_path['media'], query)
            os.makedirs(search_media_dir, exist_ok=True)
            search_excel_dir = os.path.join(base_path['excel'], query)
            os.makedirs(search_excel_dir, exist_ok=True)
            base_path_search = {'media': search_media_dir, 'excel': search_excel_dir}

            # 执行搜索
            success, msg, notes = self.xhs_apis.search_some_note(query, require_num, cookies_str, sort, note_type,
                                                                 proxies)
            if success:
                filtered_notes = []
                for note in notes:
                    try:
                        logger.debug(f"\n{'=' * 30}\n处理搜索笔记ID: {note.get('id', 'unknown')}")

                        # 类型检查
                        if note.get('model_type') != "note":
                            logger.debug(f"非笔记类型: {note.get('model_type')}")
                            continue

                        # 获取点赞数
                        note_card = note.get('note_card', {})
                        interact_info = note_card.get('interact_info', {})
                        liked_count_str = interact_info.get('liked_count', '0')

                        # 类型转换
                        try:
                            liked_count = int(liked_count_str)
                        except ValueError:
                            logger.warning(f"无效点赞数值: {liked_count_str}, 笔记ID: {note.get('id')}")
                            liked_count = 0

                        logger.debug(f"搜索笔记点赞数: {liked_count} (阈值: {min_likes})")

                        # 过滤逻辑
                        if liked_count > min_likes:
                            filtered_notes.append(note)
                            logger.debug("✅ 保留搜索笔记")
                        else:
                            logger.debug("❌ 过滤搜索笔记")
                    except Exception as e:
                        logger.error(f"处理搜索笔记异常: {str(e)}")
                        continue

                notes = filtered_notes
                logger.info(f'搜索 {query} 有效笔记数量（点赞>{min_likes}）: {len(notes)}')

                # 生成笔记URL
                for note in notes:
                    note_url = f"https://www.xiaohongshu.com/explore/{note['id']}?xsec_token={note['xsec_token']}"
                    note_list.append(note_url)

            # 调用下载
            if save_choice in ['all', 'excel']:
                excel_name = query
            self.spider_some_note(note_list, cookies_str, base_path_search, save_choice, excel_name, proxies)

            # 随机休眠
            # sleep_time = random.randint(2, 10)
            # logger.info(f"搜索下载完成，休眠 {sleep_time} 秒")
            # time.sleep(sleep_time)

        except Exception as e:
            logger.error(f"搜索处理异常: {str(e)}")
        return note_list, success, msg


if __name__ == '__main__':
    # 配置日志
    logger.remove()
    logger.add(sys.stderr, level="DEBUG")  # 设置为DEBUG级别查看详细信息

    cookies_str, base_path = init()
    data_spider = Data_Spider()

    data_spider.spider_note(note_url="https://www.xiaohongshu.com/explore/67f7bc90000000000e00489d?xsec_token=ABqgW6BAsG4ToyFtnJx8Fg1XuER_1yql5nh9pYrCub3C4=",cookies_str= cookies_str)

    # 示例1: 搜索下载（设置min_likes=100）
    # search_queries = ["健康食谱"]
    # search_queries = [
    #     # "考公万能六项框架"
    #     # ,  # 基于网页1的高分结构化方法论[1](@ref)
    #     # "申论80分写作模板",  # 网页1/5均强调申论模板重要性[1,5](@ref)
    #     # "行测正确率提升技巧",  # 网页6/7高频提及的痛点需求[6,7](@ref)
    #     # "省考乡村振兴案例",  # 网页1中山东等省考重点方向[1](@ref)
    #     # "考公资料免费领取",  # 网页2/3/5用户引流核心路径[2,3,5](@ref)
    #     # "面试考官视角解析",  # 网页4/5强调的差异化内容[4,5](@ref)
    #     "公考网课对比测评",  # 网页3/6关于网课选择的核心需求[3,6](@ref)
    #     "考公作息时间表",  # 网页1/6提到的精细化时间管理[1,6](@ref)
    #     "事业单位备考攻略",  # 网页3/5涉及的拓展考试类型[3,5](@ref)
    #     "考公心理调适方法"  # 网页7/4提及的备考心态问题[4,7](@ref)
    # ]
    # 0: 全部, 1: 视频, 2: 图文
    # for query in search_queries:
    #     logger.info(f"\n{'#' * 30}\n开始处理搜索词: {query}")
    #     min_likes = random.randint(80, 150)
    #     data_spider.spider_some_search_note(
    #         query=query,
    #         require_num=30,
    #         cookies_str=cookies_str,
    #         base_path=base_path,
    #         save_choice='all',
    #         sort="general",
    #         note_type=0,
    #         min_likes=min_likes  # 设置点赞阈值
    #     )

    # 示例2: 用户主页下载（设置min_likes=50）
    # users = [
    #     'https://www.xiaohongshu.com/user/profile/5f08450b000000000101dc15?xsec_token=ABZocRwyzF6OvGirfHVv451r7_fbBGoVEG0HB34bM1my8=&xsec_source=pc_feed'
    # ]
    # for user_url in users:
    #     logger.info(f"\n{'#' * 30}\n开始处理用户主页: {user_url}")
    #     data_spider.spider_user_all_note(
    #         user_url=user_url,
    #         cookies_str=cookies_str,
    #         base_path=base_path,
    #         save_choice='all',
    #         min_likes=1000  # 设置点赞阈值
    #     )

    conn.close()
    logger.success("所有任务处理完成")
