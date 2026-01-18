"""
Session Management - Save and Load Algorithm Parameters
Handles persistence of last used parameters across program sessions
"""
import json
import traceback
from config import CONFIG


def save_session_params(algorithm, umap_params, tsne_params, point_size, group_col,
                        group_cols=None, data_cols=None, file_path=None, sheet_name=None,
                        render_mode='UMAP', selected_2d_cols=None, selected_3d_cols=None,
                        language=None, tooltip_columns=None, ui_theme=None):
    """
    Save current session parameters to temporary file
    """
    try:
        session_data = {
            'algorithm': algorithm,
            'umap_params': umap_params,
            'tsne_params': tsne_params,
            'point_size': point_size,
            'group_col': group_col,
            'group_cols': group_cols,
            'data_cols': data_cols,
            'file_path': file_path,
            'sheet_name': sheet_name,
            'render_mode': render_mode,
            'selected_2d_cols': selected_2d_cols or [],
            'selected_3d_cols': selected_3d_cols or [],
            'language': language,
            'tooltip_columns': tooltip_columns,
            'ui_theme': ui_theme
        }
        
        print(f"[DEBUG] Saving session params. Tooltip columns: {tooltip_columns}", flush=True)

        with open(CONFIG['params_temp_file'], 'w', encoding='utf-8') as f:
            json.dump(session_data, f, indent=2, ensure_ascii=False)
        
        print(f"[INFO] Session parameters saved to {CONFIG['params_temp_file']}", flush=True)
        return True
    except Exception as e:
        print(f"[WARN] Failed to save session parameters: {e}", flush=True)
        traceback.print_exc()
        return False


def load_session_params():
    """
    Load last session parameters from temporary file
    
    Returns:
        dict with keys: algorithm, umap_params, tsne_params, point_size, group_col
        or None if file doesn't exist or load fails
    """
    try:
        params_file = CONFIG['params_temp_file']
        
        if not params_file.exists():
            print("[INFO] No previous session found", flush=True)
            return None
        
        with open(params_file, 'r', encoding='utf-8') as f:
            session_data = json.load(f)
        
        print(f"[INFO] Session parameters loaded from {params_file}", flush=True)
        print(f"[INFO] Previous algorithm: {session_data.get('algorithm', 'UMAP')}", flush=True)
        print(f"[INFO] Previous group: {session_data.get('group_col', 'Province')}", flush=True)
        return session_data
    except Exception as e:
        print(f"[WARN] Failed to load session parameters: {e}", flush=True)
        traceback.print_exc()
        return None


def clear_session_params():
    """Clear saved session parameters"""
    try:
        params_file = CONFIG['params_temp_file']
        if params_file.exists():
            params_file.unlink()
            print("[INFO] Session parameters cleared", flush=True)
            return True
    except Exception as e:
        print(f"[WARN] Failed to clear session parameters: {e}", flush=True)
    return False


def get_temp_dir_size():
    """Get size of temp directory in MB"""
    try:
        total_size = 0
        for item in CONFIG['temp_dir'].iterdir():
            if item.is_file():
                total_size += item.stat().st_size
        return total_size / (1024 * 1024)  # Convert to MB
    except:
        return 0
