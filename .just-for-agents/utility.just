[no-cd]
archive-large dir='.':
    #!/usr/bin/env bash
    command -v zip >/dev/null 2>&1 || { echo >&2 "ERROR: zip is not installed."; exit 1; }
    FILES=$(find "{{dir}}" -maxdepth 1 -type f -size +1M)
    if [ -z "$FILES" ]; then echo "No files larger than 1MB found."; exit 0; fi
    zip "archive_$(date +%Y%m%d_%H%M%S).zip" $FILES

[no-cd]
md5 file:
    #!/usr/bin/env bash
    if command -v md5sum >/dev/null 2>&1; then
        md5sum "{{file}}"
    elif command -v md5 >/dev/null 2>&1; then
        md5 "{{file}}"
    else
        echo "ERROR: No md5 tool found." >&2
        exit 1
    fi
