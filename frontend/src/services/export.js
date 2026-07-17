import { toast } from 'react-hot-toast'
import * as XLSX from 'xlsx';

/**
 * Export data to an Excel (.xlsx) file.
 * @param {Array<Object>} data - The list of objects to export.
 * @param {string} filename - The filename without extension (e.g. 'recruiters_export')
 */
export function exportToExcel(data, filename) {
  if (!data || data.length === 0) {
    toast.error("No data available to export.");
    return;
  }
  
  // Create a worksheet from the data
  const worksheet = XLSX.utils.json_to_sheet(data);
  
  // Create a new workbook and append the worksheet
  const workbook = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(workbook, worksheet, "Data");
  
  // Save the file
  XLSX.writeFile(workbook, `${filename}.xlsx`);
}
