from __future__ import annotations

import base64
import html as html_lib
import os
import tempfile
from io import BytesIO
from pathlib import Path

import streamlit as st
from PIL import Image, ImageChops, ImageOps

from src.application.conversation_service import ConversationService
from src.application.image_medicine_service import ImageMedicineService
from src.application.medicine_service import MedicineService
from src.conversation.contextualizer import ConversationContextualizer
from src.rag.service import PharmoraRAG
from src.vision.medicine_identifier import MedicineImageIdentifier
from src.vision.ocr import MedicineOCR


BASE_DIR = Path(__file__).resolve().parent
LOGO_PATH = BASE_DIR / "assets" / "pharmora_logo.png"


st.set_page_config(
    page_title="Pharmora",
    page_icon=str(LOGO_PATH) if LOGO_PATH.exists() else None,
    layout="wide",
    initial_sidebar_state="expanded",
)


def render_html(
    content: str,
) -> None:
    st.html(
        content
    )


@st.cache_data(
    show_spinner=False
)
def get_logo_data_uri() -> str | None:
    if not LOGO_PATH.exists():
        return None

    image = Image.open(
        LOGO_PATH
    ).convert(
        "RGB"
    )

    background = Image.new(
        "RGB",
        image.size,
        "white",
    )

    difference = ImageChops.difference(
        image,
        background,
    ).convert(
        "L"
    )

    difference = difference.point(
        lambda pixel: (
            255
            if pixel > 15
            else 0
        )
    )

    bbox = difference.getbbox()

    if bbox is not None:
        image = image.crop(
            bbox
        )

    image = ImageOps.expand(
        image,
        border=8,
        fill="white",
    )

    buffer = BytesIO()

    image.save(
        buffer,
        format="PNG",
        optimize=True,
    )

    encoded = base64.b64encode(
        buffer.getvalue()
    ).decode(
        "utf-8"
    )

    return (
        "data:image/png;base64,"
        + encoded
    )


