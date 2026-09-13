import json
import os
import re

transcript_path = r"C:\Users\Rida\.gemini\antigravity-ide\brain\78de0c4d-1fd6-4db0-b85d-476534db1b45\.system_generated\logs\transcript_full.jsonl"
if not os.path.exists(transcript_path):
    transcript_path = r"C:\Users\Rida\.gemini\antigravity-ide\brain\78de0c4d-1fd6-4db0-b85d-476534db1b45\.system_generated\logs\transcript.jsonl"

output_txt_paths = [
    r"c:\Users\Rida\Desktop\hackerrank-orchestrate-september26-main\chat_transcript.txt",
    r"c:\Users\Rida\Desktop\hackerrank-orchestrate-september26-main\chat_transcript",
    r"c:\Users\Rida\Desktop\hackerrank-orchestrate-september26-main\hackerrank-orchestrate-september26-main\chat_transcript.txt",
    r"c:\Users\Rida\Desktop\hackerrank-orchestrate-september26-main\hackerrank-orchestrate-september26-main\chat_transcript",
]

def sanitize_text(text):
    if not text:
        return ""
    # Mask GitHub tokens
    text = re.sub(r'ghp_[A-Za-z0-9]{30,}', '[REDACTED_GITHUB_TOKEN]', text)
    text = re.sub(r'github_pat_[A-Za-z0-9_]{30,}', '[REDACTED_GITHUB_TOKEN]', text)
    return text

lines_out = []
lines_out.append("=" * 80)
lines_out.append("AI CHAT TRANSCRIPT - HACKERRANK ORCHESTRATE")
lines_out.append(f"Conversation ID: 78de0c4d-1fd6-4db0-b85d-476534db1b45")
lines_out.append("=" * 80)
lines_out.append("")

with open(transcript_path, 'r', encoding='utf-8', errors='replace') as f:
    for line_idx, line in enumerate(f, 1):
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except Exception:
            continue
            
        step_idx = entry.get("step_index", line_idx)
        source = entry.get("source", "UNKNOWN")
        step_type = entry.get("type", "")
        created_at = entry.get("created_at", "")
        content = sanitize_text(entry.get("content", ""))
        tool_calls = entry.get("tool_calls", [])
        
        if step_type == "USER_INPUT" or source == "USER_EXPLICIT":
            lines_out.append(f"\n{'─'*40}")
            lines_out.append(f"[USER] (Step {step_idx} | {created_at})")
            lines_out.append(f"{'─'*40}")
            if content:
                lines_out.append(str(content).strip())
            lines_out.append("")
        elif step_type in ("PLANNER_RESPONSE", "MODEL_OUTPUT") or source == "MODEL":
            lines_out.append(f"\n{'─'*40}")
            lines_out.append(f"[ASSISTANT] (Step {step_idx} | {created_at})")
            lines_out.append(f"{'─'*40}")
            if content:
                lines_out.append(str(content).strip())
            if tool_calls:
                lines_out.append("\n[Tool Calls]:")
                for tc in tool_calls:
                    t_name = tc.get("name", "tool")
                    t_args = tc.get("args", {})
                    lines_out.append(f"  • Tool: {t_name}")
                    for k, v in t_args.items():
                        v_str = sanitize_text(str(v))
                        if len(v_str) > 300:
                            v_str = v_str[:300] + "... [truncated]"
                        lines_out.append(f"    - {k}: {v_str}")
            lines_out.append("")
        elif step_type in ("TOOL_RESPONSE", "SYSTEM_MESSAGE", "TOOL_RESULT"):
            lines_out.append(f"[SYSTEM / TOOL RESPONSE] (Step {step_idx} | {created_at})")
            if content:
                c_str = str(content)
                if len(c_str) > 1000:
                    c_str = c_str[:1000] + "\n... [truncated tool output] ..."
                lines_out.append(c_str)
            lines_out.append("")

full_transcript_text = "\n".join(lines_out)

for out_p in output_txt_paths:
    os.makedirs(os.path.dirname(out_p), exist_ok=True)
    with open(out_p, 'w', encoding='utf-8') as out_f:
        out_f.write(full_transcript_text)
    print(f"Exported sanitized transcript to: {out_p} ({len(full_transcript_text)} characters, {len(lines_out)} lines)")

print("All sanitized transcripts exported successfully!")
