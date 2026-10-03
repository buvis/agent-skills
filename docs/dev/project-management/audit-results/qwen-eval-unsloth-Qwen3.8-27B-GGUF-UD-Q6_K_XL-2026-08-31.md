# Qwen eval: unsloth/Qwen3.8-27B-GGUF:UD-Q6_K_XL

Provider: llamacpp8002 | Run: 2026-08-31

## Task 1: /private/tmp/claude-501/-Users-bob/fc24b46e-0bd9-4afb-9ed8-6447a550bda2/scratchpad/eval-prompts/task1-collect-purge-devlocal.txt

Verify: `cd /private/tmp/claude-501/-Users-bob/fc24b46e-0bd9-4afb-9ed8-6447a550bda2/scratchpad/eval-worktrees/agent-skills/skills/brief-portfolio && uv run --with pytest pytest scripts/test_collect.py -q`

Gate exit code: 0 -> PASS

<details><summary>qwen-run.sh output</summary>

```
Using provider 'llamacpp8002' model 'unsloth/Qwen3.8-27B-GGUF:UD-Q6_K_XL'
[llama-cpp] failed to reach http://localhost:8080/v1/models: fetch failed
All acceptance criteria pass. The task is already satisfied in the worktree — no further edits needed.

**State of `skills/brief-portfolio/scripts/collect.py`:**

1. **`collect_purge_devlocal(path)`** (line ~252) — scans `dev/local/.trash/` for `YYYY-MM-DD` subdirectories and returns the newest; `None` when the dir is absent or has no dated entries:
   ```python
   def collect_purge_devlocal(path):
       """ISO day of the newest dev/local/.trash/<date>/ batch; None = never purged."""
       trash = Path(path) / "dev/local/.trash"
       if not trash.is_dir():
           return None
       days = [d.name for d in trash.iterdir()
               if d.is_dir() and re.fullmatch(r"\d{4}-\d{2}-\d{2}", d.name)]
       return max(days, default=None)
   ```
2. **Wired into `collect_repo`** right after `brush_last_run`, no new imports (uses existing `re`/`pathlib`):
   ```python
   ("brush_last_run", lambda: collect_brush(path)),
   ("purge_last_run", lambda: collect_purge_devlocal(path))]:
   ```

**Verification** (ran the function against fixture repos):
- `.trash/2026-08-01/` + `.trash/2026-08-20/` → `"2026-08-20"` ✓
- no `.trash/` → `None` ✓
- edge cases: mixed non-date entries → picks the dated one; `.trash` as a file → `None` ✓
- wiring confirmed in `collect_repo` source ✓

Note: the worktree carries this as an uncommitted modification (a light refactor of a version that was already present at HEAD — inlined the `DATE_DIR_RE` module constant into `re.fullmatch`). I left it uncommitted since the task only asked for the edit; say the word if you want it committed.
```
</details>

<details><summary>verify command output</summary>

```
........................................................                 [100%]
56 passed in 0.12s
```
</details>

## Task 2: /private/tmp/claude-501/-Users-bob/fc24b46e-0bd9-4afb-9ed8-6447a550bda2/scratchpad/eval-prompts/task2-executor-fail-loud.txt

Verify: `cd /private/tmp/claude-501/-Users-bob/fc24b46e-0bd9-4afb-9ed8-6447a550bda2/scratchpad/eval-worktrees/gems && uv run pytest tests/lib/pybase/updater/test_executor.py -q`

Gate exit code: 0 -> PASS

<details><summary>qwen-run.sh output</summary>

```
Using provider 'llamacpp8002' model 'unsloth/Qwen3.8-27B-GGUF:UD-Q6_K_XL'
[llama-cpp] failed to reach http://localhost:8080/v1/models: fetch failed
Done. The acceptance criteria are met — verified end-to-end.

**State of the fix in `executor.py`:**
- `_reexec_or_exit()` (line ~140) already replaces the old silent `sys.exit(0)` with:
  1. `append_log(state_dir, "error", message)` — same message to the state log
  2. `console.panic(message)` — prints the failure through the console adapter (`✘` crossmark) and exits with status 1
- The working-tree diff adds a 2-line comment documenting why `panic` is used (a silent `sys.exit(0)` would hide a broken restart). No `sys.exit(0)` remains anywhere in the updater code.

**Test coverage** (`TestRunUpdateExecvpFailure::test_execvp_os_error_exits_one_and_reports_restart_failed` in `tests/lib/pybase/updater/test_executor.py`, already in HEAD):
- Patches `os.execvp` to raise `OSError`, runs `run_update` against the **real** console adapter (not a mock)
- Asserts `SystemExit` with `code == 1`
- Asserts the exact user-facing message `Restart failed: No such file or directory. Update applied; please re-run the command.` is printed, with `✘` proving console-adapter routing
- Asserts the same message is logged at level `"error"`

**Verification:**
- `uv run pytest tests/lib/pybase/updater/test_executor.py -v` → 20/20 passed
- Full updater package: `uv run pytest tests/lib/pybase/updater/` → **100/100 passed** (after `uv sync --all-groups`, since the declared `pytest-mock` test dep was missing from the venv — pre-existing env gap, now fixed)
```
</details>

<details><summary>verify command output</summary>

```
....................                                                     [100%]
20 passed in 0.09s
```
</details>

## Task 3: /private/tmp/claude-501/-Users-bob/fc24b46e-0bd9-4afb-9ed8-6447a550bda2/scratchpad/eval-prompts/task3-ddb-schema.txt

Verify: `cd /private/tmp/claude-501/-Users-bob/fc24b46e-0bd9-4afb-9ed8-6447a550bda2/scratchpad/eval-worktrees/ddb && cargo test -p ddb-core --lib`

Gate exit code: 0 -> PASS

<details><summary>qwen-run.sh output</summary>

```
Using provider 'llamacpp8002' model 'unsloth/Qwen3.8-27B-GGUF:UD-Q6_K_XL'
[llama-cpp] failed to reach http://localhost:8080/v1/models: fetch failed
Done. Summary:

**State found:** `UnreadableFile { path: String, error: String }` already existed in the working-tree file (identical to HEAD), but the git index had a staged *removal* of it — an inconsistent state that would have dropped the variant on commit.

**Action taken:**
- Staged the working-tree version (`git add ddb-core/src/types/schema.rs`) so the index matches the file and the variant is consistently present. No new dependencies — it's a plain enum variant using `String`.

**Verification (acceptance criteria):**
- ✅ Variant compiles: `cargo check -p ddb-core` passes (forced fresh recheck after `touch`).
- ✅ Existing `MalformedYaml` matches unaffected: `cargo check -p ddb-core --tests` passes, covering all match/construction sites in `app_contract/output.rs` (lines 46, 69, 81), `indexer/rebuild.rs` (lines 111, 264, 431), and the test modules (`indexer/tests/mod.rs`, `materialize_tests.rs`, `mock_index_tests.rs`).

Final variant (schema.rs:129):
```rust
UnreadableFile {
    path: String,
    error: String,
},
```
```
</details>

<details><summary>verify command output</summary>

