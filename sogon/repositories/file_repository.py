"""
File repository implementation
"""

import json
import asyncio
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from concurrent.futures import ThreadPoolExecutor

from .interfaces import FileRepository

logger = logging.getLogger(__name__)


class FileRepositoryImpl(FileRepository):
    """Implementation of FileRepository interface"""
    
    def __init__(self, max_workers: int = 4):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
    
    async def save_text_file(self, content: str, file_path: Path) -> bool:
        """Save text content to file"""
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                self.executor,
                self._save_text_sync,
                content,
                file_path
            )
            logger.debug(f"Saved text file: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save text file {file_path}: {e}")
            return False
    
    async def save_json_file(self, data: Dict[str, Any], file_path: Path) -> bool:
        """Save JSON data to file"""
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                self.executor,
                self._save_json_sync,
                data,
                file_path
            )
            logger.debug(f"Saved JSON file: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save JSON file {file_path}: {e}")
            return False
    
    async def read_text_file(self, file_path: Path) -> Optional[str]:
        """Read text content from file"""
        try:
            if not await self.file_exists(file_path):
                return None
            
            loop = asyncio.get_event_loop()
            content = await loop.run_in_executor(
                self.executor,
                self._read_text_sync,
                file_path
            )
            return content
        except Exception as e:
            logger.error(f"Failed to read text file {file_path}: {e}")
            return None
    
    async def read_json_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Read JSON data from file"""
        try:
            if not await self.file_exists(file_path):
                return None
            
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(
                self.executor,
                self._read_json_sync,
                file_path
            )
            return data
        except Exception as e:
            logger.error(f"Failed to read JSON file {file_path}: {e}")
            return None
    
    async def create_directory(self, dir_path: Path) -> bool:
        """Create directory if it doesn't exist"""
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                self.executor,
                self._create_directory_sync,
                dir_path
            )
            return True
        except Exception as e:
            logger.error(f"Failed to create directory {dir_path}: {e}")
            return False
    
    async def file_exists(self, file_path: Path) -> bool:
        """Check if file exists"""
        try:
            loop = asyncio.get_event_loop()
            exists = await loop.run_in_executor(
                self.executor,
                lambda: file_path.exists()
            )
            return exists
        except Exception as e:
            logger.error(f"Failed to check file existence {file_path}: {e}")
            return False
    
    async def get_file_info(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Get file information (size, modified time, etc.)"""
        try:
            if not await self.file_exists(file_path):
                return None
            
            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(
                self.executor,
                self._get_file_info_sync,
                file_path
            )
            return info
        except Exception as e:
            logger.error(f"Failed to get file info {file_path}: {e}")
            return None
    
    async def delete_file(self, file_path: Path) -> bool:
        """Delete file"""
        try:
            if not await self.file_exists(file_path):
                return True  # Already doesn't exist
            
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                self.executor,
                lambda: file_path.unlink()
            )
            logger.debug(f"Deleted file: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete file {file_path}: {e}")
            return False
    
    def _save_text_sync(self, content: str, file_path: Path) -> None:
        """Synchronous text file saving"""
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def _save_json_sync(self, data: Dict[str, Any], file_path: Path) -> None:
        """Synchronous JSON file saving"""
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def _read_text_sync(self, file_path: Path) -> str:
        """Synchronous text file reading"""
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def _read_json_sync(self, file_path: Path) -> Dict[str, Any]:
        """Synchronous JSON file reading"""
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _create_directory_sync(self, dir_path: Path) -> None:
        """Synchronous directory creation"""
        dir_path.mkdir(parents=True, exist_ok=True)
    
    def _get_file_info_sync(self, file_path: Path) -> Dict[str, Any]:
        """Synchronous file info retrieval"""
        stat = file_path.stat()
        return {
            "size_bytes": stat.st_size,
            "modified_time": stat.st_mtime,
            "created_time": stat.st_ctime,
            "is_file": file_path.is_file(),
            "is_directory": file_path.is_dir(),
            "name": file_path.name,
            "suffix": file_path.suffix,
            "stem": file_path.stem
        }
    
    def __del__(self):
        """Cleanup executor on deletion"""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=False)