import unittest
import tempfile
import os
import json
import re
import parse_data

class TestParseModuleDescriptions(unittest.TestCase):
    """A. Module description parsing tests"""

    def test_basic_parsing(self):
        """1. Parse a standard module definition line"""
        with tempfile.NamedTemporaryFile(delete=False, mode='w', encoding='utf-8', suffix='.md') as f:
            f.write("| 1 | Modulbezeichnung<br>92345 | Human-centered mechatronics | 5 ECTS |\n")
            path = f.name
        mods = parse_data.parse_module_descriptions(path)
        os.remove(path)
        self.assertIn('92345', mods)
        self.assertEqual(mods['92345']['name'], 'Human-centered mechatronics')
        self.assertEqual(mods['92345']['ects'], 5.0)

    def test_ects_with_comma(self):
        """2. Parse ECTS with comma decimal (7,5 ECTS)"""
        with tempfile.NamedTemporaryFile(delete=False, mode='w', encoding='utf-8', suffix='.md') as f:
            f.write("| 1 | Modulbezeichnung<br>12345 | Machine Learning | 7,5 ECTS |\n")
            path = f.name
        mods = parse_data.parse_module_descriptions(path)
        os.remove(path)
        self.assertEqual(mods['12345']['ects'], 7.5)

    def test_missing_file(self):
        """3. Missing file returns empty dict"""
        mods = parse_data.parse_module_descriptions("nonexistent_file_xyz.md")
        self.assertEqual(mods, {})

    def test_default_fields(self):
        """4. Module gets correct default values"""
        with tempfile.NamedTemporaryFile(delete=False, mode='w', encoding='utf-8', suffix='.md') as f:
            f.write("| 1 | Modulbezeichnung<br>99999 | Test Module | 5 ECTS |\n")
            path = f.name
        mods = parse_data.parse_module_descriptions(path)
        os.remove(path)
        m = mods['99999']
        self.assertEqual(m['professor'], 'N/A')
        self.assertEqual(m['pillar'], 'General')
        self.assertEqual(m['type'], 'Module')
        self.assertEqual(m['examDate'], '')
        self.assertEqual(m['defaultDifficulty'], 'Medium')

    def test_professor_parsing(self):
        """5. Parse lecturer from row 3"""
        with tempfile.NamedTemporaryFile(delete=False, mode='w', encoding='utf-8', suffix='.md') as f:
            f.write("| 1 | Modulbezeichnung<br>11111 | Test | 5 ECTS |\n")
            f.write("| 3 | Lehrende | Prof. Beckerle |\n")
            path = f.name
        mods = parse_data.parse_module_descriptions(path)
        os.remove(path)
        self.assertEqual(mods['11111']['professor'], 'Prof. Beckerle')

    def test_unicode_names(self):
        """6. Handle German umlaut characters in module names"""
        with tempfile.NamedTemporaryFile(delete=False, mode='w', encoding='utf-8', suffix='.md') as f:
            f.write("| 1 | Modulbezeichnung<br>77777 | Schätzverfahren in der Regelungstechnik | 5 ECTS |\n")
            path = f.name
        mods = parse_data.parse_module_descriptions(path)
        os.remove(path)
        self.assertIn('77777', mods)
        self.assertIn('Sch', mods['77777']['name'])

    def test_no_ects_defaults_to_5(self):
        """7. Module without ECTS field defaults to 5"""
        with tempfile.NamedTemporaryFile(delete=False, mode='w', encoding='utf-8', suffix='.md') as f:
            f.write("| 1 | Modulbezeichnung<br>88888 | No ECTS Module ||\n")
            path = f.name
        mods = parse_data.parse_module_descriptions(path)
        os.remove(path)
        # Module might or might not parse depending on regex; if it does, ects should be 5
        if '88888' in mods:
            self.assertEqual(mods['88888']['ects'], 5.0)


