import re

md_path = r"C:\Users\M.Yaswanth\.gemini\antigravity\brain\30aa54b5-df37-4ea0-8501-96113e9431f1\smart_classroom_documentation.md"

with open(md_path, 'r', encoding='utf-8') as f:
    content = f.read()

mermaid_pattern = re.compile(r'```mermaid\s*\n(.*?)\n```', re.DOTALL)
mermaid_blocks = mermaid_pattern.findall(content)

print("Total diagrams:", len(mermaid_blocks))
if len(mermaid_blocks) >= 5:
    diagram_5 = mermaid_blocks[4]
    print("--- DIAGRAM 5 ---")
    print(diagram_5[:500])
    print("...")
    print(diagram_5[-500:])
