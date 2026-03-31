# Phase 0 — Bootstrap

> Goal: Infra chạy được, API + Web skeleton sẵn sàng để bắt đầu code feature.

## Tasks

### Infra

- [x] **P0.1** — Tạo `infra/docker/docker-compose.yml`
  - Services: postgres (với pgvector extension), redis, minio
  - Volume mounts cho data persistence
  - Healthcheck cho từng service
  - `.env.example` với default values
  - **Spec**: ARCHITECTURE.md, DB_SCHEMA.md (extensions)

- [x] **P0.2** — Tạo init script cho Postgres
  - `infra/docker/init-db.sql`: CREATE EXTENSION vector; tạo database
  - Đảm bảo chạy tự động khi container start lần đầu

- [x] **P0.3** — Tạo init script cho MinIO
  - Tạo default bucket khi start
  - Config access key/secret trong env

### API (FastAPI)

- [x] **P0.4** — Scaffold `apps/api/`
  - `pyproject.toml` hoặc `requirements.txt`
  - Dependencies: fastapi, uvicorn, sqlalchemy, asyncpg, python-multipart, boto3/minio, redis
  - Project structure:
    ```
    apps/api/
    ├── app/
    │   ├── main.py          # FastAPI app + lifespan
    │   ├── config.py         # Settings from env
    │   ├── db.py             # SQLAlchemy async engine + session
    │   ├── deps.py           # Dependency injection
    │   └── routers/
    │       └── health.py     # GET /health
    ├── alembic/              # migrations
    ├── alembic.ini
    └── Dockerfile
    ```

- [x] **P0.5** — Setup Alembic migrations
  - Config kết nối Postgres
  - Initial migration: tạo bảng `workspaces` (id, name, created_at) + `users` (id, email, password_hash, name, role, is_active, created_at, updated_at) + `user_workspaces` (user_id, workspace_id, ws_role, created_at)
  - **Spec**: DB_SCHEMA.md

- [ ] **P0.15** — Seed super_admin user
  - Script hoặc migration seed 1 super_admin account khi init DB
  - Default credentials từ env vars (SUPER_ADMIN_EMAIL, SUPER_ADMIN_PASSWORD)
  - role = super_admin (không cần record trong user_workspaces — implicit access tất cả)
  - Password hash bằng bcrypt
  - **Spec**: SECURITY_AND_TENANCY.md

- [ ] **P0.16** — Auth module (JWT)
  - `app/auth/`: JWT encode/decode, password hashing (bcrypt)
  - `POST /v1/auth/login` → return access_token + refresh_token + user
  - `POST /v1/auth/refresh` → return new access_token
  - `GET /v1/auth/me` → return current user
  - Auth dependency: extract user from JWT, inject vào request
  - **Spec**: API_CONTRACT.md (Auth section)

- [ ] **P0.17** — Role-based access control middleware
  - `require_super_admin`: chỉ super_admin mới access được
  - `require_auth`: cả super_admin + admin đều access được (authenticated)
  - `require_ws_role(min_role)`: check ws_role trong workspace hiện tại
    - `require_ws_role("viewer")`: member bất kỳ
    - `require_ws_role("editor")`: editor hoặc owner
    - `require_ws_role("owner")`: chỉ owner
  - Workspace context: lấy workspace_id từ header `X-Workspace-Id`
  - Admin: check membership trong user_workspaces + ws_role đủ quyền
  - Super_admin: bypass tất cả workspace checks
  - **Spec**: SECURITY_AND_TENANCY.md

- [ ] **P0.18** — Users CRUD (super_admin only)
  - `POST /v1/users` — tạo admin user (chưa assign workspace, chỉ tạo account)
  - `GET /v1/users` — list users (filter by workspace_id optional)
  - `PATCH /v1/users/{id}` — update name, is_active
  - `DELETE /v1/users/{id}` — deactivate user
  - Tất cả endpoints require super_admin role
  - **Spec**: API_CONTRACT.md

- [ ] **P0.19** — Workspaces CRUD
  - `POST /v1/workspaces` — tạo workspace + chỉ định owner (super_admin only)
  - `GET /v1/workspaces` — super_admin thấy tất cả, admin thấy workspaces mình là member
  - `PATCH /v1/workspaces/{id}` — update name (super_admin hoặc ws_role=owner)
  - `DELETE /v1/workspaces/{id}` — delete (super_admin hoặc ws_role=owner)
  - **Spec**: API_CONTRACT.md

- [ ] **P0.25** — Workspace Members API
  - `POST /v1/workspaces/{id}/members` — invite admin user vào workspace (super_admin hoặc ws_role=owner)
    - Body: { user_id, ws_role: "owner"|"editor"|"viewer" }
  - `GET /v1/workspaces/{id}/members` — list members (any workspace member)
  - `PATCH /v1/workspaces/{id}/members/{user_id}` — change ws_role (super_admin hoặc owner)
    - Không thể demote last owner
  - `DELETE /v1/workspaces/{id}/members/{user_id}` — remove member (super_admin hoặc owner)
    - Không thể remove last owner
  - **Spec**: API_CONTRACT.md

