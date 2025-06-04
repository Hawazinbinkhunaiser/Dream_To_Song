import streamlit as st
import requests
import time
import json
from datetime import datetime
import base64
from io import BytesIO
import threading
from typing import Dict, List, Optional

# Page configuration
st.set_page_config(
    page_title="Suno AI Music Generator",
    page_icon="🎵",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .stProgress > div > div > div > div {
        background-color: #1f77b4;
    }
    .song-card {
        border: 1px solid #ddd;
        border-radius: 10px;
        padding: 20px;
        margin: 10px 0;
        background-color: #f9f9f9;
    }
    .status-badge {
        padding: 5px 10px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: bold;
        text-align: center;
        display: inline-block;
        margin: 5px 0;
    }
    .status-pending {
        background-color: #ffeaa7;
        color: #fdcb6e;
    }
    .status-processing {
        background-color: #74b9ff;
        color: #0984e3;
    }
    .status-complete {
        background-color: #00b894;
        color: #00cec9;
    }
    .status-error {
        background-color: #e17055;
        color: #d63031;
    }
</style>
""", unsafe_allow_html=True)

class SunoMusicGenerator:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://apibox.erweima.ai/api/v1"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    def generate_music(self, prompt: str, style: str = "", title: str = "", 
                      custom_mode: bool = True, instrumental: bool = False, 
                      model: str = "V4", negative_tags: str = "", 
                      callback_url: str = "https://httpbin.org/post") -> Dict:
        """Generate music using Suno API"""
        
        endpoint = f"{self.base_url}/generate"
        
        payload = {
            "prompt": prompt,
            "customMode": custom_mode,
            "instrumental": instrumental,
            "model": model,
            "callBackUrl": callback_url
        }
        
        if custom_mode:
            if not instrumental:
                payload["style"] = style
                payload["title"] = title
            else:
                payload["style"] = style
                payload["title"] = title
                # Remove prompt for instrumental in custom mode
                if instrumental:
                    payload.pop("prompt", None)
        
        if negative_tags:
            payload["negativeTags"] = negative_tags
        
        try:
            response = requests.post(endpoint, json=payload, headers=self.headers)
            return {
                "success": True,
                "status_code": response.status_code,
                "data": response.json()
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_generation_status(self, task_id: str) -> Dict:
        """Get status of music generation task"""
        # Based on the API documentation and common patterns, try these endpoints
        possible_endpoints = [
            f"{self.base_url}/details/{task_id}",  # Most likely based on docs
            f"{self.base_url}/task/{task_id}",
            f"{self.base_url}/generate/{task_id}",
            f"{self.base_url}/status/{task_id}",
            f"{self.base_url}/music/{task_id}",
            f"{self.base_url}/v1/details/{task_id}",
            f"{self.base_url}/api/v1/details/{task_id}",
            f"{self.base_url}/api/v1/task/{task_id}",
            f"{self.base_url}/api/v1/status/{task_id}"
        ]
        
        results = []
        
        for endpoint in possible_endpoints:
            try:
                response = requests.get(endpoint, headers=self.headers)
                result_data = {
                    "endpoint": endpoint,
                    "status_code": response.status_code,
                    "success": response.status_code == 200,
                    "response_text": response.text[:500] if response.text else "",
                }
                
                if response.status_code == 200:
                    try:
                        json_data = response.json()
                        result_data["data"] = json_data
                        results.append(result_data)
                        
                        # Return the first successful response
                        return {
                            "success": True,
                            "status_code": response.status_code,
                            "data": json_data,
                            "endpoint_used": endpoint,
                            "all_attempts": results
                        }
                    except:
                        result_data["error"] = "Invalid JSON response"
                
                results.append(result_data)
                
            except Exception as e:
                results.append({
                    "endpoint": endpoint,
                    "error": str(e),
                    "success": False
                })
        
        return {
            "success": False,
            "error": "No valid status endpoint found",
            "all_attempts": results
        }
    
    def get_music_details(self, task_id: str) -> Dict:
        """Get detailed music generation results using POST method"""
        # Some APIs require POST instead of GET
        possible_endpoints = [
            f"{self.base_url}/details",
            f"{self.base_url}/api/v1/details",
            f"{self.base_url}/fetch"
        ]
        
        for endpoint in possible_endpoints:
            try:
                # Try with task_id in body
                payload = {"task_id": task_id}
                response = requests.post(endpoint, json=payload, headers=self.headers)
                
                if response.status_code == 200:
                    return {
                        "success": True,
                        "status_code": response.status_code,
                        "data": response.json(),
                        "endpoint_used": endpoint
                    }
            except Exception as e:
                continue
        
        return {
            "success": False,
            "error": "No valid details endpoint found"
        }

def initialize_session_state():
    """Initialize session state variables"""
    if 'generated_songs' not in st.session_state:
        st.session_state.generated_songs = []
    if 'generation_status' not in st.session_state:
        st.session_state.generation_status = {}
    if 'api_key' not in st.session_state:
        st.session_state.api_key = ""

def validate_inputs(prompt: str, style: str, title: str, custom_mode: bool, 
                   instrumental: bool, model: str) -> tuple:
    """Validate user inputs based on API requirements"""
    errors = []
    
    # Model-specific limits
    if model in ["V3_5", "V4"]:
        prompt_limit = 3000 if custom_mode else 400
        style_limit = 200
    else:  # V4_5
        prompt_limit = 5000 if custom_mode else 400
        style_limit = 1000
    
    # Validate prompt
    if custom_mode:
        if not instrumental and len(prompt) > prompt_limit:
            errors.append(f"Prompt exceeds {prompt_limit} character limit for {model}")
        if not instrumental and not prompt.strip():
            errors.append("Prompt is required when not instrumental in custom mode")
    else:
        if len(prompt) > 400:
            errors.append("Prompt exceeds 400 character limit in non-custom mode")
        if not prompt.strip():
            errors.append("Prompt is required")
    
    # Validate style and title for custom mode
    if custom_mode:
        if not style.strip():
            errors.append("Style is required in custom mode")
        elif len(style) > style_limit:
            errors.append(f"Style exceeds {style_limit} character limit for {model}")
        
        if not title.strip():
            errors.append("Title is required in custom mode")
        elif len(title) > 80:
            errors.append("Title exceeds 80 character limit")
    
    return len(errors) == 0, errors

def check_and_update_status():
    """Check status of all pending generations and update accordingly"""
    if not st.session_state.api_key:
        return
    
    generator = SunoMusicGenerator(st.session_state.api_key)
    updated = False
    
    for song_key, status_info in st.session_state.generation_status.items():
        if status_info.get('status') == 'processing':
            task_id = status_info.get('task_id')
            if task_id:
                # Try to get status
                result = generator.get_generation_status(task_id)
                
                if result['success']:
                    data = result.get('data', {})
                    
                    # Check if generation is complete
                    if data.get('code') == 200 and data.get('data'):
                        song_data = data['data']
                        
                        # Check if we have audio URLs (indicates completion)
                        if isinstance(song_data, list) and len(song_data) > 0:
                            first_song = song_data[0]
                            if first_song.get('audio_url'):
                                # Mark as complete and add to generated songs
                                st.session_state.generation_status[song_key]['status'] = 'complete'
                                st.session_state.generated_songs.extend(song_data)
                                updated = True
                        
                        elif isinstance(song_data, dict) and song_data.get('audio_url'):
                            # Single song completed
                            st.session_state.generation_status[song_key]['status'] = 'complete'
                            st.session_state.generated_songs.append(song_data)
                            updated = True
                    
                    # Check for error status
                    elif data.get('code') != 200:
                        st.session_state.generation_status[song_key]['status'] = 'error'
                        st.session_state.generation_status[song_key]['error_message'] = data.get('msg', 'Unknown error')
                        updated = True
                
                # Try alternative method if first one fails
                elif not result['success']:
                    details_result = generator.get_music_details(task_id)
                    if details_result['success']:
                        # Process details_result similar to above
                        data = details_result.get('data', {})
                        if data.get('code') == 200 and data.get('data'):
                            song_data = data['data']
                            if isinstance(song_data, list) and len(song_data) > 0:
                                first_song = song_data[0]
                                if first_song.get('audio_url'):
                                    st.session_state.generation_status[song_key]['status'] = 'complete'
                                    st.session_state.generated_songs.extend(song_data)
                                    updated = True
    
    return updated
    """Display a song card with audio player and download button"""
    with st.container():
        st.markdown(f'<div class="song-card">', unsafe_allow_html=True)
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.subheader(f"🎵 {song_data.get('title', f'Song {index + 1}')}")
            st.write(f"**Style:** {song_data.get('tags', 'N/A')}")
            st.write(f"**Duration:** {song_data.get('duration', 0):.1f}s")
            st.write(f"**Model:** {song_data.get('model_name', 'N/A')}")
            st.write(f"**Created:** {song_data.get('createTime', 'N/A')}")
        
        with col2:
            if song_data.get('image_url'):
                try:
                    st.image(song_data['image_url'], width=150)
                except:
                    st.write("🎼 No image")
        
        # Audio player
        if song_data.get('audio_url'):
            st.audio(song_data['audio_url'])
            
            # Download button
            try:
                audio_response = requests.get(song_data['audio_url'])
                if audio_response.status_code == 200:
                    st.download_button(
                        label="📥 Download MP3",
                        data=audio_response.content,
                        file_name=f"{song_data.get('title', f'song_{index+1}')}.mp3",
                        mime="audio/mpeg",
                        key=f"download_{song_data.get('id', index)}"
                    )
            except Exception as e:
                st.error(f"Error preparing download: {str(e)}")
        
        # Show lyrics/prompt if available
        if song_data.get('prompt'):
            with st.expander("View Lyrics/Prompt"):
                st.text(song_data['prompt'])
        
        st.markdown('</div>', unsafe_allow_html=True)

def main():
    initialize_session_state()
    
    st.title("🎵 Suno AI Music Generator")
    st.markdown("Transform your lyrics into beautiful songs using Suno's AI models!")
    
    # Sidebar for API configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # API Key input
        api_key = st.text_input(
            "Suno API Key",
            type="password",
            value=st.session_state.api_key,
            help="f991f229712ece64cdc0b9bcaa58ccaf"
        )
        
        if api_key:
            st.session_state.api_key = api_key
        
        st.markdown("---")
        
        # Model selection
        model = st.selectbox(
            "Model Version",
            ["V4_5", "V4", "V3_5"],
            index=0,
            help="V4_5: Superior genre blending, up to 8 min\nV4: Best quality, up to 4 min\nV3_5: Creative diversity, up to 4 min"
        )
        
        # Mode selection
        custom_mode = st.checkbox(
            "Custom Mode",
            value=True,
            help="Enable for advanced settings with style and title control"
        )
        
        # Instrumental option
        instrumental = st.checkbox(
            "Instrumental Only",
            value=False,
            help="Generate music without vocals"
        )
    
    # Main content area
    if not st.session_state.api_key:
        st.warning("⚠️ Please enter your Suno API key in the sidebar to continue.")
        st.info("💡 Get your API key from the Suno API documentation.")
        return
    
    # Create tabs
    tab1, tab2, tab3 = st.tabs(["🎼 Generate Music", "📊 Generation Status", "🎵 Generated Songs"])
    
    with tab1:
        st.header("Generate Your Music")
        
        # Input form
        with st.form("music_generation_form"):
            # Lyrics/Prompt input
            if custom_mode and not instrumental:
                prompt = st.text_area(
                    "Song Lyrics",
                    height=200,
                    placeholder="Enter your song lyrics here...\n\n[Verse 1]\nYour lyrics here...\n\n[Chorus]\nMore lyrics...",
                    help=f"Max characters: {5000 if model == 'V4_5' else 3000}"
                )
            else:
                prompt = st.text_area(
                    "Music Description/Prompt",
                    height=100,
                    placeholder="Describe the music you want to generate...",
                    help=f"Max characters: {400 if not custom_mode else (5000 if model == 'V4_5' else 3000)}"
                )
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Style input (for custom mode)
                style = st.text_input(
                    "Music Style/Genre",
                    placeholder="e.g., Jazz, Classical, Electronic, Rock",
                    disabled=not custom_mode,
                    help=f"Required in custom mode. Max characters: {1000 if model == 'V4_5' else 200}"
                )
            
            with col2:
                # Title input (for custom mode)
                title = st.text_input(
                    "Song Title",
                    placeholder="Enter song title",
                    disabled=not custom_mode,
                    help="Required in custom mode. Max 80 characters"
                )
            
            # Negative tags (optional)
            negative_tags = st.text_input(
                "Exclude Styles (Optional)",
                placeholder="e.g., Heavy Metal, Upbeat Drums",
                help="Music styles to avoid in the generation"
            )
            
            # Generate button
            generate_button = st.form_submit_button(
                "🎵 Generate 2 Songs",
                type="primary",
                use_container_width=True
            )
        
        # Handle form submission
        if generate_button:
            # Validate inputs
            is_valid, errors = validate_inputs(prompt, style, title, custom_mode, instrumental, model)
            
            if not is_valid:
                for error in errors:
                    st.error(f"❌ {error}")
            else:
                # Initialize generator
                generator = SunoMusicGenerator(st.session_state.api_key)
                
                # Show generation progress
                progress_bar = st.progress(0, text="Preparing to generate songs...")
                status_placeholder = st.empty()
                
                # Generate songs
                with st.spinner("Generating your songs..."):
                    songs_generated = []
                    
                    for i in range(2):
                        progress_bar.progress((i + 1) * 50, text=f"Generating song {i + 1}/2...")
                        status_placeholder.info(f"🎵 Generating song {i + 1}...")
                        
                        result = generator.generate_music(
                            prompt=prompt,
                            style=style,
                            title=f"{title} - Version {i + 1}" if title else f"Generated Song {i + 1}",
                            custom_mode=custom_mode,
                            instrumental=instrumental,
                            model=model,
                            negative_tags=negative_tags
                        )
                        
                        if result['success'] and result['status_code'] == 200:
                            songs_generated.append(result['data'])
                            status_placeholder.success(f"✅ Song {i + 1} generation started successfully!")
                            
                            # Extract task_id from response more thoroughly
                            response_data = result['data']
                            task_id = None
                            
                            # Try different possible locations for task_id
                            if isinstance(response_data, dict):
                                # Common locations for task_id
                                task_id = (
                                    response_data.get('task_id') or 
                                    response_data.get('taskId') or
                                    response_data.get('id') or
                                    response_data.get('data', {}).get('task_id') or
                                    response_data.get('data', {}).get('taskId') or
                                    response_data.get('data', {}).get('id')
                                )
                                
                                # If still no task_id, look deeper
                                if not task_id and 'data' in response_data:
                                    data_section = response_data['data']
                                    if isinstance(data_section, list) and len(data_section) > 0:
                                        first_item = data_section[0]
                                        if isinstance(first_item, dict):
                                            task_id = (
                                                first_item.get('task_id') or
                                                first_item.get('taskId') or
                                                first_item.get('id')
                                            )
                            
                            # Store in session state with better task_id extraction
                            generation_key = f"song_{len(st.session_state.generated_songs) + len(songs_generated)}"
                            st.session_state.generation_status[generation_key] = {
                                "status": "processing",
                                "task_id": task_id,
                                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "prompt": prompt,
                                "style": style,
                                "title": f"{title} - Version {i + 1}" if title else f"Generated Song {i + 1}",
                                "model": model,
                                "full_response": response_data,  # Store full response for debugging
                                "generation_request": {  # Store original request for reference
                                    "custom_mode": custom_mode,
                                    "instrumental": instrumental,
                                    "negative_tags": negative_tags
                                }
                            }
                            
                            # Show task_id extraction info
                            if task_id:
                                status_placeholder.info(f"📝 Task ID extracted: {task_id}")
                            else:
                                status_placeholder.warning(f"⚠️ No task ID found in response for song {i + 1}. Check debug info in Status tab.")
                            
                            # Store the raw response for debugging
                            debug_key = f"debug_response_{generation_key}"
                            if 'debug_responses' not in st.session_state:
                                st.session_state.debug_responses = {}
                            st.session_state.debug_responses[debug_key] = response_data
                        else:
                            st.error(f"❌ Failed to generate song {i + 1}: {result.get('error', 'Unknown error')}")
                    
                    progress_bar.progress(100, text="Songs generation completed!")
                    
                    if songs_generated:
                        st.success(f"🎉 Successfully initiated generation of {len(songs_generated)} songs!")
                        st.info("📝 Check the 'Generation Status' tab to monitor progress and the 'Generated Songs' tab to play completed songs.")
    
    with tab2:
        st.header("📊 Generation Status")
        
        if not st.session_state.generation_status:
            st.info("No active generations. Generate some music first!")
        else:
            # Auto-refresh and manual refresh options
            col1, col2, col3 = st.columns([1, 1, 2])
            
            with col1:
                if st.button("🔄 Refresh Status", type="secondary"):
                    with st.spinner("Checking status..."):
                        updated = check_and_update_status()
                        if updated:
                            st.success("✅ Status updated!")
                            st.rerun()
                        else:
                            st.info("No status changes detected")
            
            with col2:
                auto_refresh = st.checkbox("Auto-refresh (30s)", value=False)
            
            with col3:
                if auto_refresh:
                    # Auto-refresh every 30 seconds
                    time.sleep(30)
                    updated = check_and_update_status()
                    if updated:
                        st.rerun()
            
            st.markdown("---")
            
            # Debug information and manual task check
            with st.expander("🔧 Debug Information & Manual Check"):
                st.markdown("**Current Session Data:**")
                st.json(st.session_state.generation_status)
                
                st.markdown("---")
                st.markdown("**Manual Task ID Check:**")
                st.info("If you have a task ID from Suno's logs, enter it here to check its status manually.")
                
                col_debug1, col_debug2 = st.columns([2, 1])
                with col_debug1:
                    manual_task_id = st.text_input("Enter Task ID:", placeholder="e.g., 2fac****9f72")
                with col_debug2:
                    if st.button("Check Manual ID", disabled=not manual_task_id.strip()):
                        if manual_task_id.strip() and st.session_state.api_key:
                            generator = SunoMusicGenerator(st.session_state.api_key)
                            
                            with st.spinner("Checking manual task ID..."):
                                result = generator.get_generation_status(manual_task_id.strip())
                                
                                if result['success']:
                                    st.success("✅ Found task data!")
                                    
                                    # Display the response
                                    st.json(result['data'])
                                    
                                    # Check if this contains completed songs
                                    data = result.get('data', {})
                                    if data.get('code') == 200 and data.get('data'):
                                        song_data = data['data']
                                        
                                        if isinstance(song_data, list):
                                            completed_songs = [song for song in song_data if song.get('audio_url')]
                                            if completed_songs:
                                                st.success(f"🎵 Found {len(completed_songs)} completed songs!")
                                                
                                                # Option to add to session
                                                if st.button("Add to Generated Songs", key="add_manual_songs"):
                                                    st.session_state.generated_songs.extend(completed_songs)
                                                    st.success("Songs added to Generated Songs tab!")
                                                    st.rerun()
                                        
                                        elif isinstance(song_data, dict) and song_data.get('audio_url'):
                                            st.success("🎵 Found 1 completed song!")
                                            if st.button("Add to Generated Songs", key="add_manual_song"):
                                                st.session_state.generated_songs.append(song_data)
                                                st.success("Song added to Generated Songs tab!")
                                                st.rerun()
                                
                                else:
                                    st.error("❌ Failed to get task data")
                                    st.json(result.get('all_attempts', []))
                
                st.markdown("---")
                st.markdown("**API Endpoint Testing Results:**")
                if st.button("Test All Endpoints", key="test_endpoints"):
                    if st.session_state.generation_status:
                        first_task = list(st.session_state.generation_status.values())[0]
                        test_task_id = first_task.get('task_id')
                        
                        if test_task_id:
                            generator = SunoMusicGenerator(st.session_state.api_key)
                            result = generator.get_generation_status(test_task_id)
                            
                            st.markdown("**Endpoint Test Results:**")
                            for attempt in result.get('all_attempts', []):
                                status_color = "🟢" if attempt.get('success') else "🔴"
                                st.markdown(f"{status_color} `{attempt.get('endpoint', 'Unknown')}` - Status: {attempt.get('status_code', 'Error')}")
                                
                                if attempt.get('response_text'):
                                    with st.expander(f"Response from {attempt.get('endpoint', 'Unknown')}"):
                                        st.text(attempt['response_text'])
                        else:
                            st.warning("No task ID found to test with")
            
            for song_key, status_info in st.session_state.generation_status.items():
                with st.container():
                    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
                    
                    with col1:
                        st.write(f"**{status_info.get('title', 'Unknown Title')}**")
                        st.write(f"Model: {status_info.get('model', 'N/A')}")
                        st.write(f"Started: {status_info.get('timestamp', 'N/A')}")
                    
                    with col2:
                        status = status_info.get('status', 'unknown')
                        if status == 'processing':
                            st.markdown('<span class="status-badge status-processing">🔄 Processing</span>', unsafe_allow_html=True)
                            # Show progress bar for processing
                            st.progress(50, text="Generating...")
                        elif status == 'complete':
                            st.markdown('<span class="status-badge status-complete">✅ Complete</span>', unsafe_allow_html=True)
                        elif status == 'error':
                            st.markdown('<span class="status-badge status-error">❌ Error</span>', unsafe_allow_html=True)
                            if status_info.get('error_message'):
                                st.error(f"Error: {status_info['error_message']}")
                        else:
                            st.markdown('<span class="status-badge status-pending">⏳ Pending</span>', unsafe_allow_html=True)
                    
                    with col3:
                        task_id = status_info.get('task_id')
                        if task_id:
                            st.code(f"Task: {task_id[:8]}...", language=None)
                        else:
                            st.warning("No Task ID")
                    
                    with col4:
                        # Manual check button for individual songs
                        if st.button(f"Check {song_key}", key=f"check_{song_key}"):
                            if task_id and st.session_state.api_key:
                                generator = SunoMusicGenerator(st.session_state.api_key)
                                result = generator.get_generation_status(task_id)
                                
                                if result['success']:
                                    st.success("✅ Status checked")
                                    with st.expander(f"Response for {song_key}"):
                                        st.json(result['data'])
                                else:
                                    st.error(f"❌ Failed: {result.get('error', 'Unknown error')}")
                
                st.markdown("---")
    
    with tab3:
        st.header("🎵 Generated Songs")
        
        if not st.session_state.generated_songs:
            st.info("No completed songs yet. Songs will appear here once generation is complete.")
            st.markdown("""
            **Note:** This demo shows the structure for displaying completed songs. 
            In a production app, you would:
            1. Implement webhook handling to receive completion callbacks
            2. Poll the API status endpoint periodically
            3. Update the songs list when generation completes
            """)
            
            # Show example of how completed songs would look
            st.markdown("---")
            st.subheader("Preview: How completed songs will appear")
            
            # Mock song data for demonstration
            mock_song = {
                "id": "demo_song_1",
                "title": "Demo Song",
                "tags": "demo, example",
                "duration": 180.5,
                "model_name": "chirp-v4",
                "createTime": "2025-01-01 12:00:00",
                "prompt": "[Verse]\nThis is a demo song\nShowing how the interface works\n[Chorus]\nWhen your songs are ready\nThey'll appear just like this",
                "audio_url": None,  # No actual audio for demo
                "image_url": None   # No actual image for demo
            }
            
            with st.container():
                st.markdown(f'<div class="song-card">', unsafe_allow_html=True)
                
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.subheader(f"🎵 {mock_song['title']} (Demo)")
                    st.write(f"**Style:** {mock_song['tags']}")
                    st.write(f"**Duration:** {mock_song['duration']}s")
                    st.write(f"**Model:** {mock_song['model_name']}")
                    st.write(f"**Created:** {mock_song['createTime']}")
                
                with col2:
                    st.write("🎼 Audio & Image")
                    st.write("Will appear here")
                
                st.info("🎵 Audio player and download button will appear here when songs are ready")
                
                with st.expander("View Lyrics/Prompt"):
                    st.text(mock_song['prompt'])
                
                st.markdown('</div>', unsafe_allow_html=True)
        else:
            # Display actual generated songs
            for i, song in enumerate(st.session_state.generated_songs):
                display_song_card(song, i)
                if i < len(st.session_state.generated_songs) - 1:
                    st.markdown("---")
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: gray; padding: 20px;'>
        🎵 Powered by Suno AI | Built with Streamlit<br>
        <small>Generated files are retained for 15 days before deletion</small>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
