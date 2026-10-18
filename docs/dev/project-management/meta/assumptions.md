# Assumptions ledger — PRD 00029

## 1: Merge doubled changelog type sections

- N0 = 177, measured just before the edit. It matches the dispatch figure, not the PRD's 176 from 2026-10-17.
- Within each merged section, the earlier section's bullets come first, then the later duplicate's bullets in their original order.
- Kept the single blank line between a heading and its first bullet, and between sections.

## 2: Drop excluded-scope changelog bullets

- "Continuation lines" means the indented lines under a bullet, up to the next `- **` bullet. Removed no blank lines or headings.

## 3: Refile the work bullet from Added to Fixed

- "End of the sole Fixed section" means after its last bullet, which is the last line of the file. Added no blank line before the bullet, to match how the Fixed bullets are spaced.
- The blank line above the bullet's old spot in Added was a separator for that bullet alone, so it was removed with the bullet.

## 7: Record the brief-portfolio removal

- The task's "exactly one bullet matches" check means exactly one brief-portfolio bullet sits between the Removed and Fixed headings, not one match in the whole file — the historical bullets naming brief-portfolio stay as written and also match the pattern.
- The Removed section already held two bullets (the Codex retirements); the new one goes last in that section.
- The bullet text is one line, exactly as given, with no wrapping.

## 8: Cut the 0.1.0 release heading

- The release date is 2026-10-18, as the task text gives it, rather than the date of a later commit.
