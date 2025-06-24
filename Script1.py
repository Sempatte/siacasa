#!/usr/bin/env python3
"""
Script para generar el árbol de directorios del proyecto SIACASA
Ejecutar desde la raíz del proyecto: python generate_tree.py
"""

import os
from pathlib import Path

def should_ignore(name):
    """Define qué archivos/carpetas ignorar"""
    ignore_patterns = {
        # Directorios comunes a ignorar
        '__pycache__', '.git', '.pytest_cache', '.vscode', '.idea',
        'node_modules', '.env', 'venv', 'env', '.venv',
        # Archivos específicos
        '.gitignore', '.DS_Store', 'Thumbs.db', '*.pyc', '*.pyo',
        # Logs y temporales
        'logs', '*.log', 'temp', 'tmp',
        # Build/dist
        'build', 'dist', '*.egg-info'
    }
    
    # Verificar patrones exactos
    if name in ignore_patterns:
        return True
    
    # Verificar patrones con wildcards
    for pattern in ignore_patterns:
        if '*' in pattern:
            if pattern.startswith('*') and name.endswith(pattern[1:]):
                return True
            if pattern.endswith('*') and name.startswith(pattern[:-1]):
                return True
    
    return False

def generate_tree(directory, prefix="", max_depth=5, current_depth=0):
    """Genera el árbol de directorios recursivamente"""
    if current_depth > max_depth:
        return ""
    
    directory = Path(directory)
    if not directory.exists():
        return f"❌ Directorio no encontrado: {directory}\n"
    
    items = []
    try:
        # Obtener todos los elementos y filtrar los ignorados
        all_items = [item for item in directory.iterdir() 
                    if not should_ignore(item.name)]
        
        # Separar directorios y archivos, y ordenar
        dirs = sorted([item for item in all_items if item.is_dir()])
        files = sorted([item for item in all_items if item.is_file()])
        
        items = dirs + files
    except PermissionError:
        return f"{prefix}❌ Sin permisos para acceder\n"
    
    tree_str = ""
    
    for i, item in enumerate(items):
        is_last = i == len(items) - 1
        
        # Elegir el conector apropiado
        if is_last:
            connector = "└── "
            new_prefix = prefix + "    "
        else:
            connector = "├── "
            new_prefix = prefix + "│   "
        
        # Agregar información adicional para archivos
        if item.is_file():
            try:
                size = item.stat().st_size
                if size > 1024 * 1024:  # > 1MB
                    size_str = f" ({size // (1024*1024)}MB)"
                elif size > 1024:  # > 1KB
                    size_str = f" ({size // 1024}KB)"
                else:
                    size_str = f" ({size}B)" if size > 0 else ""
                
                # Agregar extensión destacada para archivos importantes
                important_extensions = {'.py', '.json', '.md', '.txt', '.yml', '.yaml'}
                if item.suffix.lower() in important_extensions:
                    tree_str += f"{prefix}{connector}📄 {item.name}{size_str}\n"
                else:
                    tree_str += f"{prefix}{connector}{item.name}{size_str}\n"
            except OSError:
                tree_str += f"{prefix}{connector}{item.name}\n"
        else:
            # Es un directorio
            tree_str += f"{prefix}{connector}📁 {item.name}/\n"
            
            # Recursión para subdirectorios
            if current_depth < max_depth:
                tree_str += generate_tree(item, new_prefix, max_depth, current_depth + 1)
    
    return tree_str

def get_project_stats(directory):
    """Obtiene estadísticas básicas del proyecto"""
    directory = Path(directory)
    stats = {
        'total_files': 0,
        'total_dirs': 0,
        'python_files': 0,
        'total_size': 0,
        'file_extensions': {}
    }
    
    try:
        for item in directory.rglob('*'):
            if should_ignore(item.name):
                continue
                
            if item.is_file():
                stats['total_files'] += 1
                try:
                    stats['total_size'] += item.stat().st_size
                except OSError:
                    pass
                
                if item.suffix == '.py':
                    stats['python_files'] += 1
                
                ext = item.suffix.lower() or 'sin extensión'
                stats['file_extensions'][ext] = stats['file_extensions'].get(ext, 0) + 1
                
            elif item.is_dir():
                stats['total_dirs'] += 1
    except Exception as e:
        print(f"Error calculando estadísticas: {e}")
    
    return stats

def main():
    """Función principal"""
    project_root = Path.cwd()
    print("🌳 GENERADOR DE ÁRBOL DE PROYECTO SIACASA")
    print("=" * 50)
    print(f"📍 Directorio raíz: {project_root}")
    print(f"📍 Directorio absoluto: {project_root.absolute()}")
    print()
    
    # Generar árbol
    print("📋 ESTRUCTURA DEL PROYECTO:")
    print("-" * 30)
    print(f"📁 {project_root.name}/")
    tree = generate_tree(project_root, max_depth=4)
    print(tree)
    
    # Estadísticas del proyecto
    print("\n📊 ESTADÍSTICAS DEL PROYECTO:")
    print("-" * 30)
    stats = get_project_stats(project_root)
    
    print(f"📁 Total directorios: {stats['total_dirs']}")
    print(f"📄 Total archivos: {stats['total_files']}")
    print(f"🐍 Archivos Python: {stats['python_files']}")
    
    # Convertir tamaño total a unidad legible
    total_size = stats['total_size']
    if total_size > 1024 * 1024:
        size_str = f"{total_size / (1024*1024):.1f} MB"
    elif total_size > 1024:
        size_str = f"{total_size / 1024:.1f} KB"
    else:
        size_str = f"{total_size} bytes"
    
    print(f"💾 Tamaño total: {size_str}")
    print()
    
    # Top 5 extensiones más comunes
    if stats['file_extensions']:
        print("🔖 Top 5 extensiones de archivo:")
        sorted_exts = sorted(stats['file_extensions'].items(), 
                           key=lambda x: x[1], reverse=True)[:5]
        for ext, count in sorted_exts:
            print(f"   {ext}: {count} archivos")
    
    print()
    print("✅ ¡Árbol generado exitosamente!")
    print()
    print("💡 INSTRUCCIONES:")
    print("   1. Copia toda la salida de este script")
    print("   2. Pégala en tu conversación con Claude")
    print("   3. Incluye cualquier información adicional relevante")
    print()
    print("🚀 ¡Listo para compartir con Claude!")

if __name__ == "__main__":
    main()
