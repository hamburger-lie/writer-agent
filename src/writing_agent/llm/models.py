"""DeepSeek model constants and default agent-to-model mappings."""

DEEPSEEK_CHAT = "deepseek-chat"
DEEPSEEK_REASONER = "deepseek-reasoner"

REASONING_MODELS = {DEEPSEEK_REASONER}

DEFAULT_MODEL_BY_AGENT = {
    "planner": DEEPSEEK_REASONER,
    "researcher": DEEPSEEK_CHAT,
    "writer": DEEPSEEK_CHAT,
    "polisher": DEEPSEEK_CHAT,
    "reviewer": DEEPSEEK_REASONER,
    "librarian": DEEPSEEK_CHAT,
}