def load_css() -> None:
    st.html(
        """
        <style>
        @import url(
            'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Manrope:wght@600;700&display=swap'
        );

        :root {
            --ph-primary: #19B35A;
            --ph-primary-dark: #0D7A3A;
            --ph-primary-soft: #EAF8EF;
            --ph-background: #F7FAF8;
            --ph-white: #FFFFFF;
            --ph-text: #17231C;
            --ph-secondary: #6C7A71;
            --ph-border: #E2EAE5;
        }

        html,
        body {
            font-family: "Inter", sans-serif;
        }

        .stApp {
            background: var(--ph-background);
            color: var(--ph-text);
        }

        header[data-testid="stHeader"] {
            background: rgba(247, 250, 248, 0.94);
        }

        #MainMenu {
            visibility: hidden;
        }

        footer {
            visibility: hidden;
        }

        [data-testid="stSidebar"] {
            background: var(--ph-white);
            border-right: 1px solid var(--ph-border);
        }

        [data-testid="stSidebar"] > div:first-child {
            padding-top: 1rem;
        }

        .block-container {
            max-width: 1080px;
            width: 100%;
            padding-top: 3.5rem;
            padding-bottom: 5rem;
            box-sizing: border-box;
        }

        .ph-brand-wrapper {
            width: 100%;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            margin: 2px auto 34px auto;
        }

        .ph-brand-logo {
            display: block;
            width: 112px;
            height: auto;
            object-fit: contain;
            margin: 0 auto;
        }

        .ph-brand-subtitle {
            max-width: 175px;
            margin-top: 7px;
            text-align: center;
            color: var(--ph-secondary);
            font-size: 0.71rem;
            line-height: 1.45;
        }

        .ph-brand-fallback {
            font-family: "Manrope", sans-serif;
            font-size: 1.25rem;
            font-weight: 700;
            color: var(--ph-text);
        }

        .ph-eyebrow {
            color: var(--ph-primary-dark);
            font-size: 0.72rem;
            font-weight: 700;
            letter-spacing: 0.075em;
            text-transform: uppercase;
        }

        .ph-hero {
            max-width: 780px;
            margin-bottom: 46px;
        }

        .ph-hero h1 {
            margin: 13px 0 15px 0;
            padding: 0;
            font-family: "Manrope", sans-serif;
            font-size: clamp(2.25rem, 4vw, 3.4rem);
            line-height: 1.11;
            letter-spacing: -0.045em;
            font-weight: 700;
            color: var(--ph-text);
        }

        .ph-hero p {
            margin: 0;
            color: var(--ph-secondary);
            font-size: 1rem;
            line-height: 1.7;
            max-width: 680px;
        }

        .ph-section-title {
            color: var(--ph-primary-dark);
            font-size: 0.72rem;
            font-weight: 700;
            letter-spacing: 0.07em;
            text-transform: uppercase;
            margin-bottom: 13px;
        }

        .ph-card {
            background: var(--ph-white);
            border: 1px solid var(--ph-border);
            border-radius: 17px;
            padding: 17px;
            margin-top: 16px;
            box-shadow: 0 6px 22px rgba(22, 58, 37, 0.035);
        }

        .ph-card-label {
            color: var(--ph-secondary);
            font-size: 0.69rem;
            font-weight: 700;
            letter-spacing: 0.07em;
            text-transform: uppercase;
            margin-bottom: 11px;
        }

        .ph-medicine-name {
            color: var(--ph-text);
            font-family: "Manrope", sans-serif;
            font-size: 0.98rem;
            font-weight: 700;
            line-height: 1.45;
            margin-bottom: 10px;
        }

        .ph-medicine-meta {
            color: var(--ph-secondary);
            font-size: 0.82rem;
            line-height: 1.75;
        }

        .ph-cis {
            display: inline-block;
            margin-top: 12px;
            padding: 5px 9px;
            color: var(--ph-primary-dark);
            background: var(--ph-primary-soft);
            border-radius: 8px;
            font-size: 0.7rem;
            font-weight: 700;
        }

        .ph-empty-chat {
            background: var(--ph-white);
            border: 1px solid var(--ph-border);
            border-radius: 20px;
            padding: 3rem 2rem;
            text-align: center;
            box-shadow: 0 10px 30px rgba(23, 52, 34, 0.025);
        }

        .ph-empty-chat h3 {
            margin: 0 0 10px 0;
            color: var(--ph-text);
            font-family: "Manrope", sans-serif;
            font-size: 1.15rem;
            font-weight: 700;
        }

        .ph-empty-chat p {
            max-width: 510px;
            margin: auto;
            color: var(--ph-secondary);
            font-size: 0.88rem;
            line-height: 1.65;
        }

        .ph-source {
            background: #FBFDFB;
            border: 1px solid var(--ph-border);
            border-radius: 12px;
            padding: 11px 13px;
            margin-bottom: 8px;
            color: var(--ph-secondary);
            font-size: 0.8rem;
            line-height: 1.5;
        }

        .ph-source strong {
            color: var(--ph-text);
        }

        .ph-disclaimer {
            color: #7B887F;
            font-size: 0.71rem;
            line-height: 1.6;
            margin-top: 32px;
        }

        div[data-testid="stButton"] button {
            border-radius: 12px;
            min-height: 43px;
            font-weight: 600;
            border: 1px solid var(--ph-border);
        }

        div[data-testid="stButton"] button:hover {
            color: var(--ph-primary-dark);
            border-color: var(--ph-primary);
        }

        div[data-testid="stButton"] button[kind="primary"] {
            color: white !important;
            background: var(--ph-primary) !important;
            border-color: var(--ph-primary) !important;
        }

        div[data-testid="stTextInput"] input {
            min-height: 44px;
            color: var(--ph-text);
            background: white;
            border: 1px solid var(--ph-border);
            border-radius: 12px;
        }

        div[data-testid="stTextInput"] input:focus {
            border-color: var(--ph-primary);
            box-shadow: 0 0 0 1px var(--ph-primary);
        }

        .stTabs [data-baseweb="tab-list"] {
            gap: 3px;
            border-bottom: 1px solid var(--ph-border);
        }

        .stTabs [data-baseweb="tab"] {
            color: var(--ph-secondary);
            font-size: 0.78rem;
            font-weight: 500;
            padding-left: 0;
            padding-right: 18px;
        }

        .stTabs [aria-selected="true"] {
            color: var(--ph-primary-dark) !important;
        }

        .stTabs [data-baseweb="tab-highlight"] {
            background-color: var(--ph-primary) !important;
        }

        [data-testid="stFileUploaderDropzone"] {
            background: #FAFDFA;
            border: 1px dashed #AAD9BC;
            border-radius: 14px;
        }

        .ph-user-row {
            width: 100%;
            display: flex;
            justify-content: flex-end;
            box-sizing: border-box;
            margin: 16px 0 20px 0;
            padding: 0;
        }

        .ph-user-group {
            width: fit-content;
            max-width: 72%;
            display: flex;
            flex-direction: column;
            align-items: flex-end;
            box-sizing: border-box;
        }

        .ph-user-label {
            color: var(--ph-secondary);
            font-size: 0.72rem;
            font-weight: 700;
            margin: 0 4px 6px 0;
        }

        .ph-user-bubble {
            width: fit-content;
            max-width: 100%;
            background: var(--ph-primary);
            color: var(--ph-white);
            padding: 13px 16px;
            border-radius: 18px 18px 5px 18px;
            box-shadow: 0 6px 18px rgba(25, 179, 90, 0.10);
            font-size: 0.92rem;
            line-height: 1.6;
            white-space: normal;
            overflow-wrap: anywhere;
            word-break: normal;
            box-sizing: border-box;
        }

        [class*="st-key-ph-assistant-message-"] {
            width: 100%;
            max-width: 86%;
            margin: 16px auto 24px 0;
            box-sizing: border-box;
        }

        [class*="st-key-ph-assistant-message-"] .ph-assistant-label {
            color: var(--ph-primary-dark);
            font-size: 0.72rem;
            font-weight: 700;
            margin: 0 0 6px 4px;
        }

        [class*="st-key-ph-assistant-message-"]
        [data-testid="stMarkdownContainer"] {
            width: 100%;
            max-width: 100%;
            background: var(--ph-white);
            color: var(--ph-text);
            border: 1px solid var(--ph-border);
            padding: 15px 17px;
            border-radius: 5px 18px 18px 18px;
            box-shadow: 0 7px 22px rgba(21, 56, 35, 0.035);
            font-size: 0.92rem;
            line-height: 1.65;
            overflow-wrap: anywhere;
            box-sizing: border-box;
        }

        [class*="st-key-ph-assistant-message-"]
        [data-testid="stMarkdownContainer"] p:first-child {
            margin-top: 0;
        }

        [class*="st-key-ph-assistant-message-"]
        [data-testid="stMarkdownContainer"] p:last-child {
            margin-bottom: 0;
        }

        [data-testid="stBottomBlockContainer"] {
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
            padding-top: 0 !important;
        }

        [data-testid="stChatInput"] {
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
            padding: 0 !important;
        }

        [data-testid="stChatInput"] > div {
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
        }

        [data-testid="stChatInput"] [data-baseweb="textarea"] {
            background: var(--ph-white) !important;
            border: 1px solid var(--ph-border) !important;
            border-radius: 17px !important;
            box-shadow:
                0 8px 24px rgba(21, 56, 35, 0.055) !important;
            min-height: 54px !important;
            max-width: 100% !important;
            box-sizing: border-box !important;
        }

        [data-testid="stChatInput"] textarea {
            background: transparent !important;
            color: var(--ph-text) !important;
            min-height: 52px !important;
            padding: 14px 52px 14px 17px !important;
            font-size: 0.92rem !important;
            line-height: 1.45 !important;
            max-width: 100% !important;
            box-sizing: border-box !important;
        }

        [data-testid="stChatInput"] textarea::placeholder {
            color: #98A29C !important;
        }

        [data-testid="stChatInput"]
        [data-baseweb="textarea"]:focus-within {
            border-color: var(--ph-primary) !important;
            box-shadow:
                0 0 0 2px rgba(25, 179, 90, 0.10),
                0 8px 24px rgba(21, 56, 35, 0.055) !important;
        }

        [data-testid="stChatInput"] button {
            background: var(--ph-primary) !important;
            color: var(--ph-white) !important;
            border: none !important;
            border-radius: 11px !important;
            width: 38px !important;
            height: 38px !important;
            margin-right: 7px !important;
        }

        [data-testid="stChatInput"] button:hover {
            background: var(--ph-primary-dark) !important;
        }

        @media (max-width: 1100px) {
            .block-container {
                padding-left: 1.4rem;
                padding-right: 1.4rem;
            }

            .ph-user-group {
                max-width: 78%;
            }

            [class*="st-key-ph-assistant-message-"] {
                max-width: 92%;
            }
        }

        @media (max-width: 900px) {
            .ph-user-group {
                max-width: 82%;
            }

            [class*="st-key-ph-assistant-message-"] {
                max-width: 94%;
            }
        }

        @media (max-width: 768px) {
            .block-container {
                padding-top: 2rem;
                padding-left: 1rem;
                padding-right: 1rem;
            }

            .ph-hero h1 {
                font-size: 2.15rem;
            }

            .ph-user-group {
                max-width: 88%;
            }

            [class*="st-key-ph-assistant-message-"] {
                max-width: 100%;
            }
        }

        @media (max-width: 600px) {
            .ph-user-group {
                max-width: 92%;
            }
        }
        </style>
        """
    )


