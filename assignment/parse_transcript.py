import json

input_file = r"C:\Users\User\.gemini\antigravity\brain\30be0ab6-4891-4d63-b37e-d5f130f86a13\.system_generated\logs\transcript_full.jsonl"
output_file = r"C:\Users\User\Desktop\Osmos_DataAnalyst_Submission\AI_Transcript_RAW.md"

with open(input_file, 'r', encoding='utf-8') as f_in, open(output_file, 'w', encoding='utf-8') as f_out:
    for line in f_in:
        try:
            data = json.loads(line)
            # Only include user input and planner response (the AI's text output)
            if data.get('type') == 'USER_INPUT':
                f_out.write("### USER:\n\n")
                f_out.write(data.get('content', ''))
                f_out.write("\n\n---\n\n")
            elif data.get('type') == 'PLANNER_RESPONSE':
                # Sometimes PLANNER_RESPONSE contains text, sometimes just tool calls.
                content = data.get('content', '')
                if content and content.strip():
                    f_out.write("### AI (Gemini):\n\n")
                    f_out.write(content)
                    f_out.write("\n\n---\n\n")
        except Exception as e:
            pass
