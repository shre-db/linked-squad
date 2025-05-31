import sys
import os
import textwrap
# Add the project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

import streamlit as st
from streamlit_chat import message
import uuid
import json
from backend.orchestrator.state_schema import ProfileBotState
from backend.orchestrator.langgraph_graph import get_graph_runner
from linkedin.mock_profiles import get_mock_profile

# Page configuration
st.set_page_config(
    page_title="LinkedIn Assistant",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded",
)

class LinkedInGenieStreamlit:
    def __init__(self):
        # Initialize session state variables
        if 'session_id' not in st.session_state:
            st.session_state.session_id = str(uuid.uuid4())
        
        if 'bot_state' not in st.session_state:
            st.session_state.bot_state = ProfileBotState(session_id=st.session_state.session_id)
        
        if 'graph_runner' not in st.session_state:
            st.session_state.graph_runner = get_graph_runner()
        
        if 'messages' not in st.session_state:
            st.session_state.messages = []
        
        if 'linkedin_profile_loaded' not in st.session_state:
            st.session_state.linkedin_profile_loaded = False
        
        if 'welcome_animation_shown' not in st.session_state:
            st.session_state.welcome_animation_shown = False
        
        # Apply custom styling
        self._apply_custom_styling()

    def _load_svg_icon(self, icon_path):
        """Load and return SVG icon as base64 encoded string"""
        try:
            with open(icon_path, 'r') as f:
                svg_content = f.read()
            import base64
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

    def _format_structured_data(self, data, title):
        """Format structured data for display in the sidebar"""
        if not data:
            return ""
        
        formatted = f"### {title}\n\n"
        
        if isinstance(data, dict):
            for section, content in data.items():
                section_title = section.replace('_', ' ').title()
                formatted += f"**{section_title}:**\n"
                
                if isinstance(content, list):
                    for i, item in enumerate(content, 1):
                        if isinstance(item, dict):
                            formatted += f"  {i}. "
                            for key, value in item.items():
                                formatted += f"{key}: {value} | "
                            formatted = formatted.rstrip(" | ") + "\n"
                        else:
                            formatted += f"  - {item}\n"
                elif isinstance(content, dict):
                    for key, value in content.items():
                        formatted += f"  - {key}: {value}\n"
                else:
                    formatted += f"  {content}\n"
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
                st.header("📊 Profile Information")
            
            # Display LinkedIn profile info
            if st.session_state.bot_state.linkedin_data:
                profile = st.session_state.bot_state.linkedin_data
                st.success(f"✅ Profile loaded: {profile.get('name', 'Unknown')}")
                
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

    def _process_user_input(self, user_input):
        """Process user input through the graph runner"""
        # Check if user provided a LinkedIn URL
        if "linkedin.com/in/" in user_input:
            st.session_state.bot_state.linkedin_url = user_input
            st.session_state.bot_state.linkedin_data = get_mock_profile(linkedin_url=user_input)
            st.session_state.linkedin_profile_loaded = True
            
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
            st.session_state.bot_state = ProfileBotState.model_validate(updated_state_dict)
            
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

    def run(self):
        """Main Streamlit app interface"""
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
        
        # Display conversation history
        with chat_container:
            for i, msg in enumerate(st.session_state.messages):
                if msg["role"] == "user":
                    message(msg["content"], is_user=True, key=f"user_{i}")
                else:
                    message(msg["content"], is_user=False, key=f"bot_{i}")
        
        # Quick action buttons with custom icons
        st.markdown("#### Quick Actions")
        
        # Create more compact columns for buttons with reduced spacing
        col1, col2, col3, col4 = st.columns(4, gap="small")
        
        # # Load icons for buttons
        # linkedin_icon = self._load_svg_icon(os.path.join(project_root, "assets", "linkedin-logo.svg"))
        # trend_icon = self._load_svg_icon(os.path.join(project_root, "assets", "trend-up.svg"))
        # pencil_icon = self._load_svg_icon(os.path.join(project_root, "assets", "pencil-simple-line.svg"))
        # user_check_icon = self._load_svg_icon(os.path.join(project_root, "assets", "user-check.svg"))
        
        with col1:
            if st.button("Demo Profile", key="demo_btn", help="Load John Smith demo profile", use_container_width=True):
                demo_url = "https://www.linkedin.com/in/johnsmith"
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
        # Add user message to session
        st.session_state.messages.append({"role": "user", "content": user_input})
        
        # Process through the bot
        with st.spinner("Processing..."):
            bot_response = self._process_user_input(user_input)
        
        # Add bot response to session
        st.session_state.messages.append({"role": "assistant", "content": bot_response})
        
        # Rerun to update the interface
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

def main():
    app = LinkedInGenieStreamlit()
    app.run()

if __name__ == "__main__":
    main()