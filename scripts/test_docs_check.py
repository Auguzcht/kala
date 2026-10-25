"""Policy regression fixtures; no live network, docs or runtime configuration."""
import tempfile
import unittest
from pathlib import Path

import docs_check as check


class DocsPolicyTests(unittest.TestCase):
    def audit_text(self, text, name='docs/features/example/README.md'):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
            return check.audit(root, [name])

    def test_current_operating_link_fails(self):
        result = self.audit_text('[required](../../archive/design.md)')
        self.assertEqual(result['counts']['record_link_violations'], 1)

    def test_historical_section_and_nested_subsection_pass(self):
        result = self.audit_text('## Historical sources\n### Older design\n[x](../../archive/a.md)')
        self.assertFalse(result['issues'])
        self.assertEqual(result['counts']['record_links'], 1)

    def test_next_peer_heading_resets_permission(self):
        result = self.audit_text('## Historical sources\n[x](../../archive/a.md)\n## Operation\n[y](../../archive/b.md)')
        self.assertEqual(result['counts']['record_link_violations'], 1)
        self.assertEqual(result['issues'][0]['line'], 4)

    def test_verified_heading_and_requirement_field_pass(self):
        result = self.audit_text('- Verified by: [proof](../../work/a/evidence/test.md)\n## Verified by\n[proof](../../work/a/evidence/test.md)')
        self.assertFalse(result['issues'])
        self.assertEqual(result['counts']['record_links'], 2)

    def test_verified_field_does_not_allow_following_lines(self):
        result = self.audit_text('- Verified by: test.py\n[operation](../../work/a/evidence/test.md)')
        self.assertEqual(result['counts']['record_link_violations'], 1)

    def test_reference_links_are_checked_at_use_not_definition(self):
        result = self.audit_text('[source]: ../../archive/a.md\n[operate][source]\n## Historical sources\n[source]')
        self.assertEqual(result['counts']['record_links'], 2)
        self.assertEqual(result['counts']['record_link_violations'], 1)
        self.assertEqual(result['issues'][0]['line'], 2)

    def test_html_and_encoded_and_nested_record_targets(self):
        result = self.audit_text('<a href="../../work/team/nested/evidence/check.md">proof</a>\n[x](../../%61rchive/a.md)')
        self.assertEqual(result['counts']['record_link_violations'], 2)

    def test_repository_hosted_url_is_not_a_bypass(self):
        result = self.audit_text('[x](https://example.com/repo/blob/main/docs/archive/a.md)')
        self.assertEqual(result['counts']['record_link_violations'], 1)

    def test_normalization_prevents_dot_segment_bypass(self):
        self.assertEqual(check.record_target('docs/README.md', 'engineering/../archive/a.md'), 'docs/archive/a.md')

    def test_fenced_and_inline_code_examples_are_not_links(self):
        result = self.audit_text('```md\n[x](../../archive/a.md)\n```\n`[x](../../archive/a.md)`')
        self.assertEqual(result['counts']['record_links'], 0)
        self.assertFalse(result['issues'])

    def test_work_item_and_current_spec_are_not_restricted_records(self):
        result = self.audit_text('[work](../../work/a/work-items/a.md)\n[current](../study/README.md)')
        self.assertFalse(result['issues'])

    def test_record_document_links_not_truth_layer(self):
        result = self.audit_text('[x](../../archive/a.md)', 'docs/work/a/README.md')
        self.assertFalse(result['issues'])

    def test_every_machine_path_family_and_encoded_paths_fail(self):
        result = self.audit_text('/Users/a/file /tmp/a /private/a ~/.codex/a /Applications/a /var/folders/a\n%2FUsers%2Fa%2Ffile')
        self.assertEqual(result['counts']['machine_local_path_violations'], 7)

    def test_marker_exempts_only_its_line_including_fenced_paths(self):
        result = self.audit_text('```text\n/tmp/old (local only, not retained)\n/private/new\n```')
        self.assertEqual(result['counts']['marked_local_only_paths'], 1)
        self.assertEqual(result['counts']['machine_local_path_violations'], 1)

    def test_relative_paths_and_normal_web_urls_pass(self):
        self.assertFalse(self.audit_text('[source](../../../apps/web/src/app/router.tsx)\nhttps://example.com/page')['issues'])

    def test_setext_section_resets_at_next_section(self):
        result = self.audit_text('Historical sources\n------------------\n[x](../../archive/a.md)\nOperate\n-------\n[x](../../archive/b.md)')
        self.assertEqual(result['counts']['record_links'], 2)
        self.assertEqual(result['counts']['record_link_violations'], 1)

    def test_non_markdown_text_document_paths_are_checked(self):
        result = self.audit_text('{"path": "/Users/example/file"}', 'docs/example.json')
        self.assertEqual(result['counts']['machine_local_path_violations'], 1)

    def test_agent_router_is_checked_but_other_root_readme_is_not(self):
        self.assertEqual(self.audit_text('[x](docs/archive/a.md)', 'AGENTS.md')['counts']['record_link_violations'], 1)
        self.assertEqual(self.audit_text('/tmp/test', 'README.md')['counts']['documentation_files'], 0)


if __name__ == '__main__':
    unittest.main()