def configure_secrets() -> None:
    try:
        if "GROQ_API_KEY" in st.secrets:
            os.environ["GROQ_API_KEY"] = str(
                st.secrets["GROQ_API_KEY"]
            )

        if "GROQ_MODEL" in st.secrets:
            os.environ["GROQ_MODEL"] = str(
                st.secrets["GROQ_MODEL"]
            )

    except FileNotFoundError:
        pass


@st.cache_resource(
    show_spinner=False
)
def get_rag() -> PharmoraRAG:
    return PharmoraRAG()


@st.cache_resource(
    show_spinner=False
)
def get_contextualizer() -> ConversationContextualizer:
    return ConversationContextualizer()


@st.cache_resource(
    show_spinner=False
)
def get_ocr() -> MedicineOCR:
    return MedicineOCR()


def initialize_state() -> None:
    if "medicine_service" in st.session_state:
        return

    medicine_service = MedicineService()

    identifier = MedicineImageIdentifier(
        ocr=get_ocr(),
        catalog=medicine_service.catalog,
    )

    image_service = ImageMedicineService(
        identifier=identifier,
        medicine_service=medicine_service,
    )

    st.session_state.medicine_service = medicine_service
    st.session_state.image_service = image_service
    st.session_state.conversation_service = None
    st.session_state.search_results = []
    st.session_state.last_result = None


