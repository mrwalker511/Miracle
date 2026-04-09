import re

with open('tests/test_orchestrator_loop.py', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('from unittest.mock import MagicMock, call', 'from unittest.mock import MagicMock, AsyncMock, call')

text = text.replace('db.create_iteration.return_value = uuid.uuid4()', 'db.create_iteration = AsyncMock(return_value=uuid.uuid4())\n    db.update_task_status = AsyncMock()\n    db.update_iteration = AsyncMock()\n    db.store_metric = AsyncMock()')

text = text.replace('orch.planner = MagicMock()', 'orch.planner = AsyncMock()')
text = text.replace('orch.coder = MagicMock()', 'orch.coder = AsyncMock()')
text = text.replace('orch.tester = MagicMock()', 'orch.tester = AsyncMock()')
text = text.replace('orch.reflector = MagicMock()', 'orch.reflector = AsyncMock()')
text = text.replace('orch.metrics = MagicMock()', 'orch.metrics = AsyncMock()')

text = text.replace('orch.vector_store.find_similar_failures.return_value = []', 'orch.vector_store.find_similar_failures = AsyncMock(return_value=[])\n    orch.vector_store.store_failure_with_embedding = AsyncMock()\n    orch.vector_store.store_pattern_with_embedding = AsyncMock()')

text = text.replace('def tracking_coder(ctx):', 'async def tracking_coder(ctx):')
text = text.replace('def tracking_tester(ctx):', 'async def tracking_tester(ctx):')
text = text.replace('def tracking_reflector(ctx):', 'async def tracking_reflector(ctx):')

# replace def test_ with async def test_ and add decorator
text = re.sub(r'(\s+)def test_(.*?):', r'\1@pytest.mark.asyncio\1async def test_\2:', text)

# replace orch.run() with await orch.run()
text = text.replace('orch.run()', 'await orch.run()')
text = text.replace('result = await orch.run()', 'result = await orch.run()') # this might double if previously changed, but it wasn't.

# replace lambda side effects with async functions
# lambda ctx: (call_order.append('planner'), PLAN_RESULT)[1]
import textwrap

for agent_name, result_var in [('planner', 'PLAN_RESULT'), ('coder', 'CODE_RESULT'), ('tester', 'PASS_RESULT'), ('reviewer', '{"review": None}'), ('auditor', '{"audit": None}')]:
    find_str = f"lambda ctx: (call_order.append('{agent_name}'), {result_var})[1]"
    replace_str = f"lambda ctx: _async_tracker(call_order, '{agent_name}', {result_var})"
    text = text.replace(find_str, replace_str)

# add async tracker helper manually
helper_text = """
async def _async_tracker(call_order, name, result):
    call_order.append(name)
    return result
"""
text = text.replace('CONFIG = {', helper_text + '\nCONFIG = {')

with open('tests/test_orchestrator_loop.py', 'w', encoding='utf-8') as f:
    f.write(text)

