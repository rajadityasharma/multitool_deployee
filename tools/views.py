from django.shortcuts import render, redirect
from rembg import remove
from PIL import Image, ImageEnhance, ImageDraw
import base64
from io import BytesIO
import io
from fpdf import FPDF
import tempfile
import os
from django.core.files.uploadedfile import InMemoryUploadedFile


def background_remover(request):
    image_data = None

    if request.method == 'POST':
        uploaded_file = request.FILES.get('image')
        bg_type = request.POST.get('bg_type')
        color = request.POST.get('color')
        bg_image_file = request.FILES.get('bg_image')
        gradient_top = request.POST.get('gradient_top', '#ffffff')
        gradient_bottom = request.POST.get('gradient_bottom', '#cccccc')
        gradient_direction = request.POST.get('gradient_direction', 'vertical')

        if uploaded_file:
            try:
                input_image = Image.open(uploaded_file).convert("RGBA")
                output_image = remove(input_image)

                # 🌈 Background logic
                if bg_type == 'color' and color:
                    bg = Image.new("RGBA", output_image.size, color)
                    bg.paste(output_image, (0, 0), mask=output_image.split()[3])
                    output_image = bg

                elif bg_type == 'image' and bg_image_file:
                    bg_img = Image.open(bg_image_file).convert("RGBA").resize(output_image.size)
                    bg_img.paste(output_image, (0, 0), mask=output_image.split()[3])
                    output_image = bg_img

                elif bg_type == 'gradient':
                    width, height = output_image.size
                    gradient = Image.new("RGBA", (width, height))
                    draw = ImageDraw.Draw(gradient)

                    def hex_to_rgb(hex_color):
                        hex_color = hex_color.lstrip('#')
                        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4)) + (255,)

                    top_color = hex_to_rgb(gradient_top)
                    bottom_color = hex_to_rgb(gradient_bottom)

                    if gradient_direction == 'vertical':
                        for y in range(height):
                            ratio = y / height
                            color = tuple(int(top_color[i] * (1 - ratio) + bottom_color[i] * ratio) for i in range(4))
                            draw.line([(0, y), (width, y)], fill=color)
                    elif gradient_direction == 'horizontal':
                        for x in range(width):
                            ratio = x / width
                            color = tuple(int(top_color[i] * (1 - ratio) + bottom_color[i] * ratio) for i in range(4))
                            draw.line([(x, 0), (x, height)], fill=color)
                    elif gradient_direction == 'diagonal':
                        for y in range(height):
                            for x in range(width):
                                ratio = (x + y) / (width + height)
                                color = tuple(int(top_color[i] * (1 - ratio) + bottom_color[i] * ratio) for i in range(4))
                                draw.point((x, y), fill=color)

                    gradient.paste(output_image, (0, 0), mask=output_image.split()[3])
                    output_image = gradient

                # Convert to base64
                buffer = io.BytesIO()
                output_image.save(buffer, format='PNG')
                buffer.seek(0)
                image_data = base64.b64encode(buffer.read()).decode('utf-8')

            except Exception as e:
                print("Error in processing image:", e)

    return render(request, 'background_remover.html', {'image_data': image_data})

  
def dashboard(request):
    return render(request, 'dashboard.html')

def image_enhancer(request):
    enhanced_image = None

    if request.method == 'POST' and request.FILES.get('image'):
        uploaded_file = request.FILES['image']
        image = Image.open(uploaded_file)

        # Enhance the image
        enhancer_brightness = ImageEnhance.Brightness(image)
        image = enhancer_brightness.enhance(1.3)

        enhancer_contrast = ImageEnhance.Contrast(image)
        image = enhancer_contrast.enhance(1.3)

        enhancer_sharpness = ImageEnhance.Sharpness(image)
        image = enhancer_sharpness.enhance(2.0)

        # Convert to base64
        buffer = io.BytesIO()
        image.save(buffer, format='PNG')
        buffer.seek(0)
        enhanced_image = base64.b64encode(buffer.read()).decode('utf-8')

    return render(request, 'image_enhancer.html', {'enhanced_image': enhanced_image})

    # views.py (add this view in tools/views.py)


def image_compressor(request):
    context = {}
    if request.method == 'POST':
        image_file = request.FILES.get('image')
        mode = request.POST.get('mode')
        value = float(request.POST.get('value'))
        unit = request.POST.get('unit')  # 'KB' or 'MB'
        output_format = request.POST.get('format', 'JPEG')
        width = request.POST.get('width')
        height = request.POST.get('height')

        img = Image.open(image_file)
        original_size = round(image_file.size / 1024, 2)  # KB

        # Resize if dimensions provided
        if width and height:
            try:
                img = img.resize((int(width), int(height)))
            except:
                pass

        buffer = BytesIO()

        if mode == 'percentage':
            quality = max(1, min(95, int(value)))  # clamp between 1–95
            img.save(buffer, format=output_format, quality=quality, optimize=True)
        elif mode == 'target':
            # Convert MB to KB if needed
            target_size_kb = value * 1024 if unit == 'MB' else value
            # Try reducing quality in steps until target met
            for q in range(95, 5, -5):
                buffer = BytesIO()
                img.save(buffer, format=output_format, quality=q, optimize=True)
                size_kb = len(buffer.getvalue()) / 1024
                if size_kb <= target_size_kb:
                    break
        else:
            img.save(buffer, format=output_format, optimize=True)

        image_data = base64.b64encode(buffer.getvalue()).decode('utf-8')
        compressed_size = round(len(buffer.getvalue()) / 1024, 2)  # KB

        context = {
            'image_data': image_data,
            'format': output_format,
            'original_size': original_size,
            'compressed_size': compressed_size,
        }

    return render(request, 'image_compressor.html', context)