- [x] **P0.6** — `GET /health` endpoint
  - Return `{"status": "ok", "db": true, "redis": true}`
  - Check DB + Redis connectivity

### Web (Next.js)

- [x] **P0.7** — Scaffold `apps/web/`
  - Next.js + TypeScript + Tailwind CSS
  - Project structure:
    ```
    apps/web/
    ├── src/
    │   ├── app/
    │   │   ├── layout.tsx       # Root layout with sidebar
    │   │   ├── page.tsx         # Home / redirect
    │   │   ├── datasets/
    │   │   ├── workflows/
    │   │   ├── apps/
    │   │   └── chat/
    │   ├── components/
    │   │   ├── layout/
    │   │   │   ├── Sidebar.tsx
    │   │   │   └── Topbar.tsx
    │   │   └── ui/              # shared UI components
    │   └── lib/
    │       └── api.ts           # API client base
    ├── package.json
    ├── tailwind.config.ts
    └── Dockerfile
    ```
  - **Spec**: FRONTEND_SPEC.md

- [x] **P0.8** — Layout component: Sidebar + Topbar
  - Navigation links: Datasets, Workflows, Apps, Chat
  - Responsive sidebar (collapse trên mobile)
  - Sidebar hiển thị menu items dựa trên role:
    - super_admin: thấy thêm "Users", "Workspaces" management
    - admin: chỉ thấy Datasets, Workflows, Apps, Chat

- [ ] **P0.20** — Login page (`/login`)
  - Form: email + password
  - Call POST /v1/auth/login
  - Lưu JWT vào httpOnly cookie hoặc memory (không localStorage cho security)
  - Redirect tới dashboard sau khi login thành công
  - Protected routes: redirect về /login nếu chưa auth

- [ ] **P0.21** — Auth context + middleware (frontend)
  - AuthProvider: store user info + token + active workspace
  - `useAuth()` hook: user, login, logout, isSuper, isAdmin
  - `useWorkspace()` hook: activeWorkspace, wsRole, switchWorkspace, workspaces[]
  - `usePermission()` hook: canEdit, canManageMembers, isOwner, isViewer (dựa trên wsRole)
  - API client: auto attach Authorization header + X-Workspace-Id header
  - Auto refresh token khi expired

- [ ] **P0.22** — Super Admin: Users management page (`/admin/users`)
  - List users (table: email, name, role, workspace, status)
  - Create user form (email, password, name, workspace dropdown)
  - Edit/deactivate user
  - Chỉ hiển thị nếu role = super_admin

- [ ] **P0.23** — Super Admin: Workspaces management page (`/admin/workspaces`)
  - List workspaces
  - Create/edit workspace
  - Chỉ hiển thị nếu role = super_admin

- [ ] **P0.24** — Workspace switcher (tất cả users)
  - Dropdown trong Topbar để chọn workspace đang làm việc
  - super_admin: hiển thị tất cả workspaces
  - admin: hiển thị chỉ workspaces mình là member (kèm ws_role badge)
  - Hiện active workspace name + ws_role (owner/editor/viewer)
  - Khi switch workspace → reload data + update permission context
  - Auto-select workspace đầu tiên khi login (nếu admin chỉ có 1 WS)

- [ ] **P0.26** — Workspace Members management UI
  - Tab hoặc section trong workspace settings
  - Chỉ hiển thị cho owner + super_admin
  - List members: email, name, ws_role, actions
  - Invite member: search/select admin user → assign ws_role
  - Change role: dropdown (owner/editor/viewer)
  - Remove member: confirm dialog
  - Validation: không thể remove/demote last owner

- [ ] **P0.27** — Permission-aware UI components
  - `<PermissionGate wsRole="editor">` wrapper component — hide children nếu không đủ quyền
  - Datasets page: hide "New Dataset", "Upload", "Delete" buttons cho viewer
  - Workflows page: hide "New Workflow", "Save", "Delete" cho viewer
  - Apps page: hide "New App", "Edit", "Delete" cho viewer
  - Show read-only indicator/badge khi user là viewer
  - Document table: hide "Index" button cho viewer

### Responsive Design

- [ ] **P0.28** — Responsive foundation setup
  - Tailwind config: confirm breakpoints (sm:640, md:768, lg:1024, xl:1280)
  - Mobile-first approach: base CSS = mobile, scale up với `md:` `lg:`
  - `useMediaQuery()` hook hoặc `useBreakpoint()` cho conditional rendering
  - `<BottomSheet>` shared component cho mobile modals/panels
  - **Spec**: FRONTEND_SPEC.md (Responsive Design section)

