from dataclasses import dataclass


@dataclass(frozen=True)
class ArgosProviderKeyspace:
    """Zenoh key builder for one Argos provider with resource-scoped requests."""

    root: str = 'argos'
    provider_id: str = ''

    def __post_init__(self) -> None:
        if not self.provider_id:
            raise ValueError('provider_id is required')

    @property
    def provider_prefix(self) -> str:
        return f'{self.root}/providers/{self.provider_id}'

    @property
    def manifest(self) -> str:
        return f'{self.provider_prefix}/manifest'

    @property
    def heartbeat(self) -> str:
        return f'{self.provider_prefix}/heartbeat'

    @property
    def request_selector(self) -> str:
        return f'{self.provider_prefix}/resources/*/request/*'

    @property
    def event_selector(self) -> str:
        return f'{self.provider_prefix}/resources/*/event/*'

    @property
    def request_prefix(self) -> str:
        return f'{self.provider_prefix}/resources'

    @property
    def response_prefix(self) -> str:
        return f'{self.provider_prefix}/resources'

    @property
    def event_prefix(self) -> str:
        return f'{self.provider_prefix}/resources'

    @property
    def state_prefix(self) -> str:
        return f'{self.provider_prefix}/resources'

    def resource_request_prefix(self, resource_id: str) -> str:
        return f'{self.provider_prefix}/resources/{resource_id}/request'

    def resource_response_prefix(self, resource_id: str) -> str:
        return f'{self.provider_prefix}/resources/{resource_id}/response'

    def resource_event_prefix(self, resource_id: str) -> str:
        return f'{self.provider_prefix}/resources/{resource_id}/event'

    def resource_state_prefix(self, resource_id: str) -> str:
        return f'{self.provider_prefix}/resources/{resource_id}/state'

    def response(self, resource_id: str, request_id: str) -> str:
        return f'{self.resource_response_prefix(resource_id)}/{request_id}'

    def event(self, resource_id: str, event_type: str) -> str:
        return f'{self.resource_event_prefix(resource_id)}/{event_type}'

    def state(self, resource_id: str, state_name: str) -> str:
        return f'{self.resource_state_prefix(resource_id)}/{state_name}'


@dataclass(frozen=True)
class PairKeyspace:
    """Legacy Pair key builder for one robot or hardware provider."""

    root: str = 'pair'
    provider_id: str = ''
    target_kind: str = 'robots'
    target_id: str = ''

    def __post_init__(self) -> None:
        if self.target_kind not in {'robots', 'hardware'}:
            raise ValueError("target_kind must be 'robots' or 'hardware'")

    @property
    def manifest(self) -> str:
        return f'{self.root}/providers/{self.provider_id}/manifest'

    @property
    def heartbeat(self) -> str:
        return f'{self.root}/providers/{self.provider_id}/heartbeat'

    @property
    def request_prefix(self) -> str:
        return f'{self.root}/{self.target_kind}/{self.target_id}/request'

    @property
    def response_prefix(self) -> str:
        return f'{self.root}/{self.target_kind}/{self.target_id}/response'

    @property
    def event_prefix(self) -> str:
        return f'{self.root}/{self.target_kind}/{self.target_id}/event'

    @property
    def state_prefix(self) -> str:
        return f'{self.root}/{self.target_kind}/{self.target_id}/state'

    @property
    def request_selector(self) -> str:
        return f'{self.request_prefix}/**'

    def response(self, request_id: str) -> str:
        return f'{self.response_prefix}/{request_id}'

    def event(self, event_type: str) -> str:
        return f'{self.event_prefix}/{event_type}'

    def state(self, state_name: str) -> str:
        return f'{self.state_prefix}/{state_name}'

