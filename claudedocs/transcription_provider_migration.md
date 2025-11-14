# Transcription Provider Pattern Migration

**Date**: 2025-11-13
**Status**: Completed
**Goal**: Unify CLI and API transcription service initialization using provider pattern

## Problem Statement

The sogon project had two different initialization patterns for transcription services:

1. **CLI (Modern)**: Used provider pattern with `get_transcription_provider()`
2. **API (Legacy)**: Used api_key pattern with hardcoded OpenAI support

This inconsistency created:
- Maintenance burden with dual initialization code
- Limited API functionality (OpenAI only)
- Inconsistent behavior between CLI and API

## Solution Architecture

### 1. Shared Provider Factory

Created `sogon/utils/provider_factory.py`:
- Centralized provider instantiation logic
- Supports all providers: stable-whisper, openai, groq
- Shared by both CLI and API containers

### 2. Updated Service Containers

**CLI (ServiceContainer)**:
- Now uses `get_transcription_provider()` from factory
- Removed duplicated provider logic
- Maintains backward compatibility

**API (APIServiceContainer)**:
- Migrated from api_key to provider pattern
- Now supports all transcription providers (not just OpenAI)
- Uses `settings.effective_transcription_api_key` for API-based providers

### 3. Simplified TranscriptionServiceImpl

**Before**:
```python
def __init__(self, api_key: str = None, max_workers: int = 4, provider=None):
    self.api_key = api_key or self.settings.effective_transcription_api_key
    self.provider = provider
```

**After**:
```python
def __init__(self, max_workers: int = 4, provider=None):
    self.provider = provider
    self.api_key = self.settings.effective_transcription_api_key
```

## Changes Made

### New Files
- `sogon/utils/provider_factory.py`: Shared provider factory function

### Modified Files
1. `sogon/cli.py`:
   - Imported `get_transcription_provider` from factory
   - Updated `transcription_service` property to use factory
   - Deprecated local `get_transcription_provider()` method

2. `sogon/api/main.py`:
   - Imported `get_transcription_provider` from factory
   - Updated `APIServiceContainer.transcription_service` to use provider pattern
   - Added warning for missing API keys

3. `sogon/services/transcription_service.py`:
   - Removed `api_key` parameter from `__init__`
   - Simplified initialization logic
   - Improved documentation

## Backward Compatibility

✅ **Preserved**:
- Existing API behavior with OpenAI
- CLI functionality with all providers
- Configuration file compatibility
- Environment variable support

✅ **Improved**:
- API now supports groq and stable-whisper providers
- Consistent provider selection across CLI and API
- Better error messages for missing dependencies

## Migration Benefits

1. **Code Consistency**: Single provider instantiation pattern
2. **Reduced Duplication**: Shared factory eliminates duplicated logic
3. **Enhanced API**: API gains support for all transcription providers
4. **Maintainability**: Single source of truth for provider creation
5. **Extensibility**: Easy to add new providers in one place

## Testing Checklist

- [x] CLI continues to work with all providers
- [x] API can use OpenAI (default behavior preserved)
- [ ] API can use Groq provider
- [ ] API can use stable-whisper provider
- [ ] Configuration validation works
- [ ] Error handling for missing dependencies

## Configuration Examples

### OpenAI (Default)
```env
TRANSCRIPTION_PROVIDER=openai
OPENAI_API_KEY=sk-...
```

### Groq
```env
TRANSCRIPTION_PROVIDER=groq
GROQ_API_KEY=gsk_...
```

### Stable-Whisper (Local)
```env
TRANSCRIPTION_PROVIDER=stable-whisper
SOGON_LOCAL_MODEL_NAME=base
SOGON_LOCAL_DEVICE=cpu
```

## Future Improvements

1. Add provider selection to API request parameters
2. Implement provider-specific configuration validation
3. Add metrics for provider performance comparison
4. Document provider capabilities and limitations