def activate_conversation() -> None:
    medicine_service = (
        st.session_state.medicine_service
    )

    session = medicine_service.session

    if session is None:
        st.session_state.conversation_service = None
        return

    current = (
        st.session_state.conversation_service
    )

    if (
        current is None
        or current.session is not session
    ):
        st.session_state.conversation_service = (
            ConversationService(
                session=session,
                rag=get_rag(),
                contextualizer=get_contextualizer(),
            )
        )


def render_brand() -> None:
    logo_uri = get_logo_data_uri()

    if logo_uri is None:
        render_html(
            """
            <div class="ph-brand-wrapper">
                <div class="ph-brand-fallback">
                    Pharmora
                </div>

                <div class="ph-brand-subtitle">
                    Pharmaceutical information assistant
                </div>
            </div>
            """
        )

        return

    render_html(
        f"""
        <div class="ph-brand-wrapper">
            <img
                src="{logo_uri}"
                class="ph-brand-logo"
                alt="Pharmora"
            >

            <div class="ph-brand-subtitle">
                Pharmaceutical information assistant
            </div>
        </div>
        """
    )


def get_profile() -> dict | None:
    return (
        st.session_state
        .medicine_service
        .get_display_profile()
    )


def render_medicine_card() -> None:
    profile = get_profile()

    if profile is None:
        render_html(
            """
            <div class="ph-card">
                <div class="ph-card-label">
                    Current medicine
                </div>

                <div class="ph-medicine-meta">
                    No medicine selected yet.
                </div>
            </div>
            """
        )

        return

    name = html_lib.escape(
        str(
            profile["name"]
        )
    )

    strength = html_lib.escape(
        str(
            profile.get(
                "strength"
            )
            or "Not specified"
        )
    )

    pharmaceutical_form = (
        html_lib.escape(
            str(
                profile.get(
                    "pharmaceutical_form"
                )
                or "Not specified"
            )
        )
    )

    routes = ", ".join(
        profile.get(
            "administration_routes",
            [],
        )
    )

    substances = ", ".join(
        profile.get(
            "active_substances",
            [],
        )
    )

    cis = html_lib.escape(
        str(
            profile["cis"]
        )
    )

    extra = ""

    if substances:
        extra = (
            "<br>"
            + html_lib.escape(
                substances
            )
        )

    render_html(
        f"""
        <div class="ph-card">
            <div class="ph-card-label">
                Current medicine
            </div>

            <div class="ph-medicine-name">
                {name}
            </div>

            <div class="ph-medicine-meta">
                {strength}<br>
                {pharmaceutical_form}<br>
                {html_lib.escape(routes or "Route not specified")}
                {extra}
            </div>

            <div class="ph-cis">
                CIS {cis}
            </div>
        </div>
        """
    )


