---
id: ${id}
title: ${title_yaml}
date: ${date}
tags: ${tags}
type: project
publish: false
processed: false
completed: false
resources: "[project resources](${resources_url})"
deliverable: ${deliverable}
---

# ${title}

## Description

One paragraph summarizing the problem statement.

## Log

- [ ] ${log_timestamp} - plan the next action to move this project forward | #gtd/act/now 📅 ${today}

## Plan

Plan the steps to complete the project. Use templates for recurring projects.

## Solution

Describe what was done to get project closure acceptance.

${body}

---

- parent:: [[notes/${id}|${title}]]${ticket_line}
- us::
- psd::
