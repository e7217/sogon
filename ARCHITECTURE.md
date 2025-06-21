# SOGON Architecture Documentation

## Overview

SOGON has been refactored to follow modern software architecture principles with clear separation of concerns, dependency injection, and testability. The architecture is implemented in two phases as outlined in the refactor instruction document.

## Phase 1: Foundation Architecture ✅

### Directory Structure

```
sogon/
├── config/              # Configuration management
│   ├── settings.py      # Pydantic settings with .env support
│   └── validation.py    # Configuration validation
├── models/              # Domain models
│   ├── audio.py         # AudioFile, AudioChunk, AudioProcessingMetadata
│   ├── transcription.py # TranscriptionResult, TranscriptionSegment
│   ├── job.py          # ProcessingJob, JobStatus, JobType
│   └── correction.py    # CorrectionResult, CorrectionMetadata
├── exceptions/          # Custom exceptions
│   ├── base.py         # Base exception classes
│   ├── audio.py        # Audio processing exceptions
│   ├── transcription.py # Transcription exceptions
│   ├── job.py          # Job execution exceptions
│   └── correction.py   # Text correction exceptions
└── utils/              # Utility functions
    ├── logging.py      # Centralized logging setup
    └── file_ops.py     # File operation utilities
```

### Key Features

- **Type Safety**: All models use dataclasses with proper type hints
- **Domain-Driven Design**: Clear separation between different business domains
- **Error Handling**: Standardized exception hierarchy
- **Configuration Management**: Centralized settings with environment variable support

## Phase 2: Service Layer Architecture ✅

### Additional Structure

```
sogon/
├── services/            # Business logic layer
│   ├── interfaces.py    # Service contracts (ABC)
│   ├── audio_service.py # Audio processing implementation
│   ├── transcription_service.py # Transcription implementation
│   ├── correction_service.py # Text correction implementation
│   ├── youtube_service.py # YouTube operations implementation
│   ├── file_service.py  # File operations implementation
│   └── workflow_service.py # Complete workflow orchestration
└── repositories/        # Data access layer
    ├── interfaces.py    # Repository contracts (ABC)
    ├── file_repository.py # File system operations
    ├── job_repository.py # Job persistence
    └── cache_repository.py # Caching operations
```

### Key Features

- **Service Layer**: Business logic separated from infrastructure concerns
- **Repository Pattern**: Data access abstraction
- **Dependency Injection**: Services receive dependencies through constructor
- **Interface Segregation**: Small, focused interfaces
- **Async Support**: Full async/await support throughout

## Service Interfaces

### AudioService
- `get_audio_info()`: Analyze audio file metadata
- `split_audio()`: Split large files into processable chunks
- `validate_format()`: Check format compatibility
- `cleanup_chunks()`: Clean up temporary files

### TranscriptionService
- `transcribe_audio()`: Transcribe single audio file
- `transcribe_chunks()`: Transcribe multiple chunks in parallel
- `combine_transcriptions()`: Merge chunk results

### CorrectionService
- `correct_text()`: Apply text corrections
- `correct_transcription()`: Correct with metadata preservation

### WorkflowService
- `process_youtube_url()`: Complete YouTube workflow
- `process_local_file()`: Complete local file workflow
- `get_job_status()`: Track processing progress

## Usage Examples

### Using the Refactored Architecture

```python
# main_refactored.py - New entry point
python main_refactored.py "https://youtube.com/watch?v=..." --format srt
python main_refactored.py "audio.mp3" --no-ai-correction
```

### Using Legacy Code (Still Works)

```python
# main.py - Original entry point
python main.py "https://youtube.com/watch?v=..." 
```

### Programmatic Usage

```python
from sogon.services import ServiceContainer

# Initialize services with dependency injection
services = ServiceContainer()

# Process YouTube URL
job = await services.workflow_service.process_youtube_url(
    url="https://youtube.com/watch?v=...",
    output_dir=Path("./output"),
    format="srt",
    enable_correction=True
)

# Check status
status = await services.workflow_service.get_job_status(job.id)
```

## Benefits of New Architecture

### 1. **Testability**
- Each service can be mocked independently
- Clear contracts through interfaces
- Dependency injection enables easy test setup

### 2. **Maintainability** 
- Single responsibility principle
- Loose coupling between components
- Clear separation of concerns

### 3. **Extensibility**
- Easy to add new services
- Plugin architecture through interfaces
- Repository pattern allows different storage backends

### 4. **Performance**
- Async/await throughout
- Parallel processing capabilities
- Efficient resource management

### 5. **Type Safety**
- Full type hints
- Pydantic models for configuration
- Static type checking support

## Migration Path

The refactored architecture coexists with the legacy code:

1. **Phase 1** ✅: Foundation models and exceptions
2. **Phase 2** ✅: Service layer and repositories  
3. **Phase 3** (Future): Event-driven architecture
4. **Phase 4** (Future): Full async workflows with queuing

## Configuration

Settings are managed through Pydantic with environment variable support:

```python
# .env file
GROQ_API_KEY="your-api-key"
MAX_CHUNK_SIZE_MB=24
AUDIO_FORMATS="mp3,m4a,wav"

# Automatic loading in services
settings = get_settings()
api_key = settings.groq_api_key
```

## Error Handling

Standardized exception hierarchy:

```python
try:
    result = await service.process_audio(audio_file)
except AudioProcessingError as e:
    logger.error(f"Audio processing failed: {e}")
except TranscriptionError as e:
    logger.error(f"Transcription failed: {e}")
except SogonError as e:
    logger.error(f"General SOGON error: {e}")
```

## Future Enhancements

### Phase 3: Event-Driven Architecture
- Event bus for workflow coordination
- Plugin system for extensibility
- Real-time progress updates

### Phase 4: Advanced Features  
- Job queuing with Redis/Celery
- Horizontal scaling support
- Web API with FastAPI
- Caching with Redis
- Metrics and monitoring