def select_by_cis(
    cis: str,
) -> None:
    result = (
        st.session_state
        .medicine_service
        .select_by_cis(
            cis
        )
    )

    if result["status"] == "selected":
        activate_conversation()
        st.session_state.last_result = None


def render_search() -> None:
    query = st.text_input(
        "Medicine name",
        placeholder="Doliprane 500 mg comprimé",
        label_visibility="collapsed",
        key="medicine_search",
    )

    if st.button(
        "Search",
        type="primary",
        use_container_width=True,
        key="search_button",
    ):
        if query.strip():
            st.session_state.search_results = (
                st.session_state
                .medicine_service
                .search(
                    query.strip(),
                    limit=10,
                )
            )

    results = (
        st.session_state.search_results
    )

    if not results:
        return

    labels = {
        medicine["name"]: medicine["cis"]
        for medicine in results
    }

    selected = st.selectbox(
        "Search results",
        options=list(
            labels.keys()
        ),
        label_visibility="collapsed",
    )

    if st.button(
        "Use this medicine",
        use_container_width=True,
        key="select_result",
    ):
        select_by_cis(
            labels[selected]
        )

        st.session_state.search_results = []

        st.rerun()


def identify_image(
    uploaded_file,
) -> dict:
    suffix = Path(
        uploaded_file.name
    ).suffix.lower()

    if suffix not in {
        ".jpg",
        ".jpeg",
        ".png",
    }:
        suffix = ".jpg"

    temporary_path = None

    try:
        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=suffix,
        ) as temp:
            temp.write(
                uploaded_file.getbuffer()
            )

            temporary_path = (
                temp.name
            )

        result = (
            st.session_state
            .image_service
            .identify_and_select(
                temporary_path
            )
        )

        if result["status"] == "resolved":
            activate_conversation()
            st.session_state.last_result = None

        return result

    finally:
        if (
            temporary_path
            and os.path.exists(
                temporary_path
            )
        ):
            os.remove(
                temporary_path
            )


def render_scan() -> None:
    uploaded_file = st.file_uploader(
        "Medicine box image",
        type=[
            "jpg",
            "jpeg",
            "png",
        ],
        label_visibility="collapsed",
        key="medicine_scan",
    )

    if uploaded_file is None:
        return

    if st.button(
        "Identify medicine",
        type="primary",
        use_container_width=True,
        key="identify_button",
    ):
        with st.spinner(
            "Reading medicine box..."
        ):
            result = identify_image(
                uploaded_file
            )

        if result["status"] == "resolved":
            st.success(
                "Medicine identified successfully."
            )

            st.rerun()

        elif result["status"] == "ambiguous":
            st.warning(
                "The image does not contain enough information "
                "to identify one unique medicine. Try another "
                "photo showing the name, dosage and form."
            )

        else:
            st.error(
                "This medicine could not be identified "
                "in the Pharmora catalogue."
            )


