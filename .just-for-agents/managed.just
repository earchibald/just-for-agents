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
@dry-run request_id:
    python3 -m just_for_agents dry-run "{{request_id}}"

[no-cd]
@review request_id:
    python3 -m just_for_agents review "{{request_id}}"

[no-cd]
@dashboard:
    python3 -m just_for_agents dashboard

[no-cd]
@new recipe_name command desc='' params='' author='' review_notes='':
    python3 -m just_for_agents new "{{recipe_name}}" --command "{{command}}" --desc "{{desc}}" --params "{{params}}" --author "{{author}}" --review-notes "{{review_notes}}"

[no-cd]
@edit recipe_name author='' review_notes='':
    python3 -m just_for_agents edit "{{recipe_name}}" --author "{{author}}" --review-notes "{{review_notes}}"

[no-cd]
@delete recipe_name author='' review_notes='':
    python3 -m just_for_agents delete "{{recipe_name}}" --author "{{author}}" --review-notes "{{review_notes}}"

[no-cd]
@render-include:
    python3 -m just_for_agents render-include

[no-cd]
@approve request_id operator='' rationale='':
    python3 -m just_for_agents approve "{{request_id}}" --operator "{{operator}}" --rationale "{{rationale}}"
