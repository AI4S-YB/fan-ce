# Chat Endpoint Configuration Refactoring

**Date**: 2025-10-31
**Author**: Claude Code
**Status**: Completed

## Overview

This document describes the refactoring of the chat system to support multiple endpoints with configurable capabilities, including file upload support. The key change is removing hardcoded `agent_id` from the frontend and making the system more flexible through configuration-driven architecture.

## Objectives

1. **Remove agent_id from frontend**: Backend determines agent based on endpoint
2. **Support file upload**: Add file upload capability to chat input
3. **Configuration-driven**: Easy to add new endpoints without code changes
4. **Backward compatibility**: Existing text chat functionality remains unchanged

## Architecture Changes

### Before
```
User Input → ChatRequest (with agent_id) → Single /api/chat endpoint → Backend
```

### After
```
User Input → Route Config → ChatRequest (with optional files) → Configured endpoint → Backend
                    ↓
            File Upload Support (optional)
```

## Files Modified

### 1. New Configuration File
**File**: `apps/web-antd/src/config/chat-endpoints.ts`

```typescript
export interface ChatEndpointConfig {
  url: string                    // API endpoint URL
  inputType: 'text' | 'file'    // Input type identifier
  supportsFileUpload: boolean    // File upload capability
  fileFieldName?: string         // FormData field name for files
  maxFileSize?: number           // Max file size in MB
  acceptedFileTypes?: string[]   // Accepted file extensions
}

export const CHAT_ENDPOINTS = {
  default: {
    url: '/api/chat',
    inputType: 'text',
    supportsFileUpload: false,
  },
  fileAnalysis: {
    url: '/api/chat/file',
    inputType: 'file',
    supportsFileUpload: true,
    fileFieldName: 'files',
    maxFileSize: 10,
    acceptedFileTypes: ['.pdf', '.doc', '.docx', '.txt'],
  },
}

// Route-based endpoint selection
export function getChatEndpointConfig(path: string): ChatEndpointConfig
```

### 2. API Layer Changes
**File**: `apps/web-antd/src/api/agent/chat.ts`

**Changes**:
- Removed `agent_id` from `ChatRequest` interface
- Added `file_upload?: File[]` to `ChatRequest` interface
- Modified `buildFormData()` to accept `ChatEndpointConfig` and handle file uploads
- Modified `sendChatMessage()` to accept `ChatEndpointConfig` and build dynamic URLs

### 3. Component Changes
**File**: `apps/web-antd/src/views/agent/chat/components/ChatInput.vue`

**New Features**:
- File upload button (conditionally rendered based on `supportsFileUpload` prop)
- File list display with remove capability
- File size validation
- Modified submit event to emit `{ message: string; file_upload?: File[] }`

**New Props**:
```typescript
supportsFileUpload?: boolean
maxFileSize?: number
acceptedFileTypes?: string[]
```

### 4. Composable Changes
**File**: `apps/web-antd/src/views/agent/chat/composables/useChatStream.ts`

**Changes**:
- `sendMessage()` now accepts `ChatEndpointConfig` as second parameter
- Passes config to `sendChatMessage()` API call

### 5. Page Integration
**File**: `apps/web-antd/src/views/agent/chat/index.vue`

**Changes**:
- Removed `activeAgentId` computed property
- Added `chatEndpointConfig` computed property using route-based selection
- Modified `sendChat()` to accept `{ message: string; files?: File[] }`
- Updated all `sendMessage()` calls to include `chatEndpointConfig.value`
- Passed file upload props to `ChatInput` component

## Configuration Guide

### Adding a New Endpoint

1. **Add endpoint configuration** in `chat-endpoints.ts`:

```typescript
export const CHAT_ENDPOINTS = {
  // ... existing configs

  myNewEndpoint: {
    url: '/api/chat/custom',
    inputType: 'file',
    supportsFileUpload: true,
    fileFieldName: 'documents',
    maxFileSize: 20,
    acceptedFileTypes: ['.pdf', '.xlsx'],
  },
}
```

2. **Update route matching logic** in `getChatEndpointConfig()`:

```typescript
export function getChatEndpointConfig(path: string): ChatEndpointConfig {
  if (path.includes('/custom-chat')) return CHAT_ENDPOINTS.myNewEndpoint
  if (path.includes('/file-chat')) return CHAT_ENDPOINTS.fileAnalysis
  return CHAT_ENDPOINTS.default
}
```

3. **Add route** (optional) in `apps/web-antd/src/router/routes/modules/agent.ts`:

```typescript
{
  path: 'custom-chat',
  name: 'CustomChat',
  component: () => import('#/views/agent/chat/index.vue'),
  meta: { title: 'Custom Chat' },
}
```

That's it! No other code changes needed.

## Usage Examples

### Text-Only Chat (Default)
- Route: `/agent/chat`
- No file upload button shown
- Behavior unchanged from before

### File Upload Chat
- Route: `/agent/file-chat`
- File upload button appears in input area
- Users can attach files before sending
- Files are validated against size and type constraints

### Interrupt Functionality
- Works with both text and file upload modes
- Accept/Reject options function normally
- File uploads cleared after successful submission

## API Contract

### Request Format

**Text Chat** (FormData):
```
message: string
stream: boolean
team_id: string
project_id: string
checkpoint_id?: string
conversation_id?: string
```

**File Upload Chat** (FormData):
```
message: string
stream: boolean
team_id: string
project_id: string
file_upload: File[]  // Multiple files - field name configurable via fileFieldName
checkpoint_id?: string
conversation_id?: string
```

**Note**: The file field name in FormData is determined by `config.fileFieldName` (defaults to `'file_upload'`).

**Note**: `agent_id` is no longer sent from frontend. Backend determines agent based on endpoint.

## Benefits

1. **Flexibility**: Easy to add new endpoints without modifying core logic
2. **Maintainability**: Configuration separated from implementation
3. **Scalability**: Can support unlimited endpoint types
4. **Clean Architecture**: Single responsibility principle maintained
5. **Backward Compatibility**: Existing functionality preserved

## Testing Checklist

- [ ] Default text chat works without errors
- [ ] File upload button appears on file-enabled routes
- [ ] File size validation works correctly
- [ ] File type validation works correctly
- [ ] Multiple files can be uploaded
- [ ] Files are cleared after submission
- [ ] Interrupt functionality works with file uploads
- [ ] Error handling works for failed file uploads
- [ ] Auto-scroll works with file upload UI

## Future Enhancements

1. **Drag & Drop**: Add drag-and-drop file upload support
2. **Image Preview**: Show thumbnails for image files
3. **Upload Progress**: Show progress bar for large files
4. **Voice Input**: Add voice recording capability
5. **Multi-Modal**: Support mixed text, file, and voice inputs
6. **Dynamic Config**: Load endpoint config from backend API

## Migration Notes

For existing code that imports from modified files:

1. **ChatRequest usage**: Remove `agent_id` field, optionally add `file_upload` field
2. **sendMessage() calls**: Add second parameter `chatEndpointConfig`
3. **ChatInput events**: Update `@submit` handler to accept object instead of string

Example migration:
```typescript
// Before
emit('submit', message)

// After
emit('submit', { message, file_upload })
```

## References

- [Ant Design Upload Component](https://www.antdv.com/components/upload)
- [FormData API](https://developer.mozilla.org/en-US/docs/Web/API/FormData)
- [File API](https://developer.mozilla.org/en-US/docs/Web/API/File)