def render_identification_panel() -> None:
    render_html(
        """
        <div class="ph-section-title">
            Identify your medicine
        </div>
        """
    )

    search_tab, scan_tab = st.tabs(
        [
            "Search by name",
            "Scan medicine box",
        ]
    )

    with search_tab:
        render_search()

    with scan_tab:
        render_scan()

    render_medicine_card()


def render_sources(
    result: dict,
) -> None:
    sources = result.get(
        "sources",
        [],
    )

    if not sources:
        return

    with st.expander(
        "Sources"
    ):
        for source in sources:
            reference = html_lib.escape(
                str(
                    source.get(
                        "reference",
                        "",
                    )
                )
            )

            document_type = html_lib.escape(
                str(
                    source.get(
                        "document_type",
                        "",
                    )
                )
            )

            section_number = html_lib.escape(
                str(
                    source.get(
                        "section_number",
                        "",
                    )
                )
            )

            section_title = html_lib.escape(
                str(
                    source.get(
                        "section_title",
                        "",
                    )
                )
            )

            source_url = source.get(
                "source_url",
                "",
            )

            render_html(
                f"""
                <div class="ph-source">
                    <strong>
                        {reference}
                    </strong><br>
                    {document_type}
                    · {section_number}
                    · {section_title}
                </div>
                """
            )

            if source_url:
                st.link_button(
                    "Open official source",
                    source_url,
                )


def render_chat() -> None:
    profile = get_profile()

    if profile is None:
        render_html(
            """
            <div class="ph-empty-chat">
                <h3>
                    Start with your medicine
                </h3>

                <p>
                    Search for your medicine by name or scan
                    the box. Once identified, Pharmora can
                    answer questions using official
                    pharmaceutical documents.
                </p>
            </div>
            """
        )

        return

    activate_conversation()

    session = (
        st.session_state
        .medicine_service
        .session
    )

    if session is None:
        return

    history = (
        session.full_history()
    )

    for index, message in enumerate(
        history
    ):
        role = message[
            "role"
        ]

        content = message[
            "content"
        ]

        if role == "user":
            safe_content = (
                html_lib.escape(
                    str(content)
                )
                .replace(
                    "\n",
                    "<br>"
                )
            )

            render_html(
                f"""
                <div class="ph-user-row">
                    <div class="ph-user-group">
                        <div class="ph-user-label">
                            You
                        </div>

                        <div class="ph-user-bubble">
                            {safe_content}
                        </div>
                    </div>
                </div>
                """
            )

        else:
            with st.container(
                key=(
                    f"ph-assistant-message-"
                    f"{index}"
                )
            ):
                render_html(
                    """
                    <div class="ph-assistant-label">
                        Pharmora
                    </div>
                    """
                )

                st.markdown(
                    content
                )

    last_result = (
        st.session_state
        .last_result
    )

    if last_result is not None:
        render_sources(
            last_result
        )

    question = st.chat_input(
        "Ask a question about this medicine"
    )

    if not question:
        return

    with st.spinner(
        "Searching official pharmaceutical sources..."
    ):
        result = (
            st.session_state
            .conversation_service
            .ask(
                question
            )
        )

    st.session_state.last_result = (
        result
    )

    st.rerun()


configure_secrets()
load_css()
initialize_state()


with st.sidebar:
    render_brand()

    render_identification_panel()

    render_html(
        """
        <div class="ph-disclaimer">
            Pharmora provides documentary pharmaceutical
            information and does not replace medical advice,
            diagnosis or treatment decisions.
        </div>
        """
    )


render_html(
    """
    <section class="ph-hero">
        <div class="ph-eyebrow">
            Pharmora
        </div>

        <h1>
            Comprenez votre médicament en toute confiance.
        </h1>

        <p>
            Posez vos questions, scannez la boîte et obtenez
            des réponses claires basées sur des sources
            pharmaceutiques officielles.
        </p>
    </section>
    """
)


render_chat()