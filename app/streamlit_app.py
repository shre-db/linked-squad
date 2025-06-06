import sys
import os
import re
import textwrap
import base64
# Add the project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Load environment variables at startup
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(project_root, '.env'))
except ImportError:
    # dotenv not available, will rely on system environment
    pass

import streamlit as st
import uuid
import json
import time
# Delay imports that require API keys until after configuration

# from app.ui_utils import load_svg_icon

# gear_icon_path = os.path.join(project_root, "assets", "gear-light.svg")
# settings_icon = load_svg_icon(gear_icon_path)

# Page configuration
st.set_page_config(
    page_title="LinkedIn Assistant",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Clear Streamlit cache at the start of every session to prevent caching issues
def clear_streamlit_cache():
    """Clear all Streamlit cache to prevent lingering state issues between sessions"""
    try:
        # Clear all cached data (st.cache_data)
        st.cache_data.clear()
        
        # Clear all cached resources (st.cache_resource) 
        st.cache_resource.clear()
        
        # Also clear legacy cache if it exists (for older Streamlit versions)
        if hasattr(st, 'legacy_caching'):
            st.legacy_caching.clear_cache()
        
        # Clear any cached hash functions
        if hasattr(st, '_hash_funcs'):
            st._hash_funcs.clear()
        
        # Clear any cached singleton objects
        if hasattr(st, '_singleton_funcs'):
            st._singleton_funcs.clear()
        
        # Clear any cached memo functions (another legacy cache)
        if hasattr(st, 'memo'):
            try:
                st.memo.clear()
            except:
                pass
        
        # Clear any cached experimental memo functions
        if hasattr(st, 'experimental_memo'):
            try:
                st.experimental_memo.clear()
            except:
                pass
        
        # Clear any cached experimental singleton functions
        if hasattr(st, 'experimental_singleton'):
            try:
                st.experimental_singleton.clear()
            except:
                pass
        
        print("Streamlit cache cleared successfully")
    except Exception as e:
        print(f"Warning: Could not clear cache: {e}")

# Clear cache immediately when the app starts, before any other initialization
clear_streamlit_cache()

# Additional startup cache clearing for a completely fresh session
try:
    # Clear backend memory on app startup to prevent cross-session contamination
    from backend.memory import clear_memory
    clear_memory()
except:
    pass  # Ignore if backend not yet available

def clear_all_streamlit_state(clear_session_state=False):
    """Clear all Streamlit cache and optionally session state for a completely fresh start"""
    # First clear all caches
    clear_streamlit_cache()
    
    # Clear backend persistent state that could cause cross-session issues
    try:
        # Clear LangGraph memory saver
        from backend.memory import clear_memory
        clear_memory()
        print("Backend memory cleared successfully")
    except Exception as e:
        print(f"Warning: Could not clear backend memory: {e}")
    
    # Clear any cached agent instances by forcing re-import
    try:
        # Clear Python module cache for agents to force fresh instances
        import sys
        modules_to_clear = [
            'backend.orchestrator.handlers',
            'agents.router',
            'agents.career_guide', 
            'agents.content_rewriter',
            'agents.job_fit_evaluator',
            'agents.profile_analyzer'
        ]
        for module in modules_to_clear:
            if module in sys.modules:
                del sys.modules[module]
        print("Agent modules cleared successfully")
    except Exception as e:
        print(f"Warning: Could not clear agent modules: {e}")
    
    # Optionally clear session state (useful for complete reset)
    if clear_session_state and hasattr(st, 'session_state'):
        try:
            # Create a list of keys to avoid modifying dict during iteration
            keys_to_remove = list(st.session_state.keys())
            for key in keys_to_remove:
                del st.session_state[key]
            print("Session state cleared successfully")
        except Exception as e:
            print(f"Warning: Could not clear session state: {e}")

def _get_profile_bot_state():
    """Lazy import ProfileBotState to avoid premature initialization"""
    try:
        from backend.orchestrator.state_schema import ProfileBotState
        return ProfileBotState
    except Exception as e:
        st.error(f"Error importing ProfileBotState: {e}")
        return None

def _get_profile_function():
    """Lazy import get_profile to avoid premature initialization"""
    try:
        from linkedin.profiles import get_mock_profile
        return get_mock_profile
    except Exception as e:
        st.error(f"Error importing get_profile: {e}")
        return None
    
def _get_default_avatar():
    bot_path = os.path.join(os.path.dirname(__file__), "..", "assets", "sparkle-light.svg")
    user_path = os.path.join(os.path.dirname(__file__), "..", "assets", "user-light.svg")
    return bot_path, user_path

class LinkedInGenieStreamlit:
    def __init__(self):
        # Initialize session state variables
        if 'session_id' not in st.session_state:
            st.session_state.session_id = str(uuid.uuid4())
        
        # Only initialize bot_state after API keys are configured
        if 'bot_state' not in st.session_state:
            st.session_state.bot_state = None
        
        if 'graph_runner' not in st.session_state:
            st.session_state.graph_runner = None
        
        if 'messages' not in st.session_state:
            st.session_state.messages = []
        
        if 'linkedin_profile_loaded' not in st.session_state:
            st.session_state.linkedin_profile_loaded = False
        
        if 'welcome_animation_shown' not in st.session_state:
            st.session_state.welcome_animation_shown = False
        
        if 'pending_message' not in st.session_state:
            st.session_state.pending_message = None
        
        if 'processing' not in st.session_state:
            st.session_state.processing = False
        
        if 'api_keys_configured' not in st.session_state:
            st.session_state.api_keys_configured = self._check_existing_api_keys()
        
        if 'show_logout_dialog' not in st.session_state:
            st.session_state.show_logout_dialog = False
        
        if 'show_invalid_profile_dialog' not in st.session_state:
            st.session_state.show_invalid_profile_dialog = False
        
        # Apply custom styling
        self._apply_custom_styling()

    def _load_svg_icon(self, icon_path):
        """Load and return SVG icon as base64 encoded string"""
        try:
            with open(icon_path, 'r') as f:
                svg_content = f.read()
            return base64.b64encode(svg_content.encode()).decode()
        except Exception as e:
            print(f"Error loading icon {icon_path}: {e}")
            return None

    def _apply_custom_styling(self):
        """Apply custom CSS styling to improve font and overall appearance"""
        custom_css = """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Nunito+Sans:wght@300;400;500;600;700&display=swap');
        
        /* Main font family for the entire app */
        html, body, [class*="css"] {
            font-family: 'Nunito Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }
        
        /* Title styling */
        .main h1 {
            font-family: 'Nunito Sans', sans-serif;
            font-weight: 700;
            font-size: 2.5rem;
            color: #0A66C2;
            margin-bottom: 0.5rem;
        }
        
        /* Subtitle and description styling */
        .main p {
            font-family: 'Nunito Sans', sans-serif;
            font-weight: 400;
            font-size: 1.1rem;
            color: #5f6368;
            line-height: 1.6;
        }
        
        /* Headers in sidebar and main content */
        .main h2, .main h3, .sidebar h1, .sidebar h2, .sidebar h3 {
            font-family: 'Nunito Sans', sans-serif;
            font-weight: 600;
            color: #1f2937;
        }
        
        /* Button styling */
        .stButton > button {
            font-family: 'Nunito Sans', sans-serif;
            font-weight: 500;
            border-radius: 8px;
            border: 1px solid #e5e7eb;
            transition: all 0.2s ease;
        }
        
        .stButton > button:hover {
            border-color: #0A66C2;
            color: #0A66C2;
        }
        
        /* Chat input styling */
        .stChatInput > div > div > input {
            font-family: 'Nunito Sans', sans-serif;
            font-weight: 400;
        }
        
        /* Sidebar styling */
        .css-1d391kg {
            background-color: #f8fafc;
        }
        
        /* Welcome message styling */
        .main ul li {
            font-family: 'Nunito Sans', sans-serif;
            font-weight: 400;
            color: #374151;
            margin-bottom: 0.5rem;
        }
        
        /* Expander text */
        .streamlit-expanderHeader {
            font-family: 'Nunito Sans', sans-serif;
            font-weight: 500;
        }
        
        /* Success/info messages */
        .stSuccess, .stInfo, .stWarning, .stError {
            font-family: 'Nunito Sans', sans-serif;
        }
        
        /* Feature list styling */
        .feature-item {
            display: flex;
            align-items: center;
            margin-bottom: 1rem;
            padding: 0.75rem;
            background-color: #f8fafc;
            border-radius: 8px;
            border-left: 4px solid #0A66C2;
        }
        
        .feature-icon {
            width: 24px;
            height: 24px;
            margin-right: 12px;
            flex-shrink: 0;
        }
        
        .feature-content {
            flex: 1;
        }
        
        .feature-title {
            font-weight: 600;
            color: #1f2937;
            margin-bottom: 0.25rem;
        }
        
        .feature-description {
            font-size: 0.95rem;
            color: #6b7280;
            margin: 0;
        }
        
        /* Simple blinking cursor */
        @keyframes blink {
            0%, 50% { opacity: 1; }
            51%, 100% { opacity: 0; }
        }
        </style>
        """
        st.markdown(custom_css, unsafe_allow_html=True)

    def _check_existing_api_keys(self):
        """Check if API keys already exist and are valid"""
        # Check if .env file exists first - if not, API keys are definitely not configured
        env_path = os.path.join(project_root, '.env')
        if not os.path.exists(env_path):
            # Clear any existing environment variables that might be cached
            os.environ.pop('GOOGLE_API_KEY', None)
            os.environ.pop('APIFY_API_TOKEN', None)
            return False
        
        # Check environment variables that might be loaded from .env
        google_key = os.getenv('GOOGLE_API_KEY')
        # apify_key = os.getenv('APIFY_API_TOKEN')  # Commented out for now
        
        # If found in environment, validate them
        # For now, only require Google API key since we're using mock profiles
        if google_key:
            google_valid = (google_key not in ['', 'your_google_api_key_here'] and len(google_key) > 10)
            # apify_valid = (apify_key not in ['', 'your_apify_api_token_here'] and len(apify_key) > 10)
            
            if google_valid:  # and apify_valid (commented out)
                return True
        
        try:
            with open(env_path, 'r') as f:
                content = f.read()
            
            # Parse the content to extract key-value pairs
            google_key = None
            # apify_key = None  # Commented out for now
            
            for line in content.split('\n'):
                line = line.strip()
                if line.startswith('GOOGLE_API_KEY='):
                    google_key = line.split('=', 1)[1].strip()
                # elif line.startswith('APIFY_API_TOKEN='):  # Commented out for now
                #     apify_key = line.split('=', 1)[1].strip()
            
            # Validate that Google key exists and is not placeholder value
            google_valid = (google_key and 
                          google_key not in ['', 'your_google_api_key_here'] and
                          len(google_key) > 10)  # Basic length check
            
            # Commented out Apify validation
            # apify_valid = (apify_key and 
            #              apify_key not in ['', 'your_apify_api_token_here'] and
            #              len(apify_key) > 10)  # Basic length check
            
            # If Google key is valid in file, reload environment
            if google_valid:  # and apify_valid (commented out)
                try:
                    from dotenv import load_dotenv
                    load_dotenv(env_path, override=True)
                    return True
                except ImportError:
                    # Set environment variables manually if dotenv not available
                    os.environ['GOOGLE_API_KEY'] = google_key
                    # os.environ['APIFY_API_TOKEN'] = apify_key  # Commented out for now
                    return True
            
            return False
            
        except Exception as e:
            print(f"Error checking API keys: {e}")
            return False

    def _save_api_keys(self, google_api_key, apify_api_token=""):
        """Save API keys to .env file with improved validation"""
        # Trim whitespace
        google_api_key = google_api_key.strip()
        apify_api_token = apify_api_token.strip() if apify_api_token else ""
        
        # Basic validation for Google API key (required)
        if not google_api_key:
            st.error("❌ Google API key cannot be empty.")
            return False
        
        # Commented out Apify validation since we're using mock profiles
        # if not apify_api_token:
        #     st.error("❌ Apify API token cannot be empty.")
        #     return False
        
        # Check for placeholder values
        if google_api_key in ['your_google_api_key_here', 'enter_your_key_here']:
            st.error("❌ Please provide a valid Google API key (not placeholder text).")
            return False
        
        # Commented out Apify placeholder validation
        # if apify_api_token in ['your_apify_api_token_here', 'enter_your_token_here']:
        #     st.error("❌ Please provide a valid Apify API token (not placeholder text).")
        #     return False
        
        # Basic length validation for Google API key
        if len(google_api_key) < 10:
            st.error("❌ Google API key appears to be too short. Please check your key.")
            return False
        
        # Commented out Apify length validation
        # if len(apify_api_token) < 10:
        #     st.error("❌ Apify API token appears to be too short. Please check your token.")
        #     return False
        
        # Save to .env file
        env_path = os.path.join(project_root, '.env')
        # Include Apify token (even if empty) to maintain compatibility
        env_content = f"""# Google Gemini API key
GOOGLE_API_KEY={google_api_key}

# APIFY settings (currently using mock profiles)
APIFY_API_TOKEN={apify_api_token if apify_api_token else 'your_apify_api_token_here'}
"""
        try:
            with open(env_path, 'w') as f:
                f.write(env_content)
            
            # Reload environment variables
            try:
                from dotenv import load_dotenv
                load_dotenv(override=True)
                
                # Verify the keys were loaded into environment
                # For now, only check Google API key since Apify is not required
                if not os.getenv('GOOGLE_API_KEY'):
                    st.warning("Google API key saved but may not be loaded into environment yet.")
                    
            except ImportError:
                st.info("API key saved. You may need to restart the app to load it.")
            
            return True
            
        except Exception as e:
            st.error(f"❌ Failed to save API keys: {str(e)}")
            return False

    def _display_api_config_screen(self):
        """Display API key configuration screen"""
        # Load LinkedIn logo for banner
        linkedin_icon_path = os.path.join(project_root, "assets", "linkedin-logo.svg")
        key_icon_path = os.path.join(project_root, "assets", "key-duotone.svg")
        linkedin_icon_b64 = self._load_svg_icon(linkedin_icon_path)
        key_icon_b64 = self._load_svg_icon(key_icon_path)

        # LinkedIn Assistant Banner
        if linkedin_icon_b64:
            title_html = f"""
            <div style="display: flex; align-items: center; margin-bottom: 1rem;">
                <img src="data:image/svg+xml;base64,{linkedin_icon_b64}" 
                     style="width: 40px; height: 40px; margin-right: 12px;" 
                     alt="LinkedIn logo">
                <h1 style="margin: 0; font-family: 'Nunito Sans', sans-serif; font-weight: 700; font-size: 2.5rem; color: #0A66C2;">
                    LinkedIn Assistant
                </h1>
            </div>
            """
            st.markdown(title_html, unsafe_allow_html=True)
        else:
            # Fallback to emoji if icon can't be loaded
            st.title("💼 LinkedIn Assistant")
        
        st.markdown("Your AI-powered career advisor for LinkedIn optimization")
        
        st.markdown("---")
        
        # API Configuration section (centered)
        with st.container():
            col1, col2, col3 = st.columns([1, 3, 1])
            with col2:
                config_req_html = f"""
                <div style="display: flex; align-items: center; margin-bottom: 1rem;">
                    <img src="data:image/svg+xml;base64,{key_icon_b64}" 
                        style="width: 40px; height: 40px; margin-right: 12px;" 
                        alt="API key icon">
                    <h3 style="margin: 0; font-family: 'Nunito Sans', sans-serif; font-weight: 500; font-size: 2.0rem; color: #000000;">
                        API Configuration Required
                    </h3>
                </div>
                """
                st.markdown(config_req_html, unsafe_allow_html=True)
                st.markdown("Welcome! To get started with your AI career assistant, please provide your API key below.")
                # Check if .env file exists but keys are invalid
                env_path = os.path.join(project_root, '.env')
                if os.path.exists(env_path):
                    st.info("Found existing .env file, but API keys need to be updated or are invalid.", icon=":material/info:")

        st.markdown('<div style="height: 24px;"></div>', unsafe_allow_html=True)
        
        with st.container():
            # Create centered columns for better layout
            col1, col2, col3 = st.columns([1, 3, 1])
            with col2:
                # st.markdown("### Required API Key")
                # st.markdown("Google API key is required for the assistant to function properly:")
                
                # Add spacing before first API key section
                st.markdown("")

                gemini_key_html = f"""
                <div style="display: flex; align-items: center; margin-bottom: 0.3rem;">
                    <h3 style="margin: 0; font-family: 'Nunito Sans', sans-serif; font-weight: 500; font-size: 1.5rem; color: #000000;">
                        Google Gemini API Key
                    </h3>
                </div>                
                """

                st.markdown(gemini_key_html, unsafe_allow_html=True)
                st.markdown("- Visit [Google AI Studio](https://makersuite.google.com/app/apikey) to get your free API key")
                st.markdown("- This is used to power the AI conversation and analysis")
                st.markdown("")
                
                google_api_key = st.text_input(
                    "Google API Key",
                    type="password",
                    placeholder="Enter your Google Gemini API key...",
                    key="google_api_input",
                    help="Your Google Gemini API key from AI Studio"
                )
                
                # Temporarily commented out - using mock profiles for now
                # st.markdown("#### 2. Apify API Token")
                # st.markdown("• Visit [Apify Console](https://console.apify.com/account/integrations) to get your API token")
                # st.markdown("• This is used to scrape LinkedIn profile data")
                # 
                # apify_api_token = st.text_input(
                #     "Apify API Token",
                #     type="password",
                #     placeholder="Enter your Apify API token...",
                #     key="apify_api_input",
                #     help="Your Apify API token from the Console"
                # )
                
                # Set empty apify token for now since we're using mock profiles
                apify_api_token = ""
                
                # Add spacing before button section
                st.markdown("")
                # st.markdown("---")
                st.markdown("")
                
                # Save button with better styling - make it more prominent
                if st.button("Save API Key & Login", type="primary", use_container_width=False, icon=":material/save:"):
                    # For now, we only need Google API key since we're using mock profiles
                    if google_api_key:
                        if self._save_api_keys(google_api_key, apify_api_token):
                            st.session_state.api_keys_configured = True
                            st.success("API key saved successfully! Loading assistant...", icon=":material/check_circle:")
                            # Small delay to show success message before rerun
                            time.sleep(1)
                            st.rerun()
                    else:
                        st.warning("Please provide your Google API key to continue.")
                
                # Add helpful information
                st.markdown("")
                # st.markdown("---")
                st.markdown("")
                
                with st.expander("Why do we need this API key?", expanded=False, icon=":material/info:"):
                    st.markdown("""
                    **Google Gemini API Key:**
                    - Powers the AI conversation and profile analysis
                    - Provides intelligent career guidance and content suggestions
                    - Free tier available with generous usage limits
                    
                    **Note:** We're currently using mock / downloaded LinkedIn profiles for demonstration, so no Apify token is needed at this time.
                    
                    **Security Note:** Your API key is stored locally in a `.env` file and is not shared with anyone.
                    """)

    def _format_structured_data(self, data, title):
        """Format structured data for display in the sidebar"""
        if not data:
            return ""
        
        # Agent outputs are now markdown strings, so we can return them directly
        if isinstance(data, str):
            # Data is already markdown-formatted, return as-is
            return data
        
        # Legacy handling for dictionary data (if any still exists)
        formatted = ""
        if isinstance(data, dict):
            for section, content in data.items():
                # Skip certain meta fields that aren't meant for display
                if section in ['overall_score', 'overall_fit_score']:
                    continue
                    
                if isinstance(content, str):
                    # Content is already markdown-formatted, just add it
                    formatted += f"{content}\n\n"
                elif isinstance(content, (int, float)):
                    # Handle numeric values like scores
                    section_title = section.replace('_', ' ').title()
                    formatted += f"**{section_title}:** {content}\n\n"
                elif isinstance(content, list):
                    section_title = section.replace('_', ' ').title()
                    formatted += f"**{section_title}:**\n"
                    for item in content:
                        formatted += f"- {item}\n"
                    formatted += "\n"
                elif isinstance(content, dict):
                    section_title = section.replace('_', ' ').title()
                    formatted += f"**{section_title}:**\n"
                    for key, value in content.items():
                        formatted += f"- {key}: {value}\n"
                    formatted += "\n"
        
        return formatted

    def _display_sidebar_info(self):
        """Display structured information in the sidebar"""
        with st.sidebar:
            # Profile Information header - keep custom LinkedIn icon for branding
            linkedin_icon = self._load_svg_icon(os.path.join(project_root, "assets", "linkedin-logo.svg"))
            if linkedin_icon:
                header_html = f"""
                <div style="display: flex; align-items: center; margin-bottom: 1rem;">
                    <img src="data:image/svg+xml;base64,{linkedin_icon}" 
                         style="width: 20px; height: 20px; margin-right: 8px;" 
                         alt="Profile icon">
                    <h2 style="margin: 0; font-family: 'Nunito Sans', sans-serif; font-weight: 600; color: #1f2937;">
                        Profile Information
                    </h2>
                </div>
                """
                st.markdown(header_html, unsafe_allow_html=True)
            else:
                st.header("Profile Information")
            
            # Only display if bot_state is initialized
            if st.session_state.bot_state is None:
                st.info("Initializing assistant...")
                return
            
            # Display LinkedIn profile info
            if st.session_state.bot_state.linkedin_data:
                profile = st.session_state.bot_state.linkedin_data
                extracted_name = st.session_state.bot_state.linkedin_url.split("/")[-2] if st.session_state.bot_state.linkedin_url else "Unknown"
                st.success(f"Profile loaded: {extracted_name}", icon=":material/check_circle:")
                
                with st.expander("Profile Summary", expanded=True):
                    st.write(f"**About:** {profile.get('about', 'No description')}")
                    
                    if profile.get('skills'):
                        st.write("**Skills:**")
                        for skill in profile['skills']:
                            st.write(f"• {skill}")
            
            # Display analysis results with Material Symbols trending_up icon
            if st.session_state.bot_state.profile_analysis_report:
                with st.expander("Profile Analysis", expanded=False, icon=":material/person_check:"):
                    formatted = self._format_structured_data(
                        st.session_state.bot_state.profile_analysis_report, 
                        "Analysis Report"
                    )
                    st.markdown(formatted)
            
            # Display content suggestions with Material Symbols edit icon
            if st.session_state.bot_state.content_rewrites_suggestions:
                with st.expander("Content Suggestions", expanded=False, icon=":material/edit:"):
                    formatted = self._format_structured_data(
                        st.session_state.bot_state.content_rewrites_suggestions,
                        "Content Suggestions"
                    )
                    st.markdown(formatted)
            
            # Display job fit evaluation with Material Symbols person_check icon
            if st.session_state.bot_state.job_fit_evaluation_report:
                with st.expander("Job Fit Evaluation", expanded=False, icon=":material/fact_check:"):
                    formatted = self._format_structured_data(
                        st.session_state.bot_state.job_fit_evaluation_report,
                        "Job Fit Report"
                    )
                    st.markdown(formatted)
            
            # Display career guidance with Material Symbols work icon
            if st.session_state.bot_state.career_guidance_notes:
                with st.expander("Career Guidance", expanded=False, icon=":material/trending_up:"):
                    formatted = self._format_structured_data(
                        st.session_state.bot_state.career_guidance_notes,
                        "Career Guidance"
                    )
                    st.markdown(formatted)
            
            # Add settings section
            st.markdown("---")
            with st.expander("Settings", expanded=False, icon=":material/settings:"):
                st.markdown("**API Configuration**")
                if st.button("Reconfigure API Keys", help="Update your API keys", use_container_width=True, icon=":material/autorenew:"):
                    # Clear API key configuration to force reconfiguration
                    st.session_state.api_keys_configured = False
                    if 'api_keys_tested' in st.session_state:
                        del st.session_state.api_keys_tested
                    if 'keys_loaded_message_shown' in st.session_state:
                        del st.session_state.keys_loaded_message_shown
                    st.rerun()
                
                st.markdown("")
                st.markdown("**Session Management**")
                if st.button("Logout & Clear Data", help="Clear all data and API keys, then restart", use_container_width=True, type="secondary", icon=":material/logout:"):
                    st.session_state.show_logout_dialog = True
                    st.rerun()
                
                st.markdown("")
                st.markdown("**Development Tools**")
                if st.button("Full Reset (Dev)", help="Complete reset of all caches and state for development", use_container_width=True, type="secondary", icon=":material/refresh:"):
                    self._full_reset_for_development()

    def _validate_linkedin_url(self, user_input):
        """Validate if LinkedIn URL contains valid keywords"""
        valid_keywords = ["arjun-srivastava-ml", "michael-rodriguez-cfa", "sarah-chen-architect"]
        
        # Check if input contains a LinkedIn URL
        if "linkedin.com/in/" in user_input:
            # Check if any of the valid keywords are in the URL
            for keyword in valid_keywords:
                if keyword in user_input:
                    return True
            return False
        return True  # Not a LinkedIn URL, so no validation needed

    def _show_invalid_profile_dialog(self):
        """Show dialog when LinkedIn profile is not found"""
        @st.dialog("LinkedIn Profile Not Found")
        def profile_not_found():
            st.warning("**User not found**", icon=":material/person_off:")
            
            st.markdown("The LinkedIn profile you entered is not available in our system.")
            st.markdown("")
            st.markdown("**Please try one of the following URLs:**")
            
            # Show the valid URLs
            valid_urls = [
                "https://www.linkedin.com/in/arjun-srivastava-ml/",
                "https://www.linkedin.com/in/michael-rodriguez-cfa/", 
                "https://www.linkedin.com/in/sarah-chen-architect/"
            ]
            for url in valid_urls:
                st.markdown(f"```plaintext\n{url}\n```")

            st.markdown("")

            col1, col2, col3 = st.columns([1, 1, 1])
            with col2:
                if st.button("OK", type="primary", use_container_width=True):
                    st.session_state.show_invalid_profile_dialog = False
                    st.rerun()
        
        profile_not_found()

    def _clear_all_data(self):
        """Clear all session data including API keys and .env file"""
        # Clear .env file to remove stored API keys
        env_path = os.path.join(project_root, '.env')
        if os.path.exists(env_path):
            try:
                os.remove(env_path)
            except Exception as e:
                st.error(f"Error removing .env file: {e}")
        
        # Clear environment variables to remove API keys from memory
        os.environ.pop('GOOGLE_API_KEY', None)
        os.environ.pop('APIFY_API_TOKEN', None)
        
        # Use the comprehensive clearing function to clear everything
        clear_all_streamlit_state(clear_session_state=True)
    
    def _show_logout_dialog(self):
        """Show logout confirmation dialog"""
        @st.dialog("Confirm Logout")
        def logout_confirmation():
            st.warning("**Are you sure you want to logout?**", icon=":material/warning:")
            
            st.markdown("This will:")
            st.markdown("- Clear all your session data")
            st.markdown("- Remove stored API keys from your device")
            st.markdown("- Clear conversation history")
            st.markdown("- Clear profile data")
            st.markdown("- Restart the application")
            
            st.markdown("")
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("Cancel", use_container_width=True):
                    st.session_state.show_logout_dialog = False
                    st.rerun()
            
            with col2:
                if st.button("Yes, Logout", type="primary", use_container_width=True):
                    self._clear_all_data()
                    st.success("Data cleared successfully! Restarting...", icon=":material/check_circle:")
                    time.sleep(2)  # Brief delay to show success message
                    st.rerun()
        
        logout_confirmation()

    def _initialize_graph_runner(self):
        """Initialize the graph runner with proper error handling"""
        if st.session_state.graph_runner is None:
            try:
                # Import only when needed to avoid premature initialization
                from backend.orchestrator.langgraph_graph import get_graph_runner
                st.session_state.graph_runner = get_graph_runner()
                return True
            except Exception as e:
                st.error(f"❌ Error initializing the assistant: {str(e)}")
                st.error("Please check your API keys and try again.")
                return False
        return True

    def _process_user_input(self, user_input):
        """Process user input through the graph runner"""
        # Initialize graph runner if not already done (after API keys are configured)
        if not self._initialize_graph_runner():
            return "Failed to initialize the assistant. Please check your API keys."
        
        # Validate LinkedIn URL before processing
        if not self._validate_linkedin_url(user_input):
            st.session_state.show_invalid_profile_dialog = True
            return "Invalid LinkedIn profile URL. Please check the dialog for valid options."
        
        # Check if user provided a LinkedIn URL
        if "linkedin.com/in/" in user_input:
            get_mock_profile = _get_profile_function()
            if get_mock_profile:
                st.session_state.bot_state.linkedin_url = user_input
                # Parse linked URL from user_input starting with https://
                # Extract the LinkedIn URL from user_input (handles cases where user pastes extra text)
                match = re.search(r"(https?://[^\s]+linkedin\.com/in/[^\s]+)", user_input)
                parsed_url = match.group(1) if match else user_input
                st.session_state.bot_state.linkedin_data = get_mock_profile(linkedin_url=parsed_url)
                st.session_state.linkedin_profile_loaded = True
            else:
                return "Error: Could not load profile scraping function. Please check your setup."
            
        # Update state with user input
        st.session_state.bot_state.user_input = user_input
        st.session_state.bot_state.conversation_history.append({
            "role": "user", 
            "content": user_input
        })
        
        # Process through graph runner
        try:
            updated_state_dict = st.session_state.graph_runner.invoke(
                st.session_state.bot_state.model_dump(),
                config={"configurable": {"thread_id": st.session_state.bot_state.session_id}},
            )
            ProfileBotState = _get_profile_bot_state()
            if ProfileBotState:
                st.session_state.bot_state = ProfileBotState.model_validate(updated_state_dict)
            else:
                return "Error: Could not load bot state. Please check your setup."
            
            # Get bot response
            bot_response = st.session_state.bot_state.current_bot_response or "I'm processing your request..."
            
            # Add to conversation history
            if bot_response:
                st.session_state.bot_state.conversation_history.append({
                    "role": "assistant",
                    "content": bot_response
                })
            
            return bot_response
            
        except Exception as e:
            error_msg = f"Sorry, I encountered an error: {str(e)}"
            st.session_state.bot_state.conversation_history.append({
                "role": "assistant",
                "content": error_msg
            })
            return error_msg

    def _initialize_bot_state_if_needed(self):
        """Initialize bot state after API keys are configured"""
        if st.session_state.bot_state is None and st.session_state.api_keys_configured:
            ProfileBotState = _get_profile_bot_state()
            if ProfileBotState:
                st.session_state.bot_state = ProfileBotState(session_id=st.session_state.session_id)
                return True
            else:
                st.error("❌ Failed to initialize bot state. Please check your configuration.")
                return False
        return True

    def run(self):
        """Main Streamlit app interface"""
        # Handle logout dialog
        if st.session_state.get('show_logout_dialog', False):
            self._show_logout_dialog()
            return
        
        # Handle invalid profile dialog
        if st.session_state.get('show_invalid_profile_dialog', False):
            self._show_invalid_profile_dialog()
            return
        
        # Double-check API keys are configured and .env file exists
        # This ensures proper behavior after logout when .env file is deleted
        env_path = os.path.join(project_root, '.env')
        if not os.path.exists(env_path) or not st.session_state.api_keys_configured:
            # Force re-check of API keys if .env file doesn't exist
            st.session_state.api_keys_configured = self._check_existing_api_keys()
            
        # Check if API keys are configured
        if not st.session_state.api_keys_configured:
            self._display_api_config_screen()
            return
        
        # Show confirmation when keys are loaded from existing .env (only once)
        if st.session_state.api_keys_configured and 'keys_loaded_message_shown' not in st.session_state:
            if os.path.exists(os.path.join(project_root, '.env')):
                st.success("API keys loaded from existing configuration!", icon=":material/check_circle:")
            st.session_state.keys_loaded_message_shown = True
        
        # Test API keys if they were just configured
        if st.session_state.api_keys_configured and 'api_keys_tested' not in st.session_state:
            with st.spinner("Testing API keys..."):
                is_valid, message = self._test_api_keys()
                if not is_valid:
                    st.error(f"❌ API key validation failed: {message}")
                    st.error("Please check your API keys and restart the app.")
                    if st.button("Reconfigure API Keys", icon=":material/autorenew:"):
                        st.session_state.api_keys_configured = False
                        st.rerun()
                    return
                else:
                    st.session_state.api_keys_tested = True
        
        # Initialize bot state if needed
        if not self._initialize_bot_state_if_needed():
            return
        
        # Load LinkedIn logo for title
        linkedin_icon_path = os.path.join(project_root, "assets", "linkedin-logo.svg")
        linkedin_icon_b64 = self._load_svg_icon(linkedin_icon_path)
        
        if linkedin_icon_b64:
            title_html = f"""
            <div style="display: flex; align-items: center; margin-bottom: 1rem;">
                <img src="data:image/svg+xml;base64,{linkedin_icon_b64}" 
                     style="width: 40px; height: 40px; margin-right: 12px;" 
                     alt="LinkedIn logo">
                <h1 style="margin: 0; font-family: 'Nunito Sans', sans-serif; font-weight: 700; font-size: 2.5rem; color: #0A66C2;">
                    LinkedIn Assistant
                </h1>
            </div>
            """
            st.markdown(title_html, unsafe_allow_html=True)
        else:
            # Fallback to emoji if icon can't be loaded
            st.title("💼 LinkedIn Assistant")
        
        st.markdown("Your AI-powered career advisor for LinkedIn optimization")
        
        # Display sidebar information
        self._display_sidebar_info()
        
        # Main chat interface
        st.markdown("---")
        
        # Display welcome message if no conversation history and animation not shown yet
        if not st.session_state.messages and not st.session_state.welcome_animation_shown:
            st.markdown("#### Welcome to LinkedIn Assistant! I can help you with:")
            
            # Define features with their corresponding icons
            features = [
                {
                    "icon": "user-check.svg",
                    "title": "Profile Analysis",
                    "description": "Analyze your LinkedIn profile for improvements"
                },
                {
                    "icon": "pencil-simple-line.svg", 
                    "title": "Content Rewriting",
                    "description": "Suggest better ways to present your experience"
                },
                {
                    "icon": "read-cv-logo.svg",
                    "title": "Job Fit Evaluation", 
                    "description": "Evaluate how well you match specific job requirements"
                },
                {
                    "icon": "trend-up.svg",
                    "title": "Career Guidance",
                    "description": "Provide personalized career advice"
                }
            ]
            
            # Display features with streaming effect only on first load
            for i, feature in enumerate(features):
                icon_path = os.path.join(project_root, "assets", feature["icon"])
                icon_b64 = self._load_svg_icon(icon_path)
                
                if icon_b64:
                    # Use streaming effect with staggered delays
                    self._display_streaming_feature(
                        icon_b64, 
                        feature["title"], 
                        feature["description"], 
                        delay=0.01 * i  # Staggered delay for each feature
                    )
                else:
                    # Fallback if icon can't be loaded
                    st.markdown(f"- **{feature['title']}** - {feature['description']}")
            
            # Set flag to indicate welcome animation has been shown
            st.session_state.welcome_animation_shown = True
            
        elif not st.session_state.messages and st.session_state.welcome_animation_shown:
            # Display static welcome message (no animation) if already shown before
            st.markdown("#### Welcome to LinkedIn Assistant! I can help you with:")
            
            features = [
                {
                    "icon": "user-check.svg",
                    "title": "Profile Analysis",
                    "description": "Analyze your LinkedIn profile for improvements"
                },
                {
                    "icon": "pencil-simple-line.svg", 
                    "title": "Content Rewriting",
                    "description": "Suggest better ways to present your experience"
                },
                {
                    "icon": "read-cv-logo.svg",
                    "title": "Job Fit Evaluation", 
                    "description": "Evaluate how well you match specific job requirements"
                },
                {
                    "icon": "trend-up.svg",
                    "title": "Career Guidance",
                    "description": "Provide personalized career advice"
                }
            ]
            
            # Display features without animation (static)
            for feature in features:
                icon_path = os.path.join(project_root, "assets", feature["icon"])
                icon_b64 = self._load_svg_icon(icon_path)
                
                if icon_b64:
                    # Display static feature without streaming
                    feature_html = f"""
                    <div class="feature-item">
                        <img src="data:image/svg+xml;base64,{icon_b64}" class="feature-icon" alt="{feature['title']} icon">
                        <div class="feature-content">
                            <div class="feature-title">{feature['title']}</div>
                            <div class="feature-description">{feature['description']}</div>
                        </div>
                    </div>
                    """
                    st.markdown(feature_html, unsafe_allow_html=True)
                else:
                    # Fallback if icon can't be loaded
                    st.markdown(f"- **{feature['title']}** - {feature['description']}")
        
        if not st.session_state.messages:
            st.markdown("---")
        
        # Chat container
        chat_container = st.container()

        bot_path, user_path = _get_default_avatar()
        
        # Display conversation history FIRST
        with chat_container:
            for i, msg in enumerate(st.session_state.messages):
                if msg["role"] == "user":
                    with st.chat_message("user", avatar=user_path):
                        st.write(msg["content"])
                else:
                    with st.chat_message("assistant", avatar=bot_path):
                        st.write(msg["content"])
        
        # Handle pending message processing AFTER chat messages are displayed
        if st.session_state.pending_message and not st.session_state.processing:
            st.session_state.processing = True
            with chat_container:
                with st.spinner("Processing..."):
                    bot_response = self._process_user_input(st.session_state.pending_message)
            
            # Add bot response to session
            st.session_state.messages.append({"role": "assistant", "content": bot_response})
            
            # Clear pending message and processing flag
            st.session_state.pending_message = None
            st.session_state.processing = False
            st.rerun()
        
        # Quick action buttons with custom icons
        # st.markdown("#### Quick Actions")
        
        # Create more compact columns for buttons with reduced spacing
        col1, col2, col3, col4 = st.columns(4, gap="small")
        
        with col1:
            if st.button("Demo Profile", key="demo_btn", help="Load Michael Rodriguez demo profile", use_container_width=True):
                demo_url = "https://www.linkedin.com/in/michael-rodriguez-cfa/"
                self._handle_user_input(demo_url)
        
        with col2:
            if st.button("Analyze Profile", key="analyze_btn", help="Analyze your LinkedIn profile", use_container_width=True):
                self._handle_user_input("Analyze my LinkedIn profile")
        
        with col3:
            if st.button("Improve Content", key="content_btn", help="Get content improvement suggestions", use_container_width=True):
                self._handle_user_input("Help me rewrite my profile content")
        
        with col4:
            if st.button("Job Fit Check", key="jobfit_btn", help="Evaluate job fit", use_container_width=True):
                self._handle_user_input("Evaluate my job fit")
        
        # Chat input
        user_input = st.chat_input("Type your message here...")
        
        if user_input:
            self._handle_user_input(user_input)

    def _handle_user_input(self, user_input):
        """Handle user input and update the chat"""
        # Add user message to session immediately
        st.session_state.messages.append({"role": "user", "content": user_input})
        
        # Set pending message for processing on next run
        st.session_state.pending_message = user_input
        
        # Rerun to show the user's message and trigger processing
        st.rerun()

    def _display_streaming_feature(self, icon_b64, title, description, delay=0):
        """Display a feature with streaming text effect using Python and time module"""
        import time
        
        # Create placeholder for the feature item
        feature_container = st.empty()
        
        # Initial empty state
        if delay > 0:
            time.sleep(delay)
        
        # Show icon and container
        feature_html = f"""
        <div class="feature-item">
            <img src="data:image/svg+xml;base64,{icon_b64}" class="feature-icon" alt="{title} icon">
            <div class="feature-content">
                <div class="feature-title" id="title-text"></div>
                <div class="feature-description" id="desc-text"></div>
            </div>
        </div>
        """
        
        # Stream title character by character
        title_placeholder = st.empty()
        title_text = ""
        for char in title:
            title_text += char
            title_html = f"""
            <div class="feature-item">
                <img src="data:image/svg+xml;base64,{icon_b64}" class="feature-icon" alt="{title} icon">
                <div class="feature-content">
                    <div class="feature-title">{title_text}<span style="animation: blink 1s infinite;">|</span></div>
                    <div class="feature-description"></div>
                </div>
            </div>
            """
            title_placeholder.markdown(title_html, unsafe_allow_html=True)
            time.sleep(0.005)  # delay between characters
        
        # Remove cursor and add description
        time.sleep(0.01)  # Pause before description
        
        # Stream description character by character
        desc_text = ""
        for char in description:
            desc_text += char
            final_html = f"""
            <div class="feature-item">
                <img src="data:image/svg+xml;base64,{icon_b64}" class="feature-icon" alt="{title} icon">
                <div class="feature-content">
                    <div class="feature-title">{title}</div>
                    <div class="feature-description">{desc_text}<span style="animation: blink 1s infinite;">|</span></div>
                </div>
            </div>
            """
            title_placeholder.markdown(final_html, unsafe_allow_html=True)
            time.sleep(0.005)  # 30ms delay between characters
        
        # Final state without cursor
        time.sleep(0.01)
        final_html_clean = f"""
        <div class="feature-item">
            <img src="data:image/svg+xml;base64,{icon_b64}" class="feature-icon" alt="{title} icon">
            <div class="feature-content">
                <div class="feature-title">{title}</div>
                <div class="feature-description">{desc_text}</div>
            </div>
        </div>
        """
        title_placeholder.markdown(final_html_clean, unsafe_allow_html=True)

    def _test_api_keys(self):
        """Test if the configured API keys are working"""
        try:
            # Test Google API key (only required one for now)
            google_key = os.getenv('GOOGLE_API_KEY')
            # apify_key = os.getenv('APIFY_API_TOKEN')  # Commented out for mock profiles
            
            if not google_key:
                return False, "Google API key not found in environment"
            
            # Basic format check for Google API key
            if not google_key.startswith('AI') or len(google_key) < 30:
                return False, "Google API key format appears invalid"
            
            # Commented out Apify validation since we're using mock profiles
            # if len(apify_key) < 20:
            #     return False, "Apify API token format appears invalid"
            
            return True, "Google API key appears valid"
            
        except Exception as e:
            return False, f"Error testing API keys: {str(e)}"

    def _full_reset_for_development(self):
        """Complete reset for development - clears everything including backend state"""
        try:
            # Clear all Streamlit cache and backend state
            clear_all_streamlit_state(clear_session_state=True)
            
            # Clear environment variables
            os.environ.pop('GOOGLE_API_KEY', None)
            os.environ.pop('APIFY_API_TOKEN', None)
            
            # Additional Python cache clearing
            import gc
            gc.collect()  # Force garbage collection
            
            st.success("Complete reset performed - all caches and state cleared!", icon=":material/check_circle:")
            time.sleep(1)
            st.rerun()
            
        except Exception as e:
            st.error(f"Error during full reset: {e}")

def main():
    app = LinkedInGenieStreamlit()
    app.run()

if __name__ == "__main__":
    main()
