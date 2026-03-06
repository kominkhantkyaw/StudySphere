import uuid
from typing import IO, Optional, List
from urllib.parse import urlparse

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from supabase import create_client, Client


def _get_supabase_client() -> Client:
    """
    Return a configured Supabase client or raise a clear error if settings are missing.
    """
    url = settings.SUPABASE_URL
    key = settings.SUPABASE_KEY
    if not url or not key:
        raise ImproperlyConfigured(
            'SUPABASE_URL and SUPABASE_KEY must be set in the environment to use Supabase storage.'
        )
    return create_client(url, key)


def upload_file(file: IO, prefix: str = '') -> str:
    """
    Upload a Django UploadedFile/File-like object to Supabase Storage.

    Returns the public URL on success. Raises on failure so callers can show the real error or fall back.
    """
    client = _get_supabase_client()

    # Prevent duplicate filenames using a UUID prefix
    original_name = getattr(file, "name", "upload")
    unique_name = f"{uuid.uuid4()}_{original_name}"
    path = f"{prefix.rstrip('/')}/{unique_name}" if prefix else unique_name

    # Read the file into memory; for very large files you may want a streaming approach.
    file_bytes = file.read()
    # Reset cursor so the same UploadedFile can still be saved to Django storage if needed.
    try:
        file.seek(0)
    except Exception:
        pass
    content_type = getattr(file, "content_type", None) or "application/octet-stream"

    try:
        client.storage.from_(settings.SUPABASE_BUCKET).upload(
            path,
            file_bytes,
            file_options={"content-type": content_type},
        )
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning("Supabase upload failed for %s: %s", path, exc)
        raise
    return client.storage.from_(settings.SUPABASE_BUCKET).get_public_url(path)


def delete_file_by_url(public_url: str) -> bool:
    """
    Best-effort deletion of a Supabase object given its public URL.
    Returns True if a delete was attempted without obvious errors.
    """
    if not public_url:
        return False

    try:
        parsed = urlparse(public_url)
        # Expected path: /storage/v1/object/public/<bucket>/<stored_path>
        parts: List[str] = parsed.path.split('/')
        if 'object' not in parts:
            return False
        # Find bucket segment and everything after it.
        try:
            bucket_index = parts.index(settings.SUPABASE_BUCKET)
        except ValueError:
            return False
        stored_path = '/'.join(parts[bucket_index + 1:])
        if not stored_path:
            return False

        client = _get_supabase_client()
        client.storage.from_(settings.SUPABASE_BUCKET).remove([stored_path])
        return True
    except Exception as exc:  # pragma: no cover - defensive
        print(f"[Supabase] Failed to delete {public_url}: {exc}")
        return False