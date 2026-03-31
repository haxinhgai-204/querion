# Querion — Implementation Plan

> Mini-Dify: multi-workspace datasets/knowledge base, workflow canvas, SSE streaming chat with citations.

## Overview

6 phases, mỗi phase tương ứng 1 sprint trong TECH_PLAN.
Mỗi phase có file task riêng (`PHASE_X_TASKS.md`) để antigravity pick task và code.

| Phase | Tên | Mô tả | Depends on |
|-------|-----|--------|------------|
| 0 | Bootstrap | Docker infra + API/Web skeleton + Auth/RBAC | — |
| 1 | Datasets | CRUD datasets + upload documents | Phase 0 |
| 2 | Indexing | Worker pipeline + pgvector retrieval | Phase 1 |
| 3 | Chat SSE | Streaming chat + citations/sources | Phase 2 |
| 4 | Workflows | Canvas UI + LangGraph runtime | Phase 2 |
| 5 | Apps & Observability | App binding + run logs + demo | Phase 3, 4 |

## Dependency Graph

```
Phase 0 (Bootstrap)
  └── Phase 1 (Datasets)
        └── Phase 2 (Indexing)
              ├── Phase 3 (Chat SSE)
              └── Phase 4 (Workflows)
                    └── Phase 5 (Apps & Observability)
```

## Cross-cutting Requirements

- **Dark/Light Theme**: Toàn bộ UI hỗ trợ chuyển đổi sáng/tối. Setup trong Phase 0, áp dụng xuyên suốt mọi phase.
- **i18n (EN/VI)**: Đa ngôn ngữ Anh - Việt. Setup trong Phase 0, tất cả text hiển thị phải dùng translation keys.
- **Role-based Access (RBAC)**: 2 system roles (super_admin, admin) + 3 workspace roles (owner, editor, viewer). Admin có thể thuộc nhiều workspaces với ws_role khác nhau. Owner quản lý members trong WS của mình. Setup trong Phase 0, enforce xuyên suốt mọi API endpoint + UI route.
- **Responsive Design**: Mobile-first, hỗ trợ mobile (375px+) → tablet (768px+) → desktop (1024px+). Sidebar collapse, bottom sheets cho mobile, layout adapt theo breakpoint. Setup foundation trong Phase 0, mọi component ở mọi phase phải responsive.

## Definition of Done (MVP)

1. Dataset created → document uploaded → indexed → chunk preview visible
2. Workflow created in canvas → saved JSON → test-run produces answer + citations
3. App binds workflow → Chat streams via SSE → Sources panel shows top retrieved chunks
4. Minimal observability: run logs + node timings
5. UI supports dark/light theme toggle
6. UI supports English/Vietnamese language switching
7. Super admin can manage all workspaces, users, and cross-workspace data
8. Admin can belong to multiple workspaces with different roles (owner/editor/viewer)
9. Workspace owner can invite/remove members and change their roles
10. Viewer sees data read-only, editor can CRUD resources, owner manages membership
11. UI fully responsive: mobile (375px+), tablet (768px+), desktop (1024px+)

## Task File Index

- [Phase 0 Tasks](./PHASE_0_TASKS.md)
- [Phase 1 Tasks](./PHASE_1_TASKS.md)
- [Phase 2 Tasks](./PHASE_2_TASKS.md)
- [Phase 3 Tasks](./PHASE_3_TASKS.md)
- [Phase 4 Tasks](./PHASE_4_TASKS.md)
- [Phase 5 Tasks](./PHASE_5_TASKS.md)

## Conventions

- **Task ID format**: `P{phase}.{number}` (e.g., P0.1, P1.3)
- **Status**: `[ ]` todo, `[~]` in progress, `[x]` done
- **Spec refs**: link tới docs/starter/ cho chi tiết
