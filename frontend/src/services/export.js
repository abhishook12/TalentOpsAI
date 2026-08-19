import { toast } from 'react-hot-toast'

/**
 * Standardizes recruiter / candidate record to the exact 5 required columns:
 * 1. Name
 * 2. Email
 * 3. Company
 * 4. Phone Number
 * 5. Designation
 */
export function formatRecruiterForExport(item) {
  if (!item) {
    return {
      'Name': '',
      'Email': '',
      'Company': '',
      'Phone Number': '',
      'Designation': ''
    };
  }

  return {
    'Name': item.Name || item.recruiter_name || item.name || item.contact_name || '',
    'Email': item.Email || item.email || item.verified_email || item.likely_email || '',
    'Company': item.Company || item.company_name || item.company || '',
    'Phone Number': item['Phone Number'] || item.Phone || item.phone || item.phone_number || item.direct_phone || '',
    'Designation': item.Designation || item.designation || item.title || item.specialization || item.position || ''
  };
}

/**
 * Export data to an Excel (.xlsx) file with ONLY the 5 required columns:
 * Name, Email, Company, Phone Number, Designation
 * @param {Array<Object>} data - The list of recruiter/contact objects to export.
 * @param {string} filename - The filename without extension (e.g. 'recruiters_export')
 */
export async function exportToExcel(data, filename = 'recruiters_export') {
  if (!data || data.length === 0) {
    toast.error("No data available to export.");
    return;
  }
  
  // Format each row to strictly contain only: Name, Email, Company, Phone Number, Designation
  const standardizedData = data.map(formatRecruiterForExport);
  
  // Dynamically load XLSX only when needed
  const XLSX = await import('xlsx');
  
  // Create a worksheet with specific column headers
  const worksheet = XLSX.utils.json_to_sheet(standardizedData, {
    header: ['Name', 'Email', 'Company', 'Phone Number', 'Designation']
  });
  
  // Set clean auto column widths
  worksheet['!cols'] = [
    { wch: 25 }, // Name
    { wch: 32 }, // Email
    { wch: 28 }, // Company
    { wch: 18 }, // Phone Number
    { wch: 32 }, // Designation
  ];
  
  // Create a new workbook and append the worksheet
  const workbook = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(workbook, worksheet, "Recruiters");
  
  // Clean filename
  const cleanFilename = filename.endsWith('.xlsx') ? filename : `${filename}.xlsx`;
  
  // Save the file
  XLSX.writeFile(workbook, cleanFilename);
  toast.success(`Exported ${standardizedData.length} records successfully!`);
}
