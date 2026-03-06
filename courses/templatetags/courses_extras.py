from urllib.parse import urlparse, parse_qs

from django import template


register = template.Library()


@register.filter
def is_youtube(url: str) -> bool:
    """Return True if the URL looks like a YouTube link."""
    if not url:
        return False
    try:
        parsed = urlparse(str(url))
    except Exception:
        return False
    host = (parsed.netloc or '').lower()
    return 'youtube.com' in host or 'youtu.be' in host


@register.filter
def youtube_embed(url: str) -> str:
    """
    Convert a YouTube watch/short URL to an embed URL.
    Fallback: return the original URL if we cannot parse it.
    """
    if not url:
        return ''
    try:
        parsed = urlparse(str(url))
    except Exception:
        return str(url)

    host = (parsed.netloc or '').lower()
    video_id = ''

    if 'youtube.com' in host:
        # Handle typical watch URLs: https://www.youtube.com/watch?v=VIDEO_ID
        qs = parse_qs(parsed.query or '')
        video_id = qs.get('v', [''])[0]
        # Handle share URLs like https://www.youtube.com/shorts/VIDEO_ID
        if not video_id and parsed.path:
            parts = parsed.path.strip('/').split('/')
            if parts and parts[0] in {'shorts', 'embed', 'live', 'v'} and len(parts) > 1:
                video_id = parts[1]
    elif 'youtu.be' in host:
        # Short link: https://youtu.be/VIDEO_ID (ignore query/fragment)
        video_id = (parsed.path or '').strip('/').split('/')[0].split('?')[0]

    if not video_id:
        return str(url)

    # Use youtube-nocookie.com to avoid Error 153 (embed configuration)
    return f'https://www.youtube-nocookie.com/embed/{video_id}'

