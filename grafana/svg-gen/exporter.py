import os
import base64

def get_mime_type(filename):
    ext = os.path.splitext(filename)[1].lower()
    if ext in ('.jpg', '.jpeg'):
        return 'image/jpeg'
    elif ext == '.png':
        return 'image/png'
    elif ext == '.svg':
        return 'image/svg+xml'
    elif ext == '.gif':
        return 'image/gif'
    elif ext == '.webp':
        return 'image/webp'
    else:
        return 'image/png' # Default fallback

def export_to_svg(width, height, items, output_path):
    """
    Synthesizes the canvas layers into a single SVG file.
    items: List of ImageLayerItem ordered from bottom to top (by Z-value).
    """
    xml = []
    xml.append('<?xml version="1.0" encoding="UTF-8" standalone="no"?>')
    xml.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="100%" height="100%">')
    
    # Define SVG filters for drop-shadow and glow visibility effects
    xml.append('  <defs>')
    xml.append('    <filter id="shadow" x="-30%" y="-30%" width="160%" height="160%">')
    xml.append('      <feDropShadow dx="3" dy="3" stdDeviation="4" flood-color="#000000" flood-opacity="0.75"/>')
    xml.append('    </filter>')
    xml.append('    <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">')
    xml.append('      <feDropShadow dx="0" dy="0" stdDeviation="6" flood-color="#00d2ff" flood-opacity="0.9"/>')
    xml.append('    </filter>')
    xml.append('  </defs>')
    
    for item in items:
        # Get coordinates relative to the canvas origin (0, 0)
        x = item.x()
        y = item.y()
        w = item.rect.width()
        h = item.rect.height()
        
        mime = getattr(item, 'processed_mime_type', None) or get_mime_type(item.filename)
        raw_data = getattr(item, 'processed_file_data', item.file_data)
        if not isinstance(raw_data, bytes):
            raw_data = bytes(raw_data)
        b64_data = base64.b64encode(raw_data).decode('utf-8')
        href = f"data:{mime};base64,{b64_data}"
        
        filter_attr = ""
        if hasattr(item, 'effect_type'):
            if item.effect_type == "shadow":
                filter_attr = ' filter="url(#shadow)"'
            elif item.effect_type == "glow":
                filter_attr = ' filter="url(#glow)"'
        
        # Write image element with exact 1-to-1 canvas ratio preservation and visibility filter
        xml.append(f'  <image href="{href}" x="{x}" y="{y}" width="{w}" height="{h}" preserveAspectRatio="none"{filter_attr} />')
        
    xml.append('</svg>')
    
    # Create target directory if it doesn't exist
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(xml))
