#!/usr/bin/env python3
"""Create a simple source favicon image for the blog."""
from PIL import Image, ImageDraw, ImageFont
import os

def create_source_favicon():
    """Create a high-resolution source image for favicon generation."""
    # Create a 512x512 image with a gradient background
    size = 512
    img = Image.new('RGB', (size, size), color='#ffffff')
    draw = ImageDraw.Draw(img)
    
    # Create a simple design - rounded square with "PR" text
    # Background color - friendly blue/teal
    bg_color = (52, 152, 219)  # Nice blue color
    
    # Draw rounded rectangle background
    margin = 50
    draw.rounded_rectangle(
        [(margin, margin), (size - margin, size - margin)],
        radius=80,
        fill=bg_color
    )
    
    # Add "PR" text (Poradnik Rodzica)
    try:
        # Try to use a nice font, fall back to default if not available
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 200)
    except:
        font = ImageFont.load_default()
    
    # Calculate text position to center it
    text = "PR"
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    position = ((size - text_width) // 2, (size - text_height) // 2 - 20)
    
    # Draw text with white color
    draw.text(position, text, fill='#ffffff', font=font)
    
    # Save the image
    output_path = '/home/swider/auto-article/kids/static/icons/source.png'
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    img.save(output_path, 'PNG', quality=95)
    print(f"Source favicon created at: {output_path}")
    
    return output_path

if __name__ == "__main__":
    create_source_favicon()
