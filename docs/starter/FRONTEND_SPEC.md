# Frontend Spec (Next.js)

## Pages
- /login
- /datasets
- /datasets/[datasetId]
- /workflows
- /workflows/[workflowId]
- /apps
- /apps/[appId]
- /chat
- /admin/users (super_admin only)
- /admin/workspaces (super_admin only)

## Auth & RBAC (UI)
- Login page: email + password → JWT
- AuthProvider + useAuth() hook
- Protected routes: redirect to /login if not authenticated
- Role-based UI:
  - super_admin: sees all pages + /admin/* + workspace switcher (all workspaces)
  - admin: sees Datasets, Workflows, Apps, Chat + workspace switcher (only their workspaces)
- Sidebar menu items filtered by role
- Workspace switcher (Topbar):
  - super_admin: dropdown all workspaces
  - admin: dropdown chỉ workspaces mình là member
  - Hiện active workspace name + ws_role badge
- Permission-based UI elements:
  - viewer: hide create/edit/delete buttons, upload areas, index buttons; show read-only badges
  - editor: show all CRUD UI, hide member management
  - owner: show all CRUD UI + member management (invite/remove/change roles)
  - super_admin: show everything + /admin/* pages

## Key components
- Sidebar + Topbar layout
- ThemeToggle (light/dark/system)
- LanguageSwitcher (EN/VI)
- WorkspaceSwitcher (super_admin: all WS, admin: own WS list)
- WorkspaceMembersPanel (owner/super_admin: invite/remove/change roles)
- UploadDropzone
- DocumentsTable (status, index button)
- ChunksPreviewModal
- WorkflowCanvas (React Flow)
- NodePropertiesPanel
- ChatComposer
- ChatStreamViewer (SSE)
- SourcesPanel

## Dark/Light Theme
- Use `next-themes` + Tailwind `darkMode: "class"`
- CSS variables for semantic color tokens
- All components must use theme-aware colors (no hardcoded colors)
- Support: light, dark, system (follow OS preference)
- Persist preference in localStorage

## Internationalization (i18n)
- Support: English (en), Vietnamese (vi)
- Use `next-intl` or `react-i18next`
- All user-facing text must use translation keys
- Translation files per feature module (common, datasets, workflows, apps, chat)
- Persist locale preference in localStorage/cookie
- Default locale: en

## SSE client behavior
- POST /v1/chat-messages { response_mode:"streaming" }
- Parse lines starting with `data:`
- Update UI incrementally per `message` event
- On `message_end` finalize message and attach citations

SSE contract aligned with Dify docs:
https://docs.dify.ai/api-reference/chat/send-chat-message

## Responsive Design

### Breakpoints (Tailwind defaults)
- `sm` (640px): mobile landscape
- `md` (768px): tablet
- `lg` (1024px): desktop
- `xl` (1280px): large desktop

### Layout behavior per breakpoint

| Component | Mobile (<768px) | Tablet (768-1023px) | Desktop (≥1024px) |
|---|---|---|---|
| **Sidebar** | Hidden, hamburger menu toggle → slide-over overlay | Collapsed (icons only), hover/click expand | Full width, always visible |
| **Topbar** | Compact: hamburger + logo + avatar only. WS switcher/theme/lang trong dropdown menu | Full topbar, tất cả controls visible | Full topbar |
| **Datasets list** | Card layout, 1 column, stacked | Card layout, 2 columns | Table layout hoặc 3-col cards |
| **Dataset detail / DocumentsTable** | Stacked cards thay vì table. Mỗi doc = card (filename, status, actions) | Simplified table (hide size column) | Full table (all columns) |
| **UploadDropzone** | Full width, tap to upload (no drag hint) | Full width with drag hint | Inline within page |
| **ChunksPreviewModal** | Full screen bottom sheet | Centered modal (80% width) | Centered modal (60% width) |
| **Workflow Canvas** | ⚠️ Limited support: read-only view, pinch-to-zoom, no drag-drop editing. Banner "Use desktop for editing" | Usable but tight: smaller node palette, side panel becomes bottom sheet | Full canvas + side panel |
| **NodePropertiesPanel** | Bottom sheet (slide up) | Bottom sheet hoặc narrow side panel | Side panel (right) |
| **Chat page** | Full screen chat, sources panel = bottom sheet khi tap source | 2-column: chat + collapsible sources | 3-column: conversations + chat + sources |
| **ChatComposer** | Fixed bottom bar, full width input | Fixed bottom bar | Inline within chat area |
| **SourcesPanel** | Bottom sheet, swipe up to see | Collapsible side panel | Always visible side panel |
| **Admin pages** | Stacked cards, simplified forms | Table layout | Full table + inline actions |
| **WorkspaceSwitcher** | Full screen modal hoặc bottom sheet | Dropdown | Dropdown |
| **Members management** | Stacked cards per member | Table | Table + inline actions |

### Mobile-specific UX
- Touch targets minimum 44x44px
- Swipe gestures: swipe right to open sidebar, swipe left to close
- Bottom sheet pattern cho modals/panels (thay vì centered modal)
- No hover states, dùng tap/long-press thay thế
- Sticky headers cho tables/lists khi scroll
- Pull-to-refresh cho list pages (datasets, workflows, apps)

### Implementation approach
- Mobile-first CSS: base styles = mobile, use `md:` `lg:` for larger screens
- Tailwind responsive utilities (`hidden md:block`, `md:hidden`, etc.)
- `useMediaQuery()` hook hoặc Tailwind `useBreakpoint` cho conditional rendering
- Test trên: iPhone SE (375px), iPhone 14 (390px), iPad (768px), Desktop (1280px+)

## UX rules (MVP)
- Poll document status when indexing
- Show top_k sources with score + snippet + open source (presigned url)
