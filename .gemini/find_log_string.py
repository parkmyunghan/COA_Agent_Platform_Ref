
import os

search_text = "타겟 클래스 목록"
root_dir = r"C:\POC\COA_Agent_Platform"

for root, dirs, files in os.walk(root_dir):
    if ".git" in root or ".venv" in root:
        continue
    for file in files:
        if file.endswith(".py"):
            path = os.path.join(root, file)
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if search_text in content:
                        print(f"Found in: {path}")
            except:
                try:
                    with open(path, 'r', encoding='euc-kr') as f:
                        content = f.read()
                        if search_text in content:
                            print(f"Found in: {path}")
                except:
                    pass
