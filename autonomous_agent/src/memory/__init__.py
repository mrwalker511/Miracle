"""Memory layer — Miracle's core differentiator.

Stores failures and successful patterns in PostgreSQL + pgvector so the
agent learns across sessions. Each failure is embedded and indexed; when
the Reflector encounters an error, it queries for similar past failures
to inform the fix hypothesis.

  db_manager:       PostgreSQL CRUD for tasks, iterations, metrics
  vector_store:     pgvector similarity search (failures + patterns)
  failure_analyzer: Parses raw errors into structured FailureLog objects
  pattern_matcher:  Finds successful code templates for similar tasks
"""
