import streamlit as st
from resources.ec2_manager import EC2Manager
from resources.s3_manager import S3Manager
from resources.route53_manager import Route53Manager

# --- Page Configuration ---
st.set_page_config(
    page_title="Molchoctl WebApp",
    page_icon="☁️",
    layout="wide"
)

# --- Title & Header ---
st.title("☁️ Molcho Platform Engineering")
st.markdown("### Self-Service Cloud Portal")
st.divider()

# --- Sidebar Navigation ---
st.sidebar.title("Navigation")
service = st.sidebar.radio(
    "Select Service:",
    ["EC2 (Compute)", "S3 (Storage)", "Route53 (DNS)"]
)

st.sidebar.markdown("---")
st.sidebar.info("🔒 Logged in as: **Platform User**")

# --- Routing Logic ---
if "EC2" in service:
    st.header("🖥️ EC2 Instance Management")
    # Initialize the Manager (Logic)
    ec2_manager = EC2Manager()

    # --- 1. List Instances (The Dashboard) ---
    st.subheader("Active Instances")
    try:
        instances = ec2_manager.list_instances()
        
        if not instances:
            st.info("No instances found. Launch one below! 👇")
        else:
            # Convert the list of dictionaries to a Pandas DataFrame for a pretty table
            import pandas as pd
            df = pd.DataFrame(instances)
            
            # Show the table (use_container_width makes it fill the screen)
            st.dataframe(
                df, 
                column_config={
                    "InstanceId": "ID",
                    "State": "Status",
                    "Type": "Size",
                    "PublicIP": "Public IP"
                },
                use_container_width=True
            )
    except Exception as e:
        st.error(f"Error loading instances: {e}")

    st.divider()

    # --- 2. Create Instance Form ---
    st.subheader("🚀 Launch New Instance")
    
    # st.form prevents the page from reloading while you type
    with st.form("create_ec2_form"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            name = st.text_input("Server Name", placeholder="molcho-web-01")
        with col2:
            os_type = st.selectbox("Operating System", ["amazon_linux", "ubuntu"])
        with col3:
            instance_type = st.selectbox("Instance Type", ["t3.micro", "t2.small"])
        
        # The form is only submitted when this button is clicked
        submitted = st.form_submit_button("Launch Instance")
        
        if submitted:
            if not name:
                st.error("Please provide a server name.")
            else:
                with st.spinner("Provisioning instance (this may take a few seconds)..."):
                    # We use keyword arguments (name=name) to be safe regardless of parameter order
                    result = ec2_manager.create_instance(
                        name_tag=name, 
                        os_type=os_type, 
                        instance_type=instance_type
                    )
                    
                    if "error" in result:
                        st.error(f"Failed: {result['error']}")
                    else:
                        st.success(f"Success! Created instance {result['id']}")
                        st.rerun()  # Force reload to show the new instance in the table

    st.divider()

    # --- 3. Manage Instances (Start/Stop/Delete) ---
    st.subheader("⚙️ Manage Instance State")
    
    if instances:
        # --- UX IMPROVEMENT: Mapping Names to IDs ---
        # We create a dictionary where:
        # Key (What you see): "ServerName (InstanceID)"
        # Value (What code uses): "InstanceID"
        instance_map = {f"{i['Name']} ({i['ID']})": i['ID'] for i in instances}
        
        # The dropdown now shows the readable keys
        selected_label = st.selectbox("Select Instance to Manage:", list(instance_map.keys()))
        
        # We grab the actual ID from our map to send to AWS
        selected_id = instance_map[selected_label]
        
        # Create 3 columns for the buttons
        btn1, btn2, btn3 = st.columns(3)
        
        with btn1:
            if st.button("▶ Start Instance"):
                res = ec2_manager.manage_state(selected_id, "start")
                if "success" in res:
                    st.success(f"Starting {selected_label}...")
                    st.rerun()
                else:
                    st.error(res.get("error"))

        with btn2:
            if st.button("⏹ Stop Instance"):
                res = ec2_manager.manage_state(selected_id, "stop")
                if "success" in res:
                    st.warning(f"Stopping {selected_label}...")
                    st.rerun()
                else:
                    st.error(res.get("error"))

        with btn3:
            # Type='primary' makes the button red/highlighted
            if st.button("🗑 Terminate (Delete)", type="primary"):
                res = ec2_manager.manage_state(selected_id, "delete")
                if "success" in res:
                    st.success(f"Terminated {selected_label}.")
                    st.rerun()
                else:
                    st.error(res.get("error"))

elif "S3" in service:
    st.header("📦 S3 Bucket Storage")
    
    s3_manager = S3Manager()

    # --- 1. List Buckets ---
    st.subheader("Existing Buckets")
    try:
        buckets = s3_manager.list_buckets()
        
        if not buckets:
            st.info("No tagged buckets found. (Buckets must have 'Project: platform-engineering' tag)")
        else:
            # FIX: Updated to remove warning (use_container_width -> width)
            st.dataframe(buckets, width="stretch")
    except Exception as e:
        st.error(f"Error loading buckets: {e}")

    st.divider()

    # --- 2. Create Bucket ---
    st.subheader("🆕 Create New Bucket")
    with st.form("create_s3_form"):
        col1, col2 = st.columns([3, 1])
        
        with col1:
            b_name = st.text_input("Bucket Name", placeholder="molcho-data-123")
        with col2:
            st.write("") # Spacer
            st.write("") 
            # FIX: Add Public Access Toggle
            is_public = st.checkbox("Enable Public Access? 🌍")
        
        if st.form_submit_button("Create Bucket"):
            if not b_name:
                st.error("Bucket name is required.")
            else:
                # FIX: Smart Cleaning (Strip spaces AND replace middle spaces with hyphens)
                clean_name = b_name.strip().replace(" ", "-").lower()
                
                with st.spinner(f"Creating {'PUBLIC' if is_public else 'PRIVATE'} bucket: {clean_name}..."):
                    # We pass the public flag to the manager
                    res = s3_manager.create_bucket(clean_name, public=is_public)
                    
                    if "error" in res:
                        st.error(res['error'])
                    else:
                        st.success(f"Successfully created bucket: {clean_name}")
                        st.rerun()

    st.divider()

    # --- 3. Manage Buckets (Upload & Delete) ---
    st.subheader("📂 Manage Bucket Content")
    
    if buckets:
        bucket_names = [b['Name'] for b in buckets]
        selected_bucket = st.selectbox("Select Target Bucket:", bucket_names)

        tab1, tab2 = st.tabs(["⬆ Upload File", "🗑 Delete Bucket"])

        # TAB 1: Upload Logic
        with tab1:
            uploaded_file = st.file_uploader("Choose a file to upload")
            
            if uploaded_file is not None:
                if st.button("Upload to S3"):
                    import tempfile
                    import os
                    
                    with tempfile.NamedTemporaryFile(delete=False) as tmp:
                        tmp.write(uploaded_file.getvalue())
                        tmp_path = tmp.name
                    
                    try:
                        with st.spinner("Uploading..."):
                            res = s3_manager.upload_file(
                                selected_bucket, 
                                tmp_path, 
                                object_name=uploaded_file.name
                            )
                            
                            if "success" in res:
                                st.success(f"✅ Uploaded '{uploaded_file.name}' to {selected_bucket}")
                            else:
                                st.error(res.get('error'))
                    finally:
                        os.unlink(tmp_path)

        # TAB 2: Delete Logic
        with tab2:
            st.warning("⚠️ Warning: Bucket must be empty before deleting.")
            
            if st.button("Delete Bucket", type="primary"):
                res = s3_manager.delete_bucket(selected_bucket)
                if "success" in res:
                    st.success(f"Deleted {selected_bucket}")
                    st.rerun()
                else:
                    st.error(res.get('error'))

elif "Route53" in service:
    st.header("🌐 Route53 DNS Manager")
    
    route53_manager = Route53Manager()

    # --- 1. List Hosted Zones ---
    st.subheader("Hosted Zones (Domains)")
    try:
        zones = route53_manager.list_hosted_zones()
        if not zones:
            st.info("No hosted zones found.")
        else:
            st.dataframe(zones, width="stretch")
    except Exception as e:
        st.error(f"Error loading zones: {e}")

    st.divider()

    # --- 2. Create New Zone ---
    with st.expander("➕ Create New Hosted Zone"):
        with st.form("create_zone_form"):
            domain_name = st.text_input("Domain Name", placeholder="molcho-app.com")
            private_zone = st.checkbox("Private Zone (VPC only)")
            
            if st.form_submit_button("Create Zone"):
                if not domain_name:
                    st.error("Domain name is required.")
                else:
                    with st.spinner("Creating Hosted Zone..."):
                        res = route53_manager.create_hosted_zone(domain_name, private_zone)
                        if "error" in res:
                            st.error(res['error'])
                        else:
                            st.success(f"Created zone: {res['Id']}")
                            st.rerun()

    st.divider()

    # --- 3. Manage Records ---
    if zones:
        st.subheader("📝 Manage DNS Records")
        
        # Create a map: "molcho.com (Z123...)" -> "Z123..."
        zone_map = {f"{z['Name']} ({z['Id']})": z['Id'] for z in zones}
        selected_zone_label = st.selectbox("Select Zone to Manage:", list(zone_map.keys()))
        selected_zone_id = zone_map[selected_zone_label]
        
        # TABS for viewing vs creating
        tab_view, tab_add, tab_del = st.tabs(["👁 View Records", "➕ Add Record", "❌ Delete Record"])
        
        # TAB 1: View
        with tab_view:
            records = route53_manager.list_records(selected_zone_id)
            if records:
                st.dataframe(records, width="stretch")
            else:
                st.info("No records found in this zone.")

        # TAB 2: Add Record
        with tab_add:
            with st.form("add_record_form"):
                c1, c2, c3 = st.columns([2, 1, 1])
                with c1:
                    r_name = st.text_input("Record Name", placeholder="www")
                with c2:
                    r_type = st.selectbox("Type", ["A", "CNAME", "TXT"])
                with c3:
                    r_ttl = st.number_input("TTL", value=300, min_value=60)
                
                r_value = st.text_input("Value", placeholder="1.2.3.4 (for A) or example.com (for CNAME)")
                
                if st.form_submit_button("Add Record"):
                    if not r_name or not r_value:
                        st.error("Name and Value are required.")
                    else:
                        # Auto-append domain if user forgot (e.g., 'www' -> 'www.molcho.com')
                        # But Route53 is usually smart. Let's send it raw.
                        full_name = r_name # The manager might handle the full name logic
                        
                        res = route53_manager.create_record(selected_zone_id, full_name, r_type, r_value, r_ttl)
                        if "success" in res:
                            st.success(f"Created record: {full_name} -> {r_value}")
                            st.rerun()
                        else:
                            st.error(res.get('error'))

        # TAB 3: Delete Record
        with tab_del:
            st.warning("⚠️ Deleting records can break your site.")
            # We need to pick a record to delete. 
            # We'll use a dropdown of existing records.
            if records:
                # Create readable list: "www.molcho.com. (A)"
                record_map = {f"{r['Name']} ({r['Type']})": r for r in records}
                selected_rec_label = st.selectbox("Select Record to Delete:", list(record_map.keys()))
                
                if st.button("Delete Selected Record", type="primary"):
                    target = record_map[selected_rec_label]
                    # We need to send the exact values to delete safely
                    res = route53_manager.delete_record(selected_zone_id, target['Name'], target['Type'], target['Value'])
                    if "success" in res:
                        st.success("Record deleted.")
                        st.rerun()
                    else:
                        st.error(res.get('error'))
