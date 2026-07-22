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
    
    for item in items:
        # Get coordinates relative to the canvas origin (0, 0)
        x = item.x()
        y = item.y()
        w = item.rect.width()
        h = item.rect.height()
        
        mime = get_mime_type(item.filename)
        b64_data = base64.b64encode(item.file_data).decode('utf-8')
        href = f"data:{mime};base64,{b64_data}"
        
        # Write image element with exact 1-to-1 canvas ratio preservation
        xml.append(f'  <image href="{href}" x="{x}" y="{y}" width="{w}" height="{h}" preserveAspectRatio="none" />')
        
    xml.append('</svg>')
    
    # Create target directory if it doesn't exist
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(xml))