- [ ] **P0.29** — Responsive Sidebar
  - Mobile (<768px): hidden by default, hamburger button trong Topbar, slide-over overlay khi mở
  - Tablet (768-1023px): collapsed (icons only), expand on hover/click
  - Desktop (≥1024px): full width, always visible
  - Swipe right to open, swipe left to close (mobile)
  - Backdrop overlay khi sidebar mở trên mobile
  - **Spec**: FRONTEND_SPEC.md

- [ ] **P0.30** — Responsive Topbar
  - Mobile: compact — hamburger + logo + avatar only. Theme/language/WS switcher gom vào dropdown menu
  - Tablet+Desktop: full topbar với tất cả controls visible
  - Touch targets minimum 44x44px cho mobile
  - **Spec**: FRONTEND_SPEC.md

- [ ] **P0.31** — Responsive shared UI primitives
  - Responsive modals: centered modal (desktop/tablet) ↔ full-screen bottom sheet (mobile)
  - Responsive tables: table layout (desktop) ↔ card/stacked layout (mobile)
  - `<ResponsiveTable>` component: auto-switch giữa table và card view theo breakpoint
  - `<ResponsiveModal>` component: auto-switch giữa modal và bottom sheet
  - Sticky headers cho tables/lists khi scroll
  - Pull-to-refresh cho list pages
  - **Spec**: FRONTEND_SPEC.md

### Dark/Light Theme

- [x] **P0.10** — Setup dark/light theme system
  - Cài `next-themes` (hoặc tự implement với CSS variables)
  - ThemeProvider wrap toàn bộ app
  - Tailwind `darkMode: "class"` config
  - CSS variables cho color tokens (background, foreground, card, border, muted, accent, etc.)
  - Đảm bảo tất cả component dùng semantic color tokens thay vì hardcode colors
  - Persist theme preference vào localStorage

- [x] **P0.11** — **ThemeToggle** component
  - Button/dropdown trong Topbar để switch light/dark/system
  - Icon thay đổi theo theme (sun/moon)
  - Smooth transition khi switch

### Internationalization (i18n)

- [x] **P0.12** — Setup i18n framework
  - Cài `next-intl` hoặc `react-i18next` + `i18next`
  - Cấu trúc translation files:
    ```
    src/
    └── locales/
        ├── en/
        │   ├── common.json      # shared: buttons, labels, nav
        │   ├── datasets.json
        │   ├── workflows.json
        │   ├── apps.json
        │   └── chat.json
        └── vi/
            ├── common.json
            ├── datasets.json
            ├── workflows.json
            ├── apps.json
            └── chat.json
    ```
  - I18nProvider wrap app
  - Persist locale preference vào localStorage/cookie
  - Default locale: `en`

- [x] **P0.13** — **LanguageSwitcher** component
  - Dropdown trong Topbar để switch EN/VI
  - Hiển thị flag icon hoặc language code
  - Đặt cạnh ThemeToggle

- [x] **P0.14** — Translation keys cho common/navigation
  - `common.json` (EN + VI): sidebar labels, button texts (Save, Cancel, Create, Delete, etc.), status labels, error messages chung
  - Tất cả text trong Sidebar, Topbar phải dùng translation keys (không hardcode)

### Integration

- [x] **P0.9** — Docker Compose dev workflow
  - Đảm bảo `docker compose up -d` start tất cả services
  - API có thể connect tới Postgres, Redis, MinIO
  - Web dev server chạy local (hoặc trong container)
  - Viết `README.md` root với setup instructions

## Acceptance Criteria

- [x] `docker compose up -d` → tất cả containers healthy
- [x] `curl localhost:8000/health` → `{"status": "ok"}`
- [x] `localhost:3000` → thấy layout với sidebar navigation
- [x] Toggle theme → UI chuyển đổi light/dark mượt mà
- [x] Switch language → tất cả text chuyển EN↔VI
- [x] Refresh page → theme + language preference được giữ nguyên
- [ ] Super admin login → thấy tất cả workspaces, users management
- [ ] Super admin tạo workspace + chỉ định owner → owner login thấy workspace đó
- [ ] Owner invite editor/viewer → họ login thấy workspace trong switcher
- [ ] Admin thuộc nhiều WS → workspace switcher hiện tất cả WS kèm ws_role badge
- [ ] Viewer login → thấy data nhưng tất cả create/edit/delete buttons bị ẩn
- [ ] Editor → CRUD resources OK, nhưng không thấy member management
- [ ] Owner → CRUD resources + invite/remove members + change roles
- [ ] Không thể remove/demote last owner của workspace
- [ ] Admin không thể access /admin/users, /admin/workspaces
- [ ] Switch workspace → data + permissions thay đổi theo workspace context
- [ ] Mobile (375px): sidebar ẩn, hamburger mở slide-over, topbar compact
- [ ] Tablet (768px): sidebar collapsed (icons), expand on click
- [ ] Desktop (1024px+): sidebar full, topbar full controls
- [ ] Modals → bottom sheet trên mobile, centered modal trên desktop
- [ ] Tables → card/stacked layout trên mobile, table trên desktop
