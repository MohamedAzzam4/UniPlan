import unittest
import tempfile
import os
import parse_data

class TestParseData(unittest.TestCase):
    def setUp(self):
        self.mod_md = tempfile.NamedTemporaryFile(delete=False, mode='w', encoding='utf-8')
        self.exam_md = tempfile.NamedTemporaryFile(delete=False, mode='w', encoding='utf-8')
        self.old_exam_md = tempfile.NamedTemporaryFile(delete=False, mode='w', encoding='utf-8')
        
        # mod_md content
        self.mod_md.write("| 1 | Modulbezeichnung<br>92345 | Human-centered mechatronics | 5 ECTS |\n")
        self.mod_md.write("| 1 | Modulbezeichnung<br>12345 | Machine Learning | 7,5 ECTS |\n")
        self.mod_md.write("| 3 | Lehrende | Prof. Beckerle |\n")
        
        # exam_md (2026) content
        self.exam_md.write("| Datum/Date | Nummer | Name | Prüfung | Dauer |\n")
        self.exam_md.write("| 20.07.2026 | 92345 | Prof. Beckerle | HCM | 60 Minuten |\n")
        self.exam_md.write("| 21.07.2026 | 11111 |  | Unknown Module | 90 Minuten |\n")
        
        # old_exam_md (2025) content
        self.old_exam_md.write("| pdatum | Rastertermin | pnr | pruefer_name | pltxt |\n")
        self.old_exam_md.write("| 28.07.2025 | W 1 T 1 | 92345 | Jürgen Frickel | FPGA-Entwurf |\n")
        self.old_exam_md.write("| 29.07.2025 | W 1 T 2 | 22222 | Max Mustermann | New Old Module |\n")
        self.old_exam_md.write("| 30.07.2025 | W 1 T 3 | 12345 | John Doe | Machine Learning |\n")
        self.old_exam_md.write("| invalid date | W 1 T 3 | 33333 | Jane Doe | Broken Date |\n")
        
        self.mod_md.close()
        self.exam_md.close()
        self.old_exam_md.close()

    def tearDown(self):
        os.remove(self.mod_md.name)
        os.remove(self.exam_md.name)
        os.remove(self.old_exam_md.name)

    # 1. Test parsing module descriptions basic
    def test_parse_module_descriptions_basic(self):
        mods = parse_data.parse_module_descriptions(self.mod_md.name)
        self.assertIn('92345', mods)
        self.assertEqual(mods['92345']['name'], 'Human-centered mechatronics')

    # 2. Test ECTS parsing with comma
    def test_parse_module_ects_comma(self):
        mods = parse_data.parse_module_descriptions(self.mod_md.name)
        self.assertEqual(mods['12345']['ects'], 7.5)

    # 3. Test missing file for module descriptions returns empty dict
    def test_parse_module_descriptions_missing_file(self):
        mods = parse_data.parse_module_descriptions("does_not_exist.md")
        self.assertEqual(mods, {})

    # 4. Test parsing 2026 exam dates attaches to existing
    def test_parse_exam_dates_existing(self):
        mods = parse_data.parse_module_descriptions(self.mod_md.name)
        mods = parse_data.parse_exam_dates(self.exam_md.name, mods)
        self.assertEqual(mods['92345']['examDate'], '2026-07-20')

    # 5. Test parsing 2026 exam dates adds new module if missing
    def test_parse_exam_dates_new_module(self):
        mods = parse_data.parse_exam_dates(self.exam_md.name, {})
        self.assertIn('11111', mods)
        self.assertEqual(mods['11111']['examDate'], '2026-07-21')

    # 6. Test missing file for 2026 exam dates returns same dict
    def test_parse_exam_dates_missing_file(self):
        mods = {'dummy': 'data'}
        res = parse_data.parse_exam_dates("does_not_exist.md", mods)
        self.assertEqual(res, mods)

    # 7. Test old exam dates missing file returns same dict
    def test_parse_old_exam_dates_missing_file(self):
        mods = {'dummy': 'data'}
        res = parse_data.parse_expected_exam_dates("does_not_exist.md", mods)
        self.assertEqual(res, mods)

    # 8. Test old exam dates attaches expectedExamDate to existing module
    def test_parse_old_exam_dates_existing(self):
        mods = parse_data.parse_module_descriptions(self.mod_md.name)
        mods = parse_data.parse_expected_exam_dates(self.old_exam_md.name, mods)
        self.assertEqual(mods['92345']['expectedExamDate'], '2026-07-28')

    # 9. Test old exam dates shifts year from 2025 to 2026
    def test_parse_old_exam_dates_year_shift(self):
        mods = parse_data.parse_expected_exam_dates(self.old_exam_md.name, {})
        self.assertEqual(mods['22222']['expectedExamDate'], '2026-07-29')

    # 10. Test old exam dates adds new module if missing
    def test_parse_old_exam_dates_new_module(self):
        mods = parse_data.parse_expected_exam_dates(self.old_exam_md.name, {})
        self.assertIn('22222', mods)
        self.assertEqual(mods['22222']['name'], 'New Old Module')

    # 11. Test old exam dates sets default ECTS for new module
    def test_parse_old_exam_dates_default_ects(self):
        mods = parse_data.parse_expected_exam_dates(self.old_exam_md.name, {})
        self.assertEqual(mods['22222']['ects'], 5.0)

    # 12. Test old exam dates ignores rows without correct date format
    def test_parse_old_exam_dates_invalid_date(self):
        mods = parse_data.parse_expected_exam_dates(self.old_exam_md.name, {})
        self.assertNotIn('33333', mods)

    # 13. Test integration: module gets both expected and confirmed dates
    def test_integration_both_dates(self):
        mods = parse_data.parse_module_descriptions(self.mod_md.name)
        mods = parse_data.parse_expected_exam_dates(self.old_exam_md.name, mods)
        mods = parse_data.parse_exam_dates(self.exam_md.name, mods)
        self.assertEqual(mods['92345']['expectedExamDate'], '2026-07-28')
        self.assertEqual(mods['92345']['examDate'], '2026-07-20')

    # 14. Test integration: professor name overrides "N/A"
    def test_integration_prof_override(self):
        mods = parse_data.parse_expected_exam_dates(self.old_exam_md.name, {})
        # Should set prof to Max Mustermann
        self.assertEqual(mods['22222']['professor'], 'Max Mustermann')

    # 15. Test integration: professor name from module descriptions stays intact
    def test_integration_prof_preservation(self):
        mods = parse_data.parse_module_descriptions(self.mod_md.name)
        mods['12345']['professor'] = 'Prof. Known'
        mods = parse_data.parse_expected_exam_dates(self.old_exam_md.name, mods)
        # Should not be overwritten by "John Doe"
        self.assertEqual(mods['12345']['professor'], 'Prof. Known')

if __name__ == '__main__':
    unittest.main()
