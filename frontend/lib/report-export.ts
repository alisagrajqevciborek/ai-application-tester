import type { TestHistory, TestIssue } from "@/lib/types"

interface ExportReportParams {
  test: TestHistory
  summaryText: string
  issues: TestIssue[]
  criticalCount: number
  majorCount: number
  minorCount: number
}

const sanitizeStackTrace = (text: string): string =>
  text.replace(/\/_next\/static\/chunks\/[^\s),:\]]+/g, (match) => {
    const filename = match.split("/").pop() ?? match
    return filename.replace(/[?#].*$/, "")
  })

const breakLongWords = (text: string, maxLen = 55): string =>
  text.replace(new RegExp(`\\S{${maxLen},}`, "g"), (word) =>
    word.replace(/([/_.\\-])(?=[A-Za-z0-9])/g, "$1 ").trimEnd()
  )

const pdfText = (text: string): string => breakLongWords(sanitizeStackTrace(text ?? ""))

const getLiveIssueCounts = (issues: TestIssue[]) => {
  const counts = { critical: 0, major: 0, minor: 0 }

  for (const issue of issues) {
    const severity = (issue.severity ?? "").toLowerCase()
    if (severity === "critical") counts.critical += 1
    else if (severity === "major") counts.major += 1
    else if (severity === "minor") counts.minor += 1
  }

  return counts
}

const buildExpectedBehaviorFromIssue = (issue: TestIssue): string => {
  const title = (issue.title ?? "").toLowerCase()
  const description = (issue.description ?? "").toLowerCase()
  const location = (issue.location ?? "").trim()
  const target = location ? ` on ${location}` : ""

  const checks: Array<[RegExp, string]> = [
    [/login|sign\s*in|auth/, `Users should be able to complete login successfully${target}; the action should trigger authentication immediately and navigate to the authenticated page without retries or unresponsive clicks.`],
    [/button|click|tap|unresponsive/, `The button interaction should respond on the first click/tap${target}, execute its assigned action, and show the expected UI state change without delay.`],
    [/validation|form|input|field|email|password/, `Form validation should display clear inline messages next to the affected field${target}, keep messages visible in viewport, and block submission only until valid input is provided.`],
    [/alt\s*text|accessibility|aria/, `Accessible metadata should be present${target}: informative images need meaningful alt text, decorative images should use empty alt attributes, and assistive technologies should read content correctly.`],
    [/contrast|color/, `Text and interactive elements should meet WCAG AA contrast requirements${target} so all labels and content remain readable in normal viewing conditions.`],
    [/performance|slow|latency|load|response/, `The page should load and become interactive within target performance thresholds${target}, with stable rendering and responsive user actions during initial load.`],
    [/api|request|network|4\d\d|5\d\d|failed|error/, `All required network/API requests should succeed${target} with valid responses, and dependent UI components should render complete data without broken states.`],
    [/font|typography/, `Custom fonts should load successfully${target}, and text should render with the intended font family, spacing, and visual consistency.`],
    [/image|screenshot|media/, `Images and media should load correctly${target} with valid sources, proper dimensions, and no broken placeholders.`],
  ]

  for (const [pattern, expected] of checks) {
    if (pattern.test(title) || pattern.test(description)) {
      return expected
    }
  }

  return `The affected feature should complete its primary user action successfully${target}, display the correct UI outcome, and avoid console or runtime errors during normal use.`
}

export const getExpectedResultText = (issue: TestIssue): string => {
  const raw = (issue.description ?? "").replace(/\r\n/g, "\n").trim()
  if (!raw) {
    return "The feature should work correctly without errors after the fix."
  }

  const lines = raw.split("\n").map((line) => line.trim())
  const headerRegex = /^(what[’']?s happening|what visitors may notice|why it happens|why it matters|suggested fix|suggested next step|details \(from the test\)|quick check|expected behavior)\s*:\s*$/i
  let currentSection = ""
  const quickCheckItems: string[] = []
  const expectedItems: string[] = []

  for (const line of lines) {
    if (!line) continue
    if (headerRegex.test(line)) {
      currentSection = line.toLowerCase()
      continue
    }

    if (currentSection.startsWith("quick check")) {
      const cleaned = line.replace(/^[-•]\s*/, "").replace(/^\d+\.\s*/, "").trim()
      if (cleaned) quickCheckItems.push(cleaned)
      continue
    }

    if (currentSection.startsWith("expected behavior")) {
      const cleaned = line.replace(/^[-•]\s*/, "").replace(/^\d+\.\s*/, "").trim()
      if (cleaned) expectedItems.push(cleaned)
    }
  }

  const picked = expectedItems.length > 0 ? expectedItems : quickCheckItems
  if (picked.length > 0) {
    return picked.join(" ")
  }

  return buildExpectedBehaviorFromIssue(issue)
}

export const getPdfLocationText = (issue: TestIssue): string => {
  const selector = (issue.selector ?? "").trim()
  if (selector) {
    return selector
  }

  const rawLocation = (issue.location ?? "").trim()
  if (!rawLocation) {
    return ""
  }

  try {
    const url = new URL(rawLocation)
    const path = `${url.pathname || ""}${url.search || ""}${url.hash || ""}`.trim()
    return path === "/" ? "" : path
  } catch {
    const stripped = rawLocation.replace(/^https?:\/\/[^/]+/i, "").trim()
    return stripped === "/" ? "" : stripped
  }
}

const waitForNetworkIdle = (idleMs = 500): Promise<void> =>
  new Promise((resolve) => {
    let timer: ReturnType<typeof setTimeout> = setTimeout(resolve, idleMs)
    try {
      const observer = new PerformanceObserver(() => {
        clearTimeout(timer)
        timer = setTimeout(() => {
          observer.disconnect()
          resolve()
        }, idleMs)
      })
      observer.observe({ entryTypes: ["resource"] })
    } catch {
      // fallback timer already running
    }
  })

export const exportReportPdf = async ({
  test,
  summaryText,
  issues,
  criticalCount,
  majorCount,
  minorCount,
}: ExportReportParams): Promise<void> => {
  await waitForNetworkIdle()

  const liveCounts = getLiveIssueCounts(issues)
  const resolvedCriticalCount = Math.max(criticalCount, liveCounts.critical)
  const resolvedMajorCount = Math.max(majorCount, liveCounts.major)
  const resolvedMinorCount = Math.max(minorCount, liveCounts.minor)

  const { default: jsPDF } = await import("jspdf")
  const doc = new jsPDF()
  const pageWidth = doc.internal.pageSize.getWidth()
  const margin = 20
  let yPos = margin

  doc.setFont("times", "normal")

  doc.setFontSize(14)
  doc.setTextColor(255, 140, 0)
  doc.text("TestFlow - Test Report", margin, yPos)
  yPos += 12

  doc.setFontSize(14)
  doc.setTextColor(0, 0, 0)
  doc.setFont("times", "bold")
  doc.text("Test Information", margin, yPos)
  yPos += 8

  doc.setFontSize(12)
  doc.setFont("times", "normal")
  const testInfo = [
    ["Application Name", test.appName],
    ["Version", test.versionName],
    ["Test Type", test.testType.charAt(0).toUpperCase() + test.testType.slice(1)],
    ["Test Date", test.date],
    ["Status", test.status.charAt(0).toUpperCase() + test.status.slice(1)],
    ["Pass Rate", `${test.passRate}%`],
    ["Fail Rate", `${test.failRate}%`],
  ]

  testInfo.forEach((row) => {
    if (yPos > doc.internal.pageSize.getHeight() - 30) {
      doc.addPage()
      yPos = margin
    }
    doc.setFont("times", "bold")
    doc.text(`${row[0]}:`, margin, yPos)
    doc.setFont("times", "normal")
    doc.text(row[1], margin + 60, yPos)
    yPos += 7
  })

  yPos += 5

  if (yPos > doc.internal.pageSize.getHeight() - 50) {
    doc.addPage()
    yPos = margin
  }
  doc.setFontSize(14)
  doc.setFont("times", "bold")
  doc.text("Test Summary", margin, yPos)
  yPos += 8

  doc.setFontSize(12)
  doc.setFont("times", "normal")
  const summaryLines = doc.splitTextToSize(pdfText(summaryText), pageWidth - 2 * margin)
  summaryLines.forEach((line: string) => {
    if (yPos > doc.internal.pageSize.getHeight() - 30) {
      doc.addPage()
      yPos = margin
    }
    doc.text(line, margin, yPos)
    yPos += 6
  })

  yPos += 5

  if (yPos > doc.internal.pageSize.getHeight() - 50) {
    doc.addPage()
    yPos = margin
  }
  doc.setFontSize(14)
  doc.setFont("times", "bold")
  doc.text("Issue Statistics", margin, yPos)
  yPos += 8

  doc.setFontSize(12)
  doc.setFont("times", "normal")
  const stats = [
    ["Critical Issues", resolvedCriticalCount.toString()],
    ["Major Issues", resolvedMajorCount.toString()],
    ["Minor Issues", resolvedMinorCount.toString()],
    ["Total Issues", issues.length.toString()],
  ]

  stats.forEach((row) => {
    if (yPos > doc.internal.pageSize.getHeight() - 30) {
      doc.addPage()
      yPos = margin
    }
    doc.setFont("times", "bold")
    doc.text(`${row[0]}:`, margin, yPos)
    doc.setFont("times", "normal")
    doc.text(row[1], margin + 60, yPos)
    yPos += 7
  })

  yPos += 5

  if (yPos > doc.internal.pageSize.getHeight() - 60) {
    doc.addPage()
    yPos = margin
  }
  doc.setFontSize(14)
  doc.setFont("times", "bold")
  doc.text("Detailed Findings", margin, yPos)
  yPos += 10

  if (issues.length > 0) {
    const col1W = 12
    const col2W = 80
    const col3W = pageWidth - 2 * margin - col1W - col2W
    const colX = [margin, margin + col1W, margin + col1W + col2W]
    const headerH = 10
    const cellPad = 2.5
    const lineH = 5.5

    const drawTableHeader = () => {
      doc.setFillColor(255, 140, 0)
      doc.rect(margin, yPos, col1W + col2W + col3W, headerH, "F")
      doc.setFontSize(12)
      doc.setFont("times", "bold")
      doc.setTextColor(255, 255, 255)
      doc.text("#", colX[0] + cellPad, yPos + headerH - cellPad)
      doc.text("Error Title", colX[1] + cellPad, yPos + headerH - cellPad)
      doc.text("Expected Result", colX[2] + cellPad, yPos + headerH - cellPad)
      doc.setTextColor(0, 0, 0)
      yPos += headerH
    }

    drawTableHeader()

    issues.forEach((issue, index) => {
      const locationText = getPdfLocationText(issue)
      const titleLines = doc.splitTextToSize(pdfText(issue.title), col2W - 2 * cellPad)
      const severityLabel = "Severity: "
      const severityValue = issue.severity.charAt(0).toUpperCase() + issue.severity.slice(1)
      const severityLines = doc.splitTextToSize(
        pdfText(`${severityLabel}${severityValue}`),
        col2W - 2 * cellPad
      )
      const locationLabel = "Location: "
      const locationLines = locationText
        ? doc.splitTextToSize(pdfText(`${locationLabel}${locationText}`), col2W - 2 * cellPad)
        : []
      const expectedResultText = getExpectedResultText(issue)

      const secondColLineCount = titleLines.length + severityLines.length + locationLines.length
      const thirdColLines = doc.splitTextToSize(pdfText(expectedResultText), col3W - 2 * cellPad)
      const maxLines = Math.max(secondColLineCount, thirdColLines.length, 1)
      const cellH = maxLines * lineH + 2 * cellPad

      if (yPos + cellH > doc.internal.pageSize.getHeight() - margin) {
        doc.addPage()
        yPos = margin
        drawTableHeader()
      }

      if (index % 2 === 0) {
        doc.setFillColor(252, 252, 252)
        doc.rect(margin, yPos, col1W + col2W + col3W, cellH, "F")
      }

      doc.setDrawColor(210, 210, 210)
      doc.rect(colX[0], yPos, col1W, cellH)
      doc.rect(colX[1], yPos, col2W, cellH)
      doc.rect(colX[2], yPos, col3W, cellH)

      doc.setFontSize(12)
      doc.setFont("times", "bold")
      doc.text(`${index + 1}`, colX[0] + cellPad, yPos + cellPad + lineH)

      let secondColY = yPos + cellPad + lineH
      const secondColX = colX[1] + cellPad

      titleLines.forEach((line: string) => {
        doc.setFont("times", "bold")
        doc.text(line, secondColX, secondColY)
        secondColY += lineH
      })

      severityLines.forEach((line: string, idx: number) => {
        doc.setFont("times", "normal")
        if (idx === 0 && line.startsWith(severityLabel)) {
          doc.setFont("times", "bold")
          doc.text(severityLabel, secondColX, secondColY)
          const labelWidth = doc.getTextWidth(severityLabel)
          doc.setFont("times", "normal")
          doc.text(line.slice(severityLabel.length), secondColX + labelWidth, secondColY)
        } else {
          doc.text(line, secondColX, secondColY)
        }
        secondColY += lineH
      })

      locationLines.forEach((line: string, idx: number) => {
        doc.setFont("times", "normal")
        if (idx === 0 && line.startsWith(locationLabel)) {
          doc.setFont("times", "bold")
          doc.text(locationLabel, secondColX, secondColY)
          const labelWidth = doc.getTextWidth(locationLabel)
          doc.setFont("times", "normal")
          doc.text(line.slice(locationLabel.length), secondColX + labelWidth, secondColY)
        } else {
          doc.text(line, secondColX, secondColY)
        }
        secondColY += lineH
      })

      doc.setFont("times", "normal")
      thirdColLines.forEach((line: string, li: number) => {
        doc.text(line, colX[2] + cellPad, yPos + cellPad + (li + 1) * lineH)
      })

      yPos += cellH
    })
  } else {
    doc.setFontSize(12)
    doc.setFont("times", "normal")
    doc.text("No issues found during testing.", margin, yPos)
    yPos += 7
  }

  const totalPages = (doc as any).internal.getNumberOfPages()
  for (let i = 1; i <= totalPages; i++) {
    doc.setPage(i)
    doc.setFontSize(12)
    doc.setFont("times", "normal")
    doc.setTextColor(150, 150, 150)
    doc.text(
      `Page ${i} of ${totalPages} - TestFlow Test Report`,
      pageWidth / 2,
      doc.internal.pageSize.getHeight() - 10,
      { align: "center" }
    )
  }

  doc.save(`testflow-report-${test.versionName.replace(/\s+/g, "-")}-${test.date.replace(/\//g, "-")}.pdf`)
}

export const exportReportExcel = async ({
  test,
  summaryText,
  issues,
  criticalCount,
  majorCount,
}: ExportReportParams): Promise<void> => {
  const ExcelJSImport = await import("exceljs")
  const ExcelJS: any = (ExcelJSImport as any).default ?? ExcelJSImport

  const toTitleCase = (value: string) => value.charAt(0).toUpperCase() + value.slice(1)
  const getPriorityLabel = (severity: string): string => {
    if (severity === "critical") return "High"
    if (severity === "major") return "Medium"
    return "Low"
  }

  const liveCounts = getLiveIssueCounts(issues)
  const resolvedCriticalCount = Math.max(criticalCount, liveCounts.critical)
  const resolvedMajorCount = Math.max(majorCount, liveCounts.major)
  const overallPriority = resolvedCriticalCount > 0 ? "High" : resolvedMajorCount > 0 ? "Medium" : "Low"

  const rows: Array<Array<string>> = []
  const emptyRow = () => new Array(10).fill("")

  const titleRow = emptyRow()
  titleRow[0] = "TEST CASE TEMPLATE"
  rows.push(titleRow)
  rows.push(emptyRow())

  const leftMeta: Array<[string, string]> = [
    ["Project Name", test.appName],
    ["Priority", overallPriority],
    ["Description", summaryText],
    ["Test Objective", "Validate the feature behavior and capture defects found during automated execution."],
  ]
  const rightMeta: Array<[string, string]> = [
    ["Test Case Author", "TestFlow AI"],
    ["Test Case Reviewer", "QA Team"],
    ["Test Case Version", test.versionName],
    ["Test Execution Date", test.date],
  ]

  for (let i = 0; i < 4; i++) {
    const row = emptyRow()
    row[0] = leftMeta[i][0]
    row[2] = leftMeta[i][1]
    row[5] = rightMeta[i][0]
    row[7] = rightMeta[i][1]
    rows.push(row)
  }

  rows.push(emptyRow())

  const tableHeaderIndex = rows.length
  rows.push([
    "Test Case ID",
    "Test Steps",
    "Input Data",
    "Expected Results",
    "Actual Results",
    "Test Environment",
    "Execution Status",
    "Bug Severity",
    "Bug Priority",
    "Notes",
  ])

  if (issues.length === 0) {
    rows.push([
      "1",
      "No issues detected",
      "-",
      "The feature should work correctly without errors.",
      "No failing behavior observed.",
      `${test.appName} (${toTitleCase(test.testType)})`,
      toTitleCase(test.status),
      "-",
      "-",
      "Run completed successfully.",
    ])
  } else {
    issues.forEach((issue, index) => {
      const locationText = getPdfLocationText(issue)
      const actualResult = (issue.description || issue.title || "Detected failure in the tested feature.")
        .replace(/\r\n/g, "\n")
        .split("\n")
        .map((line) => line.trim())
        .filter((line) => line.length > 0)
        .slice(0, 2)
        .join(" ")

      rows.push([
        String(index + 1),
        issue.title,
        locationText || "-",
        getExpectedResultText(issue),
        actualResult,
        `${test.appName} (${toTitleCase(test.testType)})`,
        toTitleCase(test.status),
        toTitleCase(issue.severity),
        getPriorityLabel(issue.severity),
        "",
      ])
    })
  }

  const workbook = new ExcelJS.Workbook()
  const worksheet = workbook.addWorksheet("Test Case Report")

  worksheet.columns = [
    { width: 12 },
    { width: 28 },
    { width: 22 },
    { width: 34 },
    { width: 28 },
    { width: 20 },
    { width: 18 },
    { width: 14 },
    { width: 14 },
    { width: 24 },
  ]

  rows.forEach((row) => worksheet.addRow(row))

  worksheet.mergeCells("A1:J1")
  worksheet.mergeCells("A3:B3"); worksheet.mergeCells("C3:D3")
  worksheet.mergeCells("A4:B4"); worksheet.mergeCells("C4:D4")
  worksheet.mergeCells("A5:B5"); worksheet.mergeCells("C5:D5")
  worksheet.mergeCells("A6:B6"); worksheet.mergeCells("C6:D6")
  worksheet.mergeCells("F3:G3"); worksheet.mergeCells("H3:I3")
  worksheet.mergeCells("F4:G4"); worksheet.mergeCells("H4:I4")
  worksheet.mergeCells("F5:G5"); worksheet.mergeCells("H5:I5")
  worksheet.mergeCells("F6:G6"); worksheet.mergeCells("H6:I6")

  const borderAll = {
    top: { style: "thin", color: { argb: "FF4B4B4B" } },
    bottom: { style: "thin", color: { argb: "FF4B4B4B" } },
    left: { style: "thin", color: { argb: "FF4B4B4B" } },
    right: { style: "thin", color: { argb: "FF4B4B4B" } },
  }

  const labelStyle = {
    font: { bold: true, size: 12 },
    fill: { type: "pattern", pattern: "solid", fgColor: { argb: "FFF2D233" } },
    alignment: { vertical: "middle", horizontal: "left", wrapText: true },
    border: borderAll,
  }

  const valueStyle = {
    font: { size: 11 },
    fill: { type: "pattern", pattern: "solid", fgColor: { argb: "FFEDEDED" } },
    alignment: { vertical: "middle", horizontal: "left", wrapText: true },
    border: borderAll,
  }

  const titleStyle = {
    font: { bold: true, size: 24, color: { argb: "FF111111" } },
    fill: { type: "pattern", pattern: "solid", fgColor: { argb: "FFEDEDED" } },
    alignment: { vertical: "middle", horizontal: "center" },
  }

  const tableHeaderStyle = {
    font: { bold: true, size: 11, color: { argb: "FFFFFFFF" } },
    fill: { type: "pattern", pattern: "solid", fgColor: { argb: "FF4957A6" } },
    alignment: { vertical: "middle", horizontal: "center", wrapText: true },
    border: borderAll,
  }

  const dataCellStyle = {
    font: { size: 11 },
    fill: { type: "pattern", pattern: "solid", fgColor: { argb: "FFEDEDED" } },
    alignment: { vertical: "top", horizontal: "left", wrapText: true },
    border: borderAll,
  }

  const chipPassStyle = {
    font: { bold: true, size: 10, color: { argb: "FF2E7D32" } },
    fill: { type: "pattern", pattern: "solid", fgColor: { argb: "FFE8F5E9" } },
    alignment: { vertical: "middle", horizontal: "center" },
    border: borderAll,
  }

  const chipHighStyle = {
    font: { bold: true, size: 10, color: { argb: "FFC62828" } },
    fill: { type: "pattern", pattern: "solid", fgColor: { argb: "FFFFEBEE" } },
    alignment: { vertical: "middle", horizontal: "center" },
    border: borderAll,
  }

  const chipMediumStyle = {
    font: { bold: true, size: 10, color: { argb: "FFEF6C00" } },
    fill: { type: "pattern", pattern: "solid", fgColor: { argb: "FFFFF3E0" } },
    alignment: { vertical: "middle", horizontal: "center" },
    border: borderAll,
  }

  const chipLowStyle = {
    font: { bold: true, size: 10, color: { argb: "FF1565C0" } },
    fill: { type: "pattern", pattern: "solid", fgColor: { argb: "FFE3F2FD" } },
    alignment: { vertical: "middle", horizontal: "center" },
    border: borderAll,
  }

  const applyStyle = (row: number, col: number, style: any) => {
    const cell = worksheet.getCell(row, col)
    cell.font = style.font
    cell.fill = style.fill
    cell.alignment = style.alignment
    cell.border = style.border
  }

  applyStyle(1, 1, titleStyle)

  for (let r = 3; r <= 6; r++) {
    applyStyle(r, 1, labelStyle)
    applyStyle(r, 3, valueStyle)
    applyStyle(r, 6, labelStyle)
    applyStyle(r, 8, valueStyle)
  }

  const tableHeaderRow = tableHeaderIndex + 1
  for (let c = 1; c <= 10; c++) {
    applyStyle(tableHeaderRow, c, tableHeaderStyle)
  }

  for (let r = tableHeaderRow + 1; r <= rows.length; r++) {
    for (let c = 1; c <= 10; c++) {
      applyStyle(r, c, dataCellStyle)
    }

    const status = (String(rows[r - 1][6] || "")).toLowerCase()
    if (status === "pass" || status === "success" || status === "running") {
      applyStyle(r, 7, chipPassStyle)
    }

    const severity = (String(rows[r - 1][7] || "")).toLowerCase()
    if (severity === "high" || severity === "critical" || severity === "major") {
      applyStyle(r, 8, chipHighStyle)
    } else if (severity === "medium") {
      applyStyle(r, 8, chipMediumStyle)
    } else if (severity === "low" || severity === "minor") {
      applyStyle(r, 8, chipLowStyle)
    }

    const priority = (String(rows[r - 1][8] || "")).toLowerCase()
    if (priority === "high") {
      applyStyle(r, 9, chipHighStyle)
    } else if (priority === "medium") {
      applyStyle(r, 9, chipMediumStyle)
    } else if (priority === "low") {
      applyStyle(r, 9, chipLowStyle)
    }
  }

  worksheet.getRow(1).height = 42
  for (let r = 2; r <= rows.length; r++) {
    if (r === tableHeaderRow) {
      worksheet.getRow(r).height = 30
    } else if (r > tableHeaderRow) {
      worksheet.getRow(r).height = 48
    } else {
      worksheet.getRow(r).height = 24
    }
  }

  worksheet.autoFilter = {
    from: { row: tableHeaderRow, column: 1 },
    to: { row: tableHeaderRow, column: 10 },
  }

  const buffer = await workbook.xlsx.writeBuffer()
  const blob = new Blob([buffer], {
    type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  })
  const url = URL.createObjectURL(blob)
  const link = document.createElement("a")
  link.href = url
  link.download = `testflow-test-case-report-${test.versionName.replace(/\s+/g, "-")}-${test.date.replace(/\//g, "-")}.xlsx`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}
