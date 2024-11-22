from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
import os
from datetime import datetime

def get_detailed_metadata(image_path):
    try:
        image = Image.open(image_path)
        
        # Dictionary cơ bản lưu metadata
        metadata = {
            "Filename": os.path.basename(image_path),
            "Image Size": image.size,
            "Image Format": image.format,
            "Mode": image.mode,
            "Creation Time": datetime.fromtimestamp(os.path.getctime(image_path)),
            "Modified Time": datetime.fromtimestamp(os.path.getmtime(image_path))
        }
        
        # Đọc EXIF data
        if hasattr(image, '_getexif') and image._getexif():
            exif = image._getexif()
            
            # Các tag cần quan tâm
            important_tags = {
                'DateTimeOriginal': 'Thời gian chụp',
                'Make': 'Hãng thiết bị',
                'Model': 'Model thiết bị',
                'Software': 'Phần mềm',
                'GPSInfo': 'Thông tin GPS'
            }
            
            for tag_id in exif:
                tag = TAGS.get(tag_id, tag_id)
                value = exif.get(tag_id)
                
                # Xử lý GPS Info
                if tag == 'GPSInfo':
                    gps_data = {}
                    for t in value:
                        sub_tag = GPSTAGS.get(t, t)
                        gps_data[sub_tag] = value[t]
                    
                    try:
                        if all(k in gps_data for k in ['GPSLatitude', 'GPSLongitude', 'GPSLatitudeRef', 'GPSLongitudeRef']):
                            lat = convert_to_degrees(gps_data['GPSLatitude'])
                            lon = convert_to_degrees(gps_data['GPSLongitude'])
                            
                            if gps_data['GPSLatitudeRef'] == 'S':
                                lat = -lat
                            if gps_data['GPSLongitudeRef'] == 'W':
                                lon = -lon
                            
                            metadata['GPS Coordinates'] = {
                                'Latitude': lat,
                                'Longitude': lon
                            }
                            
                            # Thêm độ cao nếu có
                            if 'GPSAltitude' in gps_data:
                                altitude = float(gps_data['GPSAltitude'].numerator) / float(gps_data['GPSAltitude'].denominator)
                                if 'GPSAltitudeRef' in gps_data and gps_data['GPSAltitudeRef'] == 1:
                                    altitude = -altitude
                                metadata['GPS Coordinates']['Altitude'] = f"{altitude}m"
                    except Exception as e:
                        metadata['GPS Error'] = str(e)
                
                # Xử lý các tag thông thường
                elif tag in important_tags.values() or tag in important_tags.keys():
                    try:
                        if isinstance(value, bytes):
                            value = value.decode()
                        metadata[tag] = value
                    except:
                        continue
        
        return metadata
    
    except Exception as e:
        return f"Error reading image: {str(e)}"

def convert_to_degrees(value):
    try:
        d = float(value[0].numerator) / float(value[0].denominator)
        m = float(value[1].numerator) / float(value[1].denominator)
        s = float(value[2].numerator) / float(value[2].denominator)
        return d + (m / 60.0) + (s / 3600.0)
    except:
        return None

# Sử dụng hàm
image_path = "466786310_1121410436653099_5204090562939197957_n.jpg"
metadata = get_detailed_metadata(image_path)

# In kết quả chi tiết
for key, value in metadata.items():
    print(f"{key}: {value}")