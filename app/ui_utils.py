import streamlit as st

def show_footer():
    st.markdown("---")
    st.markdown("Built with ❤️ | [GitHub](https://github.com/shre-db/linked-squad)")

def get_mock_profile():
    return {
        "name": "Jane Doe",
        "about": "Aspiring data scientist with strong foundations in ML and Python.",
        "experience": [
            {"title": "Data Analyst", "company": "Acme Corp", "description": "Worked on dashboards and reporting."}
        ],
        "skills": ["Python", "SQL", "Data Visualization"]
    }

def load_svg_icon(icon_path):
    """Load and return SVG icon as base64 encoded string"""
    try:
        with open(icon_path, 'r') as f:
            svg_content = f.read()
        import base64
        return base64.b64encode(svg_content.encode()).decode()
    except Exception as e:
        print(f"Error loading icon {icon_path}: {e}")
        return None