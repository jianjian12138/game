import unittest
from core.agent_adapters import (
    AgentAdapterRegistry,
    ClaudeCodeAdapter,
    OpenAICodexAdapter,
    HermesAgentAdapter,
    StandaloneCLIAdapter
)

class TestAgentAdapters(unittest.TestCase):
    def test_registry_contains_all_target_frameworks(self):
        adapters = AgentAdapterRegistry.list_all_adapters()
        self.assertIn("claude_code", adapters)
        self.assertIn("codex", adapters)
        self.assertIn("hermes", adapters)
        self.assertIn("standalone", adapters)

    def test_claude_code_adapter_mcp_tools(self):
        adapter = AgentAdapterRegistry.get_adapter("claude_code")
        self.assertIsNotNone(adapter)
        self.assertEqual(adapter.protocol, "mcp_stdio")
        tools = adapter.list_tools()
        self.assertGreater(len(tools), 10)
        # Test tool execution
        res = adapter.execute_tool("list_agents", {})
        self.assertEqual(res["status"], "SUCCESS")

    def test_openai_codex_adapter_function_calling_schema(self):
        adapter = AgentAdapterRegistry.get_adapter("codex")
        self.assertIsNotNone(adapter)
        self.assertEqual(adapter.protocol, "openai_function_calling")
        schemas = adapter.list_tools()
        self.assertGreater(len(schemas), 10)
        self.assertEqual(schemas[0]["type"], "function")
        self.assertIn("name", schemas[0]["function"])

    def test_hermes_adapter_sdk_execution(self):
        adapter = AgentAdapterRegistry.get_adapter("hermes")
        self.assertIsNotNone(adapter)
        self.assertEqual(adapter.protocol, "python_sdk")
        res = adapter.execute_tool("simulate_monte_carlo", {"games": 50})
        self.assertEqual(res["status"], "SUCCESS")
        self.assertIn("matrix", res)

if __name__ == "__main__":
    unittest.main()
