# Keystone documentation

The backend exposes seven tools: blast_radius, criticality, rank_owners, trace_decision, ownership_history, verify_path, propose_action. The agent-local submit_answer tool terminates an answer and is not an eighth backend tool.

See [the tool API](../app/README.md), [agent/dev operation](../eval/README.md), [rules](RULES.md), [catalog confidence](gate_change.md), and [Fix 4 changes and validation](fix4_changes.md). Ownership/history and rejected-document provenance are READ-only; operational actions still require a fresh current-graph pass.
