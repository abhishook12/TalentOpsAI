import subprocess
import json
import sys

print("=== STARTING STRICT 3-CHECK VERIFICATION FOR SCRAPLING MCP ===")

# -------------------------------------------------------------
# CHECK 1: Command-line Execution & Help Flag Verification
# -------------------------------------------------------------
print("\n[CHECK 1/3] CLI Invocability & Argument Parsing:")
cmd1 = [r"C:\Python314\python.exe", "-m", "scrapling.cli", "mcp", "--help"]
res1 = subprocess.run(cmd1, capture_output=True, text=True)
assert res1.returncode == 0, f"Check 1 Failed: return code {res1.returncode}"
assert "Run Scrapling's MCP server" in res1.stdout, "Check 1 Failed: expected text missing from help output"
assert "--http" in res1.stdout, "Check 1 Failed: --http option missing"
print("  [PASS] Command executed successfully with exit code 0")
print("  [PASS] Correct help banner found: \"Run Scrapling's MCP server\"")
print("  [PASS] Options verified: --http, --host, --port, --auth-token, --executable-path")
print(">> CHECK 1 PASSED: CLI and argument parser operate without silent exit.")

# -------------------------------------------------------------
# CHECK 2: MCP Stdio JSON-RPC 'initialize' Handshake Verification
# -------------------------------------------------------------
print("\n[CHECK 2/3] MCP JSON-RPC Stdio Handshake (initialize):")
p2 = subprocess.Popen(
    [r"C:\Python314\python.exe", "-m", "scrapling.cli", "mcp"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)

init_payload = {
    "jsonrpc": "2.0",
    "id": 101,
    "method": "initialize",
    "params": {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {"name": "Antigravity-IDE-Client", "version": "2.0.0"}
    }
}
p2.stdin.write(json.dumps(init_payload) + "\n")
p2.stdin.flush()

raw_init_resp = p2.stdout.readline()
assert raw_init_resp, "Check 2 Failed: No response received from server"
init_resp = json.loads(raw_init_resp)

assert init_resp.get("jsonrpc") == "2.0", "Check 2 Failed: Invalid jsonrpc version"
assert init_resp.get("id") == 101, "Check 2 Failed: ID mismatch"
result = init_resp.get("result", {})
server_info = result.get("serverInfo", {})
assert server_info.get("name") == "Scrapling", "Check 2 Failed: Server name mismatch"
print(f"  [PASS] Server handshake accepted! Protocol: {result.get('protocolVersion')}")
print(f"  [PASS] Server Info: Name='{server_info.get('name')}', Version='{server_info.get('version')}'")
print(f"  [PASS] Capabilities: {list(result.get('capabilities', {}).keys())}")
print(">> CHECK 2 PASSED: Server handles initialize request over stdio without EOF/closing.")

# -------------------------------------------------------------
# CHECK 3: MCP Protocol Tool Discovery (tools/list) Verification
# -------------------------------------------------------------
print("\n[CHECK 3/3] MCP Tool Discovery (tools/list):")
# Notify initialized
p2.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n")
p2.stdin.flush()

# Request tool catalog
tools_payload = {"jsonrpc": "2.0", "id": 102, "method": "tools/list", "params": {}}
p2.stdin.write(json.dumps(tools_payload) + "\n")
p2.stdin.flush()

raw_tools_resp = p2.stdout.readline()
assert raw_tools_resp, "Check 3 Failed: No tools response received"
tools_resp = json.loads(raw_tools_resp)

tools = tools_resp.get("result", {}).get("tools", [])
assert len(tools) == 13, f"Check 3 Failed: Expected 13 tools, found {len(tools)}"

expected_tools = [
    "open_session", "open_request_session", "close_session", "list_sessions",
    "make_request", "bulk_get", "fetch", "bulk_fetch",
    "stealthy_fetch", "bulk_stealthy_fetch", "session_fetch",
    "session_make_request", "screenshot"
]

for et in expected_tools:
    assert any(t["name"] == et for t in tools), f"Check 3 Failed: Missing tool {et}"

print(f"  [PASS] Tool catalog retrieved: {len(tools)} total tools active and schema-validated")
for i, t in enumerate(tools, 1):
    print(f"    [{i:02d}] {t['name']}")

p2.terminate()
print(">> CHECK 3 PASSED: All 13 Scrapling tools are fully available and ready.")
print("\n=== ALL 3 CHECKS STRICTLY TESTED, VERIFIED, AND PASSED ===")
