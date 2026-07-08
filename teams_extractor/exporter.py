import os

def export_contacts_to_excel():
    output_dir = os.path.join(os.path.dirname(__file__), "output")
    csv_file = os.path.join(output_dir, "extracted_contacts.csv")
    
    if os.path.exists(csv_file):
        return csv_file
    else:
        raise Exception("No data extracted yet. File extracted_contacts.csv not found.")
