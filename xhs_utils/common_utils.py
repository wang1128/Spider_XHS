import os
from loguru import logger
from dotenv import load_dotenv

# !!!! 改文件夹名字 放在这里 哈哈哈哈

def load_env():
    load_dotenv()
    cookies_str = os.getenv('COOKIES')
    return cookies_str

def init():
    # 这个很重要！！！！！！！！！ 路径在这里！！！！！！
    media_base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '/Volumes/PenghaoMac2/XHS data'))
    excel_base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '/Volumes/PenghaoMac2/XHS data'))
    # media_base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '/Users/penghao/Documents/GitHub/Spider_XHS/datas/media_datas'))
    # excel_base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '/Users/penghao/Documents/GitHub/Spider_XHS/datas/media_datas'))
    for base_path in [media_base_path, excel_base_path]:
        if not os.path.exists(base_path):
            os.makedirs(base_path)
            logger.info(f'创建目录 {base_path}')
    cookies_str = load_env()
    base_path = {
        'media': media_base_path,
        'excel': excel_base_path,
    }
    return cookies_str, base_path
