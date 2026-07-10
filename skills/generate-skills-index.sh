#!/usr/bin/env bash
# generate-skills-index.sh
# Run from the root of your skills directory.
# Generates index.json listing all skills that contain a SKILL.md file.
#
# Each skill entry includes a "version" field: a sha256 checksum computed
# over every file's relative path and content, recursively. This lets
# OpenCode detect skill updates (see IndexSkill.version in opencode's
# skill discovery) without hand-maintaining a version number — any change
# to any file in the skill directory changes the checksum automatically.

set -euo pipefail

OUTPUT="index.json"
SKILLS_JSON="[]"

# Computes a sha256 checksum over all files in a skill directory.
# Hashes relative path + file content for every file, in sorted path
# order, so renames/additions/removals change the checksum just like
# content edits do.
compute_version() {
    local skill_dir="$1"
    local file relative
    {
        while IFS= read -r file; do
            relative="${file#${skill_dir}}"
            printf '%s\0' "$relative"
            cat "$file"
        done < <(find "$skill_dir" -type f | sort)
    } | sha256sum | cut -d' ' -f1
}

for skill_dir in */; do
    skill_name="${skill_dir%/}"

    # Skip if no SKILL.md present
    [[ ! -f "${skill_dir}SKILL.md" ]] && continue

    # Collect all files in the skill directory, recursively
    files_json="[]"
    while IFS= read -r file; do
        relative="${file#${skill_dir}}"
        files_json=$(printf '%s' "$files_json" | \
            jq --arg f "$relative" '. += [$f]')
    done < <(find "$skill_dir" -type f | sort)

    version=$(compute_version "$skill_dir")

    SKILLS_JSON=$(printf '%s' "$SKILLS_JSON" | \
        jq --arg name "$skill_name" \
           --arg version "$version" \
           --argjson files "$files_json" \
           '. += [{"name": $name, "files": $files, "version": $version}]')
done

printf '%s' "$SKILLS_JSON" | jq '{skills: .}' > "$OUTPUT"
echo "Written: $OUTPUT"
