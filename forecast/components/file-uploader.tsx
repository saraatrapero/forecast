"use client"

import { useRef, useState } from "react"
import { Upload, AlertCircle } from "lucide-react"
import * as XLSX from "xlsx"

interface FileUploaderProps {
  onFileUpload: (data: any) => void
}

export default function FileUploader({ onFileUpload }: FileUploaderProps) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [isDragging, setIsDragging] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const parseDateHeader = (header: string): Date | null => {
    if (!header || header.length === 0) return null

    const headerStr = String(header).trim()

    // Si es un número (fecha de Excel), convertir
    const numValue = Number.parseFloat(headerStr)
    if (!isNaN(numValue) && numValue > 0) {
      // Número de serie de Excel (días desde 1900-01-01)
      const excelDate = new Date((numValue - 25569) * 86400 * 1000)
      if (excelDate.getFullYear() >= 1995 && excelDate.getFullYear() <= new Date().getFullYear() + 5) {
        return new Date(excelDate.getFullYear(), excelDate.getMonth(), 1)
      }
    }

    // Formatos de texto esperados
    const formats = [
      { regex: /^(\d{4})-(\d{1,2})$/, year: 1, month: 2 }, // YYYY-MM
      { regex: /^(\d{1,2})-(\d{4})$/, year: 2, month: 1 }, // MM-YYYY
      { regex: /^(\d{4})\/(\d{1,2})$/, year: 1, month: 2 }, // YYYY/MM
      { regex: /^(\d{1,2})\/(\d{4})$/, year: 2, month: 1 }, // MM/YYYY
      { regex: /^(\d{4})\.(\d{1,2})$/, year: 1, month: 2 }, // YYYY.MM
      { regex: /^(\d{4})\s(\d{1,2})$/, year: 1, month: 2 }, // YYYY MM
      { regex: /^(\d{1,2})-([a-z]{3,})-(\d{4})$/i, month: 1, year: 3 }, // DD-MMM-YYYY
      { regex: /^([a-z]{3,})-(\d{4})$/i, month: 1, year: 2 }, // MMM-YYYY
      { regex: /^(\d{1,2})\/(\d{1,2})\/(\d{4})$/, month: 1, day: 2, year: 3 }, // MM/DD/YYYY
      { regex: /^(\d{1,2})-(\d{1,2})-(\d{4})$/, month: 1, day: 2, year: 3 }, // MM-DD-YYYY
    ]

    for (const fmt of formats) {
      const match = headerStr.match(fmt.regex)
      if (match) {
        const year = Number.parseInt(match[fmt.year])
        const month = Number.parseInt(match[fmt.month])

        // Validar que sea un año razonable
        if (year < 1995 || year > new Date().getFullYear() + 5) continue
        if (month >= 1 && month <= 12) {
          return new Date(year, month - 1, 1)
        }
      }
    }

    // Intenta parseador estándar como último recurso
    try {
      const parsed = new Date(headerStr)
      if (!isNaN(parsed.getTime())) {
        if (parsed.getFullYear() >= 1995 && parsed.getFullYear() <= new Date().getFullYear() + 5) {
          return new Date(parsed.getFullYear(), parsed.getMonth(), 1)
        }
      }
    } catch (_) {
      // Ignorar
    }

    return null
  }

  const parseExcel = (arrayBuffer: ArrayBuffer) => {
    try {
      const workbook = XLSX.read(new Uint8Array(arrayBuffer), { type: "array" })
      const worksheet = workbook.Sheets[workbook.SheetNames[0]]

      const rawData = XLSX.utils.sheet_to_json(worksheet, {
        header: 1,
        defval: "",
      })

      if (!rawData.length || rawData.length < 3) {
        throw new Error("El archivo debe tener al menos encabezados, conceptos y datos")
      }

      const dataStartCol = 9 // Columna J

      const conceptRow = (rawData[0] as (string | number)[]) || []
      const dateRow = (rawData[1] as (string | number)[]) || []

      const mesesRaw: { fecha: Date; original: string; concepto: string; colIdx: number }[] = []

      console.log("[v0] Estructura encontrada:")
      console.log("[v0] Fila 1 (conceptos):", conceptRow.slice(dataStartCol, dataStartCol + 10))
      console.log("[v0] Fila 2 (fechas):", dateRow.slice(dataStartCol, dataStartCol + 10))

      for (let i = dataStartCol; i < dateRow.length; i++) {
        const dateStr = String(dateRow[i] || "").trim()
        const concepto = String(conceptRow[i] || "").trim()

        if (!dateStr || dateStr.length < 2) continue

        const fecha = parseDateHeader(dateStr)
        if (fecha) {
          mesesRaw.push({
            fecha,
            original: dateStr,
            concepto,
            colIdx: i,
          })
          console.log(`[v0] Fecha encontrada: "${dateStr}" (${concepto}) -> ${fecha.toLocaleDateString()}`)
        } else {
          console.log(`[v0] No se pudo parsear fecha: "${dateStr}"`)
        }
      }

      if (mesesRaw.length === 0) {
        throw new Error(
          "No se encontraron fechas válidas en la fila 2 del Excel. " +
            "Soportados: YYYY-MM, MM-YYYY, YYYY/MM, DD/MM/YYYY, etc.",
        )
      }

      // Ordenar por fecha
      mesesRaw.sort((a, b) => a.fecha.getTime() - b.fecha.getTime())

      const dataMap = new Map<string, any>()
      let totalSkus = 0

      for (let rowIdx = 2; rowIdx < rawData.length; rowIdx++) {
        const row = rawData[rowIdx] as (string | number)[]

        const codigoRaw = String(row[0] || "").trim()
        if (!codigoRaw || codigoRaw.length < 35) continue

        const codigoCliente = codigoRaw.substring(0, 28)
        const codigoArticulo = codigoRaw.substring(codigoRaw.length - 7)

        // Metadatos
        const envaseDesc = String(row[1] || "").trim()
        const formatoDesc = String(row[2] || "").trim()
        const grupoMat = String(row[3] || "").trim()
        const grupoMatDesc = String(row[4] || "").trim()
        const marcaDesc = String(row[5] || "").trim()
        const materialId = String(row[6] || "").trim()
        const marcaDesglose = String(row[7] || "").trim()
        const negocioDesc = String(row[8] || "").trim()

        // Ventas por mes
        const ventasMes: Record<string, { valor: number; concepto: string }> = {}
        mesesRaw.forEach((m) => {
          const val = row[m.colIdx]
          const numVal = typeof val === "number" ? val : Number.parseFloat(String(val || "0"))
          const key = m.original
          if (!ventasMes[key]) {
            ventasMes[key] = { valor: 0, concepto: m.concepto }
          }
          ventasMes[key].valor = isNaN(numVal) ? 0 : numVal
        })

        const skuId = `${codigoCliente}-${codigoArticulo}`
        dataMap.set(skuId, {
          codigoCliente,
          codigoArticulo,
          skuId,
          envaseDesc,
          formatoDesc,
          grupoMat,
          grupoMatDesc,
          marcaDesc,
          materialId,
          marcaDesglose,
          negocioDesc,
          ventasMes,
        })
        totalSkus++
      }

      if (dataMap.size === 0) {
        throw new Error("No se encontraron datos válidos en el archivo a partir de la fila 3")
      }

      // Agrupar por cliente
      const clientesMap = new Map<string, any>()
      dataMap.forEach((sku) => {
        if (!clientesMap.has(sku.codigoCliente)) {
          clientesMap.set(sku.codigoCliente, {
            codigo: sku.codigoCliente,
            skus: [],
          })
        }
        clientesMap.get(sku.codigoCliente).skus.push(sku)
      })

      const clientes = Array.from(clientesMap.values())

      console.log(
        "[v0] Parseado exitosamente:",
        clientes.length,
        "clientes,",
        totalSkus,
        "SKUs,",
        mesesRaw.length,
        "períodos",
      )

      onFileUpload({
        clientes,
        meses: mesesRaw.map((m) => m.original),
        mesesFecha: mesesRaw.map((m) => m.fecha),
        conceptos: mesesRaw.reduce((acc, m) => ({ ...acc, [m.original]: m.concepto }), {}),
        totalSkus,
      })
      setError(null)
    } catch (err) {
      console.error("[v0] Error parsing:", err)
      setError(err instanceof Error ? err.message : "Error al procesar el archivo")
    }
  }

  const handleFile = (file: File) => {
    if (!file.name.endsWith(".xlsx") && !file.name.endsWith(".xls")) {
      setError("Por favor, sube un archivo Excel (.xlsx o .xls)")
      return
    }

    const reader = new FileReader()
    reader.onload = (e) => {
      if (e.target?.result) {
        parseExcel(e.target.result as ArrayBuffer)
      }
    }
    reader.onerror = () => setError("Error al leer el archivo")
    reader.readAsArrayBuffer(file)
  }

  return (
    <div>
      <div
        onDragOver={(e) => {
          e.preventDefault()
          setIsDragging(true)
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={(e) => {
          e.preventDefault()
          setIsDragging(false)
          const file = e.dataTransfer.files?.[0]
          if (file) handleFile(file)
        }}
        className={`border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors ${
          isDragging ? "border-blue-400 bg-blue-950/30" : "border-slate-600 bg-slate-900/50 hover:border-slate-500"
        }`}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".xlsx,.xls"
          onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
          className="hidden"
        />
        <button onClick={() => inputRef.current?.click()} className="flex flex-col items-center gap-2 w-full">
          <Upload className="w-8 h-8 text-blue-400" />
          <span className="text-sm font-medium text-slate-300">Arrastra tu Excel aquí o haz clic</span>
          <span className="text-xs text-slate-500">Formato: Cliente (28 chars) + SKU (7 chars) + datos de ventas</span>
        </button>
      </div>

      {error && (
        <div className="flex items-center gap-2 mt-3 p-3 bg-red-900/30 rounded-lg border border-red-700/50">
          <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0" />
          <span className="text-xs text-red-300">{error}</span>
        </div>
      )}
    </div>
  )
}