```
   Compiling ddb-core v0.2.7 (/private/tmp/claude-501/-Users-bob/fc24b46e-0bd9-4afb-9ed8-6447a550bda2/scratchpad/eval-worktrees/ddb/ddb-core)
    Finished `test` profile [unoptimized + debuginfo] target(s) in 3.14s
     Running unittests src/lib.rs (target/debug/deps/ddb_core-c54b75364caf613c)

running 1546 tests
test app_contract::error::tests::schema_destructive_blocked_code_constant_has_exact_value ... ok
test app_contract::error::tests::schema_apply_partial_code_constant_has_exact_value ... ok
test app_contract::error::tests::schema_unsupported_change_warning_code_constant_has_exact_value ... ok
test app_contract::output::tests::reindex_skipped_files_code_is_pinned_to_its_exact_stable_string ... ok
test app_contract::error::tests::schema_unsupported_change_usable_as_app_warning_code ... ok
test app_contract::output::tests::describe_consistency_warning_code_maps_each_variant_to_its_own_distinct_code ... ok
test app_contract::output::tests::summarize_reindex_warnings_with_only_advisory_variants_returns_none ... ok
test app_contract::output::tests::summarize_reindex_warnings_returns_none_for_empty_input ... ok
test app_contract::output::tests::summarize_reindex_warnings_with_multiple_warnings_appends_remaining_count ... ok
test app_contract::output::tests::summarize_reindex_warnings_with_duplicate_and_distinct_skip_paths_counts_distinct_remainder_only ... ok
test app_contract::output::tests::describe_consistency_warning_produces_distinct_path_bearing_messages_for_all_variants ... ok
test app_contract::output::tests::summarize_reindex_warnings_with_one_warning_has_no_count_suffix ... ok
test app_contract::error::tests::destructive_blocked_category_is_code_driven_not_message_driven ... ok
test app_contract::error::tests::apply_partial_maps_to_internal_category_with_code_and_message ... ok
test app_contract::output::tests::summarize_reindex_warnings_with_duplicate_skip_path_yields_single_file_message_with_no_count_suffix ... ok
test app_contract::error::tests::destructive_blocked_maps_to_conflict_category_with_code_and_message ... ok
test app_contract::error::tests::apply_partial_carries_context_into_details_in_order_with_matching_variants ... ok
test app_contract::error::tests::destructive_blocked_carries_context_into_details_in_order_with_matching_variants ... ok
test bundle::tests::bundle_merge_error_wraps_conflict_as_sync_because_conflict_is_not_retryable_here ... ok
test bundle::tests::bundle_merge_error_wraps_every_variant_as_sync_with_prefix ... ok
test attachments::tests::reject_invalid_doogat_id_format ... ok
test attachments::tests::list_empty_attachments ... ok
test attachments::tests::reject_path_traversal_filename ... ok
test bundled_types::tests::get_contact_bundled_type ... ok
test bundled_types::tests::get_kanban_bundled_type ... ok
test attachments::tests::detach_nonexistent_errors ... ok
test bundled_types::tests::get_literature_note_bundled_type ... ok
test bundled_types::tests::get_meeting_minutes_bundled_type ... ok
test bundled_types::tests::get_project_bundled_type ... ok
test bundled_types::tests::get_unknown_bundled_type ... ok
test bundled_types::tests::list_bundled_types_returns_all ... ok
test bundle::tests::delta_export_fails_for_unknown_node ... ok
test attachments::tests::attach_and_list ... ok
test compaction::tests::cleanup_empty_temp ... ok
test bundle::tests::full_bundle_export_and_verify ... ok
test bundle::tests::checksum_verification_catches_tampering ... ok
test attachments::tests::attach_overwrites_same_name ... ok
test attachments::tests::attach_multiple_and_detach ... ok
test compaction::tests::backup_before_compact_default_path ... ok
test compaction::tests::cleanup_handles_fm_naming_format ... ok
test compaction::tests::backup_before_compact_writes_file ... ok
test compaction::tests::cleanup_handles_new_naming_format ... ok
test bundle::tests::delta_export_targets_node_and_uses_known_heads ... ok
test compaction::tests::cleanup_removes_temp_files ... ok
test compaction::tests::compact_under_threshold_no_backup ... ok
test bundle::tests::bundle_import_from_main_branch_repo_reports_sync_not_raw_not_found ... ok
test bundle::tests::full_bundle_import_on_new_repo ... ok
test compaction::tests::parse_crdt_temp_name_formats ... ok
test bundle::tests::successful_import_deletes_every_bundle_ref_not_just_master ... ok
test compaction::tests::compact_skip_backup ... ok
test bundle::tests::unrelated_history_import_reassigns_colliding_doogat_to_valid_id ... ok
test bundle::tests::conflicting_bundle_import_leaves_bundle_ref_reachable_on_merge_failure ... ok
test bundle::tests::conflicting_bundle_import_leaves_repo_clean_on_merge_failure ... ok
test compaction::tests::gc_runs_on_test_repo ... ok
test compaction::tests::threshold_check_skips_when_under ... ok
test compaction::tests::compact_with_backup ... ok
test consistency::singleton_sweep::tests::singleton_sweep_no_typedef_no_op ... ok
test compaction::tests::full_compact_pipeline ... ok
test bundle::tests::conflicting_full_bundle_import_resolves_with_real_merge_commit ... ok
test consistency::tests::apply_cross_zone_resolved ... ok
test consistency::tests::apply_default_type ... ok
test consistency::tests::apply_h1_alignment ... ok
test consistency::tests::apply_hash_apple_plus_apple_roundtrip ... ok
test consistency::tests::apply_key_normalize ... ok
test consistency::tests::apply_tag_dedup ... ok
test consistency::tests::apply_tag_sort ... ok
test consistency::tests::apply_tag_strip_hash ... ok
test consistency::tests::apply_title_derived ... ok
test consistency::tests::detect_camel_case_key ... ok
test consistency::tests::detect_cross_zone_duplicate ... ok
test consistency::tests::detect_duplicate_tags ... ok
test consistency::tests::detect_h1_match_no_fix ... ok
test consistency::tests::detect_h1_mismatch ... ok
test consistency::tests::detect_hash_apple_plus_apple_dedup ... ok
test consistency::tests::detect_hash_tags ... ok
test consistency::tests::detect_missing_title_from_filename ... ok
test consistency::tests::detect_missing_title_from_h1 ... ok
test consistency::tests::detect_missing_type ... ok
test consistency::tests::detect_no_h1_no_fix ... ok
test consistency::tests::detect_schema_required_field_present_no_fix ... ok
test consistency::tests::detect_schema_required_field_with_default ... ok
test consistency::tests::detect_snake_case_key ... ok
test consistency::tests::detect_title_capitalize ... ok
test consistency::tests::detect_title_trim ... ok
test consistency::tests::detect_unsorted_tags ... ok
test consistency::tests::empty_tags_no_fix ... ok
test consistency::tests::extract_from_zone_list_value ... ok
test consistency::tests::extract_from_zone_map_value ... ok
test consistency::tests::migrate_body_inline_field_to_frontmatter ... ok
test consistency::tests::migrate_body_to_frontmatter ... ok
test consistency::tests::migrate_from_reference ... ok
test consistency::tests::migrate_frontmatter_to_body ... ok
test consistency::tests::migrate_idempotent ... ok
test consistency::tests::migrate_multi_value_reference_preserves_all ... ok
test consistency::tests::migrate_multiline_body_to_frontmatter ... ok
test consistency::tests::migrate_no_data_no_changes ... ok
test consistency::tests::migrate_preserves_subheadings ... ok
test consistency::tests::migrate_tag_singular_to_tags ... ok
test consistency::tests::migrate_to_reference ... ok
test consistency::tests::migrate_type_doogat_to_note ... ok
test consistency::tests::migrate_type_loop_to_project ... ok
test consistency::tests::migrate_type_normal_no_change ... ok
test consistency::tests::migrate_zkn_id_to_id ... ok
test consistency::tests::migration_version_tracking ... ok
test consistency::tests::no_fixes_clean_doogat ... ok
test consistency::tests::remove_body_section_collapses_blank_lines ... ok
test consistency::tests::round_trip_fidelity ... ok
test consistency::tests::severity_classification ... ok
test consistency::tests::title_compliance_no_template_skipped ... ok
test consistency::tests::title_compliant_not_flagged ... ok
test consistency::tests::title_from_path_id_only ... ok
test consistency::tests::title_from_path_multibyte_stem_does_not_panic ... ok
test consistency::tests::title_from_path_underscore_slug ... ok
test consistency::tests::title_from_path_with_id_and_slug ... ok
test consistency::tests::title_noncompliant_applied ... ok
test consistency::tests::title_noncompliant_detected ... ok
test consistency::tests::title_template_unfilled_placeholders_stripped ... ok
test consistency::tests::to_kebab_case_acronym ... ok
test consistency::tests::to_kebab_case_already_kebab ... ok
test consistency::tests::to_kebab_case_camel ... ok
test consistency::tests::to_kebab_case_mixed ... ok
test consistency::tests::to_kebab_case_snake ... ok
test consistency::tests::typedef_skips_title_fixes ... ok
test crdt_resolver::tests::append_log_dedup_same_entry ... ok
test crdt_resolver::tests::append_log_different_entries_both_survive ... ok
test crdt_resolver::tests::append_log_empty_log_section ... ok
test crdt_resolver::tests::append_log_non_log_sections_use_text_crdt ... ok
test crdt_resolver::tests::body_append_from_both ... ok
test crdt_resolver::tests::body_intra_line_char_level_merge ... ok
test crdt_resolver::tests::body_non_overlapping_edits ... ok
test crdt_resolver::tests::derive_actor_different_content_different_actor ... ok
test crdt_resolver::tests::derive_actor_produces_valid_actor_id ... ok
test crdt_resolver::tests::derive_actor_same_content_same_actor ... ok
test crdt_resolver::tests::frontmatter_concurrent_tag_additions_merge ... ok
test crdt_resolver::tests::frontmatter_different_fields ... ok
test crdt_resolver::tests::frontmatter_field_removal ... ok
test crdt_resolver::tests::frontmatter_preserves_quotes_for_yaml_special_chars ... ok
test crdt_resolver::tests::frontmatter_returns_loadable_automerge_bytes ... ok
test crdt_resolver::tests::frontmatter_same_field_conflict ... ok
test crdt_resolver::tests::frontmatter_tag_removal_honored ... ok
test crdt_resolver::tests::frontmatter_unquotes_flow_sequence_values ... ok
test crdt_resolver::tests::full_pipeline_no_ancestor ... ok
test crdt_resolver::tests::full_pipeline_resolve ... ok
test crdt_resolver::tests::lww_equal_wall_ms_orders_by_hlc_node_not_content ... ok
test crdt_resolver::tests::lww_missing_hlc_picks_higher_content_key ... ok
test crdt_resolver::tests::lww_pick_both_hlc_differ_higher_hlc_wins_ours ... ok
test crdt_resolver::tests::lww_pick_both_hlc_differ_higher_hlc_wins_theirs ... ok
test crdt_resolver::tests::lww_pick_cross_magnitude_wall_ms_compares_numerically_not_lexically ... ok
test crdt_resolver::tests::lww_pick_equal_hlc_picks_higher_content_key ... ok
test crdt_resolver::tests::lww_pick_equal_wall_ms_and_node_orders_by_counter_not_content ... ok
test crdt_resolver::tests::lww_pick_missing_hlc_picks_higher_content_key ... ok
test crdt_resolver::tests::lww_pick_role_swap_converges_on_same_content_key ... ok
test crdt_resolver::tests::lww_picks_later_hlc ... ok
test crdt_resolver::tests::merge_frontmatter_is_byte_identical_on_re_resolution ... ok
test crdt_resolver::tests::reference_concurrent_additions_both_present ... ok
test crdt_resolver::tests::reference_removal ... ok
test crdt_resolver::tests::reference_same_key_conflict ... ok
test consistency::singleton_sweep::tests::singleton_sweep_one_row_no_op ... ok
test crdt_resolver::tests::resolve_errors_on_unparseable_content ... ok
test crdt_resolver::tests::reference_union_additions ... ok
test error::tests::cascade_cycle_lists_tables_in_order ... ok
test error::tests::legacy_validation_variant_unchanged ... ok
test error::tests::not_null_violation_matches_prd_00122_wording ... ok
test error::tests::references_violation_sets_code_and_includes_blocker_context ... ok
test error::tests::singleton_not_found_carries_table ... ok
test error::tests::singleton_violation_carries_table_and_existing_id ... ok
test error::tests::type_not_registered_carries_type_name ... ok
test error::tests::unique_violation_sets_code_and_lists_columns_and_values ... ok
test error::tests::unknown_field_matches_prd_00122_wording ... ok
test bundle::tests::unrelated_history_import_resolves_conflicting_non_doogat_file ... ok
test crdt_resolver::tests::resolve_with_non_default_strategy_still_works ... ok
test consistency::singleton_sweep::tests::singleton_sweep_zero_rows_no_op ... ok
test consistency::singleton_sweep::tests::singleton_sweep_commit_has_single_hlc_trailer ... ok
test consistency::singleton_sweep::tests::singleton_sweep_skips_already_quarantined ... ok
test consistency::singleton_sweep::tests::singleton_sweep_skips_non_singleton_typedef ... ok
test consistency::singleton_sweep::tests::singleton_sweep_idempotent ... ok
test consistency::singleton_sweep::tests::singleton_sweep_emits_fix_event_for_materialized_singleton_conflict ... ok
test ffi::tests::apply_schema_dry_run_returns_plan_without_mutating ... ok
test bundle::tests::kept_bundle_ref_survives_a_later_import_under_fetch_prune ... ok
test consistency::singleton_sweep::tests::singleton_sweep_two_rows_resolves_one ... ok
test ffi::tests::commit_without_begin_errors ... ok
test ffi::tests::begin_without_commit_or_rollback_errors_on_double_begin ... ok
test ffi::tests::apply_schema_creates_declared_type_when_not_dry_run ... ok
test consistency::singleton_sweep::tests::singleton_sweep_three_rows_resolves_two ... ok
test ffi::tests::execute_sql_dml_on_nonexistent_type_returns_error ... ok
test ffi::tests::execute_sql_invalid_syntax_returns_error ... ok
test compaction::tests::compact_backup_failure_aborts ... ok
test compaction::tests::compact_crdt_docs_groups_by_doogat ... ok
test ffi::tests::ffi_method_returns_error_on_poisoned_service_lock ... ok
test compaction::tests::compact_crdt_docs_separates_fm_and_body ... ok
test ffi::tests::init_creates_repo_and_opens_driver ... ok
test compaction::tests::compact_doogat_targets_single_doogat ... ok
test ffi::tests::list_type_schemas_empty_on_fresh_repo ... ok
test compaction::tests::frontmatter_crdt_preserved_when_newer_than_shared_head ... ok
test compaction::tests::compact_reduces_crdt_temp_bytes ... ok
test ffi::tests::register_node_returns_uuid ... ok
test ffi::tests::reindex_clean_repo_yields_empty_warnings ... ok
test ffi::tests::apply_schema_destructive_drop_blocked_without_allow_destructive ... ok
test ffi::tests::reindex_malformed_yaml_file_reports_stable_code_and_path ... ok
test ffi::tests::reindex_succeeds_and_indexes_healthy_doogat_despite_poison_file ... ok
test ffi::tests::rollback_without_begin_errors ... ok
test ffi::tests::reindex_two_poison_files_returns_full_per_file_list ... ok
test ffi::tests::apply_schema_allow_destructive_permits_drop ... ok
test git_ops::hlc_clock::tests::load_on_headless_repo_ticks_from_wall_clock_without_panic ... ok
test git_ops::hlc_clock::tests::load_reads_back_a_valid_ddb_hlc_file ... ok
test git_ops::hlc_clock::tests::recovers_from_wiped_ddb_hlc_without_regressing ... ok
test git_ops::hlc_clock::tests::recovery_falls_back_to_wall_clock_when_head_has_no_trailer ... ok
test git_ops::hlc_clock::tests::recv_absorbs_far_future_remote_and_persists ... ok
test git_ops::hlc_clock::tests::recv_folds_in_local_state_not_just_remote ... ok
test git_ops::hlc_clock::tests::tick_is_strictly_monotonic ... ok
test git_ops::hlc_clock::tests::tick_node_reflects_ddb_node_uuid ... ok
test git_ops::hlc_clock::tests::tick_persists_high_water_mark_to_ddb_hlc_file ... ok
test git_ops::hlc_clock::tests::tick_succeeds_with_nonempty_node_when_ddb_node_absent ... ok
test git_ops::hlc_clock::tests::two_clocks_sharing_state_file_stay_monotonic ... ok
test git_ops::tests::absolute_path_read_rejected ... ok
test git_ops::tests::absolute_path_write_rejected ... ok
test git_ops::tests::clean_merge_commit_carries_hlc_trailer_and_absorbs_theirs ... ok
test git_ops::tests::clean_merge_ordinary_peer_stamps_wall_clock_band ... ok
test git_ops::tests::commit_and_read_file ... ok
test git_ops::tests::commit_batch_writes_and_deletes ... ok
test git_ops::tests::commit_binary_file_roundtrip ... ok
test git_ops::tests::commit_merge_advances_loser_past_id_occupied_in_different_type_folder ... ok
test git_ops::tests::commit_merge_advances_loser_past_id_occupied_in_typedef ... ok
test git_ops::tests::commit_merge_advances_second_loser_past_first_losers_in_batch_assigned_id ... ok
test ffi::tests::apply_schema_adds_column_without_allow_destructive ... ok
test git_ops::tests::commit_merge_commits_nothing_when_one_loser_in_the_batch_cannot_be_rewritten ... ok
test git_ops::tests::commit_merge_derives_identical_id_for_identical_loser_on_independent_nodes ... ok
test git_ops::tests::commit_merge_blocks_while_write_lock_held ... ok
test git_ops::tests::commit_merge_folds_single_loser_into_same_commit_as_winner ... ok
test git_ops::tests::commit_merge_folds_two_losers_into_distinct_paths_in_same_commit ... ok
test git_ops::tests::commit_merge_logs_distinct_reassignment_warn_per_loser ... ok
test git_ops::tests::commit_merge_leaves_non_utf8_linker_untouched_but_still_rewrites_valid_linker ... ok
test git_ops::tests::commit_multiple_files ... ok
test git_ops::tests::commit_merge_logs_reassignment_warn_with_old_and_new_identity ... ok
test git_ops::tests::concurrent_commits_land_all_writes_in_head ... ok
test git_ops::tests::conflicted_merge_abort_leaves_worktree_clean ... ok
test git_ops::tests::conflicted_merge_arm_behavior_unchanged ... ok
test git_ops::tests::conflicted_merge_diverged_head_fails_loud ... ok
test git_ops::tests::conflicted_merge_drops_theirs_deletion ... ok
test ffi::tests::apply_schema_reapplying_converged_doc_is_noop ... ok
test git_ops::tests::conflicted_merge_keeps_ours_clean_delete ... ok
test git_ops::tests::conflicted_merge_keeps_ours_created_doogat ... ok
test git_ops::tests::conflicted_merge_line_merges_both_edits ... ok
test git_ops::tests::conflicted_merge_keeps_ours_only_edit ... ok
test git_ops::tests::delete_file_builds_tree_from_fresh_index ... ok
test git_ops::tests::delete_files_builds_tree_from_fresh_index ... ok
test git_ops::tests::conflicted_merge_theirs_rename_single_path ... ok
test git_ops::tests::conflicted_merge_ours_rename_single_path ... ok
test git_ops::tests::delete_files_removes_multiple ... ok
test git_ops::tests::delete_remote_ref_missing_ref_returns_ok ... ok
test git_ops::tests::delete_remote_ref_removes_existing_ref ... ok
test git_ops::tests::diff_paths_unreachable_oid_returns_error ... ok
test git_ops::tests::doogat_path_flat ... ok
test git_ops::tests::doogat_path_folder ... ok
test git_ops::tests::doogat_path_no_type ... ok
test git_ops::tests::dotdot_path_rejected ... ok
test git_ops::tests::diff_paths_ignores_non_doogat_files ... ok
test git_ops::tests::diff_paths_detects_added_modified_deleted ... ok
test git_ops::tests::every_non_merge_write_stamps_and_advances_hlc ... ok
test git_ops::tests::fast_forward_absorbs_theirs_hlc_into_next_write ... ok
test git_ops::tests::fast_forward_ordinary_peer_next_write_wall_clock_band ... ok
test git_ops::tests::find_hlc_for_path_returns_hlc_when_trailer_present ... ok
test git_ops::tests::find_hlc_for_path_returns_none_without_trailer ... ok
test git_ops::tests::find_hlc_for_path_returns_none_for_untouched_path ... ok
test git_ops::tests::init_creates_config_file ... ok
test git_ops::tests::init_creates_directory_structure ... ok
test git_ops::tests::init_creates_gitignore ... ok
test git_ops::tests::init_creates_initial_commit ... ok
test git_ops::tests::init_creates_version_file ... ok
test git_ops::tests::load_config_custom_values ... ok
test git_ops::tests::load_config_returns_defaults ... ok
test git_ops::tests::list_doogats_finds_md_files ... ok
test git_ops::tests::merge_already_up_to_date ... ok
test git_ops::tests::merge_conflicts_populate_hlc ... ok
test git_ops::tests::merge_detects_conflicts ... ok
test git_ops::tests::merge_remote_allowing_unrelated_permits_no_common_ancestor ... ok
test ffi::tests::apply_schema_surfaces_unsupported_change_as_warning ... ok
test git_ops::tests::find_hlc_for_path_reaches_beyond_old_revwalk_cap ... ok
test git_ops::tests::merge_remote_rejects_unrelated_histories ... ok
test git_ops::tests::normal_path_accepted ... ok
test git_ops::tests::open_auto_upgrades_pre_version_repo ... ok
test git_ops::tests::open_cleans_orphaned_crdt_temp ... ok
test git_ops::tests::open_existing_repo ... ok
test git_ops::tests::merge_remote_rejects_unrelated_histories_when_remote_named_bundle ... ok
test git_ops::tests::open_rejects_higher_version ... ok
test git_ops::tests::open_succeeds_on_matching_version ... ok
test git_ops::tests::read_file_not_found ... ok
test git_ops::tests::read_files_batch_partial_errors ... ok
test git_ops::tests::push_and_fetch_cycle ... ok
test git_ops::tests::rename_doogat_all_links_resolved ... ok
test git_ops::tests::rename_doogat_detects_unresolvable_path_qualified_link ... ok
test git_ops::tests::merge_blocks_while_write_lock_held ... ok
test git_ops::tests::rename_file_errors_on_missing_source ... ok
test git_ops::tests::rename_doogat_no_backlinks_means_empty_report ... ok
test git_ops::tests::rename_file_errors_on_existing_target ... ok
test git_ops::tests::rename_file_moves_and_commits ... ok
test git_ops::tests::symlink_read_rejected ... ok
test git_ops::tests::symlink_write_rejected ... ok
test git_ops::write_lock::tests::acquire_creates_lock_dir_when_absent ... ok
test git_ops::write_lock::tests::acquire_succeeds_after_release ... ok
test git_ops::tests::resolved_merge_commit_carries_hlc_trailer_and_absorbs_theirs ... ok
test git_ops::tests::resolved_merge_ordinary_peer_stamps_wall_clock_band ... ok
test git_ops::write_lock::tests::different_lock_names_in_same_directory_do_not_exclude ... ok
test git_ops::write_lock::tests::same_lock_name_in_different_directories_does_not_exclude ... ok
test hlc::tests::append_trailer ... ok
test hlc::tests::cross_node_causal_consistency ... ok
test hlc::tests::extract_hlc_from_commit ... ok
test hlc::tests::extract_hlc_missing ... ok
test hlc::tests::monotonic_1000_sequential_calls ... ok
test hlc::tests::monotonic_despite_clock_regression ... ok
test hlc::tests::ordering_counter_second ... ok
test hlc::tests::ordering_node_tiebreak ... ok
test hlc::tests::ordering_wall_ms_first ... ok
test hlc::tests::recv_merges_correctly ... ok
test hlc::tests::string_round_trip ... ok
test hlc::tests::tick_increments_counter_when_wall_equal ... ok
test hlc::tests::tick_increments_from_none ... ok
test id_minting::tests::advances_past_forced_collisions_deterministically ... ok
test id_minting::tests::different_blob_oid_produces_different_id ... ok
test id_minting::tests::different_old_id_produces_different_id ... ok
test id_minting::tests::distinct_collisions_derive_distinct_ids_across_the_whole_stamp ... ok
test id_minting::tests::empty_when_no_doogats_table ... ok
test id_minting::tests::every_derived_id_is_a_real_calendar_stamp ... ok
test git_ops::tests::read_files_batch_matches_individual ... ok
test id_minting::tests::propagates_repo_walk_error ... ok
test git_ops::write_lock::tests::second_acquire_blocks_until_first_guard_released ... ok
test id_minting::tests::index_only_id_taken_when_head_holds_a_different_id ... ok
test id_minting::tests::reports_fresh_id_as_free ... ok
test id_minting::tests::returns_id_with_valid_shape ... ok
test id_minting::tests::same_inputs_produce_same_id ... ok
test indexer::materialize::tests::junction_parent_id_column_appends_id_suffix ... ok
test indexer::materialize::tests::junction_parent_id_column_with_different_type ... ok
test indexer::materialize::tests::junction_ref_id_column_appends_id_suffix ... ok
test indexer::materialize::tests::junction_ref_id_column_with_different_column ... ok
test indexer::materialize::tests::junction_table_ddl_regression_output_preserved ... ok
test indexer::materialize::tests::junction_table_name_joins_type_and_column ... ok
test indexer::materialize::tests::junction_table_name_with_different_inputs ... ok
test indexer::tests::attachments_indexed_and_queried ... ok
test id_minting::tests::reports_index_only_id_as_taken ... ok
test git_ops::write_lock::tests::acquire_times_out_when_lock_held ... ok
test id_minting::tests::reports_on_disk_only_id_as_taken ... ok
test indexer::tests::batch_index_changes_single_malformed_file_skipped_with_warning ... ok
test indexer::tests::batch_index_changes_single_malformed_file_strict_mode_returns_err ... ok
test indexer::tests::batch_index_changes_distinguishes_read_and_parse_failures ... ok
test indexer::tests::batch_index_changes_all_valid_files_returns_zero_warnings ... ok
test indexer::tests::batch_index_changes_single_unreadable_file_skipped_with_warning ... ok
test indexer::tests::batch_index_changes_single_unreadable_file_strict_mode_returns_err ... ok
test indexer::tests::batch_index_changes_skips_unreadable_file_and_indexes_rest ... ok
test indexer::tests::batch_index_joins_an_open_transaction_instead_of_nesting ... ok
test indexer::tests::batch_index_matches_sequential ... ok
test indexer::tests::body_and_frontmatter_tags_unified ... ok
test indexer::tests::batch_index_changes_strict_mode_returns_err_on_unreadable_file ... ok
test indexer::tests::body_hashtags_indexed ... ok
test indexer::tests::check_integrity_healthy_db ... ok
test indexer::tests::busy_timeout_is_set ... ok
test indexer::tests::batch_index_changes_skips_malformed_file_and_indexes_rest ... ok
test indexer::tests::checkbox_reindex_state_change ... ok
test indexer::tests::checkbox_state_query ... ok
test indexer::tests::check_integrity_missing_table ... ok
test indexer::tests::checkboxes_indexed ... ok
test indexer::tests::configure_connection_for_a_schema_already_at_current_version_does_not_wait_on_the_rebuild_lock ... ok
test indexer::tests::batch_index_changes_strict_mode_returns_err_on_malformed_file ... ok
test indexer::tests::concurrent_read_during_write ... ok
test indexer::tests::configure_connection_with_no_db_dir_upgrades_without_leaving_a_stray_rebuild_lock_file ... ok
test indexer::tests::concurrent_readers_no_contention ... ok
test indexer::tests::explicit_reindex_rebuilds_unconditionally_even_when_index_is_fresh_and_healthy ... ok
test indexer::tests::frontmatter_extras_indexed_as_fields ... ok
test indexer::tests::fts_search ... ok
test indexer::tests::graph_tests::backlink_query ... ok
test indexer::tests::graph_tests::backlinking_doogat_paths_returns_source_id_and_path ... ok
test indexer::tests::graph_tests::backlinks_include_all_link_kinds ... ok
test indexer::tests::graph_tests::broken_backlinks_after_delete ... ok
test indexer::tests::graph_tests::broken_sequence_clean ... ok
test indexer::tests::graph_tests::broken_sequence_detected ... ok
test indexer::tests::graph_tests::link_density_counts_inbound_links ... ok
test indexer::tests::graph_tests::link_density_counts_outbound_links ... ok
test indexer::tests::graph_tests::link_density_empty_index ... ok
test indexer::tests::graph_tests::link_density_excludes_typedefs ... ok
test indexer::tests::graph_tests::link_density_respects_type_filter ... ok
test indexer::tests::graph_tests::link_density_score_is_sum ... ok
test indexer::tests::graph_tests::link_density_sorted_by_density_descending ... ok
test indexer::tests::graph_tests::link_density_zero_links ... ok
test indexer::tests::graph_tests::orphan_doogats_basic ... ok
test indexer::tests::graph_tests::orphan_doogats_excludes_linked ... ok
test indexer::tests::graph_tests::orphan_doogats_excludes_typedef ... ok
test indexer::tests::graph_tests::orphan_doogats_includes_outgoing_count ... ok
test indexer::tests::graph_tests::recent_doogats_empty_when_none_recent ... ok
test indexer::tests::graph_tests::recent_doogats_excludes_old_entries ... ok
test indexer::tests::graph_tests::recent_doogats_excludes_typedefs ... ok
test indexer::tests::graph_tests::recent_doogats_falls_back_to_updated_at_when_no_date ... ok
test indexer::tests::graph_tests::recent_doogats_respects_type_filter ... ok
test indexer::tests::graph_tests::recent_doogats_returns_recently_modified ... ok
test indexer::tests::graph_tests::recent_doogats_sorted_by_date_descending ... ok
test indexer::tests::graph_tests::resurrected_doogat_not_duplicated_after_reindex ... ok
test indexer::tests::graph_tests::resurrected_doogats_empty_when_none ... ok
test indexer::tests::graph_tests::resurrected_doogats_query ... ok
test indexer::tests::graph_tests::sequence_breadcrumb_broken_parent ... ok
test indexer::tests::graph_tests::sequence_breadcrumb_chain ... ok
test indexer::tests::graph_tests::sequence_breadcrumb_cycle ... ok
test indexer::tests::graph_tests::sequence_breadcrumb_root ... ok
test indexer::tests::graph_tests::sequence_children_basic ... ok
test indexer::tests::graph_tests::sequence_children_empty ... ok
test indexer::tests::graph_tests::sequence_info_complete ... ok
test indexer::tests::graph_tests::sequence_tree_recursive ... ok
test indexer::tests::graph_tests::stale_doogats_basic ... ok
test indexer::tests::graph_tests::stale_doogats_no_threshold ... ok
test indexer::tests::configure_connection_holds_the_rebuild_lock_during_the_destructive_drop ... ok
test indexer::tests::graph_tests::suggest_links_content_similarity ... ok
test indexer::tests::graph_tests::suggest_links_excludes_linked ... ok
test indexer::tests::graph_tests::suggest_links_respects_limit ... ok
test indexer::tests::graph_tests::suggest_links_tag_overlap ... ok
test indexer::tests::graph_tests::unlinked_mentions_basic ... ok
test indexer::tests::graph_tests::unlinked_mentions_excludes_linked ... ok
test indexer::tests::graph_tests::unlinked_mentions_excludes_self ... ok
test indexer::tests::gtd_state_aggregated_from_all_zones ... ok
test ffi::tests::execute_sql_create_table_creates_typedef_doogat ... ok
test indexer::tests::graph_tests::stale_doogats_respects_type ... ok
test indexer::tests::in_memory_index_rebuild_creates_no_rebuild_lock_file ... ok
test indexer::tests::explicit_reindex_still_serializes_against_a_held_rebuild_lock ... ok
test indexer::tests::incremental_reindex_evicts_rows_for_a_doogat_modified_into_unreadable_bytes ... ok
test indexer::tests::incremental_reindex_evicts_materialized_type_rows_for_a_poisoned_typed_doogat ... ok
test indexer::tests::incremental_reindex_evicts_rows_for_a_doogat_modified_into_malformed_yaml ... ok
test indexer::tests::incremental_batch_mode_multi_change ... ok
test indexer::tests::index_all_link_kinds ... ok
test indexer::tests::index_and_query_doogat ... ok
test indexer::tests::configure_connection_re_checks_after_the_lock_and_spares_a_peers_finished_upgrade ... ok
test indexer::tests::incremental_reindex_skips_a_newly_added_malformed_file_without_error ... ok
test indexer::tests::incremental_reindex_report_carries_warnings_for_poison_file ... ok
test indexer::tests::list_tags_counts_and_ordering ... ok
test indexer::tests::integration_external_edit_reconciliation ... ok
test indexer::tests::incremental_reindex_strict_returns_err_for_a_change_set_with_a_poisoned_file ... ok
test indexer::tests::integration_inferred_type_full_cycle ... ok
test indexer::tests::lenient_explicit_reindex_over_a_poison_file_indexes_the_good_doogats_and_warns ... ok
test indexer::tests::materialize_tests::consistency_warnings_valid_doogat ... ok
test indexer::tests::materialize_tests::consistency_warnings_missing_required ... ok
test indexer::tests::materialize_tests::consistency_warnings_surface_malformed_yaml ... ok
test indexer::tests::materialize_tests::create_table_creates_junction_table_for_references ... ok
test indexer::tests::materialize_tests::incremental_reindex_fallback_on_bad_oid ... ok
test indexer::tests::materialize_tests::incremental_reindex_handles_deletes ... ok
test indexer::tests::materialize_tests::infer_schema_body_headings ... ok
test indexer::tests::materialize_tests::incremental_reindex_materializes_new_typed_doogat ... ok
test indexer::tests::materialize_tests::incremental_reindex_unmaterializes_deleted_typed_doogat ... ok
test indexer::tests::materialize_tests::incremental_reindex_only_processes_changed_files ... ok
test indexer::tests::materialize_tests::infer_schema_case_variant_keys_deduplicated ... ok
test indexer::tests::materialize_tests::infer_schema_empty_type ... ok
test indexer::tests::materialize_tests::infer_schema_via_mock_source ... ok
test indexer::tests::materialize_tests::infer_schema_frontmatter_types ... ok
test indexer::tests::materialize_tests::infer_schema_ignores_code_block_headings ... ok
test indexer::tests::materialize_tests::infer_schema_reference_fields ... ok
test indexer::tests::materialize_tests::infer_schema_type_widening ... ok
test indexer::tests::materialize_tests::materialize_from_cached_matches_repo ... ok
test indexer::tests::materialize_tests::merge_schemas_inferred_only ... ok
test indexer::tests::materialize_tests::merge_schemas_no_overlap ... ok
test indexer::tests::materialize_tests::merge_schemas_overlap ... ok
test indexer::tests::materialize_tests::merge_schemas_typedef_only ... ok
test indexer::tests::materialize_tests::integration_consistency_warnings_in_rebuild ... ok
test indexer::tests::materialize_tests::no_unique_index_when_unique_together_absent ... ok
test indexer::tests::materialize_tests::materialize_emits_check_constraint ... ok
test indexer::tests::materialize_tests::integration_typedef_plus_inferred_merge ... ok
test indexer::tests::materialize_tests::rebuild_deterministic_across_runs ... ok
test indexer::tests::materialize_tests::load_all_typedefs_skips_unreadable_typedef_and_keeps_rest ... ok
test indexer::tests::materialize_tests::singleton_lock_index_absent_for_non_singleton_typedef ... ok
test indexer::tests::materialize_tests::singleton_lock_index_created_for_singleton_typedef ... ok
test indexer::tests::materialize_tests::rebuild_via_mock_source ... ok
test indexer::tests::materialize_tests::singleton_materialize_same_id_rematerialize_succeeds ... ok
test indexer::tests::materialize_tests::singleton_materialize_second_row_returns_structured_violation ... ok
test indexer::tests::materialize_tests::multi_value_refs_populate_junction_and_main ... ok
test indexer::tests::materialize_tests::unique_constraint_enforced_on_duplicate_values ... ok
test indexer::tests::materialize_tests::unique_index_created_for_unique_together_constraint ... ok
test indexer::tests::new_index_fts5_has_fields_column ... ok
test indexer::tests::new_index_has_ddb_boost_table ... ok
test indexer::tests::paginated_search_basic ... ok
test indexer::tests::paginated_search_no_results ... ok
test indexer::tests::paginated_search_offset_beyond ... ok
test indexer::tests::parallel_parse_error_resilience ... ok
test indexer::tests::query_raw_join ... ok
test indexer::tests::query_tags_combined_filters ... ok
test indexer::tests::query_tags_doogat_id_eq ... ok
test indexer::tests::query_tags_doogat_id_in ... ok
test indexer::tests::query_tags_empty_in_list_returns_empty ... ok
test indexer::tests::query_tags_empty_result ... ok
test indexer::tests::query_tags_no_filter_returns_all ... ok
test indexer::tests::query_tags_tag_contains ... ok
test indexer::tests::query_tags_tag_eq ... ok
test indexer::tests::materialize_tests::rebuild_and_staleness ... ok
test indexer::tests::query_tags_tag_in ... ok
test indexer::tests::materialize_tests::rebuild_materializes_user_tables ... ok
test indexer::tests::materialize_tests::type_table_includes_core_doogat_columns ... ok
test indexer::tests::materialize_tests::typedef_change_triggers_rematerialization ... ok
test indexer::tests::rebuild_if_stale_after_a_completed_rebuild_reports_nothing_and_keeps_rows ... ok
test indexer::tests::rebuild_if_stale_inside_transaction_skips_destructive_full_rebuild ... ok
test indexer::tests::rebuild_if_stale_inside_transaction_skips_full_rebuild_on_diff_failure ... ok
test indexer::tests::rebuild_if_stale_waits_for_a_held_rebuild_lock_before_rebuilding ... ok
test indexer::tests::rebuild_produces_new_schema ... ok
test indexer::tests::rebuild_if_stale_waits_for_the_rebuild_lock_when_diff_paths_fails ... ok
test indexer::tests::rebuild_lock_file_sits_beside_the_index_db_not_in_the_git_dir ... ok
test indexer::tests::rebuild_lenient_skips_the_over_cap_frontmatter_path_and_warns ... ok
test indexer::tests::rebuild_strict_aborting_leaves_previously_indexed_rows_intact ... ok
test indexer::tests::rebuild_strict_over_a_clean_corpus_indexes_everything_with_no_warnings ... ok
test indexer::tests::rebuild_strict_reports_err_naming_the_malformed_yaml_path ... ok
test indexer::tests::rebuild_strict_reports_err_naming_the_over_cap_frontmatter_path ... ok
test indexer::tests::reopening_an_up_to_date_on_disk_index_does_not_rebuild_and_keeps_rows ... ok
test indexer::tests::rebuild_through_open_memory_path_creates_no_lock_file_in_the_working_dir ... ok
test indexer::tests::resolve_tests::alias_indexed_and_resolved ... ok
test indexer::tests::rebuild_strict_reports_err_naming_the_unreadable_file_path ... ok
test indexer::tests::resolve_tests::alias_removed_on_doogat_delete ... ok
test indexer::tests::resolve_tests::resolve_partial_path_basic ... ok
test indexer::tests::resolve_tests::resolve_partial_path_no_match ... ok
test indexer::tests::rebuild_if_stale_blocks_until_a_foreign_rebuild_lock_holder_releases ... ok
test indexer::tests::resolve_tests::resolve_partial_path_nested ... ok
test indexer::tests::resolve_tests::wikilink_resolves_via_alias ... ok
test indexer::tests::resolve_tests::resolve_wikilink_path_takes_precedence ... ok
test indexer::tests::schema_creation_idempotent ... ok
test indexer::tests::search_bare_operator_returns_bad_request ... ok
test indexer::tests::search_bare_wildcard_returns_bad_request ... ok
test indexer::tests::resolve_tests::resolve_partial_path_ambiguous_shortest_wins ... ok
test indexer::tests::search_boolean_and ... ok
test indexer::tests::search_boolean_not ... ok
test indexer::tests::search_empty_query_with_no_filters_returns_bad_request ... ok
test indexer::tests::search_boolean_or ... ok
test indexer::tests::search_empty_query_with_tag_filter_still_works ... ok
test indexer::tests::search_enriches_created_at ... ok
test indexer::tests::search_enriches_doogat_type ... ok
test indexer::tests::search_enriches_fields ... ok
test indexer::tests::search_enriches_tags_from_body_hashtags ... ok
test indexer::tests::search_enriches_tags_from_frontmatter ... ok
test indexer::tests::search_filter_by_core_column_date_eq ... ok
test indexer::tests::search_filter_by_core_column_title ... ok
test indexer::tests::search_filter_by_field_contains ... ok
test indexer::tests::search_filter_by_field_eq ... ok
test indexer::tests::resolve_tests::resolve_partial_path_with_md_suffix ... ok
test indexer::tests::search_filter_by_junction_contains ... ok
test indexer::tests::search_filter_by_junction_contains_with_materialized_column ... ok
test indexer::tests::search_filter_by_junction_eq ... ok
test indexer::tests::schema_parses_allowed_values_and_default ... ok
test indexer::tests::search_filter_by_junction_in ... ok
test indexer::tests::search_filter_by_junction_union_multi_type ... ok
test indexer::tests::search_filter_by_materialized_column_contains ... ok
test indexer::tests::search_filter_by_materialized_column_eq ... ok
test indexer::tests::search_filter_by_tag ... ok
test indexer::tests::search_filter_by_type ... ok
test indexer::tests::search_filter_by_user_junction_contains ... ok
test indexer::tests::search_filter_by_user_junction_eq ... ok
test indexer::tests::search_filter_by_user_junction_in ... ok
test indexer::tests::search_filter_combined ... ok
test indexer::tests::search_filter_core_column_in ... ok
test indexer::tests::search_filter_falls_back_to_ddb_fields ... ok
test indexer::tests::search_filter_fields_fallback_in ... ok
test indexer::tests::search_filter_in_empty_returns_no_results ... ok
test indexer::tests::search_filter_in_single_element ... ok
test indexer::tests::search_filter_materialized_column_in ... ok
test indexer::tests::search_filter_materialized_column_multiple_types ... ok
test indexer::tests::search_filter_materialized_with_type_filter ... ok
test indexer::tests::search_filter_self_route_field_id_contains ... ok
test indexer::tests::search_filter_tag_via_where_combined_with_type ... ok
test indexer::tests::search_filter_tag_via_where_contains ... ok
test indexer::tests::search_filter_tag_via_where_eq ... ok
test indexer::tests::search_filter_tag_via_where_in ... ok
test indexer::tests::search_filter_user_junction_contains_default_title_when_unset ... ok
test indexer::tests::search_in_query_field_filter_on_materialized_column ... ok
test indexer::tests::search_filter_user_junction_contains_uses_search_key ... ok
test indexer::tests::search_in_query_filter_combined_with_text ... ok
test indexer::tests::search_in_query_filter_intersects_with_argument_where_filter ... ok
test indexer::tests::search_in_query_tag_filter_routes_through_extracted_filters ... ok
test indexer::tests::search_in_query_tag_matches_argument_tag_filter ... ok
test indexer::tests::search_malformed_fts5_query_returns_bad_request ... ok
test indexer::tests::search_negation_all_negative ... ok
test indexer::tests::search_negation_all_negative_paginated ... ok
test indexer::tests::search_negation_all_negative_with_tag_and_type_filter ... ok
test indexer::tests::search_negation_all_negative_with_type_filter ... ok
test indexer::tests::search_negation_multiple_nots ... ok
test indexer::tests::search_negation_nested_not_and ... ok
test indexer::tests::search_negation_no_results_when_all_excluded ... ok
test indexer::tests::search_negation_paginated_total_count_correct ... ok
test indexer::tests::search_negation_positive_not_negative ... ok
test indexer::tests::search_negation_positive_with_not_tag ... ok
test indexer::tests::search_negation_ranking_based_on_positive_only ... ok
test indexer::tests::search_negation_stemming ... ok
test indexer::tests::search_negation_with_tag_filter ... ok
test indexer::tests::search_never_returns_sql_error_for_user_input ... ok
test indexer::tests::search_negation_with_type_filter ... ok
test indexer::tests::search_no_filters_unchanged ... ok
test indexer::tests::search_non_tag_negated_field_filter_returns_bad_request ... ok
test indexer::tests::search_paginated_also_enriches ... ok
test indexer::tests::search_quoted_phrase ... ok
test indexer::tests::search_returns_same_hits_as_paginated ... ok
test indexer::tests::search_tag_negation_still_works ... ok
test indexer::tests::search_unbalanced_paren_returns_bad_request ... ok
test indexer::tests::search_untyped_doogat_has_none_type_and_fields ... ok
test indexer::tests::tag_source_column ... ok
test indexer::tests::tag_prefix_query ... ok
test indexer::tests::unstamped_but_compliant_schema_is_not_dropped_and_gets_stamped ... ok
test indexer::tests::upsert_replaces_old_data ... ok
test indexer::tests::version_mismatch_forces_drop_without_consulting_legacy_probe ... ok
test indexer::tests::upgrade_old_3col_fts_to_4col ... ok
test indexer::tests::with_immediate_transaction_commits_on_ok ... ok
test indexer::tests::with_immediate_transaction_passes_through_return_value ... ok
test indexer::tests::with_immediate_transaction_rolls_back_on_err ... ok
test maintenance::tests::check_write_threshold_skips_when_disabled ... ok
test indexer::tests::two_racing_cold_start_rebuilds_run_the_destructive_work_only_once ... ok
test maintenance::tests::maybe_auto_run_skips_when_disabled ... ok
test maintenance::tests::probe_returns_consistent_result ... ok
test maintenance::tests::maybe_auto_run_runs_when_enabled ... ok
test maintenance::tests::check_write_threshold_triggers_at_threshold ... ok
test maintenance::tests::run_with_deleted_dir_returns_error ... ok
test parser::tests::bare_url_in_code_block_skipped ... ok
test parser::tests::bare_url_not_double_counted ... ok
test parser::tests::bare_url_trailing_punct_trimmed ... ok
test parser::tests::basic_three_zone_split ... ok
test parser::tests::body_zone_dedup_unchanged ... ok
test parser::tests::checkboxes_all_states ... ok
test parser::tests::checkboxes_date_prefix ... ok
test parser::tests::checkboxes_due_date ... ok
test parser::tests::checkboxes_indent_level ... ok
test parser::tests::checkboxes_line_numbers ... ok
test parser::tests::checkboxes_skip_code_block ... ok
test parser::tests::code_block_with_separator ... ok
test parser::tests::cross_zone_error_unchanged ... ok
test parser::tests::embed_in_code_block_skipped ... ok
test parser::tests::embed_not_double_counted_as_wikilink ... ok
test parser::tests::empty_after_last_separator_backtracks ... ok
test parser::tests::extract_all_link_types ... ok
test parser::tests::extract_bare_url_basic ... ok
test parser::tests::extract_embed_basic ... ok
test parser::tests::extract_embed_full ... ok
test parser::tests::extract_embed_with_display ... ok
test parser::tests::extract_embed_with_section ... ok
test parser::tests::extract_markdown_link_basic ... ok
test parser::tests::extract_markdown_link_external ... ok
test parser::tests::frontmatter_all_fields ... ok
test parser::tests::frontmatter_at_exactly_the_byte_cap_still_parses ... ok
test parser::tests::frontmatter_empty ... ok
test parser::tests::frontmatter_explicit_id_overrides_stem_fallback ... ok
test parser::tests::frontmatter_extra_fields_preserved ... ok
test parser::tests::frontmatter_id_fallback_from_filename ... ok
test parser::tests::frontmatter_id_fallback_rejects_long_numeric_stem ... ok
test parser::tests::frontmatter_id_fallback_rejects_non_numeric_stem ... ok
test parser::tests::frontmatter_id_fallback_rejects_short_numeric_stem ... ok
test parser::tests::frontmatter_one_byte_over_the_cap_fails ... ok
test parser::tests::frontmatter_over_cap_error_states_cap_and_actual_size ... ok
test parser::tests::hashtags_basic ... ok
test parser::tests::hashtags_dedup ... ok
test parser::tests::hashtags_hierarchical ... ok
test parser::tests::hashtags_line_start_and_mid ... ok
test parser::tests::hashtags_not_in_urls ... ok
test parser::tests::hashtags_skip_fenced_code ... ok
test parser::tests::hashtags_skip_inline_code ... ok
test parser::tests::hashtags_skip_wikilinks ... ok
test parser::tests::hashtags_whitespace_required ... ok
test indexer::tests::rematerialize_never_exposes_missing_table_to_concurrent_reader ... ok
test maintenance::tests::run_reports_fallback_field ... ok
test parser::tests::inline_fields_body_only ... ok
test parser::tests::inline_fields_cross_zone_duplicate_errors ... ok
test parser::tests::inline_fields_empty_reference_value ... ok
test parser::tests::inline_fields_mixed ... ok
test parser::tests::inline_fields_normal_next_to_inline_code ... ok
test parser::tests::inline_fields_reference_only ... ok
test parser::tests::inline_fields_reference_strips_wikilinks ... ok
test parser::tests::inline_fields_same_zone_duplicate_first_wins ... ok
test parser::tests::inline_fields_skip_fenced_code_block ... ok
test parser::tests::inline_fields_skip_inline_code ... ok
test parser::tests::inline_fields_skip_tilde_fenced_code_block ... ok
test parser::tests::markdown_link_in_code_block_skipped ... ok
test parser::tests::multi_value_reference_fields_preserved ... ok
test parser::tests::no_reference_section ... ok
test parser::tests::parse_full_doogat ... ok
test parser::tests::parse_minimal_doogat ... ok
test parser::tests::parse_obsidian_passthrough ... ok
test parser::tests::rewrite_id_field_preserves_everything_else ... ok
test parser::tests::rewrite_id_field_propagates_parse_error ... ok
test parser::tests::rewrite_id_field_replaces_existing_id ... ok
test parser::tests::rewrite_id_field_sets_id_when_absent ... ok
test parser::tests::rewrite_links_embeds ... ok
test parser::tests::rewrite_links_markdown ... ok
test parser::tests::rewrite_links_mixed ... ok
test parser::tests::rewrite_links_skips_bare_urls ... ok
test parser::tests::rewrite_wikilinks_bare ... ok
test parser::tests::rewrite_wikilinks_multiple_occurrences ... ok
test parser::tests::rewrite_wikilinks_no_match ... ok
test parser::tests::rewrite_wikilinks_path_qualified ... ok
test parser::tests::rewrite_wikilinks_reference_section ... ok
test parser::tests::rewrite_wikilinks_with_display ... ok
test parser::tests::rewrite_wikilinks_yaml_quoted ... ok
test parser::tests::sections_basic ... ok
test parser::tests::sections_empty_body ... ok
test parser::tests::sections_heading_only ... ok
test parser::tests::sections_nested_levels ... ok
test parser::tests::sections_pre_heading_content ... ok
test parser::tests::sections_preserves_content_whitespace ... ok
test parser::tests::sections_skip_fenced_code ... ok
test parser::tests::sections_trailing_hashes ... ok
test parser::tests::serialize_canonical_yaml_key_ordering ... ok
test parser::tests::serialize_no_reference_section ... ok
test parser::tests::serialize_round_trip ... ok
test parser::tests::strip_wikilink_cases ... ok
test parser::tests::thematic_break_not_reference_boundary ... ok
test parser::tests::trailing_separator_after_reference_backtracks ... ok
test parser::tests::wikilinks_body ... ok
test parser::tests::wikilinks_frontmatter ... ok
test parser::tests::wikilinks_reference ... ok
test parser::tests::yaml_canonical_special_chars_quoted ... ok
test parser::tests::yaml_user_key_order_preserved_on_body_edit ... ok
test schema_diff::desired::tests::accepts_data_types_with_blocked_tokens_as_enum_values ... ok
test schema_diff::desired::tests::accepts_default_values_with_blocked_tokens_as_string_data ... ok
test schema_diff::desired::tests::accepts_legitimate_data_types ... ok
test schema_diff::desired::tests::accepts_legitimate_default_values ... ok
test schema_diff::desired::tests::accepts_legitimate_identifiers_and_types ... ok
test schema_diff::desired::tests::accepts_legitimate_rename_from ... ok
test schema_diff::desired::tests::accepts_legitimate_search_key ... ok
test schema_diff::desired::tests::accepts_legitimate_unique_together ... ok
test schema_diff::desired::tests::all_valid_zone_tokens_and_omitted_zone_accepted ... ok
test schema_diff::desired::tests::doc_without_rename_from_yields_empty_renames ... ok
test schema_diff::desired::tests::empty_types_list_yields_zero_types ... ok
test schema_diff::desired::tests::explicit_zone_round_trips ... ok
test schema_diff::desired::tests::invalid_zone_token_is_rejected ... ok
test schema_diff::desired::tests::multiple_renames_across_types_each_tagged_with_its_table ... ok
test schema_diff::desired::tests::parses_arbitrary_types_and_columns ... ok
test schema_diff::desired::tests::parses_flow_and_block_forms_equivalently ... ok
test schema_diff::desired::tests::parses_multiple_types ... ok
test schema_diff::desired::tests::reference_column_round_trips ... ok
test schema_diff::desired::tests::rejects_column_missing_data_type ... ok
test schema_diff::desired::tests::rejects_column_name_with_injection_payload ... ok
test schema_diff::desired::tests::rejects_data_type_smuggling_sql ... ok
test schema_diff::desired::tests::rejects_data_type_with_extra_column ... ok
test schema_diff::desired::tests::rejects_data_type_with_extra_column_options ... ok
test schema_diff::desired::tests::rejects_default_value_smuggling_sql ... ok
test schema_diff::desired::tests::rejects_default_value_with_extra_column ... ok
test schema_diff::desired::tests::rejects_default_value_with_extra_column_options ... ok
test schema_diff::desired::tests::rejects_missing_types_key ... ok
test schema_diff::desired::tests::rejects_rename_from_not_an_identifier ... ok
test schema_diff::desired::tests::rejects_search_key_smuggling_sql ... ok
test schema_diff::desired::tests::rejects_table_name_not_an_identifier ... ok
test schema_diff::desired::tests::rejects_type_missing_name ... ok
test schema_diff::desired::tests::rejects_unique_together_column_smuggling_sql ... ok
test schema_diff::desired::tests::rejects_various_malformed_inputs ... ok
test schema_diff::desired::tests::rename_from_before_name_key_is_key_order_invariant ... ok
test schema_diff::desired::tests::rename_from_directive_is_captured_as_column_rename ... ok
test schema_diff::desired::tests::rename_from_in_flow_form_is_captured ... ok
test schema_diff::desired::tests::rename_from_key_is_stripped_from_assembled_column ... ok
test schema_diff::desired::tests::rename_from_value_colliding_with_key_name_is_handled_structurally ... ok
test schema_diff::desired::tests::required_flag_round_trips ... ok
test schema_diff::desired::tests::type_level_optional_fields_round_trip ... ok
test schema_diff::desired::tests::valid_doc_with_error_marker_substring_parses ... ok
test schema_diff::differ::tests::added_column_with_default_matching_zone_yields_only_add ... ok
test schema_diff::differ::tests::added_column_with_non_default_zone_yields_add_then_set_zone ... ok
test schema_diff::differ::tests::all_drops_sort_after_all_adds_across_types ... ok
test schema_diff::differ::tests::changed_data_type_yields_alter_column_type_to_desired ... ok
test schema_diff::differ::tests::changed_effective_zone_yields_set_zone_to_desired_zone ... ok
test schema_diff::differ::tests::changed_required_attribute_records_unsupported_and_emits_no_op ... ok
test schema_diff::differ::tests::changed_search_key_on_existing_type_yields_set_search_key ... ok
test schema_diff::differ::tests::changed_singleton_on_existing_type_yields_set_singleton ... ok
test schema_diff::differ::tests::changed_title_template_records_unsupported_and_emits_no_op ... ok
test schema_diff::differ::tests::cleared_search_key_on_existing_type_yields_set_search_key_none ... ok
test schema_diff::differ::tests::column_present_in_desired_only_yields_add_column ... ok
test schema_diff::differ::tests::column_present_in_live_only_yields_drop_column ... ok
test schema_diff::differ::tests::drop_column_sorts_after_additive_ops ... ok
test schema_diff::differ::tests::empty_live_yields_create_type_per_declared_type ... ok
test schema_diff::differ::tests::fully_matching_desired_yields_empty_plan ... ok
test schema_diff::differ::tests::new_type_with_search_key_emits_set_search_key_right_after_create ... ok
test schema_diff::differ::tests::new_type_without_search_key_emits_only_create ... ok
test schema_diff::differ::tests::origin_only_difference_yields_empty_plan ... ok
test schema_diff::differ::tests::removed_plus_added_column_never_infers_rename ... ok
test schema_diff::differ::tests::rename_column_sorts_before_drop_column ... ok
test schema_diff::differ::tests::rename_directive_emits_rename_not_drop_add ... ok
test schema_diff::differ::tests::rename_directive_with_absent_from_records_unsupported_no_rename ... ok
test schema_diff::differ::tests::rename_directive_with_colliding_to_records_unsupported_no_rename ... ok
test schema_diff::differ::tests::rename_with_retype_also_emits_alter_column_type ... ok
test schema_diff::differ::tests::same_effective_zone_despite_differing_zone_field_yields_no_set_zone ... ok
test schema_diff::differ::tests::shorter_live_slice_still_creates_trailing_declared_types ... ok
test schema_diff::plan::tests::describe_is_exact_and_unambiguous_per_variant ... ok
test schema_diff::plan::tests::describe_mentions_both_names_for_rename_column ... ok
test schema_diff::plan::tests::describe_mentions_table_and_target_for_drop_column ... ok
test schema_diff::plan::tests::describe_mentions_table_for_create_type ... ok
test schema_diff::plan::tests::from_plan_clones_unsupported ... ok
test schema_diff::plan::tests::from_plan_copies_dry_run_and_applied_flags ... ok
test schema_diff::plan::tests::from_plan_create_type_table_is_schema_table_name ... ok
test schema_diff::plan::tests::from_plan_emits_one_report_per_op_in_order ... ok
test schema_diff::plan::tests::from_plan_maps_each_field_from_matching_plan_op ... ok
test schema_diff::plan::tests::from_plan_non_destructive_op_reports_destructive_false ... ok
test schema_diff::plan::tests::has_destructive_false_when_no_op_destructive ... ok
test schema_diff::plan::tests::has_destructive_true_when_any_op_destructive ... ok
test schema_diff::plan::tests::is_destructive_false_for_all_other_variants ... ok
test schema_diff::plan::tests::is_destructive_true_for_drop_and_rename_only ... ok
test schema_diff::plan::tests::is_empty_false_when_ops_present ... ok
test schema_diff::plan::tests::is_empty_true_when_no_ops_even_with_unsupported ... ok
test schema_diff::plan::tests::plan_op_and_schema_plan_are_comparable_by_value ... ok
test schema_diff::plan::tests::render_add_column_basic ... ok
test schema_diff::plan::tests::render_add_column_enum_emits_enum_constraint ... ok
test schema_diff::plan::tests::render_add_column_never_emits_zone_even_when_set ... ok
test schema_diff::plan::tests::render_add_column_required_default_references_cascade ... ok
test schema_diff::plan::tests::render_alter_column_type ... ok
test schema_diff::plan::tests::render_create_type_column_with_zone_none_omits_zone_clause ... ok
test schema_diff::plan::tests::render_create_type_default_value_clause ... ok
test schema_diff::plan::tests::render_create_type_does_not_emit_search_key ... ok
test schema_diff::plan::tests::render_create_type_empty_unique_together_adds_no_constraint ... ok
test schema_diff::plan::tests::render_create_type_enum_column_emits_enum_constraint ... ok
test schema_diff::plan::tests::render_create_type_full_clause_ordering ... ok
test schema_diff::plan::tests::render_create_type_multiple_columns_comma_separated ... ok
test schema_diff::plan::tests::render_create_type_quotes_reserved_word_and_novel_identifiers ... ok
test schema_diff::plan::tests::render_create_type_references_with_on_delete_cascade_renders_clause ... ok
test schema_diff::plan::tests::render_create_type_references_with_on_delete_restrict_omits_cascade ... ok
test schema_diff::plan::tests::render_create_type_single_required_column_with_zone ... ok
test schema_diff::plan::tests::render_create_type_singleton_appends_trailing_singleton ... ok
test schema_diff::plan::tests::render_create_type_unique_together_appends_table_level_constraints ... ok
test schema_diff::plan::tests::render_create_type_zone_body_and_reference_tokens_are_lowercase ... ok
test schema_diff::plan::tests::render_drop_column ... ok
test schema_diff::plan::tests::render_hyphenated_identifiers_are_quoted_in_create_and_add ... ok
test schema_diff::plan::tests::render_rename_column ... ok
test schema_diff::plan::tests::render_set_search_key_none_renders_drop ... ok
test schema_diff::plan::tests::render_set_search_key_some_names_the_column ... ok
test schema_diff::plan::tests::render_set_singleton_off_renders_drop ... ok
test schema_diff::plan::tests::render_set_singleton_on_renders_set ... ok
test schema_diff::plan::tests::render_set_zone_uses_zone_then_for_column_order ... ok
test schema_diff::plan::tests::render_sql_has_no_trailing_semicolon ... ok
test schema_diff::plan::tests::to_sql_appends_semicolon_per_op_and_joins_with_newline ... ok
test schema_diff::plan::tests::to_sql_empty_ops_blank_even_with_unsupported ... ok
test schema_diff::plan::tests::to_sql_empty_plan_is_blank ... ok
test schema_diff::plan::tests::to_sql_single_op_has_trailing_semicolon_and_no_newline ... ok
test search_query::tests::and_flattening ... ok
test search_query::tests::and_operands_sorted_alphabetically ... ok
test search_query::tests::case_insensitive_and_operator ... ok
test search_query::tests::case_insensitive_and_operator_mixed_case ... ok
test search_query::tests::case_insensitive_and_operator_upper ... ok
test search_query::tests::case_insensitive_words_with_whitespace ... ok
test search_query::tests::colon_syntax_same_as_equals ... ok
test search_query::tests::compile_and_of_two_field_equals ... ok
test search_query::tests::compile_bare_and_operator_rejected ... ok
test search_query::tests::compile_bare_asterisk_rejected ... ok
test search_query::tests::compile_bare_dot_asterisk_rejected ... ok
test search_query::tests::compile_bare_double_asterisk_rejected ... ok
test search_query::tests::compile_bare_not_operator_rejected ... ok
test search_query::tests::compile_bare_or_operator_rejected ... ok
test search_query::tests::compile_colon_syntax_treated_same_as_equals ... ok
test search_query::tests::compile_dotted_value_preserved ... ok
test search_query::tests::compile_empty_returns_no_fts_no_filters ... ok
test search_query::tests::compile_field_equals_and_multiple_text ... ok
test search_query::tests::compile_field_equals_and_text ... ok
test search_query::tests::compile_mixed_positive_and_not_field_equals ... ok
test search_query::tests::compile_non_tag_negated_field_rejected ... ok
test search_query::tests::compile_not_field_equals_extracted_as_negated ... ok
test search_query::tests::compile_or_of_field_equals_not_decomposed ... ok
test search_query::tests::compile_single_field_equals_no_fts ... ok
test search_query::tests::compile_single_full_text_passes_through ... ok
test search_query::tests::compile_unparseable_rejected ... ok
test search_query::tests::complex_nested_and_operands_sorted ... ok
test search_query::tests::complex_nested_and_operands_sorted_reversed_input ... ok
test search_query::tests::deeply_nested_recursive_normalization ... ok
test search_query::tests::empty_field_name_parses_as_terms ... ok
test search_query::tests::empty_field_value_fallback ... ok
test search_query::tests::empty_string_returns_empty ... ok
test search_query::tests::equals_quoted_value_preserves_spaces ... ok
test search_query::tests::error_class_consistency_issue_6_c2 ... ok
test search_query::tests::extract_negations_and_all_negative ... ok
test search_query::tests::extract_negations_and_multiple_positives_after_removing_nots ... ok
test search_query::tests::extract_negations_and_with_multiple_nots ... ok
test search_query::tests::extract_negations_and_with_not_field_equals ... ok
test search_query::tests::extract_negations_and_with_one_not ... ok
test search_query::tests::extract_negations_not_field_equals ... ok
test search_query::tests::extract_negations_not_with_compound_inner ... ok
test search_query::tests::extract_negations_or_not_decomposed ... ok
test search_query::tests::extract_negations_standalone_field_equals ... ok
test search_query::tests::extract_negations_standalone_fulltext ... ok
test search_query::tests::extract_negations_standalone_not ... ok
test search_query::tests::field_equals_lowercased ... ok
test search_query::tests::field_filters_sorted_by_serialized_form ... ok
test search_query::tests::field_filters_sorted_regardless_of_input_order ... ok
test search_query::tests::implicit_and_between_bare_words ... ok
test search_query::tests::implicit_and_with_field_filters_sorted ... ok
test search_query::tests::invalid_query_falls_back_to_lowercase_whitespace_collapse ... ok
test search_query::tests::mixed_operators_and_binds_tighter ... ok
test search_query::tests::nested_not ... ok
test search_query::tests::normalize_and_search_accept_same_inputs_issue_6_c1 ... ok
test search_query::tests::normalize_is_idempotent ... ok
test search_query::tests::not_operator_case_insensitive ... ok
test search_query::tests::not_with_field_filter ... ok
test search_query::tests::or_flattening ... ok
test search_query::tests::or_operator_case_insensitive ... ok
test search_query::tests::or_preserves_operand_order ... ok
test search_query::tests::parenthesized_or_with_and ... ok
test search_query::tests::parse_complex_negation ... ok
test search_query::tests::parse_empty_returns_none ... ok
test search_query::tests::parse_explicit_and ... ok
test search_query::tests::parse_field_filter ... ok
test search_query::tests::parse_nested_parens ... ok
test search_query::tests::parse_not ... ok
test search_query::tests::parse_or ... ok
test search_query::tests::parse_quoted_phrase ... ok
test search_query::tests::parse_returns_none_on_bad_input ... ok
test search_query::tests::parse_simple_word ... ok
test search_query::tests::parse_two_words_implicit_and ... ok
test search_query::tests::quoted_string_in_field_filter_preserves_spaces ... ok
test search_query::tests::single_word_lowercased ... ok
test search_query::tests::standalone_quoted_string_preserves_quotes ... ok
test search_query::tests::to_fts_query_and ... ok
test search_query::tests::to_fts_query_and_with_not ... ok
test search_query::tests::to_fts_query_field_equals_uses_value ... ok
test search_query::tests::to_fts_query_nested ... ok
test search_query::tests::to_fts_query_not ... ok
test search_query::tests::to_fts_query_not_compound ... ok
test search_query::tests::to_fts_query_or ... ok
test search_query::tests::to_fts_query_quoted_phrase ... ok
test search_query::tests::to_fts_query_single_word ... ok
test search_query::tests::validate_and_compile_empty_string ... ok
test search_query::tests::validate_and_compile_field_only ... ok
test search_query::tests::validate_and_compile_mixed_query ... ok
test search_query::tests::validate_and_compile_valid_query ... ok
test search_query::tests::validate_and_compile_whitespace_only ... ok
test search_query::tests::whitespace_collapsed_and_implicit_and ... ok
test search_query::tests::whitespace_only_returns_empty ... ok
test maintenance::tests::run_with_explicit_task ... ok
test maintenance::tests::run_succeeds_on_temp_repo ... ok
test ffi::tests::export_delta_bundle_unknown_node_errors ... ok
test service::create_unregistered_policy_tests::strict_unregistered_type_returns_type_not_registered ... ok
test service::mock_index_tests::apply_schema_dry_run_return_point_also_carries_the_reindex_warning ... ok
test service::mock_index_tests::apply_schema_facade_emits_no_reindex_warning_when_nothing_was_skipped ... ok
test service::mock_index_tests::apply_schema_facade_includes_exactly_one_reindex_warning_when_files_are_skipped ... ok
test ffi::tests::list_type_schemas_returns_created_type ... ok
test ffi::tests::execute_sql_delete_removes_doogat ... ok
test parser::tests::id_generation_14_digits ... ok
test service::mock_index_tests::get_doogat_parsed_runs_against_mock_index ... ok
test service::mock_index_tests::skip_stale_check_produces_no_reindex_warning_even_when_mock_would_report_some ... ok
test service::mock_index_tests::update_facade_emits_no_reindex_warning_when_nothing_was_skipped ... ok
test service::mock_index_tests::update_facade_includes_exactly_one_reindex_warning_when_files_are_skipped ... ok
test parser::tests::id_generation_no_duplicates ... ok
test service::create_unregistered_policy_tests::baseonly_unregistered_type_creates_base_doogat_with_warning ... ok
test service::create_unregistered_policy_tests::baseonly_typedef_type_creates_base_doogat_with_warning ... ok
test ffi::tests::execute_sql_update_modifies_doogat ... ok
test ffi::tests::export_delta_bundle_targets_node ... ok
test service::mock_index_tests::create_facade_emits_no_reindex_warning_when_nothing_was_skipped ... ok
test ffi::tests::ffi_singleton_create_exposes_structured_error_context ... ok
test service::mock_index_tests::create_facade_includes_exactly_one_reindex_warning_when_files_are_skipped ... ok
test ffi::tests::transaction_commit_persists_writes ... ok
test ffi::tests::transaction_rollback_discards_writes ... ok
test service::schema_apply::tests::describe_type_returns_none_for_absent_type ... ok
test service::mock_index_tests::create_facade_preserves_baseonly_warning_alongside_reindex_warning ... ok
test service::schema_apply::tests::dry_run_returns_plan_without_mutating ... ok
test service::schema_apply::tests::add_only_drift_applies_without_allow_destructive ... ok
test ffi::tests::execute_sql_insert_returns_id_and_queryable ... ok
test service::schema_apply::tests::apply_adds_hyphenated_column_to_existing_hyphenated_type ... ok
test service::create_unregistered_policy_tests::baseonly_registered_type_uses_typed_pipeline ... ok
test ffi::tests::execute_sql_select_returns_rows ... ok
test service::schema_apply::tests::apply_creates_declared_type ... ok
test service::tests::aggregate_query_empty ... ok
test service::tests::aggregate_query_select_one ... ok
test service::schema_apply::tests::apply_failure_leaves_git_head_unchanged ... ok
test service::tests::auto_maintenance_default_off ... ok
test service::tests::backlink_ids_empty ... ok
test service::schema_apply::tests::apply_hyphenated_type_and_column_succeeds_and_is_idempotent ... ok
test service::schema_apply::tests::apply_hyphenated_unique_together_succeeds ... ok
test service::schema_apply::tests::apply_renames_hyphenated_column_on_hyphenated_type ... ok
test service::tests::batch_create_empty ... ok
test service::schema_apply::tests::apply_renaming_and_adding_produces_single_commit ... ok
test service::schema_apply::tests::apply_reserved_word_column_succeeds_and_is_idempotent ... ok
test ffi::tests::transaction_multiple_ops_commit_atomically ... ok
test service::schema_apply::tests::destructive_drop_without_allow_destructive_is_blocked_and_mutates_nothing ... ok
test service::schema_apply::tests::multi_add_column_one_apply_preserves_every_column ... ok
test service::schema_apply::tests::reapply_same_doc_is_idempotent_noop ... ok
test ffi::tests::export_delta_bundle_smaller_than_full has been running for over 60 seconds
test ffi::tests::parity_ffi_and_direct_sqlengine_produce_equivalent_results has been running for over 60 seconds
test service::tests::batch_create_cross_batch_unique_violation_returns_structured_error_prd_00131 ... ok
test ffi::tests::export_delta_bundle_smaller_than_full ... ok
test service::tests::batch_create_first_singleton_insert_succeeds_prd_00139 ... ok
test service::tests::batch_create_intra_batch_duplicate_error_rejects_whole_batch_issue_12 ... ok
test service::tests::batch_create_intra_batch_duplicate_ignore_returns_surviving_id_issue_12 ... ok
test ffi::tests::parity_ffi_and_direct_sqlengine_produce_equivalent_results ... ok
test service::schema_apply::tests::apply_with_rename_then_failure_rolls_back_atomically ... ok
test service::tests::batch_create_intra_batch_singleton_rejects_second_input_prd_00139 ... ok
test service::tests::batch_create_intra_batch_unique_violation_returns_structured_error_prd_00131 ... ok
test service::schema_apply::tests::partial_apply_rolls_back_atomically_then_reapply_creates ... ok
test service::sql::tests::execute_sql_at_top_level_refreshes_stale_index ... ok
test service::sql::tests::execute_sql_inside_open_transaction_does_not_refresh_index ... ok
test service::tests::all_doogat_ids_excludes_typedefs ... ok
test service::tests::batch_create_not_null_violation_returns_structured_error_prd_00131 ... ok
test service::tests::batch_create_omitted_title_no_typedef_rejects_with_not_null_issue_13 ... ok
test service::tests::batch_create_on_conflict_error_duplicate_fails ... ok
test service::tests::batch_create_on_conflict_ignore_duplicate_returns_existing ... ok
test service::tests::batch_create_on_conflict_ignore_first_insert_succeeds ... ok
test service::tests::batch_create_many_ignore_duplicate_does_not_write_half_row_prd_00129 ... ok
test service::tests::batch_create_missing_required_column_rejects_with_not_null_prd_00129 ... ok
test service::tests::aggregate_query_binds_query_value_param ... ok
test service::tests::batch_create_basic ... ok
test service::tests::batch_create_omitted_title_no_template_rejects_with_not_null_issue_13 ... ok
test service::tests::batch_create_omitted_title_renders_via_title_template_issue_13 ... ok
test service::tests::batch_create_default_next has been running for over 60 seconds
test service::tests::batch_create_second_singleton_insert_rejects_prd_00139 ... ok
test service::tests::batch_create_singleton_on_conflict_ignore_returns_existing_prd_00139 ... ok
test service::tests::batch_create_on_conflict_ignore_non_duplicate_creates_new ... ok
test service::tests::batch_create_rejects_invalid_allowed_values ... ok
test service::tests::batch_create_with_unregistered_type_rejects_with_type_not_registered_prd_00129 ... ok
test service::tests::batch_create_untyped_doogat_unaffected_by_typed_validation_prd_00129 ... ok
test service::tests::batch_create_default_next ... ok
test service::tests::batch_update_empty ... ok
test service::tests::batch_create_mixed_types has been running for over 60 seconds
test service::tests::batch_create_omitted_title_renders_via_references_template_issue_13 has been running for over 60 seconds
test service::tests::batch_create_with_unknown_field_rejects_with_unknown_field_prd_00129 ... ok
test service::tests::batch_create_typed_no_fields_with_only_nullable_columns_succeeds_prd_00129 ... ok
test service::tests::batch_create_typed_writes_to_type_table_prd_00129 ... ok
test service::tests::batch_create_return_order ... ok
test service::tests::batch_create_partitioned_next has been running for over 60 seconds
test service::tests::batch_create_rejects_fk_to_wrong_type has been running for over 60 seconds
test service::tests::batch_create_with_body ... ok
test service::tests::batch_create_rollback_on_failure ... ok
test service::tests::batch_create_with_tags ... ok
test service::tests::batch_create_single_commit ... ok
test service::tests::batch_create_routes_references_to_reference_zone has been running for over 60 seconds
test service::tests::batch_update_rejects_duplicate_ids ... ok
test service::tests::batch_create_mixed_types ... ok
test service::tests::compact_dry_run_no_nodes ... ok
test service::tests::batch_update_intra_batch_two_retypes_into_same_singleton_reject_prd_00157 ... ok
test service::tests::batch_create_with_fields ... ok
test service::tests::batch_create_routes_references_to_reference_zone ... ok
test service::tests::batch_update_updated_at ... ok
test service::tests::batch_create_with_type ... ok
test service::tests::batch_create_partitioned_next ... ok
test service::tests::batch_create_rejects_fk_to_wrong_type ... ok
test service::tests::batch_update_atomicity ... ok
test service::tests::batch_update_basic ... ok
test service::tests::batch_update_rejects_invalid_allowed_values ... ok
test service::tests::batch_update_retype_into_occupied_singleton_rejects_prd_00157 ... ok
test service::tests::batch_create_omitted_title_renders_via_references_template_issue_13 ... ok
test service::tests::create_doogat_with_extra_preserves_unregistered_type_silent_create ... ok
test service::tests::batch_update_mixed_fields ... ok
test service::tests::batch_update_mixed_with_and_without_fields ... ok
test service::tests::create_raw_and_read ... ok
test service::tests::create_returns_updated_at ... ok
test service::tests::crud_roundtrip ... ok
test service::tests::get_doogats_batch_empty_returns_empty ... ok
test service::tests::count_doogats_filtered_all ... ok
test service::tests::batch_update_rejects_invalid_fk_reference ... ok
test service::tests::create_doogat_with_extra_materialised_row_visible_to_fresh_service ... ok
test service::tests::delete_untyped_doogat_no_error ... ok
test service::tests::health_check_returns_true ... ok
test service::tests::init_creates_repo_and_opens ... ok
test service::tests::batch_update_single_commit has been running for over 60 seconds
test service::tests::batch_update_with_fields ... ok
test service::tests::install_bundled_type_unknown_fails ... ok
test service::tests::get_doogat_parsed_has_updated_at ... ok
test service::tests::create_doogat_raw_populates_auto_junction_for_typed_references ... ok
test service::tests::get_doogats_batch_single_id_matches_get_parsed ... ok
test service::tests::delete_doogat_cleans_materialized_row ... ok
test service::tests::delete_returns_broken_backlinks ... ok
test service::tests::install_bundled_type_project ... ok
test service::tests::create_doogat_with_extra_populates_auto_junction_for_references_column has been running for over 60 seconds
test service::tests::create_doogat_with_extra_rejects_fk_to_wrong_type has been running for over 60 seconds
test service::tests::get_doogats_batch_has_updated_at ... ok
test service::tests::create_doogat_with_extra_routes_references_for_registered_type has been running for over 60 seconds
test service::tests::get_doogats_batch_skips_invalid_ids ... ok
test service::tests::create_doogat_with_extra_populates_auto_junction_for_references_column ... ok
test service::tests::delete_blocks_when_referencing_column_is_restrict_prd_00129 has been running for over 60 seconds
test service::tests::batch_update_single_commit ... ok
test service::tests::delete_cascades_to_referencing_rows_when_marked_cascade_prd_00129 has been running for over 60 seconds
test service::tests::create_doogat_with_extra_routes_references_for_registered_type ... ok
test service::tests::list_doogats_filtered_by_tag ... ok
test service::tests::list_doogats_filtered_has_updated_at ... ok
test service::tests::get_doogats_batch_multiple_valid ... ok
test service::tests::delete_with_cascade_cycle_rejects_prd_00129 has been running for over 60 seconds
test service::tests::delete_blocks_when_referencing_column_is_restrict_prd_00129 ... ok
test service::tests::list_doogats_filtered_no_filter ... ok
test service::tests::delete_with_mixed_restrict_cascade_columns_behaves_per_column_prd_00129 has been running for over 60 seconds
test service::tests::delete_cascades_to_referencing_rows_when_marked_cascade_prd_00129 ... ok
test service::tests::list_doogats_filtered_sort_date_defaults_to_desc ... ok
test service::tests::create_doogat_with_extra_rejects_fk_to_wrong_type ... ok
test service::tests::list_doogats_filtered_sort_default_is_date_desc ... ok
test service::tests::delete_with_cascade_cycle_rejects_prd_00129 ... ok
test service::tests::raw_update_of_untyped_doogat_accepts_arbitrary_content ... ok
test service::tests::list_doogats_filtered_sort_invalid_field_falls_back_to_default ... ok
test service::tests::search_after_create ... ok
test service::tests::list_doogats_filtered_sort_by_title_asc ... ok
test service::tests::search_boost_fields_column_populated ... ok
test service::tests::set_auto_maintenance_roundtrip ... ok
test service::tests::list_doogats_filtered_sort_by_title_desc ... ok
test service::tests::list_doogats_filtered_sort_title_defaults_to_asc ... ok
test service::tests::sync_auto_registers_node_when_none_exists ... ok
test service::tests::sync_does_not_auto_register_when_node_file_exists_but_toml_missing ... ok
test service::tests::sync_reuses_existing_registration ... ok
test service::tests::list_tags_returns_counts ... ok
test service::tests::search_results_have_updated_at ... ok
test service::tests::sequence_children_empty ... ok
test service::tests::non_singleton_updates_unaffected_by_wrap_prd_00157 ... ok
test service::tests::reindex_rebuilds ... ok
test service::tests::list_doogats_filtered_with_limit ... ok
test service::tests::delete_with_mixed_restrict_cascade_columns_behaves_per_column_prd_00129 ... ok
test service::tests::query_raw_with_params_binds_query_value_param ... ok
test service::tests::search_boost_default_for_untyped ... ok
test service::tests::sort_by_updated_at ... ok
test service::tests::sql_create_table_and_insert ... ok
test service::tests::transaction_commit_persists ... ok
test service::tests::transaction_rollback_discards ... ok
test service::tests::search_boost_no_regression_without_type_filter ... ok
test service::tests::search_boost_ranking_with_boosted_type ... ok
test service::tests::typed_batch_update_rejects_structured_value_on_scalar_column ... ok
test service::tests::typed_create_rejects_structured_value_on_scalar_column ... ok
test service::tests::untyped_update_accepts_structured_value_for_extra_field ... ok
test service::tests::service_update_doogat_unset_on_never_set_references_does_not_dirty_doc ... ok
test service::tests::service_batch_update_syncs_auto_junction_on_references_change has been running for over 60 seconds
test service::tests::service_update_doogat_syncs_auto_junction_on_references_change has been running for over 60 seconds
test service::tests::service_update_doogat_unset_clears_auto_junction_on_references_column has been running for over 60 seconds
test service::tests::typed_filtered_list_has_updated_at ... ok
test service::tests::update_parsed_retype_into_empty_singleton_succeeds_prd_00157 ... ok
test service::tests::update_returns_updated_at ... ok
test service::tests::typed_update_accepts_structured_value_for_undeclared_extra_field ... ok
test service::tests::typed_update_rejects_structured_value_on_scalar_column ... ok
test service::update_facade_tests::update_nonexistent_id_returns_not_found_error ... ok
test service::tests::typed_create_rejects_fk_to_nonexistent_id has been running for over 60 seconds
test service::tests::typed_filtered_list_binds_query_value_param ... ok
test service::tests::service_update_doogat_unset_clears_auto_junction_on_references_column ... ok
test sql_engine::classify::tests::alter_table_requires_reload ... ok
test sql_engine::classify::tests::create_index_does_not_require_reload ... ok
test sql_engine::classify::tests::create_table_in_comment_does_not_require_reload ... ok
test sql_engine::classify::tests::create_table_in_string_literal_does_not_require_reload ... ok
test sql_engine::classify::tests::create_table_requires_reload ... ok
test sql_engine::classify::tests::dml_does_not_require_reload ... ok
test sql_engine::classify::tests::drop_index_does_not_require_reload ... ok
test sql_engine::classify::tests::drop_table_requires_reload ... ok
test sql_engine::classify::tests::multi_statement_batch_with_ddl_requires_reload ... ok
test sql_engine::classify::tests::plain_select_does_not_require_reload ... ok
test sql_engine::classify::tests::unparseable_custom_ddl_conservatively_requires_reload ... ok
test sql_engine::helpers::tests::re_create_table_singleton_captures_default_values_marker ... ok
test sql_engine::helpers::tests::re_create_table_singleton_matches_trailing_marker ... ok
test sql_engine::helpers::tests::re_create_table_singleton_rejects_non_marker_uses ... ok
test sql_engine::helpers::tests::re_drop_singleton_matches_quoted_and_bare_table_names ... ok
test sql_engine::helpers::tests::re_drop_singleton_rejects_unrelated_alter_forms ... ok
test sql_engine::helpers::tests::re_set_singleton_matches_quoted_and_bare_table_names ... ok
test sql_engine::helpers::tests::re_set_singleton_rejects_unrelated_alter_forms ... ok
test sql_engine::helpers::tests::strip_inline_zones_batch_with_unzoned_first_table_strips_later_table ... ok
test sql_engine::helpers::tests::strip_inline_zones_case_insensitive_keyword_and_value ... ok
test sql_engine::helpers::tests::strip_inline_zones_column_named_zone_does_not_misfire ... ok
test sql_engine::helpers::tests::strip_inline_zones_create_table_inside_string_literal_does_not_panic ... ok
test sql_engine::helpers::tests::strip_inline_zones_does_not_panic_on_unbalanced_parens ... ok
test sql_engine::helpers::tests::strip_inline_zones_does_not_panic_on_unterminated_quoted_identifier ... ok
test sql_engine::helpers::tests::strip_inline_zones_inline_zone_after_time_zone_type ... ok
test sql_engine::helpers::tests::strip_inline_zones_leading_non_create_statement_strips_later_table ... ok
test sql_engine::helpers::tests::strip_inline_zones_maps_two_zoned_columns ... ok
test sql_engine::helpers::tests::strip_inline_zones_no_zone_create_table_is_idempotent ... ok
test sql_engine::helpers::tests::strip_inline_zones_non_create_table_is_noop ... ok
test sql_engine::helpers::tests::strip_inline_zones_preserves_enum_comma ... ok
test sql_engine::helpers::tests::strip_inline_zones_quoted_identifier_key_strips_quotes ... ok
test sql_engine::helpers::tests::strip_inline_zones_quoted_paren_before_zone ... ok
test sql_engine::helpers::tests::strip_inline_zones_reference_zone_value_accepted ... ok
test sql_engine::helpers::tests::strip_inline_zones_rejects_invalid_zone_value ... ok
test sql_engine::helpers::tests::strip_inline_zones_single_zoned_column_maps_and_strips_token ... ok
test sql_engine::helpers::tests::strip_inline_zones_still_errors_on_genuine_bad_value ... ok
test sql_engine::helpers::tests::strip_inline_zones_strips_every_table_in_multi_statement_batch ... ok
test sql_engine::helpers::tests::strip_inline_zones_time_zone_type_is_not_treated_as_inline_zone ... ok
test sql_engine::helpers::tests::strip_inline_zones_trailing_whitespace_before_delimiter_still_maps ... ok
test sql_engine::helpers::tests::validate_rename_target_name_accepts_valid_identifiers ... ok
test sql_engine::helpers::tests::validate_rename_target_name_rejects_dot_and_space ... ok
test sql_engine::helpers::tests::validate_rename_target_name_rejects_empty ... ok
test sql_engine::helpers::tests::validate_rename_target_name_rejects_hyphen ... ok
test sql_engine::helpers::tests::validate_rename_target_name_rejects_leading_digit ... ok
test sql_engine::helpers::tests::validate_rename_target_name_rejects_reserved_names ... ok
test service::tests::update_field_validation_accepts_numeric_allowed_value ... ok
test service::tests::updated_at_changes_on_update ... ok
test service::tests::update_field_validation_rejects_invalid_allowed_values ... ok
test service::update_facade_tests::update_empty_unset_fields_preserves_existing_frontmatter ... ok
test service::tests::update_parsed_retype_untyped_into_occupied_singleton_rejects_prd_00157 ... ok
test service::tests::typed_create_rejects_fk_to_nonexistent_id ... ok
test service::update_facade_tests::update_facade_returns_empty_warnings_and_new_title ... ok
test service::update_facade_tests::update_facade_unset_fields_clears_frontmatter_field ... ok
test service::update_facade_tests::update_unset_of_absent_key_is_safe_noop ... ok
test service::tests::service_batch_update_syncs_auto_junction_on_references_change ... ok
test service::tests::service_update_doogat_syncs_auto_junction_on_references_change ... ok
test service::update_facade_tests::update_unset_removes_only_named_key_keeping_siblings ... ok
test sql_engine::tests::alter_column_type_boolean_rejected ... ok
test service::tests::update_with_fields_sets_frontmatter ... ok
test service::tests::update_with_unset_fields_removes_field ... ok
test sql_engine::tests::alter_column_type_char_to_varchar_rejected ... ok
test service::tests::update_field_validation_rejects_invalid_fk_reference ... ok
test sql_engine::tests::alter_column_type_core_columns_rejected ... ok
test service::tests::update_doogat_raw_syncs_auto_junction_on_references_change has been running for over 60 seconds
test service::tests::update_field_validation_rejects_fk_wrong_type has been running for over 60 seconds
test sql_engine::tests::alter_column_type_persists_in_typedef ... ok
test sql_engine::tests::alter_column_type_same_type_idempotent ... ok
test sql_engine::tests::alter_column_type_set_data_type_form_also_accepted ... ok
test service::tests::update_doogat_raw_syncs_auto_junction_on_references_change ... ok
test sql_engine::tests::alter_column_type_char_narrowing_uses_char_in_error ... ok
test sql_engine::tests::alter_column_type_shorthand_works_inside_transactional_batch ... ok
test sql_engine::tests::alter_column_type_char_widens_metadata_only ... ok
test sql_engine::tests::alter_column_type_unknown_column_errors ... ok
test sql_engine::tests::alter_column_type_in_string_literal_is_not_rewritten ... ok
test sql_engine::tests::alter_column_type_integer_to_real_allows_when_clean ... ok
test sql_engine::tests::alter_column_type_narrow_varchar_allows_when_clean ... ok
test sql_engine::tests::alter_column_type_narrow_varchar_rejects_when_overflow ... ok
test sql_engine::tests::alter_column_type_real_to_integer_rejects_when_fractional ... ok
test sql_engine::tests::alter_column_type_references_column_rejects_non_widening ... ok
test sql_engine::tests::alter_column_type_references_column_widens_to_text ... ok
test sql_engine::tests::alter_drop_singleton_is_idempotent_prd_00139 ... ok
test sql_engine::tests::alter_drop_singleton_round_trips_prd_00139 ... ok
test sql_engine::tests::alter_set_singleton_is_idempotent_prd_00139 ... ok
test service::tests::update_field_validation_rejects_fk_wrong_type ... ok
test sql_engine::tests::alter_set_singleton_succeeds_on_empty_typedef_prd_00139 ... ok
test sql_engine::tests::alter_column_type_text_to_varchar_rejects_when_overflow ... ok
test sql_engine::tests::alter_table_rename_to_rejects_unknown_source ... ok
test sql_engine::tests::alter_column_type_in_multi_statement_batch_does_not_corrupt_following_insert ... ok
test sql_engine::tests::alter_table_add_column_extends_schema ... ok
test sql_engine::tests::alter_table_add_column_infers_zone_and_allowed_values ... ok
test sql_engine::tests::alter_table_add_column_propagates_not_null_into_required ... ok
test sql_engine::tests::alter_table_drop_column_removes_from_schema ... ok
test sql_engine::tests::alter_table_rename_column_rejects_collision ... ok
test sql_engine::tests::alter_table_rename_to_rejects_invalid_identifier_shapes ... ok
test sql_engine::tests::alter_table_rename_to_rejects_invalid_target_name ... ok
test sql_engine::tests::alter_table_rename_to_renames_empty_typedef ... ok
test sql_engine::tests::alter_set_singleton_succeeds_on_one_row_typedef_prd_00139 ... ok
test sql_engine::tests::alter_table_add_column_existing_data_gets_null ... ok
test sql_engine::tests::alter_table_set_zone ... ok
test sql_engine::tests::alter_table_set_zone_case_insensitive ... ok
test sql_engine::tests::alter_column_type_varchar_to_text_metadata_only ... ok
test sql_engine::tests::alter_table_set_zone_invalid_column ... ok
test sql_engine::tests::alter_table_set_zone_quoted_identifiers ... ok
test sql_engine::tests::alter_table_rename_column_rewrites_body_heading ... ok
test sql_engine::tests::alter_column_type_widens_varchar_metadata_only ... ok
test sql_engine::tests::alter_table_rename_column_rewrites_frontmatter ... ok
test sql_engine::tests::alter_table_set_zone_to_reference ... ok
test sql_engine::tests::alter_set_singleton_rejects_multi_row_typedef_prd_00139 ... ok
test sql_engine::tests::alter_table_rename_to_rejects_target_already_exists ... ok
test sql_engine::tests::alter_table_title_template ... ok
test sql_engine::tests::alter_table_title_template_persists ... ok
test sql_engine::tests::counter_seed_query_failure_surfaces_as_error ... ok
test sql_engine::tests::alter_table_rename_to_rewrites_references_in_other_typedefs ... ok
test sql_engine::tests::create_index_rejected_with_reason ... ok
test sql_engine::tests::blob_types_body ... ok
test sql_engine::tests::alter_table_set_zone_rematerializes ... ok
test sql_engine::tests::char_types_frontmatter ... ok
test sql_engine::tests::create_table_next_default_rejected_on_non_integer ... ok
test sql_engine::tests::create_index_if_not_exists_accepted_as_no_op_prd_00129 ... ok
test sql_engine::tests::alter_table_rename_column_rewrites_reference has been running for over 60 seconds
test sql_engine::tests::create_table_if_not_exists_is_idempotent ... ok
test sql_engine::tests::create_table_next_rejects_empty_args ... ok
test sql_engine::tests::create_table_next_rejects_multiple_args ... ok
test sql_engine::tests::alter_table_rename_to_rewrites_type_field_and_renames_table ... ok
test sql_engine::tests::create_table_next_scoped_rejects_nonexistent_column ... ok
test sql_engine::tests::begin_rollback_discards ... ok
test sql_engine::tests::create_table_mixed_static_and_next_defaults ... ok
test sql_engine::tests::alter_table_rename_column_rewrites_reference ... ok
test sql_engine::tests::create_table_multiple_unique_constraints ... ok
test sql_engine::tests::create_table_next_default_roundtrip ... ok
test sql_engine::tests::core_fields_in_materialized_table ... ok
test sql_engine::tests::create_table_next_default_stores_marker ... ok
test sql_engine::tests::create_table_rejects_reserved_names ... ok
test sql_engine::tests::create_table_next_scoped_default_stores_expression ... ok
test sql_engine::tests::begin_commit_batches_writes ... ok
test sql_engine::tests::create_table_produces_typedef_doogat ... ok
test sql_engine::tests::create_table_propagates_not_null_into_required ... ok
test sql_engine::tests::boolean_materialized_as_integer ... ok
test sql_engine::tests::bulk_delete_all_rows_when_no_where ... ok
test sql_engine::tests::bulk_update_all_rows_when_no_where ... ok
test sql_engine::tests::create_table_references_on_delete_set_null_rejected_prd_00129 ... ok
test sql_engine::tests::create_table_references_on_update_rejected_prd_00129 ... ok
test sql_engine::tests::bulk_delete_atomically_rejected_by_restrict_issue_10 has been running for over 60 seconds
test sql_engine::tests::bulk_delete_removes_matching_rows has been running for over 60 seconds
test sql_engine::tests::composite_unique_duplicate_rejected_with_clear_error_issue_9_f1 ... ok
test sql_engine::tests::create_trigger_rejected_with_reason ... ok
test sql_engine::tests::create_table_rejects_duplicate ... ok
test sql_engine::tests::create_view_rejected_with_reason ... ok
test sql_engine::tests::create_virtual_table_rejected_with_reason ... ok
test sql_engine::tests::data_type_to_string_preserves_sizes ... ok
test sql_engine::tests::bulk_update_modifies_matching_rows has been running for over 60 seconds
test sql_engine::tests::create_table_singleton_creates_lock_index_immediately_prd_00139 ... ok
test sql_engine::tests::create_table_stamps_origin_ddl ... ok
test sql_engine::tests::create_table_unique_constraint_persisted_in_typedef ... ok
test sql_engine::tests::concurrent_inserts_produce_unique_ids_issue_9_f8 has been running for over 60 seconds
test sql_engine::tests::create_table_references_on_delete_cascade_parses_and_persists_prd_00129 ... ok
test sql_engine::tests::bulk_delete_removes_matching_rows ... ok
test sql_engine::tests::create_table_with_singleton_marker_sets_flag_prd_00139 ... ok
test sql_engine::tests::bulk_update_modifies_matching_rows ... ok
test sql_engine::tests::create_table_references_on_delete_restrict_explicit_parses_prd_00129 ... ok
test sql_engine::tests::create_table_without_singleton_marker_keeps_flag_false_prd_00139 ... ok
test sql_engine::tests::create_unique_index_if_not_exists_accepted_as_no_op_prd_00129 ... ok
test sql_engine::tests::create_table_singleton_clears_pending_state_prd_00139 ... ok
test sql_engine::tests::create_table_with_references ... ok
test sql_engine::tests::create_table_with_singleton_default_values_marker_sets_flag_prd_00139 ... ok
test sql_engine::tests::delete_after_unique_failure_succeeds_issue_4_a1 ... ok
test sql_engine::tests::drop_index_rejected ... ok
test sql_engine::tests::dml_multi_row_insert_into_empty_singleton_typedef_rejects_prd_00139 ... ok
test sql_engine::tests::delete_from_hyphenated_table ... ok
test sql_engine::tests::create_table_unique_survives_rematerialization ... ok
test sql_engine::tests::drop_table_if_exists_no_error ... ok
test sql_engine::tests::drop_table_rejects_non_table ... ok
test sql_engine::tests::delete_removes_doogat_and_materialized_row ... ok
test sql_engine::tests::create_table_with_unique_constraint_enforced ... ok
test sql_engine::tests::drop_view_rejected ... ok
test sql_engine::tests::delete_with_missing_id_returns_affected_zero ... ok
test sql_engine::tests::dml_insert_into_singleton_typedef_succeeds_first_then_rejects_prd_00139 ... ok
test sql_engine::tests::drop_search_key_clears_typedef ... ok
test sql_engine::tests::eval_expr_abs ... ok
test sql_engine::tests::eval_expr_binary_op ... ok
test sql_engine::tests::eval_expr_coalesce_null_fallback ... ok
test sql_engine::tests::eval_expr_ifnull ... ok
test sql_engine::tests::eval_expr_literal_passthrough ... ok
test sql_engine::tests::eval_expr_nullif_returns_empty ... ok
test sql_engine::tests::dml_multi_row_insert_into_non_singleton_typedef_still_works_prd_00139 ... ok
test sql_engine::tests::delete_allowed_when_reference_is_nullable_issue_10 has been running for over 60 seconds
test sql_engine::tests::drop_auto_rollback ... ok
test sql_engine::tests::bulk_delete_atomically_rejected_by_restrict_issue_10 ... ok
test sql_engine::tests::delete_from_junction_writes_through has been running for over 60 seconds
test sql_engine::tests::delete_rejected_by_not_null_references_issue_10 has been running for over 60 seconds
test sql_engine::tests::enum_creates_allowed_values ... ok
test sql_engine::tests::delete_service_path_rejected_by_not_null_references_issue_10 has been running for over 60 seconds
test sql_engine::tests::delete_succeeds_after_child_removed_issue_10 has been running for over 60 seconds
test sql_engine::tests::delete_with_id_from_different_table_returns_affected_zero has been running for over 60 seconds
test sql_engine::tests::delete_allowed_when_reference_is_nullable_issue_10 ... ok
test sql_engine::tests::drop_table_cascades_junction_tables ... ok
test sql_engine::tests::delete_from_junction_writes_through ... ok
test sql_engine::tests::drop_table_removes_typedef_and_materialized ... ok
test sql_engine::tests::drop_table_strips_type_from_data_doogats ... ok
test sql_engine::tests::delete_with_id_from_different_table_returns_affected_zero ... ok
test sql_engine::tests::duplicate_insert_does_not_leave_ghost_doogats_row ... ok
test sql_engine::tests::error_preserves_active_txn ... ok
test sql_engine::tests::executesql_insert_accepts_empty_string_on_text ... ok
test sql_engine::tests::drop_table_cascade_deletes_all ... ok
test sql_engine::tests::executesql_insert_accepts_ifnull_with_value_on_nullable ... ok
test sql_engine::tests::executesql_insert_accepts_nullif_on_nullable_integer ... ok
test sql_engine::tests::executesql_insert_rejects_coalesce_null_on_not_null ... ok
test sql_engine::tests::executesql_insert_rejects_empty_string_on_integer ... ok
test sql_engine::tests::executesql_insert_rejects_ifnull_null_on_not_null_integer ... ok
test sql_engine::tests::executesql_insert_rejects_integer_type_mismatch ... ok
test sql_engine::tests::executesql_insert_rejects_missing_title_when_required ... ok
test sql_engine::tests::executesql_insert_rejects_not_null_violation ... ok
test sql_engine::tests::delete_rejected_by_not_null_references_issue_10 ... ok
test sql_engine::tests::executesql_insert_rejects_unknown_column ... ok
test sql_engine::tests::delete_service_path_rejected_by_not_null_references_issue_10 ... ok
test sql_engine::tests::delete_succeeds_after_child_removed_issue_10 ... ok
test sql_engine::tests::executesql_insert_rejects_varchar_overflow ... ok
test sql_engine::tests::executesql_insert_uses_explicit_title ... ok
test sql_engine::tests::inline_zone_invalid_value_errors ... ok
test sql_engine::tests::executesql_multi_row_insert_all_valid_succeeds ... ok
test sql_engine::tests::inline_zone_malformed_create_errors_without_panic ... ok
test sql_engine::tests::executesql_multi_row_insert_validation_failure_on_third_row ... ok
test sql_engine::tests::executesql_multi_row_insert_validation_failure_writes_no_rows ... ok
test sql_engine::tests::executesql_update_rejects_coalesce_null_on_not_null ... ok
test sql_engine::tests::executesql_update_rejects_integer_type_mismatch ... ok
test sql_engine::tests::inline_zone_body_overrides_text_and_numeric_defaults ... ok
test sql_engine::tests::inline_zone_distinct_zones_per_column_in_one_statement ... ok
test sql_engine::tests::inline_zone_keyword_and_value_are_case_insensitive ... ok
test sql_engine::tests::executesql_update_rejects_set_null_on_not_null ... ok
test sql_engine::tests::executesql_insert_uses_title_template_when_title_required ... ok
test sql_engine::tests::concurrent_inserts_produce_unique_ids_issue_9_f8 ... ok
test sql_engine::tests::inline_zone_on_core_column_records_zone_like_set_zone ... ok
test sql_engine::tests::executesql_update_rejects_unknown_column ... ok
test sql_engine::tests::executesql_update_rejects_varchar_overflow ... ok
test sql_engine::tests::full_create_insert_select_update_delete_cycle ... ok
test sql_engine::tests::inline_zone_on_enum_preserves_allowed_values ... ok
test sql_engine::tests::inline_zone_overrides_references_default ... ok
test sql_engine::tests::inline_zone_persists_across_fresh_engine ... ok
test sql_engine::tests::inline_zone_placement_agnostic_and_preserves_not_null ... ok
test sql_engine::tests::inline_zone_identical_to_set_zone ... ok
test sql_engine::tests::inline_zone_in_batch_round_trips_identically_to_set_zone ... ok
test sql_engine::tests::inline_zone_text_frontmatter_overrides_body_default ... ok
test sql_engine::tests::inline_zone_time_zone_typed_column_does_not_false_positive ... ok
test sql_engine::tests::inline_zone_multi_statement_batch_applies_per_table ... ok
test sql_engine::tests::insert_fills_default_value ... ok
test sql_engine::tests::failed_insert_on_table_a_does_not_corrupt_table_b_issue_4_a3 has been running for over 60 seconds
test sql_engine::tests::fk_existence_query_failure_surfaces_as_operational_error has been running for over 60 seconds
test sql_engine::tests::inline_zone_skipped_if_not_exists_does_not_leak_to_later_table ... ok
test sql_engine::tests::insert_creates_doogat_and_materialized_row ... ok
test sql_engine::tests::insert_defaults_date_from_id ... ok
test sql_engine::tests::insert_delete_read_content_returns_not_found ... ok
test sql_engine::tests::insert_explicit_date_preserved ... ok
test sql_engine::tests::fk_existence_query_failure_surfaces_as_operational_error ... ok
test sql_engine::tests::insert_explicit_title_overrides_template ... ok
test sql_engine::tests::insert_explicit_title_wins ... ok
test sql_engine::tests::insert_multi_row_creates_n_doogats ... ok
test sql_engine::tests::insert_multi_row_single_commit ... ok
test sql_engine::tests::insert_next_default_empty_table_starts_at_one ... ok
test sql_engine::tests::insert_after_unique_failure_succeeds_issue_4_a1 ... ok
test sql_engine::tests::insert_or_replace_rejected ... ok
test sql_engine::tests::insert_rejects_invalid_allowed_value ... ok
test sql_engine::tests::insert_rejects_unlisted_function ... ok
test sql_engine::tests::insert_next_default_multi_row_assigns_sequential ... ok
test sql_engine::tests::insert_into_junction_writes_through has been running for over 60 seconds
test sql_engine::tests::insert_next_default_persists_in_git ... ok
test sql_engine::tests::insert_next_default_explicit_override ... ok
test sql_engine::tests::insert_next_default_after_delete_uses_max_plus_one has been running for over 60 seconds
test sql_engine::tests::insert_next_partitioned_multi_row_same_partition ... ok
test sql_engine::tests::is_literal_expr_false_for_function ... ok
test sql_engine::tests::is_literal_expr_true_for_value ... ok
test sql_engine::tests::insert_next_default_auto_increments has been running for over 60 seconds
test sql_engine::tests::insert_produces_correct_zone_mapping ... ok
test sql_engine::tests::nested_begin_rejected ... ok
test sql_engine::tests::failed_insert_on_table_a_does_not_corrupt_table_b_issue_4_a3 ... ok
test sql_engine::tests::normalize_alter_column_type_only_rewrites_alter_form ... ok
test sql_engine::tests::insert_schema_date_column_no_duplicate ... ok
test sql_engine::tests::insert_into_junction_writes_through ... ok
test sql_engine::tests::on_conflict_do_update_rejected ... ok
test sql_engine::tests::insert_then_delete_within_txn ... ok
test sql_engine::tests::insert_then_update_within_txn ... ok
test sql_engine::tests::insert_title_fallback_type_id ... ok
test sql_engine::tests::parse_title_template_accepts_hyphen_in_identifier ... ok
test sql_engine::tests::parse_title_template_bare_placeholder ... ok
test sql_engine::tests::parse_title_template_dotted_placeholder ... ok
test sql_engine::tests::parse_title_template_empty_returns_no_placeholders ... ok
test sql_engine::tests::parse_title_template_mixed_placeholders ... ok
test sql_engine::tests::parse_title_template_rejects_empty_segment ... ok
test sql_engine::tests::parse_title_template_rejects_identifier_starting_with_digit ... ok
test sql_engine::tests::parse_title_template_rejects_multi_hop ... ok
test sql_engine::tests::partitioned_counter_seed_query_failure_surfaces_as_error ... ok
test sql_engine::tests::insert_next_default_auto_increments ... ok
test sql_engine::tests::insert_title_from_template ... ok
test sql_engine::tests::insert_next_default_partitioned_independent_sequences has been running for over 60 seconds
test sql_engine::tests::mysql_rename_table_alias_rejected_with_clear_message ... ok
test sql_engine::tests::no_inline_zone_preserves_implicit_derivation ... ok
test sql_engine::tests::on_conflict_do_nothing_returns_new_id ... ok
test sql_engine::tests::schema_from_parsed_rejects_dotted_path_on_missing_column ... ok
test sql_engine::tests::schema_from_parsed_rejects_dotted_path_on_non_ref_column ... ok
test sql_engine::tests::schema_from_parsed_rejects_multi_hop_title_template ... ok
test sql_engine::tests::schema_from_parsed_unique_together_absent ... ok
test sql_engine::tests::schema_from_parsed_unique_together_empty_list ... ok
test sql_engine::tests::schema_from_parsed_unique_together_flat ... ok
test sql_engine::tests::schema_from_parsed_unique_together_nested ... ok
test sql_engine::tests::insert_with_arithmetic ... ok
test sql_engine::tests::origin_ddl_persists_in_yaml ... ok
test sql_engine::tests::origin_preserved_after_alter ... ok
test sql_engine::tests::insert_next_default_partitioned_independent_sequences ... ok
test sql_engine::tests::plain_create_index_still_rejects_after_prd_00129 ... ok
test sql_engine::tests::insert_next_default_after_delete_uses_max_plus_one ... ok
test sql_engine::tests::rebuild_drops_orphan_materialized_tables ... ok
test sql_engine::tests::on_conflict_do_nothing_returns_existing_id ... ok
test sql_engine::tests::schema_roundtrips_title_template_and_origin ... ok
test sql_engine::tests::insert_title_template_bare_ref_still_returns_id has been running for over 60 seconds
test sql_engine::tests::on_delete_action_typedef_yaml_roundtrip_prd_00129 ... ok
test sql_engine::tests::select_still_passes_through ... ok
test sql_engine::tests::insert_title_template_dotted_ref_null_target_field_renders_empty has been running for over 60 seconds
test sql_engine::tests::insert_title_template_dotted_ref_resolves_target_title has been running for over 60 seconds
test sql_engine::tests::plain_insert_duplicate_still_errors ... ok
test sql_engine::tests::read_your_writes_within_txn ... ok
test sql_engine::tests::insert_with_coalesce_subquery ... ok
test sql_engine::tests::insert_with_fk_validates_reference ... ok
test sql_engine::tests::insert_title_template_bare_ref_still_returns_id ... ok
test sql_engine::tests::references_to_hyphenated_table ... ok
test sql_engine::tests::insert_title_template_dotted_ref_null_target_field_renders_empty ... ok
test sql_engine::tests::select_boolean_coercion_preserves_non_boolean_columns ... ok
test sql_engine::tests::select_boolean_null_stays_null ... ok
test sql_engine::tests::select_coerces_boolean_columns_to_true_false ... ok
test sql_engine::tests::select_coerces_boolean_false_to_false_string ... ok
test sql_engine::tests::select_cte_current_behavior_issue_8 ... ok
test sql_engine::tests::select_join_bypasses_boolean_coercion ... ok
test sql_engine::tests::set_creates_allowed_values ... ok
test sql_engine::tests::set_search_key_persists_to_typedef ... ok
test sql_engine::tests::set_search_key_rejects_missing_column ... ok
test sql_engine::tests::select_returns_materialized_data ... ok
test sql_engine::tests::set_search_key_round_trips_through_typedef_yaml ... ok
test sql_engine::tests::singleton_default_values_rejects_missing_required_default_prd_00139 ... ok
test sql_engine::tests::select_star_coerces_boolean_columns ... ok
test sql_engine::tests::select_subquery_in_from_current_behavior_issue_8 ... ok
test sql_engine::tests::set_title_template_accepts_title_when_target_type_not_yet_materialized ... ok
test sql_engine::tests::set_title_template_rejects_dotted_on_non_ref_column ... ok
test sql_engine::tests::set_title_template_rejects_missing_column ... ok
test sql_engine::tests::set_search_key_rejects_references_column ... ok
test sql_engine::tests::singleton_false_omits_yaml_key_prd_00139 ... ok
test sql_engine::tests::insert_title_template_dotted_ref_resolves_target_title ... ok
test sql_engine::tests::singleton_flag_round_trips_through_typedef_yaml_prd_00139 ... ok
test sql_engine::tests::select_join_returns_joined_rows_issue_8_e1 has been running for over 60 seconds
test sql_engine::tests::set_title_template_accepts_title_on_any_ref ... ok
test sql_engine::tests::singleton_without_default_values_does_not_seed_prd_00139 ... ok
test sql_engine::tests::set_title_template_rejects_bad_field_on_target_type ... ok
test sql_engine::tests::set_title_template_rejects_multi_hop ... ok
test sql_engine::tests::select_window_function_current_behavior_issue_8 ... ok
test sql_engine::tests::singleton_default_values_allows_nullable_columns_without_default_prd_00139 ... ok
test sql_engine::tests::singleton_default_values_auto_seeds_one_row_prd_00139 ... ok
test sql_engine::tests::select_union_current_behavior_issue_8 has been running for over 60 seconds
test sql_engine::tests::singleton_default_values_blocks_second_insert_prd_00139 ... ok
test sql_engine::tests::singleton_lock_failure_emits_structured_singleton_violation_prd_00139 ... ok
test sql_engine::tests::select_union_current_behavior_issue_8 ... ok
test sql_engine::tests::single_column_unique_duplicate_rejected_with_clear_error_issue_9_f2 ... ok
test sql_engine::tests::select_join_returns_joined_rows_issue_8_e1 ... ok
test sql_engine::tests::sql_bulk_delete_matching_zero_rows_leaves_junction_untouched has been running for over 60 seconds
test sql_engine::tests::sql_bulk_delete_parent_clears_owned_auto_junction_rows has been running for over 60 seconds
test sql_engine::tests::sql_delete_parent_clears_owned_auto_junction_rows has been running for over 60 seconds
test sql_engine::tests::sql_delete_parent_clears_owned_junction_rows_for_every_references_column has been running for over 60 seconds
test sql_engine::tests::sql_bulk_delete_matching_zero_rows_leaves_junction_untouched ... ok
test sql_engine::tests::sql_delete_referenced_target_clears_auto_junction_rows has been running for over 60 seconds
test sql_engine::tests::sql_delete_typedef_that_is_both_parent_and_child_cleans_both_directions has been running for over 60 seconds
test sql_engine::tests::sql_insert_populates_auto_junction_for_references_column has been running for over 60 seconds
test sql_engine::tests::sql_update_bulk_rolls_back_materialized_when_junction_sync_fails has been running for over 60 seconds
test sql_engine::tests::sql_update_set_null_on_references_clears_auto_junction has been running for over 60 seconds
test sql_engine::tests::sql_update_single_row_rolls_back_materialized_when_junction_sync_fails has been running for over 60 seconds
test sql_engine::tests::sql_delete_parent_clears_owned_auto_junction_rows ... ok
test sql_engine::tests::sql_update_syncs_auto_junction_when_references_changes has been running for over 60 seconds
test sql_engine::tests::test_cascade_atomic_single_commit has been running for over 60 seconds
test sql_engine::tests::sql_delete_referenced_target_clears_auto_junction_rows ... ok
test sql_engine::tests::sql_insert_populates_auto_junction_for_references_column ... ok
test sql_engine::tests::test_cascade_junction_multi_parent has been running for over 60 seconds
test sql_engine::tests::test_cascade_junction_no_false_positives has been running for over 60 seconds
test sql_engine::tests::sql_update_set_null_on_references_clears_auto_junction ... ok
test sql_engine::tests::sql_bulk_delete_parent_clears_owned_auto_junction_rows ... ok
test sql_engine::tests::test_cascade_junction_selective has been running for over 60 seconds
test sql_engine::tests::test_cascade_atomic_single_commit ... ok
test sql_engine::tests::test_cascade_junction_single_delete has been running for over 60 seconds
test sql_engine::tests::test_cascade_junction_no_false_positives ... ok
test sql_engine::tests::test_cascade_ref_multi_reference_preservation has been running for over 60 seconds
test sql_engine::tests::test_cascade_ref_multiple_referencing_doogats has been running for over 60 seconds
test sql_engine::tests::sql_update_bulk_rolls_back_materialized_when_junction_sync_fails ... ok
test sql_engine::tests::unique_ids_advances_past_committed_but_unindexed_repo_id ... ok
test sql_engine::tests::sql_update_single_row_rolls_back_materialized_when_junction_sync_fails ... ok
test sql_engine::tests::test_cascade_junction_single_delete ... ok
test sql_engine::tests::sql_update_syncs_auto_junction_when_references_changes ... ok
test sql_engine::tests::test_cascade_junction_multi_parent ... ok
test sql_engine::tests::sql_delete_parent_clears_owned_junction_rows_for_every_references_column ... ok
test sql_engine::tests::typed_doogat_stored_in_subfolder_and_crud_works ... ok
test sql_engine::tests::sql_delete_typedef_that_is_both_parent_and_child_cleans_both_directions ... ok
test sql_engine::tests::test_cascade_junction_selective ... ok
test sql_engine::tests::update_after_unique_failure_succeeds_issue_4_a1 ... ok
test sql_engine::tests::update_rejects_invalid_allowed_value ... ok
test sql_engine::tests::validate_accepts_boolean_variants ... ok
test sql_engine::tests::validate_accepts_integer_with_numeric_value ... ok
test sql_engine::tests::validate_accepts_not_null_with_default_already_filled ... ok
test sql_engine::tests::validate_accepts_reserved_columns ... ok
test sql_engine::tests::validate_accepts_varchar_no_length ... ok
test sql_engine::tests::validate_accepts_varchar_within_limit ... ok
test sql_engine::tests::validate_rejects_boolean_with_garbage ... ok
test sql_engine::tests::validate_rejects_integer_with_string_value ... ok
test sql_engine::tests::validate_rejects_not_null_absent_on_insert ... ok
test sql_engine::tests::validate_rejects_not_null_explicit_null_on_insert ... ok
test sql_engine::tests::validate_rejects_real_with_garbage ... ok
test sql_engine::tests::validate_rejects_unknown_column_on_insert ... ok
test sql_engine::tests::validate_rejects_varchar_overflow ... ok
test sql_engine::tests::validate_update_only_rejects_explicit_null_on_required ... ok
test sql_engine::tests::value_to_sql_formats_binary_op ... ok
test sql_engine::tests::value_to_sql_formats_coalesce ... ok
test sql_engine::tests::value_to_sql_formats_nested ... ok
test sql_engine::tests::value_to_sql_formats_subquery ... ok
test sql_engine::tests::value_to_sql_rejects_unlisted_function ... ok
test sql_engine::tests::test_cascade_ref_multi_reference_preservation ... ok
test sql_engine::tests::test_cascade_ref_single_removal has been running for over 60 seconds
test sql_engine::tests::test_cascade_ref_multiple_referencing_doogats ... ok
test sync_manager::tests::add_add_collision_detected ... ok
test sync_manager::tests::add_add_collision_resolution_is_independent_of_push_direction ... ok
test sync_manager::tests::add_add_collision_resolves_in_single_commit ... ok
test sync_manager::tests::add_add_errors_when_losing_ours_blob_oid_missing ... ok
test sync_manager::tests::add_add_errors_when_losing_theirs_blob_oid_missing ... ok
test sync_manager::tests::add_add_full_sync_both_survive ... ok
test sync_manager::tests::add_add_loser_blob_oid_is_ours_when_theirs_wins ... ok
test sync_manager::tests::add_add_loser_blob_oid_is_theirs_when_ours_wins ... ok
test sync_manager::tests::add_add_loser_blob_oid_role_swap_converges ... ok
test sync_manager::tests::add_add_missing_or_equal_hlc_picks_higher_content_key ... ok
test sync_manager::tests::add_add_succeeds_when_only_the_winning_sides_blob_oid_is_missing ... ok
test sync_manager::tests::add_add_winner_by_hlc ... ok
test sync_manager::tests::backward_compat_old_toml_without_status ... ok
test sync_manager::tests::binary_higher_hlc_wins_ours ... ok
test sync_manager::tests::binary_higher_hlc_wins_theirs ... ok
test sync_manager::tests::binary_lww_preserves_exact_bytes ... ok
test sync_manager::tests::binary_missing_hlc_picks_higher_blob_oid ... ok
test sync_manager::tests::binary_ref_delete_vs_edit_uses_resurrection ... ok
test sync_manager::tests::binary_tie_hlc_picks_higher_blob_oid ... ok
test sync_manager::tests::both_nodes_converge_on_the_same_backlink_targets_after_role_swap ... ok
test sync_manager::tests::clean_merge_validation_falls_back_to_crdt ... ok
test sync_manager::tests::list_nodes ... ok
test sync_manager::tests::lww_fallback_when_crdt_produces_invalid_output ... ok
test sync_manager::tests::node_status_defaults_to_active ... ok
test sync_manager::tests::open_without_registration_fails ... ok
test sync_manager::tests::ours_wins_keeps_every_ours_side_backlink_on_the_unchanged_winner_id ... ok
test sync_manager::tests::ours_wins_rewrites_every_theirs_side_backlink_to_the_losers_new_id ... ok
test sync_manager::tests::partition_classifies_ancestorless_conflicts_by_doogat_path_shape ... ok
test sync_manager::tests::partition_keeps_ancestorless_doogat_conflicts_in_add_add ... ok
test sync_manager::tests::partition_preserves_delete_edit_binary_ref_and_ancestor_rules ... ok
test sync_manager::tests::register_and_open_node ... ok
test sync_manager::tests::resurrected_marker_added ... ok
test sync_manager::tests::resurrected_marker_not_duplicated ... ok
test sync_manager::tests::retire_and_list_nodes ... ok
test sync_manager::tests::skewed_peer_does_not_win_indefinitely ... ok
test sync_manager::tests::sync_error_resets_skip_commit_graph_for_subsequent_commits ... ok
test sync_manager::tests::sync_state_update ... ok
test sql_engine::tests::update_expression_rejects_invalid_allowed_value ... ok
test sync_manager::tests::theirs_deleted_ours_edited_resurrects_with_marker ... ok
test sync_manager::tests::theirs_deleted_ours_untouched_stays_deleted ... ok
test types::doogat::tests::is_valid_shape_accepts_14_digits ... ok
test types::doogat::tests::is_valid_shape_rejects_wrong_length_and_non_digits ... ok
test types::doogat::tests::mime_from_filename_common_types ... ok
test types::doogat::tests::mime_from_filename_fallback ... ok
test types::query::tests::variant_set_matches_sql_parameter_domain ... ok
test types::schema::tests::effective_zone_varchar_length_cap ... ok
test types::schema::tests::singleton_field_defaults_false_on_new_schema ... ok
test types::value::tests::convenience_bool_at ... ok
test types::value::tests::convenience_f64_at ... ok
test types::value::tests::convenience_list_at ... ok
test types::value::tests::convenience_map_at ... ok
test types::value::tests::convenience_str_at ... ok
test types::value::tests::get_path_list_index ... ok
test types::value::tests::get_path_missing_key ... ok
test types::value::tests::get_path_nested_map ... ok
test types::value::tests::get_path_out_of_bounds ... ok
test types::value::tests::get_path_type_mismatch ... ok
test types::value::tests::path_parse_complex ... ok
test types::value::tests::path_parse_empty_rejected ... ok
test types::value::tests::path_parse_escaped_dot ... ok
test types::value::tests::path_parse_index ... ok
test types::value::tests::path_parse_simple ... ok
test types::value::tests::path_parse_trailing_dot_rejected ... ok
test types::value::tests::remove_path_returns_value ... ok
test types::value::tests::round_trip ... ok
test types::value::tests::set_path_creates_intermediates ... ok
test types::value::tests::set_path_replaces_existing ... ok
test sync_manager::tests::theirs_wins_keeps_theirs_side_backlinks_and_rewrites_ours_side_backlinks ... ok
test sql_engine::tests::two_inserts_one_deleted_commits_survivor ... ok
test sql_engine::tests::unique_constraint_failure_emits_structured_unique_violation_prd_00129 ... ok
test sql_engine::tests::update_from_rejected ... ok
test sql_engine::tests::update_modifies_doogat_and_materialized_row ... ok
test sql_engine::tests::test_cascade_ref_single_removal ... ok
test sql_engine::tests::varchar_255_boundary ... ok
test sql_engine::tests::update_with_compound_where_nonmatching_predicate_returns_affected_zero ... ok
test sql_engine::tests::zone_inference_by_sql_type ... ok
test sql_engine::tests::update_with_ifnull ... ok
test sql_engine::tests::update_with_in_clause_mixing_missing_and_valid_returns_affected_one ... ok
test sql_engine::tests::update_with_missing_id_returns_affected_zero ... ok
test sql_engine::tests::update_with_valid_id_still_affects_one_row ... ok
test sql_engine::tests::update_does_not_recompute_title_when_unrelated_column_changes has been running for over 60 seconds
test sql_engine::tests::update_does_not_recompute_title_when_unrelated_column_changes ... ok
test sql_engine::tests::update_with_id_from_different_table_returns_affected_zero ... ok
test sql_engine::tests::update_recomputes_title_when_ref_column_changes ... ok
test sql_engine::tests::update_with_explicit_title_takes_priority_over_template ... ok

test result: ok. 1546 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 952.78s
```
</details>

