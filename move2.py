import os
import shutil

# 定义源目录和目标目录
source_root = "/Volumes/PenghaoMac2/XHS data/小红书图文PDF输出"
target_root = "/Volumes/PenghaoMac2/分赛道整理"

# 遍历源目录所有文件及子目录
for root, dirs, files in os.walk(source_root):
    for file in files:
        # 构造源文件完整路径
        src_path = os.path.join(root, file)

        # 计算相对于源根目录的相对路径（用于匹配目标目录结构）
        rel_path = os.path.relpath(root, source_root)
        target_dir = os.path.join(target_root, rel_path)

        # 仅当目标目录存在时移动文件
        if os.path.exists(target_dir):
            try:
                dest_path = os.path.join(target_dir, file)
                shutil.move(src_path, dest_path)
                print(f"成功移动：{file} → {target_dir}")
            except Exception as e:
                print(f"移动失败：{file} - 错误信息：{str(e)}")
        else:
            print(f"跳过：目标目录不存在 {target_dir}")