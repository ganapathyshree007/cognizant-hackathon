const { Workbook, SpreadsheetFile } = require('@oai/artifact-tool');

async function main() {
  const wb = Workbook.create();
  const navy = '#0B1F3A';
  const teal = '#0F766E';
  const pale = '#F6F8FB';

  const overview = wb.worksheets.add('Dashboard Overview');
  overview.getRange('A1:H1').merge();
  overview.getRange('A1').values = [['UC07 | Power BI Dashboard Package']];
  overview.getRange('A1').format = { fill: navy, font: { bold: true, color: '#FFFFFF', size: 20 }, horizontalAlignment: 'center', verticalAlignment: 'center' };
  overview.getRange('A1:H1').format.rowHeight = 34;
  overview.getRange('A3:H3').merge();
  overview.getRange('A3').values = [['Care-manager decision support • Human review required • Opportunity scoring never replaces safety evaluation']];
  overview.getRange('A3').format = { fill: '#E0F2FE', font: { color: navy, italic: true }, horizontalAlignment: 'center' };
  overview.getRange('A5:B10').values = [
    ['Dashboard page', 'Purpose'],
    ['1. Navigator Command Center', 'Executive view of CMS proxy-risk cases, risk bands, pathways, and queue.'],
    ['2. Safety First', 'Separate Synthea validation page for safety rule outcomes.'],
    ['3. Care Manager Workbench', 'Case-level review and human approval workflow.'],
    ['4. Provider Navigator', 'Compact demo directory; backend API remains the live source.'],
    ['5. Intervention & Outcomes', 'Approved actions and outcomes separated by anchor.']
  ];
  overview.getRange('A5:B5').format = { fill: teal, font: { bold: true, color: '#FFFFFF' } };
  overview.getRange('A5:B10').format.wrapText = true;
  overview.getRange('A5:B10').format.borders = { style: 'continuous', color: '#CBD5E1' };
  overview.getRange('A5').format.columnWidth = 31;
  overview.getRange('B5').format.columnWidth = 72;
  overview.getRange('A13:H13').merge();
  overview.getRange('A13').values = [['Critical data guardrail: CMS member identifiers must never be joined to Synthea member identifiers. They are distinct source populations.']];
  overview.getRange('A13').format = { fill: '#FEF2F2', font: { bold: true, color: '#991B1B' }, wrapText: true };
  overview.getRange('A13:H13').format.rowHeight = 30;

  const sources = wb.worksheets.add('Source Tables');
  sources.getRange('A1:E1').merge();
  sources.getRange('A1').values = [['Power BI Import Map']];
  sources.getRange('A1').format = { fill: navy, font: { bold: true, color: '#FFFFFF', size: 16 }, horizontalAlignment: 'center' };
  sources.getRange('A3:E12').values = [
    ['Power BI table', 'Rows', 'Role', 'Source population', 'Import note'],
    ['Fact_CMS_Cases', 60398, 'Core case fact', 'CMS proxy-risk', 'Relate index_date to Dim_Date only.'],
    ['Dim_Date', 1006, 'Date dimension', 'Derived', 'One-to-many with Fact_CMS_Cases.'],
    ['Fact_Evidence_Links', 144595, 'Drill-through evidence', 'CMS proxy-risk', 'Use for a case-level evidence detail page.'],
    ['Dim_Evidence_Nodes', 184570, 'Evidence metadata', 'CMS proxy-risk', 'Use only with documented graph keys.'],
    ['Fact_Synthea_Safety', 2168, 'Safety validation fact', 'Synthea', 'Keep disconnected from CMS tables.'],
    ['Dim_Provider_Demo', 5, 'Demo directory', 'Provider catalogue', 'Live search must call protected API.'],
    ['Fact_Interventions', 3, 'Operational fact', 'Local demo state', 'Current rows may be tests.'],
    ['Fact_Outcomes', 3, 'Operational fact', 'Local demo state', 'Do not combine outcome anchor types.'],
    ['Fact_Audit_Events', 1, 'Audit evidence', 'Local demo state', 'Use only for operational demonstration.']
  ];
  sources.getRange('A3:E3').format = { fill: teal, font: { bold: true, color: '#FFFFFF' } };
  sources.getRange('A3:E12').format.wrapText = true;
  sources.getRange('A3:E12').format.borders = { style: 'continuous', color: '#CBD5E1' };
  ['A','B','C','D','E'].forEach((c,i)=>sources.getRange(`${c}3`).format.columnWidth=[29,12,24,22,45][i]);

  const measures = wb.worksheets.add('DAX Measures');
  measures.getRange('A1:C1').merge();
  measures.getRange('A1').values = [['Copy these DAX measures into Power BI']];
  measures.getRange('A1').format = { fill: navy, font: { bold: true, color: '#FFFFFF', size: 16 }, horizontalAlignment: 'center' };
  measures.getRange('A3:C11').values = [
    ['Measure', 'DAX', 'Format'],
    ['Cases', 'DISTINCTCOUNT(Fact_CMS_Cases[case_id])', 'Whole number'],
    ['High Risk Cases', 'CALCULATE([Cases], Fact_CMS_Cases[risk_band] = "HIGH")', 'Whole number'],
    ['High Risk Rate', 'DIVIDE([High Risk Cases], [Cases])', 'Percentage'],
    ['Average Risk Score', 'AVERAGE(Fact_CMS_Cases[risk_score_pct])', '1 decimal'],
    ['Observed Repeat ED 90d', 'AVERAGE(Fact_CMS_Cases[repeat_ed_90d_flag])', 'Percentage'],
    ['Safety Cases', 'COUNTROWS(Fact_Synthea_Safety)', 'Whole number'],
    ['Possible Emergency', 'CALCULATE([Safety Cases], Fact_Synthea_Safety[safety_status] = "POSSIBLE_EMERGENCY")', 'Whole number'],
    ['Interventions Logged', 'COUNTROWS(Fact_Interventions)', 'Whole number']
  ];
  measures.getRange('A3:C3').format = { fill: teal, font: { bold: true, color: '#FFFFFF' } };
  measures.getRange('A3:C11').format.wrapText = true;
  measures.getRange('A3:C11').format.borders = { style: 'continuous', color: '#CBD5E1' };
  measures.getRange('A3').format.columnWidth = 28;
  measures.getRange('B3').format.columnWidth = 82;
  measures.getRange('C3').format.columnWidth = 18;
  measures.getRange('A3:C11').format.fill = pale;
  measures.getRange('A3:C3').format.fill = teal;

  const out = 'C:/COGNIZANT HACKATHON/powerbi_dashboard/UC07_PowerBI_Dashboard_Companion.xlsx';
  const output = await SpreadsheetFile.exportXlsx(wb);
  await output.save(out);
  console.log(out);
}
main().catch(err => { console.error(err); process.exit(1); });
