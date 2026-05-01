[no-cd]
@bootstrap:
    python3 -m just_for_agents bootstrap

[no-cd]
@queue:
    python3 -m just_for_agents queue

[no-cd]
@inspect request_id:
    python3 -m just_for_agents inspect "{{request_id}}"

[no-cd]
@render-include:
    python3 -m just_for_agents render-include

[no-cd]
@approve request_id operator='' rationale='':
    python3 -m just_for_agents approve "{{request_id}}" --operator "{{operator}}" --rationale "{{rationale}}"
