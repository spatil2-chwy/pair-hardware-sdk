import json
import os
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, Optional, Tuple

from rclpy.node import Node

from argos_provider_bridge.core.keyspace import ArgosProviderKeyspace, PairKeyspace
from argos_provider_bridge.core.messages import event_message, heartbeat_message, response_message

try:
    import zenoh
except ImportError:
    zenoh = None


class ProviderRequestError(ValueError):
    """Request error with an optional structured code for providers that need one."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class ArgosZenohProvider(Node):
    """Base ROS node that exposes resource-scoped Argos capability requests over Zenoh."""

    def __init__(
        self,
        node_name: str,
        target_kind: str = 'robots',
        default_provider_id: str = '',
        default_target_id: str = '',
        default_provider_key_root: str = 'argos',
    ) -> None:
        super().__init__(node_name)
        self._target_kind = target_kind
        self._default_provider_id = default_provider_id
        self._default_target_id = default_target_id
        self.declare_parameter('provider_key_root', default_provider_key_root)
        self.declare_parameter('pair_key_root', '')
        self.declare_parameter('provider_id', '')
        self.declare_parameter('target_id', '')
        self.declare_parameter('zenoh_connect', '')
        self.declare_parameter('zenoh_listen', '')
        self.declare_parameter('zenoh_mode', '')
        self.declare_parameter('heartbeat_period_s', 2.0)

        self.configure_provider_identity(
            provider_id=self._string_param('provider_id') or self._default_provider_id,
            target_id=self._string_param('target_id') or self._default_target_id,
            provider_key_root=self._string_param('provider_key_root'),
            pair_key_root=self._string_param('pair_key_root'),
        )
        self.zenoh_connect = self._csv_value(self._string_param('zenoh_connect'))
        self.zenoh_listen = self._csv_value(self._string_param('zenoh_listen'))
        self.zenoh_mode = self._string_param('zenoh_mode')

        self._session = None
        self._subscribers = []
        self._event_subscriber = None
        self._worker = ThreadPoolExecutor(max_workers=4, thread_name_prefix=f'{node_name}_zenoh')
        self._shutdown = threading.Event()
        self._heartbeat_timer = None
        self._instance_id = f'{node_name}-{os.getpid()}-{uuid.uuid4().hex[:8]}'

    def configure_provider_identity(
        self,
        provider_id: str,
        target_id: str = '',
        provider_key_root: str = 'argos',
        pair_key_root: str = '',
    ) -> None:
        provider_root = str(provider_key_root or '').strip('/')
        pair_root = str(pair_key_root or '').strip('/')
        root = provider_root or pair_root or 'argos'
        provider_id = str(provider_id or '').strip('/')
        target_id = str(target_id or '').strip('/')
        if not provider_id:
            raise ValueError('provider_id parameter is required')
        self.provider_id = provider_id
        self.target_id = target_id
        self.uses_argos_resources = root == 'argos'
        if self.uses_argos_resources:
            self.keyspace = ArgosProviderKeyspace(root=root, provider_id=provider_id)
        else:
            if not target_id:
                raise ValueError('target_id parameter is required')
            self.keyspace = PairKeyspace(
                root=root,
                provider_id=provider_id,
                target_kind=self._target_kind,
                target_id=target_id,
            )

    def capability_manifest(self) -> Dict[str, Any]:
        raise NotImplementedError

    def dispatch(self, resource_id: str, op: str, args: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

    def handle_event(self, resource_id: str, event_type: str, message: Dict[str, Any]) -> None:
        pass

    def request_selector(self) -> str:
        return self.keyspace.request_selector

    def request_selectors(self) -> list[str]:
        return [self.request_selector()]

    def start_zenoh(self) -> None:
        if zenoh is None:
            raise RuntimeError("Python package 'zenoh' is not installed. Install it in this ROS environment.")

        request_selectors = self.request_selectors()
        self._session = zenoh.open(self._zenoh_config())
        self._subscribers = [
            self._session.declare_subscriber(
                request_selector,
                self._on_zenoh_sample,
            )
            for request_selector in request_selectors
        ]
        if self.uses_argos_resources:
            self._event_subscriber = self._session.declare_subscriber(
                self.keyspace.event_selector,
                self._on_zenoh_event_sample,
            )
        self.publish_manifest()
        self._heartbeat_timer = self.create_timer(
            float(self.get_parameter('heartbeat_period_s').value),
            self.publish_heartbeat,
        )
        self.get_logger().info(
            f'Bridge instance {self._instance_id} listening on {", ".join(request_selectors)}; '
            f'responding on {self.keyspace.response_prefix}'
        )

    def stop_zenoh(self) -> None:
        self._shutdown.set()
        if self._heartbeat_timer is not None:
            self.destroy_timer(self._heartbeat_timer)
            self._heartbeat_timer = None
        self._worker.shutdown(wait=False, cancel_futures=True)
        for subscriber in self._subscribers:
            self._close_or_undeclare(subscriber)
        self._subscribers = []
        self._close_or_undeclare(self._event_subscriber)
        self._close_or_undeclare(self._session)

    def publish_manifest(self) -> None:
        self.put_json(self.keyspace.manifest, self.capability_manifest())

    def publish_heartbeat(self) -> None:
        self.put_json(
            self.keyspace.heartbeat,
            heartbeat_message(
                self.keyspace.provider_id,
                getattr(self.keyspace, 'target_id', ''),
            ),
        )

    def publish_event(self, resource_id: str, event_type: str, op: str, data: Dict[str, Any]) -> None:
        if self.uses_argos_resources:
            self.put_json(
                self.keyspace.event(resource_id, event_type),
                event_message(op, data, source_provider_id=self.keyspace.provider_id),
            )
        else:
            self.put_json(self.keyspace.event(event_type), event_message(op, data))

    def put_json(self, key: str, payload: Dict[str, Any]) -> None:
        if self._session is None:
            return
        self._session.put(key, json.dumps(payload).encode('utf-8'))

    def response_payload_for_exception(self, exc: Exception) -> Tuple[Dict[str, Any], Any]:
        return {}, str(exc)

    def _on_zenoh_sample(self, sample) -> None:
        self._worker.submit(self._handle_sample, sample)

    def _on_zenoh_event_sample(self, sample) -> None:
        self._worker.submit(self._handle_event_sample, sample)

    def _handle_sample(self, sample) -> None:
        key = self._sample_key(sample)
        resource_id, request_id = self._resource_and_request_from_key(key)
        op = '<unknown>'
        try:
            payload = self._sample_payload_bytes(sample).decode('utf-8')
            request = json.loads(payload)
            request_id = str(request.get('id') or request_id)
            op = str(request.get('op') or '')
            args = request.get('args') or {}
            if not request_id:
                raise ValueError('request id is required')
            if not op:
                raise ValueError('request op is required')
            if not isinstance(args, dict):
                raise ValueError('request args must be an object')
            if not resource_id:
                raise ValueError('request resource id is required')

            self._log_request(key, resource_id, request_id, op, args)
            result = self.dispatch(resource_id, op, args)
            self._publish_response(resource_id, request_id, True, result, None)
            self._log_response(resource_id, request_id, True, result, None)
        except Exception as exc:
            self.get_logger().error(f'Request failed resource={resource_id} id={request_id} op={op}: {exc}')
            if request_id:
                result, error = self.response_payload_for_exception(exc)
                self._publish_response(resource_id, request_id, False, result, error)
                self._log_response(resource_id, request_id, False, result, error)

    def _handle_event_sample(self, sample) -> None:
        key = self._sample_key(sample)
        resource_id, event_type = self._resource_and_event_from_key(key)
        try:
            payload = self._sample_payload_bytes(sample).decode('utf-8')
            message = json.loads(payload)
            if message.get('source_provider_id') == self.keyspace.provider_id:
                return
            if not resource_id or not event_type:
                raise ValueError('event resource id and type are required')
            self.handle_event(resource_id, event_type, message)
        except Exception as exc:
            self.get_logger().error(f'Event handling failed resource={resource_id} event={event_type}: {exc}')

    def _publish_response(
        self,
        resource_id: str,
        request_id: str,
        ok: bool,
        result: Optional[Dict[str, Any]],
        error: Any,
    ) -> None:
        if self.uses_argos_resources:
            self.put_json(self.keyspace.response(resource_id, request_id), response_message(request_id, ok, result, error))
        else:
            self.put_json(self.keyspace.response(request_id), response_message(request_id, ok, result, error))

    def _log_request(
        self,
        key: str,
        resource_id: str,
        request_id: str,
        op: str,
        args: Dict[str, Any],
    ) -> None:
        trace = {
            'instance_id': self._instance_id,
            'key': key,
            'resource_id': resource_id,
            'request_id': request_id,
            'op': op,
            'api_id': args.get('api_id'),
            'parameter': args.get('parameter'),
            'topic': args.get('topic'),
            'priority': args.get('priority'),
        }
        self.get_logger().info(f'Zenoh request {json.dumps(trace, sort_keys=True)}')

    def _log_response(
        self,
        resource_id: str,
        request_id: str,
        ok: bool,
        result: Optional[Dict[str, Any]],
        error: Any,
    ) -> None:
        if self.uses_argos_resources:
            response_key = self.keyspace.response(resource_id, request_id)
        else:
            response_key = self.keyspace.response(request_id)
        trace = {
            'instance_id': self._instance_id,
            'key': response_key,
            'resource_id': resource_id,
            'request_id': request_id,
            'ok': ok,
            'result': result,
            'error': error,
        }
        self.get_logger().info(f'Zenoh response {json.dumps(trace, sort_keys=True)}')

    def _zenoh_config(self):
        config = zenoh.Config()
        if self.zenoh_connect:
            self._insert_zenoh_json5(config, 'connect/endpoints', self.zenoh_connect)
        if self.zenoh_listen:
            self._insert_zenoh_json5(config, 'listen/endpoints', self.zenoh_listen)
        if self.zenoh_mode:
            self._insert_zenoh_json5(config, 'mode', self.zenoh_mode)
        return config

    def _insert_zenoh_json5(self, config, key: str, value: Any) -> None:
        encoded = json.dumps(value)
        if hasattr(config, 'insert_json5'):
            config.insert_json5(key, encoded)
        elif hasattr(config, 'insert'):
            config.insert(key, encoded)
        else:
            config[key] = encoded

    def _string_param(self, name: str) -> str:
        return str(self.get_parameter(name).value or '')

    def _csv_value(self, value: str) -> list:
        return [item.strip() for item in value.split(',') if item.strip()]

    def _sample_key(self, sample) -> str:
        key = getattr(sample, 'key_expr', None)
        if key is None:
            key = getattr(sample, 'keyexpr', None)
        if key is None:
            key = getattr(sample, 'key', '')
        return str(key)

    def _request_id_from_key(self, key: str) -> str:
        return key.rstrip('/').split('/')[-1] if key else ''

    def _resource_and_request_from_key(self, key: str) -> tuple[str, str]:
        request_id = self._request_id_from_key(key)
        if not self.uses_argos_resources:
            return getattr(self.keyspace, 'target_id', ''), request_id
        parts = key.strip('/').split('/')
        try:
            resource_index = parts.index('resources') + 1
            return parts[resource_index], request_id
        except (ValueError, IndexError):
            return '', request_id

    def _resource_and_event_from_key(self, key: str) -> tuple[str, str]:
        parts = key.strip('/').split('/')
        try:
            resource_index = parts.index('resources') + 1
            event_index = parts.index('event') + 1
            return parts[resource_index], '/'.join(parts[event_index:])
        except (ValueError, IndexError):
            return '', ''

    def _sample_payload_bytes(self, sample) -> bytes:
        payload = getattr(sample, 'payload', b'')
        if isinstance(payload, bytes):
            return payload
        if isinstance(payload, bytearray):
            return bytes(payload)
        if hasattr(payload, 'to_bytes'):
            return bytes(payload.to_bytes())
        if hasattr(payload, 'deserialize'):
            return payload.deserialize(bytes)
        if hasattr(payload, 'to_string'):
            return payload.to_string().encode('utf-8')
        return bytes(payload)

    def _close_or_undeclare(self, obj: Any) -> None:
        if obj is None:
            return
        for method_name in ('undeclare', 'close'):
            method = getattr(obj, method_name, None)
            if callable(method):
                method()
                return