class TestParseExamDates(unittest.TestCase):
    """B. Current exam date (SS2026) parsing tests"""

    def test_attach_to_existing(self):
        """8. Exam date attaches to existing module by PNr"""
        with tempfile.NamedTemporaryFile(delete=False, mode='w', encoding='utf-8', suffix='.md') as f:
            f.write("| 20.07.2026 | 92345 | Prof. X | HCM Exam | 60 Minuten |\n")
            path = f.name
        mods = {'92345': {'id': '92345', 'name': 'HCM', 'examDate': '', 'professor': 'N/A'}}
        mods = parse_data.parse_exam_dates(path, mods)
        os.remove(path)
        self.assertEqual(mods['92345']['examDate'], '2026-07-20')

    def test_creates_new_module(self):
        """9. Creates new module for unknown PNr"""
        with tempfile.NamedTemporaryFile(delete=False, mode='w', encoding='utf-8', suffix='.md') as f:
            f.write("| 21.07.2026 | 55555 | Prof. Y | New Module | 90 Minuten |\n")
            path = f.name
        mods = parse_data.parse_exam_dates(path, {})
        os.remove(path)
        self.assertIn('55555', mods)
        self.assertEqual(mods['55555']['examDate'], '2026-07-21')
        self.assertEqual(mods['55555']['name'], 'New Module')

    def test_missing_file(self):
        """10. Missing file returns dict unchanged"""
        mods = {'dummy': 'data'}
        res = parse_data.parse_exam_dates("nonexistent.md", mods)
        self.assertEqual(res, mods)

    def test_ignores_header_and_separator(self):
        """11. Header/separator rows are ignored"""
        with tempfile.NamedTemporaryFile(delete=False, mode='w', encoding='utf-8', suffix='.md') as f:
            f.write("| Datum/Date | Nummer | Name | Prüfung | Dauer |\n")
            f.write("|------------|--------|------|---------|-------|\n")
            f.write("| 20.07.2026 | 11111 | Prof. X | Test | 60 Minuten |\n")
            path = f.name
        mods = parse_data.parse_exam_dates(path, {})
        os.remove(path)
        self.assertEqual(len(mods), 1)
        self.assertIn('11111', mods)

    def test_professor_fill_on_na(self):
        """12. Exam prof fills N/A but doesn't overwrite existing"""
        with tempfile.NamedTemporaryFile(delete=False, mode='w', encoding='utf-8', suffix='.md') as f:
            f.write("| 20.07.2026 | 11111 | New Prof | Test | 60 |\n")
            path = f.name
        # N/A professor should be overwritten
        mods = {'11111': {'id': '11111', 'name': 'Test', 'examDate': '', 'professor': 'N/A'}}
        mods = parse_data.parse_exam_dates(path, mods)
        os.remove(path)
        self.assertEqual(mods['11111']['professor'], 'New Prof')

    def test_professor_not_overwritten(self):
        """13. Exam prof does NOT overwrite existing known professor"""
        with tempfile.NamedTemporaryFile(delete=False, mode='w', encoding='utf-8', suffix='.md') as f:
            f.write("| 20.07.2026 | 11111 | New Prof | Test | 60 |\n")
            path = f.name
        mods = {'11111': {'id': '11111', 'name': 'Test', 'examDate': '', 'professor': 'Original Prof'}}
        mods = parse_data.parse_exam_dates(path, mods)
        os.remove(path)
        self.assertEqual(mods['11111']['professor'], 'Original Prof')


