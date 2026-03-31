# Workflow Spec (mini Dify)

Workflow runtime is executed by LangGraph:
https://github.com/langchain-ai/langgraph

## Goal
Store workflow as JSON (from React Flow) and run it deterministically on backend.

## Supported node types (MVP)
1) input
2) retrieve
3) compose_prompt
4) llm_generate
5) output

## JSON schema (conceptual)
{
  "nodes": [{ "id": "...", "type": "...", "data": {...}}],
  "edges": [{ "source": "...", "target": "..."}]
}

## Node configs
### retrieve.data
- dataset_ids: string[]
- top_k: number (default 5)

### compose_prompt.data
- template: string
  Variables:
  - {{system_prompt}}
  - {{query}}
  - {{context}} (joined retrieved chunks)

### llm_generate.data
- model: string
- temperature: number
- max_tokens?: number

## Validation rules
- exactly one input node and one output node
- graph must be a DAG
- must have a path input -> output
- only allow supported node types
- for MVP, enforce linear chain (each node has at most 1 outgoing edge)

## Runtime state
- query: string
- inputs: object
- retrieved_chunks: [{chunk_id, content, score, document_id}]
- prompt_messages: [{role, content}]
- answer: string (streaming)
- citations: retriever_resources[]