def image_to_pdf(request):
    pdf_data = None

    if request.method == 'POST':
        images = request.FILES.getlist('images')
        fit_option = request.POST.get('fit_option', 'fit')  # 'fit' as default

        if images:
            pdf = FPDF()
            temp_files = []

            try:
                for image_file in images:
                    img = Image.open(image_file).convert('RGB')

                    # Save to temp file
                    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
                    img.save(temp_file, format='JPEG')
                    temp_file.close()
                    temp_files.append(temp_file.name)

                    pdf.add_page()

                    if fit_option == 'fill':
                        # Fill the entire page, might crop
                        pdf.image(temp_file.name, x=0, y=0, w=pdf.w, h=pdf.h)
                    else:
                        # Fit while maintaining aspect ratio
                        img_width, img_height = img.size
                        aspect_ratio = img_width / img_height
                        page_width = pdf.w - 20
                        page_height = pdf.h - 20
                        page_aspect = page_width / page_height

                        if aspect_ratio > page_aspect:
                            new_width = page_width
                            new_height = new_width / aspect_ratio
                        else:
                            new_height = page_height
                            new_width = new_height * aspect_ratio

                        x = (pdf.w - new_width) / 2
                        y = (pdf.h - new_height) / 2
                        pdf.image(temp_file.name, x=x, y=y, w=new_width, h=new_height)

                # Generate base64 PDF
                pdf_string = pdf.output(dest='S').encode('latin1')
                pdf_data = base64.b64encode(pdf_string).decode('utf-8')

            except Exception as e:
                print("Image to PDF error:", e)

            finally:
                for path in temp_files:
                    try:
                        os.remove(path)
                    except:
                        pass

    return render(request, 'image_to_pdf.html', {'pdf_data': pdf_data})


def image_cropper(request):
    return render(request, 'image_cropper.html')


def stamp_file(request):
    base_image_data = None
    stamp_image_data = None

    if request.method == 'POST':
        base_file = request.FILES.get('base_file')
        stamp_file_obj = request.FILES.get('stamp_file')

        try:
            base_file.seek(0)
            base_image_data = base64.b64encode(base_file.read()).decode('utf-8')

            stamp_file_obj.seek(0)
            stamp_image_data = base64.b64encode(stamp_file_obj.read()).decode('utf-8')

        except Exception as e:
            print("Error:", e)

    return render(request, 'stamp_file.html', {
        'base_image_data': base_image_data,
        'stamp_image_data': stamp_image_data,
    })



def image_merger(request):
    merged_image = None

    if request.method == "POST":
        images = request.FILES.getlist("images")
        merge_direction = request.POST.get("merge_direction", "horizontal")
        resize_option = request.POST.get("resize_option", "none")
        spacing = int(request.POST.get("spacing", 0))
        bg_color = request.POST.get("bg_color", "#FFFFFF")

        if len(images) >= 2:
            pil_images = [Image.open(img).convert("RGBA") for img in images]

            # 🔄 Resize Logic
            if resize_option == "width":
                min_width = min(img.width for img in pil_images)
                pil_images = [img.resize((min_width, int(img.height * min_width / img.width))) for img in pil_images]
            elif resize_option == "height":
                min_height = min(img.height for img in pil_images)
                pil_images = [img.resize((int(img.width * min_height / img.height), min_height)) for img in pil_images]
            elif resize_option == "both":
                min_width = min(img.width for img in pil_images)
                min_height = min(img.height for img in pil_images)
                pil_images = [img.resize((min_width, min_height)) for img in pil_images]

            # 🔳 Calculate final canvas size
            if merge_direction == "horizontal":
                total_width = sum(img.width for img in pil_images) + spacing * (len(pil_images) - 1)
                max_height = max(img.height for img in pil_images)
                final_image = Image.new("RGBA", (total_width, max_height), bg_color)
                x_offset = 0
                for img in pil_images:
                    final_image.paste(img, (x_offset, 0), img)
                    x_offset += img.width + spacing

            else:  # vertical
                total_height = sum(img.height for img in pil_images) + spacing * (len(pil_images) - 1)
                max_width = max(img.width for img in pil_images)
                final_image = Image.new("RGBA", (max_width, total_height), bg_color)
                y_offset = 0
                for img in pil_images:
                    final_image.paste(img, (0, y_offset), img)
                    y_offset += img.height + spacing

            # ✅ Convert to base64 for frontend
            buffer = BytesIO()
            final_image.convert("RGB").save(buffer, format="PNG")
            merged_image = base64.b64encode(buffer.getvalue()).decode()

    return render(request, "image_merger.html", {
        "merged_image": merged_image
    })