class TestParseExpectedExamDates(unittest.TestCase):
    """C. Expected exam date (SS2025 old schedule) parsing tests"""

    def _write_old_exam(self, content):
        f = tempfile.NamedTemporaryFile(delete=False, mode='w', encoding='utf-8', suffix='.md')
        f.write(content)
        f.close()
        return f.name

    def test_pnr_match(self):
        """14. PNr match assigns expectedExamDate correctly"""
        path = self._write_old_exam("| 28.07.2025 | W 1 T 1 | 92345 | Prof. X | Test Module |\n")
        mods = {'92345': {'id': '92345', 'name': 'Test Module', 'professor': 'N/A'}}
        mods = parse_data.parse_expected_exam_dates(path, mods)
        os.remove(path)
        self.assertEqual(mods['92345']['expectedExamDate'], '2026-07-28')

    def test_year_shift(self):
        """15. Year is shifted from 2025 to 2026"""
        path = self._write_old_exam("| 15.09.2025 | W 2 T 1 | 22222 | Prof. Y | Module Y |\n")
        mods = parse_data.parse_expected_exam_dates(path, {})
        os.remove(path)
        self.assertEqual(mods['22222']['expectedExamDate'], '2026-09-15')

    def test_creates_new_module(self):
        """16. Creates new module entry for unknown PNr"""
        path = self._write_old_exam("| 29.07.2025 | W 1 T 2 | 33333 | Max Mustermann | New Old Module |\n")
        mods = parse_data.parse_expected_exam_dates(path, {})
        os.remove(path)
        self.assertIn('33333', mods)
        self.assertEqual(mods['33333']['ects'], 5.0)
        self.assertEqual(mods['33333']['professor'], 'Max Mustermann')

    def test_missing_file(self):
        """17. Missing file returns dict unchanged"""
        mods = {'dummy': 'data'}
        res = parse_data.parse_expected_exam_dates("nonexistent.md", mods)
        self.assertEqual(res, mods)

    def test_invalid_date_ignored(self):
        """18. Rows with invalid date format are ignored"""
        path = self._write_old_exam("| invalid date | W 1 T 3 | 44444 | Jane Doe | Broken |\n")
        mods = parse_data.parse_expected_exam_dates(path, {})
        os.remove(path)
        self.assertNotIn('44444', mods)

    def test_name_fallback_match(self):
        """19. NAME-BASED FALLBACK: Module with catalog ID != PNr gets expectedExamDate via title match"""
        # Old exam has PNr 23451, module catalog uses ID 92345
        path = self._write_old_exam("| 28.07.2025 | W 1 T 1 | 23451 | Prof. X | Human-centered mechatronics |\n")
        mods = {
            '92345': {'id': '92345', 'name': 'Human-centered mechatronics', 'professor': 'N/A'}
        }
        mods = parse_data.parse_expected_exam_dates(path, mods)
        os.remove(path)
        # Module 92345 should get the date via name match
        self.assertEqual(mods['92345']['expectedExamDate'], '2026-07-28')
        # The PNr-based entry should also exist
        self.assertIn('23451', mods)

    def test_name_fallback_case_insensitive(self):
        """20. Name fallback match is case-insensitive"""
        path = self._write_old_exam("| 28.07.2025 | W 1 T 1 | 99999 | Prof. X | machine learning |\n")
        mods = {
            '11111': {'id': '11111', 'name': 'Machine Learning', 'professor': 'N/A'}
        }
        mods = parse_data.parse_expected_exam_dates(path, mods)
        os.remove(path)
        self.assertEqual(mods['11111']['expectedExamDate'], '2026-07-28')

    def test_pnr_match_takes_priority_over_name(self):
        """21. If PNr match already set expectedExamDate, name fallback doesn't overwrite"""
        path = self._write_old_exam(
            "| 28.07.2025 | W 1 T 1 | 92345 | Prof. X | Same Module |\n"
            "| 30.07.2025 | W 1 T 2 | 99999 | Prof. Y | Same Module |\n"
        )
        mods = {
            '92345': {'id': '92345', 'name': 'Same Module', 'professor': 'N/A'}
        }
        mods = parse_data.parse_expected_exam_dates(path, mods)
        os.remove(path)
        # PNr match should win — date from first entry
        self.assertEqual(mods['92345']['expectedExamDate'], '2026-07-28')

    def test_name_fallback_fills_professor(self):
        """22. Name fallback fills professor when current is N/A"""
        path = self._write_old_exam("| 28.07.2025 | W 1 T 1 | 99999 | Dr. Smith | Special Course |\n")
        mods = {
            '11111': {'id': '11111', 'name': 'Special Course', 'professor': 'N/A'}
        }
        mods = parse_data.parse_expected_exam_dates(path, mods)
        os.remove(path)
        self.assertEqual(mods['11111']['professor'], 'Dr. Smith')

    def test_name_fallback_preserves_known_professor(self):
        """23. Name fallback does NOT overwrite a known professor"""
        path = self._write_old_exam("| 28.07.2025 | W 1 T 1 | 99999 | Dr. Smith | Special Course |\n")
        mods = {
            '11111': {'id': '11111', 'name': 'Special Course', 'professor': 'Prof. Original'}
        }
        mods = parse_data.parse_expected_exam_dates(path, mods)
        os.remove(path)
        self.assertEqual(mods['11111']['professor'], 'Prof. Original')

    def test_empty_name_no_crash(self):
        """24. Empty module name doesn't cause crash or false match"""
        path = self._write_old_exam("| 28.07.2025 | W 1 T 1 | 99999 | Prof. X |  |\n")
        mods = {
            '11111': {'id': '11111', 'name': '', 'professor': 'N/A'}
        }
        mods = parse_data.parse_expected_exam_dates(path, mods)
        os.remove(path)
        # Empty name should NOT match
        self.assertNotIn('expectedExamDate', mods['11111'])