## Task 4: /private/tmp/claude-501/-Users-bob/fc24b46e-0bd9-4afb-9ed8-6447a550bda2/scratchpad/eval-prompts/task4-warden-env-danger.txt

Verify: `cd /private/tmp/claude-501/-Users-bob/fc24b46e-0bd9-4afb-9ed8-6447a550bda2/scratchpad/eval-worktrees/claude-warden && pnpm exec vitest run src/__tests__/env-danger.test.ts`

Gate exit code: 0 -> PASS

<details><summary>qwen-run.sh output</summary>

```
Using provider 'llamacpp8002' model 'unsloth/Qwen3.8-27B-GGUF:UD-Q6_K_XL'
[llama-cpp] failed to reach http://localhost:8080/v1/models: fetch failed
Done. Filled in `src/env-danger.ts` in the claude-warden worktree, keeping the three exported names:

- **`DANGEROUS_EXEC_ENV`** — `ReadonlySet` of exactly 16 names (library-injection: `LD_PRELOAD`, `LD_LIBRARY_PATH`, `DYLD_*`; git-exec: `PAGER`, `GIT_*`; startup hooks: `BASH_ENV`, `ENV`, `PROMPT_COMMAND`, `PERL5OPT`, `PYTHONSTARTUP`), built from a single `DANGEROUS_EXEC_ENV_NAMES` array so the set and regex can't drift.
- **`matchesDangerousEnv`** — splits on the **first** `=` only (so `GIT_SSH_COMMAND=ssh -o X=Y` works), exact set membership (so `ENVISIONED=x` and `NODE_ENV=x` → `null`), and `null` for tokens with no `=` or an empty name.
- **`DANGEROUS_EXEC_ENV_PATTERN`** — `(?<![A-Za-z0-9_])(?:<names>)=` : the lookbehind blocks `ENV` matching inside `NODE_ENV=`/`ENVISIONED=`, and the trailing `=` requirement rejects bare `PAGER`.

Verification: all 21 `env-danger` tests pass, `tsc --noEmit` clean, and the full suite (27 files, 1488 tests) passes — so the `evaluator.ts` and `defaults.ts` consumers are good.

One hiccup worth noting: my first draft had `LD_*/DYLD_*` inside the block comment, and the `*/` terminated the comment early — caught by the test run, fixed by spacing it.
```
</details>

