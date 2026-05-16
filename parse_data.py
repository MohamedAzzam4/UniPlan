import re
import json
import sys
import os

def parse_module_descriptions(file_path):
    modules = {}
    if not os.path.exists(file_path):
        return modules
        
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    current_module_id = None
    
    for line in lines:
        # Check for Module definition
        # e.g. | 1 | Modulbezeichnung<br>92345 | Human-centered mechatronics and robotics | 5 ECTS |
        m_id_match = re.search(r'\|\s*1\s*\|\s*(?:Modulbezeichnung|Module name)(?:<br>|\s+)(\d+)\s*\|\s*([^|]+)\s*\|(?:\s*([\d,]+)\s*ECTS\s*\|)?', line)
        if m_id_match:
            mod_id = m_id_match.group(1).strip()
            name_raw = m_id_match.group(2).strip()
            # Handle potential markdown artifacts in name
            name = re.sub(r'<br>.*', '', name_raw).strip()
            
            ects_raw = m_id_match.group(3) if m_id_match.group(3) else "5"
            ects = float(ects_raw.replace(',', '.'))
            
            current_module_id = mod_id
            modules[current_module_id] = {
                "id": current_module_id,
                "name": name,
                "ects": ects,
                "professor": "N/A",
                "description": "",
                "hasLectures": True,
                "pillar": "General",
                "type": "Module",
                "examDate": "",
                "defaultDifficulty": "Medium"
            }
            continue
            
        if current_module_id:
            # Parse Lecturer
            if '| 3 |' in line and ('Lehrende' in line or 'Lecturers' in line):
                prof_match = re.search(r'\|\s*3\s*\|\s*(?:Lehrende|Lecturers)\s*\|\s*(.*?)\s*\|', line)
                if prof_match:
                    prof_name = prof_match.group(1).replace('<br>', ', ').strip()
                    if prof_name and "No lecturers available" not in prof_name:
                        modules[current_module_id]["professor"] = prof_name
            # Parse Description
            if '| 5 |' in line and ('Inhalt' in line or 'Contents' in line):
                desc_match = re.search(r'\|\s*5\s*\|\s*(?:Inhalt|Contents)\s*\|\s*(.*?)\s*\|', line)
                if desc_match:
                    desc_text = desc_match.group(1).replace('<br>', ' ').strip()
                    modules[current_module_id]["description"] = desc_text
                    
    return modules

def parse_exam_dates(file_path, modules):
    if not os.path.exists(file_path):
        return modules
        
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    for line in lines:
        # e.g. | 20.07.2026 | 76791 | Claudio Castellini | Advanced Upper-Limb Prosthetics | 60 Minuten |
        match = re.search(r'\|\s*(\d{2}\.\d{2}\.\d{4})\s*\|\s*(\d+)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|', line)
        if match:
            date_str = match.group(1)
            mod_id = match.group(2)
            prof = match.group(3).strip()
            name = match.group(4).strip()
            
            d, m, y = date_str.split('.')
            iso_date = f"{y}-{m}-{d}"
            
            if mod_id in modules:
                modules[mod_id]["examDate"] = iso_date
                if prof and modules[mod_id]["professor"] == "N/A":
                    modules[mod_id]["professor"] = prof
            else:
                modules[mod_id] = {
                    "id": mod_id,
                    "name": name,
                    "ects": 5.0, # Defaulting to 5 if not found in module desc
                    "professor": prof if prof else "N/A",
                    "description": "",
                    "hasLectures": True,
                    "pillar": "General",
                    "type": "Module",
                    "examDate": iso_date,
                    "defaultDifficulty": "Medium"
                }
    return modules

def parse_expected_exam_dates(file_path, modules):
    if not os.path.exists(file_path):
        return modules
        
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    for line in lines:
        # e.g. | 28.07.2025 | W 1 T 1 | 914513 | Jürgen Frickel | FPGA-Entwurf mit VHDL |
        match = re.search(r'\|\s*(\d{2}\.\d{2}\.\d{4})\s*\|\s*(.*?)\s*\|\s*(\d+)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|', line)
        if match:
            date_str = match.group(1)
            # group(2) is rastertermin, ignore
            mod_id = match.group(3)
            prof = match.group(4).strip()
            name = match.group(5).strip()
            
            d, m, y = date_str.split('.')
            # Shift the year to 2026 for timeline plotting as requested by user
            iso_date = f"2026-{m}-{d}"
            
            if mod_id in modules:
                modules[mod_id]["expectedExamDate"] = iso_date
                if prof and modules[mod_id]["professor"] == "N/A":
                    modules[mod_id]["professor"] = prof
            else:
                modules[mod_id] = {
                    "id": mod_id,
                    "name": name,
                    "ects": 5.0, # Defaulting to 5
                    "professor": prof if prof else "N/A",
                    "description": "",
                    "hasLectures": True,
                    "pillar": "General",
                    "type": "Module",
                    "expectedExamDate": iso_date,
                    "defaultDifficulty": "Medium"
                }
    return modules

def parse_toc_metadata(file_path, modules):
    current_pillar = "General"
    current_type = "Module"
    
    if not os.path.exists(file_path):
        return modules
        
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    in_toc = False
    for line in lines:
        if 'Table of contents' in line:
            in_toc = True
            continue
            
        if in_toc:
            if '<span id=' in line:
                break
                
            cat_match = re.search(r'\|\s*(.*?)\s*-\s*(core modules?|specialization module|Seminar & laboratory)\s*\|', line, re.I)
            if cat_match:
                current_pillar = cat_match.group(1).strip()
                t = cat_match.group(2).strip().lower()
                if 'core' in t:
                    current_type = 'Core'
                elif 'specialization' in t:
                    current_type = 'Elective'
                elif 'seminar' in t:
                    current_type = 'Seminar'
                continue
                
            mod_match = re.search(r'\|\s*.*?\((\d+)\).*?\|', line)
            if mod_match:
                mod_id = mod_match.group(1).strip()
                if mod_id in modules:
                    modules[mod_id]['pillar'] = current_pillar
                    modules[mod_id]['type'] = current_type
    
    return modules

def generate_courses_js(modules, output_path):
    data = list(modules.values())
    js_content = f"const COURSE_DATA = {json.dumps(data, indent=2, ensure_ascii=False)};"
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(js_content)

if __name__ == "__main__":
    if len(sys.argv) < 5:
        print("Usage: python parse_data.py <module_md> <exam_md> <old_exam_md> <output_js>")
        sys.exit(1)
    
    mod_path = sys.argv[1]
    exam_path = sys.argv[2]
    old_exam_path = sys.argv[3]
    out_path = sys.argv[4]
    
    mods = parse_module_descriptions(mod_path)
    mods = parse_toc_metadata(mod_path, mods)
    mods = parse_expected_exam_dates(old_exam_path, mods)
    mods = parse_exam_dates(exam_path, mods)
    generate_courses_js(mods, out_path)
    print(f"Successfully exported {len(mods)} modules to {out_path}")
