import streamlit as st
import streamlit_authenticator as stauth
from modules.processor import *

import yaml
from yaml.loader import SafeLoader

with open('config.yaml') as file:
    config = yaml.load(file, Loader=SafeLoader)

# Pre-hashing all plain text passwords once
# stauth.Hasher.hash_passwords(config['credentials'])

authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)

try:
    authenticator.login()
except Exception as e:
    st.error(e)

if st.session_state['authentication_status']:

    # st.title('Some content')
    st.title("Image Metadata Modifier 📸")
    
    # Sidebar settings
    with st.sidebar:
        st.header("Settings")
        device_options = [
            "iPhone 15 Pro Max",
            "iPhone 15 Pro",
            "iPhone 15",
            "iPhone 14 Pro Max",
            "iPhone 14 Pro",
            "iPhone 14",
            "iPhone 13 Pro Max",
            "iPhone 13 Pro",
            "iPhone 13",
            "iPhone 12 Pro Max",
            "iPhone 12 Pro",
            "iPhone 11 Pro Max",
            "iPhone 11 Pro",
            "iPhone X",
            "iPhone XS Max",
            "iPhone 7",
            "iPhone 7 Plus",
            "iPhone 8"
        ]
        selected_device = st.selectbox("📱 Select Device", device_options)
        max_date = date(2024, 10, 11)
        selected_date = st.date_input(
            "📅 Select Date",
            max_value=max_date,
        )
        time_options = ["day", "night", "random"]
        selected_time = st.selectbox("🕒 Select Time of Day", time_options)
        authenticator.logout()
        st.write(f'Welcome *{st.session_state["name"]}*')
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
elif st.session_state['authentication_status'] is False:
    st.error('Username/password is incorrect')
elif st.session_state['authentication_status'] is None:
    st.warning('Please enter your username and password')