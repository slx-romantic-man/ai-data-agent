import os
import shutil
import subprocess
import time

qdrant_path = "data/qdrant"

print("Attempting to unlock and remove Qdrant storage...")

# 方法1: 尝试使用attrib移除只读属性
try:
    subprocess.run(f'attrib -r -s -h "{qdrant_path}\\*.*" /s /d', shell=True, check=False)
    print("OK: Removed read-only attributes")
except:
    pass

# 方法2: 尝试使用rmdir强制删除
try:
    subprocess.run(f'rmdir /s /q "{qdrant_path}"', shell=True, check=False)
    time.sleep(1)
    if not os.path.exists(qdrant_path):
        print("OK: Successfully removed via rmdir")
        exit(0)
except:
    pass

# 方法3: Python递归删除
try:
    shutil.rmtree(qdrant_path, ignore_errors=True)
    time.sleep(1)
    if not os.path.exists(qdrant_path):
        print("OK: Successfully removed via shutil")
        exit(0)
except:
    pass

# 方法4: 重命名旧目录
try:
    old_name = f"{qdrant_path}.locked.{int(time.time())}"
    os.rename(qdrant_path, old_name)
    print(f"OK: Renamed to {old_name}")
    exit(0)
except Exception as e:
    print(f"FAIL: All methods failed: {e}")
    exit(1)
