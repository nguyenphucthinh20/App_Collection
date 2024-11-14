import os
import pyheif
from PIL import Image, ExifTags
import piexif
from geopy.geocoders import Nominatim
from datetime import datetime
import random
import shutil
import streamlit as st
import tempfile
import io
import zipfile
# Cấu hình page
st.set_page_config(
    page_title="Image Metadata Modifier",
    page_icon="📷",
    layout="wide"
)
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

    def fix_image_orientation(self, image):
        try:
            for orientation in ExifTags.TAGS.keys():
                if ExifTags.TAGS[orientation] == 'Orientation':
                    break
            exif = image._getexif()
            if exif is not None and orientation in exif:
                if exif[orientation] == 2:
                    image = image.transpose(Image.FLIP_LEFT_RIGHT)
                elif exif[orientation] == 3:
                    image = image.transpose(Image.ROTATE_180)
                elif exif[orientation] == 4:
                    image = image.transpose(Image.FLIP_TOP_BOTTOM)
                elif exif[orientation] == 5:
                    image = image.transpose(Image.FLIP_LEFT_RIGHT).transpose(Image.ROTATE_90)
                elif exif[orientation] == 6:
                    image = image.transpose(Image.ROTATE_270)
                elif exif[orientation] == 7:
                    image = image.transpose(Image.FLIP_LEFT_RIGHT).transpose(Image.ROTATE_270)
                elif exif[orientation] == 8:
                    image = image.transpose(Image.ROTATE_90)
            return image
        except (AttributeError, KeyError, IndexError):
            return image

    def modify_image_metadata(self, image_path, output_path, new_device=None, new_date=None, day_or_night=None):
        try:
            # Lấy tên file và phần mở rộng
            base_name, ext = os.path.splitext(os.path.basename(image_path))
            
            # Tạo đường dẫn đầy đủ cho file output
            output_file = os.path.join(output_path, f"{base_name}.jpg")
            
            # Chuyển đổi HEIC sang JPEG nếu là file HEIC
            if ext.lower() == '.heic':
                heif_file = pyheif.read(image_path)
                image = Image.frombytes(
                    heif_file.mode,
                    heif_file.size,
                    heif_file.data,
                    "raw",
                    heif_file.mode,
                    heif_file.stride,
                )
                
                # Copy EXIF data từ file HEIC
                for metadata in heif_file.metadata or []:
                    if metadata['type'] == 'Exif':
                        exif_dict = piexif.load(metadata['data'])
                        break
                else:
                    exif_dict = {'0th': {}, 'Exif': {}, 'GPS': {}, '1st': {}, 'thumbnail': None}
            else:
                # Nếu là file JPEG, đọc ảnh và fix orientation
                image = Image.open(image_path)
                image = self.fix_image_orientation(image)
                exif_dict = piexif.load(image_path)

            # Thay đổi model thiết bị nếu được chỉ định
            if new_device and "0th" in exif_dict:
                exif_dict["0th"][piexif.ImageIFD.Model] = new_device.encode('utf-8')

            # Thay đổi ngày nếu được chỉ định
            if new_date:
                try:
                    # date_obj = datetime.strptime(new_date, '%d/%m/%Y')
                    date_obj = new_date
                    
                    # Random giờ dựa trên day_or_night
                    if day_or_night == 'day':
                        random_hour = random.randint(8, 16)
                    elif day_or_night == 'night':
                        random_hour = random.randint(18, 23)
                    else:
                        random_hour = random.randint(0, 23)

                    random_minute = random.randint(0, 59)
                    random_second = random.randint(0, 59)
                    new_datetime = f"{date_obj.strftime('%Y:%m:%d')} {random_hour:02}:{random_minute:02}:{random_second:02}"
                    datetime_bytes = new_datetime.encode('utf-8')
                    
                    # Cập nhật các trường datetime
                    if "0th" in exif_dict:
                        exif_dict["0th"][piexif.ImageIFD.DateTime] = datetime_bytes
                    if "Exif" in exif_dict:
                        exif_dict["Exif"][piexif.ExifIFD.DateTimeOriginal] = datetime_bytes
                        exif_dict["Exif"][piexif.ExifIFD.DateTimeDigitized] = datetime_bytes
                    
                except ValueError as e:
                    print(f"Invalid date format. Please use dd/mm/yyyy. Error: {e}")
                    return False

            # Loại bỏ thông tin Orientation để tránh xoay ảnh
            if "0th" in exif_dict and piexif.ImageIFD.Orientation in exif_dict["0th"]:
                del exif_dict["0th"][piexif.ImageIFD.Orientation]

            # Lưu lại EXIF data vào ảnh trong thư mục output
            exif_bytes = piexif.dump(exif_dict)
            image.save(output_file, format="JPEG", exif=exif_bytes, quality=95)
            
            # Xác nhận thay đổi
            verification = piexif.load(output_file)
            print("Verification after modification:")
            if new_device and piexif.ImageIFD.Model in verification['0th']:
                print(f"Device: {verification['0th'][piexif.ImageIFD.Model].decode('utf-8')}")
            if new_date and piexif.ImageIFD.DateTime in verification['0th']:
                print(f"Date: {verification['0th'][piexif.ImageIFD.DateTime].decode('utf-8')}")
            
            return True

        except Exception as e:
            print(f"Error modifying metadata: {e}")
            return False

