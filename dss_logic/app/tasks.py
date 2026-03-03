import base64
import datetime
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont


FIXED_WIDTH = 300  # Desired fixed width for the image
FIXED_HEIGHT = 200  # Desired fixed height for the image
TEXT_AREA_WIDTH = 300  # Width of the text area to the right of the image
FONT_PATH = "DejaVuSans.ttf"  # Path to the font file, update it as necessary




def annotate_image(data):
    """
    Annotate the image with text information and return the base64-encoded string of the annotated image.

    Args:
        data (dict): Dictionary with base64 image data and optional email.

    Returns:
        str: Base64-encoded string of the annotated image.
    """
    try:
        # Extract and decode the base64 image
        signature_base64 = data["signature"]

        # Remove the data URL prefix
        if signature_base64.startswith("data:image/png;base64,"):
            signature_base64 = signature_base64.split(",")[1]

        # Add padding if necessary
        missing_padding = len(signature_base64) % 4
        if missing_padding:
            signature_base64 += '=' * (4 - missing_padding)

        signature_bytes = base64.b64decode(signature_base64)
        try:
            image = Image.open(BytesIO(signature_bytes)).convert("RGBA")
        except Exception as e:
            print(f"Error opening image: {e}")
            return None

        # Resize the image to the fixed dimensions while maintaining the aspect ratio
        image = resize_image_to_fixed_dimensions(image, FIXED_WIDTH, FIXED_HEIGHT)

        # Create a new image with a transparent background
        if data.get("annotate"):
            new_image = Image.new('RGBA', (FIXED_WIDTH + TEXT_AREA_WIDTH, FIXED_HEIGHT), (255, 255, 255, 0))
        else:
            new_image = Image.new('RGBA', (FIXED_WIDTH , FIXED_HEIGHT), (255, 255, 255, 0))

        # Paste the resized signature image on the left
        new_image.paste(image, (0, 0), image)

        # Create a drawing context
        d = ImageDraw.Draw(new_image)
        
        # Set font size based on the fixed height
        font_size = round((0.1 * FIXED_HEIGHT))
        try:
            font = ImageFont.truetype(FONT_PATH, font_size)
        except IOError:
            raise IOError(f"The font file at {FONT_PATH} does not exist or cannot be opened.")

        text_color = (0, 0, 0, 255)

        # Current date and time
        now = datetime.datetime.now()
        date_string = now.strftime("%Y-%m-%d")
        time_string = now.strftime("%H:%M:%S")

        # Initial text position - reduced spacing to 2 pixels
        text_pos_x = FIXED_WIDTH + 2
        text_pos_y = 20

        # Draw the text
        if data.get("annotate"):
            if data.get("signerEmail") and data.get("email"):
                test_text = "Document signed by "
                d.text((text_pos_x, text_pos_y), text=test_text, font=font, fill=text_color)
                text_pos_y += font_size + 12  # Adjust y-position for next text

                # Draw the email
                email_text = data["email"]
                d.text((text_pos_x, text_pos_y), text=email_text, font=font, fill=text_color)
                text_pos_y += font_size + 12  # Adjust y-position for next text

            if data.get("date"):
                # Draw the date
                d.text((text_pos_x, text_pos_y), text=f"Date: {date_string}", font=font, fill=text_color)
                text_pos_y += font_size + 12  # Adjust y-position for next text

            if data.get("signTimestamp"):
                # Draw the timestamp
                d.text((text_pos_x, text_pos_y), text=f"Time: {time_string}", font=font, fill=text_color)

        # Convert the final image to base64
        buffered = BytesIO()
        new_image.save(buffered, format="PNG")
        new_image.save("image.png")
        new_image.show()
        img_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

        # Return the base64 string of the annotated image
        return f"data:image/png;base64,{img_base64}"

    except base64.binascii.Error as e:
        print("Error decoding base64:", e)
    except IOError as e:
        print("Error opening image:", e)
    except Exception as e:
        print("An error occurred:", e)
        return None


def resize_image_to_fixed_dimensions(image, fixed_width, fixed_height):
    """
    Resize the image to the fixed dimensions while maintaining the aspect ratio.

    Args:
        image (PIL.Image.Image): The image to be resized.
        fixed_width (int): The desired fixed width for the image.
        fixed_height (int): The desired fixed height for the image.

    Returns:
        PIL.Image.Image: The resized image.
    """
    original_width, original_height = image.size
    aspect_ratio = original_width / original_height

    if fixed_width / fixed_height > aspect_ratio:
        new_width = int(fixed_height * aspect_ratio)
        new_height = fixed_height
    else:
        new_width = fixed_width
        new_height = int(fixed_width / aspect_ratio)

    resized_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)

    # Create a new image with a transparent background
    new_image = Image.new('RGBA', (fixed_width, fixed_height), (255, 255, 255, 0))
    new_image.paste(resized_image, ((fixed_width - new_width) // 2, (fixed_height - new_height) // 2))

    return new_image