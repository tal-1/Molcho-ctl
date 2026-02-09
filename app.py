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
    # We will add the S3 UI code here later

elif "Route53" in service:
    st.header("🌐 Route53 DNS Manager")
    # We will add the DNS UI code here later
