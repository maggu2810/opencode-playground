#!/usr/bin/env bash
# generate-skills-index.sh
# Run from the root of your skills directory.
# Generates index.json listing all skills that contain a SKILL.md file.

set -euo pipefail

OUTPUT="index.json"
SKILLS_JSON="[]"

for skill_dir in */; do
    skill_name="${skill_dir%/}"

    # Skip if no SKILL.md present
    [[ ! -f "${skill_dir}SKILL.md" ]] && continue

    # Collect all files in the skill directory
    files_json="[]"
    while IFS= read -r file; do
        relative="${file#${skill_dir}}"
        files_json=$(printf '%s' "$files_json" | \
            jq --arg f "$relative" '. += [$f]')
    done < <(find "$skill_dir" -maxdepth 1 -type f | sort)

    SKILLS_JSON=$(printf '%s' "$SKILLS_JSON" | \
        jq --arg name "$skill_name" \
           --argjson files "$files_json" \
           '. += [{"name": $name, "files": $files}]')
done

printf '%s' "$SKILLS_JSON" | jq '{skills: .}' > "$OUTPUT"
echo "Written: $OUTPUT"
