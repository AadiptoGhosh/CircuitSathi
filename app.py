"""
CircuitSathi — Local-First Open-Weight AI Assistant for Electronics Engineering
Streamlit Main Application Interface.
"""

from pathlib import Path
import io
import base64
import streamlit as st
import pandas as pd

# Core modules
from config import settings, UPLOADS_DIR, SAMPLE_DOCS_DIR
from src.llm import llm_client
from src.pdf_ingest import process_pdf, validate_pdf_file
from src.ocr import is_ocr_available
from src.retrieval import vector_store, format_context_for_prompt
from src.prompts import (
    CIRCUITSATHI_SYSTEM_PROMPT,
    CIRCUITSATHI_RAG_PROMPT,
    CIRCUITSATHI_IMAGE_PROMPT,
)
from src.component_library import component_library, ComponentSpec
from src.bom import BOMItem, BOMProject
from src.troubleshooting import (
    TroubleshootingRequest,
    conduct_troubleshooting,
)
from src.safety import (
    calculate_led_resistor,
    calculate_voltage_divider,
    check_circuit_safety,
)
from src.storage import (
    save_uploaded_file,
    delete_uploaded_document,
    purge_all_data,
)

# Set page configuration
st.set_page_config(
    page_title="CircuitSathi — AI Electronics Engineering Companion",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load custom CSS
css_path = Path(__file__).parent / "assets" / "style.css"
if css_path.exists():
    with open(css_path, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


# --- Session State Initialization ---
if "messages" not in st.session_state:
    st.session_state.messages = []

if "bom_project" not in st.session_state:
    st.session_state.bom_project = BOMProject(
        project_name="Autonomous Line Follower",
        project_objective="Dual-motor differential drive with optical tracking",
        supply_voltage="7.4V 2S LiPo",
        controller="ESP32-WROOM-32D",
        budget_inr=2500.0,
        items=[
            BOMItem(
                name="ESP32-WROOM-32D Dev Board",
                quantity=1,
                purpose="Main controller & telemetry",
                specifications="3.3V logic, Dual Core 240MHz",
                suggested_part_number="ESP32-WROOM-32D",
                unit_price_inr=450.0,
                is_price_verified=True,
                source_reference="Espressif Datasheet",
                compatibility_notes="Requires 3.3V logic matching"
            ),
            BOMItem(
                name="TB6612FNG Motor Driver",
                quantity=1,
                purpose="H-Bridge dual motor drive",
                specifications="VM=4.5V-15V, 1.2A cont, MOSFET",
                suggested_part_number="TB6612FNG",
                unit_price_inr=160.0,
                is_price_verified=True,
                source_reference="Toshiba Datasheet Page 1",
                compatibility_notes="STBY must be tied to VCC"
            ),
            BOMItem(
                name="5-Channel TCRT5000 IR Sensor Array",
                quantity=1,
                purpose="Line contrast optical detection",
                specifications="5V/3.3V compatible, digital outs",
                suggested_part_number="TCRT5000",
                unit_price_inr=190.0,
                is_price_verified=True,
                source_reference="Vishay TCRT5000"
            ),
            BOMItem(
                name="N20 Micro Metal Gearmotors (6V 600RPM)",
                quantity=2,
                purpose="Locomotion wheels",
                specifications="Operating voltage: 3V-9V, Stall ~800mA",
                suggested_part_number="GA12-N20",
                unit_price_inr=220.0,
                is_price_verified=True
            ),
            BOMItem(
                name="100nF Ceramic Decoupling Capacitors",
                quantity=4,
                purpose="High-frequency power rail decoupling",
                specifications="50V X7R 0.1µF",
                suggested_part_number="Ceramic Disc",
                unit_price_inr=2.5,
                is_price_verified=True,
                source_reference="Best practice"
            ),
            BOMItem(
                name="Custom 3D-Printed Chassis & Mounts",
                quantity=1,
                purpose="Structural mounting",
                specifications="PLA filament, 20% infill",
                suggested_part_number="Custom",
                unit_price_inr=None,
                is_price_verified=False,
                compatibility_notes="Unpriced custom component"
            ),
        ]
    )


# --- Helper: Check Ollama Status ---
@st.cache_data(ttl=15)
def get_cached_ollama_status():
    return llm_client.check_status()

ollama_status = get_cached_ollama_status()
stats = vector_store.get_stats()


# --- Sidebar Navigation ---
with st.sidebar:
    st.markdown("## ⚡ CircuitSathi")
    st.caption("Your Local AI Engineering Companion")
    st.markdown("---")

    # Connection Status Pill
    if ollama_status["online"]:
        st.markdown(
            f'<span class="badge-online">● Ollama Online</span> '
            f'<span class="badge-cyan">{settings.active_model}</span>',
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            '<span class="badge-offline">● Ollama Offline</span>',
            unsafe_allow_html=True
        )

    st.markdown(f"**Indexed Docs:** {stats['document_count']} ({stats['total_chunks']} chunks)")
    st.markdown("---")

    selected_nav = st.radio(
        "Navigation",
        [
            "💬 Engineering Chat",
            "📄 Datasheet Assistant",
            "🔍 Component Explorer",
            "📊 BOM Generator",
            "🛠️ Circuit Troubleshooting",
            "📸 Schematic Inspector",
            "⚙️ Settings & System"
        ],
        index=0
    )

    st.markdown("---")
    st.markdown("### 🔒 Privacy Guarantee")
    st.caption(
        "**100% On-Device Processing**\n"
        "Your schematics, code, and proprietary datasheets are processed locally via Ollama. "
        "No cloud telemetry or external API calls."
    )


# ==============================================================================
# SECTION 1: ENGINEERING CHAT
# ==============================================================================
if selected_nav == "💬 Engineering Chat":
    st.title("💬 Engineering Chat")
    st.caption("Evidence-grounded conversational electronics and embedded-systems assistant.")

    # Status alert if Ollama is not ready
    if not ollama_status["online"]:
        st.error(
            "⚠️ **Local Ollama is not running.**\n\n"
            "CircuitSathi requires local Ollama for AI generation. Open PowerShell and run:\n"
            "```powershell\nollama serve\n```"
        )
    elif not ollama_status["has_default_model"] and not ollama_status.get("models"):
        st.warning(
            f"⚠️ **Model `{settings.default_model}` is not downloaded.**\n\n"
            f"Open PowerShell and run:\n```powershell\n{llm_client.get_download_command()}\n```"
        )

    # Chat controls bar
    col_c1, col_c2, col_c3 = st.columns([3, 2, 2])
    with col_c1:
        use_rag = st.checkbox("🔍 Search Uploaded Datasheets (RAG)", value=True, help="Retrieve verified passages from uploaded PDFs")
    with col_c2:
        if st.button("🗑️ Clear Chat", use_container_width=True):
            st.session_state.messages = []
            st.rerun()
    with col_c3:
        if stats["document_count"] == 0:
            if st.button("📥 Load Sample Docs", use_container_width=True, help="Load TB6612FNG & LM7805 sample datasheets"):
                for p_name in ["TB6612FNG_Datasheet.pdf", "LM7805_Datasheet.pdf"]:
                    p_path = SAMPLE_DOCS_DIR / p_name
                    if p_path.exists():
                        res = process_pdf(p_path)
                        vector_store.add_document_chunks(res.chunks)
                st.success("Sample datasheets indexed!")
                st.rerun()

    # Quick Electrical Calculators Expander
    with st.expander("⚡ Quick Engineering Calculators (Deterministic)"):
        calc_tab1, calc_tab2 = st.tabs(["LED Current-Limiting Resistor", "Voltage Divider"])
        with calc_tab1:
            q_col1, q_col2, q_col3 = st.columns(3)
            with q_col1:
                v_sup = st.number_input("Supply Voltage (V)", value=5.0, min_value=1.0, max_value=48.0, step=0.5)
            with q_col2:
                v_fwd = st.number_input("LED Forward Voltage Vf (V)", value=2.0, min_value=1.0, max_value=5.0, step=0.1)
            with q_col3:
                i_target = st.number_input("Target Current (mA)", value=15.0, min_value=1.0, max_value=50.0, step=1.0)
            
            calc_res = calculate_led_resistor(v_sup, v_fwd, i_target)
            if calc_res["success"]:
                st.info(
                    f"**Ideal Resistance:** {calc_res['ideal_resistance_ohms']} Ω | "
                    f"**Standard E12 Resistor:** **{calc_res['standard_e12_resistor_ohms']} Ω** | "
                    f"**Actual Current:** {calc_res['actual_current_ma']} mA | "
                    f"**Power Dissipated:** {calc_res['power_dissipation_watts'] * 1000:.1f} mW ({calc_res['recommended_package_rating']} rating)"
                )
            else:
                st.error(calc_res["error"])

        with calc_tab2:
            vd_col1, vd_col2, vd_col3 = st.columns(3)
            with vd_col1:
                vd_vin = st.number_input("Vin (V)", value=12.0, step=1.0)
            with vd_col2:
                vd_r1 = st.number_input("R1 (Ω)", value=10000.0, step=1000.0)
            with vd_col3:
                vd_r2 = st.number_input("R2 (Ω)", value=3300.0, step=100.0)
            
            vd_res = calculate_voltage_divider(vd_vin, vd_r1, vd_r2)
            if vd_res["success"]:
                st.info(
                    f"**Vout:** **{vd_res['vout']} V** | "
                    f"**Quiescent Current:** {vd_res['quiescent_current_ma']} mA | "
                    f"**R1 Power:** {vd_res['power_r1_watts'] * 1000:.1f} mW | "
                    f"**R2 Power:** {vd_res['power_r2_watts'] * 1000:.1f} mW"
                )

    st.markdown("---")

    # Display chat history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if "citations" in msg and msg["citations"]:
                st.markdown("**Citations:** " + " ".join([f"`{c}`" for c in msg["citations"]]))
            if "passages" in msg and msg["passages"]:
                with st.expander("🔍 View Retrieved Supporting Passages"):
                    for p in msg["passages"]:
                        st.markdown(f"**{p['citation']}** *(Similarity: {p['score']:.2f})*")
                        st.text(p["content"])

    # User Input
    if prompt := st.chat_input("Ask an electronics question (e.g., 'What is the voltage limit of TB6612FNG?')"):
        # Append user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Prepare Assistant response
        with st.chat_message("assistant"):
            retrieved_passages = []
            citations = []

            if use_rag and stats["total_chunks"] > 0:
                retrieved_passages = vector_store.query(prompt, top_k=settings.top_k_retrieval)
                citations = [p["citation"] for p in retrieved_passages]

            with st.spinner("Analyzing technical evidence with local model..."):
                if retrieved_passages:
                    context_str = format_context_for_prompt(retrieved_passages)
                    full_prompt = CIRCUITSATHI_RAG_PROMPT.format(
                        retrieved_context=context_str,
                        query=prompt
                    )
                else:
                    full_prompt = prompt

                try:
                    # Non-streaming or streaming generation
                    response_text = llm_client.generate(
                        prompt=full_prompt,
                        system_prompt=CIRCUITSATHI_SYSTEM_PROMPT,
                        stream=False
                    )
                except Exception as e:
                    response_text = (
                        f"⚠️ **Inference Error**: {str(e)}\n\n"
                        f"Please ensure Ollama is running and has the model installed (`{settings.active_model}`)."
                    )

                st.markdown(response_text)

                if citations:
                    st.markdown("**Citations:** " + " ".join([f"`{c}`" for c in citations]))
                if retrieved_passages:
                    with st.expander("🔍 View Retrieved Supporting Passages"):
                        for p in retrieved_passages:
                            st.markdown(f"**{p['citation']}** *(Similarity: {p['score']:.2f})*")
                            st.text(p["content"])

            # Store in session state
            st.session_state.messages.append({
                "role": "assistant",
                "content": response_text,
                "citations": citations,
                "passages": retrieved_passages
            })


# ==============================================================================
# SECTION 2: DATASHEET ASSISTANT
# ==============================================================================
elif selected_nav == "📄 Datasheet Assistant":
    st.title("📄 Datasheet & Technical Document Assistant")
    st.caption("Upload PDFs, extract page-accurate text, perform OCR on scans, and semantic retrieval.")

    col_up1, col_up2 = st.columns([3, 2])
    with col_up1:
        uploaded_files = st.file_uploader(
            "Upload Component Datasheets (PDF)",
            type=["pdf"],
            accept_multiple_files=True,
            help="All files remain completely on your local drive."
        )

        if uploaded_files:
            for up_file in uploaded_files:
                file_bytes = up_file.read()
                save_path = save_uploaded_file(file_bytes, up_file.name)
                
                with st.spinner(f"Ingesting & Chunking {up_file.name}..."):
                    try:
                        ingest_res = process_pdf(save_path)
                        added = vector_store.add_document_chunks(ingest_res.chunks)
                        st.success(
                            f"✅ **{ingest_res.doc_name}**: Indexed {ingest_res.page_count} pages, "
                            f"{added} chunks into local ChromaDB!"
                        )
                        if ingest_res.ocr_pages_count > 0:
                            st.info(f"OCR applied to {ingest_res.ocr_pages_count} scanned pages.")
                        for w in ingest_res.warnings:
                            st.warning(f"⚠️ {w}")
                    except Exception as e:
                        st.error(f"Failed to ingest {up_file.name}: {str(e)}")

    with col_up2:
        st.markdown("### Quick Demo Setup")
        st.write("Test semantic retrieval immediately with authentic sample datasheets:")
        if st.button("⚡ Index Sample Datasheets (TB6612FNG & LM7805)", use_container_width=True):
            with st.spinner("Indexing sample datasheets..."):
                for p_name in ["TB6612FNG_Datasheet.pdf", "LM7805_Datasheet.pdf"]:
                    sample_path = SAMPLE_DOCS_DIR / p_name
                    if sample_path.exists():
                        res = process_pdf(sample_path)
                        vector_store.add_document_chunks(res.chunks)
                st.success("Sample datasheets indexed successfully!")
                st.rerun()

    st.markdown("---")
    st.subheader("📚 Currently Indexed Documents")

    doc_list = vector_store.list_documents()
    if not doc_list:
        st.info("No documents indexed yet. Upload a datasheet above or click 'Index Sample Datasheets'.")
    else:
        for doc in doc_list:
            c1, c2, c3, c4 = st.columns([4, 2, 2, 2])
            with c1:
                st.markdown(f"**📄 {doc['doc_name']}**")
            with c2:
                st.markdown(f"Pages: `{doc['page_count']}`")
            with c3:
                st.markdown(f"Chunks: `{doc['chunk_count']}`")
            with c4:
                if st.button("🗑️ Delete", key=f"del_{doc['doc_name']}", use_container_width=True):
                    delete_uploaded_document(doc["doc_name"])
                    st.success(f"Deleted {doc['doc_name']}")
                    st.rerun()

    st.markdown("---")
    st.subheader("🔍 Direct Semantic Document Search")
    test_q = st.text_input("Enter search query into indexed datasheets:", placeholder="e.g. STBY standby pin truth table")
    if test_q:
        results = vector_store.query(test_q, top_k=4)
        if not results:
            st.warning("No relevant passages found meeting the relevance threshold.")
        else:
            for r in results:
                st.markdown(
                    f'<div class="component-card">'
                    f'<strong>{r["citation"]}</strong> &nbsp; '
                    f'<span class="citation-pill">Similarity: {r["score"]:.2f}</span><br><br>'
                    f'<code>{r["content"]}</code>'
                    f'</div>',
                    unsafe_allow_html=True
                )


# ==============================================================================
# SECTION 3: COMPONENT EXPLORER
# ==============================================================================
elif selected_nav == "🔍 Component Explorer":
    st.title("🔍 Component Explorer")
    st.caption("Search vetted electronics specifications, operating voltages, pinouts, and critical warnings.")

    search_term = st.text_input("Search Components by Name, Part Number, Category, or Application:", placeholder="e.g. TB6612FNG, ESP32, LM7805, Motor Driver")
    
    categories = ["All Categories", "Motor Driver", "Microcontroller / SoC", "Linear Voltage Regulator", "Diode / Rectifier"]
    selected_cat = st.selectbox("Filter Category:", categories)

    found_components = component_library.search(search_term)
    if selected_cat != "All Categories":
        found_components = [c for c in found_components if selected_cat.lower() in c.category.lower()]

    st.markdown(f"**Showing {len(found_components)} components**")

    for spec in found_components:
        with st.container():
            st.markdown(
                f'<div class="component-card">'
                f'<div class="component-title">{spec.name} ({spec.part_number})</div>'
                f'<div class="component-subtitle">Manufacturer: {spec.manufacturer} | Category: {spec.category} | Source: {spec.source_reference}</div>'
                f'</div>',
                unsafe_allow_html=True
            )

            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**⚡ Operating Voltage:** {spec.operating_voltage}")
                st.markdown(f"**🔥 Absolute Max Ratings:** `{spec.max_ratings}`")
                st.markdown(f"**🔌 Continuous Current:** {spec.continuous_current}")
                if spec.peak_current:
                    st.markdown(f"**⚡ Peak Current:** {spec.peak_current}")
                
                st.markdown("**Key Features:**")
                for f in spec.key_features:
                    st.markdown(f"- {f}")

            with col2:
                st.markdown("**Pinout & Connections:**")
                for p in spec.pin_configuration:
                    st.markdown(f"- `{p}`")

                st.markdown("**Typical Applications:**")
                for a in spec.typical_applications:
                    st.markdown(f"- {a}")

            # Critical Warnings
            if spec.critical_warnings:
                for w in spec.critical_warnings:
                    st.markdown(f'<div class="warning-box">⚠️ <strong>Critical Warning:</strong> {w}</div>', unsafe_allow_html=True)

            st.markdown("---")

    # Add Component Expander
    with st.expander("➕ Add Custom Component to Local Library"):
        with st.form("add_comp_form"):
            c_name = st.text_input("Component Name", placeholder="e.g. 2N2222 NPN Transistor")
            c_part = st.text_input("Part Number", placeholder="e.g. 2N2222")
            c_mfr = st.text_input("Manufacturer", placeholder="e.g. ON Semiconductor")
            c_cat = st.text_input("Category", placeholder="e.g. BJT Transistor")
            c_volt = st.text_input("Operating Voltage", placeholder="e.g. Vce max = 40V")
            c_max = st.text_input("Absolute Maximum Ratings", placeholder="e.g. Ic = 800mA, Vcbo = 75V")
            c_curr = st.text_input("Continuous Current", placeholder="e.g. 600mA")
            c_pins = st.text_area("Pin Configuration (one per line)", placeholder="Pin 1: Emitter\nPin 2: Base\nPin 3: Collector")
            c_src = st.text_input("Source Reference", placeholder="e.g. ON Semi Datasheet Rev 6")
            c_warn = st.text_input("Critical Warning", placeholder="e.g. Base current limiting resistor is required to avoid destruction")
            
            submitted = st.form_submit_button("Save Component")
            if submitted and c_name and c_part:
                new_spec = ComponentSpec(
                    name=c_name,
                    part_number=c_part,
                    manufacturer=c_mfr or "Not verified",
                    category=c_cat or "General",
                    operating_voltage=c_volt or "Not verified",
                    max_ratings=c_max or "Not verified",
                    continuous_current=c_curr or "Not verified",
                    pin_configuration=[p.strip() for p in c_pins.split("\n") if p.strip()],
                    critical_warnings=[c_warn] if c_warn else [],
                    source_reference=c_src or "User Added",
                    is_verified=True
                )
                component_library.add_component(new_spec)
                st.success(f"Component '{c_name}' added to local library!")
                st.rerun()


# ==============================================================================
# SECTION 4: BOM GENERATOR
# ==============================================================================
elif selected_nav == "📊 BOM Generator":
    st.title("📊 Bill of Materials (BOM) Generator")
    st.caption("Deterministic financial arithmetic, Pydantic validation, and professional Excel/CSV export.")

    proj = st.session_state.bom_project

    # Project Metadata Inputs
    with st.expander("🛠️ Project Specifications & Requirements", expanded=True):
        m_c1, m_c2, m_c3 = st.columns(3)
        with m_c1:
            proj.project_name = st.text_input("Project Name", value=proj.project_name)
            proj.supply_voltage = st.text_input("Power Supply", value=proj.supply_voltage)
        with m_c2:
            proj.controller = st.text_input("Microcontroller", value=proj.controller)
            proj.budget_inr = st.number_input("Allocated Budget (₹ INR)", value=float(proj.budget_inr or 2500.0), step=100.0)
        with m_c3:
            proj.project_objective = st.text_input("Objective", value=proj.project_objective)

    st.markdown("---")

    # Metrics Summary
    tot_c1, tot_c2, tot_c3 = st.columns(3)
    with tot_c1:
        st.markdown(
            f'<div class="metric-container">'
            f'<div class="metric-title">Verified Total Cost</div>'
            f'<div class="metric-value">₹{proj.verified_total_inr:.2f}</div>'
            f'</div>',
            unsafe_allow_html=True
        )
    with tot_c2:
        budget_margin = (proj.budget_inr or 0.0) - proj.verified_total_inr
        color = "#10B981" if budget_margin >= 0 else "#EF4444"
        st.markdown(
            f'<div class="metric-container">'
            f'<div class="metric-title">Budget Margin</div>'
            f'<div class="metric-value" style="color: {color};">₹{budget_margin:.2f}</div>'
            f'</div>',
            unsafe_allow_html=True
        )
    with tot_c3:
        st.markdown(
            f'<div class="metric-container">'
            f'<div class="metric-title">Items Status</div>'
            f'<div class="metric-value">{len(proj.items) - proj.unpriced_items_count}/{len(proj.items)} Priced</div>'
            f'</div>',
            unsafe_allow_html=True
        )

    # Interactive Table
    st.subheader("📋 BOM Items Table")
    df = proj.to_dataframe()
    st.dataframe(df, use_container_width=True)

    # Add Item to BOM form
    with st.expander("➕ Add New Item to BOM"):
        with st.form("add_bom_item_form"):
            b_c1, b_c2, b_c3 = st.columns(3)
            with b_c1:
                item_name = st.text_input("Component Name", placeholder="e.g. 1N4007 Diode")
                item_qty = st.number_input("Quantity", min_value=1, value=1, step=1)
                item_purpose = st.text_input("Purpose", placeholder="e.g. Flyback protection")
            with b_c2:
                item_specs = st.text_input("Specifications", placeholder="e.g. 1000V 1A DO-41")
                item_part = st.text_input("Part Number", placeholder="e.g. 1N4007")
                item_price = st.number_input("Unit Price (₹ INR, 0 if unverified)", min_value=0.0, value=0.0, step=0.5)
            with b_c3:
                item_src = st.text_input("Source Reference", placeholder="e.g. Local Electronics Supplier")
                item_compat = st.text_input("Compatibility Notes", placeholder="e.g. Cathode to VM")
                item_verified = st.checkbox("Price is Verified?", value=item_price > 0)

            add_submit = st.form_submit_button("Add Item")
            if add_submit and item_name:
                new_item = BOMItem(
                    name=item_name,
                    quantity=int(item_qty),
                    purpose=item_purpose or "General",
                    specifications=item_specs or "Standard",
                    suggested_part_number=item_part or "-",
                    unit_price_inr=float(item_price) if item_price > 0 else None,
                    is_price_verified=item_verified and item_price > 0,
                    source_reference=item_src or "Supplier",
                    compatibility_notes=item_compat
                )
                proj.items.append(new_item)
                st.success(f"Added {item_name} to BOM!")
                st.rerun()

    # Export Section
    st.markdown("---")
    st.subheader("📥 Export Bill of Materials")
    ex_c1, ex_c2 = st.columns(2)
    with ex_c1:
        excel_bytes = proj.export_excel_bytes()
        st.download_button(
            label="📊 Download Formatted Excel Workbook (.xlsx)",
            data=excel_bytes,
            file_name=f"BOM_{proj.project_name.replace(' ', '_')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
    with ex_c2:
        csv_data = proj.export_csv()
        st.download_button(
            label="📄 Download CSV File (.csv)",
            data=csv_data,
            file_name=f"BOM_{proj.project_name.replace(' ', '_')}.csv",
            mime="text/csv",
            use_container_width=True
        )


# ==============================================================================
# SECTION 5: CIRCUIT TROUBLESHOOTING
# ==============================================================================
elif selected_nav == "🛠️ Circuit Troubleshooting":
    st.title("🛠️ Circuit Troubleshooting Assistant")
    st.caption("Guided diagnostic workflows fusing deterministic electrical checks and evidence-based AI reasoning.")

    with st.form("troubleshoot_form"):
        st.markdown("### 1. Circuit Parameters & Safety Profile")
        t_c1, t_c2, t_c3 = st.columns(3)
        with t_c1:
            t_v = st.number_input("Supply Voltage (V)", value=5.0, min_value=0.5, max_value=250.0, step=0.5)
            t_ctrl_v = st.selectbox("Controller Logic Level", [3.3, 5.0, 1.8], index=0)
        with t_c2:
            t_i = st.number_input("Estimated Total Current (A)", value=0.8, min_value=0.01, max_value=50.0, step=0.1)
            t_peri_v = st.selectbox("Peripheral / Sensor Logic Level", [3.3, 5.0, 12.0], index=1)
        with t_c3:
            t_has_inductive = st.checkbox("Includes Motors, Solenoids, or Relays?", value=True)
            t_is_battery = st.checkbox("Battery Powered?", value=True)
            t_battery_type = st.text_input("Battery Type (if battery powered)", value="2S LiPo 7.4V 1500mAh")

        st.markdown("### 2. Circuit Details & Symptoms")
        t_desc = st.text_input("Project Description", value="Differential drive robot with TB6612FNG and ESP32")
        t_wiring = st.text_area("Wiring Configuration", value="ESP32 GPIO 16, 17 connected to AIN1, AIN2. Motor connected to AO1, AO2. Common ground connected.")
        t_power = st.text_input("Power Supply Details", value="7.4V LiPo connected to TB6612FNG VM pin. ESP32 powered from 5V regulator.")
        t_comps = st.text_input("Components & Part Numbers", value="TB6612FNG, ESP32-WROOM-32D, N20 DC Gearmotors")
        t_symptoms = st.text_area("Observed Symptoms", value="Motors do not spin at all when code runs. Microcontroller LED is on, but motor outputs measure 0V.")
        t_expected = st.text_input("Expected Behavior", value="Motors should spin forward when PWMA is high and AIN1=HIGH, AIN2=LOW.")
        t_measurements = st.text_input("Measurements Taken", value="VM voltage = 7.4V, VCC voltage = 3.3V, STBY pin voltage = 0.05V")

        submit_troubleshoot = st.form_submit_button("🔍 Run Diagnostic Analysis")

    if submit_troubleshoot:
        req = TroubleshootingRequest(
            project_description=t_desc,
            wiring_topology=t_wiring,
            power_supply=t_power,
            supply_voltage_v=t_v,
            estimated_current_a=t_i,
            components=t_comps,
            symptoms=t_symptoms,
            expected_behavior=t_expected,
            measurements_taken=t_measurements,
            has_motors_or_relays=t_has_inductive,
            is_battery_powered=t_is_battery,
            battery_type=t_battery_type,
            controller_logic_v=t_ctrl_v,
            peripheral_logic_v=t_peri_v
        )

        with st.spinner("Executing deterministic safety checks & model diagnosis..."):
            diag_result = conduct_troubleshooting(req)

        # 1. Deterministic Safety Warnings Box
        st.subheader("⚠️ Safety & Electrical Hazard Checks")
        if not diag_result.safety_warnings:
            st.success("✅ No critical voltage, thermal, or logic level violations detected.")
        else:
            for w in diag_result.safety_warnings:
                if w["severity"] == "CRITICAL HAZARD":
                    st.markdown(f'<div class="hazard-box">🚨 <strong>{w["category"]}</strong>: {w["message"]}</div>', unsafe_allow_html=True)
                elif w["severity"] == "WARNING":
                    st.markdown(f'<div class="warning-box">⚠️ <strong>{w["category"]}</strong>: {w["message"]}</div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="advisory-box">ℹ️ <strong>{w["category"]}</strong>: {w["message"]}</div>', unsafe_allow_html=True)

        # 2. Citations & Supporting Passages
        if diag_result.retrieved_citations:
            st.markdown("**Datasheet Citations Found:** " + " ".join([f"`{c}`" for c in diag_result.retrieved_citations]))

        # 3. AI Diagnostic Analysis
        st.subheader("🩺 Root Cause & Diagnostic Plan")
        st.markdown(diag_result.analysis_text)

        st.caption(f"🔒 {diag_result.disclaimer}")


# ==============================================================================
# SECTION 6: SCHEMATIC & IMAGE INSPECTOR
# ==============================================================================
elif selected_nav == "📸 Schematic Inspector":
    st.title("📸 Schematic & Image Inspector")
    st.caption("Upload schematic diagrams, PCB layouts, or breadboard wiring photos for visual analysis.")

    uploaded_img = st.file_uploader(
        "Upload Circuit Image (PNG, JPG)",
        type=["png", "jpg", "jpeg"],
        help="Analyzed locally if your Ollama model supports vision (e.g. Gemma 3 / LLaVA)."
    )

    if uploaded_img:
        img_bytes = uploaded_img.read()
        st.image(img_bytes, caption="Uploaded Circuit Image", use_container_width=True)

        if st.button("🔍 Analyze Schematic Image"):
            with st.spinner("Analyzing image features..."):
                b64_img = base64.b64encode(img_bytes).decode("utf-8")
                try:
                    analysis = llm_client.generate(
                        prompt="Analyze this electronics circuit schematic or breadboard wiring.",
                        system_prompt=CIRCUITSATHI_IMAGE_PROMPT,
                        images=[b64_img],
                        stream=False
                    )
                    st.markdown("### Analysis Results")
                    st.markdown(analysis)
                except Exception as e:
                    st.warning(
                        f"Visual inference returned: {str(e)}\n\n"
                        "Note: Vision capability requires an image-capable model variant in Ollama."
                    )


# ==============================================================================
# SECTION 7: SETTINGS & SYSTEM
# ==============================================================================
elif selected_nav == "⚙️ Settings & System":
    st.title("⚙️ Settings & System Diagnostics")
    st.caption("Configure local Ollama connection, model weights, retrieval parameters, and local data.")

    # Status Overview
    st.subheader("🖥️ Ollama Local Server")
    s_col1, s_col2 = st.columns(2)
    with s_col1:
        st.text_input("Ollama Host URL", value=settings.ollama_base_url, disabled=True)
        st.markdown(f"**Connection Status:** `{'ONLINE' if ollama_status['online'] else 'OFFLINE'}`")
    with s_col2:
        installed_models = ollama_status.get("models", [])
        st.markdown(f"**Detected Local Models ({len(installed_models)}):**")
        if installed_models:
            for m in installed_models:
                st.markdown(f"- `{m}`")
        else:
            st.info("No models currently installed in Ollama.")

    st.markdown("---")
    st.subheader("🧠 Model Selection")
    all_options = list(set([settings.default_model, settings.fallback_model] + installed_models))
    current_idx = all_options.index(settings.active_model) if settings.active_model in all_options else 0
    new_model = st.selectbox("Select Active Model:", all_options, index=current_idx)
    if new_model != settings.active_model:
        settings.active_model = new_model
        st.success(f"Active model switched to `{new_model}`")

    # Command Guide to Pull Recommended Models
    st.markdown("#### Recommended Models:")
    st.markdown(
        "- Default Recommended: `gemma3:4b` (`ollama pull gemma3:4b`)\n"
        "- Lightweight Fallback: `gemma3:1b` (`ollama pull gemma3:1b`)\n"
        "- Currently Available: `" + (", ".join(installed_models) if installed_models else "None") + "`"
    )

    st.markdown("---")
    st.subheader("🔍 Vector Store & Retrieval Configuration")
    r_col1, r_col2 = st.columns(2)
    with r_col1:
        settings.top_k_retrieval = st.slider("Top-K Retrieval Count", min_value=1, max_value=8, value=settings.top_k_retrieval)
    with r_col2:
        settings.score_threshold = st.slider("Similarity Score Threshold", min_value=0.05, max_value=0.7, value=settings.score_threshold, step=0.05)

    st.markdown("---")
    st.subheader("👁️ OCR Engine Status")
    ocr_ok = is_ocr_available()
    if ocr_ok:
        st.success("✅ Tesseract OCR is installed and available for scanned PDFs.")
    else:
        st.info("ℹ️ Tesseract OCR is not detected on PATH. Text extraction from vector/digital PDFs is fully active. To OCR scanned documents, install Tesseract for Windows.")

    st.markdown("---")
    st.subheader("🧹 Privacy & Local Data Wipe")
    st.warning("Permanently deletes all uploaded PDFs, extracted text chunks, and local ChromaDB vectors.")
    if st.button("🚨 Purge All Local Uploads and Vector Database", type="secondary"):
        if purge_all_data():
            st.success("All local documents and vector collections purged cleanly!")
            st.rerun()
        else:
            st.error("Error purging data.")