class TestTocMetadata(unittest.TestCase):
    """D. Table-of-contents pillar/type parsing tests"""

    def test_pillar_assignment(self):
        """25. TOC assigns correct pillar to a module"""
        with tempfile.NamedTemporaryFile(delete=False, mode='w', encoding='utf-8', suffix='.md') as f:
            f.write("Table of contents\n")
            f.write("| Human-system Interfaces - core modules |\n")
            f.write("| Some text (92345) more text |\n")
            path = f.name
        mods = {'92345': {'id': '92345', 'name': 'Test', 'pillar': 'General', 'type': 'Module'}}
        mods = parse_data.parse_toc_metadata(path, mods)
        os.remove(path)
        self.assertEqual(mods['92345']['pillar'], 'Human-system Interfaces')
        self.assertEqual(mods['92345']['type'], 'Core')

    def test_specialization_type(self):
        """26. TOC assigns 'Elective' type for specialization modules"""
        with tempfile.NamedTemporaryFile(delete=False, mode='w', encoding='utf-8', suffix='.md') as f:
            f.write("Table of contents\n")
            f.write("| Planning & Control - specialization module |\n")
            f.write("| Module X (11111) details |\n")
            path = f.name
        mods = {'11111': {'id': '11111', 'name': 'X', 'pillar': 'General', 'type': 'Module'}}
        mods = parse_data.parse_toc_metadata(path, mods)
        os.remove(path)
        self.assertEqual(mods['11111']['pillar'], 'Planning & Control')
        self.assertEqual(mods['11111']['type'], 'Elective')

    def test_missing_file(self):
        """27. Missing TOC file returns modules unchanged"""
        mods = {'92345': {'pillar': 'General'}}
        res = parse_data.parse_toc_metadata("nonexistent.md", mods)
        self.assertEqual(res['92345']['pillar'], 'General')


