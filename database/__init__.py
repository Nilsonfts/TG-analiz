# Database package - экспортируем Database класс из основного файла
import os
import sys

# Добавляем путь к корневой директории в sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

try:
    from database import Database
except ImportError:
    # Если не получается импортировать, пытаемся через абсолютный путь
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "database",
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "database.py"),
    )
    database_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(database_module)
    Database = database_module.Database

__all__ = ["Database"]
