import unittest
import tempfile
import os
import parse_data

class TestParseData(unittest.TestCase):
    def setUp(self):
        self.mod_md = tempfile.NamedTemporaryFile(delete=False, mode='w', encoding='utf-8')
        self.exam_md = tempfile.NamedTemporaryFile(delete=False, mode='w', encoding='utf-8')
        
        # Write dummy mod md
        self.mod_md.write("| 1 | Modulbezeichnung<br>92345 | Human-centered mechatronics | 5 ECTS |\n")
        self.mod_md.write("| 2 | ...\n")
        self.mod_md.write("| 3 | Lehrende | Prof. Beckerle |\n")
        self.mod_md.write("| 4 | ...\n")
        self.mod_md.write("| 5 | Inhalt | This is a test description. |\n")
        self.mod_md.close()
        
        # Write dummy exam md
        self.exam_md.write("| Datum/Date | Nummer | Name | Prüfung | Dauer |\n")
        self.exam_md.write("| 20.07.2026 | 92345 | Prof. Beckerle | HCM | 60 Minuten |\n")
        self.exam_md.write("| 21.07.2026 | 11111 |  | Unknown Module | 90 Minuten |\n")
        self.exam_md.close()

    def tearDown(self):
        os.remove(self.mod_md.name)
        os.remove(self.exam_md.name)

    def test_parse_module_descriptions(self):
        mods = parse_data.parse_module_descriptions(self.mod_md.name)
        self.assertIn('92345', mods)
        self.assertEqual(mods['92345']['name'], 'Human-centered mechatronics')
        self.assertEqual(mods['92345']['ects'], 5.0)
        self.assertEqual(mods['92345']['professor'], 'Prof. Beckerle')
        self.assertEqual(mods['92345']['description'], 'This is a test description.')

    def test_parse_exam_dates(self):
        mods = parse_data.parse_module_descriptions(self.mod_md.name)
        mods = parse_data.parse_exam_dates(self.exam_md.name, mods)
        
        # Check existing module updated
        self.assertIn('92345', mods)
        self.assertEqual(mods['92345']['examDate'], '2026-07-20')
        
        # Check new module added from exam dates
        self.assertIn('11111', mods)
        self.assertEqual(mods['11111']['name'], 'Unknown Module')
        self.assertEqual(mods['11111']['examDate'], '2026-07-21')
        self.assertEqual(mods['11111']['professor'], 'N/A')
        self.assertEqual(mods['11111']['ects'], 5.0)

if __name__ == '__main__':
    unittest.main()