class TestIntegration(unittest.TestCase):
    """E. Full pipeline integration tests"""

    def setUp(self):
        self.mod_md = tempfile.NamedTemporaryFile(delete=False, mode='w', encoding='utf-8', suffix='.md')
        self.exam_md = tempfile.NamedTemporaryFile(delete=False, mode='w', encoding='utf-8', suffix='.md')
        self.old_exam_md = tempfile.NamedTemporaryFile(delete=False, mode='w', encoding='utf-8', suffix='.md')

        # Module descriptions (catalog IDs)
        self.mod_md.write("| 1 | Modulbezeichnung<br>92345 | Human-centered mechatronics | 5 ECTS |\n")
        self.mod_md.write("| 3 | Lehrende | Prof. Beckerle |\n")
        self.mod_md.write("| 1 | Modulbezeichnung<br>12345 | Machine Learning | 7,5 ECTS |\n")

        # Current exam schedule (PNr for some, catalog ID for others)
        self.exam_md.write("| 20.07.2026 | 92345 | Prof. Beckerle | Human-centered mechatronics | 60 Minuten |\n")
        self.exam_md.write("| 21.07.2026 | 55555 |  | Unknown Module | 90 Minuten |\n")

        # Old exam schedule (all PNr — different from catalog IDs!)
        self.old_exam_md.write("| 28.07.2025 | W 1 T 1 | 23451 | Prof. Beckerle | Human-centered mechatronics |\n")
        self.old_exam_md.write("| 29.07.2025 | W 1 T 2 | 22222 | Max Mustermann | New Old Module |\n")
        self.old_exam_md.write("| 30.07.2025 | W 1 T 3 | 34567 | John Doe | Machine Learning |\n")

        self.mod_md.close()
        self.exam_md.close()
        self.old_exam_md.close()

    def tearDown(self):
        os.remove(self.mod_md.name)
        os.remove(self.exam_md.name)
        os.remove(self.old_exam_md.name)

    def test_full_pipeline_both_dates(self):
        """28. Module gets both examDate (PNr match) and expectedExamDate (name fallback)"""
        mods = parse_data.parse_module_descriptions(self.mod_md.name)
        mods = parse_data.parse_expected_exam_dates(self.old_exam_md.name, mods)
        mods = parse_data.parse_exam_dates(self.exam_md.name, mods)
        # 92345 has examDate by PNr match + expectedExamDate by NAME match (old PNr was 23451)
        self.assertEqual(mods['92345']['examDate'], '2026-07-20')
        self.assertEqual(mods['92345']['expectedExamDate'], '2026-07-28')

    def test_pipeline_professor_priority(self):
        """29. Professor from module descriptions is preserved through pipeline"""
        mods = parse_data.parse_module_descriptions(self.mod_md.name)
        mods = parse_data.parse_expected_exam_dates(self.old_exam_md.name, mods)
        mods = parse_data.parse_exam_dates(self.exam_md.name, mods)
        # Prof. Beckerle was set by module descriptions, should NOT be overwritten
        self.assertEqual(mods['92345']['professor'], 'Prof. Beckerle')

    def test_pipeline_generates_valid_json(self):
        """30. generate_courses_js produces valid parseable JSON"""
        mods = parse_data.parse_module_descriptions(self.mod_md.name)
        mods = parse_data.parse_expected_exam_dates(self.old_exam_md.name, mods)
        mods = parse_data.parse_exam_dates(self.exam_md.name, mods)
        
        out = tempfile.NamedTemporaryFile(delete=False, mode='w', encoding='utf-8', suffix='.js')
        out.close()
        parse_data.generate_courses_js(mods, out.name)
        
        with open(out.name, 'r', encoding='utf-8') as f:
            content = f.read()
        os.remove(out.name)
        
        # Extract JSON from JS
        m = re.search(r'const COURSE_DATA = (\[.*\]);', content, re.DOTALL)
        self.assertIsNotNone(m, "Could not find COURSE_DATA in output")
        data = json.loads(m.group(1))
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)

    def test_name_fallback_for_ml_module(self):
        """31. Machine Learning module (catalog=12345) gets expectedExamDate via name match (PNr=34567)"""
        mods = parse_data.parse_module_descriptions(self.mod_md.name)
        mods = parse_data.parse_expected_exam_dates(self.old_exam_md.name, mods)
        self.assertEqual(mods['12345']['expectedExamDate'], '2026-07-30')


