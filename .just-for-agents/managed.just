[no-cd]
@bootstrap:
    python3 -m just_for_agents bootstrap

[no-cd]
@queue:
    python3 -m just_for_agents queue

[no-cd]
@inspect request_id:
    python3 -m just_for_agents inspect "{{request_id}}"