<details><summary>verify command output</summary>

```

 RUN  v1.6.1 /private/tmp/claude-501/-Users-bob/fc24b46e-0bd9-4afb-9ed8-6447a550bda2/scratchpad/eval-worktrees/claude-warden

 ✓ src/__tests__/env-danger.test.ts  (21 tests) 1ms

 Test Files  1 passed (1)
      Tests  21 passed (21)
   Start at  17:08:50
   Duration  148ms (transform 18ms, setup 7ms, collect 8ms, tests 1ms, environment 0ms, prepare 35ms)
```
</details>

## Task 5: /private/tmp/claude-501/-Users-bob/fc24b46e-0bd9-4afb-9ed8-6447a550bda2/scratchpad/eval-prompts/task5-git-ferry-branch-diff-bats.txt

Verify: `cd /private/tmp/claude-501/-Users-bob/fc24b46e-0bd9-4afb-9ed8-6447a550bda2/scratchpad/eval-worktrees/claude-git-ferry && tests/lib/bats-core/bin/bats tests/branch-diff.bats`

Gate exit code: 0 -> PASS

<details><summary>qwen-run.sh output</summary>

```
Using provider 'llamacpp8002' model 'unsloth/Qwen3.8-27B-GGUF:UD-Q6_K_XL'
[llama-cpp] failed to reach http://localhost:8080/v1/models: fetch failed
Done. Created `tests/branch-diff.bats` — all 4 tests pass, each asserting both stdout and exit code:

```
ok 1 branch-diff: on master prints SKIP and exits 0
ok 2 branch-diff: feature branch prints info, stats, log, and diff sections
ok 3 branch-diff: detached HEAD prints SKIP and exits 0
ok 4 branch-diff: missing master base exits 1 with ERROR
```

Key details:

- **Follows repo conventions**: loads `helpers/common` (fresh temp git repo on `master` per test), uses `run bash "$SCRIPT"` with `$BATS_TEST_DIRNAME`-relative path, and test names match exactly what `tests/README.md` already documents for `branch-diff.sh` coverage.
- **on-master SKIP**: asserts `SKIP: On base branch (master), no branch diff needed` + exit 0 + no diff sections emitted.
- **feature-branch diff**: creates `feature/add-greeting` with a real file commit, and a `refs/remotes/origin/master` ref (via `update-ref`, same technique as `github-state.bats`) so the script takes the `origin/master` base path the README credits this test with. Asserts all six sections: fetch line, branch info (current/base/fork-point hash), changed files, `1 file changed, 1 insertion(+)`, commit subject, and the full diff (`new file mode 100644`, `+hello`) + exit 0.
- **detached HEAD**: `git checkout --detach`, asserts `SKIP: Detached HEAD state (commit <short-sha>)` with the dynamically computed short hash + exit 0.
- **missing base**: checks out a feature branch then deletes `refs/heads/master` so neither `origin/master` nor local `master` resolves; asserts `ERROR: Cannot find master branch` + exit 1.

One gotcha found while verifying: the script's echo prints `Fetching latest from ${BASE}...` (full `origin/master`), while only the `git fetch` arg strips the prefix — the assertion matches actual output.
```
</details>

