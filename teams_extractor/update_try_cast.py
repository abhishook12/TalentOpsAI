path = r"C:\TalentOpsAI\backend\app\services\recruiter_store.py"
with open(path, "r", encoding="utf-8") as f:
    text = f.read()

target = 'where_clauses.append("created_at >= CAST(? AS TIMESTAMP)")'
replacement = 'where_clauses.append("TRY_CAST(created_at AS TIMESTAMP) >= CAST(? AS TIMESTAMP)")'

text = text.replace(target, replacement)
with open(path, "w", encoding="utf-8") as f:
    f.write(text)
print("Updated recruiter_store.py with TRY_CAST!")
