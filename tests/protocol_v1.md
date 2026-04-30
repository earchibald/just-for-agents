# just-for-agents Test Protocol v1

## Methodology
Each test is delegated to a fresh subagent in an isolated `/tmp/just-sandbox` directory.

## Success Criteria
1. Agent runs `just bootstrap` and `just`.
2. Agent correctly identifies missing capability.
3. Agent uses `add-tool` with valid syntax.
4. Agent executes the tool and reports the correct stdout.
5. `Justfile` remains a valid justfile.

## Test Cases
1. **whoami**: `whoami` -> Print current user.
2. **list-md**: `ls *.md` -> List markdown files.
3. **search-api**: `grep "@usage" Justfile` -> Find API usage tags.
4. **show-path**: `pwd` -> Verify workspace root.
5. **check-python**: `python3 --version` -> Verify environment.
6. **md-to-txt**: `cp {{file}}.md {{file}}.txt` -> File manipulation.
7. **greet**: `echo "{{greeting}}, {{name}}!"` -> Complex params.
8. **count-recipes**: `just --summary | wc -w` -> Meta-discovery.
9. **dry-run**: `echo "rm -rf /"` -> Safety simulation.
10. **lifecycle**: Add `temp-tool`, run it, then `remove-tool temp-tool`.
