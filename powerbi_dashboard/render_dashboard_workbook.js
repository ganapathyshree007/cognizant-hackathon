const fs = require('node:fs/promises');
const { FileBlob, SpreadsheetFile } = require('@oai/artifact-tool');

async function main() {
  const path = 'C:/COGNIZANT HACKATHON/powerbi_dashboard/UC07_PowerBI_Dashboard_Companion.xlsx';
  const wb = await SpreadsheetFile.importXlsx(await FileBlob.load(path));
  for (const [sheetName, range] of [
    ['Dashboard Overview', 'A1:H13'],
    ['Source Tables', 'A1:E12'],
    ['DAX Measures', 'A1:C11']
  ]) {
    const image = await wb.render({ sheetName, range, scale: 2, format: 'png' });
    await fs.writeFile(`C:/COGNIZANT HACKATHON/powerbi_dashboard/render_${sheetName.replaceAll(' ', '_')}.png`, new Uint8Array(await image.arrayBuffer()));
  }
}
main().catch(err => { console.error(err); process.exit(1); });