def process_images_in_folder_or_file(input_path, new_device=None, new_date=None, day_or_night=None):
    processor = HeicProcessor()

    # Tạo tên folder output
    if os.path.isdir(input_path):
        output_path = input_path + "_output"
    else:
        # Nếu là file, tạo folder output cùng cấp với file input
        parent_dir = os.path.dirname(input_path)
        base_name = os.path.splitext(os.path.basename(input_path))[0]
        output_path = os.path.join(parent_dir, base_name + "_output")

    # Tạo folder output nếu chưa tồn tại
    if os.path.exists(output_path):
        shutil.rmtree(output_path)  # Xóa folder cũ nếu tồn tại
    os.makedirs(output_path)

    if os.path.isdir(input_path):
        image_files = [f for f in os.listdir(input_path) if f.lower().endswith(('.jpg', '.jpeg', '.heic'))]
        print(f"Found {len(image_files)} images in folder {input_path}")

        for image_file in image_files:
            image_path = os.path.join(input_path, image_file)
            success = processor.modify_image_metadata(
                image_path,
                output_path,
                new_device=new_device,
                new_date=new_date,
                day_or_night=day_or_night
            )

            if success:
                print(f"Metadata modified successfully for {image_file}")
            else:
                print(f"Failed to modify metadata for {image_file}")
    
    elif os.path.isfile(input_path):
        success = processor.modify_image_metadata(
            input_path,
            output_path,
            new_device=new_device,
            new_date=new_date,
            day_or_night=day_or_night
        )

        if success:
            print(f"Metadata modified successfully for {input_path}")
            output_file = os.path.join(output_path, f"{base_name}.jpg")
            return output_file
        else:
            print(f"Failed to modify metadata for {input_path}")
    else:
        print(f"{input_path} is neither a file nor a folder. Please provide a valid path.")
    
    print("+++++++++++++++++++++++++++", output_path)
    return None
def main():
    st.title("Image Metadata Modifier 📸")
    
    # Sidebar settings
    with st.sidebar:
        st.header("Settings")
        device_options = [
            "iPhone 15 Pro Max",
            "iPhone 15 Pro",
            "iPhone 14 Pro Max",
            "iPhone 14 Pro",
            "iPhone 13 Pro Max",
            "iPhone 13 Pro",
            "iPhone 12 Pro Max",
            "iPhone 12 Pro",
            "iPhone 11 Pro Max",
            "iPhone 11 Pro",
            "iPhone X",
        ]
        selected_device = st.selectbox("📱 Select Device", device_options)
        selected_date = st.date_input("📅 Select Date")
        time_options = ["day", "night", "random"]
        selected_time = st.selectbox("🕒 Select Time of Day", time_options)
    
    # File uploader
    uploaded_files = st.file_uploader(
        "Upload Images (JPG, JPEG, HEIC)", 
        type=["jpg", "jpeg", "heic"],
        accept_multiple_files=True
    )
    
    if st.button("Process Images") and uploaded_files:
        # Create progress bar
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Create a temporary directory to store uploaded files
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a BytesIO object to store the ZIP file
            zip_buffer = io.BytesIO()
            
            # Create ZIP file
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                # Process each file
                for idx, uploaded_file in enumerate(uploaded_files):
                    status_text.text(f"Processing {uploaded_file.name}...")
                    
                    # Save uploaded file to temporary directory
                    temp_file_path = os.path.join(temp_dir, uploaded_file.name)
                    with open(temp_file_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    
                    try:
                        # Process the image
                        output_file = process_images_in_folder_or_file(
                            temp_file_path,
                            new_device=selected_device,
                            new_date=selected_date,
                            day_or_night=selected_time
                        )
                        
                        if output_file and os.path.exists(output_file):
                            # Add processed file to ZIP
                            zip_file.write(
                                output_file, 
                                os.path.basename(output_file)
                            )
                        else:
                            st.error(f"Failed to process {uploaded_file.name}")
                    
                    except Exception as e:
                        st.error(f"Error processing {uploaded_file.name}: {str(e)}")
                    
                    # Update progress bar
                    progress_bar.progress((idx + 1) / len(uploaded_files))

            # Reset buffer position
            zip_buffer.seek(0)
            
            # Create download button for ZIP file
            st.download_button(
                label="Download Processed Images (ZIP)",
                data=zip_buffer,
                file_name="processed_images.zip",
                mime="application/zip"
            )
            st.success("✅ Processing complete!")
                # Add footer
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center'>
            <p>Made with ❤️ by ThinhNP</p>
        </div>
        """, 
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()
# def main():
#     input_path = "1107Thao/6-10 images/P12S007/assets/IMG_5560.HEIC"  # Thay thế bằng đường dẫn tới file hoặc folder
    
#     process_images_in_folder_or_file(
#         input_path,
#         new_device="iPhone 14 Pro Max",
#         new_date="25/12/2023",
#         day_or_night="night"
#     )

# if __name__ == "__main__":
#     main()