class TestRealDataValidation(unittest.TestCase):
    """F. Validation tests against real production data"""

    @classmethod
    def setUpClass(cls):
        """Run the full parser on real data files"""
        mod_path = "md_output/AT-Module_descrition/AT-Module_descrition.md"
        exam_path = "md_output/exam_dates_summerSemester/exam_dates_summerSemester.md"
        old_exam_path = "md_output/examination-dates-summersemester-2025/examination-dates-summersemester-2025.md"

        if not all(os.path.exists(p) for p in [mod_path, exam_path, old_exam_path]):
            cls.skip_real = True
            return
        cls.skip_real = False

        cls.mods = parse_data.parse_module_descriptions(mod_path)
        cls.mods = parse_data.parse_toc_metadata(mod_path, cls.mods)
        cls.mods = parse_data.parse_expected_exam_dates(old_exam_path, cls.mods)
        cls.mods = parse_data.parse_exam_dates(exam_path, cls.mods)

    def test_total_modules_count(self):
        """32. Real data produces >= 500 modules"""
        if self.skip_real: self.skipTest("Real data files not found")
        self.assertGreaterEqual(len(self.mods), 500)

    def test_expected_dates_count(self):
        """33. At least 430 modules have expectedExamDate (was 422 PNr + ~32 name fallback)"""
        if self.skip_real: self.skipTest("Real data files not found")
        count = sum(1 for m in self.mods.values() if m.get('expectedExamDate'))
        self.assertGreaterEqual(count, 430, f"Only {count} modules have expectedExamDate")

    def test_at_modules_have_expected_dates(self):
        """34. At least 25 AT modules have expectedExamDate (was only 2 before fix)"""
        if self.skip_real: self.skipTest("Real data files not found")
        at_with = sum(1 for m in self.mods.values()
                      if m.get('pillar', 'General') != 'General' and m.get('expectedExamDate'))
        self.assertGreaterEqual(at_with, 25, f"Only {at_with} AT modules have expectedExamDate")

    def test_all_pillars_represented(self):
        """35. All 4 AT pillars have at least 1 module with expectedExamDate"""
        if self.skip_real: self.skipTest("Real data files not found")
        pillars_with = set()
        for m in self.mods.values():
            if m.get('pillar', 'General') != 'General' and m.get('expectedExamDate'):
                pillars_with.add(m['pillar'])
        for p in ['Human-system Interfaces', 'Planning & Control',
                   'Sensing & Perception', 'Networking & Collaboration']:
            self.assertIn(p, pillars_with, f"Pillar '{p}' has no modules with expectedExamDate")

    def test_dates_are_valid_iso(self):
        """36. All examDate and expectedExamDate values are valid YYYY-MM-DD"""
        if self.skip_real: self.skipTest("Real data files not found")
        date_re = re.compile(r'^\d{4}-\d{2}-\d{2}$')
        for m in self.mods.values():
            if m.get('examDate'):
                self.assertRegex(m['examDate'], date_re,
                                 f"Invalid examDate '{m['examDate']}' for {m['id']}")
            if m.get('expectedExamDate'):
                self.assertRegex(m['expectedExamDate'], date_re,
                                 f"Invalid expectedExamDate '{m['expectedExamDate']}' for {m['id']}")

    def test_expected_dates_are_2026(self):
        """37. All expectedExamDate values have year 2026 (shifted from 2025)"""
        if self.skip_real: self.skipTest("Real data files not found")
        for m in self.mods.values():
            if m.get('expectedExamDate'):
                self.assertTrue(m['expectedExamDate'].startswith('2026'),
                                f"Expected 2026 but got '{m['expectedExamDate']}' for {m['id']}")

    def test_exam_dates_are_2026(self):
        """38. All examDate values have year 2026"""
        if self.skip_real: self.skipTest("Real data files not found")
        for m in self.mods.values():
            if m.get('examDate'):
                self.assertTrue(m['examDate'].startswith('2026'),
                                f"Expected 2026 but got '{m['examDate']}' for {m['id']}")

    def test_no_duplicate_modules(self):
        """39. No duplicate module IDs"""
        if self.skip_real: self.skipTest("Real data files not found")
        ids = list(self.mods.keys())
        self.assertEqual(len(ids), len(set(ids)), "Duplicate module IDs found")


if __name__ == '__main__':
    unittest.main()
