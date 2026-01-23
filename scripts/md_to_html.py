import re

# Read markdown file
with open("c:\\POC\\(NEW)Defense_Intelligent_Agent_Platform\\docs\\coa_recommendation_process.md", "r", encoding="utf-8") as f:
    md_content = f.read()

# Convert markdown headers to HTML
html_content = md_content
html_content = re.sub(r'^### (.*?)$', r'<h3>\1</h3>', html_content, flags=re.MULTILINE)
html_content = re.sub(r'^## (.*?)$', r'<h2>\1</h2>', html_content, flags=re.MULTILINE)
html_content = re.sub(r'^# (.*?)$', r'<h1>\1</h1>', html_content, flags=re.MULTILINE)

# Convert code blocks (but not mermaid)
html_content = re.sub(r'```python\n(.*?)```', r'<pre><code class="language-python">\1</code></pre>', html_content, flags=re.DOTALL)
html_content = re.sub(r'```sparql\n(.*?)```', r'<pre><code class="language-sparql">\1</code></pre>', html_content, flags=re.DOTALL)

# Convert mermaid blocks
html_content = re.sub(r'```mermaid\n(.*?)```', r'<div class="mermaid">\1</div>', html_content, flags=re.DOTALL)

# Convert tables (basic)
html_content = re.sub(r'^\|(.*?)\|$', lambda m: '<tr>' + ''.join(f'<td>{cell.strip()}</td>' for cell in m.group(1).split('|')) + '</tr>', html_content, flags=re.MULTILINE)

# Convert bold
html_content = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', html_content)

# Convert lists
html_content = re.sub(r'^- (.*?)$', r'<li>\1</li>', html_content, flags=re.MULTILINE)
html_content = re.sub(r'^(\d+)\. (.*?)$', r'<li>\2</li>', html_content, flags=re.MULTILINE)

# Wrap in HTML template
html_template = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>방책 추천 시스템 상세 프로세스</title>
    <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
    <style>
        body {{
            font-family: 'Malgun Gothic', sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
            line-height: 1.6;
        }}
        h1 {{ color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }}
        h2 {{ color: #34495e; border-bottom: 2px solid #95a5a6; padding-bottom: 8px; margin-top: 30px; }}
        h3 {{ color: #555; margin-top: 20px; }}
        table {{ 
            border-collapse: collapse; 
            width: 100%; 
            margin: 20px 0;
            background: white;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        th, td {{ 
            border: 1px solid #ddd; 
            padding: 12px; 
            text-align: left; 
        }}
        th {{ 
            background-color: #3498db; 
            color: white; 
            font-weight: bold;
        }}
        tr:nth-child(even) {{ background-color: #f9f9f9; }}
        pre {{ 
            background: #2c3e50; 
            color: #ecf0f1; 
            padding: 15px; 
            border-radius: 5px; 
            overflow-x: auto;
            margin: 15px 0;
        }}
        code {{ font-family: 'Consolas', monospace; }}
        .mermaid {{ 
            background: white; 
            padding: 20px; 
            border-radius: 8px; 
            margin: 20px 0;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        ul, ol {{ margin: 10px 0; padding-left: 30px; }}
        li {{ margin: 5px 0; }}
        strong {{ color: #e74c3c; }}
    </style>
</head>
<body>
    {html_content}
    <script>
        mermaid.initialize({{ startOnLoad: true, theme: 'default' }});
    </script>
</body>
</html>"""

# Save HTML file
with open("c:\\POC\\(NEW)Defense_Intelligent_Agent_Platform\\docs\\coa_recommendation_process.html", "w", encoding="utf-8") as f:
    f.write(html_template)

print("✅ HTML 파일 생성 완료!")
print("위치: c:\\POC\\(NEW)Defense_Intelligent_Agent_Platform\\docs\\coa_recommendation_process.html")
print("브라우저에서 열어서 다이어그램을 확인하세요!")
