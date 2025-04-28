import sqlite3
from urllib.parse import urlparse, urlunparse


def clean_url(old_url):
    """移除URL中的查询参数和片段"""
    parsed = urlparse(old_url)
    return urlunparse(parsed._replace(query='', fragment=''))


def update_database(db_path):
    # 连接数据库
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # 创建临时备份表
        cursor.execute("CREATE TABLE IF NOT EXISTS temp_backup AS SELECT * FROM downloaded_notes WHERE 0")

        # 获取所有旧数据
        cursor.execute("SELECT url, note_info FROM downloaded_notes")
        rows = cursor.fetchall()

        for old_url, data in rows:
            new_url = clean_url(old_url)

            if new_url == old_url:
                continue  # 无需处理

            # 插入新记录（如果不存在）
            cursor.execute("""
                           INSERT
                           OR IGNORE INTO temp_backup (url, note_info)
                VALUES (?, ?)
                           """, (new_url, data))

            # 删除旧记录
            cursor.execute("DELETE FROM downloaded_notes WHERE url = ?", (old_url,))

        # 将备份数据合并回主表
        cursor.execute("""
            INSERT OR REPLACE INTO downloaded_notes (url, note_info)
            SELECT url, note_info FROM temp_backup
        """)

        # 删除临时表
        cursor.execute("DROP TABLE temp_backup")

        conn.commit()
        print("数据库更新完成！")

    except Exception as e:
        conn.rollback()
        print(f"操作失败，已回滚: {str(e)}")
    finally:
        conn.close()


def query_url_record(db_path, target_url):
    """
    查询指定URL的数据库记录
    :param db_path: 数据库路径
    :param target_url: 要查询的URL
    :return: 查询结果（存在返回记录数据，不存在返回None）
    """
    try:
        # 连接数据库
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 执行安全查询（使用参数化查询防止SQL注入）
        cursor.execute("""
                       SELECT *
                       FROM downloaded_notes
                       WHERE url = ?
                       """, (target_url,))

        # 获取结果
        result = cursor.fetchone()

        return result

    except sqlite3.Error as e:
        print(f"数据库错误: {str(e)}")
        return None
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    # 使用前请先备份数据库！
    db_path = "downloaded_notes.db"  # 修改为你的数据库路径
    # update_database(db_path)

    target_url = "https://www.xiaohongshu.com/explore/637cc54f00000000100111c3"

    # 执行查询
    record = query_url_record(db_path, target_url)

    # 处理结果
    if record:
        print("找到匹配记录：")
        print(f"URL: {record[0]}")
        print(f"关联数据: {record[1]}")
    else:
        print("未找到匹配记录")