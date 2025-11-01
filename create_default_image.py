from PIL import Image, ImageDraw, ImageFont

# Create a new image with a light gray background
img = Image.new('RGB', (1200, 630), 'lightgray')
draw = ImageDraw.Draw(img)

# Add text (no custom font, using default)
text = "Default Image"
bbox = draw.textbbox((0, 0), text)
text_width = bbox[2] - bbox[0]
text_height = bbox[3] - bbox[1]

# Calculate text position for center alignment
x = (1200 - text_width) / 2
y = (630 - text_height) / 2

# Draw the text
draw.text((x, y), text, fill='black')

# Save the image
img.save('/home/swider/auto-article/kids/static/img/default.jpg')