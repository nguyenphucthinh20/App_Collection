import pyheif
from PIL import Image
import piexif
from geopy.geocoders import Nominatim
from datetime import datetime
from unidecode import unidecode

class HeicProcessor:
    def __init__(self, user_agent="your_app_name_here"):
        self.geolocator = Nominatim(user_agent=user_agent)

    def gps_to_decimal(self, gps):
        if gps is None:
            return None
        degrees = gps[0][0] / gps[0][1]
        minutes = gps[1][0] / gps[1][1]
        seconds = gps[2][0] / gps[2][1]
        return degrees + (minutes / 60.0) + (seconds / 3600.0)

    def reverse_geocode(self, latitude, longitude):
        try:
            location = self.geolocator.reverse((latitude, longitude), language="en", timeout=10)
            return location.address if location else "Address not found"
        except Exception as e:
            print(f"Error while fetching address: {e}")
            return "Address not found"

    def get_capture_date(self, exif_dict):
        if "0th" in exif_dict and piexif.ImageIFD.DateTime in exif_dict["0th"]:
            datetime_str = exif_dict["0th"][piexif.ImageIFD.DateTime].decode('utf-8')
            date_str = datetime_str.split(" ")[0]
            date_obj = datetime.strptime(date_str, '%Y:%m:%d')
            return date_obj.strftime('%d/%m/%Y')
        return "Date not found"

    def get_device_model(self, exif_dict):
        if "0th" in exif_dict and piexif.ImageIFD.Model in exif_dict["0th"]:
            model = exif_dict["0th"][piexif.ImageIFD.Model].decode('utf-8')
            return model.strip()
        return "Device model not found"

    def process_gps_info(self, exif_dict):
        if piexif.GPSIFD.GPSLatitude in exif_dict.get("GPS", {}):
            gps_info = exif_dict["GPS"]
            latitude = self.gps_to_decimal(gps_info.get(piexif.GPSIFD.GPSLatitude, None))
            longitude = self.gps_to_decimal(gps_info.get(piexif.GPSIFD.GPSLongitude, None))

            if latitude and longitude:
                address = self.reverse_geocode(latitude, longitude)
                address = [part.strip() for part in address.split(',')]
                return [unidecode(part) for part in address]
        return None

    def convert_heic_to_jpg(self, input_path, output_path):
        try:
            # Đọc file HEIC và lấy metadata
            heif_file = pyheif.read(input_path)
            metadata = heif_file.metadata

            # Kiểm tra metadata có chứa thông tin Exif
            exif_data = None
            for meta in metadata:
                if meta['type'] == 'Exif':
                    exif_data = meta['data']
                    break

            # Chuyển đổi từ HEIC sang JPG
            image = Image.frombytes(
                heif_file.mode,
                heif_file.size,
                heif_file.data,
                "raw",
                heif_file.mode,
                heif_file.stride,
            )

            # Khởi tạo các biến kết quả
            result = {
                'address': None,
                'capture_date': None,
                'device_model': None
            }

            if exif_data:
                exif_dict = piexif.load(exif_data)
                
                # Lấy thông tin thiết bị, địa chỉ và ngày chụp
                result['device_model'] = self.get_device_model(exif_dict)
                result['address'] = self.process_gps_info(exif_dict)
                result['capture_date'] = self.get_capture_date(exif_dict)

                # Lưu ảnh với exif
                exif_bytes = piexif.dump(exif_dict)
                image.save(output_path, format="JPEG", exif=exif_bytes)
            else:
                # Lưu ảnh không có exif
                image.save(output_path, format="JPEG")

            return result

        except Exception as e:
            print(f"Error processing file: {e}")
            return None

    def print_image_info(self, result):
        if result:
            print(f"Device: {result['device_model']}")
            if result['address']:
                print(f"Location: {result['address'][-1]}")
                print(f"Area: {result['address'][-3]}")
            print(f"Date: {result['capture_date']}")
        else:
            print("No information available")

# Sử dụng class
def main():
    processor = HeicProcessor(user_agent="your_app_name_here")
    result = processor.convert_heic_to_jpg(
        "1107Thao/3-5 images/P12S002/assets/IMG_9097.HEIC", 
        "output.jpg"
    )
    processor.print_image_info(result)

if __name__ == "__main__":
    main()