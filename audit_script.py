#!/usr/bin/env python3
"""
Скрипт аудита проекта TG-analiz для выявления файлов к удалению
"""
import os
import glob
from pathlib import Path
from typing import List, Dict

def scan_project() -> Dict[str, List[str]]:
    """Сканирует проект и определяет файлы для удаления"""
    root_dir = Path("/workspaces/TG-analiz")
    
    files_to_remove = {
        "duplicate_main": [],
        "duplicate_dockerfile": [],
        "duplicate_requirements": [],
        "backup_files": [],
        "outdated_docs": [],
        "config_duplicates": [],
        "other_clutter": []
    }
    
    # Сканируем все файлы
    for file_path in root_dir.rglob("*"):
        if file_path.is_file():
            filename = file_path.name
            relative_path = str(file_path.relative_to(root_dir))
            
            # Дублирующиеся main.py файлы
            if filename.startswith("main") and filename.endswith(".py") and filename != "main.py":
                files_to_remove["duplicate_main"].append(relative_path)
            
            # Бэкапы main.py
            if filename.startswith("main.py."):
                files_to_remove["backup_files"].append(relative_path)
            
            # Дублирующиеся Dockerfile
            if filename.startswith("Dockerfile") and filename != "Dockerfile":
                files_to_remove["duplicate_dockerfile"].append(relative_path)
            
            # Дублирующиеся requirements
            if filename.startswith("requirements") and filename != "requirements.txt":
                files_to_remove["duplicate_requirements"].append(relative_path)
            
            # Устаревшие документы
            if filename.endswith(".md"):
                if any(keyword in filename.lower() for keyword in 
                       ["old", "backup", "deploy", "fix", "critical", "troubleshooting", 
                        "setup", "railway", "gradual", "restore", "next_steps", "quick_start", "status"]):
                    files_to_remove["outdated_docs"].append(relative_path)
            
            # Procfile дублирующиеся
            if filename.startswith("Procfile") and filename != "Procfile":
                files_to_remove["config_duplicates"].append(relative_path)
            
            # Другие временные файлы
            if any(ext in filename for ext in [".backup", ".old", ".simple", ".ultra", ".minimal"]):
                if relative_path not in files_to_remove["backup_files"]:
                    files_to_remove["other_clutter"].append(relative_path)
    
    return files_to_remove

def generate_audit_report(files_to_remove: Dict[str, List[str]]) -> str:
    """Генерирует отчет аудита"""
    report = []
    report.append("# AUDIT REPORT - TG-analiz Repository Cleanup")
    report.append("## Generated: 2025-07-20")
    report.append("")
    
    total_files = sum(len(files) for files in files_to_remove.values())
    report.append(f"**Total files to remove: {total_files}**")
    report.append("")
    
    for category, files in files_to_remove.items():
        if files:
            report.append(f"### {category.replace('_', ' ').title()} ({len(files)} files)")
            report.append("")
            for file in sorted(files):
                report.append(f"- `{file}`")
            report.append("")
    
    return "\n".join(report)

if __name__ == "__main__":
    files_to_remove = scan_project()
    report = generate_audit_report(files_to_remove)
    
    # Сохраняем отчет
    with open("/workspaces/TG-analiz/AUDIT_REPORT.md", "w", encoding="utf-8") as f:
        f.write(report)
    
    print("✅ Audit report generated: AUDIT_REPORT.md")
    print(f"📊 Total files to remove: {sum(len(files) for files in files_to_remove.values())}")
