import streamlit as st
import time
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
from geopy.geocoders import Nominatim
import pillow_heif
from io import BytesIO

st.set_page_config(
    page_title="Image Location Finder",
    page_icon="🌍",
    layout="wide"
)

def get_decimal_from_dms(dms, ref):
    degrees = dms[0]
    minutes = dms[1] / 60.0
    seconds = dms[2] / 3600.0
    
    if ref in ['S', 'W']:
        degrees = -degrees
        minutes = -minutes 
        seconds = -seconds
        
    return degrees + minutes + seconds

def convert_heic_to_jpg(heic_data):
    try:
        # Đọc file HEIC
        heif_file = pillow_heif.read_heif(heic_data)
        # Chuyển đổi sang PIL Image
        image = Image.frombytes(
            heif_file.mode,
            heif_file.size,
            heif_file.data,
            "raw",
        )
        # Chuyển đổi sang JPG
        jpg_data = BytesIO()
        image.save(jpg_data, format='JPEG')
        return Image.open(jpg_data)
    except Exception as e:
        st.error(f"Lỗi khi chuyển đổi HEIC sang JPG: {str(e)}")
        return None

def get_gps_data(image):
    try:
        exif = image._getexif()
        
        if not exif:
            return None, None

        gps_info = {}
        
        for tag_id in exif:
            tag = TAGS.get(tag_id, tag_id)
            data = exif.get(tag_id)
            
            if tag == 'GPSInfo':
                for t in data:
                    sub_tag = GPSTAGS.get(t, t)
                    gps_info[sub_tag] = data[t]

        if not gps_info:
            return None, None

        lat = get_decimal_from_dms(gps_info['GPSLatitude'], gps_info['GPSLatitudeRef'])
        lon = get_decimal_from_dms(gps_info['GPSLongitude'], gps_info['GPSLongitudeRef'])
        
        return lat, lon
        
    except Exception as e:
        st.error(f"Lỗi khi đọc GPS: {str(e)}")
        return None, None

def get_location_info(latitude, longitude):
    try:
        geolocator = Nominatim(user_agent="my_app")
        time.sleep(1)
        
        location = geolocator.reverse(f"{latitude}, {longitude}", language='vi')
        if location and location.raw.get('address'):
            address = location.raw['address']
            
            state = address.get('state', '')
            city = address.get('city', '')
            suburb = address.get('suburb', '')
            
            location_info = {
                'state': state,
                'city': city,
                'suburb': suburb,
                'full_address': location.address
            }
            return location_info
            
    except Exception as e:
        st.error(f"Lỗi khi lấy thông tin địa điểm: {str(e)}")
    return None

def main():
    st.title("🌍 Xác định vị trí từ ảnh")
    st.write("Upload ảnh để xác định vị trí chụp (Hỗ trợ: JPG, JPEG, HEIC)")

    uploaded_file = st.file_uploader("Chọn ảnh", type=['jpg', 'jpeg', 'heic'])

    if uploaded_file is not None:
        try:
            # Hiển thị thanh tiến trình
            progress_bar = st.progress(0)
            status_text = st.empty()

            # Đọc và xử lý ảnh
            status_text.text("Đang đọc ảnh...")
            progress_bar.progress(20)

            if uploaded_file.name.lower().endswith('.heic'):
                image = convert_heic_to_jpg(uploaded_file.read())
            else:
                image = Image.open(uploaded_file)

            # Hiển thị ảnh
            st.image(image, caption="Ảnh đã upload", use_column_width=True)
            
            progress_bar.progress(40)
            status_text.text("Đang trích xuất thông tin GPS...")

            # Lấy tọa độ GPS
            latitude, longitude = get_gps_data(image)
            
            progress_bar.progress(60)
            
            if latitude is None or longitude is None:
                st.warning("Không tìm thấy thông tin GPS trong ảnh.")
                return

            status_text.text("Đang lấy thông tin địa điểm...")
            progress_bar.progress(80)

            # Lấy thông tin địa điểm
            location_info = get_location_info(latitude, longitude)
            
            progress_bar.progress(100)
            status_text.text("Hoàn thành!")

            if location_info:
                # Hiển thị kết quả trong các columns
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("Thông tin GPS")
                    st.write(f"📍 Vĩ độ: {latitude}")
                    st.write(f"📍 Kinh độ: {longitude}")

                with col2:
                    st.subheader("Thông tin địa điểm")
                    st.write(f"🏛️ Tỉnh/Thành phố: {location_info['state']}")
                    st.write(f"🏢 Quận/Huyện: {location_info['city']}")
                    st.write(f"🏠 Phường/Xã: {location_info['suburb']}")
                
                st.subheader("Địa chỉ đầy đủ")
                st.info(location_info['full_address'])

                # Hiển thị bản đồ
                map_data = f'''
                    <iframe width="100%" height="450" style="border:0" loading="lazy" allowfullscreen
                    src="https://www.openstreetmap.org/export/embed.html?bbox={longitude-0.01}%2C{latitude-0.01}%2C{longitude+0.01}%2C{latitude+0.01}&amp;layer=mapnik&amp;marker={latitude}%2C{longitude}">
                    </iframe>
                '''
                st.components.v1.html(map_data, height=450)
            else:
                st.error("Không thể xác định được địa điểm.")

        except Exception as e:
            st.error(f"Có lỗi xảy ra: {str(e)}")

if __name__ == "__main__":
    main()