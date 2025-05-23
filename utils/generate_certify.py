import os
from datetime import datetime

from PIL import Image, ImageDraw, ImageFont


async def generate_certify(text, user_id, policy):
    if policy == 'admin':
        certificate = Image.open('/root/bot_britva/utils/certify_admin.png')
    else:
        certificate = Image.open('/root/bot_britva/utils/certify_barber.png')
    draw = ImageDraw.Draw(certificate)

    font_path = '/root/bot_britva/utils/akzidenzgroteskpro_boldex.otf'
    font_size = 32
    font = ImageFont.truetype(font_path, font_size)
    today_date = datetime.now().strftime("%d.%m.%Y")
    name_position = (240, 1161)
    date_position = (820, 1296)
    draw.text(name_position, text, font=font, fill="black")
    draw.text(date_position, today_date, font=font, fill="black")
    try:
        os.makedirs(f'/root/bot_britva/utils/certifies/')
    except Exception:
        ...
    output_path = f'/root/bot_britva/utils/certifies/{user_id}.png'
    certificate.save(output_path)
    return output_path
