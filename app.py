"""
VERA-WA - Verification Engine for Results & Accountability
Streamlit Web Application for Washington State Education Data

Phase II infrastructure for Washington's accountability redesign.
Connects inputs, outputs, and outcomes at the individual student level.

Data sourced from data.wa.gov open data portal (OSPI datasets).
"""

import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# =============================================================================
# Configuration
# =============================================================================

st.set_page_config(
    page_title="VERA-WA | Washington Education Accountability",
    page_icon="🌲",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Washington State Colors
FOREST_GREEN = "#2E4A3F"
DARK_GREEN = "#1a2e26"
GOLD = "#C5A900"
WHITE = "#FFFFFF"
CREAM = "#F8F8F5"

# Custom CSS
st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Public+Sans:wght@400;600;700&display=swap');

    .stApp {{
        background-color: {CREAM};
    }}

    section[data-testid="stSidebar"] {{
        background-color: {FOREST_GREEN};
    }}
    section[data-testid="stSidebar"] .stMarkdown {{
        color: white;
    }}
    section[data-testid="stSidebar"] label {{
        color: white !important;
    }}
    section[data-testid="stSidebar"] .stRadio label,
    section[data-testid="stSidebar"] .stRadio label span,
    section[data-testid="stSidebar"] .stRadio label p,
    section[data-testid="stSidebar"] .stRadio label div {{
        color: white !important;
    }}

    h1, h2, h3 {{
        font-family: 'Public Sans', sans-serif;
        color: {FOREST_GREEN};
    }}
    h1 {{
        border-bottom: 4px solid {GOLD};
        padding-bottom: 16px;
    }}

    .stat-card {{
        background: white;
        padding: 20px;
        border-radius: 8px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        border-left: 4px solid {FOREST_GREEN};
    }}
    .stat-card .value {{
        font-size: 2.5rem;
        font-weight: 700;
        color: {FOREST_GREEN};
    }}
    .stat-card .label {{
        font-size: 0.9rem;
        color: #666;
    }}

    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
</style>
""", unsafe_allow_html=True)

# =============================================================================
# Data Functions - Washington State data.wa.gov API (OSPI Datasets)
# =============================================================================

# Working Socrata API endpoints from data.wa.gov
ENROLLMENT_ENDPOINT = "https://data.wa.gov/resource/2rwv-gs2e.json"  # 2024-25 Enrollment
ASSESSMENT_ENDPOINT = "https://data.wa.gov/resource/x73g-mrqp.json"  # 2023-24 Assessment


@st.cache_data(ttl=3600)
def fetch_enrollment_data(limit=50000):
    """Fetch enrollment data from data.wa.gov OSPI dataset."""
    try:
        # Query school-level enrollment aggregated from grade-level records
        response = requests.get(
            ENROLLMENT_ENDPOINT,
            params={
                "$limit": limit,
                "$where": "organizationlevel='School' AND schoolname IS NOT NULL",
            },
            timeout=60
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error fetching enrollment data: {e}")
        return []


@st.cache_data(ttl=3600)
def fetch_assessment_data(limit=10000):
    """Fetch SBAC assessment data from data.wa.gov OSPI dataset."""
    try:
        response = requests.get(
            ASSESSMENT_ENDPOINT,
            params={
                "$limit": limit,
                "$where": "organizationlevel='School' AND testadministration='SBAC'",
            },
            timeout=60
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error fetching assessment data: {e}")
        return []


def safe_int(value, default=0):
    """Safely convert value to int."""
    try:
        if value is None or value == "" or value == "N/A":
            return default
        return int(float(value))
    except (ValueError, TypeError):
        return default


def safe_float(value, default=0.0):
    """Safely convert value to float."""
    try:
        if value is None or value == "" or value == "N/A":
            return default
        # Handle percentage strings
        if isinstance(value, str) and value.endswith('%'):
            return float(value.rstrip('%'))
        return float(value)
    except (ValueError, TypeError):
        return default


def aggregate_schools(enrollment_data):
    """Aggregate enrollment data to school level with totals."""
    if not enrollment_data:
        return pd.DataFrame()

    df = pd.DataFrame(enrollment_data)

    # Convert enrollment columns to numeric
    for col in ['all_students', 'low_income', 'english_language_learners',
                'students_with_disabilities', 'homeless']:
        if col in df.columns:
            df[col] = df[col].apply(safe_int)

    # Aggregate by school
    agg_cols = {
        'all_students': 'sum',
        'districtname': 'first',
        'county': 'first',
        'currentschooltype': 'first',
        'esdname': 'first',
    }

    # Add optional columns if present
    for col in ['low_income', 'english_language_learners', 'students_with_disabilities', 'homeless']:
        if col in df.columns:
            agg_cols[col] = 'sum'

    schools = df.groupby('schoolname').agg(agg_cols).reset_index()

    # Filter out district totals and invalid entries
    schools = schools[~schools['schoolname'].str.contains('District Total', case=False, na=False)]
    schools = schools[schools['all_students'] > 0]

    # Calculate percentages
    if 'low_income' in schools.columns:
        schools['pct_low_income'] = (schools['low_income'] / schools['all_students'] * 100).round(1)
    if 'english_language_learners' in schools.columns:
        schools['pct_ell'] = (schools['english_language_learners'] / schools['all_students'] * 100).round(1)
    if 'students_with_disabilities' in schools.columns:
        schools['pct_swd'] = (schools['students_with_disabilities'] / schools['all_students'] * 100).round(1)

    return schools


# =============================================================================
# Sidebar
# =============================================================================

with st.sidebar:
    st.markdown(f"""
        <div style="text-align: center; padding: 20px 0;">
            <span style="font-size: 3rem;">🌲</span>
            <h2 style="color: white; margin: 10px 0;">VERA-WA</h2>
            <p style="color: {GOLD}; font-size: 0.9rem;">Verification Engine for Results & Accountability</p>
            <p style="color: rgba(255,255,255,0.6); font-size: 0.8rem;">Washington State</p>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    page = st.radio(
        "Navigate",
        ["📊 School Dashboard", "📈 Assessment Analysis", "🎓 Phase II Infrastructure", "ℹ️ About VERA-WA"],
        label_visibility="collapsed"
    )

    st.markdown(f"""
        <div style="
            height: 4px;
            background: linear-gradient(90deg, {GOLD}, #D4AF37, {GOLD});
            margin: 30px 0 20px 0;
            border-radius: 2px;
        "></div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
        <p style="color: {GOLD}; font-size: 1.4rem; font-weight: 700; text-align: center; margin: 12px 0 6px 0;">
            VERA-WA v0.1
        </p>
        <p style="color: white; font-size: 0.9rem; text-align: center; margin: 0 0 12px 0;">
            Phase II Infrastructure
        </p>
        <p style="text-align: center;">
            <a href="https://data.wa.gov" target="_blank" style="
                color: {GOLD};
                font-size: 1rem;
                font-weight: 600;
                text-decoration: none;
                border-bottom: 2px solid {GOLD};
            ">data.wa.gov Open Data</a>
        </p>
    """, unsafe_allow_html=True)


# =============================================================================
# Load Data
# =============================================================================

enrollment_raw = fetch_enrollment_data()
schools_df = aggregate_schools(enrollment_raw)


# =============================================================================
# Page: School Dashboard
# =============================================================================

if page == "📊 School Dashboard":
    st.title("Washington School Dashboard")
    st.caption("Live data from data.wa.gov • OSPI Report Card Enrollment 2024-25")

    if schools_df.empty:
        st.error("Unable to load enrollment data. Please try again later.")
    else:
        # Filters
        col1, col2, col3 = st.columns(3)
        with col1:
            counties = ["All"] + sorted(schools_df["county"].dropna().unique().tolist())
            selected_county = st.selectbox("County", counties)
        with col2:
            districts = ["All"] + sorted(schools_df["districtname"].dropna().unique().tolist())
            selected_district = st.selectbox("District", districts)
        with col3:
            school_types = {
                "All": "All",
                "P": "Public Schools",
                "A": "Alternative",
                "V": "Vocational/Skills Center",
                "S": "Special Education",
            }
            selected_type = st.selectbox("School Type", list(school_types.keys()),
                                         format_func=lambda x: school_types.get(x, x))

        # Filter data
        filtered = schools_df.copy()
        if selected_county != "All":
            filtered = filtered[filtered["county"] == selected_county]
        if selected_district != "All":
            filtered = filtered[filtered["districtname"] == selected_district]
        if selected_type != "All":
            filtered = filtered[filtered["currentschooltype"] == selected_type]

        # Summary stats
        st.markdown("### Overview")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown(f"""
                <div class="stat-card">
                    <div class="value">{len(filtered):,}</div>
                    <div class="label">Schools</div>
                </div>
            """, unsafe_allow_html=True)
        with c2:
            total_enrollment = filtered["all_students"].sum()
            st.markdown(f"""
                <div class="stat-card">
                    <div class="value">{int(total_enrollment):,}</div>
                    <div class="label">Total Students</div>
                </div>
            """, unsafe_allow_html=True)
        with c3:
            num_districts = filtered["districtname"].nunique()
            st.markdown(f"""
                <div class="stat-card">
                    <div class="value">{num_districts}</div>
                    <div class="label">Districts</div>
                </div>
            """, unsafe_allow_html=True)
        with c4:
            num_counties = filtered["county"].nunique()
            st.markdown(f"""
                <div class="stat-card">
                    <div class="value">{num_counties}</div>
                    <div class="label">Counties</div>
                </div>
            """, unsafe_allow_html=True)

        st.markdown("---")

        # Schools by county chart
        col_left, col_right = st.columns(2)

        with col_left:
            st.markdown("### Schools by County")
            county_counts = filtered.groupby("county").agg({
                "schoolname": "count",
                "all_students": "sum"
            }).reset_index()
            county_counts.columns = ["County", "Schools", "Enrollment"]
            county_counts = county_counts.sort_values("Schools", ascending=False).head(15)

            fig = px.bar(
                county_counts,
                x="County",
                y="Schools",
                color="Enrollment",
                color_continuous_scale=["#90EE90", FOREST_GREEN]
            )
            fig.update_layout(xaxis_tickangle=-45, height=400)
            st.plotly_chart(fig, use_container_width=True)

        with col_right:
            st.markdown("### Enrollment by District (Top 15)")
            district_counts = filtered.groupby("districtname").agg({
                "all_students": "sum"
            }).reset_index()
            district_counts.columns = ["District", "Students"]
            district_counts = district_counts.sort_values("Students", ascending=True).tail(15)

            fig = px.bar(
                district_counts,
                x="Students",
                y="District",
                orientation='h',
                color="Students",
                color_continuous_scale=["#90EE90", FOREST_GREEN]
            )
            fig.update_layout(height=400, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")

        # Demographics summary
        if 'pct_low_income' in filtered.columns:
            st.markdown("### Demographics Overview")
            demo_cols = st.columns(3)

            with demo_cols[0]:
                avg_low_income = filtered['pct_low_income'].mean()
                st.markdown(f"""
                    <div class="stat-card">
                        <div class="value">{avg_low_income:.1f}%</div>
                        <div class="label">Avg. Low Income</div>
                    </div>
                """, unsafe_allow_html=True)

            with demo_cols[1]:
                if 'pct_ell' in filtered.columns:
                    avg_ell = filtered['pct_ell'].mean()
                    st.markdown(f"""
                        <div class="stat-card">
                            <div class="value">{avg_ell:.1f}%</div>
                            <div class="label">Avg. English Learners</div>
                        </div>
                    """, unsafe_allow_html=True)

            with demo_cols[2]:
                if 'pct_swd' in filtered.columns:
                    avg_swd = filtered['pct_swd'].mean()
                    st.markdown(f"""
                        <div class="stat-card">
                            <div class="value">{avg_swd:.1f}%</div>
                            <div class="label">Avg. Students w/ Disabilities</div>
                        </div>
                    """, unsafe_allow_html=True)

            st.markdown("---")

        # School table
        st.markdown("### Schools")
        display_cols = ["schoolname", "districtname", "county", "currentschooltype", "all_students"]
        if 'pct_low_income' in filtered.columns:
            display_cols.append('pct_low_income')

        display_df = filtered[display_cols].copy()
        display_df.columns = ["School", "District", "County", "Type", "Enrollment"] + \
                            (["% Low Income"] if 'pct_low_income' in filtered.columns else [])

        st.dataframe(
            display_df.sort_values("Enrollment", ascending=False),
            use_container_width=True,
            hide_index=True
        )

        # Download
        csv = filtered.to_csv(index=False)
        st.download_button("Download CSV", csv, "vera_wa_schools.csv", "text/csv")


# =============================================================================
# Page: Assessment Analysis
# =============================================================================

elif page == "📈 Assessment Analysis":
    st.title("SBAC Assessment Analysis")
    st.caption("Live data from data.wa.gov • OSPI Report Card Assessment 2023-24")

    st.markdown("""
    Washington uses **Smarter Balanced (SBAC)** assessments for ELA and Math in grades 3-8 and 10.
    VERA-WA analyzes achievement patterns to identify schools needing support before they reach crisis.
    """)

    # Fetch assessment data
    assessment_raw = fetch_assessment_data(limit=5000)

    if assessment_raw:
        assessment_df = pd.DataFrame(assessment_raw)

        st.markdown("### Assessment Data Overview")

        # Key metrics
        metrics_cols = st.columns(4)

        with metrics_cols[0]:
            num_schools = assessment_df['schoolname'].nunique()
            st.markdown(f"""
                <div class="stat-card">
                    <div class="value">{num_schools:,}</div>
                    <div class="label">Schools with Results</div>
                </div>
            """, unsafe_allow_html=True)

        with metrics_cols[1]:
            num_records = len(assessment_df)
            st.markdown(f"""
                <div class="stat-card">
                    <div class="value">{num_records:,}</div>
                    <div class="label">Assessment Records</div>
                </div>
            """, unsafe_allow_html=True)

        with metrics_cols[2]:
            subjects = assessment_df['testsubject'].nunique()
            st.markdown(f"""
                <div class="stat-card">
                    <div class="value">{subjects}</div>
                    <div class="label">Subjects Tested</div>
                </div>
            """, unsafe_allow_html=True)

        with metrics_cols[3]:
            grades = assessment_df['gradelevel'].nunique()
            st.markdown(f"""
                <div class="stat-card">
                    <div class="value">{grades}</div>
                    <div class="label">Grade Levels</div>
                </div>
            """, unsafe_allow_html=True)

        st.markdown("---")

        # Filter controls
        col1, col2, col3 = st.columns(3)

        with col1:
            subjects_list = ["All"] + sorted(assessment_df['testsubject'].dropna().unique().tolist())
            selected_subject = st.selectbox("Subject", subjects_list)

        with col2:
            grades_list = ["All"] + sorted(assessment_df['gradelevel'].dropna().unique().tolist())
            selected_grade = st.selectbox("Grade Level", grades_list)

        with col3:
            counties_list = ["All"] + sorted(assessment_df['county'].dropna().unique().tolist())
            selected_county = st.selectbox("County", counties_list, key="assessment_county")

        # Filter data
        filtered_assess = assessment_df.copy()
        if selected_subject != "All":
            filtered_assess = filtered_assess[filtered_assess['testsubject'] == selected_subject]
        if selected_grade != "All":
            filtered_assess = filtered_assess[filtered_assess['gradelevel'] == selected_grade]
        if selected_county != "All":
            filtered_assess = filtered_assess[filtered_assess['county'] == selected_county]

        st.markdown("---")

        # Proficiency analysis
        st.markdown("### Proficiency Rates by Subject")

        if 'percent_met_tested_only' in filtered_assess.columns:
            filtered_assess['proficiency'] = filtered_assess['percent_met_tested_only'].apply(
                lambda x: safe_float(x) * 100 if safe_float(x) <= 1 else safe_float(x)
            )

            subject_prof = filtered_assess.groupby('testsubject')['proficiency'].mean().reset_index()
            subject_prof.columns = ['Subject', 'Proficiency Rate']
            subject_prof['Proficiency Rate'] = subject_prof['Proficiency Rate'].round(1)

            fig = px.bar(
                subject_prof,
                x='Subject',
                y='Proficiency Rate',
                color='Proficiency Rate',
                color_continuous_scale=["#CC142B", "#C5A900", FOREST_GREEN],
                range_color=[30, 70]
            )
            fig.update_layout(height=350)
            fig.add_hline(y=50, line_dash="dash", line_color="gray",
                         annotation_text="50% Threshold", annotation_position="right")
            st.plotly_chart(fig, use_container_width=True)

        # Sample records
        st.markdown("### Assessment Records")
        display_cols = ['schoolname', 'districtname', 'county', 'gradelevel',
                       'testsubject', 'percent_consistent_grade_level_knowledge_and_above']
        available_cols = [c for c in display_cols if c in filtered_assess.columns]

        st.dataframe(
            filtered_assess[available_cols].head(100),
            use_container_width=True,
            hide_index=True
        )

    else:
        st.info("Loading assessment data from OSPI...")

        st.markdown("""
        ### What VERA-WA Will Analyze

        - **ELA Performance** by grade, school, and demographic group
        - **Math Performance** patterns and growth trajectories
        - **Achievement Gaps** between student subgroups
        - **Schools At Risk** based on declining performance trends
        - **Intervention Effectiveness** tracking over time
        """)


# =============================================================================
# Page: Phase II Infrastructure
# =============================================================================

elif page == "🎓 Phase II Infrastructure":
    st.title("Phase II Infrastructure")

    st.markdown(f"""
    Washington's State Board of Education completed **Phase I** of accountability redesign with
    the Learning Policy Institute. Phase II needs technical infrastructure to measure inputs,
    outputs, and outcomes at the individual student level.

    **VERA-WA is that infrastructure.**
    """)

    st.markdown("---")

    # Three pillars
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(f"""
        <div style="background: white; padding: 30px; border-radius: 8px; border-top: 4px solid {FOREST_GREEN}; height: 100%;">
            <h3 style="color: {FOREST_GREEN}; font-size: 1.2rem; margin-bottom: 16px;">📥 Inputs</h3>
            <p style="color: #555; font-size: 0.95rem; line-height: 1.7;">
                <strong>Conditions for Learning</strong><br><br>
                • Teacher qualifications<br>
                • Resource allocation<br>
                • School climate data<br>
                • Facility conditions<br>
                • Support services access
            </p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div style="background: white; padding: 30px; border-radius: 8px; border-top: 4px solid {GOLD}; height: 100%;">
            <h3 style="color: {FOREST_GREEN}; font-size: 1.2rem; margin-bottom: 16px;">📤 Outputs</h3>
            <p style="color: #555; font-size: 0.95rem; line-height: 1.7;">
                <strong>Academic Performance</strong><br><br>
                • SBAC ELA scores<br>
                • SBAC Math scores<br>
                • WCAS Science scores<br>
                • Graduation rates<br>
                • Course completion
            </p>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div style="background: white; padding: 30px; border-radius: 8px; border-top: 4px solid #CC142B; height: 100%;">
            <h3 style="color: {FOREST_GREEN}; font-size: 1.2rem; margin-bottom: 16px;">🎯 Outcomes</h3>
            <p style="color: #555; font-size: 0.95rem; line-height: 1.7;">
                <strong>State Goals Alignment</strong><br><br>
                • College enrollment<br>
                • Career readiness<br>
                • Opportunity gap closure<br>
                • Equity indicators<br>
                • Long-term success
            </p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    st.markdown("### VERA's Role in Phase II")

    st.markdown("""
    | Phase I (Complete) | Phase II (VERA) |
    |-------------------|-----------------|
    | Framework design | Technical implementation |
    | Stakeholder engagement | Data system integration |
    | Conceptual model | Student-level verification |
    | Policy recommendations | Real-time analytics |
    """)

    st.markdown("---")

    st.markdown("### Data Systems Connected")

    data_cols = st.columns(4)
    systems = [
        ("CEDARS", "Student-level data reporting"),
        ("EDS", "Education Data System"),
        ("SBAC/WCAS", "Assessment results"),
        ("EOGOAC", "Equity gap analytics")
    ]

    for col, (name, desc) in zip(data_cols, systems):
        with col:
            st.markdown(f"""
            <div style="background: {FOREST_GREEN}; color: white; padding: 20px; border-radius: 8px; text-align: center;">
                <strong style="font-size: 1.1rem;">{name}</strong><br>
                <span style="font-size: 0.85rem; opacity: 0.8;">{desc}</span>
            </div>
            """, unsafe_allow_html=True)


# =============================================================================
# Page: About
# =============================================================================

elif page == "ℹ️ About VERA-WA":
    st.title("About VERA-WA")

    st.markdown(f"""
    ## Verification Engine for Results & Accountability

    **VERA-WA** provides the technical infrastructure for Washington's Phase II
    accountability redesign. It connects the inputs/outputs/outcomes framework
    to student-level data verification.

    ---

    ## The Phase I Foundation

    Washington's State Board of Education, working with OSPI, EOGOAC, and the
    Learning Policy Institute, completed Phase I of accountability redesign:

    - Defined inputs/outputs/outcomes framing
    - Established "conditions for learning" as accountability dimension
    - Created continuous improvement model
    - Engaged equity-focused stakeholders

    ---

    ## What Phase II Needs

    The gap Phase I identified: **what technical infrastructure actually measures
    those inputs and outcomes at the individual student level?**

    VERA-WA answers that question by:

    - Connecting to CEDARS student-level data
    - Integrating SBAC/WCAS assessment results
    - Tracking resource allocation to student outcomes
    - Verifying intervention effectiveness
    - Supporting EOGOAC equity analytics

    ---

    ## Data Sources

    All data from **[data.wa.gov](https://data.wa.gov)**, Washington's open data portal:

    - **Enrollment Data:** [Report Card Enrollment 2024-25](https://data.wa.gov/education/Report-Card-Enrollment-2024-25-School-Year/2rwv-gs2e) - Demographics, program participation
    - **Assessment Data:** [Report Card Assessment 2023-24](https://data.wa.gov/education/Report-Card-Assessment-Data-2023-24-School-Year/x73g-mrqp) - SBAC ELA/Math results
    - **WSIF Data:** [Washington School Improvement Framework 2025](https://data.wa.gov/education/Washington-School-Improvement-Framework-WSIF-2025-/u25x-vdun) - Accountability indicators

    ---

    ## Key Partners

    | Organization | Role |
    |--------------|------|
    | **SBE** | State Board of Education - accountability oversight |
    | **OSPI** | Office of Superintendent - data systems |
    | **EOGOAC** | Educational Opportunity Gap Oversight Committee |
    | **LPI** | Learning Policy Institute - research partnership |

    ---

    <p style="color: #666; font-size: 0.9rem;">
        VERA-WA v0.1 | Built by <a href="https://hallucinations.cloud" style="color: {FOREST_GREEN};">Hallucinations.cloud</a> |
        An <a href="https://h-edu.solutions" style="color: {FOREST_GREEN};">H-EDU.Solutions</a> Initiative
    </p>
    """, unsafe_allow_html=True)
