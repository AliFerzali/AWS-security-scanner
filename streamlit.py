import streamlit as st
import json
import io
import pandas as pd
from fpdf import FPDF
import checker
from datetime import datetime
import streamlit.components.v1 as components

# --- Recommended Actions Mapping ---
recommended_actions = {
    "Public access may be allowed due to misconfigured Public Access Block settings.":
        "Update the Public Access Block settings to enable BlockPublicAcls, IgnorePublicAcls, BlockPublicPolicy, and RestrictPublicBuckets.",
    "Bucket logging is not enabled.":
        "Enable bucket logging to track access and modifications for audit purposes.",
    "SSH (port 22) open to the world.":
        "Restrict SSH access by allowing only known IP addresses or use a VPN/bastion host.",
    "RDP (port 3389) open to the world.":
        "Restrict RDP access to specific IP ranges or use a bastion host for secure remote access.",
    "ICMP (Ping) open to the world.":
        "Limit ICMP access to known IP ranges or disable it if not required.",
    "Wide-open rule (0.0.0.0/0) detected.":
        "Review and tighten security group rules to only allow necessary traffic.",
    "HTTP (port 80) open to the world.":
        "Restrict HTTP access or use a web application firewall (WAF) to protect against attacks.",
    "User does not have MFA enabled.":
        "Enable Multi-Factor Authentication (MFA) on the user account.",
    "User account appears to be inactive (no console or API usage).":
        "Review the account's usage and consider deactivating or removing unused accounts.",
    "Default route to an Internet Gateway detected; verify if intended for public subnets.":
        "Ensure that default routes are appropriate for public subnets; for private subnets, adjust the route to use a NAT Gateway.",
    "Overly permissive rule allowing all traffic from 0.0.0.0/0 detected.":
        "Tighten ACL rules to restrict traffic to only necessary sources and destinations.",
    "VPC Flow Logs are not enabled, which may hinder network traffic monitoring.":
        "Enable VPC Flow Logs to capture and analyze network traffic for anomalies."
}

# --- Function to Run Compliance Checks ---
def run_compliance_checks():
    results = {
        "S3_Compliance_Issues": checker.check_s3_compliance(),
        "EC2_SG_Issues": checker.check_ec2_security_groups(),
        "IAM_Issues": checker.check_iam_policies(),
        "VPC_Issues": checker.check_vpc_configurations()
    }
    return results

# --- Function to Generate PDF Report Using fpdf ---
def generate_pdf_report(results):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "AWS Compliance Scan Report", ln=True, align="C")
    pdf.ln(10)
    
    for category, items in results.items():
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, category.replace("_", " "), ln=True)
        pdf.set_font("Arial", "", 12)
        for item in items:
            resource = (
                item.get("Bucket") or
                item.get("SecurityGroup") or
                item.get("Role") or
                item.get("User") or
                item.get("RouteTable") or
                item.get("NetworkACL") or
                item.get("VPC") or
                "Unknown"
            )
            pdf.cell(0, 10, f"Resource: {resource}", ln=True)
            for issue in item.get("Issues", []):
                issue_text = issue.get("Issue")
                mapping = issue.get("DORA_Mapping")
                action = recommended_actions.get(issue_text, "No recommendation available.")
                pdf.multi_cell(0, 10, f"Issue: {issue_text}\nDORA Mapping: {mapping}\nRecommendation: {action}\n", border=0)
            pdf.ln(5)
        pdf.ln(10)
    
    pdf_output = pdf.output(dest="S")
    if isinstance(pdf_output, bytearray):
        pdf_output = bytes(pdf_output)
    return pdf_output

# --- Custom CSS for Dataframe Styling ---
custom_code = """
<style>
    .dataframe th, .dataframe td {
        text-align: left;
    }
</style>
"""

# --- Streamlit Dashboard ---
def main():
    st.title("AWS Cloud Security Compliance Checker")
    st.markdown("""
    This dashboard displays the results of automated compliance checks on AWS resources, mapping detected misconfigurations to specific DORA compliance requirements.
    """)

    # *** Create a placeholder for the timestamp ***
    timestamp_placeholder = st.empty()

    # --- Auto-run compliance checks on first load ---
    if "results" not in st.session_state:
        st.session_state.results = run_compliance_checks()
        st.session_state.last_run = datetime.now()

    # --- "Re-Run Compliance Checks" Button ---
    if st.button("Re-Run Compliance Checks"):
        with st.spinner("Collecting data from AWS..."):
            st.session_state.results = run_compliance_checks()
            st.session_state.last_run = datetime.now()
        st.success("✅ Compliance checks completed!")
    
    # *** Update the timestamp placeholder with the current last_run value ***
    timestamp_placeholder.markdown(f"**Last checked:** {st.session_state.last_run.strftime('%Y-%m-%d %H:%M:%S')}")

    results = st.session_state.results

    # --- Inject Custom CSS ---
    components.html(custom_code, height=0)

    # --- Display Results in Formatted Tables ---
    for category, items in results.items():
        st.subheader(category.replace("_", " "))
        table_data = []
        for item in items:
            resource = (
                item.get("Bucket") or
                item.get("SecurityGroup") or
                item.get("Role") or
                item.get("User") or
                item.get("RouteTable") or
                item.get("NetworkACL") or
                item.get("VPC") or
                "Unknown"
            )
            for issue in item.get("Issues", []):
                table_data.append({
                    "No.": len(table_data) + 1,  # Numbering starts from 1
                    "Resource": resource,
                    "Issue": issue.get("Issue"),
                    "DORA Mapping": issue.get("DORA_Mapping"),
                    "Recommendation": recommended_actions.get(issue.get("Issue"), "No recommendation available.")
                })

        if table_data:
            df = pd.DataFrame(table_data)
            df = df.set_index("No.")  # Use "No." as index
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No issues detected for this category.")

    # --- Generate PDF Report ---
    pdf_data = generate_pdf_report(results)
    st.download_button(
        label="Download PDF Report",
        data=pdf_data,
        file_name="Compliance_Report.pdf",
        mime="application/pdf"
    )

if __name__ == '__main__':
    main()
