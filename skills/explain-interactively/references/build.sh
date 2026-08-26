#!/bin/bash
# Assembles the course from parts.
# Usage: bash build.sh <course-directory>
#
# Takes the course directory as an argument rather than reading the working
# directory: a Bash tool call starts in its own cwd, so a caller cannot rely on
# having changed into the course first.
set -e
course="${1:?usage: build.sh <course-directory>}"
[ -d "$course/modules" ] || { echo "no modules/ under $course" >&2; exit 1; }
cat "$course/_base.html" "$course"/modules/*.html "$course/_footer.html" > "$course/index.html"
echo "Built $course/index.html - open it in your browser."
