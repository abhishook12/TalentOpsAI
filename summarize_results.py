import sys

log_file = r"C:\Users\User\.gemini\antigravity\brain\20daca92-83ff-46fc-8eab-b6d5b71faf35\.system_generated\tasks\task-29.log"

summary = {}
current_file = None

with open(log_file, 'r', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if line.startswith("--- Found matches in "):
            current_file = line.replace("--- Found matches in ", "").replace(" ---", "")
            if current_file not in summary:
                summary[current_file] = {}
        elif line.startswith("Company Matched: "):
            company = line.replace("Company Matched: ", "")
            if company not in summary[current_file]:
                summary[current_file][company] = 0
            summary[current_file][company] += 1

print("Summary of findings:")
for file, companies in summary.items():
    print(f"\nFile: {file}")
    for comp, count in companies.items():
        print(f"  - {comp}: {count} records found")
