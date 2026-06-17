import time
from typing import Any, Dict, Optional


def response_message(
    request_id: str,
    ok: bool,
    result: Optional[Dict[str, Any]] = None,
    error: Any = None,
) -> Dict[str, Any]:
    return {
        'id': request_id,
        'type': 'response',
        'ok': ok,
        'result': result if result is not None else None,
        'error': error,
        'ts': time.time(),
    }


def event_message(op: str, data: Dict[str, Any], source_provider_id: Optional[str] = None) -> Dict[str, Any]:
    message = {
        'type': 'event',
        'op': op,
        'data': data,
        'ts': time.time(),
    }
    if source_provider_id:
        message['source_provider_id'] = source_provider_id
    return message


def heartbeat_message(provider_id: str, target_id: str = '', status: str = 'online') -> Dict[str, Any]:
    return {
        'type': 'heartbeat',
        'provider_id': provider_id,
        'target_id': target_id,
        'status': status,
        'ts': time.time(),
    }
