# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common Development Commands

### Development Servers
- `pnpm dev` - Start all applications simultaneously
- `pnpm dev:antd` - Start Ant Design Vue app (port 5666)
- `pnpm dev:ele` - Start Element Plus app (port 5667)  
- `pnpm dev:naive` - Start Naive UI app (port 5668)
- `pnpm dev:docs` - Start documentation site (port 5173)
- `pnpm dev:play` - Start playground app (port 5555)

### Build Commands
- `pnpm build` - Build all applications for production
- `pnpm build:antd` - Build only Ant Design Vue app
- `pnpm build:ele` - Build only Element Plus app
- `pnpm build:naive` - Build only Naive UI app
- `pnpm build:analyze` - Build with bundle analysis

### Quality Assurance
- `pnpm lint` - Run ESLint for code quality
- `pnpm format` - Format code with Prettier
- `pnpm check` - Run all checks (circular deps, types, spelling)
- `pnpm check:type` - TypeScript type checking
- `pnpm test:unit` - Run unit tests with Vitest
- `pnpm test:e2e` - Run end-to-end tests

### Utility Commands
- `pnpm clean` - Clean build artifacts and dependencies
- `pnpm reinstall` - Clean reinstall all dependencies
- `pnpm preview` - Preview built applications

### Single Test Commands
- `vitest run --dom` - Run all unit tests
- `vitest run --dom --reporter=verbose` - Run unit tests with detailed output
- `vitest run --dom packages/utils` - Run tests for specific package
- `pnpm -F playground test:e2e` - Run E2E tests for playground only

## Architecture Overview

This is a Vue 3 + TypeScript monorepo using pnpm workspaces, built on the vben-admin framework. The project demonstrates multi-UI framework support with shared core functionality.

### Monorepo Structure

**Applications (`/apps/`):**
- `web-antd/` - Primary enterprise admin app using Ant Design Vue
- `web-ele/` - Element Plus variant
- `web-naive/` - Naive UI variant
- `backend-mock/` - Development API mock server

**Core Packages (`/packages/`):**
- `@core/` - Fundamental UI components and utilities
- `effects/` - Business logic packages (access, layouts, hooks, plugins, request)
- `types/` - Shared TypeScript definitions
- `stores/` - Pinia state management
- `locales/` - Internationalization
- `icons/` - Icon management
- `utils/` - Utility functions

**Internal Tools (`/internal/`):**
- `*-config/` packages - Shared configuration for ESLint, Vite, Tailwind, etc.

### Key Technologies
- **Vue 3** with Composition API
- **TypeScript** for type safety
- **Vite** for fast development and building
- **Pinia** for state management
- **Vue Router** for routing
- **Tailwind CSS** for styling
- **Turbo** for monorepo task orchestration

### Application Structure (web-antd example)

**Core Directories:**
- `src/api/` - API service layer with organized modules (auth, system, apps, platform)
- `src/router/` - Vue Router configuration with guard system
- `src/store/` - Pinia stores for state management
- `src/views/` - Page components organized by feature
- `src/components/` - Reusable UI components
- `src/layouts/` - Application layout components
- `src/utils/` - Utility functions and helpers

**Important Files:**
- `src/router/index.ts` - Main router configuration
- `src/main.ts` - Application entry point
- `src/bootstrap.ts` - Application initialization
- `vite.config.mts` - Vite configuration with proxy setup

## Development Guidelines

### Component Organization
- Place reusable components in `src/components/`
- Organize by feature in subdirectories with index.ts exports
- Use TypeScript interfaces in separate `.ts` files for complex types

### API Integration
- API services are in `src/api/` organized by domain
- Use the shared request client from `@vben/request`
- Proxy configuration in vite.config.mts routes `/api/v1` to backend

### State Management
- Use Pinia stores in `src/store/modules/`
- Export stores from `src/store/index.ts`
- Follow the established patterns for auth, user, and app state

### Routing
- Route definitions in `src/router/routes/modules/`
- Use route guards in `src/router/guard.ts`
- Follow the hierarchical menu structure

### Styling
- Uses Tailwind CSS as primary styling solution
- Component-specific styles in `.vue` files with `<style scoped>`
- Global styles and theme variables in packages

### Environment Configuration
- Environment files: `.env`, `.env.development`, `.env.production`
- API proxy configured in `vite.config.mts`
- Default development API: `http://127.0.0.1:8002/api/v1`
- Default ports: Antd (5666), Element (5667), Naive (5668), Docs (5173), Playground (5555)

### Request Handling Architecture
- Centralized request client in `src/api/request.ts` with interceptors
- Automatic token injection and refresh logic
- Project/team ID injection for multi-tenant support
- Error handling with Ant Design message integration
- API services organized by domain in `src/api/` modules

## Testing Strategy

- Unit tests with Vitest (`vitest.config.ts`)
- E2E tests with Playwright (`playground/__tests__/e2e/`)
- Component tests using `@vue/test-utils`

## Package Management

- Uses pnpm with workspace configuration (`pnpm-workspace.yaml`)
- Shared dependencies via catalog in pnpm-workspace.yaml
- Workspace dependencies use `workspace:*` protocol
- Node.js 20.10.0+ and pnpm 9.12.0+ required
- Package manager locked to pnpm@10.10.0

## Monorepo Build System

- Turbo for task orchestration and caching (`turbo.json`)
- Build outputs cached in `dist/`, `.nitro/`, `.output/` directories
- Global dependencies tracked for cache invalidation
- Development tasks run with `cache: false` and `persistent: true`

## Code Quality and Tooling

### Linting and Formatting
- ESLint configuration in `internal/lint-configs/eslint-config/`
- Prettier and Stylelint configs in respective internal packages
- Lefthook for Git hooks management (`lefthook.yml`)
- CSpell for spell checking with custom dictionary

### Build Configuration
- Vite configuration abstracted in `internal/vite-config/`
- Tailwind CSS configuration in `internal/tailwind-config/`
- TypeScript configurations in `internal/tsconfig/`
- SVG icons plugin configured in `vite.config.mts`

## Key Development Patterns

### Component Structure
- Components use `<script setup>` syntax with TypeScript
- Props and emits defined with proper TypeScript interfaces
- Composables follow `use-*` naming convention
- Component adapters in `src/adapter/` for UI framework integration

### Authentication Flow
- JWT token-based authentication with refresh tokens
- Access control via `@vben/access` directives
- Login expiration handling with modal or redirect options
- Route guards in `src/router/guard.ts`

### State Management
- Pinia stores with TypeScript support
- Store modules for auth, user, app, dict, project
- Persistent state with encryption using secure-ls
- Multi-tenant support with project/team context

### API Integration Pattern
```typescript
// API services follow this structure:
export const someApi = (params: SomeParams): Promise<ResponseType> => {
  return requestClient.post('/endpoint', params);
};
```