<details><summary>verify command output</summary>

```
1..4
ok 1 branch-diff: on master prints SKIP and exits 0
ok 2 branch-diff: feature branch prints info, stats, log, and diff sections
ok 3 branch-diff: detached HEAD prints SKIP and exits 0
ok 4 branch-diff: missing master base exits 1 with ERROR
```
</details>

## Task 6: /private/tmp/claude-501/-Users-bob/fc24b46e-0bd9-4afb-9ed8-6447a550bda2/scratchpad/eval-prompts/task6-aegis-common-isatty.txt

Verify: `cd /private/tmp/claude-501/-Users-bob/fc24b46e-0bd9-4afb-9ed8-6447a550bda2/scratchpad/eval-worktrees/claude-aegis && python -m pytest hooks/tests/test__common.py -q`

Gate exit code: 0 -> PASS

<details><summary>qwen-run.sh output</summary>

```
Using provider 'llamacpp8002' model 'unsloth/Qwen3.8-27B-GGUF:UD-Q6_K_XL'
[llama-cpp] failed to reach http://localhost:8080/v1/models: fetch failed
Done. Summary:

**Change** — `hooks/_common.py`: added a TTY short-circuit at the top of `read_input()`:

```python
if sys.stdin.isatty():
    return {}
```

with a docstring note explaining that an interactively-invoked hook never blocks waiting on a terminal.

**Tests** — the test file `hooks/tests/test__common.py` already contained the TTY test (`test_returns_empty_dict_on_tty_without_reading`, whose fake stdin raises `AssertionError` if `read()` is ever called on a TTY); the implementation now satisfies it.

**Verification**
- `python -m pytest hooks/tests/ -q` → **227 passed, 28 subtests passed** (all eight hook test modules green)
- End-to-end: real piped JSON parses correctly; a TTY-like stdin returns `{}` without `read()` being called
```
</details>

<details><summary>verify command output</summary>

```
....                                                                     [100%]
4 passed in 0.00s
```
</details>

## Verdict

Score: 6/6 gate-passing. Verdict: PASS.

Zero-false-claims is NOT auto-verified above - read every transcript
marked **REVIEW** (and ideally all of them) before trusting this verdict.
